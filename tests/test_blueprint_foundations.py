from __future__ import annotations

from datetime import date
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
import json
import unittest

from dairy_abm.config import load_calibration, validate_calibration, value
from dairy_abm.core import ConfigError, EventLog, Packet, SimulationContext
from dairy_abm.agents.cow_agent import CowAgent
from dairy_abm.model import DairyFarmModel
from dairy_abm.reports import write_reports


class BlueprintFoundationsTest(unittest.TestCase):
    def test_context_initializes_policy_and_environment_ledger_state(self) -> None:
        ctx = SimulationContext(scenario={}, calibration={}, rng=Random(1), events=EventLog())

        self.assertEqual(
            ctx.state["policy"],
            {
                "cofeed_safety_approved": False,
                "coproduct_feed_allowed": True,
                "dairy_processor_unit_enabled": False,
                "whey_processor_unit_enabled": False,
                "thermochemical_route_active": False,
            },
        )
        self.assertEqual(ctx.state["environment_ledger"], {})

    def test_environment_streams_reject_duplicate_source_stream_and_period(self) -> None:
        ctx = SimulationContext(scenario={}, calibration={}, rng=Random(1), events=EventLog())
        stream = Packet(
            source="energy",
            name="energy_offset_packet",
            day=date(2026, 1, 1),
            payload={"kg_co2e": 1.0},
            period="daily",
            confidence="calibrated",
            stream_id="grid_offset",
        )

        ctx.record_environment_stream(stream)
        with self.assertRaises(ConfigError):
            ctx.record_environment_stream(stream)

    def test_model_policy_uses_scenario_override_then_calibration_default(self) -> None:
        calibration = load_calibration()
        model = DairyFarmModel(
            {
                "cofeed_safety_approved": True,
                "coproduct_feed_allowed": False,
                "enable_processor": True,
                "enable_whey_processing": True,
            },
            calibration,
        )

        self.assertTrue(model.ctx.state["policy"]["cofeed_safety_approved"])
        self.assertFalse(model.ctx.state["policy"]["coproduct_feed_allowed"])
        self.assertTrue(model.ctx.state["policy"]["dairy_processor_unit_enabled"])
        self.assertTrue(model.ctx.state["policy"]["whey_processor_unit_enabled"])
        self.assertEqual(
            model.ctx.state["policy"]["thermochemical_route_active"],
            value(calibration, "farm_manager.thermochemical_route_active"),
        )

    def test_policy_calibration_values_must_be_boolean(self) -> None:
        calibration = load_calibration()
        calibration["farm_manager"]["coproduct_feed_allowed"]["value"] = "yes"

        with self.assertRaises(ConfigError):
            validate_calibration(calibration)

    def test_summary_reports_effective_policy_state(self) -> None:
        model = DairyFarmModel(
            {"cofeed_safety_approved": True, "coproduct_feed_allowed": False},
            load_calibration(),
        )
        ctx = model.run()

        with TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_reports(output, ctx)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))

        self.assertTrue(summary["policy"]["cofeed_safety_approved"])
        self.assertFalse(summary["policy"]["coproduct_feed_allowed"])

    def test_processor_revenue_and_energy_cost_flow_to_manager(self) -> None:
        calibration = load_calibration()
        ctx = DairyFarmModel(
            {
                "days": 1,
                "herd_size": 2,
                "enable_processor": True,
                "enable_whey_processing": True,
            },
            calibration,
        ).run()
        cow = ctx.packets["cow_daily_packet"].payload
        processor = ctx.packets["processor_packet"].payload
        manager = ctx.packets["manager_packet"].payload
        electricity_price = ctx.packets["market_price_packet"].payload["electricity_price_per_kwh"]
        cooling_kwh = cow["milk_l"] * value(
            calibration,
            "dairy_processor.milk_cooling_kwh_per_l_milk",
        )

        self.assertTrue(processor["enabled"])
        self.assertEqual(manager["milk_revenue"], processor["processor_revenue"])
        self.assertEqual(manager["processing_energy_cost"], processor["processing_energy_kwh"] * electricity_price)
        self.assertEqual(manager["cooling_cost"], cooling_kwh * electricity_price)

    def test_coproduct_policy_blocks_whey_feed_credit(self) -> None:
        ctx = DairyFarmModel(
            {
                "days": 2,
                "herd_size": 2,
                "enable_processor": True,
                "enable_whey_processing": True,
                "coproduct_feed_allowed": False,
                "l1_nutrient_loop_enabled": False,
            },
            load_calibration(),
        ).run()

        self.assertEqual([row["feed_loop_offset_kg"] for row in ctx.daily_records], [0.0, 0.0])

    def test_processor_product_streams_conserve_processed_milk(self) -> None:
        calibration = load_calibration()
        calibration["dairy_processor"]["fraction_milk_to_processor"]["value"] = 0.5
        ctx = DairyFarmModel(
            {"days": 1, "herd_size": 2, "enable_processor": True}, calibration
        ).run()
        processor = ctx.packets["processor_packet"].payload

        self.assertAlmostEqual(processor["milk_processed_l"], processor["raw_milk_input_l"] * 0.5)
        self.assertAlmostEqual(
            sum(processor["product_streams_l"].values()), processor["milk_processed_l"]
        )
        self.assertAlmostEqual(
            processor["whey_l"],
            processor["product_streams_l"]["cheese"] * 0.88
            + processor["product_streams_l"]["yogurt"] * 0.05
            + processor["product_streams_l"]["functional"] * 0.10,
        )

    def test_manager_cash_rolls_forward_and_roi_requires_investment_basis(self) -> None:
        ctx = DairyFarmModel(
            {"days": 2, "herd_size": 2, "initial_cash_balance": 100.0},
            load_calibration(),
        ).run()
        manager = ctx.packets["manager_packet"].payload

        self.assertAlmostEqual(
            manager["cash_balance"], 100.0 + sum(row["profit"] for row in ctx.daily_records)
        )
        self.assertIsNone(manager["roi_circular_investment"])
        self.assertIsNone(manager["payback_period_years"])

    def test_manager_publishes_effective_policy_packet(self) -> None:
        ctx = DairyFarmModel(
            {"enable_processor": True, "coproduct_feed_allowed": False}, load_calibration()
        ).run()

        self.assertEqual(ctx.packets["manager_policy_packet"].payload, ctx.state["policy"])

    def test_cow_consumes_prior_day_ration_signal(self) -> None:
        calibration = load_calibration()
        calibration["feed_crop"]["crop_yield_kg_dm_per_ha_day"]["value"] = 0.0
        ctx = DairyFarmModel(
            {"days": 2, "herd_size": 2, "land_cropland_ha": 0.0}, calibration
        ).run()

        self.assertEqual(ctx.daily_records[0]["cow_ration_coverage_fraction"], 1.0)
        self.assertEqual(ctx.daily_records[1]["cow_ration_coverage_fraction"], 1.0)

    def test_cow_lifecycle_state_persists_and_publishes_herd_kpis(self) -> None:
        ctx = DairyFarmModel(
            {
                "days": 2,
                "herd": [
                    {
                        "id": "cow-1",
                        "age_days": 1_000,
                        "days_in_milk": 50,
                        "parity": 2,
                        "milk_trait": 1.1,
                        "feed_efficiency_trait": 0.9,
                    }
                ],
            },
            load_calibration(),
        ).run()
        cow = ctx.packets["cow_daily_packet"].payload
        persisted_cow = ctx.state["cows"][0]

        self.assertEqual(persisted_cow["age_days"], 1_002)
        self.assertEqual(persisted_cow["days_in_milk"], 52)
        self.assertEqual(persisted_cow["parity"], 2)
        self.assertEqual(persisted_cow["milk_trait"], 1.1)
        self.assertEqual(persisted_cow["feed_efficiency_trait"], 0.9)
        self.assertEqual(cow["mean_days_in_milk"], 51.0)
        self.assertGreater(cow["feed_conversion_ratio_kg_dm_per_l"], 0.0)
        self.assertGreater(cow["enteric_ch4_intensity_kg_per_l"], 0.0)

    def test_cow_applies_sensor_heat_and_sara_modifiers(self) -> None:
        calibration = load_calibration()
        ctx = SimulationContext(
            scenario={"herd": [{"id": "cow-1"}]},
            calibration=calibration,
            rng=Random(1),
            events=EventLog(),
        )
        agent = CowAgent(ctx)
        ctx.publish(
            Packet(
                source="sensors",
                name="sensor_observation_packet",
                day=date(2026, 1, 1),
                payload={"thi": 75.0, "rumen_ph_by_cow": {"cow-1": 5.6}},
            )
        )

        for day in range(3):
            agent.tick(date(2026, 1, day + 1))
        cow = ctx.packets["cow_daily_packet"].payload

        self.assertTrue(cow["heat_stress_active"])
        self.assertEqual(cow["sara_affected_cows"], 1)
        self.assertGreater(cow["dmi_kg"], 0.0)
        self.assertLess(cow["dmi_kg"], cow["cow_records"][0]["expected_dmi_eq2_1_kg_dm"])

    def test_cow_tracks_reproduction_state_with_daily_probability(self) -> None:
        calibration = load_calibration()
        calibration["cow"]["pregnancy_rate_monthly"]["value"] = 1.0
        ctx = DairyFarmModel(
            {"days": 2, "estrus_required_for_conception": False, "herd": [{"id": "cow-1", "days_in_milk": 100}]}, calibration
        ).run()
        cow = ctx.state["cows"][0]
        packet = ctx.packets["cow_daily_packet"].payload

        self.assertTrue(cow["pregnant"])
        self.assertEqual(cow["days_pregnant"], 1)
        self.assertEqual(packet["pregnant_cows"], 1)

    def test_cow_applies_prior_day_ration_coverage_to_intake_and_milk(self) -> None:
        calibration = load_calibration()
        ctx = SimulationContext(
            scenario={"herd": [{"id": "cow-1"}]},
            calibration=calibration,
            rng=Random(1),
            events=EventLog(),
        )
        agent = CowAgent(ctx)
        ctx.publish(
            Packet(
                source="feed_crop",
                name="feed_crop_packet",
                day=date(2026, 1, 1),
                payload={"ration_coverage_fraction": 0.5},
            )
        )

        agent.tick(date(2026, 1, 2))
        cow = ctx.packets["cow_daily_packet"].payload
        expected_milk = value(calibration, "cow.base_milk_l_per_cow_day") * (
            1.0 - 0.5 * value(calibration, "cow.ration_shortfall_milk_loss_fraction")
        )
        expected_milk *= agent._lactation_factor(
            int(ctx.state["cows"][0]["days_in_milk"]) - 1
        )

        self.assertGreater(cow["dmi_kg"], 0.0)
        self.assertLess(cow["dmi_kg"], cow["cow_records"][0]["expected_dmi_eq2_1_kg_dm"])
        self.assertAlmostEqual(cow["milk_l"], expected_milk)

    def test_cow_lifecycle_applies_annual_mortality_as_daily_hazard(self) -> None:
        calibration = load_calibration()
        calibration["cow"]["mortality_rate_annual"]["value"] = 1.0
        ctx = DairyFarmModel({"days": 1, "herd_size": 1}, calibration).run()

        self.assertFalse(ctx.state["cows"][0]["alive"])
        self.assertEqual(ctx.packets["cow_daily_packet"].payload["deaths"], 1)

    def test_feed_crop_conserves_local_feed_inventory_before_imports(self) -> None:
        calibration = load_calibration()
        calibration["feed_crop"]["crop_yield_kg_dm_per_ha_day"]["value"] = 10.0
        ctx = DairyFarmModel(
            {
                "days": 1,
                "herd_size": 1,
                "land_cropland_ha": 1.0,
                "initial_feed_inventory_kg_dm": 5.0,
            },
            calibration,
        ).run()
        feed = ctx.packets["feed_crop_packet"].payload

        self.assertEqual(feed["opening_feed_inventory_kg_dm"], 5.0)
        self.assertEqual(feed["local_feed_used_kg_dm"], 15.0)
        self.assertEqual(feed["ending_feed_inventory_kg_dm"], 0.0)
        self.assertEqual(feed["purchased_feed_kg_dm"], 7.0)

    def test_feed_crop_uses_prior_day_manure_nutrients_before_fertilizer(self) -> None:
        calibration = load_calibration()
        ctx = DairyFarmModel(
            {"days": 2, "herd_size": 1, "land_cropland_ha": 1.0}, calibration
        ).run()
        feed = ctx.packets["feed_crop_packet"].payload
        manure = ctx.daily_records[0]["compost_kg"]
        daily_n_requirement = value(calibration, "feed_crop.fertilizer_n_kg_per_ha_month") / 30.0

        self.assertGreater(manure, 0.0)
        self.assertGreater(feed["organic_n_used_kg"], 0.0)
        self.assertAlmostEqual(
            feed["fertilizer_n_required_kg"],
            daily_n_requirement - feed["organic_n_used_kg"],
        )

    def test_feed_crop_publishes_ration_protein_and_nitrogen_quantities(self) -> None:
        calibration = load_calibration()
        ctx = DairyFarmModel(
            {"days": 1, "herd_size": 1, "land_cropland_ha": 0.0}, calibration
        ).run()
        feed = ctx.packets["feed_crop_packet"].payload
        purchased_feed = feed["purchased_feed_kg_dm"]
        imported_cp_fraction = value(calibration, "feed_crop.imported_feed_crude_protein_fraction")

        self.assertAlmostEqual(
            feed["ration_crude_protein_kg"],
            purchased_feed * imported_cp_fraction
            - feed["amino_acid_cp_reduction_points"] * feed["dmi_demand_kg"],
        )
        self.assertAlmostEqual(
            feed["ration_metabolizable_protein_kg"],
            max(
                feed["ration_crude_protein_kg"],
                feed["dmi_demand_kg"] * feed["nir_crude_protein_fraction"]
                - feed["amino_acid_cp_reduction_points"] * feed["dmi_demand_kg"],
            )
            * value(calibration, "feed_crop.metabolizable_protein_fraction_of_crude_protein"),
        )
        self.assertAlmostEqual(
            feed["ration_nitrogen_kg"],
            feed["ration_crude_protein_kg"]
            * value(calibration, "feed_crop.nitrogen_fraction_of_crude_protein"),
        )

    def test_cow_publishes_nitrogen_use_efficiency_from_prior_ration(self) -> None:
        calibration = load_calibration()
        ctx = DairyFarmModel(
            {"days": 2, "herd_size": 1, "land_cropland_ha": 0.0}, calibration
        ).run()
        cow = ctx.packets["cow_daily_packet"].payload

        self.assertAlmostEqual(
            cow["nitrogen_use_efficiency"],
            cow["milk_protein_nitrogen_kg"] / ctx.packets["feed_crop_packet"].payload["ration_nitrogen_kg"],
        )

    def test_feed_crop_separates_recovered_and_fresh_irrigation(self) -> None:
        calibration = load_calibration()
        ctx = DairyFarmModel(
            {"days": 2, "herd_size": 1, "land_cropland_ha": 1.0}, calibration
        ).run()
        feed = ctx.packets["feed_crop_packet"].payload

        self.assertEqual(
            feed["irrigation_demand_l"], value(calibration, "feed_crop.irrigation_l_per_ha_day")
        )
        self.assertEqual(feed["recovered_water_applied_l"], feed["water_offset_l"])
        self.assertAlmostEqual(
            feed["freshwater_irrigation_l"] + feed["recovered_water_applied_l"],
            feed["irrigation_demand_l"],
        )

    def test_feed_crop_passes_same_day_nitrogen_context_to_manure(self) -> None:
        ctx = DairyFarmModel({"days": 1, "herd_size": 1}, load_calibration()).run()
        feed_context = ctx.packets["feed_nitrogen_context_packet"].payload
        manure = ctx.packets["manure_packet"].payload

        self.assertEqual(feed_context["ration_nitrogen_kg"], manure["feed_ration_nitrogen_kg"])
        self.assertEqual(feed_context["ration_crude_protein_kg"], manure["feed_ration_crude_protein_kg"])

    def test_genetics_annual_cycle_consumes_feed_cost_signal(self) -> None:
        ctx = DairyFarmModel(
            {"start_date": "2026-12-31", "days": 1, "herd_size": 1}, load_calibration()
        ).run()
        genetics = ctx.packets["genetics_packet"].payload
        feed = ctx.packets["feed_crop_packet"].payload

        self.assertEqual(genetics["feed_cost_signal_per_kg_dm"], feed["feed_cost_per_kg_dm"])


if __name__ == "__main__":
    unittest.main()
