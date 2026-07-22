from __future__ import annotations

from copy import deepcopy
import unittest

from dairy_abm.config import load_calibration
from dairy_abm.core import ConfigError
from dairy_abm.model import DairyFarmModel


def scenario(**overrides):
    base = {
        "name": "resource-reporting",
        "start_date": "2026-01-01",
        "days": 1,
        "seed": 2,
        "herd_size": 10,
        "land_cropland_ha": 0,
    }
    base.update(overrides)
    return base


class ResourceReportingAgentsTest(unittest.TestCase):
    def test_manure_routes_conserve_cow_manure_output(self) -> None:
        ctx = DairyFarmModel(scenario(herd_size=3), load_calibration()).run()
        cow = ctx.packets["cow_daily_packet"].payload
        manure = ctx.packets["manure_packet"].payload
        routed = manure["digester_kg"] + manure["compost_kg"] + manure["storage_kg"]
        self.assertAlmostEqual(cow["manure_kg"], routed)
        self.assertGreater(manure["biogas_ch4_m3"], 0)
        self.assertGreater(manure["nutrient_return_kg"], 0)

    def test_energy_uses_blueprint_kwh_per_ton_feedstock_anchor(self) -> None:
        calibration = load_calibration()
        ctx = DairyFarmModel(scenario(herd_size=2), calibration).run()
        manure = ctx.packets["manure_packet"].payload
        energy = ctx.packets["energy_packet"].payload
        gross_expected = manure["digester_kg"] / 1000.0 * 85.73
        net_expected = gross_expected * (1.0 - calibration["energy"]["parasitic_load_fraction"]["value"])
        self.assertAlmostEqual(energy["gross_kwh"], gross_expected)
        self.assertAlmostEqual(energy["net_kwh"], net_expected)

    def test_water_accounts_for_saving_anchor_and_recovery(self) -> None:
        ctx = DairyFarmModel(scenario(herd_size=1), load_calibration()).run()
        water = ctx.packets["water_packet"].payload
        self.assertEqual(water["water_saving_l"], 21.0)
        self.assertGreater(water["gross_water_l"], water["net_water_l"])
        self.assertGreaterEqual(water["net_water_l"], 0)

    def test_environment_avoids_double_counting_digested_ch4(self) -> None:
        ctx = DairyFarmModel(scenario(herd_size=4), load_calibration()).run()
        cow = ctx.packets["cow_daily_packet"].payload
        manure = ctx.packets["manure_packet"].payload
        environment = ctx.packets["environment_packet"].payload
        self.assertEqual(environment["enteric_ch4_kg"], cow["enteric_ch4_kg"])
        self.assertEqual(environment["manure_ch4_kg"], manure["storage_ch4_kg"])
        self.assertLessEqual(environment["net_kg_co2e"], environment["gross_kg_co2e"])
        self.assertGreaterEqual(environment["circularity_score"], 0)
        self.assertLessEqual(environment["circularity_score"], 1)

    def test_manager_profit_balances_revenue_and_costs(self) -> None:
        ctx = DairyFarmModel(scenario(herd_size=5), load_calibration()).run()
        manager = ctx.packets["manager_packet"].payload
        self.assertAlmostEqual(manager["profit"], manager["total_revenue"] - manager["total_cost"])
        self.assertIn(
            manager["recommendation"],
            {"maintain_current_policy", "review_cost_structure", "review_health_protocol"},
        )

    def test_month_end_reports_emit_environment_and_manager_rows(self) -> None:
        ctx = DairyFarmModel(scenario(start_date="2026-01-30", days=2, herd_size=2), load_calibration()).run()
        reports = {(row["month"], row["report"]) for row in ctx.monthly_records}
        self.assertIn(("2026-01", "environment"), reports)
        self.assertIn(("2026-01", "farm_manager"), reports)

    def test_invalid_runtime_manure_routes_are_rejected(self) -> None:
        calibration = deepcopy(load_calibration())
        calibration["manure"]["storage_route_fraction"]["value"] = 0.25
        with self.assertRaises(ConfigError):
            DairyFarmModel(scenario(), calibration).run()


if __name__ == "__main__":
    unittest.main()
