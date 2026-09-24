"""The farm ledger reproduces the workbook herd economics and keeps loop items separate."""

from __future__ import annotations

import unittest

from dairy_abm.analysis.cdairy_economics import CdairyPrices, feed_cost_rows, loop_feed_saving
from dairy_abm.analysis.excel_parity import annual_excel_economics
from dairy_abm.config import load_calibration, value
from dairy_abm.dashboard_conventional import herd_summary
from dairy_abm.model import DairyFarmModel

LOOPS_OFF = {
    "l1_nutrient_loop_enabled": False,
    "l2_water_loop_enabled": False,
    "l3_energy_loop_enabled": False,
    "l4_byproduct_loop_enabled": False,
}


def _run(days: int, herd: int, seed: int, **scenario):
    base = {"start_date": "2026-01-01", "days": days, "herd_size": herd, "seed": seed,
            "land_cropland_ha": 80, "auto_environment_response": False}
    return DairyFarmModel({**base, **scenario}, load_calibration()).run()


class LedgerReconciliationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.off = _run(730, 60, 11, **LOOPS_OFF)
        cls.on = _run(730, 60, 11, enable_processor=True, enable_whey_processing=True)

    def test_loops_off_herd_economics_equal_workbook_formulas_each_year(self) -> None:
        complete = [row for row in annual_excel_economics(self.off) if row["complete_year"]]
        self.assertEqual(len(complete), 2)
        for row in complete:
            records = [r for r in self.off.daily_records if r["day"].startswith(str(row["year"]))]
            cows = row["inputs"]["present_cow_days"] / 365.0
            revenue = sum(r["herd_revenue"] for r in records) / cows
            cost = sum(r["herd_cost"] for r in records) / cows
            table4 = row["table4"]
            for observed, target in (
                (revenue, table4["total_revenues"]),
                (cost, table4["total_costs"]),
                (revenue - cost, table4["profit"]),
            ):
                self.assertLessEqual(abs(observed - target), 0.005 * abs(target))
            feed = sum(r["workbook_feed_cost"] for r in records) / cows
            self.assertAlmostEqual(feed, table4["feeding_cost"], places=6)
            # With every loop off nothing offsets feed, so the charged feed is the workbook row.
            self.assertAlmostEqual(sum(r["feed_cost"] for r in records) / cows, table4["feeding_cost"], places=6)

    def test_home_grown_feed_is_charged(self) -> None:
        purchased = sum(r["purchased_feed_kg_dm"] for r in self.off.daily_records)
        feed_cost = sum(r["feed_cost"] for r in self.off.daily_records)
        self.assertEqual(purchased, 0.0)
        self.assertGreater(feed_cost, 0.0)

    def test_profit_is_herd_profit_plus_listed_loop_lines(self) -> None:
        for ctx in (self.off, self.on):
            for record in ctx.daily_records:
                manager_profit = record["herd_revenue"] - record["herd_cost"] + record["loop_net"]
                self.assertAlmostEqual(record["profit"], manager_profit, places=6)
        lines = self.on.packets["manager_packet"].payload["loop_lines"]
        self.assertEqual(
            set(lines),
            {"electricity_value", "heat_value", "carbon_credit_value", "compost_revenue", "byproduct_revenue",
             "loop_feed_saving", "water_cost", "cooling_cost", "processing_energy_cost", "disease_cost"},
        )

    def test_processor_product_sales_stay_out_of_profit(self) -> None:
        processor = sum(r["processor_revenue_not_in_profit"] for r in self.on.daily_records)
        self.assertGreater(processor, 0.0)
        for record in self.on.daily_records:
            self.assertAlmostEqual(record["milk_revenue"], record["raw_milk_revenue"])

    def test_loop_feed_offsets_lower_feed_cost_at_workbook_prices(self) -> None:
        saving = sum(r["loop_feed_saving"] for r in self.on.daily_records)
        self.assertGreater(saving, 0.0)
        for record in self.on.daily_records:
            self.assertAlmostEqual(record["feed_cost"], record["workbook_feed_cost"] - record["loop_feed_saving"])
        prices = CdairyPrices.from_calibration(load_calibration())
        wet, dry = feed_cost_rows(100.0, 20.0, prices)
        self.assertAlmostEqual(loop_feed_saving(100.0, 20.0, 12.0, prices), (wet + dry) * 0.1)
        self.assertAlmostEqual(loop_feed_saving(100.0, 20.0, 500.0, prices), wet + dry)

    def test_l3_off_has_no_digester_and_l1_on_composts(self) -> None:
        l3_off = _run(30, 20, 3, l3_energy_loop_enabled=False)
        self.assertEqual(sum(r["biogas_volume_m3"] for r in l3_off.daily_records), 0.0)
        self.assertEqual(sum(r["digestate_kg"] for r in l3_off.daily_records), 0.0)
        self.assertGreater(sum(r["compost_product_kg"] for r in l3_off.daily_records), 0.0)
        self.assertGreater(sum(r["compost_n_kg"] for r in l3_off.daily_records), 0.0)
        self.assertEqual(sum(r["compost_product_kg"] for r in self.off.daily_records), 0.0)
        self.assertEqual(sum(r["biogas_volume_m3"] for r in self.off.daily_records), 0.0)


