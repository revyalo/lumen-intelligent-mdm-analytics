"""Pure operational analytics, with explicit identity, observation and selection provenance."""
from dataclasses import dataclass
import hashlib
import math
from typing import Mapping

import pandas as pd

from .intervals import coincidence_evidence, cross_resource_conflicts, occupancy_segments, split_days, union_visits
from .validation import ValidationResult


@dataclass
class TimeAnalysis:
    tables: dict[str, pd.DataFrame]
    summary: dict
    metadata: dict


def observation_windows(rooms: list[str], dates: list[str], opening: str = "08:00",
                        closing: str = "18:00") -> pd.DataFrame:
    """Explicit daily availability, including resource-days with no visits."""
    return pd.DataFrame([{"Room": room, "Start": f"{day}T{opening}", "End": f"{day}T{closing}"}
                         for room in sorted(set(rooms)) for day in sorted(set(dates))],
                        columns=["Room", "Start", "End"])


def _windows(frame: pd.DataFrame | None) -> pd.DataFrame | None:
    if frame is None:
        return None
    if not {"Room", "Start", "End"} <= set(frame):
        raise ValueError("Observation windows require Room, Start, End")
    result = frame[["Room", "Start", "End"]].copy()
    for col in ["Start", "End"]:
        parsed = []
        for value in result[col]:
            stamp = pd.Timestamp(value)
            if pd.isna(stamp) or stamp.tzinfo is not None:
                raise ValueError("Observation windows require valid naive local timestamps")
            _ = stamp.value
            parsed.append(stamp)
        result[col] = pd.to_datetime(parsed)
    if result.Room.isna().any() or not result.Room.map(lambda x: isinstance(x, str) and bool(x.strip())).all():
        raise ValueError("Every window needs a nonempty Room")
    if (result.End <= result.Start).any():
        raise ValueError("Observation windows must have positive duration")
    result = result.sort_values(["Room", "Start", "End"]).reset_index(drop=True)
    for _, group in result.groupby("Room"):
        if (group.Start.iloc[1:].to_numpy() < group.End.iloc[:-1].to_numpy()).any():
            raise ValueError("Observation windows must not overlap")
    return result


