import io
from itertools import combinations

import numpy as np
import pandas as pd
import pytest

from intelligent_mdm.operational_time import analyze, observation_windows, read_time_csv, validate_records


def frame(rows):
    return pd.DataFrame(rows, columns=["Employee", "Start", "End"])


def result(rows, **kwargs):
    return analyze(validate_records(frame(rows)), **kwargs)


def test_union_and_three_person_peak():
    out = result([("P1", "08:00", "10:00"), ("P2", "09:00", "11:00"), ("P3", "09:30", "10:30")])
    assert out.summary["occupied_resource_seconds"] == 3*3600
    assert out.summary["peak_people_in_one_resource"] == 3
    assert out.summary["unique_pairs"] == 3
    assert out.tables["ranking"].DistinctPeople.tolist() == [2, 2, 2]
    assert out.tables["ranking"].Rank.tolist() == [1, 1, 1]
    assert len(out.tables["peak_intervals"]) == 1


@pytest.mark.parametrize("rows,employees,pairs,peak,seconds", [
    ([], 0, 0, 0, 0),
    ([("P1", "08:00", "09:00")], 1, 0, 1, 3600),
    ([("P1", "08:00", "09:00"), ("P2", "10:00", "11:00")], 2, 0, 1, 7200),
    ([("P1", "08:00", "09:00"), ("P2", "09:00", "10:00")], 2, 0, 1, 7200),
    ([("P1", "08:00", "12:00"), ("P2", "09:00", "10:00")], 2, 1, 2, 14400),
])
def test_basic_cases(rows, employees, pairs, peak, seconds):
    summary = result(rows).summary
    assert (summary["employees"], summary["unique_pairs"], summary["peak_people_in_one_resource"],
            summary["occupied_resource_seconds"]) == (employees, pairs, peak, seconds)
    assert summary["utilization"] is None
    assert summary["idle_resource_seconds"] is None


@pytest.mark.parametrize("end,pairs", [("08:01:00", 0), ("08:01:01", 1)])
def test_strict_threshold(end, pairs):
    assert result([("P1", "08:00:00", "08:05:00"), ("P2", "08:00:00", end)]).summary["unique_pairs"] == pairs


def test_short_fragments_do_not_accumulate_into_a_qualifying_contact():
    out = result([("P1", "08:00:00", "08:10:00"), ("P2", "08:00:00", "08:00:40"),
                  ("P2", "08:02:00", "08:02:40")])
    assert out.summary["unique_pairs"] == 0


def test_repeated_pairs_have_multiple_evidence_segments_and_one_neighbour():
    out = result([("P1", "08:00", "09:00"), ("P2", "08:15", "08:30"),
                  ("P2", "08:40", "08:50")])
    assert out.summary["unique_pairs"] == 1
    assert len(out.tables["coincidence_evidence"]) == 2
    assert out.tables["pairs"].QualifyingSegments.item() == 2
    assert out.tables["ranking"].DistinctPeople.tolist() == [1, 1]


def test_duplicates_self_overlaps_and_adjacency_are_unioned_with_lineage():
    data = frame([("P1", "08:00", "09:00"), ("P1", "08:00", "09:00"),
                  ("P1", "08:30", "10:00"), ("P1", "10:00", "11:00"), ("P2", "09:30", "10:30")])
    check = validate_records(data)
    assert {"duplicate_interval", "self_overlap"} <= set(check.issues.code)
    out = analyze(check)
    assert out.summary["consolidated_visits"] == 2
    assert out.summary["peak_people_in_one_resource"] == 2
    assert out.tables["consolidated_visits"].iloc[0].record_ids.count("|") == 3
    assert out.tables["coincidence_evidence"].Seconds.item() == 3600


def test_multiple_peak_plateaus_are_all_returned():
    out = result([("P1", "08:00", "12:00"), ("P2", "09:00", "09:30"), ("P3", "10:00", "10:30")])
    assert len(out.tables["peak_intervals"]) == 2
    assert out.tables["peak_intervals"].Seconds.tolist() == [1800, 1800]


