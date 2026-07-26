from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from dairy_abm.config import load_calibration
from dairy_abm.model import DairyFarmModel
from dairy_abm.reports import write_reports


class FullBlueprintCoverageTest(unittest.TestCase):
    def test_non_ui_blueprint_packets_expose_required_agent_features(self) -> None:
        ctx = DairyFarmModel(
            {
                "name": "full-blueprint-coverage",
                "start_date": "2026-11-22",
                "days": 40,
                "seed": 19,
                "herd_size": 3,
                "land_cropland_ha": 2.0,
                "land_pasture_ha": 1.0,
                "enable_land_agent": True,
                "land_grazing_enabled": True,
                "rotational_grazing_paddocks": 2,
                "enable_processor": True,
                "enable_whey_processing": True,
                "amino_acid_policy_active": True,
                "catch_crop_active": True,
                "market_scenario": "GM",
                "carbon_credit_price_per_tonne_co2e": 50.0,
                "solar_capacity_kw": 2.0,
                "policy_updates": {"default": {"vaccination_policy_active": True}},
            },
            load_calibration(),
        ).run()

        expected_packets = {
            "cow_daily_packet", "feed_crop_packet", "manure_resource_packet",
            "energy_offset_packet", "disease_state_packet", "environment_packet",
            "manager_packet", "sensor_observation_packet", "water_delivery_packet",
            "water_environment_packet", "dairy_return_feed_packet", "market_price_packet",
            "land_packet", "soil_carbon_packet", "genetics_packet",
        }
        self.assertTrue(expected_packets.issubset(ctx.packets))

        cow = ctx.packets["cow_daily_packet"].payload
        feed = ctx.packets["feed_crop_packet"].payload
        genetics = ctx.packets["genetics_packet"].payload
        self.assertIn("actual_dmi_kg_dm", cow)
        self.assertIn("per_cow_rations", feed)
        self.assertTrue(feed["catch_crop_active"])
        self.assertEqual(genetics["net_merit_template"], "GM")
        self.assertIn("candidate_pool", genetics)
        self.assertIn("offspring_id", genetics)

        self.assertIn("outbreak_active_flag", ctx.packets["disease_state_packet"].payload)
        self.assertIn("ICirc", ctx.packets["environment_packet"].payload)
        self.assertIn("actionable_recommendations", ctx.packets["manager_packet"].payload)
        self.assertIn("fleet_health", ctx.packets["sensor_observation_packet"].payload)
        self.assertIn("freshwater_withdrawal_l", ctx.packets["water_packet"].payload)
        self.assertIn("scotta_output_l", ctx.packets["processor_packet"].payload)
        self.assertIn("dong_du_gould_volatility_20d", ctx.packets["market_price_packet"].payload)
        self.assertIn("land_allocation", ctx.packets["land_packet"].payload)

    def test_policy_dispatch_precedes_disease_and_feed_precedes_cow(self) -> None:
        ctx = DairyFarmModel({"days": 1, "herd_size": 1}, load_calibration()).run()
        order = ctx.daily_records[0]["execution_order"].split(",")
        self.assertLess(order.index("feed_crop"), order.index("cow"))
        self.assertLess(order.index("farm_manager_policy"), order.index("disease"))
        self.assertLess(order.index("water_delivery"), order.index("cow"))

    def test_manager_policy_changes_and_conflicts_follow_operating_signals(self) -> None:
        calibration = load_calibration()
        calibration["market"]["feed_cost_per_kg_dm"]["value"] = 100.0
        ctx = DairyFarmModel(
            {
                "days": 1,
                "herd_size": 2,
                "land_cropland_ha": 0.0,
                "catch_crop_active": True,
                "auto_feed_cost_trigger": 1.0,
            },
            calibration,
        ).run()

        policy = ctx.packets["manager_policy_packet"].payload
        manager = ctx.packets["manager_packet"].payload
        self.assertEqual(policy["feed_mode"], "precision")
        self.assertTrue(policy["amino_acid_policy_active"])
        self.assertTrue(manager["automatic_policy_actions"])
        self.assertTrue(manager["policy_conflicts"])

    def test_daily_export_contains_operational_kpis_and_calving_adds_nonproducing_calf(self) -> None:
        ctx = DairyFarmModel(
            {
                "days": 2,
                "herd": [{"id": "dam", "pregnant": True, "days_pregnant": 279, "days_in_milk": 100}],
                "gestation_days": 280,
                "land_cropland_ha": 1.0,
            },
            load_calibration(),
        ).run()
        calves = [cow for cow in ctx.state["cows"] if str(cow["id"]).startswith("calf-dam-")]
        self.assertEqual(len(calves), 1)
        self.assertEqual(calves[0]["days_in_milk"], 0)
        self.assertNotIn(calves[0]["id"], {row["id"] for row in ctx.packets["cow_daily_packet"].payload["cow_records"]})

        with TemporaryDirectory() as tmp:
            write_reports(Path(tmp), ctx)
            header = (Path(tmp) / "daily.csv").read_text(encoding="utf-8").splitlines()[0]
        for field in ("biogas_volume_m3", "freshwater_withdrawal_l", "input_circularity", "disease_economic_cost", "policy_conflict_count"):
            self.assertIn(field, header)


if __name__ == "__main__":
    unittest.main()
