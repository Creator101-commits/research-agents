from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import json
import unittest

from dairy_abm.cli import main
from dairy_abm.config import load_calibration
from dairy_abm.model import DairyFarmModel


def l1_scenario(**overrides: object) -> dict[str, object]:
    scenario: dict[str, object] = {
        "name": "l1-loop-closure",
        "start_date": "2026-01-01",
        "days": 2,
        "seed": 7,
        "herd_size": 2,
        "land_cropland_ha": 0,
    }
    scenario.update(overrides)
    return scenario


class LoopClosureTest(unittest.TestCase):
    def test_l1_credit_is_consumed_on_the_following_day(self) -> None:
        calibration = load_calibration()
        ctx = DairyFarmModel(l1_scenario(), calibration).run()

        first_day, second_day = ctx.daily_records
        expected_credit = first_day["compost_kg"] * calibration["feed_crop"][
            "nutrient_loop_feed_substitution_fraction"
        ]["value"]

        self.assertEqual(first_day["feed_loop_offset_kg"], 0.0)
        self.assertAlmostEqual(second_day["feed_loop_offset_kg"], expected_credit)
        self.assertGreaterEqual(second_day["feed_cost"], 0.0)

    def test_l1_disabled_does_not_create_a_feed_credit(self) -> None:
        calibration = deepcopy(load_calibration())
        calibration["manure"]["l1_nutrient_loop_enabled"]["value"] = False
        ctx = DairyFarmModel(l1_scenario(), calibration).run()

        self.assertEqual([row["feed_loop_offset_kg"] for row in ctx.daily_records], [0.0, 0.0])
        self.assertEqual(ctx.state["loop_credits"]["feed_offset_kg"], 0.0)

    def test_feed_crop_drains_available_credit_once(self) -> None:
        model = DairyFarmModel(l1_scenario(days=1), load_calibration())
        model.ctx.state["loop_credits"] = {"feed_offset_kg": 100.0, "water_offset_l": 0.0}
        feed_agent = next(agent for agent in model.agents if agent.name == "feed_crop")

        feed_agent.tick(date(2026, 1, 1))

        self.assertEqual(model.ctx.state["loop_credits"], {"feed_offset_kg": 0.0, "water_offset_l": 0.0})
        self.assertEqual(model.ctx.packets["feed_crop_packet"].payload["feed_offset_kg"], 100.0)

    def test_cli_disable_l1_loop_overrides_the_scenario(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario_path = root / "scenario.json"
            scenario_path.write_text(
                json.dumps(l1_scenario(l1_nutrient_loop_enabled=True)),
                encoding="utf-8",
            )
            output_dir = root / "output"

            self.assertEqual(
                main(
                    [
                        "run",
                        "--scenario",
                        str(scenario_path),
                        "--output",
                        str(output_dir),
                        "--disable-l1-loop",
                    ]
                ),
                0,
            )

            with (output_dir / "daily.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([float(row["feed_loop_offset_kg"]) for row in rows], [0.0, 0.0])
            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertFalse(summary["scenario_flags"]["l1_nutrient_loop_enabled"])

    def test_l2_credit_is_consumed_on_the_following_day(self) -> None:
        calibration = deepcopy(load_calibration())
        calibration["water"]["water_saving_l_per_cow_day"]["value"] = 0.0
        ctx = DairyFarmModel(
            l1_scenario(land_cropland_ha=1, l1_nutrient_loop_enabled=False),
            calibration,
        ).run()

        first_day, second_day = ctx.daily_records
        expected_credit = (
            2
            * calibration["water"]["parlor_l_per_cow_day"]["value"]
            * calibration["water"]["treatment_recovery_fraction"]["value"]
            * calibration["water"]["water_loop_fresh_water_offset_fraction"]["value"]
        )

        self.assertEqual(first_day["water_loop_offset_l"], 0.0)
        self.assertAlmostEqual(second_day["water_loop_offset_l"], expected_credit)

    def test_l2_disabled_does_not_create_a_water_credit(self) -> None:
        calibration = deepcopy(load_calibration())
        calibration["water"]["water_saving_l_per_cow_day"]["value"] = 0.0
        calibration["water"]["l2_water_loop_enabled"]["value"] = False
        ctx = DairyFarmModel(
            l1_scenario(land_cropland_ha=1, l1_nutrient_loop_enabled=False),
            calibration,
        ).run()

        self.assertEqual([row["water_loop_offset_l"] for row in ctx.daily_records], [0.0, 0.0])
        self.assertEqual(ctx.state["loop_credits"], {"feed_offset_kg": 0.0, "water_offset_l": 0.0})

    def test_water_credit_is_drained_once_and_irrigation_is_nonnegative(self) -> None:
        model = DairyFarmModel(l1_scenario(days=1, land_cropland_ha=1), load_calibration())
        model.ctx.state["loop_credits"] = {"feed_offset_kg": 0.0, "water_offset_l": 10000.0}
        feed_agent = next(agent for agent in model.agents if agent.name == "feed_crop")

        feed_agent.tick(date(2026, 1, 1))

        self.assertEqual(model.ctx.state["loop_credits"], {"feed_offset_kg": 0.0, "water_offset_l": 0.0})
        self.assertEqual(model.ctx.packets["feed_crop_packet"].payload["water_offset_l"], 10000.0)
        self.assertEqual(model.ctx.packets["feed_crop_packet"].payload["irrigation_l"], 0.0)

    def test_cli_disable_l2_loop_overrides_the_scenario(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario_path = root / "scenario.json"
            scenario_path.write_text(
                json.dumps(
                    l1_scenario(
                        land_cropland_ha=1,
                        l1_nutrient_loop_enabled=False,
                        l2_water_loop_enabled=True,
                    )
                ),
                encoding="utf-8",
            )
            calibration_path = root / "calibration.json"
            calibration_path.write_text(
                json.dumps({"water": {"water_saving_l_per_cow_day": {"value": 0.0}}}),
                encoding="utf-8",
            )
            output_dir = root / "output"

            self.assertEqual(
                main(
                    [
                        "run",
                        "--scenario",
                        str(scenario_path),
                        "--calibration",
                        str(calibration_path),
                        "--output",
                        str(output_dir),
                        "--disable-l2-loop",
                    ]
                ),
                0,
            )

            with (output_dir / "daily.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([float(row["water_loop_offset_l"]) for row in rows], [0.0, 0.0])
            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertFalse(summary["scenario_flags"]["l2_water_loop_enabled"])

    def test_l3_only_controls_energy_generation(self) -> None:
        base_scenario = l1_scenario(
            land_cropland_ha=1,
            l1_nutrient_loop_enabled=False,
            l2_water_loop_enabled=False,
        )
        enabled = DairyFarmModel(base_scenario, load_calibration()).run()
        disabled = DairyFarmModel(
            l1_scenario(
                land_cropland_ha=1,
                l1_nutrient_loop_enabled=False,
                l2_water_loop_enabled=False,
                l3_energy_loop_enabled=False,
            ),
            load_calibration(),
        ).run()

        self.assertTrue(all(row["net_kwh"] > 0.0 for row in enabled.daily_records))
        self.assertEqual([row["net_kwh"] for row in disabled.daily_records], [0.0, 0.0])
        self.assertEqual(
            enabled.packets["feed_crop_packet"].payload["purchased_feed_kg_dm"],
            disabled.packets["feed_crop_packet"].payload["purchased_feed_kg_dm"],
        )
        self.assertEqual(
            enabled.packets["feed_crop_packet"].payload["irrigation_l"],
            disabled.packets["feed_crop_packet"].payload["irrigation_l"],
        )

    def test_non_energy_loops_do_not_change_energy_generation(self) -> None:
        disabled = DairyFarmModel(
            l1_scenario(
                land_cropland_ha=1,
                l1_nutrient_loop_enabled=False,
                l2_water_loop_enabled=False,
                enable_processor=True,
                enable_whey_processing=True,
                l4_byproduct_loop_enabled=False,
            ),
            load_calibration(),
        ).run()
        enabled = DairyFarmModel(
            l1_scenario(
                land_cropland_ha=1,
                enable_processor=True,
                enable_whey_processing=True,
                l4_byproduct_loop_enabled=True,
            ),
            load_calibration(),
        ).run()

        self.assertEqual(
            [row["net_kwh"] for row in enabled.daily_records],
            [row["net_kwh"] for row in disabled.daily_records],
        )

    def test_cli_disable_l3_loop_overrides_the_scenario(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario_path = root / "scenario.json"
            scenario_path.write_text(
                json.dumps(l1_scenario(l3_energy_loop_enabled=True)),
                encoding="utf-8",
            )
            output_dir = root / "output"

            self.assertEqual(
                main(
                    [
                        "run",
                        "--scenario",
                        str(scenario_path),
                        "--output",
                        str(output_dir),
                        "--disable-l3-loop",
                    ]
                ),
                0,
            )

            with (output_dir / "daily.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([float(row["net_kwh"]) for row in rows], [0.0, 0.0])
            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertFalse(summary["scenario_flags"]["l3_energy_loop_enabled"])

    def test_l4_credit_is_consumed_on_the_following_day(self) -> None:
        calibration = load_calibration()
        ctx = DairyFarmModel(
            l1_scenario(
                l1_nutrient_loop_enabled=False,
                l2_water_loop_enabled=False,
                enable_processor=True,
                enable_whey_processing=True,
            ),
            calibration,
        ).run()

        first_day, second_day = ctx.daily_records
        expected_credit = (
            ctx.daily_records[0]["milk_l"]
            * (
                calibration["dairy_processor"]["product_mix_cheese"]["value"]
                * calibration["dairy_processor"]["whey_yield_cheese"]["value"]
                + calibration["dairy_processor"]["product_mix_yogurt"]["value"]
                * calibration["dairy_processor"]["whey_yield_yogurt"]["value"]
                + calibration["dairy_processor"]["product_mix_functional"]["value"]
                * calibration["dairy_processor"]["whey_yield_functional"]["value"]
            )
            * calibration["dairy_processor"]["byproduct_loop_feed_substitution_kg_per_kg"]["value"]
            * calibration["dairy_processor"]["fraction_whey_to_feed"]["value"]
        )

        self.assertEqual(first_day["feed_loop_offset_kg"], 0.0)
        self.assertAlmostEqual(second_day["feed_loop_offset_kg"], expected_credit)

    def test_l4_disabled_does_not_create_a_feed_credit(self) -> None:
        calibration = deepcopy(load_calibration())
        calibration["dairy_processor"]["l4_byproduct_loop_enabled"]["value"] = False
        ctx = DairyFarmModel(
            l1_scenario(
                l1_nutrient_loop_enabled=False,
                l2_water_loop_enabled=False,
                enable_processor=True,
                enable_whey_processing=True,
            ),
            calibration,
        ).run()

        self.assertEqual([row["feed_loop_offset_kg"] for row in ctx.daily_records], [0.0, 0.0])
        self.assertEqual(ctx.state["loop_credits"], {"feed_offset_kg": 0.0, "water_offset_l": 0.0})

    def test_disabled_cross_agent_loops_leave_no_credit_or_feed_crop_effect(self) -> None:
        calibration = deepcopy(load_calibration())
        calibration["water"]["water_saving_l_per_cow_day"]["value"] = 0.0
        disabled_scenario = l1_scenario(
            land_cropland_ha=1,
            l1_nutrient_loop_enabled=False,
            l2_water_loop_enabled=False,
            l4_byproduct_loop_enabled=False,
            enable_processor=True,
            enable_whey_processing=True,
        )
        disabled = DairyFarmModel(disabled_scenario, calibration).run()
        reference = DairyFarmModel(
            l1_scenario(
                land_cropland_ha=1,
                l1_nutrient_loop_enabled=False,
                l2_water_loop_enabled=False,
                l4_byproduct_loop_enabled=False,
            ),
            deepcopy(calibration),
        ).run()

        self.assertEqual(disabled.state["loop_credits"], {"feed_offset_kg": 0.0, "water_offset_l": 0.0})
        self.assertEqual([row["feed_loop_offset_kg"] for row in disabled.daily_records], [0.0, 0.0])
        self.assertEqual([row["water_loop_offset_l"] for row in disabled.daily_records], [0.0, 0.0])
        self.assertEqual(
            disabled.packets["feed_crop_packet"].payload["purchased_feed_kg_dm"],
            reference.packets["feed_crop_packet"].payload["purchased_feed_kg_dm"],
        )
        self.assertEqual(
            disabled.packets["feed_crop_packet"].payload["irrigation_l"],
            reference.packets["feed_crop_packet"].payload["irrigation_l"],
        )

    def test_oversized_credits_do_not_create_negative_feed_or_irrigation(self) -> None:
        calibration = deepcopy(load_calibration())
        calibration["feed_crop"]["nutrient_loop_feed_substitution_fraction"]["value"] = 100.0
        calibration["water"]["water_saving_l_per_cow_day"]["value"] = 0.0
        calibration["water"]["water_loop_fresh_water_offset_fraction"]["value"] = 100.0
        ctx = DairyFarmModel(
            l1_scenario(land_cropland_ha=1, l4_byproduct_loop_enabled=False),
            calibration,
        ).run()
        feed_packet = ctx.packets["feed_crop_packet"].payload

        self.assertEqual(feed_packet["purchased_feed_kg_dm"], 0.0)
        self.assertEqual(feed_packet["irrigation_l"], 0.0)

    def test_cli_disable_l4_loop_overrides_the_scenario(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario_path = root / "scenario.json"
            scenario_path.write_text(
                json.dumps(
                    l1_scenario(
                        l1_nutrient_loop_enabled=False,
                        l2_water_loop_enabled=False,
                        enable_processor=True,
                        enable_whey_processing=True,
                        l4_byproduct_loop_enabled=True,
                    )
                ),
                encoding="utf-8",
            )
            output_dir = root / "output"

            self.assertEqual(
                main(
                    [
                        "run",
                        "--scenario",
                        str(scenario_path),
                        "--output",
                        str(output_dir),
                        "--disable-l4-loop",
                    ]
                ),
                0,
            )

            with (output_dir / "daily.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([float(row["feed_loop_offset_kg"]) for row in rows], [0.0, 0.0])
            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertFalse(summary["scenario_flags"]["l4_byproduct_loop_enabled"])

    def test_loop_configuration_replays_identical_daily_csv(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario_path = root / "scenario.json"
            scenario_path.write_text(
                json.dumps(
                    l1_scenario(
                        land_cropland_ha=1,
                        enable_processor=True,
                        enable_whey_processing=True,
                        l4_byproduct_loop_enabled=True,
                    )
                ),
                encoding="utf-8",
            )
            first_output = root / "first"
            second_output = root / "second"
            command = ["run", "--scenario", str(scenario_path)]

            self.assertEqual(main([*command, "--output", str(first_output)]), 0)
            self.assertEqual(main([*command, "--output", str(second_output)]), 0)

            self.assertEqual(
                (first_output / "daily.csv").read_text(encoding="utf-8"),
                (second_output / "daily.csv").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