@pytest.mark.parametrize("rows,code", [
    ([("", "08:00", "09:00")], "missing_identity"),
    ([(None, "08:00", "09:00")], "missing_identity"),
    ([("P1", "25:00", "26:00")], "invalid_time"),
    ([("P1", "8:00", "09:00")], "invalid_time"),
    ([("P1", None, "09:00")], "invalid_time"),
    ([("P1", "08:00", "08:00")], "nonpositive_duration"),
    ([("P1", "23:00", "01:00")], "nonpositive_duration"),
    ([("P1", "08:00", "09:00:00")], "inconsistent_format"),
    ([("P1", "2026-09-30T08:00:00Z", "2026-09-30T09:00:00Z")], "invalid_time"),
])
def test_invalid_inputs_are_explicit(rows, code):
    check = validate_records(frame(rows))
    assert check.has_errors
    assert code in set(check.issues.code)
    with pytest.raises(ValueError, match="validation errors"):
        analyze(check)


def test_missing_schema():
    check = validate_records(pd.DataFrame({"Employee": ["P1"]}))
    assert check.has_errors and check.records.empty


def test_quarantine_requires_explicit_opt_in_and_exports_original():
    check = validate_records(frame([("P1", "08:00", "09:00"), ("P2", "bad", "10:00")]))
    out = analyze(check, allow_quarantined=True)
    assert out.summary["employees"] == 1
    assert len(out.tables["original_input"]) == 2
    assert out.metadata["quarantined_rows_explicitly_excluded"]


def test_csv_preserves_na_identity_and_rejects_duplicate_headers():
    data = read_time_csv(b'Employee,Start,End\nNA,08:00,09:00\n')
    assert not validate_records(data).has_errors
    with pytest.raises(ValueError, match="Duplicate"):
        read_time_csv(io.BytesIO(b'Employee,Start,End,End\nP1,08:00,09:00,10:00'))


def test_mixed_row_formats_not_silently_coerced():
    check = validate_records(frame([("P1", "08:00", "09:00"), ("P2", "08:00:00", "09:00:00")]))
    assert check.has_errors and check.records.empty


def test_schedule_clipping_idle_capacity_and_weighted_hourly_mean():
    windows = observation_windows(["Shared resource"], ["2026-09-30"], "08:00", "10:00")
    out = result([("P1", "07:00", "08:30"), ("P2", "08:15", "08:45"), ("P3", "11:00", "12:00")],
                 windows=windows, capacities={"Shared resource": 1})
    assert out.summary["occupied_resource_seconds"] == 2700
    assert out.summary["available_resource_seconds"] == 7200
    assert out.summary["idle_resource_seconds"] == 4500
    assert out.summary["utilization"] == .375
    assert out.tables["daily_summary"].OvercapacitySeconds.item() == 900
    assert out.tables["clipping_audit"].excluded_seconds.sum() == 7200
    assert out.tables["hourly_occupancy"].MeanPeople.tolist() == [1., 0.]
    assert out.summary["employees"] == 2


def test_zero_visit_resource_days_and_lunch_closure():
    check = validate_records(frame([]))
    windows = pd.DataFrame([("R", "2026-09-30T08:00", "2026-09-30T09:00"),
                            ("R", "2026-09-30T10:00", "2026-09-30T11:00")], columns=["Room", "Start", "End"])
    out = analyze(check, windows=windows)
    assert out.summary["available_resource_seconds"] == 7200
    assert out.summary["idle_resource_seconds"] == 7200
    assert out.summary["utilization"] == 0
    assert out.tables["peak_intervals"].empty
    assert len(out.tables["occupancy"]) == 2


def test_overlapping_windows_and_bad_capacities_rejected():
    windows = observation_windows(["R"], ["2026-09-30"])
    with pytest.raises(ValueError, match="overlap"):
        result([], windows=pd.concat([windows, windows]))
    for value in [0, -1, 1.5, True]:
        with pytest.raises(ValueError, match="positive integers"):
            result([], capacities={"R": value})


def test_rooms_do_not_create_cross_room_contacts_or_global_peak():
    data = frame([("P1", "08:00", "09:00"), ("P2", "08:00", "09:00")]).assign(Room=["A", "B"])
    out = analyze(validate_records(data), windows=observation_windows(["A", "B"], ["2026-09-30"], "08:00", "10:00"))
    assert out.summary["unique_pairs"] == 0
    assert out.summary["peak_people_in_one_resource"] == 1
    assert out.summary["occupied_resource_seconds"] == 7200
    assert out.summary["utilization"] == .5


