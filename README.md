# Packing Verifier

Open verifier for canonical coordinate JSON submissions to the Packing Benchmark:

https://huggingface.co/spaces/NathanRoll/packing-benchmark

The command checks the same geometry constraints used by the Space:

- the `case` count and setup match the JSON geometry
- every value is finite JSON
- items stay inside the container
- items do not overlap beyond tolerance
- the benchmark metric is computed from the container

The verifier is dependency-free Python and is intended for local preflight checks before submission.

## Install

```bash
python -m pip install git+https://github.com/Nathan-Roll1/packing-verifier.git
```

For one-off use without installing into your main environment, pipe a JSON payload through stdin:

```bash
curl -L https://raw.githubusercontent.com/Nathan-Roll1/packing-verifier/main/examples/triintri_1.json \
  | python -m pipx run --spec git+https://github.com/Nathan-Roll1/packing-verifier.git packing-verifier verify -
```

## Verify A Solution

```bash
packing-verifier verify solution.json
```

Machine-readable output:

```bash
packing-verifier verify solution.json --json
```

The command exits with status `0` when geometry passes, `1` when geometry fails, and `2` for input or command errors.

## Other Commands

```bash
packing-verifier normalize solution.json
packing-verifier hash solution.json
```

`normalize` prints the verifier-normalized payload. `hash` prints the canonical solution hash used as a stable identifier.

## JSON Format

```json
{
  "schema_version": "packing-benchmark/v1",
  "case": "triintri@1",
  "item": {"type": "regular_polygon", "sides": 3, "side_length": 1},
  "container": {"type": "regular_polygon", "sides": 3, "side_length": 1},
  "placements": [
    {"x": 0.0, "y": 0.0, "rotation_radians": 0.0}
  ]
}
```

Supported shapes:

- `regular_polygon`: `sides` plus `side_length` or `circumradius`
- `circle`: `radius` or `diameter`
- `rectangle`: `width` and `height`

Coordinate convention:

- the container is centered at the origin
- placements are item centers
- rotations are radians counterclockwise
- touching is legal; overlap and protrusion are rejected

## Metric

The command reports the metric the leaderboard uses:

- `s`: side length for regular polygon containers, square/rectangle long side, and domino short side
- `r`: radius for circle containers

Smaller metric values are better. The public Space applies an additional record gate: existing cases must improve the current top metric by at least `0.0001`.

## Development

```bash
python -m unittest discover -s tests
python -m packing_verifier.cli verify examples/triintri_1.json
```
