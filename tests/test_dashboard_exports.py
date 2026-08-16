"""Contract tests for official dashboard exports."""

from __future__ import annotations

import io
import json
from pathlib import Path
from random import Random
import unittest
import zipfile

from dairy_abm.config import load_calibration
from dairy_abm.core import EventLog, SimulationContext
from dairy_abm.dashboard import serialize_dashboard_run
from dairy_abm.model import DairyFarmModel
from webapp import RUN_CACHE, _export_file, _run_simulation


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
INDEX = (WEB / "index.html").read_text(encoding="utf-8")
APP = (WEB / "js" / "app.js").read_text(encoding="utf-8")
CSS = "\n".join(path.read_text(encoding="utf-8") for path in (WEB / "styles").glob("*.css"))


class DashboardExportsTests(unittest.TestCase):
    def test_manifest_lists_only_official_write_reports_artifacts(self) -> None:
        scenario = {"name": "export-audit", "days": 1, "seed": 7, "herd_size": 2}
        ctx = DairyFarmModel(scenario, load_calibration()).run()
        payload = serialize_dashboard_run(ctx, "export01", 0.2)
        manifest = payload["exports"]

        self.assertTrue(manifest["available"])
        self.assertEqual(manifest["source"], "dairy_abm.reports.write_reports")
        self.assertEqual(
            {artifact["filename"] for artifact in manifest["artifacts"]},
            {
                "summary.json",
                "daily.csv",
                "schedule.csv",
                "monthly.csv",
                "annual.csv",
                "calibration_inventory.json",
                "export01-output.zip",
            },
        )
        self.assertTrue(
            all(
                artifact["endpoint"] == "/api/export/export01"
                if artifact["id"] == "zip"
                else artifact["endpoint"].startswith("/api/export/export01/")
                for artifact in manifest["artifacts"]
            )
        )

    def test_official_artifacts_are_generated_by_write_reports(self) -> None:
        RUN_CACHE.clear()
        result = _run_simulation({"days": 2, "seed": 12, "herd_size": 2})
        entry = RUN_CACHE[result["id"]]
        expected = {
            "summary.json",
            "daily.csv",
            "schedule.csv",
            "monthly.csv",
            "annual.csv",
            "calibration_inventory.json",
        }

        for filename in expected:
            content = _export_file(entry, filename)
            self.assertIsInstance(content, bytes)
            if filename == "calibration_inventory.json":
                self.assertIsInstance(json.loads(content), list)
            elif filename.endswith(".json"):
                self.assertIsInstance(json.loads(content), dict)
            elif filename == "daily.csv":
                self.assertGreaterEqual(len(content.decode().splitlines()), 3)
            else:
                content.decode()
        summary = json.loads(_export_file(entry, "summary.json"))
        self.assertIn("report_contract", summary)
        self.assertIn("daily.csv", zipfile.ZipFile(io.BytesIO(_export_file(entry, "export.zip"))).namelist())

    def test_missing_context_has_no_export_manifest(self) -> None:
        ctx = SimulationContext(
            scenario={"name": "empty"}, calibration={}, rng=Random(1), events=EventLog()
        )
        payload = serialize_dashboard_run(ctx, "export02", 0.0)
        self.assertFalse(payload["exports"]["available"])
        self.assertEqual(payload["exports"]["artifacts"], [])

    def test_export_page_is_routed_and_read_only(self) -> None:
        self.assertIn('id="exports-content"', INDEX)
        self.assertIn("renderExports", APP)
        self.assertIn("data.exports", APP)
        self.assertIn("write_reports", APP)
        self.assertIn("export-center", CSS)


if __name__ == "__main__":
    unittest.main()
