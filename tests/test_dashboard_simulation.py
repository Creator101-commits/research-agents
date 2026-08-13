"""Contract tests for the real-model simulation page."""

from __future__ import annotations

from pathlib import Path
import unittest

from webapp import _run_simulation


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
INDEX = (WEB / "index.html").read_text(encoding="utf-8")
APP = (WEB / "js" / "app.js").read_text(encoding="utf-8")


class DashboardSimulationTests(unittest.TestCase):
    def test_simulation_form_exposes_only_supported_run_controls(self) -> None:
        for element_id in ("scenario", "days", "start-date", "seed", "herd", "go"):
            self.assertIn(f'id="{element_id}"', INDEX)
        self.assertIn('type="date"', INDEX)
        self.assertIn('type="submit"', INDEX)
        self.assertIn("Duration", INDEX)
        self.assertIn("Start date", INDEX)
        for key in (
            "l1_nutrient_loop_enabled",
            "l2_water_loop_enabled",
            "l3_energy_loop_enabled",
            "l4_byproduct_loop_enabled",
            "enable_processor",
            "enable_whey_processing",
            "enable_land_agent",
        ):
            self.assertIn(key, APP)

    def test_form_sends_start_date_and_verified_switches_to_run_api(self) -> None:
        self.assertIn('start_date: $("start-date").value', APP)
        self.assertIn('fetch("/api/run"', (WEB / "js" / "api.js").read_text(encoding="utf-8"))
        self.assertIn('document.querySelectorAll("#switches input")', APP)
        self.assertIn('setLoading(true)', APP)
        self.assertIn('setLoading(false)', APP)

    def test_start_date_controls_the_authoritative_model_clock(self) -> None:
        result = _run_simulation(
            {
                "scenario": "baseline.json",
                "days": 2,
                "start_date": "2026-01-15",
                "seed": 8,
                "herd_size": 2,
            }
        )
        self.assertEqual([row["day"] for row in result["daily"]], ["2026-01-15", "2026-01-16"])


if __name__ == "__main__":
    unittest.main()