def test_date_scope_pairs_and_midnight_splitting():
    data = frame([("P1", "2026-09-30T23:59:00", "2026-10-01T00:02:00"),
                  ("P2", "2026-09-30T23:59:00", "2026-10-01T00:02:00")])
    out = analyze(validate_records(data))
    assert out.summary["occupied_resource_seconds"] == 180
    assert out.summary["unique_pairs"] == 1
    assert out.tables["pairs"].Date.tolist() == ["2026-10-01"]
    assert len(out.tables["daily_summary"]) == 2
    assert out.summary["mean_stay_seconds"] == 180


def test_explicit_dates_and_reference_date():
    data = frame([("P1", "08:00", "09:00"), ("P2", "08:00", "09:00")]).assign(Date=["2026-09-29", "2026-09-30"])
    out = analyze(validate_records(data))
    assert out.summary["unique_pairs"] == 0
    assert str(validate_records(frame([("P1", "08:00", "09:00")]), assumed_date="2026-01-02").records.Start.iloc[0].date()) == "2026-01-02"


def test_exact_identity_map_changes_metrics_and_retains_trace():
    check = validate_records(frame([("P1", "08:00", "09:00"), ("P1 alias", "08:15", "08:45")]))
    before = analyze(check)
    mapping = pd.DataFrame([("P1 alias", "P1")], columns=["Alias", "Canonical"])
    after = analyze(check, identity_map=mapping)
    assert before.summary["employees"] == 2 and after.summary["employees"] == 1
    assert after.summary["unique_pairs"] == 0
    assert after.tables["identity_audit"].changed.sum() == 1
    assert after.tables["identity_map"].equals(mapping)
    with pytest.raises(ValueError, match="unique"):
        analyze(check, identity_map=pd.concat([mapping, mapping]))
    chain = pd.DataFrame([("P1 alias", "P1"), ("P1", "P2")], columns=mapping.columns)
    with pytest.raises(ValueError, match="chains"):
        analyze(check, identity_map=chain)


def test_explicit_comparison_budget():
    with pytest.raises(ValueError, match="budget"):
        result([(name, "08:00", "09:00") for name in ["P1", "P2", "P3"]], max_comparisons=1)


@pytest.mark.parametrize("seed", range(12))
def test_generated_small_cases_match_independent_second_grid_reference(seed):
    rng = np.random.default_rng(seed)
    rows = []
    origin = pd.Timestamp("2026-09-30T08:00:00")
    active = {second: set() for second in range(30)}
    for _ in range(18):
        employee = f"P{rng.integers(0, 5)}"
        start = int(rng.integers(0, 25))
        end = int(rng.integers(start+1, 31))
        rows.append((employee, (origin+pd.Timedelta(start, unit="s")).isoformat(),
                     (origin+pd.Timedelta(end, unit="s")).isoformat()))
        for second in range(start, end):
            active[second].add(employee)
    expected_pairs = set()
    for a, b in combinations(sorted(set.union(*active.values())), 2):
        longest = current = 0
        for second in range(30):
            current = current+1 if {a, b} <= active[second] else 0
            longest = max(longest, current)
        if longest > 2:
            expected_pairs.add((a, b))
    out = result(rows, threshold_seconds=2)
    actual = set(zip(out.tables["pairs"].EmployeeA, out.tables["pairs"].EmployeeB))
    assert actual == expected_pairs
    assert out.summary["occupied_resource_seconds"] == sum(bool(people) for people in active.values())
    assert out.summary["person_seconds"] == sum(len(people) for people in active.values())
    assert out.summary["peak_people_in_one_resource"] == max(map(len, active.values()))
    reordered = result(list(reversed(rows)) + rows[:2], threshold_seconds=2)
    assert reordered.summary == out.summary


