from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from packing_verifier.verifier import solution_hash, verify_solution


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

    def test_redundant_regular_dimensions_must_match(self) -> None:
        bad = {
            "schema_version": "packing-benchmark/v1",
            "case": "triintri@1",
            "item": {"type": "regular_polygon", "sides": 3, "side_length": 1.0},
            "container": {
                "type": "regular_polygon",
                "sides": 3,
                "side_length": 1.0,
                "circumradius": 10.0,
            },
            "placements": [{"x": 0.0, "y": 0.0, "rotation_radians": 0.0}],
        }
        result = verify_solution(bad)
        self.assertFalse(result.ok)
        self.assertTrue(any("inconsistent" in error for error in result.errors))

    def test_exact_triintri_tt40_variants_score_identically(self) -> None:
        base_points = [
            (5.5, 0.0, 0.0), (4.5, 0.0, math.pi / 3.0),
            (4.0, 0.5, 0.0), (4.0, -0.5, 0.0),
            (3.0, 0.5, math.pi / 3.0), (3.0, -0.5, math.pi / 3.0),
            (2.5, 0.0, 0.0), (2.5, 1.0, 0.0), (2.5, -1.0, 0.0),
            (1.5, 0.0, math.pi / 3.0), (1.5, 1.0, math.pi / 3.0), (1.5, -1.0, math.pi / 3.0),
            (1.0, 1.5, 0.0), (1.0, 0.5, 0.0), (1.0, -0.5, 0.0), (1.0, -1.5, 0.0),
            (0.0, 1.0, math.pi / 3.0), (0.0, 0.0, math.pi / 3.0), (0.0, -1.0, math.pi / 3.0),
            (-0.5, 0.5, 0.0), (-0.5, -0.5, 0.0),
            (-0.75, 1.75, math.pi / 3.0), (-0.75, -1.75, math.pi / 3.0),
            (-1.25, 2.25, 0.0), (-1.25, 1.25, 0.0), (-1.25, -1.25, 0.0), (-1.25, -2.25, 0.0),
            (-1.5, 0.5, math.pi / 3.0), (-1.5, -0.5, math.pi / 3.0),
            (-2.0, 0.0, 0.0),
            (-2.25, 2.25, math.pi / 3.0), (-2.25, 1.25, math.pi / 3.0),
            (-2.25, -1.25, math.pi / 3.0), (-2.25, -2.25, math.pi / 3.0),
            (-2.75, 1.75, 0.0), (-2.75, 0.75, 0.0), (-2.75, -0.75, 0.0),
            (-2.75, -1.75, 0.0), (-2.75, -2.75, 0.0), (-2.75, 2.75, 0.0),
        ]

        def solution(case: str, points: list[tuple[float, float, float]]) -> dict[str, object]:
            return {
                "schema_version": "packing-benchmark/v1",
                "case": case,
                "setup": "triintri",
                "item": {
                    "type": "regular_polygon",
                    "sides": 3,
                    "side_length": 1.0,
                    "circumradius": 1.0 / math.sqrt(3.0),
                },
                "container": {
                    "type": "regular_polygon",
                    "sides": 3,
                    "side_length": 6.5,
                    "circumradius": 6.5 / math.sqrt(3.0),
                    "orientation_radians": 0.0,
                },
                "placements": [
                    {"id": i + 1, "x": sx / math.sqrt(3.0), "y": y, "rotation_radians": rot}
                    for i, (sx, y, rot) in enumerate(points)
                ],
            }

        result39 = verify_solution(solution("triintri@39", base_points[:-1]), tolerance=0.0)
        result40 = verify_solution(solution("triintri@40", base_points), tolerance=0.0)
        self.assertTrue(result39.ok, result39.errors)
        self.assertTrue(result40.ok, result40.errors)
        self.assertEqual(result39.metric_value, 6.5)
        self.assertEqual(result40.metric_value, 6.5)
        self.assertNotEqual(
            solution_hash(solution("triintri@39", base_points[:-1])),
            solution_hash(solution("triintri@40", base_points)),
        )


if __name__ == "__main__":
    unittest.main()
