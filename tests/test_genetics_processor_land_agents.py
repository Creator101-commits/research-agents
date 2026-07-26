from __future__ import annotations

import unittest

from dairy_abm.config import load_calibration
from dairy_abm.core import ConfigError
from dairy_abm.model import DairyFarmModel


def scenario(**overrides):
    base = {
        "name": "genetics-processor-land",
        "start_date": "2026-01-01",
        "days": 1,
        "seed": 3,
        "herd_size": 8,
        "land_cropland_ha": 0,
        "enable_land_agent": False,
    }
    base.update(overrides)
    return base


class GeneticsProcessorLandAgentsTest(unittest.TestCase):
    def test_processor_agent_is_present_but_zero_flow_by_default(self) -> None:
        ctx = DairyFarmModel(scenario(), load_calibration()).run()
        packet = ctx.packets["processor_packet"]
        cow = ctx.packets["cow_daily_packet"].payload
        self.assertEqual(packet.quality, "inactive")
        self.assertFalse(packet.payload["enabled"])
        self.assertEqual(packet.payload["milk_processed_l"], 0.0)
        self.assertEqual(packet.payload["farm_gate_milk_l"], cow["milk_l"])
        self.assertNotIn("land_packet", ctx.packets)

    def test_processor_opt_in_processes_milk_and_optional_whey(self) -> None:
        ctx = DairyFarmModel(
            scenario(enable_processor=True, enable_whey_processing=True, herd_size=2),
            load_calibration(),
        ).run()
        packet = ctx.packets["processor_packet"].payload
        cow = ctx.packets["cow_daily_packet"].payload
        self.assertTrue(packet["enabled"])
        self.assertEqual(packet["milk_processed_l"], cow["milk_l"])
        self.assertGreater(packet["processor_revenue"], cow["milk_revenue"])
        self.assertGreater(packet["processing_energy_kwh"], 0)
        self.assertGreater(packet["whey_l"], 0)
        self.assertAlmostEqual(sum(packet["product_mix"].values()), 1.0)

    def test_land_agent_disabled_keeps_feed_crop_land_ownership(self) -> None:
        ctx = DairyFarmModel(scenario(land_cropland_ha=4), load_calibration()).run()
        self.assertEqual(ctx.daily_records[0]["land_owner"], "feed_crop")
        self.assertEqual(ctx.packets["feed_crop_packet"].payload["land_owner"], "feed_crop")
        self.assertNotIn("land_packet", ctx.packets)

    def test_land_agent_opt_in_transfers_land_ownership(self) -> None:
        ctx = DairyFarmModel(scenario(enable_land_agent=True, land_cropland_ha=4), load_calibration()).run()
        self.assertEqual(ctx.daily_records[0]["land_owner"], "land")
        self.assertEqual(ctx.packets["land_packet"].payload["land_owner"], "land")
        self.assertEqual(ctx.packets["feed_crop_packet"].payload["land_owner"], "land")
        self.assertIn("land", ctx.daily_records[0]["execution_order"])

    def test_invalid_land_area_is_rejected_when_land_agent_enabled(self) -> None:
        with self.assertRaises(ConfigError):
            DairyFarmModel(scenario(enable_land_agent=True, land_cropland_ha=-1), load_calibration()).run()

    def test_annual_genetics_runs_on_calendar_year_end(self) -> None:
        ctx = DairyFarmModel(
            scenario(start_date="2026-12-31", days=1, herd_size=10),
            load_calibration(),
        ).run()
        packet = ctx.packets["genetics_packet"].payload
        self.assertEqual(packet["year"], 2026)
        self.assertEqual(packet["minimum_intake_record_days"], 35)
        self.assertEqual(packet["selected_parent_count"], 0)
        self.assertEqual(ctx.annual_records[0]["report"], "genetics")

    def test_genetics_requires_35_daily_intake_records_for_eligibility(self) -> None:
        ctx = DairyFarmModel(
            scenario(start_date="2026-11-27", days=35, herd_size=2), load_calibration()
        ).run()
        packet = ctx.packets["genetics_packet"].payload

        self.assertEqual(packet["eligible_candidate_count"], 2)
        original_cows = [cow for cow in ctx.state["cows"] if str(cow["id"]).startswith("cow-")]
        self.assertTrue(all(cow["candidate_record_complete"] for cow in original_cows))
        self.assertTrue(all(cow["recorded_dmi_days"] >= 35 for cow in original_cows))

    def test_genetics_selects_eligible_cows_by_normalized_trait_weights(self) -> None:
        calibration = load_calibration()
        for trait in calibration["genetics"]["trait_weights"].values():
            trait["value"] = 0.0
        calibration["genetics"]["trait_weights"]["milk_yield"]["value"] = 1.0
        ctx = DairyFarmModel(
            scenario(
                start_date="2026-11-27",
                days=35,
                herd=[
                    {"id": "cow-low", "milk_trait": 0.9},
                    {"id": "cow-high", "milk_trait": 1.1},
                ],
            ),
            calibration,
        ).run()
        packet = ctx.packets["genetics_packet"].payload

        self.assertEqual(packet["selected_parent_ids"], ["cow-high"])
        self.assertEqual(packet["selection_weights"]["milk_yield"], 1.0)

    def test_genetics_reweights_for_high_feed_cost_and_reports_breeder_equation(self) -> None:
        calibration = load_calibration()
        calibration["market"]["feed_cost_per_kg_dm"]["value"] = 1.0
        ctx = DairyFarmModel(
            scenario(start_date="2026-11-27", days=35, herd_size=2), calibration
        ).run()
        packet = ctx.packets["genetics_packet"].payload

        self.assertGreater(packet["selection_weights"]["feed_efficiency"], 0.3)
        self.assertGreater(packet["genetic_gain_per_generation"], 0.0)
        self.assertAlmostEqual(
            packet["genetic_gain_per_generation"],
            packet["heritability_h2_rfi_fat"]
            * packet["selection_intensity_i"]
            * packet["phenotypic_sd_rfi_fat"]
            / packet["generation_interval_years"],
        )

    def test_genetics_generates_offspring_from_parent_trait_vectors_without_mutating_parents(self) -> None:
        calibration = load_calibration()
        calibration["genetics"]["selection_intensity"]["value"] = 1.0
        calibration["genetics"]["offspring_trait_variation_fraction"]["value"] = 0.0
        herd = [
            {
                "id": "parent-a",
                "milk_trait": 1.2,
                "trait_vector": {
                    "milk_yield": 1.2,
                    "feed_efficiency": 1.2,
                    "fertility": 1.2,
                    "health": 1.2,
                    "survivability": 1.2,
                },
            },
            {
                "id": "parent-b",
                "milk_trait": 0.8,
                "trait_vector": {
                    "milk_yield": 0.8,
                    "feed_efficiency": 0.8,
                    "fertility": 0.8,
                    "health": 0.8,
                    "survivability": 0.8,
                },
            },
        ]
        ctx = DairyFarmModel(
            scenario(start_date="2026-11-27", days=35, herd=herd), calibration
        ).run()
        packet = ctx.packets["genetics_packet"].payload

        self.assertEqual(packet["offspring_parent_ids"], ["parent-a", "parent-b"])
        self.assertEqual(packet["offspring_trait_vector"]["milk_yield"], 1.0)
        self.assertEqual(ctx.state["cows"][0]["trait_vector"]["milk_yield"], 1.2)
        self.assertEqual(ctx.state["cows"][1]["trait_vector"]["milk_yield"], 0.8)

    def test_genetics_reweights_for_disease_pressure_and_low_cull_value(self) -> None:
        calibration = load_calibration()
        calibration["disease"]["mastitis_daily_probability"]["value"] = 1.0
        calibration["disease"]["recovery_daily_probability"]["value"] = 0.0
        calibration["market"]["cull_cow_price"]["value"] = 500.0
        ctx = DairyFarmModel(
            scenario(start_date="2026-11-27", days=35, herd_size=2), calibration
        ).run()
        packet = ctx.packets["genetics_packet"].payload

        self.assertGreater(packet["active_disease_cases"], 0)
        self.assertEqual(packet["cull_cow_price"], 500.0)
        self.assertGreater(packet["selection_weights"]["health"], 0.1)
        self.assertGreater(packet["selection_weights"]["survivability"], 0.1)


if __name__ == "__main__":
    unittest.main()
