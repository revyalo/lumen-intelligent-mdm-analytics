import argparse
import logging
from pathlib import Path

from intelligent_mdm.ingestion import generate, load_bundle, save_bundle, validate_bundle


def main():
    parser = argparse.ArgumentParser(description="Intelligent MDM & Analytics — reproducible local lab")
    parser.add_argument("--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="Generate an original synthetic relational bundle")
    gen.add_argument("--size", choices=["demo", "large"], default="demo")
    gen.add_argument("--seed", type=int, default=42)
    gen.add_argument("--output", type=Path, default=Path("data/synthetic/demo"))
    exp = sub.add_parser("experiments", help="Run quality, matching, clustering and anomaly experiments")
    exp.add_argument("--output", type=Path, default=Path("docs/experiments"))
    exp.add_argument("--scales", nargs="+", choices=["demo", "large"], default=["demo", "large"])
    exp.add_argument("--seeds", nargs="+", type=int, default=[42, 123])
    exp.add_argument("--semantic-model", default=None)
    report = sub.add_parser("report", help="Build an evidence ZIP with HTML/JSON/CSV/PNG")
    report.add_argument("--input", type=Path)
    report.add_argument("--size", choices=["demo", "large"], default="demo")
    report.add_argument("--seed", type=int, default=42)
    report.add_argument("--table", default="customer_sources")
    report.add_argument("--output", type=Path, default=Path("runtime/evidence_report.zip"))
    from intelligent_mdm.operational_time.commands import add_time_commands
    add_time_commands(sub)
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if args.command == "generate":
        bundle = generate(args.size, args.seed)
        issues = validate_bundle(bundle)
        if not issues.empty:
            raise SystemExit(issues.to_string(index=False))
        save_bundle(bundle, args.output)
        print(f"Generated {sum(len(t) for t in bundle.tables.values()):,} rows in {args.output}")
    elif args.command == "experiments":
        from intelligent_mdm.reporting.experiments import run_experiments
        run_experiments(args.output, tuple(args.scales), tuple(args.seeds), args.semantic_model)
        print(f"Experiment results: {args.output}")
    elif args.command == "report":
        from intelligent_mdm.reporting import build_report
        bundle = load_bundle(args.input) if args.input else generate(args.size, args.seed)
        if args.table not in bundle.tables:
            raise SystemExit("Unknown table")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(build_report(bundle, name=args.table))
        print(f"Evidence report: {args.output}")

    elif args.command.startswith("time-"):
        from intelligent_mdm.operational_time.commands import run_time_command
        try:
            run_time_command(args)
        except (ValueError, OSError) as exc:
            parser.error(str(exc))


if __name__ == "__main__":
    main()
