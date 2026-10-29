"""Explicit temporal input contract; ambiguous records are quarantined, never repaired."""
from dataclasses import dataclass
from datetime import date
import hashlib
import io
import re
from typing import BinaryIO, TextIO

import pandas as pd

RECORD_COLUMNS = ["record_id", "Employee", "Room", "Start", "End"]
ISSUE_COLUMNS = ["record_id", "severity", "code", "detail"]
PATTERNS = {
    "clock_minutes": r"\d{2}:\d{2}",
    "clock_seconds": r"\d{2}:\d{2}:\d{2}",
    "iso_minutes": r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}",
    "iso_seconds": r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
    "space_minutes": r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}",
    "space_seconds": r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
}


@dataclass
class ValidationResult:
    original: pd.DataFrame
    records: pd.DataFrame
    issues: pd.DataFrame
    metadata: dict

    @property
    def has_errors(self) -> bool:
        return bool(self.issues.severity.eq("error").any())


def read_time_csv(source: bytes | BinaryIO | TextIO) -> pd.DataFrame:
    """Read UTF-8 values literally, preserving names such as 'NA' and header duplicates."""
    import csv

    content = source if isinstance(source, bytes) else source.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    header = next(csv.reader(io.StringIO(content)), [])
    if len(header) != len(set(header)):
        raise ValueError("Duplicate CSV column names")
    if not header:
        raise ValueError("CSV has no header")
    try:
        return pd.read_csv(io.StringIO(content), dtype=str, keep_default_na=False)
    except (ValueError, pd.errors.ParserError) as exc:
        raise ValueError(f"Unable to parse time CSV: {exc}") from exc


def validate_records(frame: pd.DataFrame, *, assumed_date: str = "2026-09-30") -> ValidationResult:
    """Validate strict local-clock values; return valid rows plus complete issue evidence."""
    reference = date.fromisoformat(assumed_date)
    raw = frame.copy(deep=True).reset_index(drop=True)
    issues: list[dict] = []

    def issue(rid: str, severity: str, code: str, detail: str) -> None:
        issues.append(dict(record_id=rid, severity=severity, code=code, detail=detail))

    digest = hashlib.sha256(raw.to_csv(index=False).encode()).hexdigest()
    metadata = {"input_sha256": digest, "input_rows": len(raw), "assumed_date": str(reference),
                "timezone_policy": "Naive local clock only; timezone-aware/DST input unsupported",
                "interval_policy": "[Start, End)", "default_room": "Shared resource"}
    missing = {"Employee", "Start", "End"} - set(raw)
    if missing or raw.columns.duplicated().any():
        issue("", "error", "schema", f"Missing required columns: {sorted(missing)}; headers must be unique")
        return ValidationResult(raw, pd.DataFrame(columns=RECORD_COLUMNS), pd.DataFrame(issues), metadata)
    signatures = set()
    rows = []
    for i, row in raw.iterrows():
        rid = f"row_{i+1:07d}"
        employee, room = row.Employee, row.get("Room", "Shared resource")
        invalid = False
        for field, value in [("Employee", employee), ("Room", room)]:
            if not isinstance(value, str) or not value.strip():
                issue(rid, "error", "missing_identity", f"{field} must be nonempty text")
                invalid = True
            elif value != value.strip():
                issue(rid, "warning", "identity_whitespace", f"{field} has surrounding whitespace; preserved exactly")
        signature = []
        timestamps = []
        for field in ["Start", "End"]:
            value = row[field]
            fmt = next((name for name, pattern in PATTERNS.items()
                        if isinstance(value, str) and re.fullmatch(pattern, value)), None)
            if fmt is None:
                issue(rid, "error", "invalid_time", f"{field} requires a supported strict clock or naive ISO format")
                invalid = True
                continue
            signature.append(fmt)
            try:
                if fmt.startswith("clock"):
                    day = row.get("Date", str(reference))
                    if not isinstance(day, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
                        raise ValueError("Date must be YYYY-MM-DD")
                    date.fromisoformat(day)
                    timestamp = pd.Timestamp(f"{day}T{value}")
                else:
                    timestamp = pd.Timestamp(value)
                    if field == "Start" and "Date" in raw and str(row.Date) != str(timestamp.date()):
                        raise ValueError("Date contradicts timestamp date")
                # Bound to ns range used by the sweep and strict second precision.
                _ = timestamp.value
                timestamps.append(timestamp)
            except (ValueError, TypeError, OverflowError) as exc:
                issue(rid, "error", "invalid_time", f"{field}: {exc}")
                invalid = True
        if len(signature) == 2:
            signatures.update(signature)
            if signature[0] != signature[1]:
                issue(rid, "error", "inconsistent_format", "Start and End must use the same format")
                invalid = True
        if len(timestamps) == 2 and timestamps[1] <= timestamps[0]:
            issue(rid, "error", "nonpositive_duration", "End must be after Start; overnight is never inferred")
            invalid = True
        if not invalid and len(timestamps) == 2:
            rows.append(dict(record_id=rid, Employee=employee, Room=room, Start=timestamps[0], End=timestamps[1]))
    if len(signatures) > 1:
        for row in rows:
            issue(row["record_id"], "error", "inconsistent_format", "Use one time format throughout the file")
        rows = []
    records = pd.DataFrame(rows, columns=RECORD_COLUMNS)
    if not records.empty:
        duplicate = records.duplicated(["Employee", "Room", "Start", "End"], keep="first")
        for rid in records.loc[duplicate, "record_id"]:
            issue(rid, "warning", "duplicate_interval", "Repeated interval; analysis unions it with source lineage")
        for _, group in records.groupby(["Employee", "Room"], sort=True):
            previous_end = None
            for row in group.sort_values(["Start", "End", "record_id"]).itertuples(index=False):
                if previous_end is not None and row.Start < previous_end:
                    issue(row.record_id, "warning", "self_overlap", "Same person's intervals overlap; union required")
                previous_end = max(previous_end, row.End) if previous_end is not None else row.End
    from .intervals import cross_resource_conflicts
    conflicting = cross_resource_conflicts(records)
    for rid in sorted(conflicting):
        issue(rid, "error", "cross_resource_overlap", "Consolidated stay overlaps the same identity in another resource")
    records = records.loc[~records.record_id.isin(conflicting)].reset_index(drop=True)
    metadata.update(valid_rows=len(records), quarantined_rows=len(raw)-len(records), formats=sorted(signatures))
    return ValidationResult(raw, records, pd.DataFrame(issues, columns=ISSUE_COLUMNS), metadata)