class RationAndDiseaseLineTest(unittest.TestCase):
    def test_every_cow_gets_the_herd_coverage_of_its_own_need(self) -> None:
        ctx = _run(20, 30, 2)
        feed = ctx.packets["feed_crop_packet"].payload
        coverages = {r["coverage_fraction"] for r in feed["per_cow_rations"].values()}
        self.assertEqual(coverages, {min(1.0, feed["ration_coverage_fraction"])})

    def test_disease_line_excludes_lost_milk_value(self) -> None:
        calibration = load_calibration()
        calibration["disease"]["lameness_daily_probability"]["value"] = 0.2
        calibration["disease"]["recovery_daily_probability"]["value"] = 0.01
        scenario = {"start_date": "2026-01-01", "days": 20, "herd_size": 30, "seed": 4,
                    "disease_milk_loss_value_per_cow_day": 5.0}
        ctx = DairyFarmModel(scenario, calibration).run()
        disease = ctx.packets["disease_state_packet"].payload
        manager = ctx.packets["manager_packet"].payload
        self.assertGreater(disease["milk_loss_cost"], 0.0)
        self.assertAlmostEqual(manager["disease_cost"], disease["outbreak_economic_cost"] - disease["milk_loss_cost"])


class HerdSummaryAndBodyWeightTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ctx = _run(5 * 365, 40, 5)

    def test_calvings_include_first_calving_and_peak_factor_is_used(self) -> None:
        rows = {row["modelId"]: row for row in herd_summary(self.ctx)}
        cows = {cow["id"]: cow for cow in self.ctx.state["cows"]}
        first_calvers = [key for key in rows if any(
            e.get("event") == "first_calving" for e in cows[key].get("reproduction_history", []))]
        self.assertTrue(first_calvers)
        for key in first_calvers:
            events = cows[key]["reproduction_history"]
            self.assertEqual(rows[key]["calvings"], sum(e.get("event") in ("calving", "first_calving") for e in events))
        for key, row in rows.items():
            self.assertEqual(row["peakFactor"], cows[key]["peak_factor"])

    def test_mature_cow_body_weight_stays_plausible_over_five_years(self) -> None:
        # Plausible band: NASEM Eq 2-1 support data in the Blueprint (Cow 8.1), 624 +/- 2 x 80.2 kg.
        low, high = 624 - 2 * 80.2, 624 + 2 * 80.2
        mature_parity = int(value(self.ctx.calibration, "herd.mature_parity"))
        mature = [c for c in self.ctx.state["cows"] if int(c.get("parity", 0)) >= mature_parity and c.get("body_weight_history")]
        self.assertGreater(len(mature), 10)
        for cow in mature:
            self.assertGreaterEqual(cow["body_weight_kg"], low, cow["id"])
            self.assertLessEqual(cow["body_weight_kg"], high, cow["id"])
        adults = [c for c in self.ctx.state["cows"] if c.get("alive", True) and int(c.get("parity", 0)) >= 1]
        mean_bcs = sum(c["body_condition_score"] for c in adults) / len(adults)
        self.assertGreater(mean_bcs, 2.5)
        self.assertLess(mean_bcs, 3.5)


if __name__ == "__main__":
    unittest.main()
