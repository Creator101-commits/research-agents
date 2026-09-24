"""The same seed replays identically across interpreter processes."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = """
import hashlib, json
from dairy_abm.config import load_calibration
from dairy_abm.model import DairyFarmModel
# Two years so offspring inherit from the annual sire pool (where the order bug lived).
scenario = {"days": 730, "herd_size": 60, "seed": 5, "auto_environment_response": False,
            "auto_feed_response": False, "auto_energy_response": False, "auto_biosecurity_response": False}
scenario.update({f"l{i}_{name}_loop_enabled": False for i, name in ((1, "nutrient"), (2, "water"), (3, "energy"), (4, "byproduct"))})
ctx = DairyFarmModel(scenario, load_calibration()).run()
rows = [[r["milk_l"], r["dmi_kg"], r["conceptions"], r["profit"]] for r in ctx.daily_records]
print(hashlib.sha256(json.dumps(rows).encode()).hexdigest())
"""


class DeterministicReplayTest(unittest.TestCase):
    def test_string_hash_seed_does_not_change_results(self) -> None:
        digests = set()
        for hash_seed in ("1", "2"):
            env = {**os.environ, "PYTHONHASHSEED": hash_seed}
            result = subprocess.run([sys.executable, "-B", "-c", SCRIPT], cwd=ROOT, env=env,
                                    capture_output=True, text=True, check=True)
            digests.add(result.stdout.strip())
        self.assertEqual(len(digests), 1)


if __name__ == "__main__":
    unittest.main()
