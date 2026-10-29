import json
import logging
from pathlib import Path

import pandas as pd

from intelligent_mdm.models import DatasetBundle, FOREIGN_KEYS, PRIMARY_KEYS

logger = logging.getLogger(__name__)
DATE_COLUMNS = {"created_at", "updated_at", "order_date", "sale_date", "movement_date", "as_of"}


def read_csv(source, required: tuple[str, ...] = ()) -> pd.DataFrame:
    """Read a local UTF-8 CSV; parse date columns only if every known value is valid."""
    try:
        df = pd.read_csv(source, dtype={c: "string" for c in ["tax_id", "phone", "sku", "record_id"]})
    except (ValueError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise ValueError(f"Unable to parse CSV: {exc}") from exc
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if df.columns.duplicated().any():
        raise ValueError("Duplicate column names")
    for col in DATE_COLUMNS.intersection(df.columns):
        parsed = pd.to_datetime(df[col], errors="coerce", format="mixed", utc=True).dt.tz_localize(None)
        if parsed[df[col].notna()].notna().all():
            df[col] = parsed
    return df


def validate_bundle(bundle: DatasetBundle) -> pd.DataFrame:
    """Structural checks return issues instead of silently removing bad rows."""
    issues = []
    for name, frame in bundle.tables.items():
        pk = PRIMARY_KEYS.get(name)
        if pk and pk not in frame:
            issues.append((name, "missing_primary_key", pk, len(frame)))
        elif pk:
            count = int(frame[pk].isna().sum() + frame[pk].duplicated().sum())
            if count:
                issues.append((name, "invalid_primary_key", pk, count))
        for col, target, target_key in FOREIGN_KEYS.get(name, []):
            if col not in frame or target not in bundle.tables or target_key not in bundle.tables[target]:
                issues.append((name, "missing_relation", col, len(frame)))
                continue
            count = int((~frame[col].isin(bundle.tables[target][target_key])).sum())
            if count:
                issues.append((name, "orphan_foreign_key", col, count))
    return pd.DataFrame(issues, columns=["dataset", "issue", "field", "rows"])


def save_bundle(bundle: DatasetBundle, folder: str | Path) -> None:
    path = Path(folder)
    path.mkdir(parents=True, exist_ok=True)
    for name, frame in bundle.tables.items():
        frame.to_csv(path / f"{name}.csv", index=False)
    labels = path / "evaluation_only"
    labels.mkdir(exist_ok=True)
    for name, frame in bundle.truth.items():
        frame.to_csv(labels / f"{name}.csv", index=False)
    (path / "manifest.json").write_text(json.dumps(bundle.metadata, indent=2), encoding="utf-8")
    logger.info("Saved %s tables to %s", len(bundle.tables), path)


def load_bundle(folder: str | Path) -> DatasetBundle:
    path = Path(folder)
    metadata = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    tables = {p.stem: read_csv(p) for p in sorted(path.glob("*.csv")) if p.stem in PRIMARY_KEYS}
    truth = {p.stem: read_csv(p) for p in sorted((path / "evaluation_only").glob("*.csv"))}
    if not tables:
        raise ValueError("Bundle contains no recognized tables")
    return DatasetBundle(tables, truth, metadata)
