"""Every connected Conventional dashboard control changes the Python run output."""

from __future__ import annotations

import unittest

from dairy_abm.config import load_calibration
from dairy_abm.core import read_json
from dairy_abm.dashboard_conventional import (
    DERIVED_PARAMETERS,
    SUPPORTED_PARAMETERS,
    default_config,
    resolve_inputs,
    serialize_run,
)
from dairy_abm.model import DairyFarmModel
from webapp import SCENARIO_DIR

BASE_CFG = {"number_of_cows": 30, "simulation_years": 240 / 365, "random_seed": 3}

# Changed values chosen inside each control's target range.
CHANGED = {
    "number_of_cows": 36,
    "simulation_years": 250 / 365,
    "random_seed": 4,
    "land_cropland_ha": 20,
    "wood_b": 0.3,
    "wood_c": 0.004,
    "peak_milk_L_first_parity": 30,
    "peak_milk_L_mature": 40,
    "mature_parity": 5,
    "cow_peak_std_fraction": 0.25,
    "dry_period_days": 90,
    "max_parity": 2,
    "annual_involuntary_cull_fraction": 0.3,
    "bodyweight_first_parity_kg": 450,
    "bodyweight_mature_kg": 800,
    "illness_milk_penalty_fraction": 0.6,
    "illness_duration_days_mean": 12,
    "feed_cost_per_kg": 0.45,
    "water_cost_per_L": 0.003,
    "electricity_price_currency_per_kWh": 0.25,
    "compost_value_currency_per_kg": 0.1,
    "compost_kg_per_kg_manure_to_compost": 0.6,
    "grid_avoided_kg_co2e_per_kWh": 0.8,
    "water_loop_fresh_water_offset_fraction": 0.3,
    "fraction_milk_to_processor": 0.5,
    "fraction_whey_to_animal_feed_loop": 0.9,
    "fraction_milk_to_cheese": 0.6,
    "fraction_milk_to_butter": 0.4,
    "fraction_milk_to_yogurt": 0.3,
    "fraction_milk_to_fresh": 0.3,
    "fraction_milk_to_functional": 0.3,
    "price_per_L_milk_cheese": 0.9,
    "price_per_L_milk_butter": 0.6,
    "price_per_L_milk_yogurt": 0.75,
    "price_per_L_milk_fresh": 0.45,
    "price_per_L_milk_functional": 1.2,
    "separator_solid_fraction": 0.6,
    "biogas_m3_per_kg_manure_to_digester": 0.04,
    "solar_electricity_kWh_per_cow_per_day": 1.5,
    "methane_reduction_factor": 0.7,
    "manure_kg_per_kg_dmi": 2.0,
}


def _fingerprint(cfg: dict) -> dict:
    scenario = read_json(SCENARIO_DIR / "baseline.json")
    scenario, calibration, served = resolve_inputs({"cfg": cfg}, scenario, load_calibration())
    ctx = DairyFarmModel(scenario, calibration).run()
    totals = serialize_run(ctx, served, include_series=False)["totals"]
    return {key: round(val, 9) for key, val in totals.items() if isinstance(val, (int, float))}


class ConnectedParameterEffectTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = _fingerprint(BASE_CFG)

    def test_every_connected_control_has_a_changed_value(self) -> None:
        self.assertEqual(set(CHANGED), set(SUPPORTED_PARAMETERS))

    def test_each_connected_control_changes_the_run(self) -> None:
        for key in SUPPORTED_PARAMETERS:
            with self.subTest(key=key):
                changed = _fingerprint({**BASE_CFG, key: CHANGED[key]})
                differing = [name for name in self.base if self.base[name] != changed.get(name)]
                self.assertTrue(differing, f"{key} did not change any output")

    def test_derived_controls_round_trip_their_defaults(self) -> None:
        scenario = read_json(SCENARIO_DIR / "baseline.json")
        calibration = load_calibration()
        defaults = default_config(scenario, calibration)
        for key in DERIVED_PARAMETERS:
            if key == "solar_electricity_kWh_per_cow_per_day":
                continue
            with self.subTest(key=key):
                _scenario, applied, served = resolve_inputs({"cfg": {key: defaults[key]}}, scenario, calibration)
                self.assertAlmostEqual(served[key], defaults[key])
        self.assertEqual(defaults["solar_electricity_kWh_per_cow_per_day"], 0.0)


if __name__ == "__main__":
    unittest.main()
