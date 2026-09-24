"""Parity tests: the Python economics port must reproduce the Cdairy workbook exactly."""

from __future__ import annotations

from pathlib import Path
import unittest

from dairy_abm.analysis.cdairy_economics import (
    INPUT_REFS,
    PRICE_CELLS,
    CdairyPrices,
    evaluate_year,
    per_cow_year_economics,
)
from dairy_abm.config import load_calibration
from dairy_abm.core import ConfigError, read_json

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = read_json(ROOT / "configs" / "reference_targets" / "cdairy_stats_mast.json")
REL_TOL = 1e-9


def _close(actual: float, expected: float) -> bool:
    return abs(actual - expected) <= REL_TOL * max(1.0, abs(expected))


class CdairyEconomicsParityTest(unittest.TestCase):
    def test_fixture_covers_all_strategies_and_years(self) -> None:
        self.assertEqual(set(FIXTURE["strategies"]), {"AIRAND", "AINM$", "AIMAST", "SSNM$", "ETNM$"})
        self.assertEqual(FIXTURE["years"], list(range(-4, 16)))
        for strategy in FIXTURE["strategies"].values():
            self.assertEqual(len(strategy["years"]), 20)
            self.assertEqual(set(strategy["years"][0]["inputs"]), set(INPUT_REFS))

    def test_every_workbook_row_matches_for_every_year_and_strategy(self) -> None:
        checked = 0
        for name, strategy in FIXTURE["strategies"].items():
            prices = CdairyPrices(strategy["prices"])
            for year in strategy["years"]:
                result = evaluate_year(year["inputs"], prices, year["year"] == 15)
                actual = {**result["economics"], **result["technical"]}
                for row, expected in year["expected"].items():
                    if expected is None:
                        continue
                    with self.subTest(strategy=name, year=year["year"], row=row):
                        self.assertIn(row, actual)
                        self.assertTrue(_close(actual[row], expected), f"{actual[row]} != {expected}")
                    checked += 1
        self.assertGreater(checked, 5000)

    def test_table4_year15_matches_workbook_summary(self) -> None:
        for name, strategy in FIXTURE["strategies"].items():
            final = strategy["years"][-1]
            table = evaluate_year(final["inputs"], CdairyPrices(strategy["prices"]), True)["table4"]
            for line, expected in strategy["table4_year15"].items():
                with self.subTest(strategy=name, line=line):
                    self.assertTrue(_close(table[line], expected), f"{table[line]} != {expected}")

    def test_airand_year15_headline_values(self) -> None:
        strategy = FIXTURE["strategies"]["AIRAND"]
        result = evaluate_year(strategy["years"][-1]["inputs"], CdairyPrices(strategy["prices"]), True)
        self.assertAlmostEqual(result["technical"]["milk_yield_kg_per_cow_year"], 12668.710786630883, places=6)
        self.assertAlmostEqual(result["technical"]["pregnancy_rate_35"], 0.36500341114778595, places=12)
        self.assertAlmostEqual(result["technical"]["days_open"], 110.8357783804445, places=9)
        self.assertAlmostEqual(result["technical"]["annual_cull_rate"], 0.36729202556841556, places=12)
        self.assertAlmostEqual(result["technical"]["mastitis_incidence"], 0.1733023749033755, places=12)
        self.assertAlmostEqual(result["technical"]["antibiotic_daily_doses"], 284.3, places=9)
        self.assertAlmostEqual(result["table4"]["total_costs"], 4216.787625321174, places=6)
        self.assertAlmostEqual(result["table4"]["profit"], 1541.3954411278155, places=6)

    def test_calibration_prices_equal_workbook_prices(self) -> None:
        calibration_prices = CdairyPrices.from_calibration(load_calibration())
        for name in PRICE_CELLS:
            with self.subTest(price=name):
                self.assertEqual(calibration_prices[name], FIXTURE["strategies"]["AIRAND"]["prices"][name])

    def test_missing_input_is_rejected(self) -> None:
        inputs = dict(FIXTURE["strategies"]["AIRAND"]["years"][-1]["inputs"])
        del inputs["milk_kg"]
        with self.assertRaisesRegex(ConfigError, "milk_kg"):
            per_cow_year_economics(inputs, CdairyPrices(FIXTURE["strategies"]["AIRAND"]["prices"]))


if __name__ == "__main__":
    unittest.main()
