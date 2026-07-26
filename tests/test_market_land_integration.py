from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from dairy_abm.config import load_calibration
from dairy_abm.model import DairyFarmModel


def scenario(**overrides):
    base = {
        "name": "market-land-integration",
        "start_date": "2026-01-01",
        "days": 1,
        "seed": 23,
        "herd_size": 4,
        "land_cropland_ha": 4.0,
    }
    base.update(overrides)
    return base


class MarketLandIntegrationTest(unittest.TestCase):
    def test_static_market_packet_keeps_config_provenance(self) -> None:
        ctx = DairyFarmModel(scenario(), load_calibration()).run()
        market = ctx.packets["market_price_packet"]

        self.assertEqual(market.quality, "static_config")
        self.assertEqual(market.payload["market_mode"], "static")
        self.assertEqual(market.payload["source"], "static_config")
        self.assertEqual(market.payload["market_packet_quality_flag"], "ok")

    def test_observed_market_replay_carries_missing_values_and_synchronizes_consumers(self) -> None:
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "market.csv"
            csv_path.write_text(
                "date,milk_price_per_l,feed_cost_per_kg_dm,electricity_price_per_kwh,wholesale_cheddar_price_usd_lb\n"
                "2026-01-01,0.50,0.40,0.10,1.80\n"
                "2026-01-02,NA,,0.12,2.00\n",
                encoding="utf-8",
            )
            ctx = DairyFarmModel(
                scenario(days=2, market_mode="observed", market_data_csv=str(csv_path)),
                load_calibration(),
            ).run()

        first, second = ctx.state["market_history"]
        self.assertEqual(first["source"], "observed_csv")
        self.assertEqual(second["market_packet_quality_flag"], "low_confidence")
        self.assertAlmostEqual(second["milk_price_per_l"], 0.50)
        self.assertAlmostEqual(second["feed_cost_per_kg_dm"], 0.40)
        self.assertAlmostEqual(second["electricity_price_per_kwh"], 0.12)
        self.assertAlmostEqual(second["wholesale_cheddar_price_usd_lb"], 2.00)
        self.assertTrue(any(event["source"] == "market" for event in ctx.events.events))
        self.assertAlmostEqual(ctx.daily_records[1]["milk_price_per_l"], second["milk_price_per_l"])
        self.assertAlmostEqual(
            ctx.packets["feed_crop_packet"].payload["feed_cost_per_kg_dm"],
            second["feed_cost_per_kg_dm"],
        )
        self.assertAlmostEqual(
            ctx.packets["energy_packet"].payload["electricity_price_per_kwh"],
            second["electricity_price_per_kwh"],
        )

    def test_observed_annual_row_falls_back_for_matching_year(self) -> None:
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "annual.csv"
            csv_path.write_text(
                "year,frequency,milk_price_per_l\n2026,annual,0.61\n",
                encoding="utf-8",
            )
            ctx = DairyFarmModel(
                scenario(market_mode="observed", market_data_csv=str(csv_path)),
                load_calibration(),
            ).run()

        market = ctx.packets["market_price_packet"].payload
        self.assertAlmostEqual(market["milk_price_per_l"], 0.61)
        self.assertEqual(market["period_selection"], "annual_fallback")

    def test_negative_observed_price_is_clamped_and_logged(self) -> None:
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "negative.csv"
            csv_path.write_text("date,milk_price_per_l\n2026-01-01,-1.0\n", encoding="utf-8")
            ctx = DairyFarmModel(
                scenario(market_mode="observed", market_data_csv=str(csv_path)),
                load_calibration(),
            ).run()

        self.assertEqual(ctx.packets["market_price_packet"].payload["milk_price_per_l"], 0.0)
        self.assertTrue(any(event["message"] == "negative observed market price was clamped" for event in ctx.events.events))

    def test_land_publishes_configured_seasonal_availability_and_environmental_handoffs(self) -> None:
        ctx = DairyFarmModel(
            scenario(
                start_date="2026-06-01",
                enable_land_agent=True,
                land_cropland_ha=4.0,
                land_pasture_ha=3.0,
                land_seasonal_availability={"6": 0.5},
                land_grazing_enabled=True,
                soil_carbon_sequestration_index=1.4,
            ),
            load_calibration(),
        ).run()

        land = ctx.packets["land_packet"].payload
        grazing = ctx.packets["grazing_access_packet"].payload
        soil = ctx.packets["soil_carbon_packet"].payload
        environment = ctx.packets["environment_packet"].payload
        feed = ctx.packets["feed_crop_packet"].payload
        self.assertEqual(land["seasonal_availability_source"], "scenario")
        self.assertAlmostEqual(land["cropland_available_ha"], 2.0)
        self.assertAlmostEqual(land["pasture_available_ha"], 1.5)
        self.assertTrue(grazing["enabled"])
        self.assertAlmostEqual(grazing["pasture_available_ha"], 1.5)
        self.assertEqual(soil["soil_carbon_sequestration_index"], 1.4)
        self.assertEqual(environment["soil_carbon_context"], soil)
        self.assertAlmostEqual(feed["cropland_ha"], 2.0)

    def test_land_passes_through_full_area_and_disables_grazing_without_a_seasonal_rule(self) -> None:
        ctx = DairyFarmModel(
            scenario(enable_land_agent=True, land_pasture_ha=3.0), load_calibration()
        ).run()

        land = ctx.packets["land_packet"].payload
        grazing = ctx.packets["grazing_access_packet"].payload
        self.assertEqual(land["seasonal_availability_source"], "not_configured")
        self.assertEqual(land["cropland_available_ha"], land["cropland_ha"])
        self.assertFalse(grazing["enabled"])


if __name__ == "__main__":
    unittest.main()
