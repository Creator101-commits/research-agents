from __future__ import annotations

import argparse
from pathlib import Path

from dairy_abm.config import calibration_inventory, load_calibration
from dairy_abm.core import read_json, write_json
from dairy_abm.analysis.farm_system_comparison import assess_farm_systems, write_farm_system_assessment
from dairy_abm.model import DairyFarmModel
from dairy_abm.reports import write_reports


def _add_loop_toggle_arguments(parser: argparse.ArgumentParser, loop: str, destination: str) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument(f"--enable-{loop}-loop", dest=destination, action="store_true")
    group.add_argument(f"--disable-{loop}-loop", dest=destination, action="store_false")
    parser.set_defaults(**{destination: None})


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
    _add_loop_toggle_arguments(run_parser, "l1", "l1_nutrient_loop_enabled")
    _add_loop_toggle_arguments(run_parser, "l2", "l2_water_loop_enabled")
    _add_loop_toggle_arguments(run_parser, "l3", "l3_energy_loop_enabled")
    _add_loop_toggle_arguments(run_parser, "l4", "l4_byproduct_loop_enabled")

    validate_parser = subparsers.add_parser("validate-config")
    validate_parser.add_argument("--calibration")

    list_parser = subparsers.add_parser("list-calibrations")
    list_parser.add_argument("--calibration")
    list_parser.add_argument("--output")

    assess_parser = subparsers.add_parser("assess-farm-systems")
    assess_parser.add_argument("--scenario", required=True)
    assess_parser.add_argument("--calibration")
    assess_parser.add_argument("--output", required=True)
    assess_parser.add_argument("--days", type=int)
    assess_parser.add_argument("--seeds", default="1")

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
        if args.l1_nutrient_loop_enabled is not None:
            scenario["l1_nutrient_loop_enabled"] = args.l1_nutrient_loop_enabled
        if args.l2_water_loop_enabled is not None:
            scenario["l2_water_loop_enabled"] = args.l2_water_loop_enabled
        if args.l3_energy_loop_enabled is not None:
            scenario["l3_energy_loop_enabled"] = args.l3_energy_loop_enabled
        if args.l4_byproduct_loop_enabled is not None:
            scenario["l4_byproduct_loop_enabled"] = args.l4_byproduct_loop_enabled
        model = DairyFarmModel(scenario, load_calibration(args.calibration))
        ctx = model.run()
        write_reports(Path(args.output), ctx)
        return 0

    if args.command == "assess-farm-systems":
        scenario = read_json(Path(args.scenario))
        if args.days is not None:
            scenario["days"] = args.days
        try:
            seeds = tuple(int(item.strip()) for item in args.seeds.split(",") if item.strip())
        except ValueError as exc:
            raise SystemExit("--seeds must be a comma-separated list of integers") from exc
        assessment = assess_farm_systems(
            scenario,
            load_calibration(args.calibration),
            seeds=seeds,
        )
        write_farm_system_assessment(Path(args.output), assessment)
        return 0

    raise AssertionError(f"unhandled command {args.command}")
