"""Record installed dependency versions, declared licenses and hashes of bundled notices."""
import argparse
import csv
import hashlib
import json
import tomllib
from importlib.metadata import distribution, distributions
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]


def closure(requirements: list[str]) -> set[str]:
    pending = [(Requirement(item).name, tuple(Requirement(item).extras)) for item in requirements]
    visited, result = set(), set()
    while pending:
        name, extras = pending.pop()
        name = canonicalize_name(name)
        if (name, extras) in visited:
            continue
        visited.add((name, extras))
        result.add(name)
        for text in distribution(name).requires or []:
            requirement = Requirement(text)
            if requirement.marker and not any(requirement.marker.evaluate({"extra": e}) for e in ("", *extras)):
                continue
            pending.append((requirement.name, tuple(sorted(requirement.extras))))
    return result


def inventory() -> list[dict]:
    project = tomllib.loads((ROOT/"pyproject.toml").read_text())["project"]
    runtime = closure(project["dependencies"])
    dev = closure(project["optional-dependencies"]["dev"])
    direct = {canonicalize_name(Requirement(x).name) for x in project["dependencies"]}
    rows = []
    for dist in sorted(distributions(), key=lambda d: d.metadata["Name"].lower()):
        name = canonicalize_name(dist.metadata["Name"])
        if name == canonicalize_name(project["name"]):
            continue
        expression = dist.metadata.get("License-Expression")
        classifiers = [c.split(" :: ")[-1] for c in dist.metadata.get_all("Classifier", []) if c.startswith("License ::")]
        declared = expression or "; ".join(classifiers) or (dist.metadata.get("License", "UNKNOWN").strip().splitlines() or ["UNKNOWN"])[0]
        notices = []
        for path in dist.files or []:
            base = Path(str(path)).name.lower()
            if base.startswith(("license", "licence", "copying", "notice")):
                local = Path(dist.locate_file(path))
                if local.is_file():
                    notices.append({"path": str(path), "sha256": hashlib.sha256(local.read_bytes()).hexdigest()})
        rows.append({"package": name, "version": dist.version, "scope": "runtime" if name in runtime else "development" if name in dev else "installer/tooling",
                     "direct_runtime": name in direct, "declared_license": declared,
                     "license_evidence": "License-Expression" if expression else "Classifier" if classifiers else "License first line",
                     "notices": notices})
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"runtime"/"dependency-licenses.json")
    args = parser.parse_args()
    rows = inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"scope": "Installed runtime/development distributions, optional semantic extra excluded unless installed",
                                     "packages": rows}, indent=2)+"\n", encoding="utf-8")
    with args.output.with_suffix(".csv").open("w", newline="", encoding="utf-8") as output:
        fields = ["package", "version", "scope", "direct_runtime", "declared_license", "license_evidence", "notice_files"]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({**{k: row[k] for k in fields if k != "notice_files"}, "notice_files": len(row["notices"])})
    unknown = sum(row["declared_license"] == "UNKNOWN" for row in rows)
    print(f"Inventoried {len(rows)} installed distributions; {unknown} unknown declared licenses. Full terms remain authoritative.")
