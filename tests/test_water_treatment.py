from __future__ import annotations

import unittest

from dairy_abm.config import load_calibration
from dairy_abm.model import DairyFarmModel


def scenario(**overrides):
    base = {
        "name": "water-treatment",
        "start_date": "2026-01-01",
        "days": 1,
        "seed": 37,
        "herd_size": 1,
        "land_cropland_ha": 0,
        "enable_land_agent": False,
    }
    base.update(overrides)
    return base


class WaterTreatmentTest(unittest.TestCase):
    def test_treated_water_is_capped_at_irrigation_demand_and_surplus_is_reported(self) -> None:
        calibration = load_calibration()
        calibration["water"]["treatment_recovery_fraction"]["value"] = 1.0
        calibration["water"]["amino_acid_policy_active_default"]["value"] = False
        calibration["feed_crop"]["irrigation_l_per_ha_day"]["value"] = 5.0
        ctx = DairyFarmModel(scenario(land_cropland_ha=1.0), calibration).run()
        water = ctx.packets["water_packet"].payload
        feed = ctx.packets["feed_crop_packet"].payload

        self.assertEqual(water["recycled_irrigation_l"], 5.0)
        self.assertGreater(water["treated_water_surplus_l"], 0.0)
        self.assertEqual(feed["irrigation_l"], 5.0)
        self.assertAlmostEqual(
            water["net_freshwater_use_l"], water["total_water_use_l"] - water["recycled_irrigation_l"]
        )

    def test_zero_milk_output_has_no_water_intensity(self) -> None:
        ctx = DairyFarmModel(scenario(herd_size=0, land_cropland_ha=1.0), load_calibration()).run()
        water = ctx.packets["water_packet"].payload

        self.assertIsNone(water["water_use_l_per_litre_milk"])
        self.assertGreaterEqual(water["total_water_use_l"], 0.0)

    def test_inactive_treatment_accumulates_wastewater_without_recovery_or_l2_credit(self) -> None:
        calibration = load_calibration()
        calibration["water"]["treatment_active"]["value"] = False
        calibration["water"]["amino_acid_policy_active_default"]["value"] = False
        ctx = DairyFarmModel(scenario(days=2, land_cropland_ha=1.0), calibration).run()
        water = ctx.packets["water_packet"].payload

        self.assertFalse(water["treatment_active"])
        self.assertEqual(water["treated_water_l"], 0.0)
        self.assertEqual(water["recycled_irrigation_l"], 0.0)
        self.assertGreater(water["wastewater_storage_l"], 0.0)
        self.assertEqual(ctx.daily_records[1]["water_loop_offset_l"], 0.0)

    def test_amino_acid_policy_adjustment_and_optional_nutrient_recovery_are_explicit(self) -> None:
        calibration = load_calibration()
        calibration["water"]["nutrient_recovery_enabled"]["value"] = True
        calibration["water"]["nutrient_recovery_kg_n_per_l"]["value"] = 0.01
        base = DairyFarmModel(
            scenario(amino_acid_policy_active=False), calibration
        ).run()
        adjusted = DairyFarmModel(
            scenario(amino_acid_policy_active=True), calibration
        ).run()
        base_water = base.packets["water_packet"].payload
        adjusted_water = adjusted.packets["water_packet"].payload

        self.assertEqual(base_water["amino_acid_water_adjustment_l"], 0.0)
        self.assertEqual(adjusted_water["amino_acid_water_adjustment_l"], 21.0)
        self.assertLess(adjusted_water["total_water_use_l"], base_water["total_water_use_l"])
        nutrient = base.packets["water_nutrient_recovery_packet"].payload
        self.assertGreater(nutrient["recovered_n_kg"], 0.0)

    def test_l2_credit_remains_lagged_from_treatment_output(self) -> None:
        calibration = load_calibration()
        calibration["water"]["amino_acid_policy_active_default"]["value"] = False
        ctx = DairyFarmModel(scenario(days=2, land_cropland_ha=1.0), calibration).run()
        first_water = ctx.state["water_history"][0]
        second_feed = ctx.daily_records[1]

        expected_credit = first_water["treated_water_l"] * calibration["water"][
            "water_loop_fresh_water_offset_fraction"
        ]["value"]
        self.assertEqual(ctx.daily_records[0]["water_loop_offset_l"], 0.0)
        self.assertAlmostEqual(second_feed["water_loop_offset_l"], expected_credit)


if __name__ == "__main__":
    unittest.main()
