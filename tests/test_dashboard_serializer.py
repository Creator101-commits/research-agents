"""Tests for the Python-to-dashboard serializer."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from random import Random
import unittest

from dairy_abm.config import load_calibration
from dairy_abm.core import EventLog, SimulationContext
from dairy_abm.dashboard import DASHBOARD_DAILY_FIELDS, serialize_dashboard_run
from dairy_abm.model import DairyFarmModel


class DashboardSerializerTests(unittest.TestCase):
    def test_serializes_current_run_output_and_units(self) -> None:
        ctx = DairyFarmModel(
            {
                "name": "serializer",
                "start_date": "2026-01-01",
                "days": 2,
                "seed": 12,
                "herd_size": 3,
            },
            load_calibration(),
        ).run()

        result = serialize_dashboard_run(ctx, "run1234", 1.234)

        self.assertEqual(result["run_id"], "run1234")
        self.assertEqual(result["meta"]["scenario_name"], "serializer")
        self.assertEqual(result["meta"]["start_date"], "2026-01-01")
        self.assertEqual(result["meta"]["seed"], 12)
        self.assertEqual(result["meta"]["days"], 2)
        self.assertEqual(result["meta"]["herd_size"], 3)
        self.assertEqual(result["meta"]["duration_s"], 1.23)
        self.assertEqual(result["daily"], result["series"]["daily"])
        self.assertEqual(set(result["daily"][0]), set(DASHBOARD_DAILY_FIELDS))
        self.assertAlmostEqual(result["metrics"]["milk"], sum(row["milk_l"] for row in ctx.daily_records))
        self.assertAlmostEqual(
            result["metrics"]["energy_avg"],
            sum(row["energy_self_sufficiency_pct"] for row in ctx.daily_records) / 2,
        )
        self.assertEqual(result["summary"]["milk"]["unit"], "L")
        self.assertEqual(result["summary"]["net_co2e"]["unit"], "kg CO2e")
        self.assertEqual(result["summary"]["profit"]["unit"], "currency")
        self.assertTrue(result["summary"]["milk"]["available"])
        self.assertFalse(result["features"]["enable_processor"])
        self.assertTrue(result["features"]["l1_nutrient_loop_enabled"])
        self.assertEqual(result["events"], result["meta"]["event_count"])

    def test_same_seed_and_inputs_produce_deterministic_serialization(self) -> None:
        scenario = {"name": "deterministic", "days": 3, "seed": 42, "herd_size": 4}
        first = DairyFarmModel(scenario, load_calibration()).run()
        second = DairyFarmModel(scenario, load_calibration()).run()

        self.assertEqual(
            serialize_dashboard_run(first, "same-id", 2.0),
            serialize_dashboard_run(second, "same-id", 2.0),
        )

    def test_missing_values_remain_unavailable(self) -> None:
        ctx = SimulationContext(
            scenario={"name": "missing", "days": 1, "seed": 1, "herd_size": 0},
            calibration={},
            rng=Random(1),
            events=EventLog(),
        )
        ctx.daily_records.append({"day": "2026-01-01", "milk_l": None})

        result = serialize_dashboard_run(ctx, "missing01", 0.0)

        self.assertIsNone(result["daily"][0]["profit"])
        self.assertIsNone(result["metrics"]["milk"])
        self.assertIsNone(result["summary"]["milk"]["value"])
        self.assertFalse(result["summary"]["milk"]["available"])
        self.assertEqual(result["summary"]["milk"]["reason"], "no data for selected run")

    def test_serializer_does_not_mutate_context_or_calibration(self) -> None:
        ctx = DairyFarmModel(
            {"name": "immutable", "days": 1, "seed": 3, "herd_size": 2},
            load_calibration(),
        ).run()
        scenario_before = deepcopy(ctx.scenario)
        calibration_before = deepcopy(ctx.calibration)
        records_before = deepcopy(ctx.daily_records)

        result = serialize_dashboard_run(ctx, "immutable", 0.0)
        result["daily"][0]["milk_l"] = -1
        result["summary"]["milk"]["value"] = -1

        self.assertEqual(ctx.scenario, scenario_before)
        self.assertEqual(ctx.calibration, calibration_before)
        self.assertEqual(ctx.daily_records, records_before)

    def test_warning_serialization_filters_and_copies_warning_events(self) -> None:
        ctx = SimulationContext(
            scenario={"name": "warnings", "days": 1},
            calibration={},
            rng=Random(1),
            events=EventLog(),
        )
        ctx.events.add(date(2026, 1, 1), "test", "info", "ignore this")
        ctx.events.add(date(2026, 1, 1), "test", "warning", "show this", value=2)

        result = serialize_dashboard_run(ctx, "warn0001", 0.0)
        result["warnings"][0]["message"] = "changed outside context"

        self.assertEqual(len(result["warnings"]), 1)
        self.assertEqual(result["warnings"][0]["message"], "changed outside context")
        self.assertEqual(ctx.events.events[1]["message"], "show this")


if __name__ == "__main__":
    unittest.main()
