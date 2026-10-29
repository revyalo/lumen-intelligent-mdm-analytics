"""Append-only local review events and recomputable golden-record snapshots."""
import hashlib
import sqlite3
from pathlib import Path

import pandas as pd

from intelligent_mdm.cleaning import normalize


def fingerprint(frame: pd.DataFrame) -> str:
    ordered = frame.sort_values("record_id").reindex(sorted(frame.columns), axis=1)
    return hashlib.sha256(ordered.to_csv(index=False, date_format="%Y-%m-%dT%H:%M:%S").encode()).hexdigest()


class ReviewLedger:
    """Local trusted-user audit trail, not a production identity/access-control service."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT, dataset TEXT NOT NULL,
                left_id TEXT NOT NULL, right_id TEXT NOT NULL, decision TEXT NOT NULL,
                reviewer TEXT NOT NULL, reason TEXT NOT NULL, allow_conflict INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            )""")

    def record(self, frame: pd.DataFrame, left: str, right: str, decision: str,
               reviewer: str, reason: str, allow_conflict: bool = False) -> None:
        if decision not in {"accept", "reject", "revoke"}:
            raise ValueError("Decision must be accept, reject or revoke")
        ids = frame.record_id.astype(str)
        if ids.duplicated().any() or frame.record_id.isna().any():
            raise ValueError("Unique nonmissing record IDs required")
        if left == right or not {left, right} <= set(ids):
            raise ValueError("Select two distinct existing records")
        if not reviewer.strip() or not reason.strip():
            raise ValueError("Reviewer and decision reason are required")
        a, b = sorted([left, right])
        if decision == "accept" and not allow_conflict:
            clean, _ = normalize(frame)
            subset = clean[clean.record_id.astype(str).isin([a, b])]
            for key in ["tax_id", "sku"]:
                if key in subset and subset[key].dropna().nunique() > 1:
                    raise ValueError("Conflicting identity keys require an explicit override and reason")
        with sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO events(dataset,left_id,right_id,decision,reviewer,reason,allow_conflict) VALUES (?,?,?,?,?,?,?)",
                         (fingerprint(frame), a, b, decision, reviewer.strip(), reason.strip(), int(allow_conflict)))

    def history(self, frame: pd.DataFrame) -> pd.DataFrame:
        with sqlite3.connect(self.path) as conn:
            return pd.read_sql_query("SELECT * FROM events WHERE dataset=? ORDER BY event_id", conn,
                                     params=(fingerprint(frame),))

    def effective(self, frame: pd.DataFrame) -> pd.DataFrame:
        events = self.history(frame)
        return events.drop_duplicates(["left_id", "right_id"], keep="last")


def consolidate(frame: pd.DataFrame, ledger: ReviewLedger) -> dict[str, pd.DataFrame]:
    if not {"record_id", "name"} <= set(frame) or frame.record_id.isna().any() or frame.record_id.astype(str).duplicated().any():
        raise ValueError("Golden records require name and unique, nonmissing record_id")
    clean, _ = normalize(frame.reset_index(drop=True))
    clean["record_id"] = clean.record_id.astype(str)
    parent = {i: i for i in clean.record_id}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    blocked = []
    events = ledger.effective(frame)
    for event in events[events.decision.eq("accept")].itertuples():
        left, right = find(event.left_id), find(event.right_id)
        group = clean[clean.record_id.map(find).isin([left, right])]
        keys = [k for k in ["tax_id", "sku"] if k in group and group[k].dropna().nunique() > 1]
        if keys and not event.allow_conflict:
            blocked.append({"event_id": event.event_id, "reason": "Transitive conflict: "+", ".join(keys)})
            continue
        parent[right] = left
    priority = {"administration": 0, "catalogue": 0, "sales": 1, "purchasing": 2}
    clean["_priority"] = clean["source"].map(priority).fillna(3) if "source" in clean else 3
    clean["_updated"] = pd.to_datetime(clean.updated_at, errors="coerce") if "updated_at" in clean else pd.NaT
    golden, provenance, membership = [], [], []
    for _, group in clean.groupby(clean.record_id.map(find), sort=True):
        members = sorted(group.record_id)
        gid = "G-"+hashlib.sha256("|".join(members).encode()).hexdigest()[:12]
        row = {"golden_id": gid, "member_count": len(members)}
        group = group.sort_values(["_priority", "_updated", "record_id"], ascending=[True, False, True])
        for col in frame.columns:
            if col in {"record_id", "source"}:
                continue
            options = group[group[col].notna()]
            if options.empty:
                row[col] = None
                continue
            chosen = options.iloc[0]
            row[col] = chosen[col]
            provenance.append({"golden_id": gid, "field": col, "value": str(chosen[col]),
                               "source_record_id": chosen.record_id, "distinct_values": options[col].astype(str).nunique(),
                               "rule": "Source priority, latest update, then stable record_id"})
        golden.append(row)
        membership.extend({"record_id": rid, "golden_id": gid} for rid in members)
    return {"golden_records": pd.DataFrame(golden), "provenance": pd.DataFrame(provenance),
            "membership": pd.DataFrame(membership), "blocked": pd.DataFrame(blocked), "history": ledger.history(frame)}
