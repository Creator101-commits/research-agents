"""HTTP contract tests for the Phase 3 dashboard API."""

from __future__ import annotations

from http.client import RemoteDisconnected
import json
import threading
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from http.server import ThreadingHTTPServer

from webapp import Handler, RUN_CACHE


class DashboardAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        RUN_CACHE.clear()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        RUN_CACHE.clear()

    def request(self, method: str, path: str, payload: object = None) -> tuple[int, dict, bytes]:
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
        except (URLError, RemoteDisconnected) as error:  # pragma: no cover - failure detail
            self.fail(f"request failed: {error}")

    def post_run(self, seed: int) -> dict:
        status, _, body = self.request("POST", "/api/run", {"days": 1, "seed": seed, "herd_size": 2})
        self.assertEqual(status, 200)
        return json.loads(body)

    def test_config_endpoint_returns_backend_capabilities_and_contract(self) -> None:
        status, headers, body = self.request("GET", "/api/config")
        config = json.loads(body)

        self.assertEqual(status, 200)
        self.assertIn("application/json", headers["Content-Type"])
        self.assertEqual(config["default_scenario"]["name"], "baseline")
        self.assertIn("baseline.json", config["scenarios"])
        self.assertFalse(config["feature_flags"]["enable_processor"])
        self.assertTrue(config["feature_flags"]["l1_nutrient_loop_enabled"])
        self.assertEqual(config["limits"], {"min_days": 1, "max_days": 3650, "max_cached_runs": 10})
        self.assertIn("daily", config["report_contract"])
        self.assertTrue(config["ui_capabilities"]["run"])
        self.assertNotIn("calibration", config)

    def test_calibration_endpoint_returns_inventory_not_raw_nested_config(self) -> None:
        status, _, body = self.request("GET", "/api/calibration")
        data = json.loads(body)

        self.assertEqual(status, 200)
        self.assertGreater(len(data["parameters"]), 0)
        row = data["parameters"][0]
        self.assertEqual(
            set(row),
            {"key", "agent", "default", "unit", "source", "assumption", "description", "valid_range"},
        )
        self.assertNotIn("calibration", data)
        self.assertNotIn("value", row)

    def test_get_run_returns_same_serialized_payload_as_post_run(self) -> None:
        posted = self.post_run(21)
        run_id = posted["run_id"]
        status, _, body = self.request("GET", f"/api/run/{run_id}")
        fetched = json.loads(body)

        self.assertEqual(status, 200)
        self.assertEqual(fetched["run_id"], run_id)
        self.assertEqual(fetched["meta"]["event_count"], posted["events"])
        self.assertEqual(fetched["series"]["daily"], posted["daily"])
        self.assertEqual(fetched["summary"], posted["summary"])
        self.assertEqual(fetched["metrics"], posted["metrics"])

    def test_run_accepts_nested_scenario_and_calibration_overrides(self) -> None:
        status, _, body = self.request(
            "POST",
            "/api/run",
            {
                "scenario": "baseline.json",
                "scenario_overrides": {"days": 1, "seed": 44, "herd_size": 2},
                "calibration_overrides": {"genetics.selection_intensity": 0.4},
            },
        )
        result = json.loads(body)

        self.assertEqual(status, 200)
        self.assertEqual(result["meta"]["days"], 1)
        self.assertEqual(result["meta"]["seed"], 44)
        self.assertEqual(result["meta"]["calibration_override_count"], 1)
        self.assertEqual(
            result["meta"]["calibration_overrides"],
            {"genetics.selection_intensity": 0.4},
        )

        status, _, body = self.request(
            "POST",
            "/api/run",
            {"calibration_overrides": {"genetics.selection_intensity": 2}},
        )
        self.assertEqual(status, 400)
        self.assertIn("valid range", json.loads(body)["error"])


    def test_compare_returns_cached_runs_and_python_deltas(self) -> None:
        first = self.post_run(31)
        second = self.post_run(32)
        status, _, body = self.request(
            "POST",
            "/api/compare",
            {"run_ids": [first["run_id"], second["run_id"]], "labels": {first["run_id"]: "Base"}},
        )
        comparison = json.loads(body)

        self.assertEqual(status, 200)
        self.assertTrue(comparison["ok"])
        self.assertEqual([run["run_id"] for run in comparison["runs"]], [first["run_id"], second["run_id"]])
        self.assertEqual(comparison["runs"][0]["label"], "Base")
        milk_delta = comparison["deltas"][0]["metrics"]["milk"]
        expected = second["summary"]["milk"]["value"] - first["summary"]["milk"]["value"]
        self.assertAlmostEqual(milk_delta["absolute"], expected)
        self.assertEqual(milk_delta["unit"], "L")

    def test_new_routes_return_structured_errors_for_missing_runs(self) -> None:
        status, _, body = self.request("GET", "/api/run/missing-run")
        self.assertEqual(status, 404)
        self.assertIn("run not found", json.loads(body)["error"])

        status, _, body = self.request("POST", "/api/compare", {"run_ids": ["missing-run"]})
        self.assertEqual(status, 400)
        self.assertIn("at least two", json.loads(body)["error"])


if __name__ == "__main__":
    unittest.main()
