"""Contracts for the Conventional Farm adapter and its local API."""

from __future__ import annotations

import json
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

from dairy_abm.dashboard_conventional import comparison_keys, default_config, resolve_inputs
from webapp import CALIBRATION, DEFAULT_SCENARIO, Handler, RUN_CACHE, _run_conventional


class ConventionalDashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        RUN_CACHE.clear()

    def test_ledger_mapping_reconciles_profit_and_handles_dry_cows(self) -> None:
        result = _run_conventional({
            "cfg": {"number_of_cows": 4, "simulation_years": 2 / 365, "random_seed": 7},
            "loops": {"l1": True, "l2": True, "l3": True, "l4": True},
        })
        self.assertEqual(result["days"], 2)
        self.assertEqual(result["n"], 4)
        self.assertEqual(len(result["series"]["milk"]), 2)
        ctx = RUN_CACHE[result["runId"]].ctx
        self.assertAlmostEqual(result["totals"]["milk"], sum(row["milk_l"] for row in ctx.daily_records))
        self.assertAlmostEqual(result["totals"]["profit"], sum(row["profit"] for row in ctx.daily_records))
        for cow in result["herdSummary"]:
            self.assertRegex(cow["id"], r"^C\d{5}$")
            self.assertTrue(cow["modelId"])
        self.assertAlmostEqual(
            result["totals"]["profit"],
            result["totals"]["totalRevenue"] - result["totals"]["feedCost"]
            - result["totals"]["waterCost"] + result["totals"]["otherHerdNet"],
        )
        for index, row in enumerate(ctx.daily_records):
            expected = max(0.0, row["dmi_kg"] - row["feed_loop_offset_kg"])
            self.assertAlmostEqual(result["series"]["netFeed"][index], expected)
            if row["milk_kg"] > 0:
                self.assertAlmostEqual(result["series"]["netFCR"][index], expected / row["milk_kg"])
            else:
                self.assertIsNone(result["series"]["netFCR"][index])

    def test_only_directly_mapped_controls_are_accepted(self) -> None:
        cfg = default_config({**DEFAULT_SCENARIO, "days": 1825, "seed": 42}, CALIBRATION)
        self.assertEqual(cfg["simulation_years"], 5)
        self.assertEqual(cfg["random_seed"], 42)
        with self.assertRaisesRegex(ValueError, "unsupported parameter"):
            resolve_inputs({"cfg": {"milk_yield_L_per_cow_per_day": 50}}, DEFAULT_SCENARIO, CALIBRATION)
        with self.assertRaisesRegex(ValueError, "loops must contain"):
            resolve_inputs({"loops": {"l1": True}}, DEFAULT_SCENARIO, CALIBRATION)

    def test_comparison_has_every_target_loop_combination(self) -> None:
        keys = comparison_keys()
        self.assertEqual(len(keys), 16)
        self.assertEqual(keys[0], "baseline")
        self.assertEqual(keys[-1], "all4")
        self.assertEqual(len(set(keys)), 16)


class ConventionalHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def test_params_and_run_routes(self) -> None:
        with urlopen(self.base + "/api/conventional/params") as response:
            params = json.load(response)
        self.assertEqual(params["cfg"]["simulation_years"], 5)
        self.assertIn("wood_b", params["supported"])
        request = Request(
            self.base + "/api/conventional/run",
            data=json.dumps({"cfg": {"number_of_cows": 3, "simulation_years": 1 / 365}}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            result = json.load(response)
        self.assertTrue(result["ok"])
        self.assertEqual(result["days"], 1)
        self.assertEqual(result["n"], 3)
        self.assertIn(result["runId"], RUN_CACHE)

    def test_excel_parity_route_has_eight_seed_results(self) -> None:
        with urlopen(self.base + "/api/conventional/parity") as response:
            result = json.load(response)
        self.assertEqual(result["seeds"], 8)
        saved = json.loads((Path(__file__).resolve().parents[1] / "docs/parity/parity_results_8_seeds.json").read_text())
        self.assertEqual(result["status_counts"], saved["aggregate"]["comparison"]["status_counts"])
        # Acceptance bar for the parity work: at least 21 of 31 rows within 2%.
        self.assertGreaterEqual(result["status_counts"]["match"], 21)
        self.assertIn("profit", result["selected"])


if __name__ == "__main__":
    unittest.main()
