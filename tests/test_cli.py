from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "packing_verifier.cli", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_valid_example_passes(self) -> None:
        result = self.run_cli("verify", "examples/triintri_1.json", "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["case"], "triintri@1")
        self.assertEqual(payload["metric_symbol"], "s")
        self.assertAlmostEqual(payload["metric_value"], 1.0)

    def test_overlap_fails(self) -> None:
        bad = {
            "schema_version": "packing-benchmark/v1",
            "case": "cirincir@2",
            "item": {"type": "circle", "radius": 1.0},
            "container": {"type": "circle", "radius": 2.0},
            "placements": [
                {"x": 0.0, "y": 0.0, "rotation_radians": 0.0},
                {"x": 0.0, "y": 0.0, "rotation_radians": 0.0},
            ],
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(bad, handle)
            path = handle.name
        try:
            result = self.run_cli("verify", path, "--json")
        finally:
            Path(path).unlink(missing_ok=True)
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertTrue(any("overlap" in error for error in payload["errors"]))

    def test_normalize_adds_setup(self) -> None:
        result = self.run_cli("normalize", "examples/triintri_1.json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["setup"], "triintri")


if __name__ == "__main__":
    unittest.main()
