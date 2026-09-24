"""Contract tests for the dynamic calibration parameter editor."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
INDEX = (WEB / "index.html").read_text(encoding="utf-8")
APP = (WEB / "js" / "app.js").read_text(encoding="utf-8")
API = (WEB / "js" / "api.js").read_text(encoding="utf-8")
STATE = (WEB / "js" / "state.js").read_text(encoding="utf-8")
CSS = "\n".join(path.read_text(encoding="utf-8") for path in (WEB / "styles").glob("*.css"))


class DashboardParametersTests(unittest.TestCase):
    def test_parameter_page_is_generated_from_calibration_inventory(self) -> None:
        ui = (WEB / "js" / "dashboard.js").read_text(encoding="utf-8")
        self.assertIn('id="section-params"', INDEX)
        self.assertIn('id="section-animal"', INDEX)
        self.assertIn("/api/conventional/params", ui)
        self.assertIn("Not used by the Python model", ui)
        self.assertIn("modelConfig()", ui)

    def test_parameter_editor_keeps_validation_and_metadata_in_python_contract(self) -> None:
        self.assertIn("valid_range", APP)
        self.assertIn("assumption", APP)
        self.assertIn("source", APP)
        self.assertIn("description", APP)
        self.assertIn("Fix calibration values", APP)

    def test_scenario_switch_uses_backend_defaults_and_clears_drafts(self) -> None:
        self.assertIn("scenario_defaults", APP)
        self.assertIn("applyScenarioDefaults", APP)
        self.assertIn("state.parameterDraft = {}", APP)
        self.assertIn("reference calibration", APP)
        self.assertIn("calibrationScenario", STATE)
        self.assertIn("warningCounts = new Map()", APP)


if __name__ == "__main__":
    unittest.main()
