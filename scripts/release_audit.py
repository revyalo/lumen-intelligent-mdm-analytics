"""Scan the publication tree, including ZIP members, for common release hygiene mistakes."""
import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".ruff_cache",
        "runtime", "build", "dist", ".ipynb_checkpoints", "mpl-cache", ".matplotlib", ".cache"}
PATTERNS = {
    "personal_absolute_path": re.compile(r"(?:/Users/|/home/)[A-Za-z0-9_.-]+/|[A-Z]:\\Users\\[A-Za-z0-9_.-]+\\"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "external_api_key": re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{32,}"),
    "original_assessment": re.compile(r"(?i)\b(?:" + "[aá]" + "baco|" + "or" + "via|" + "guia_" + "prueba" + r")\b"),
}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".sqlite", ".db", ".joblib", ".pkl", ".pickle",
                      ".pt", ".pth", ".safetensors", ".onnx", ".pdf"}


def audit() -> dict:
    findings, inventory = [], []

    def inspect(name: str, content: bytes, depth: int = 0):
        suffix = Path(name).suffix.lower()
        if suffix in FORBIDDEN_SUFFIXES or Path(name).name in {".env", "secrets.toml"}:
            findings.append({"file": name, "issue": "Private/runtime/model/reference file requires exclusion"})
        if len(content) > 5 * 1024 * 1024:
            findings.append({"file": name, "issue": "File exceeds 5 MiB publication budget"})
        if suffix == ".zip":
            if depth >= 2:
                findings.append({"file": name, "issue": "Nested archive depth exceeds audit limit"})
                return
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    if member.file_size > 20 * 1024 * 1024:
                        findings.append({"file": name+"!"+member.filename, "issue": "Oversized archived member"})
                        continue
                    if member.filename.startswith("/") or ".." in Path(member.filename).parts:
                        findings.append({"file": name, "issue": "Unsafe archive member path"})
                    inspect(name+"!"+member.filename, archive.read(member), depth+1)
            return
        if suffix in {".jpg", ".jpeg", ".png", ".gif", ".ico"}:
            return
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            findings.append({"file": name, "issue": "Unreviewed binary format"})
            return
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                findings.append({"file": name, "issue": label, "line": text.count("\n", 0, match.start())+1})

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in SKIP or part.endswith(".egg-info") for part in relative.parts):
            continue
        data = path.read_bytes()
        inventory.append({"path": relative.as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        inspect(relative.as_posix(), data)
    return {"status": "PASS" if not findings else "REVIEW_REQUIRED", "files_scanned": len(inventory),
            "findings": findings, "scope": "Known token/key signatures, personal paths, reference names, file sizes and ZIP members",
            "limits": "Heuristic source scan, not a guarantee against every secret. Images require visual review.",
            "inventory": inventory}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"runtime"/"release-audit.json")
    args = parser.parse_args()
    result = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(f"Release audit: {result['status']}; {result['files_scanned']} files; {len(result['findings'])} findings")
    if result["findings"]:
        print(json.dumps(result["findings"], indent=2))
        raise SystemExit(1)
