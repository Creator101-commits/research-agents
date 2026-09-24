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
        ui = (WEB / "js" / "dashboard.js").read_text(encoding="utf-8")
        for page in ("overview", "charts", "loops", "compare", "roi", "ranking", "params", "animal"):
            self.assertIn(f'id="nav-{page}"', INDEX)
            self.assertIn(f'id="section-{page}"', INDEX)
        self.assertIn("function navigate(id)", ui)

    def test_focus_loading_empty_and_reduced_motion_contracts_exist(self) -> None:
        css = (WEB / "styles" / "dashboard.css").read_text(encoding="utf-8")
        self.assertIn(":focus-visible", css)
        self.assertIn(".empty-state", css)
        self.assertIn('id="statusBadge"', INDEX)
        self.assertIn('aria-label="Toggle theme"', INDEX)

    def test_tables_and_charts_remain_readable_on_small_screens(self) -> None:
        self.assertGreaterEqual(len(re.findall(r"overflow-x:\s*auto", COMPONENTS + PAGES)), 6)
        self.assertIn('role="img"', CHARTS)
        self.assertIn("min-width: 520px", COMPONENTS + PAGES)
        self.assertIn('unit: "kg CO2e"', CHARTS)

    def test_run_controls_have_explicit_labels_and_units(self) -> None:
        ui = (WEB / "js" / "dashboard.js").read_text(encoding="utf-8")
        self.assertIn('id="runBtn"', INDEX)
        self.assertIn('id="exportBtn"', INDEX)
        self.assertIn('id="kpiGrid"', INDEX)
        self.assertIn("kg/kg", ui)
        self.assertIn("supportedParams", ui)


if __name__ == "__main__":
    unittest.main()
