from __future__ import annotations

import argparse
from pathlib import Path

from dairy_abm.config import calibration_inventory, load_calibration
from dairy_abm.core import read_json, write_json
from dairy_abm.model import DairyFarmModel
from dairy_abm.reports import write_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dairy-abm")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--scenario", required=True)
    run_parser.add_argument("--calibration")
    run_parser.add_argument("--output", required=True)
    run_parser.add_argument("--days", type=int)
    run_parser.add_argument("--seed", type=int)
    run_parser.add_argument("--enable-processor", action="store_true")
    run_parser.add_argument("--enable-whey-processing", action="store_true")
    run_parser.add_argument("--enable-land-agent", action="store_true")

    validate_parser = subparsers.add_parser("validate-config")
    validate_parser.add_argument("--calibration")

    list_parser = subparsers.add_parser("list-calibrations")
    list_parser.add_argument("--calibration")
    list_parser.add_argument("--output")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "validate-config":
        load_calibration(args.calibration)
        return 0

    if args.command == "list-calibrations":
        inventory = calibration_inventory(load_calibration(args.calibration))
        if args.output:
            write_json(Path(args.output), inventory)
        else:
            for row in inventory:
                print(f"{row['key']}\t{row['default']}\t{row['unit']}\t{row['assumption']}")
        return 0

    if args.command == "run":
        scenario = read_json(Path(args.scenario))
        if args.days is not None:
            scenario["days"] = args.days
        if args.seed is not None:
            scenario["seed"] = args.seed
        if args.enable_processor:
            scenario["enable_processor"] = True
        if args.enable_whey_processing:
            scenario["enable_whey_processing"] = True
        if args.enable_land_agent:
            scenario["enable_land_agent"] = True
        model = DairyFarmModel(scenario, load_calibration(args.calibration))
        ctx = model.run()
        write_reports(Path(args.output), ctx)
        return 0

    raise AssertionError(f"unhandled command {args.command}")
