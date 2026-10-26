import argparse
import itertools
import json
from pathlib import Path

from . import Case, build_plan
from .builders import Workbooks, sha256
from .cases import BACKGROUNDS, MEASURES, YEARS
from .data import ensure_data
from .planning import frozen_plan


def _case(args):
    if getattr(args, "case", None):
        if args.background or args.measure or args.year:
            raise ValueError("Use --case or --background/--measure/--year, not both")
        return Case.from_json(args.case)
    return Case.paper(args.background or "NZE", args.measure or "All", args.year or 2050)


def _complete(path, plan, air_transport_extra):
    record = path / "run.json"
    if not record.is_file():
        return False
    meta = json.loads(record.read_text())
    if meta["case"] != plan.case.to_dict() or meta["air_transport_extra"] != air_transport_extra or meta["engine"] != "0.3.5":
        raise ValueError(f"Existing result uses different settings: {path}")
    source = json.loads((path / "plan.json").read_text())
    if source["sources"] != plan.sources:
        raise ValueError(f"Inputs changed since {path}; use a new output directory")
    for name, expected in meta["outputs"].items():
        if not (path / name).is_file() or sha256(path / name) != expected:
            raise ValueError(f"Incomplete or modified result: {path / name}")
    for name, expected in meta["code"].items():
        current = Path(__file__).parent / name
        if not current.is_file() or sha256(current) != expected:
            raise ValueError(f"Model code changed since {path}; use a new output directory")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compose, inspect and run FULFILL sufficiency scenarios")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="List the six measures and available years/backgrounds")
    download = sub.add_parser("download", help="Download fixed, verified Zenodo inputs (about 129.6 MB for all)")
    download.add_argument("--data", type=Path, default=Path("Data"))
    download.add_argument("--only", choices=["shocks", "all"], default="all")
    download.add_argument("--offline", action="store_true", help="Only verify existing extracted data")
    for name in ("plan", "run", "reproduce", "batch"):
        cmd = sub.add_parser(name, help={"plan": "Inspect ordered instructions without solving the IO model",
                                        "run": "Run one case and its same-year no-measure control (two solves)",
                                        "reproduce": "Run unchanged historical shock files, including documented inconsistencies",
                                        "batch": "Run a selected grid; full 192-case study requires --paper-grid"}[name])
        cmd.add_argument("--data", type=Path, default=Path("Data"))
        cmd.add_argument("--inputs", type=Path, help="Custom copy of the shock workbooks; published database stays fixed")
        cmd.add_argument("--offline", action="store_true")
        cmd.add_argument("--output", type=Path)
        cmd.add_argument("--overwrite", action="store_true")
        cmd.add_argument("--excel", action="store_true", help="Also export the legacy shock workbook")
        if name != "batch":
            if name != "reproduce":
                cmd.add_argument("--case", type=Path, help="JSON case, e.g. config/diet-and-aviation.json")
            cmd.add_argument("--background", choices=BACKGROUNDS)
            cmd.add_argument("--measure", choices=["All", "0", *MEASURES])
            cmd.add_argument("--year", type=int, choices=YEARS)
        else:
            cmd.add_argument("--backgrounds", nargs="+", choices=BACKGROUNDS)
            cmd.add_argument("--measures", nargs="+", choices=["All", "0", *MEASURES])
            cmd.add_argument("--years", nargs="+", type=int, choices=YEARS)
            cmd.add_argument("--paper-grid", action="store_true", help="Explicitly select all 3 x 8 x 8 paper cases")
            cmd.add_argument("--frozen", action="store_true", help="Use unchanged historical XLSX files instead of the composable recipe")
        if name in ("reproduce", "batch"):
            cmd.add_argument("--reference", type=Path, default=Path("Shocks/filled_files"))
        if name != "plan":
            cmd.add_argument("--air-transport-extra", action="store_true", help="Explicitly add notebook 1's air-transport account; absent from the ready-made ZIP")
            cmd.add_argument("--resume", action="store_true", help="Skip completed cases only after checking their inputs, code and output hashes")
        if name in ("run", "reproduce"):
            cmd.add_argument("--no-control", action="store_true", help="Solve just the selected case")
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            print("Backgrounds:", ", ".join(BACKGROUNDS))
            print("Years:", ", ".join(map(str, YEARS)))
            for code, label in MEASURES.items():
                print(f"{code}: {label}")
            print("0: No sufficiency measures; All: all six. Custom combinations/adoption use a JSON case.")
            return 0
        if args.command == "download":
            ensure_data(args.data, groups=("shocks",) if args.only == "shocks" else ("shocks", "database"), offline=args.offline)
            return 0
        frozen = args.command == "reproduce" or (args.command == "batch" and args.frozen)
        groups = [] if args.inputs or frozen else ["shocks"]
        if args.command != "plan":
            groups.append("database")
        ensure_data(args.data, groups=groups, offline=args.offline)
        inputs = args.inputs or args.data / "Files for shocks"
        books = Workbooks(inputs)
        if args.command == "plan":
            case = _case(args)
            plan = build_plan(case, books=books)
            path = plan.save(args.output or Path("Outputs/plans") / case.identifier,
                             overwrite=args.overwrite, excel=args.excel)
            print(plan.steps.to_string(index=False))
            print(f"Plan saved to {path.resolve()}; no IO scenario has been solved.")
            return 0
        if args.command == "batch":
            if args.paper_grid and any([args.backgrounds, args.measures, args.years]):
                raise ValueError("Use --paper-grid or selected --backgrounds/--measures/--years")
            grid = (BACKGROUNDS, ["0", "All", *MEASURES], YEARS) if args.paper_grid else (
                args.backgrounds or ["NZE"], args.measures or ["0", "All"], args.years or [2050])
            cases = [Case.paper(b, m, y) for b, m, y in itertools.product(*grid)]
            output = args.output or Path("Outputs/runs/batch")
        else:
            case = _case(args)
            control = Case.paper(case.background, "0", case.year)
            cases = [case] if args.no_control or case.to_dict() == control.to_dict() else [control, case]
            output = args.output or Path("Outputs/runs") / case.identifier
        if len({c.identifier for c in cases}) != len(cases):
            raise ValueError("Cases must have distinct names")
        if output.exists() and any(output.iterdir()) and not (args.resume or args.overwrite):
            raise FileExistsError(f"Output is not empty: {output}; choose a new directory, --resume or --overwrite")
        plans = [frozen_plan(c, args.reference) if frozen else build_plan(c, books=books) for c in cases]
        pending = [p for p in plans if not (args.resume and _complete(output / p.case.identifier, p, args.air_transport_extra))]
        print(f"Selected {len(plans)} scenario(s); {len(pending)} need solving. Full published SUT, MARIO 0.3.5.")
        from .runtime import load_database, run_plan, compare_accounts
        if pending:
            db = load_database(args.data, air_transport_extra=args.air_transport_extra)
            for plan in pending:
                run_plan(db, plan, output / plan.case.identifier, overwrite=args.overwrite, excel=args.excel)
        if args.command in ("run", "reproduce") and len(plans) == 2:
            import pandas as pd
            control, scenario = [pd.read_csv(output / p.case.identifier / "accounts.csv") for p in plans]
            compare_accounts(control, scenario).to_csv(output / "comparison.csv", index=False)
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(2, f"fulfill: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