def _identities(records: pd.DataFrame, mapping: pd.DataFrame | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = records.copy()
    columns = ["record_id", "ObservedEmployee", "Employee", "changed"]
    if mapping is None:
        lookup = {}
    else:
        if not {"Alias", "Canonical"} <= set(mapping):
            raise ValueError("Identity map requires Alias and Canonical")
        if mapping.Alias.duplicated().any():
            raise ValueError("Identity aliases must be unique")
        if not mapping[["Alias", "Canonical"]].map(lambda x: isinstance(x, str) and bool(x.strip())).all().all():
            raise ValueError("Identity labels must be nonempty text")
        lookup = dict(zip(mapping.Alias, mapping.Canonical))
        if any(value in lookup and lookup[value] != value for value in lookup.values()):
            raise ValueError("Identity chains/cycles are ambiguous; provide direct canonical targets")
    audit = out[["record_id", "Employee"]].rename(columns={"Employee": "ObservedEmployee"})
    out["Employee"] = out.Employee.map(lambda x: lookup.get(x, x))
    audit["Employee"] = out.Employee
    audit["changed"] = audit.ObservedEmployee.ne(audit.Employee)
    return out, audit.reindex(columns=columns)


def _clip(records: pd.DataFrame, windows: pd.DataFrame | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, evidence = [], []
    grouped = {} if windows is None else {room: group for room, group in windows.groupby("Room")}
    for row in records.to_dict("records"):
        if windows is None:
            rows.append(row)
            continue
        kept = 0.
        group = grouped.get(row["Room"])
        if group is not None:
            # Binary search excludes windows wholly before/after this visit.
            left = group.End.searchsorted(row["Start"], side="right")
            right = group.Start.searchsorted(row["End"], side="left")
            for window in group.iloc[left:right].itertuples(index=False):
                start, end = max(row["Start"], window.Start), min(row["End"], window.End)
                rows.append({**row, "Start": start, "End": end})
                kept += (end-start).total_seconds()
        original = (row["End"]-row["Start"]).total_seconds()
        evidence.append({"record_id": row["record_id"], "original_seconds": original,
                         "retained_seconds": kept, "excluded_seconds": original-kept})
    return pd.DataFrame(rows, columns=records.columns), pd.DataFrame(evidence,
        columns=["record_id", "original_seconds", "retained_seconds", "excluded_seconds"])


def hourly_occupancy(segments: pd.DataFrame, *, has_schedule: bool) -> pd.DataFrame:
    rows = []
    for row in segments.itertuples(index=False):
        start = row.Start
        while start < row.End:
            end = min(row.End, start.floor("h") + pd.Timedelta(1, unit="h"))
            seconds = (end-start).total_seconds()
            rows.append({"Room": row.Room, "Date": row.Date, "Hour": start.hour,
                         "ObservedSeconds": seconds, "OccupiedSeconds": seconds if row.People else 0.,
                         "PersonSeconds": seconds*row.People})
            start = end
    columns = ["Room", "Date", "Hour", "ObservedSeconds", "OccupiedSeconds", "PersonSeconds",
               "MeanPeople", "Utilization"]
    if not rows:
        return pd.DataFrame(columns=columns)
    result = pd.DataFrame(rows).groupby(["Room", "Date", "Hour"], as_index=False).sum()
    result["MeanPeople"] = result.PersonSeconds / result.ObservedSeconds
    result["Utilization"] = result.OccupiedSeconds / result.ObservedSeconds if has_schedule else float("nan")
    return result.reindex(columns=columns)


def analyze(validation: ValidationResult, *, windows: pd.DataFrame | None = None,
            capacities: Mapping[str, int] | None = None, identity_map: pd.DataFrame | None = None,
            allow_quarantined: bool = False, threshold_seconds: float = 60,
            max_comparisons: int = 1_000_000, selection: dict | None = None) -> TimeAnalysis:
    """Analyze a validated population; invalid-row exclusion requires explicit caller consent."""
    if validation.has_errors and not allow_quarantined:
        raise ValueError("Input contains validation errors; fix them or explicitly allow quarantined rows")
    if not math.isfinite(threshold_seconds) or threshold_seconds < 0:
        raise ValueError("Coincidence threshold must be finite and nonnegative")
    if not isinstance(max_comparisons, int) or max_comparisons < 1:
        raise ValueError("Comparison budget must be a positive integer")
    capacities = dict(capacities or {})
    if any(not isinstance(v, int) or isinstance(v, bool) or v < 1 for v in capacities.values()):
        raise ValueError("Capacities must be positive integers")
    schedule = _windows(windows)
    records, identities = _identities(validation.records, identity_map)
    if identity_map is not None and cross_resource_conflicts(records):
        raise ValueError("Identity map creates simultaneous presence in different resources; review the mapping")
    clipped, clipping = _clip(records, schedule)
    visits = union_visits(clipped)
    daily_visits = split_days(visits)
    daily_windows = split_days(schedule) if schedule is not None else None
    segments = occupancy_segments(daily_visits, daily_windows)
    evidence, comparisons = coincidence_evidence(daily_visits, threshold_seconds=threshold_seconds,
                                                 max_comparisons=max_comparisons)
    pair_columns = ["Room", "Date", "EmployeeA", "EmployeeB", "QualifyingSegments", "QualifyingSeconds", "LongestSeconds"]
    if evidence.empty:
        pairs = pd.DataFrame(columns=pair_columns)
    else:
        pairs = evidence.groupby(pair_columns[:4], as_index=False).agg(
            QualifyingSegments=("Seconds", "size"), QualifyingSeconds=("Seconds", "sum"), LongestSeconds=("Seconds", "max"))
    distinct_pairs = set(zip(evidence.EmployeeA, evidence.EmployeeB))
    neighbours = {name: set() for name in sorted(visits.Employee.unique())}
    for a, b in distinct_pairs:
        neighbours[a].add(b)
        neighbours[b].add(a)
    ranking = pd.DataFrame([{"Employee": employee, "DistinctPeople": len(people)}
                            for employee, people in neighbours.items()], columns=["Employee", "DistinctPeople"])
    if not ranking.empty:
        ranking["Rank"] = ranking.DistinctPeople.rank(method="min", ascending=False).astype(int)
        ranking = ranking.sort_values(["Rank", "Employee"]).reset_index(drop=True)
    else:
        ranking["Rank"] = pd.Series(dtype="int64")
    daily_rows = []
    peaks = []
    for (room, day), group in segments.groupby(["Room", "Date"], sort=True):
        occupied = float(group.loc[group.People.gt(0), "Seconds"].sum())
        available = float(group.Seconds.sum()) if schedule is not None else None
        peak = int(group.People.max())
        if peak:
            peaks.extend(group.loc[group.People.eq(peak)].to_dict("records"))
        capacity = capacities.get(room)
        daily_rows.append({"Room": room, "Date": day, "OccupiedSeconds": occupied,
                           "PersonSeconds": float((group.People*group.Seconds).sum()),
                           "ObservedSpanSeconds": float(group.Seconds.sum()), "AvailableSeconds": available,
                           "IdleSeconds": available-occupied if available is not None else None,
                           "Utilization": occupied/available if available else None,
                           "PeakPeople": peak, "Capacity": capacity,
                           "OvercapacitySeconds": float(group.loc[group.People.gt(capacity), "Seconds"].sum())
                           if capacity is not None else None})
    daily_columns = ["Room", "Date", "OccupiedSeconds", "PersonSeconds", "ObservedSpanSeconds", "AvailableSeconds",
                     "IdleSeconds", "Utilization", "PeakPeople", "Capacity", "OvercapacitySeconds"]
    daily = pd.DataFrame(daily_rows, columns=daily_columns)
    durations = (visits.End-visits.Start).dt.total_seconds() if not visits.empty else pd.Series(dtype=float)
    stays = visits.assign(Seconds=durations)
    employee_time = stays.groupby("Employee", as_index=False).agg(
        Seconds=("Seconds", "sum"), ConsolidatedVisits=("Seconds", "size"))
    occupied_total = float(daily.OccupiedSeconds.sum())
    available_total = float(daily.AvailableSeconds.sum()) if schedule is not None else None
    summary = {"employees": len(neighbours), "unique_pairs": len(distinct_pairs),
               "resource_day_pairs": len(pairs), "occupied_resource_seconds": occupied_total,
               "person_seconds": float(daily.PersonSeconds.sum()), "available_resource_seconds": available_total,
               "idle_resource_seconds": available_total-occupied_total if available_total is not None else None,
               "utilization": occupied_total/available_total if available_total else None,
               "peak_people_in_one_resource": int(daily.PeakPeople.max()) if not daily.empty else 0,
               "mean_stay_seconds": float(durations.mean()) if len(durations) else None,
               "median_stay_seconds": float(durations.median()) if len(durations) else None,
               "consolidated_visits": len(visits), "pair_comparisons": comparisons,
               "capacity_configured": bool(capacities)}
    metadata = {**validation.metadata, "selected_valid_rows": len(records),
                "quarantined_rows_explicitly_excluded": allow_quarantined and validation.has_errors,
                "selection": selection or {}, "threshold_seconds": threshold_seconds,
                "threshold_policy": "One continuous segment strictly above threshold in the same resource/local date",
                "pair_ranking_scope": "Distinct people across all selected resource-days; include zero-contact people",
                "stay_policy": "Unioned per-person/resource visits clipped to observation windows, before midnight split",
                "schedule_provided": schedule is not None, "capacities": capacities,
                "identity_map_sha256": hashlib.sha256(identity_map.to_csv(index=False).encode()).hexdigest()
                if identity_map is not None else None,
                "selection_effect": "Employee filters change occupancy to the selected population",
                "max_comparisons": max_comparisons, "algorithm": "union + endpoint sweep + active-interval pair enumeration"}
    tables = {"original_input": validation.original, "validated_selected_records": records,
              "validation_issues": validation.issues, "identity_audit": identities,
              "identity_map": identity_map.copy() if identity_map is not None else pd.DataFrame(columns=["Alias", "Canonical"]),
              "clipping_audit": clipping, "consolidated_visits": stays, "daily_visits": daily_visits,
              "occupancy": segments, "daily_summary": daily, "coincidence_evidence": evidence,
              "pairs": pairs, "ranking": ranking, "employee_time": employee_time,
              "peak_intervals": pd.DataFrame(peaks, columns=segments.columns),
              "hourly_occupancy": hourly_occupancy(segments, has_schedule=schedule is not None),
              "observation_windows": schedule if schedule is not None else pd.DataFrame(columns=["Room", "Start", "End"])}
    return TimeAnalysis(tables, summary, metadata)
