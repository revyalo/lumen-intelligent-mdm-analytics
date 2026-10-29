"""Command-line entry points for generation, evidence and measured experiments."""
import argparse
import json
from pathlib import Path

import pandas as pd

from .analysis import analyze, observation_windows
from .benchmarks import run_benchmarks
from .report import build_time_report
from .synthetic import demo_fixture, generate_visits
from .validation import read_time_csv, validate_records


def add_time_commands(subparsers: argparse._SubParsersAction) -> None:
    generate = subparsers.add_parser("time-generate", help="Generate original synthetic resource visits")
    generate.add_argument("--demo", action="store_true", help="Known-answer fixture, separate invalid rows and identity map")
    generate.add_argument("--rows", type=int, default=2000)
    generate.add_argument("--seed", type=int, default=42)
    generate.add_argument("--output", type=Path, default=Path("runtime/operational-demo"))
    analyze_parser = subparsers.add_parser("time-analyze", help="Analyze a visit CSV and export operational evidence")
    analyze_parser.add_argument("--input", type=Path, required=True)
    analyze_parser.add_argument("--output", type=Path, default=Path("runtime/operational-report.zip"))
    analyze_parser.add_argument("--assumed-date", default="2026-09-30")
    analyze_parser.add_argument("--opening", help="Daily availability HH:MM[:SS]; supply together with --closing")
    analyze_parser.add_argument("--closing")
    analyze_parser.add_argument("--start-date", help="Availability begins on this ISO date; defaults to first visit")
    analyze_parser.add_argument("--end-date", help="Availability ends on this ISO date; defaults to last visit")
    analyze_parser.add_argument("--capacity", type=int, help="Explicit same capacity for every selected resource")
    analyze_parser.add_argument("--identity-map", type=Path)
    analyze_parser.add_argument("--allow-quarantined", action="store_true")
    benchmark = subparsers.add_parser("time-benchmarks", help="Measure temporal algorithms on original seeded records")
    benchmark.add_argument("--sizes", nargs="+", type=int, default=[100, 1000, 10000])
    benchmark.add_argument("--seeds", nargs="+", type=int, default=[42, 123])
    benchmark.add_argument("--output", type=Path, default=Path("runtime/operational-benchmarks"))


def run_time_command(args: argparse.Namespace) -> None:
    if args.command == "time-generate":
        args.output.mkdir(parents=True, exist_ok=True)
        if args.demo:
            fixture = demo_fixture()
            fixture.records.to_csv(args.output/"visits.csv", index=False)
            fixture.invalid_records.to_csv(args.output/"invalid_cases.csv", index=False)
            demo_fixture(aliases=True).records.to_csv(args.output/"identity_visits.csv", index=False)
            fixture.identity_map.to_csv(args.output/"identity_map.csv", index=False)
            truth = args.output/"evaluation_only"
            truth.mkdir(exist_ok=True)
            (truth/"expected.json").write_text(json.dumps(fixture.expected, indent=2)+"\n", encoding="utf-8")
        else:
            generate_visits(args.rows, args.seed).to_csv(args.output/"visits.csv", index=False)
        print(f"Operational data: {args.output}")
    elif args.command == "time-benchmarks":
        run_benchmarks(args.output, tuple(args.sizes), tuple(args.seeds))
    elif args.command == "time-analyze":
        check = validate_records(read_time_csv(args.input.read_bytes()), assumed_date=args.assumed_date)
        if bool(args.opening) != bool(args.closing):
            raise ValueError("Supply both --opening and --closing")
        rooms = sorted(check.records.Room.unique().tolist())
        windows = None
        if args.opening:
            if check.records.empty and not (args.start_date and args.end_date):
                raise ValueError("Availability for empty data needs --start-date and --end-date")
            first = args.start_date or str(check.records.Start.min().date())
            last = args.end_date or str((check.records.End.max()-pd.Timedelta(1, unit="ns")).date())
            if pd.Timestamp(first) > pd.Timestamp(last):
                raise ValueError("Availability start date must not exceed end date")
            if not rooms:
                raise ValueError("Availability for empty data also needs explicit resource labels; use the Python API")
            days = pd.date_range(first, last).strftime("%Y-%m-%d").tolist()
            windows = observation_windows(rooms, days, args.opening, args.closing)
        mapping = read_time_csv(args.identity_map.read_bytes()) if args.identity_map else None
        capacities = {room: args.capacity for room in rooms} if args.capacity is not None else None
        output = analyze(check, windows=windows, capacities=capacities, identity_map=mapping,
                         allow_quarantined=args.allow_quarantined, selection={"source": "CLI", "scope": "Entire supplied CSV"})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(build_time_report(output))
        print(json.dumps(output.summary, indent=2, allow_nan=False))
        print(f"Operational evidence: {args.output}")
