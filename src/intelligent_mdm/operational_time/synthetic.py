"""Original seeded resource visits; evaluation expectations never enter operational features."""
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class TimeFixture:
    records: pd.DataFrame
    invalid_records: pd.DataFrame
    identity_map: pd.DataFrame
    expected: dict
    metadata: dict


def demo_fixture(*, aliases: bool = False) -> TimeFixture:
    records = pd.DataFrame([
        ("Person 01", "08:15", "09:15"), ("Person 02", "08:45", "09:45"),
        ("Person 03", "09:00", "09:30"), ("Person 04", "11:00", "11:30"),
        ("Person 05", "11:10", "11:20"), ("Person 06", "11:10", "11:20"),
    ], columns=["Employee", "Start", "End"]).assign(Room="Atlas", Date="2026-09-30")
    mapping = pd.DataFrame([("Person 01 alias", "Person 01")], columns=["Alias", "Canonical"])
    if aliases:
        records.loc[len(records)] = ["Person 01 alias", "08:50", "09:10", "Atlas", "2026-09-30"]
    corrupt = pd.concat([records.iloc[:1], records.iloc[:1], pd.DataFrame([
        ("", "10:00", "10:30", "Atlas", "2026-09-30"),
        ("Person invalid", "bad", "10:00", "Atlas", "2026-09-30"),
        ("Person reversed", "12:00", "11:00", "Atlas", "2026-09-30"),
    ], columns=records.columns)], ignore_index=True)
    expected = {"scope": "Base demo, Atlas on 2026-09-30, availability 08:00–12:00, capacity 2",
                "employees": 6, "unique_pairs": 6, "occupied_resource_seconds": 7200,
                "person_seconds": 12000, "available_resource_seconds": 14400,
                "idle_resource_seconds": 7200, "utilization": .5, "peak_people_in_one_resource": 3,
                "peak_intervals": [["09:00", "09:15"], ["11:10", "11:20"]],
                "overcapacity_seconds": 1500, "ranking": "All six people tie with two distinct contacts",
                "mean_stay_seconds": 2000, "median_stay_seconds": 1800,
                "aliases_note": "With alias rows, base expectations apply only after the explicit map"}
    return TimeFixture(records, corrupt, mapping, expected,
                       {"generator": "original deterministic six-person fixture", "seed": None, "aliases": aliases})


def generate_visits(rows: int = 2000, seed: int = 42) -> pd.DataFrame:
    """Generate separated morning/afternoon visits, five rooms and multiple local dates."""
    if not isinstance(rows, int) or rows < 0:
        raise ValueError("rows must be a nonnegative integer")
    rng = np.random.default_rng(seed)
    employees = min(400, max(12, rows//20))
    origin = pd.Timestamp("2026-09-01T08:00:00")
    data = []
    for i in range(rows):
        day = i//(employees*2)
        person = (i//2) % employees
        shift = i % 2
        offset = day*86400 + shift*5*3600 + int(rng.integers(0, 120*60))
        start = origin + pd.Timedelta(offset, unit="s")
        end = start + pd.Timedelta(int(rng.integers(15*60, 90*60+1)), unit="s")
        data.append({"Employee": f"Person {person+1:04d}", "Room": f"Resource {(person+day)%5+1}",
                     "Start": start.isoformat(), "End": end.isoformat()})
    return pd.DataFrame(data, columns=["Employee", "Room", "Start", "End"])
