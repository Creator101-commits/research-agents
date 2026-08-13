from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "docs" / "dashboard_metric_map.md"
ALLOWED_STATUSES = {
    "EXISTING",
    "BACKEND_AGGREGATE",
    "BACKEND_EXPOSE",
    "MODEL_CHANGE",
    "UNSUPPORTED",
}
METRIC_HEADERS = {"UI Metric", "Chart series"}


class DashboardMetricMapTests(unittest.TestCase):
    def test_metric_tables_have_the_required_schema(self):
        lines = MAP_PATH.read_text(encoding="utf-8").splitlines()
        in_metric_table = False
        metric_rows = 0

        for line in lines:
            if not line.startswith("|"):
                in_metric_table = False
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if cells and cells[0] in METRIC_HEADERS and len(cells) == 8:
                self.assertEqual(cells[6], "Status")
                in_metric_table = True
                continue
            if not in_metric_table or line.startswith("|---"):
                continue
            self.assertEqual(len(cells), 8, line)
            self.assertIn(cells[6].strip("`"), ALLOWED_STATUSES, line)
            metric_rows += 1

        self.assertGreater(metric_rows, 100)

    def test_map_covers_the_phase_one_boundaries(self):
        text = MAP_PATH.read_text(encoding="utf-8")
        for section in (
            "## 1. Run metadata and model details",
            "## 4. Circular loops",
            "## 5. Cow performance",
            "## 6. Environment and audit ledger",
            "## 7. Economics",
            "## 8. Equipment ROI",
            "## 9. Parameters and configuration",
            "## 10. Exports and comparisons",
        ):
            self.assertIn(section, text)
        self.assertIn("`MODEL_CHANGE`", text)
        self.assertIn("`UNSUPPORTED`", text)
        self.assertIn("ctx.daily_records", text)
        self.assertIn("REPORT_CONTRACT", text)


if __name__ == "__main__":
    unittest.main()
