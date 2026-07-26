from __future__ import annotations

import unittest

from dairy_abm.config import load_calibration
from dairy_abm.model import DairyFarmModel


def scenario(**overrides):
    base = {
        "name": "manure-pathways",
        "start_date": "2026-01-01",
        "days": 2,
        "seed": 23,
        "herd_size": 2,
        "land_cropland_ha": 0,
        "enable_land_agent": False,
    }
    base.update(overrides)
    return base


class ManurePathwaysTest(unittest.TestCase):
    def test_collection_routes_and_nitrogen_streams_are_conserved_and_nonnegative(self) -> None:
        ctx = DairyFarmModel(scenario(), load_calibration()).run()
        manure = ctx.packets["manure_packet"].payload

        self.assertAlmostEqual(
            manure["manure_kg"],
            manure["collected_manure_kg"] + manure["uncollected_manure_kg"],
        )
        self.assertAlmostEqual(
            manure["collected_manure_kg"],
            manure["digester_kg"] + manure["compost_kg"] + manure["storage_input_kg"],
        )
        self.assertAlmostEqual(manure["manure_n_total_kg"], manure["urinary_n_kg"] + manure["fecal_n_kg"])
        self.assertGreaterEqual(manure["field_n2o_precursor_kg_n"], 0.0)
        self.assertGreaterEqual(manure["digestate_n_kg"], 0.0)
        self.assertGreaterEqual(manure["compost_n_kg"], 0.0)
        self.assertGreaterEqual(manure["digestate_p_kg"], 0.0)
        self.assertGreaterEqual(manure["compost_k_kg"], 0.0)

    def test_storage_capacity_clamps_inventory_and_reports_overflow(self) -> None:
        calibration = load_calibration()
        calibration["manure"]["digester_route_fraction"]["value"] = 0.0
        calibration["manure"]["compost_route_fraction"]["value"] = 0.0
        calibration["manure"]["storage_route_fraction"]["value"] = 1.0
        calibration["manure"]["storage_capacity_kg"]["value"] = 50.0
        ctx = DairyFarmModel(scenario(days=1, herd_size=1), calibration).run()
        manure = ctx.packets["manure_packet"].payload

        self.assertEqual(manure["stored_manure_inventory_kg"], 50.0)
        self.assertTrue(manure["storage_overflow_flag"])
        self.assertGreater(manure["storage_overflow_kg"], 0.0)

    def test_digester_capacity_and_safety_gate_limit_cofeed_assembly(self) -> None:
        calibration = load_calibration()
        calibration["manure"]["digester_route_fraction"]["value"] = 1.0
        calibration["manure"]["compost_route_fraction"]["value"] = 0.0
        calibration["manure"]["storage_route_fraction"]["value"] = 0.0
        unsafe = DairyFarmModel(
            scenario(
                days=1,
                herd_size=1,
                digester_capacity_pct=50.0,
                grass_cofeed_kg=100.0,
                food_waste_cofeed_kg=100.0,
            ),
            calibration,
        ).run()
        safe = DairyFarmModel(
            scenario(
                days=1,
                herd_size=1,
                digester_capacity_pct=50.0,
                grass_cofeed_kg=100.0,
                food_waste_cofeed_kg=100.0,
                cofeed_safety_approved=True,
            ),
            load_calibration(),
        ).run()
        unsafe_manure = unsafe.packets["manure_packet"].payload
        safe_manure = safe.packets["manure_packet"].payload

        self.assertAlmostEqual(unsafe_manure["digester_kg"], unsafe_manure["manure_kg"] * 0.5)
        self.assertGreater(unsafe_manure["storage_input_kg"], 0.0)
        self.assertEqual(unsafe_manure["grass_cofeed_kg"], 0.0)
        self.assertEqual(unsafe_manure["food_waste_cofeed_kg"], 0.0)
        self.assertEqual(unsafe_manure["manure_route_alert"], "cofeed_safety_rejected")
        self.assertGreater(safe_manure["digester_feedstock_kg"], safe_manure["digester_kg"])
        self.assertTrue(safe_manure["digester_feedstock_feasible"])

    def test_thermochemical_packet_is_mass_separate_and_environment_uses_storage_ch4_once(self) -> None:
        calibration = load_calibration()
        calibration["manure"]["thermochemical_route_fraction"]["value"] = 0.25
        ctx = DairyFarmModel(
            scenario(days=1, thermochemical_route_active=True), calibration
        ).run()
        manure = ctx.packets["manure_packet"].payload
        thermo = ctx.packets["thermochemical_manure_packet"].payload
        environment = ctx.packets["environment_packet"].payload

        self.assertGreater(thermo["thermochemical_manure_kg"], 0.0)
        self.assertAlmostEqual(
            manure["collected_manure_kg"],
            manure["digester_kg"]
            + manure["thermochemical_manure_kg"]
            + manure["compost_kg"]
            + manure["storage_input_kg"],
        )
        self.assertEqual(environment["manure_ch4_kg"], manure["storage_ch4_kg"])


if __name__ == "__main__":
    unittest.main()
