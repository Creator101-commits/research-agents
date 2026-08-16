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
        self.assertIn('id="parameters-content"', INDEX)
        self.assertIn("loadCalibration", API)
        self.assertIn("renderParameters", APP)
        self.assertIn('data-parameter-key', APP)
        self.assertIn("calibration_overrides", APP)
        self.assertIn("parameterDraft", STATE)
        self.assertIn("parameter-search", APP)
        self.assertIn("parameter-reset-all", APP)
        self.assertNotIn("genetics.selection_intensity", APP)
        self.assertIn("parameter-editor", CSS)

    def test_parameter_editor_keeps_validation_and_metadata_in_python_contract(self) -> None:
        self.assertIn("valid_range", APP)
        self.assertIn("assumption", APP)
        self.assertIn("source", APP)
        self.assertIn("description", APP)
        self.assertIn("Fix calibration values", APP)


if __name__ == "__main__":
    unittest.main()
