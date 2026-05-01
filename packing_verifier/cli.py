from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .verifier import (
    DEFAULT_TOLERANCE,
    canonical_json,
    load_solution_json,
    normalize_solution,
    solution_hash,
    verify_solution,
)


def read_input(path_text: str) -> str:
    if path_text == "-":
        return sys.stdin.read()
    return Path(path_text).read_text()


def load_solution(path_text: str) -> dict[str, Any]:
    return normalize_solution(load_solution_json(read_input(path_text)))


def command_verify(args: argparse.Namespace) -> int:
    solution = load_solution(args.input)
    result = verify_solution(solution, tolerance=args.tolerance)
    payload = result.as_dict()
    payload["solution_hash"] = solution_hash(solution)

    if args.normalized_json:
        payload["normalized_solution"] = solution

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        status = "PASS" if result.ok else "FAIL"
        print(f"{status} {payload['case']}")
        print(f"solution_hash: {payload['solution_hash']}")
        print(f"items: {result.n}")
        if result.metric_symbol is not None and result.metric_value is not None:
            print(f"metric: {result.metric_symbol} = {result.metric_value:.10f}")
        if result.side is not None:
            print(f"container side/diameter: {result.side:.10f}")
        if result.density is not None:
            print(f"density: {result.density:.10f}")
        print(f"max_boundary_excess: {result.max_boundary_excess:.12g}")
        print(f"max_pair_overlap_depth: {result.max_pair_overlap_depth:.12g}")
        print(f"tolerance: {result.tolerance:.12g}")
        if result.errors:
            print("errors:")
            for error in result.errors:
                print(f"  - {error}")
        if result.warnings:
            print("warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")

    return 0 if result.ok else 1


def command_hash(args: argparse.Namespace) -> int:
    solution = load_solution(args.input)
    if args.json:
        print(
            json.dumps(
                {
                    "case": solution.get("case"),
                    "setup": solution.get("setup"),
                    "solution_hash": solution_hash(solution),
                    "canonical_json": canonical_json(solution),
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(solution_hash(solution))
    return 0


def command_normalize(args: argparse.Namespace) -> int:
    solution = load_solution(args.input)
    if args.compact:
        print(canonical_json(solution))
    else:
        print(json.dumps(solution, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="packing-verifier",
        description="Verify canonical coordinate JSON for the Packing Benchmark.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify = subparsers.add_parser("verify", help="verify geometry and report the benchmark metric")
    verify.add_argument("input", help="solution JSON path, or '-' for stdin")
    verify.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE, help=f"geometry tolerance, default {DEFAULT_TOLERANCE:g}")
    verify.add_argument("--json", action="store_true", help="print machine-readable JSON")
    verify.add_argument("--normalized-json", action="store_true", help="include normalized solution in --json output")
    verify.set_defaults(func=command_verify)

    hash_cmd = subparsers.add_parser("hash", help="print the canonical solution hash")
    hash_cmd.add_argument("input", help="solution JSON path, or '-' for stdin")
    hash_cmd.add_argument("--json", action="store_true", help="print hash metadata as JSON")
    hash_cmd.set_defaults(func=command_hash)

    normalize = subparsers.add_parser("normalize", help="print verifier-normalized coordinate JSON")
    normalize.add_argument("input", help="solution JSON path, or '-' for stdin")
    normalize.add_argument("--compact", action="store_true", help="print compact canonical JSON")
    normalize.set_defaults(func=command_normalize)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, ValueError) as exc:
        print(f"packing-verifier: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
