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
        for page_id, label in PAGES.items():
            self.assertIn(f'data-page="{page_id}"', INDEX)
            self.assertIn(label, INDEX)

        for element_id in (
            "app-shell",
            "main-nav",
            "page-content",
            "run-status",
            "scenario-label",
            "active-run-meta",
            "loading-state",
            "error-banner",
            "warning-banner",
        ):
            self.assertIn(f'id="{element_id}"', INDEX)

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
        self.assertIn("aria-live", INDEX)
        self.assertIn("is-loading", CSS)
        self.assertIn("banner", CSS)
        self.assertIn("@media (max-width: 900px)", CSS)
        self.assertIn("@media (max-width: 600px)", CSS)

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
