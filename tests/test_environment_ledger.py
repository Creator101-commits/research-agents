from __future__ import annotations

from copy import deepcopy
import unittest

from dairy_abm.config import load_calibration
from dairy_abm.model import DairyFarmModel


def scenario(**overrides):
    base = {
        "name": "environment-ledger",
        "start_date": "2026-01-30",
        "days": 2,
        "seed": 19,
        "herd_size": 8,
        "land_cropland_ha": 2,
    }
    base.update(overrides)
    return base


class EnvironmentLedgerTest(unittest.TestCase):
    def test_ledger_records_source_period_units_and_avoided_streams(self) -> None:
        ctx = DairyFarmModel(scenario(), load_calibration()).run()
        environment = ctx.packets["environment_packet"].payload
        streams = environment["environmental_streams"]

        self.assertTrue(streams)
        self.assertEqual({stream["period"] for stream in streams}, {"daily"})
        self.assertEqual({stream["unit"] for stream in streams}, {"kg CO2e"})
        self.assertTrue(all(stream["source"] and stream["stream_id"] for stream in streams))
        self.assertIn("energy_grid_displacement", {stream["stream_id"] for stream in streams})
        self.assertIn("fertilizer_substitution", {stream["stream_id"] for stream in streams})
        self.assertEqual(
            len(ctx.state["environment_ledger"]),
            scenario()["days"] * len(streams),
        )

    def test_fertilizer_and_grid_offsets_are_explicit_and_net_is_unclamped(self) -> None:
        calibration = load_calibration()
        ctx = DairyFarmModel(scenario(), calibration).run()
        environment = ctx.packets["environment_packet"].payload
        feed = ctx.packets["feed_crop_packet"].payload
        energy = ctx.packets["energy_packet"].payload

        fertilizer_factor = calibration["environment"]["fertilizer_n_kg_co2e_per_kg_n"]["value"]
        self.assertAlmostEqual(
            environment["fertilizer_offset_kg_co2e"],
            feed["recycled_n_used_kg"] * fertilizer_factor,
        )
        self.assertAlmostEqual(environment["energy_offset_kg_co2e"], energy["grid_offset_kg_co2e"])
        self.assertAlmostEqual(
            environment["net_kg_co2e"],
            environment["gross_kg_co2e"] - environment["avoided_kg_co2e"],
        )

    def test_zero_production_has_null_intensities_and_logs_anomaly(self) -> None:
        ctx = DairyFarmModel(scenario(herd_size=0, days=1), load_calibration()).run()
        environment = ctx.packets["environment_packet"].payload

        self.assertIsNone(environment["kg_co2e_per_l_milk"])
        self.assertIsNone(environment["kg_co2e_per_kg_milk_protein"])
        self.assertTrue(
            any(event["message"] == "environment intensity denominator is zero" for event in ctx.events.events)
        )

    def test_grid_offset_can_make_net_carbon_negative(self) -> None:
        calibration = deepcopy(load_calibration())
        calibration["energy"]["grid_offset_kg_co2e_per_kwh"]["value"] = 10000.0
        ctx = DairyFarmModel(scenario(days=1), calibration).run()
        environment = ctx.packets["environment_packet"].payload

        self.assertLess(environment["net_kg_co2e"], 0.0)
        self.assertIn("net_negative", environment["outcome_tags"])
        self.assertTrue(
            any(event["message"] == "net carbon balance is negative" for event in ctx.events.events)
        )

    def test_monthly_and_cumulative_kpis_aggregate_daily_ledger(self) -> None:
        ctx = DairyFarmModel(scenario(), load_calibration()).run()
        environment = ctx.packets["environment_packet"].payload
        report = next(row for row in ctx.monthly_records if row["report"] == "environment")

        self.assertAlmostEqual(
            report["gross_kg_co2e"],
            sum(row["gross_kg_co2e"] for row in ctx.daily_records),
        )
        self.assertAlmostEqual(
            report["avoided_kg_co2e"],
            sum(row["avoided_kg_co2e"] for row in ctx.daily_records),
        )
        self.assertAlmostEqual(
            environment["cumulative_kpis"]["net_kg_co2e"],
            sum(row["net_kg_co2e"] for row in ctx.daily_records),
        )
        self.assertIn("circularity_indicators", environment)


if __name__ == "__main__":
    unittest.main()
