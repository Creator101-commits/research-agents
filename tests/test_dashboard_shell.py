"""Contract tests for the client-side dashboard shell."""

from __future__ import annotations

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
INDEX = (WEB / "index.html").read_text(encoding="utf-8")
APP = (WEB / "js" / "app.js").read_text(encoding="utf-8")
ROUTER = (WEB / "js" / "router.js").read_text(encoding="utf-8")
STATE = (WEB / "js" / "state.js").read_text(encoding="utf-8")
CSS = "\n".join(path.read_text(encoding="utf-8") for path in (WEB / "styles").glob("*.css"))


PAGES = {
    "overview": "Overview",
    "simulation": "Simulation",
    "charts": "Charts",
    "loops": "Circular Loops",
    "comparison": "Scenario Comparison",
    "cows": "Cow Performance",
    "environment": "Environment",
    "economics": "Economics",
    "roi": "Equipment ROI",
    "parameters": "Parameters",
    "model-details": "Model Details",
    "exports": "Export",
}


class DashboardShellTests(unittest.TestCase):
    def test_final_navigation_and_shell_regions_exist(self) -> None:
        expected = ("overview", "charts", "loops", "compare", "roi", "ranking", "params", "animal")
        for page in expected:
            self.assertIn(f'id="nav-{page}"', INDEX)
            self.assertIn(f'id="section-{page}"', INDEX)
        self.assertNotIn('id="farmLanding"', INDEX)
        self.assertIn('id="mainApp"', INDEX)

    def test_router_is_hash_based_and_state_has_shell_fields(self) -> None:
        self.assertIn("export const PAGES", ROUTER)
        self.assertIn("hashchange", ROUTER)
        self.assertIn("navigate", ROUTER)
        self.assertIn("activePage", STATE)
        self.assertIn("currentRun", STATE)
        self.assertIn("selectedPeriod", STATE)
        self.assertIn("filters", STATE)
        self.assertIn("initRouter", APP)
        self.assertIn("renderShell", APP)

    def test_shell_has_feedback_and_responsive_styles(self) -> None:
        self.assertIn('id="statusBadge"', INDEX)
        self.assertIn('data-theme-toggle', INDEX)
        self.assertIn('@media (max-width: 900px)', CSS)
        self.assertIn('--color-primary', CSS)

    def test_frontend_javascript_is_syntactically_valid(self) -> None:
        if not __import__("shutil").which("node"):
            self.skipTest("Node is required for JavaScript syntax validation")
        for script in sorted((WEB / "js").glob("*.js")):
            with self.subTest(script=script.name):
                result = subprocess.run(
                    ["node", "--check", str(script)],
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
