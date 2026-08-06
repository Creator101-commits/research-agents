"""Regression tests for the local web run desk."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import threading
import unittest
import zipfile
from http.client import RemoteDisconnected
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from webapp import (
    DISPLAY_FIELDS,
    PAGE,
    RUN_CACHE,
    Handler,
    _export_zip,
    _run_simulation,
)
from http.server import ThreadingHTTPServer


ROOT = Path(__file__).resolve().parents[1]
GRAPH_FIELDS = {
    "day",
    "milk_l",
    "profit",
    "net_kg_co2e",
    "energy_self_sufficiency_pct",
    "freshwater_withdrawal_l",
    "input_circularity",
    "output_circularity",
    "sustainability_score_0_100",
    "active_disease_cases",
}


class WebAppSimulationTests(unittest.TestCase):
    """Test the model adapter and the in-memory export contract."""

    def setUp(self):
        RUN_CACHE.clear()

    def test_display_fields_are_unique_and_include_graph_fields(self):
        keys = [key for key, _ in DISPLAY_FIELDS]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(GRAPH_FIELDS.issubset(keys))
        self.assertEqual(keys[0], "day")

    def test_run_returns_daily_rows_and_consistent_metrics(self):
        result = _run_simulation(
            {
                "scenario": "baseline.json",
                "days": 2,
                "seed": 12,
                "herd_size": 5,
            }
        )

        self.assertRegex(result["id"], r"^[0-9a-f]{8}$")
        self.assertEqual(result["days"], 2)
        self.assertEqual(result["seed"], 12)
        self.assertEqual(result["herd_size"], 5)
        self.assertEqual(len(result["daily"]), 2)
        self.assertTrue(GRAPH_FIELDS.issubset(result["daily"][0]))
        self.assertAlmostEqual(
            result["metrics"]["milk"],
            sum(row["milk_l"] for row in result["daily"]),
        )
        self.assertAlmostEqual(
            result["metrics"]["energy_avg"],
            sum(row["energy_self_sufficiency_pct"] for row in result["daily"]) / 2,
        )
        self.assertIn(result["id"], RUN_CACHE)

    def test_same_seed_is_deterministic(self):
        params = {"scenario": "baseline.json", "days": 3, "seed": 42, "herd_size": 5}
        first = _run_simulation(params)
        second = _run_simulation(params)
        self.assertEqual(first["daily"], second["daily"])
        self.assertEqual(first["metrics"], second["metrics"])

    def test_scenario_overrides_reach_the_model(self):
        result = _run_simulation(
            {
                "scenario": "baseline.json",
                "days": 1,
                "seed": 7,
                "herd_size": 4,
                "enable_processor": True,
                "enable_whey_processing": True,
                "enable_land_agent": True,
                "l1_nutrient_loop_enabled": False,
                "l2_water_loop_enabled": False,
                "l3_energy_loop_enabled": False,
                "l4_byproduct_loop_enabled": False,
            }
        )
        self.assertEqual(result["days"], 1)
        self.assertEqual(result["herd_size"], 4)
        self.assertEqual(len(result["daily"]), 1)

    def test_invalid_days_are_rejected(self):
        for value in (True, False, 0, -1, 3651, 1.5, "2"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "days must be"):
                    _run_simulation({"days": value})

    def test_scenario_path_must_stay_inside_scenario_directory(self):
        with self.assertRaisesRegex(ValueError, "must live under"):
            _run_simulation({"scenario": "../README.md", "days": 1})

    def test_run_cache_keeps_only_the_last_ten_runs(self):
        for index in range(10):
            RUN_CACHE[str(index)] = object()
        result = _run_simulation({"days": 1, "seed": 3, "herd_size": 2})
        self.assertEqual(len(RUN_CACHE), 10)
        self.assertNotIn("0", RUN_CACHE)
        self.assertIn(result["id"], RUN_CACHE)

    def test_export_zip_contains_all_report_files_and_rows(self):
        result = _run_simulation({"days": 2, "seed": 4, "herd_size": 3})
        archive_bytes = _export_zip(RUN_CACHE[result["id"]])

        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            expected = {
                "annual.csv",
                "calibration_inventory.json",
                "daily.csv",
                "monthly.csv",
                "schedule.csv",
                "summary.json",
            }
            self.assertEqual(set(archive.namelist()), expected)
            daily = archive.read("daily.csv").decode()
            self.assertEqual(len(daily.strip().splitlines()), 3)
            summary = json.loads(archive.read("summary.json"))
            self.assertIn("report_contract", summary)


class WebAppHTTPTests(unittest.TestCase):
    """Exercise the real HTTP handler on an ephemeral local port."""

    @classmethod
    def setUpClass(cls):
        RUN_CACHE.clear()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        RUN_CACHE.clear()

    def request(self, method, path, payload=None):
        body = None if payload is None else json.dumps(payload).encode()
        request = Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={"Content-Type": "application/json"} if body is not None else {},
        )
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, dict(response.headers), response.read()
        except HTTPError as error:
            with error:
                return error.code, dict(error.headers), error.read()
        except (URLError, RemoteDisconnected) as error:  # pragma: no cover - useful failure detail
            self.fail(f"request failed: {error}")

    def test_get_page_and_scenario_defaults(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn(b"Dairy Farm ABM", body)
        self.assertIn(b"Download graphs (PNG)", body)

        status, _, body = self.request("GET", "/api/scenario")
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertIn("baseline.json", data["scenarios"])
        self.assertEqual(data["defaults"]["name"], "baseline")

    def test_unknown_get_and_missing_export_return_json_404(self):
        status, headers, body = self.request("GET", "/missing")
        self.assertEqual(status, 404)
        self.assertIn("application/json", headers["Content-Type"])
        self.assertEqual(json.loads(body)["error"], "not found")

        status, _, body = self.request("GET", "/api/export/not-a-run")
        self.assertEqual(status, 404)
        self.assertIn("too old", json.loads(body)["error"])


    def test_post_unknown_route_returns_404(self):
        status, _, body = self.request("POST", "/not-api-run", {})
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(body)["error"], "not found")

    def test_post_run_returns_ok_payload_and_export_download(self):
        status, headers, body = self.request(
            "POST", "/api/run", {"days": 1, "seed": 8, "herd_size": 3}
        )
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["daily"]), 1)
        self.assertIn(data["id"], RUN_CACHE)

        status, headers, body = self.request("GET", f"/api/export/{data['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/zip")
        self.assertIn("attachment", headers["Content-Disposition"])
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            self.assertIn("daily.csv", archive.namelist())

    def test_malformed_post_has_400_response(self):
        request = Request(
            self.base_url + "/api/run",
            data=b"not-json",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=10)
        error = raised.exception
        try:
            self.assertEqual(error.code, 400)
            self.assertIn("bad request", json.loads(error.read())["error"])
        finally:
            error.close()
    def test_invalid_post_has_500_response_with_model_error(self):
        status, _, body = self.request("POST", "/api/run", {"days": 0})
        self.assertEqual(status, 500)
        self.assertIn("days must be", json.loads(body)["error"])


class WebAppClientTests(unittest.TestCase):
    """Run the dependency-free browser regression harness when Node is available."""

    @unittest.skipUnless(shutil.which("node"), "Node is required for client-side tests")
    def test_client_behaviors(self):
        harness = ROOT / "tests" / "webapp_client_harness.cjs"
        completed = subprocess.run(
            ["node", str(harness), str(ROOT / "webapp.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=20,
        )
        if completed.returncode:
            self.fail(f"client harness failed:\n{completed.stdout}\n{completed.stderr}")
        self.assertIn("webapp client tests passed", completed.stdout)


class WebAppVisualContractTests(unittest.TestCase):
    def test_chart_layout_palette_and_controls_are_present(self):
        self.assertIn("const CH = { W:520, H:244, L:76, R:18, T:48, B:40 };", PAGE)
        self.assertIn('<text x="10" y="21" class="ttl">', PAGE)
        self.assertIn('class="axislabel"', PAGE)
        self.assertIn("const barX = i => L + ((i + 0.5)/n)*plotW;", PAGE)
        self.assertIn("Math.min(48, Math.max(2, plotW/n*0.62))", PAGE)
        self.assertIn('data-d="30"', PAGE)
        self.assertIn('data-d="365"', PAGE)
        self.assertIn('const TABS = [["ledger","Ledger"],["graphs","Graphs"]];', PAGE)
        self.assertIn('const PERIODS = [["daily","Daily"],["monthly","Monthly"],["yearly","Yearly"]];', PAGE)
        self.assertIn('const dl = state.view==="graphs" && state.data', PAGE)
        self.assertIn('id="dlgraphs"', PAGE)
        self.assertIn('id="report-content"', PAGE)
        self.assertIn('id="back-workspace"', PAGE)
        self.assertIn('position: static; align-self: start', PAGE)
        self.assertIn('grid-template-columns: 260px minmax(0, 1fr)', PAGE)
        self.assertIn('class="confighead"', PAGE)
        self.assertIn('class="empty-state"', PAGE)
        self.assertIn('class="graph-lead"', PAGE)
        self.assertIn('button#go { width: 100%', PAGE)
        self.assertIn('grid-template-columns: repeat(2, minmax(0, 1fr))', PAGE)
    def test_palette_has_no_cream_tones(self):
        for color in ("#d7cdb4", "#c3b795", "#6f6756", "#fffef8", "#23201a"):
            self.assertNotIn(color, PAGE)
        self.assertIn("--paper:  #ffffff;", PAGE)
        self.assertIn("--accent: #b42318", PAGE)
        self.assertIn("--sage:   #3f6b4f", PAGE)

    def test_page_javascript_has_valid_syntax(self):
        if not shutil.which("node"):
            self.skipTest("Node is required for JavaScript syntax validation")
        script = PAGE.split("<script>", 1)[1].split("</script>", 1)[0]
        completed = subprocess.run(
            ["node", "--check"], input=script, text=True, capture_output=True
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
