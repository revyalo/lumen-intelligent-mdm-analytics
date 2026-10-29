"""Measured reproducible benchmarks; memory fields are table storage, not peak process RSS."""
import io
import json
import platform
from pathlib import Path
from time import perf_counter

import pandas as pd

from .analysis import analyze, observation_windows
from .intervals import coincidence_evidence, occupancy_segments, split_days, union_visits
from .synthetic import demo_fixture, generate_visits
from .validation import read_time_csv, validate_records


def run_benchmarks(output: str | Path, sizes: tuple[int, ...] = (100, 1000, 10000),
                   seeds: tuple[int, ...] = (42, 123)) -> dict:
    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=True)
    measurements = []
    for size in sizes:
        for seed in seeds:
            generated = generate_visits(size, seed)
            data = generated.to_csv(index=False).encode()
            start = perf_counter()
            frame = read_time_csv(io.BytesIO(data))
            loaded = perf_counter()
            check = validate_records(frame)
            validated = perf_counter()
            if check.has_errors:
                raise AssertionError("Generated valid benchmark failed validation")
            visits = split_days(union_visits(check.records))
            prepared = perf_counter()
            segments = occupancy_segments(visits)
            swept = perf_counter()
            evidence, comparisons = coincidence_evidence(visits, max_comparisons=2_000_000)
            ended = perf_counter()
            measurements.append({"rows": size, "seed": seed, "load_seconds": loaded-start,
                "validation_seconds": validated-loaded, "union_and_split_seconds": prepared-validated,
                "occupancy_seconds": swept-prepared, "coincidence_seconds": ended-swept,
                "total_measured_seconds": ended-start, "input_dataframe_bytes": int(frame.memory_usage(deep=True).sum()),
                "output_dataframe_bytes": sum(int(t.memory_usage(deep=True).sum()) for t in [visits, segments, evidence]),
                "candidate_interval_overlaps": comparisons, "qualifying_evidence_rows": len(evidence),
                "unique_pairs": len(set(zip(evidence.EmployeeA, evidence.EmployeeB))),
                "peak_people_in_one_resource": int(segments.People.max()) if len(segments) else 0,
                "occupied_resource_seconds": float(segments.loc[segments.People.gt(0), "Seconds"].sum()),
                "input_sha256": check.metadata["input_sha256"]})
            print(f"Operational benchmark: {size:,} rows, seed {seed}: {ended-start:.3f}s", flush=True)
    fixture = demo_fixture()
    demo = analyze(validate_records(fixture.records),
                   windows=observation_windows(["Atlas"], ["2026-09-30"], "08:00", "12:00"), capacities={"Atlas": 2})
    for key in ["employees", "unique_pairs", "occupied_resource_seconds", "person_seconds", "utilization",
                "peak_people_in_one_resource", "mean_stay_seconds", "median_stay_seconds"]:
        if demo.summary[key] != fixture.expected[key]:
            raise AssertionError(f"Independent demo expectation failed: {key}")
    if demo.tables["daily_summary"].OvercapacitySeconds.sum() != fixture.expected["overcapacity_seconds"]:
        raise AssertionError("Demo capacity check failed")
    peak_times = [[row.Start.strftime("%H:%M"), row.End.strftime("%H:%M")]
                  for row in demo.tables["peak_intervals"].itertuples(index=False)]
    if peak_times != fixture.expected["peak_intervals"]:
        raise AssertionError("Demo peak plateaus do not match expectations")
    pd.DataFrame(measurements).to_csv(destination/"performance.csv", index=False)
    manifest = {"python": platform.python_version(), "platform": platform.system(), "sizes": list(sizes),
                "seeds": list(seeds), "runs": len(measurements), "demo_expected_results": "PASS",
                "schedule": "Benchmarks use observed spans; availability/capacity are not inferred",
                "memory_measure": "DataFrame deep storage only; excludes Python objects, temporary allocations and peak process RSS",
                "limits": "One run per size/seed, local machine; no production capacity or hosted-CI claim"}
    (destination/"summary.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    (destination/"demo-check.json").write_text(json.dumps({"expected": fixture.expected, "actual": demo.summary,
                                                          "peak_intervals": peak_times}, indent=2)+"\n", encoding="utf-8")
    return manifest
