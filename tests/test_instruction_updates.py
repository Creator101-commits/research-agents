from __future__ import annotations

import csv
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from dairy_abm.analysis.npv import analyze_outputs, npv
from dairy_abm.config import load_calibration
from dairy_abm.model import DairyFarmModel


class InstructionUpdatesTest(unittest.TestCase):
    def scenario(self, **overrides):
        scenario = {
            "name": "instruction-updates",
            "start_date": "2026-06-01",
            "days": 1,
            "seed": 4,
            "herd_size": 4,
            "land_cropland_ha": 0,
        }
        scenario.update(overrides)
        return scenario

    def test_energy_headline_uses_feedstock_formula_and_keeps_biogas_diagnostic(self) -> None:
        calibration = load_calibration()
        ctx = DairyFarmModel(self.scenario(), calibration).run()
        energy = ctx.packets["energy_packet"].payload
        expected_gross = energy["feedstock_tons"] * calibration["energy"]["kwh_per_ton_feedstock"]["value"]
        self.assertAlmostEqual(energy["gross_kwh"], expected_gross)
        self.assertAlmostEqual(energy["biogas_derived_kwh_estimate"], energy["biogas_gross_kwh"])
        self.assertAlmostEqual(
            energy["electricity_generated_kwh"],
            expected_gross * (1.0 - calibration["energy"]["parasitic_load_fraction"]["value"]),
        )

    def test_cow_enteric_ch4_uses_calibrated_me_reference(self) -> None:
        calibration = load_calibration()
        ctx = DairyFarmModel(self.scenario(), calibration).run()
        cow = ctx.state["cows"][0]
        ration = ctx.packets["feed_crop_packet"].payload["per_cow_rations"][cow["id"]]
        expected = (
            calibration["cow"]["enteric_ch4_kg_per_cow_day"]["value"]
            * cow["dmi_history"][0]
            / calibration["cow"]["base_dmi_kg_per_cow_day"]["value"]
            * calibration["cow"]["ch4_me_reference_constant"]["value"]
            / max(1.0, ration["me_mj_per_kg_dm"])
        )
        self.assertAlmostEqual(cow["ch4_history"][0], expected)
    def test_amino_acid_flags_and_absolute_cp_points_toggle(self) -> None:
        calibration = load_calibration()
        active = DairyFarmModel(self.scenario(), calibration).run().packets["feed_crop_packet"].payload
        inactive = DairyFarmModel(self.scenario(amino_acid_policy_active=False), calibration).run().packets["feed_crop_packet"].payload
        self.assertTrue(active["nitrogen_excretion_reduced_flag"])
        self.assertTrue(active["rp_lys_flag"])
        self.assertTrue(active["rp_met_flag"])
        self.assertEqual(active["amino_acid_cp_reduction_points"], 0.02)
        self.assertFalse(inactive["nitrogen_excretion_reduced_flag"])
        self.assertFalse(inactive["rp_lys_flag"])
        self.assertFalse(inactive["rp_met_flag"])
        self.assertEqual(inactive["amino_acid_cp_reduction_points"], 0.0)

    def test_me_varies_by_production_system_and_season(self) -> None:
        calibration = load_calibration()
        values = {
            system: DairyFarmModel(self.scenario(production_system=system), calibration)
            .run()
            .packets["feed_crop_packet"]
            .payload["ration_me_mj_per_kg_dm"]
            for system in ("arid_grazing", "humid_temperate", "high_intensity")
        }
        self.assertLess(values["arid_grazing"], values["humid_temperate"])
        self.assertLess(values["humid_temperate"], values["high_intensity"])

        january = DairyFarmModel(self.scenario(start_date="2026-01-01"), calibration).run()
        july = DairyFarmModel(self.scenario(start_date="2026-07-01"), calibration).run()
        self.assertNotEqual(
            january.packets["feed_crop_packet"].payload["ration_me_mj_per_kg_dm"],
            july.packets["feed_crop_packet"].payload["ration_me_mj_per_kg_dm"],
        )

    def test_water_recovery_derives_phosphorus_and_potassium(self) -> None:
        calibration = deepcopy(load_calibration())
        calibration["water"]["nutrient_recovery_enabled"]["value"] = True
        calibration["water"]["nutrient_recovery_kg_n_per_l"]["value"] = 0.01
        ctx = DairyFarmModel(self.scenario(amino_acid_policy_active=False), calibration).run()
        water = ctx.packets["water_packet"].payload
        self.assertGreater(water["recovered_n_kg"], 0.0)
        self.assertAlmostEqual(water["recovered_p_kg"], water["recovered_n_kg"] * 0.2)
        self.assertAlmostEqual(water["recovered_k_kg"], water["recovered_n_kg"] * 0.2)

    def test_environment_publishes_leap_tags(self) -> None:
        payload = DairyFarmModel(self.scenario(), load_calibration()).run().packets["environment_packet"].payload
        self.assertEqual(payload["kpi_leap_tags"]["gross_kg_co2e"], "result")
        self.assertEqual(payload["kpi_leap_tags"]["ICirc"], "practice")
        self.assertEqual(payload["kpi_leap_tags"]["cycle_count"], "outcome")

    def test_solar_per_cow_mode_is_opt_in(self) -> None:
        calibration = load_calibration()
        flat = DairyFarmModel(self.scenario(solar_capacity_kw=2.0), calibration).run()
        sized = DairyFarmModel(self.scenario(solar_sized_per_cow=True), calibration).run()
        self.assertEqual(flat.packets["energy_packet"].payload["solar_capacity_kw"], 2.0)
        self.assertEqual(sized.packets["energy_packet"].payload["solar_capacity_kw"], 0.4)

    def test_npv_analysis_reads_daily_profit_and_equipment_summary(self) -> None:
        self.assertAlmostEqual(npv([100.0, 100.0], 0.1), 190.9090909090909)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            daily = root / "daily.csv"
            with daily.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["day", "profit"])
                writer.writeheader()
                writer.writerows([{"day": "2026-01-01", "profit": "100"}, {"day": "2026-01-02", "profit": "50"}])
            summary = root / "summary.json"
            summary.write_text(
                json.dumps(
                    {
                        "latest_packets": {
                            "manager_packet": {
                                "payload": {
                                    "equipment_roi": {
                                        "manure_system": {"annual_benefit": 365.0}
                                    }
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            result = analyze_outputs(daily, summary_path=summary, discount_rate=0.05)
            self.assertEqual(result["farm_cash_flows"], [150.0])
            self.assertAlmostEqual(result["equipment_npvs"]["manure_system"], 365.0)


if __name__ == "__main__":
    unittest.main()
