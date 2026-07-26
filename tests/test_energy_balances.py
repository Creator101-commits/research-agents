from __future__ import annotations

import unittest

from dairy_abm.config import load_calibration
from dairy_abm.model import DairyFarmModel


def scenario(**overrides):
    base = {
        "name": "energy-balances",
        "start_date": "2026-01-01",
        "days": 1,
        "seed": 31,
        "herd_size": 4,
        "land_cropland_ha": 0,
        "enable_land_agent": False,
    }
    base.update(overrides)
    return base


class EnergyBalancesTest(unittest.TestCase):
    def test_energy_displacement_is_capped_at_demand_and_surplus_is_separate(self) -> None:
        ctx = DairyFarmModel(scenario(farm_energy_demand_kwh_per_day=0.01), load_calibration()).run()
        energy = ctx.packets["energy_packet"].payload

        self.assertEqual(energy["displaced_grid_energy_kwh"], 0.01)
        self.assertAlmostEqual(energy["surplus_energy_kwh"], energy["net_kwh"] - 0.01)
        self.assertEqual(energy["energy_self_sufficiency_pct"], 100.0)
        self.assertAlmostEqual(
            energy["energy_value"], energy["displaced_grid_energy_kwh"] * energy["electricity_price_per_kwh"]
        )
        self.assertAlmostEqual(
            energy["grid_offset_kg_co2e"],
            energy["displaced_grid_energy_kwh"] * energy["grid_offset_kg_co2e_per_kwh"],
        )

    def test_energy_self_sufficiency_tracks_partial_demand_coverage(self) -> None:
        ctx = DairyFarmModel(scenario(farm_energy_demand_kwh_per_day=1000.0), load_calibration()).run()
        energy = ctx.packets["energy_packet"].payload

        self.assertEqual(energy["surplus_energy_kwh"], 0.0)
        self.assertEqual(energy["displaced_grid_energy_kwh"], energy["net_kwh"])
        self.assertGreater(energy["energy_self_sufficiency_pct"], 0.0)
        self.assertLess(energy["energy_self_sufficiency_pct"], 100.0)

    def test_heat_is_unavailable_without_a_calibrated_conversion_and_available_when_set(self) -> None:
        missing_heat = DairyFarmModel(scenario(), load_calibration()).run()
        calibrated = load_calibration()
        calibrated["energy"]["heat_mj_per_kwh"]["value"] = 3.6
        with_heat = DairyFarmModel(scenario(), calibrated).run()

        self.assertIsNone(missing_heat.packets["energy_packet"].payload["heat_generated_mj"])
        self.assertEqual(missing_heat.packets["energy_packet"].confidence, "low")
        self.assertAlmostEqual(
            with_heat.packets["energy_packet"].payload["heat_generated_mj"],
            with_heat.packets["energy_packet"].payload["net_kwh"] * 3.6,
        )

    def test_thermochemical_input_is_separate_and_l3_toggle_zeros_energy_balance(self) -> None:
        calibrated = load_calibration()
        calibrated["manure"]["thermochemical_route_fraction"]["value"] = 0.5
        calibrated["manure"]["thermochemical_syngas_kwh_per_kg"]["value"] = 0.2
        thermochemical = DairyFarmModel(
            scenario(thermochemical_route_active=True), calibrated
        ).run()
        disabled = DairyFarmModel(
            scenario(thermochemical_route_active=True, l3_energy_loop_enabled=False), calibrated
        ).run()
        thermo_energy = thermochemical.packets["energy_packet"].payload
        disabled_energy = disabled.packets["energy_packet"].payload

        self.assertGreater(thermo_energy["thermochemical_input_kwh"], 0.0)
        self.assertGreater(thermo_energy["net_kwh"], 0.0)
        self.assertEqual(disabled_energy["net_kwh"], 0.0)
        self.assertEqual(disabled_energy["displaced_grid_energy_kwh"], 0.0)
        self.assertEqual(disabled_energy["energy_value"], 0.0)

    def test_energy_uses_total_safety_approved_cofeed_mass(self) -> None:
        ctx = DairyFarmModel(
            scenario(
                cofeed_safety_approved=True,
                grass_cofeed_kg=100.0,
                food_waste_cofeed_kg=100.0,
            ),
            load_calibration(),
        ).run()
        manure = ctx.packets["manure_packet"].payload
        energy = ctx.packets["energy_packet"].payload

        self.assertGreater(manure["digester_feedstock_kg"], manure["digester_kg"])
        self.assertAlmostEqual(energy["feedstock_tons"], manure["digester_feedstock_kg"] / 1000.0)


if __name__ == "__main__":
    unittest.main()
