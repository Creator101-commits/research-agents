"""Tests for isolated, validated per-run calibration overrides."""

from __future__ import annotations

from copy import deepcopy
import unittest

from dairy_abm.config import value
from dairy_abm.core import ConfigError
from webapp import CALIBRATION, RUN_CACHE, _run_simulation


class DashboardCalibrationOverrideTests(unittest.TestCase):
    def setUp(self) -> None:
        RUN_CACHE.clear()
        self.global_before = deepcopy(CALIBRATION)

    def tearDown(self) -> None:
        self.assertEqual(CALIBRATION, self.global_before)
        RUN_CACHE.clear()

    @staticmethod
    def params(calibration_overrides: dict | None = None) -> dict:
        return {
            "scenario_overrides": {"days": 1, "seed": 7, "herd_size": 2},
            "calibration_overrides": calibration_overrides or {},
        }

    def test_valid_override_is_applied_and_reported(self) -> None:
        result = _run_simulation(
            self.params({"genetics.selection_intensity": 0.4})
        )
        cached = RUN_CACHE[result["run_id"]]

        self.assertEqual(
            value(cached.ctx.calibration, "genetics.selection_intensity"), 0.4
        )
        self.assertEqual(result["meta"]["calibration_override_count"], 1)
        self.assertEqual(
            result["meta"]["calibration_overrides"],
            {"genetics.selection_intensity": 0.4},
        )
        self.assertEqual(value(CALIBRATION, "genetics.selection_intensity"), 0.2)

    def test_unknown_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigError, "unknown calibration key"):
            _run_simulation(self.params({"not.a.parameter": 1}))

    def test_invalid_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigError, "must be numeric"):
            _run_simulation(self.params({"genetics.selection_intensity": "0.4"}))

    def test_invalid_range_is_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigError, "valid range"):
            _run_simulation(self.params({"genetics.selection_intensity": 2}))

    def test_sum_to_one_group_is_validated_after_override(self) -> None:
        with self.assertRaisesRegex(ConfigError, "trait weights must sum"):
            _run_simulation(
                self.params({"genetics.trait_weights.milk_yield": 0.9})
            )

    def test_runs_use_independent_calibration_copies(self) -> None:
        first = _run_simulation(
            self.params({"genetics.selection_intensity": 0.1})
        )
        second = _run_simulation(self.params())
        third = _run_simulation(
            self.params({"genetics.selection_intensity": 0.4})
        )

        self.assertEqual(
            value(RUN_CACHE[first["run_id"]].ctx.calibration, "genetics.selection_intensity"),
            0.1,
        )
        self.assertEqual(
            value(RUN_CACHE[second["run_id"]].ctx.calibration, "genetics.selection_intensity"),
            0.2,
        )
        self.assertEqual(
            value(RUN_CACHE[third["run_id"]].ctx.calibration, "genetics.selection_intensity"),
            0.4,
        )
        self.assertEqual(second["meta"]["calibration_override_count"], 0)
        self.assertEqual(value(CALIBRATION, "genetics.selection_intensity"), 0.2)


if __name__ == "__main__":
    unittest.main()
