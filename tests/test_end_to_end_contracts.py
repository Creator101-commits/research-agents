from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from dairy_abm.config import load_calibration
from dairy_abm.model import DairyFarmModel
from dairy_abm.reports import write_reports


def scenario(**overrides):
    base = {
        "name": "end-to-end-contracts",
        "start_date": "2026-01-30",
        "days": 2,
        "seed": 41,
        "herd_size": 6,
        "land_cropland_ha": 2.0,
    }
    base.update(overrides)
    return base


class EndToEndContractsTest(unittest.TestCase):
    def test_observed_per_litre_product_price_reaches_processor_without_wholesale_conversion(self) -> None:
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "market.csv"
            csv_path.write_text(
                "date,milk_price_per_l,price_per_l_milk_cheese,wholesale_cheddar_price_usd_lb\n"
                "2026-01-30,0.50,2.00,1.75\n"
                "2026-01-31,0.50,2.00,1.75\n",
                encoding="utf-8",
            )
            ctx = DairyFarmModel(
                scenario(
                    enable_processor=True,
                    enable_whey_processing=True,
                    market_mode="observed",
                    market_data_csv=str(csv_path),
                ),
                load_calibration(),
            ).run()

        market = ctx.packets["market_price_packet"].payload
        processor = ctx.packets["processor_packet"].payload
        self.assertEqual(market["wholesale_cheddar_price_usd_lb"], 1.75)
        self.assertEqual(processor["product_prices_per_l"]["cheese"], 2.0)
        self.assertAlmostEqual(
            processor["product_revenue"],
            sum(
                processor["product_streams_l"][name] * processor["product_prices_per_l"][name]
                for name in processor["product_streams_l"]
            ),
        )

    def test_mass_energy_and_economic_balances_hold_across_scenario_matrix(self) -> None:
        scenarios = [
            scenario(),
            scenario(enable_processor=True, enable_whey_processing=True),
            scenario(enable_land_agent=True, land_seasonal_availability={"1": 0.5}),
            scenario(l1_nutrient_loop_enabled=False, l2_water_loop_enabled=False, l3_energy_loop_enabled=False),
        ]
        for matrix_scenario in scenarios:
            with self.subTest(scenario=matrix_scenario):
                ctx = DairyFarmModel(matrix_scenario, load_calibration()).run()
                manure = ctx.packets["manure_packet"].payload
                energy = ctx.packets["energy_packet"].payload
                manager = ctx.packets["manager_packet"].payload

                self.assertAlmostEqual(
                    manure["manure_kg"],
                    manure["collected_manure_kg"] + manure["uncollected_manure_kg"],
                )
                self.assertLessEqual(energy["displaced_grid_energy_kwh"], energy["net_kwh"])
                self.assertAlmostEqual(
                    energy["energy_value"],
                    energy["displaced_grid_energy_kwh"] * energy["electricity_price_per_kwh"],
                )
                self.assertAlmostEqual(manager["profit"], manager["total_revenue"] - manager["total_cost"])
                self.assertTrue(all(row["purchased_feed_kg_dm"] >= 0.0 for row in ctx.daily_records))

    def test_observed_replay_and_report_contract_are_deterministic(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "market.csv"
            csv_path.write_text(
                "year,frequency,milk_price_per_l,feed_cost_per_kg_dm\n2026,annual,0.55,0.38\n",
                encoding="utf-8",
            )
            run_scenario = scenario(market_mode="observed", market_data_csv=str(csv_path))
            first = DairyFarmModel(run_scenario, load_calibration()).run()
            second = DairyFarmModel(run_scenario, load_calibration()).run()
            first_output = root / "first"
            second_output = root / "second"
            write_reports(first_output, first)
            write_reports(second_output, second)

            self.assertEqual(
                (first_output / "daily.csv").read_bytes(),
                (second_output / "daily.csv").read_bytes(),
            )
            summary = (first_output / "summary.json").read_text(encoding="utf-8")
            self.assertIn('"report_contract"', summary)
            self.assertIn('"kg_co2e_per_l_milk"', summary)
            self.assertIn('"confidence"', summary)


if __name__ == "__main__":
    unittest.main()
