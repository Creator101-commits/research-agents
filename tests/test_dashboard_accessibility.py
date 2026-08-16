"""Static contracts for the final responsive and accessibility pass."""

from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
INDEX = (WEB / "index.html").read_text(encoding="utf-8")
LAYOUT = (WEB / "styles" / "layout.css").read_text(encoding="utf-8")
BASE = (WEB / "styles" / "base.css").read_text(encoding="utf-8")
COMPONENTS = (WEB / "styles" / "components.css").read_text(encoding="utf-8")
PAGES = (WEB / "styles" / "pages.css").read_text(encoding="utf-8")
APP = (WEB / "js" / "app.js").read_text(encoding="utf-8")
CHARTS = (WEB / "js" / "charts.js").read_text(encoding="utf-8")


class DashboardAccessibilityTests(unittest.TestCase):
    def test_sidebar_is_collapsible_and_navigation_has_current_state(self) -> None:
        self.assertIn('id="sidebar"', INDEX)
        self.assertIn('id="rail-toggle"', INDEX)
        self.assertIn('aria-controls="sidebar"', INDEX)
        self.assertIn('aria-expanded="true"', INDEX)
        self.assertIn("is-rail-collapsed", LAYOUT)
        self.assertIn("aria-current", APP)
        self.assertIn("toggleRail", APP)

    def test_focus_loading_empty_and_reduced_motion_contracts_exist(self) -> None:
        self.assertIn(":focus-visible", BASE)
        self.assertIn('aria-busy', APP)
        self.assertIn('role="status"', INDEX)
        self.assertIn('role="alert"', INDEX)
        self.assertIn("prefers-reduced-motion", BASE + COMPONENTS + PAGES)
        self.assertIn(".empty-state", COMPONENTS)

    def test_tables_and_charts_remain_readable_on_small_screens(self) -> None:
        self.assertGreaterEqual(len(re.findall(r"overflow-x:\s*auto", COMPONENTS + PAGES)), 6)
        self.assertIn('role="img"', CHARTS)
        self.assertIn("min-width: 520px", COMPONENTS + PAGES)
        self.assertIn('unit: "kg CO2e"', CHARTS)

    def test_run_controls_have_explicit_labels_and_units(self) -> None:
        for control_id in ("scenario", "days", "start-date", "seed", "herd"):
            self.assertRegex(INDEX, rf'<label[^>]*for="{control_id}"')
        self.assertIn('aria-labelledby="systems-label"', INDEX)
        self.assertIn('id="systems-label"', INDEX)
        self.assertIn("Profit (currency)", APP)
        self.assertIn("CO2e/L (kg CO2e/L)", APP)


if __name__ == "__main__":
    unittest.main()