def test_original_synthetic_demo_has_independent_known_answers():
    from intelligent_mdm.operational_time.synthetic import demo_fixture, generate_visits
    from intelligent_mdm.operational_time.benchmarks import run_benchmarks
    fixture = demo_fixture()
    out = analyze(validate_records(fixture.records),
                  windows=observation_windows(["Atlas"], ["2026-09-30"], "08:00", "12:00"), capacities={"Atlas": 2})
    for key in ["employees", "unique_pairs", "occupied_resource_seconds", "person_seconds", "utilization",
                "mean_stay_seconds", "median_stay_seconds"]:
        assert out.summary[key] == fixture.expected[key]
    assert out.tables["ranking"].DistinctPeople.eq(2).all()
    assert out.tables["ranking"].Rank.eq(1).all()
    assert out.tables["daily_summary"].OvercapacitySeconds.item() == 1500
    pd.testing.assert_frame_equal(generate_visits(120, 42), generate_visits(120, 42))
    assert not generate_visits(120, 42).equals(generate_visits(120, 123))
    assert not validate_records(generate_visits(120, 42)).has_errors
    assert callable(run_benchmarks)


def test_operational_evidence_export_preserves_input_and_computed_tables():
    import json
    import zipfile
    from intelligent_mdm.operational_time.report import build_time_report
    from intelligent_mdm.operational_time.synthetic import demo_fixture
    data = demo_fixture().records
    out = analyze(validate_records(data))
    first = build_time_report(out)
    assert first == build_time_report(out)
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert archive.testzip() is None
        assert {"report.html", "report.json", "report.md", "original_input.csv", "identity_audit.csv",
                "coincidence_evidence.csv", "observation_windows.csv", "clipping_audit.csv"} <= set(archive.namelist())
        assert json.loads(archive.read("report.json"))["summary"] == out.summary
        pd.testing.assert_frame_equal(pd.read_csv(archive.open("original_input.csv")), data)
        assert 'resource' in archive.read("report.html").decode()


def test_full_timestamp_date_means_start_date_not_end_date():
    data = frame([("P1", "2026-09-30T23:30", "2026-10-01T00:30")]).assign(Date="2026-09-30")
    assert not validate_records(data).has_errors


def test_shared_report_archive_rejects_unsafe_members():
    from intelligent_mdm.reporting.archive import package_evidence
    with pytest.raises(ValueError, match="safe relative"):
        package_evidence({"../outside.txt": "x"}, {})


def test_simultaneous_cross_resource_presence_is_quarantined_not_inferred():
    data = frame([("P1", "08:00", "09:00"), ("P1", "08:30", "09:30"),
                  ("P2", "10:00", "11:00")]).assign(Room=["A", "B", "A"])
    check = validate_records(data)
    assert check.has_errors and len(check.records) == 1
    assert check.issues.code.eq("cross_resource_overlap").sum() == 2
    out = analyze(check, allow_quarantined=True)
    assert out.summary["employees"] == 1
    data.Employee = ["P1", "alias", "P2"]
    mapping = pd.DataFrame([("alias", "P1")], columns=["Alias", "Canonical"])
    with pytest.raises(ValueError, match="different resources"):
        analyze(validate_records(data), identity_map=mapping)


def test_date_filter_clips_cross_midnight_presence_and_retains_full_original():
    from dashboard.operational import select_population
    check = validate_records(frame([("P1", "2026-09-30T23:30", "2026-10-01T00:30")]))
    selected = select_population(check, ["Shared resource"], ["P1"], "2026-10-01", "2026-10-01")
    out = analyze(selected)
    assert out.summary["occupied_resource_seconds"] == 1800
    assert out.tables["original_input"].Start.iloc[0] == "2026-09-30T23:30"


def test_operational_cli_generates_and_analyzes_without_commercial_bundle(tmp_path, monkeypatch, capsys):
    import sys
    import zipfile
    import json
    from intelligent_mdm.cli import main
    folder = tmp_path/"visits"
    monkeypatch.setattr(sys, "argv", ["intelligent-mdm", "time-generate", "--demo", "--output", str(folder)])
    main()
    target = tmp_path/"evidence.zip"
    monkeypatch.setattr(sys, "argv", ["intelligent-mdm", "time-analyze", "--input", str(folder/"visits.csv"),
                                     "--opening", "08:00", "--closing", "12:00", "--capacity", "2", "--output", str(target)])
    main()
    with zipfile.ZipFile(target) as archive:
        assert json.loads(archive.read("report.json"))["summary"]["utilization"] == .5
    assert (folder/"evaluation_only"/"expected.json").is_file()
    assert 'Operational evidence' in capsys.readouterr().out
