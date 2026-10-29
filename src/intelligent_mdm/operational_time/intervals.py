"""Interval unions, temporal event sweeps and output-sensitive pair evidence."""
from collections import defaultdict
import heapq

import pandas as pd

VISIT_COLUMNS = ["Employee", "Room", "Start", "End", "record_ids"]
SEGMENT_COLUMNS = ["Room", "Date", "Start", "End", "People", "Seconds"]
EVIDENCE_COLUMNS = ["Room", "Date", "EmployeeA", "EmployeeB", "Start", "End", "Seconds", "record_ids_a", "record_ids_b"]


def union_visits(records: pd.DataFrame) -> pd.DataFrame:
    """Union overlapping/adjacent visits for each exact identity/resource; retain all source IDs."""
    result = []
    for (employee, room), group in records.groupby(["Employee", "Room"], sort=True):
        current = None
        ids: set[str] = set()
        for row in group.sort_values(["Start", "End", "record_id"]).itertuples(index=False):
            if current is not None and row.Start > current[1]:
                result.append([employee, room, *current, "|".join(sorted(ids))])
                current, ids = None, set()
            if current is None:
                current = [row.Start, row.End]
            else:
                current[1] = max(current[1], row.End)
            ids.add(row.record_id)
        if current is not None:
            result.append([employee, room, *current, "|".join(sorted(ids))])
    return pd.DataFrame(result, columns=VISIT_COLUMNS)


def split_days(frame: pd.DataFrame) -> pd.DataFrame:
    """Split half-open visits/windows on naive local midnight without zero-duration fragments."""
    rows = []
    for row in frame.to_dict("records"):
        start, end = row["Start"], row["End"]
        while start < end:
            stop = min(end, start.normalize() + pd.Timedelta(1, unit="D"))
            rows.append({**row, "Start": start, "End": stop, "Date": str(start.date())})
            start = stop
    return pd.DataFrame(rows, columns=[c for c in frame.columns if c != "Date"] + ["Date"])


def occupancy_segments(visits: pd.DataFrame, windows: pd.DataFrame | None = None) -> pd.DataFrame:
    """Sweep summed endpoint deltas; visits must already be unioned per identity/resource."""
    groups = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for row in visits.itertuples(index=False):
        events = groups[(row.Room, row.Date)]
        events[row.Start][0] += 1
        events[row.End][0] -= 1
    if windows is not None:
        for row in windows.itertuples(index=False):
            events = groups[(row.Room, row.Date)]
            events[row.Start][1] += 1
            events[row.End][1] -= 1
    rows = []
    for (room, day), events in sorted(groups.items()):
        people, available = 0, 0
        times = sorted(events)
        for i, start in enumerate(times[:-1]):
            delta, opening = events[start]
            people += delta
            available += opening
            end = times[i+1]
            if windows is not None and not available:
                continue
            seconds = (end-start).total_seconds()
            if rows and rows[-1][:2] == [room, day] and rows[-1][3] == start and rows[-1][4] == people:
                rows[-1][3] = end
                rows[-1][5] += seconds
            else:
                rows.append([room, day, start, end, people, seconds])
    return pd.DataFrame(rows, columns=SEGMENT_COLUMNS)


def coincidence_evidence(visits: pd.DataFrame, *, threshold_seconds: float = 60,
                         max_comparisons: int = 1_000_000) -> tuple[pd.DataFrame, int]:
    """Enumerate actual intersecting visit candidates, with an explicit work/output budget."""
    rows, comparisons = [], 0
    for (room, day), group in visits.groupby(["Room", "Date"], sort=True):
        active, ending = {}, []
        for index, row in enumerate(group.sort_values(["Start", "End", "Employee"]).itertuples(index=False)):
            while ending and ending[0][0] <= row.Start:
                _, old = heapq.heappop(ending)
                active.pop(old)
            for other in active.values():
                if other.Employee == row.Employee:
                    raise ValueError("Pair sweep requires unioned per-person intervals")
                comparisons += 1
                if comparisons > max_comparisons:
                    raise ValueError("Coincidence comparison budget exceeded; reduce date/resource/population scope")
                start, end = max(other.Start, row.Start), min(other.End, row.End)
                seconds = (end-start).total_seconds()
                if seconds > threshold_seconds:
                    a, b = sorted([other, row], key=lambda r: r.Employee)
                    rows.append([room, day, a.Employee, b.Employee, start, end, seconds, a.record_ids, b.record_ids])
            active[index] = row
            heapq.heappush(ending, (row.End, index))
    return pd.DataFrame(rows, columns=EVIDENCE_COLUMNS), comparisons


def cross_resource_conflicts(records: pd.DataFrame) -> set[str]:
    """Find consolidated same-person stays intersecting another resource, in O(n log n)."""
    conflicts: set[str] = set()
    merged = union_visits(records)
    for _, group in merged.groupby("Employee", sort=True):
        visits = list(group.sort_values(["Start", "End", "Room"]).itertuples(index=False))
        furthest = None
        for i, row in enumerate(visits):
            # Same-resource visits are disjoint after union; any remaining overlap crosses resources.
            if (furthest is not None and row.Start < furthest) or (i+1 < len(visits) and row.End > visits[i+1].Start):
                conflicts.update(row.record_ids.split("|"))
            furthest = max(furthest, row.End) if furthest is not None else row.End
    return conflicts
