"""Keep the dashboard's static formula reference tied to current model source."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.generate_formula_reference import build_reference


ROOT = Path(__file__).resolve().parents[1]


class FormulaReferenceTests(unittest.TestCase):
    def test_static_reference_matches_current_source(self) -> None:
        snapshot = json.loads((ROOT / "web/data/formulas_values.json").read_text())
        current = build_reference()
        self.assertEqual(snapshot, current)
        self.assertEqual(len(snapshot["daily_process"]), 15)
        self.assertEqual(snapshot["daily_process"][0]["name"], "Market")
        self.assertEqual(snapshot["daily_process"][-1]["name"], "Genetics intake")

    def test_every_calibration_entry_has_provenance(self) -> None:
        reference = build_reference()
        keys = [row["key"] for row in reference["calibration"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertGreater(len(keys), 300)
        for row in reference["calibration"]:
            for field in ("value", "unit", "valid_range", "source", "assumption", "description"):
                self.assertIn(field, row, row["key"])
        paths = {item["path"] for item in reference["files"]}
        self.assertIn("dairy_abm/model.py", paths)
        self.assertIn("dairy_abm/dashboard_conventional.py", paths)
        self.assertIn("web/js/dashboard.js", paths)
        self.assertTrue(any("EQUIPMENT_CATALOGUE" in row["scope"] for row in reference["frontend_literals"]))
        self.assertTrue(any("buildEquipROI" in row["scope"] for row in reference["frontend_calculations"]))

    def test_page_is_linked_from_dashboard(self) -> None:
        html = (ROOT / "web/index.html").read_text()
        self.assertIn('id="nav-formulas"', html)
        self.assertIn('id="section-formulas"', html)
        self.assertIn('/assets/js/formulas.js', html)


if __name__ == "__main__":
    unittest.main()
