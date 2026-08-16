"""Contract tests for the latest-day cow performance explorer."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from random import Random
import unittest

from dairy_abm.config import load_calibration
from dairy_abm.core import EventLog, Packet, SimulationContext
from dairy_abm.dashboard import serialize_dashboard_run
from dairy_abm.model import DairyFarmModel


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
INDEX = (WEB / "index.html").read_text(encoding="utf-8")
APP = (WEB / "js" / "app.js").read_text(encoding="utf-8")
CSS = "\n".join(path.read_text(encoding="utf-8") for path in (WEB / "styles").glob("*.css"))


class DashboardCowsTests(unittest.TestCase):
    def _run(self, **overrides):
        scenario = {
            "name": "cows",
            "start_date": "2026-01-01",
            "days": 2,
            "seed": 12,
            "herd_size": 4,
        }
        scenario.update(overrides)
        return DairyFarmModel(scenario, load_calibration()).run()

    def test_contract_merges_latest_packet_with_final_cow_state(self) -> None:
        ctx = self._run()
        result = serialize_dashboard_run(ctx, "cows01", 0.1)
        cows = result["cows"]
        packet = ctx.get_packet("cow_daily_packet")
        packet_records = packet.payload["cow_records"]
        state_by_id = {str(cow["id"]): cow for cow in ctx.state["cows"]}

        self.assertTrue(cows["available"])
        self.assertEqual(cows["period"], "latest-day")
        self.assertEqual(cows["date"], packet.day.isoformat())
        self.assertEqual(
            cows["source"],
            'ctx.packets["cow_daily_packet"].payload["cow_records"]',
        )
        self.assertEqual(len(cows["records"]), len(packet_records))
        self.assertEqual(list(cows["records"][0]), cows["contract"]["fields"])

        for row, packet_record in zip(cows["records"], packet_records):
            self.assertEqual(row["id"], packet_record["id"])
            self.assertEqual(row["milk_l"], packet_record["milk_l"])
            self.assertEqual(row["dmi_kg"], packet_record["dmi_kg"])
            self.assertEqual(row["health_status"], packet_record["health_status"])
            self.assertEqual(row["body_weight_kg"], state_by_id[row["id"]]["body_weight_kg"])
            self.assertEqual(row["body_condition_score"], state_by_id[row["id"]]["body_condition_score"])
            self.assertEqual(row["pregnant"], state_by_id[row["id"]]["pregnant"])
            self.assertEqual(row["trait_vector"], state_by_id[row["id"]]["trait_vector"])
            self.assertNotIn("efficiency_score", row)
            self.assertAlmostEqual(row["fcr_kg_dm_per_l"], row["dmi_kg"] / row["milk_l"])

        self.assertEqual(
            sum(cows["health_counts"].values()),
            len(cows["records"]),
        )
        self.assertIn("milk_yield", cows["trait_distributions"])
        self.assertEqual(
            set(cows["rankings"]),
            {"milk_l", "fcr_kg_dm_per_l", "dmi_kg", "methane_intensity_kg_ch4_per_l"},
        )
        self.assertEqual(
            cows["rankings"]["milk_l"],
            [row["id"] for row in sorted(cows["records"], key=lambda row: row["milk_l"], reverse=True)],
        )

    def test_contract_preserves_unavailable_ratios_and_missing_packet(self) -> None:
        ctx = SimulationContext(
            scenario={"name": "missing-cows", "days": 1},
            calibration={},
            rng=Random(1),
            events=EventLog(),
        )
        ctx.state["cows"] = [
            {
                "id": "cow-x",
                "body_weight_kg": 650.0,
                "body_condition_score": 3.0,
                "pregnant": False,
                "days_pregnant": 0,
                "feed_efficiency_trait": 1.0,
                "trait_vector": {"milk_yield": 1.0},
                "ch4_history": [1.0],
                "milk_history": [0.0],
            }
        ]
        ctx.publish(
            Packet(
                source="cow",
                name="cow_daily_packet",
                day=date(2026, 1, 1),
                payload={
                    "cow_records": [
                        {
                            "id": "cow-x",
                            "milk_l": 0.0,
                            "dmi_kg": 2.0,
                            "days_in_milk": 0,
                            "parity": 0,
                            "health_status": "healthy",
                            "rumen_ph": None,
                            "observed_dmi_kg": None,
                            "actual_dmi_kg_dm": 2.0,
                            "expected_dmi_eq2_1_kg_dm": 2.0,
                            "estrus_detected": False,
                            "sara_active": False,
                        }
                    ]
                },
            )
        )

        result = serialize_dashboard_run(ctx, "cows02", 0.0)
        row = result["cows"]["records"][0]
        self.assertIsNone(row["fcr_kg_dm_per_l"])
        self.assertIsNone(row["methane_intensity_kg_ch4_per_l"])
        self.assertIsNone(row["observed_dmi_kg"])
        self.assertIsNone(row["rumen_ph"])

        empty = SimulationContext(
            scenario={"name": "no-cow-packet", "days": 1},
            calibration={},
            rng=Random(1),
            events=EventLog(),
        )
        empty_result = serialize_dashboard_run(empty, "cows03", 0.0)["cows"]
        self.assertFalse(empty_result["available"])
        self.assertEqual(empty_result["records"], [])
        self.assertEqual(empty_result["period"], "latest-day")

    def test_cow_page_uses_real_records_and_no_legacy_score(self) -> None:
        self.assertIn('id="cows-content"', INDEX)
        self.assertIn("renderCows", APP)
        self.assertIn("data.cows", APP)
        self.assertIn("data-cow-sort", APP)
        start = APP.index("function renderCows")
        end = APP.index("function toolbar", start)
        cow_page = APP[start:end]
        self.assertNotIn("aggregate(", cow_page)
        self.assertNotIn("efficiency_score", APP)
        self.assertIn("cow-scatter", CSS)
        self.assertIn("cow-table", CSS)
        self.assertIn("cow-health", CSS)


if __name__ == "__main__":
    unittest.main()
