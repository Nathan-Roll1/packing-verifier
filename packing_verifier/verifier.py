from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from typing import Any


PI = math.pi
DEFAULT_TOLERANCE = 1.0e-8
CASE_PATTERN = re.compile(r"^[a-z0-9]+in[a-z0-9]+@[1-9][0-9]*$")


@dataclass
class VerificationResult:
    ok: bool
    case: str
    setup: str
    n: int
    side: float | None
    metric_symbol: str | None
    metric_value: float | None
    density: float | None
    max_boundary_excess: float
    max_pair_overlap_depth: float
    tolerance: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "case": self.case,
            "setup": self.setup,
            "n": self.n,
            "side": self.side,
            "metric_symbol": self.metric_symbol,
            "metric_value": self.metric_value,
            "density": self.density,
            "max_boundary_excess": self.max_boundary_excess,
            "max_pair_overlap_depth": self.max_pair_overlap_depth,
            "tolerance": self.tolerance,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def regular_vertices(
    sides: int,
    radius: float,
    rotation: float = 0.0,
    center: tuple[float, float] = (0.0, 0.0),
) -> list[tuple[float, float]]:
    cx, cy = center
    return [
        (
            cx + radius * math.cos(rotation + 2.0 * PI * i / sides),
            cy + radius * math.sin(rotation + 2.0 * PI * i / sides),
        )
        for i in range(sides)
    ]


def rectangle_vertices(
    width: float,
    height: float,
    rotation: float = 0.0,
    center: tuple[float, float] = (0.0, 0.0),
) -> list[tuple[float, float]]:
    cx, cy = center
    ca = math.cos(rotation)
    sa = math.sin(rotation)
    local = [
        (-width * 0.5, -height * 0.5),
        (width * 0.5, -height * 0.5),
        (width * 0.5, height * 0.5),
        (-width * 0.5, height * 0.5),
    ]
    return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in local]


def polygon_area(poly: list[tuple[float, float]]) -> float:
    twice = 0.0
    for i, (x1, y1) in enumerate(poly):
        x2, y2 = poly[(i + 1) % len(poly)]
        twice += x1 * y2 - x2 * y1
    return 0.5 * twice


def regular_area(sides: int, radius: float) -> float:
    return 0.5 * sides * radius * radius * math.sin(2.0 * PI / sides)


def finite_float(value: Any, label: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be numeric") from None
    if not math.isfinite(out):
        raise ValueError(f"{label} must be finite")
    return out


def integer_value(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    if isinstance(value, int):
        out = value
    elif isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError(f"{label} must be an integer")
        out = int(value)
    elif isinstance(value, str):
        if not re.fullmatch(r"[+-]?\d+", value.strip()):
            raise ValueError(f"{label} must be an integer")
        out = int(value)
    else:
        raise ValueError(f"{label} must be an integer")
    return out


def shape_type(spec: dict[str, Any]) -> str:
    return str(spec.get("type", "")).strip().lower()


def regular_sides(spec: dict[str, Any]) -> int:
    if "sides" not in spec:
        raise ValueError("regular_polygon requires sides")
    sides = integer_value(spec["sides"], "regular_polygon sides")
    if sides < 3:
        raise ValueError("regular polygons need at least 3 sides")
    return sides


def regular_radius(spec: dict[str, Any]) -> float:
    sides = regular_sides(spec)
    if "circumradius" in spec:
        radius = finite_float(spec["circumradius"], "regular_polygon circumradius")
    elif "side_length" in spec:
        side = finite_float(spec["side_length"], "regular_polygon side_length")
        radius = side / (2.0 * math.sin(PI / sides))
    else:
        raise ValueError("regular_polygon requires side_length or circumradius")
    if radius <= 0.0:
        raise ValueError("regular_polygon radius must be positive")
    return radius


def regular_side_length(spec: dict[str, Any]) -> float:
    sides = regular_sides(spec)
    if "side_length" in spec:
        side = finite_float(spec["side_length"], "regular_polygon side_length")
    else:
        side = 2.0 * regular_radius(spec) * math.sin(PI / sides)
    if side <= 0.0:
        raise ValueError("regular_polygon side_length must be positive")
    return side


def circle_radius(spec: dict[str, Any]) -> float:
    if "radius" in spec:
        radius = finite_float(spec["radius"], "circle radius")
    elif "diameter" in spec:
        radius = 0.5 * finite_float(spec["diameter"], "circle diameter")
    else:
        raise ValueError("circle requires radius or diameter")
    if radius <= 0.0:
        raise ValueError("circle radius must be positive")
    return radius


def rectangle_dims(spec: dict[str, Any]) -> tuple[float, float]:
    width = finite_float(spec["width"], "rectangle width")
    height = finite_float(spec["height"], "rectangle height")
    if width <= 0.0 or height <= 0.0:
        raise ValueError("rectangle width and height must be positive")
    return width, height


def optional_rotation(spec: dict[str, Any], field: str = "orientation_radians") -> float:
    return finite_float(spec.get(field, 0.0), field)


def make_item_shape(item: dict[str, Any], placement: dict[str, Any]) -> dict[str, Any]:
    kind = shape_type(item)
    if not isinstance(placement, dict):
        raise ValueError("each placement must be an object")
    x = finite_float(placement.get("x", 0.0), "placement x")
    y = finite_float(placement.get("y", 0.0), "placement y")
    rotation = finite_float(placement.get("rotation_radians", 0.0), "placement rotation_radians")

    if kind == "regular_polygon":
        radius = regular_radius(item)
        sides = regular_sides(item)
        return {
            "kind": "polygon",
            "vertices": regular_vertices(sides, radius, rotation=rotation, center=(x, y)),
            "area": regular_area(sides, radius),
        }
    if kind == "rectangle":
        width, height = rectangle_dims(item)
        return {
            "kind": "polygon",
            "vertices": rectangle_vertices(width, height, rotation=rotation, center=(x, y)),
            "area": width * height,
        }
    if kind == "circle":
        radius = circle_radius(item)
        return {
            "kind": "circle",
            "center": (x, y),
            "radius": radius,
            "area": PI * radius * radius,
        }
    raise ValueError(f"unsupported item type {kind!r}")


def make_container_shape(container: dict[str, Any]) -> dict[str, Any]:
    kind = shape_type(container)
    rotation = optional_rotation(container)
    if kind == "regular_polygon":
        radius = regular_radius(container)
        sides = regular_sides(container)
        return {
            "kind": "polygon",
            "vertices": regular_vertices(sides, radius, rotation=rotation),
            "side": regular_side_length(container),
            "area": regular_area(sides, radius),
        }
    if kind == "rectangle":
        width, height = rectangle_dims(container)
        return {
            "kind": "polygon",
            "vertices": rectangle_vertices(width, height, rotation=rotation),
            "side": max(width, height),
            "width": width,
            "height": height,
            "area": width * height,
        }
    if kind == "circle":
        radius = circle_radius(container)
        return {
            "kind": "circle",
            "center": (0.0, 0.0),
            "radius": radius,
            "side": 2.0 * radius,
            "area": PI * radius * radius,
        }
    raise ValueError(f"unsupported container type {kind!r}")


def solution_setup(solution: dict[str, Any]) -> str:
    if solution.get("setup"):
        return str(solution["setup"])
    if solution.get("case") and "@" in str(solution["case"]):
        return str(solution["case"]).split("@", 1)[0]
    item = solution.get("item", {})
    container = solution.get("container", {})
    return f"{shape_label(item)}in{shape_label(container)}"


def shape_label(spec: dict[str, Any]) -> str:
    kind = shape_type(spec)
    if kind == "regular_polygon":
        sides = regular_sides(spec)
        names = {3: "tri", 4: "squ", 5: "pen", 6: "hex", 7: "hep", 8: "oct"}
        return names.get(sides, f"{sides}gon")
    if kind == "circle":
        return "cir"
    if kind == "rectangle":
        width, height = rectangle_dims(spec)
        ratio = max(width, height) / min(width, height)
        if abs(ratio - 1.0) <= 1.0e-9:
            return "squ"
        if abs(ratio - 2.0) <= 1.0e-9:
            return "dom"
        return "rect"
    return kind or "shape"


def inferred_setup(item: dict[str, Any], container: dict[str, Any]) -> str:
    return f"{shape_label(item)}in{shape_label(container)}"


def solution_case(solution: dict[str, Any]) -> str:
    placements = solution.get("placements", [])
    n = len(placements) if isinstance(placements, list) else 0
    return str(solution.get("case") or f"{solution_setup(solution)}@{n}")


def parsed_case_count(case: str) -> int | None:
    if "@" not in case:
        return None
    try:
        return int(case.rsplit("@", 1)[1])
    except ValueError:
        return None


def parsed_case_setup(case: str) -> str | None:
    if "@" not in case:
        return None
    setup, count_text = case.rsplit("@", 1)
    if not setup or not count_text:
        return None
    try:
        count = int(count_text)
    except ValueError:
        return None
    if count <= 0:
        return None
    return setup


def container_metric(container_shape: dict[str, Any]) -> tuple[str, float]:
    if container_shape["kind"] == "circle":
        return "r", float(container_shape["radius"])
    width = container_shape.get("width")
    height = container_shape.get("height")
    if width is not None and height is not None:
        short = min(float(width), float(height))
        long = max(float(width), float(height))
        if abs(long / short - 2.0) <= 1.0e-9:
            return "s", short
    return "s", float(container_shape["side"])


def finite_points(points: list[tuple[float, float]], label: str) -> None:
    for x, y in points:
        if not math.isfinite(x + y):
            raise ValueError(f"{label} contains non-finite coordinates")


def validate_shape_finite(shape: dict[str, Any], label: str) -> None:
    if shape["kind"] == "circle":
        cx, cy = shape["center"]
        if not math.isfinite(cx + cy + shape["radius"] + shape["area"]):
            raise ValueError(f"{label} contains non-finite circle geometry")
        return
    finite_points(shape["vertices"], label)
    if not math.isfinite(shape["area"]):
        raise ValueError(f"{label} contains non-finite polygon area")


def polygon_axes(poly: list[tuple[float, float]]) -> list[tuple[float, float]]:
    axes: list[tuple[float, float]] = []
    for i, (x1, y1) in enumerate(poly):
        x2, y2 = poly[(i + 1) % len(poly)]
        nx = y1 - y2
        ny = x2 - x1
        length = math.hypot(nx, ny)
        if length > 0.0:
            axes.append((nx / length, ny / length))
    return axes


def project_poly(poly: list[tuple[float, float]], axis: tuple[float, float]) -> tuple[float, float]:
    ax, ay = axis
    vals = [x * ax + y * ay for x, y in poly]
    return min(vals), max(vals)


def project_shape(shape: dict[str, Any], axis: tuple[float, float]) -> tuple[float, float]:
    if shape["kind"] == "polygon":
        return project_poly(shape["vertices"], axis)
    cx, cy = shape["center"]
    center_proj = cx * axis[0] + cy * axis[1]
    radius = shape["radius"]
    return center_proj - radius, center_proj + radius


def circle_vertex_axes(circle: dict[str, Any], poly: list[tuple[float, float]]) -> list[tuple[float, float]]:
    cx, cy = circle["center"]
    axes = []
    for x, y in poly:
        dx = x - cx
        dy = y - cy
        length = math.hypot(dx, dy)
        if length > 1.0e-15:
            axes.append((dx / length, dy / length))
    return axes


def pair_overlap_depth(a: dict[str, Any], b: dict[str, Any]) -> float:
    if a["kind"] == "circle" and b["kind"] == "circle":
        ax, ay = a["center"]
        bx, by = b["center"]
        return a["radius"] + b["radius"] - math.hypot(ax - bx, ay - by)

    axes: list[tuple[float, float]] = []
    if a["kind"] == "polygon":
        axes.extend(polygon_axes(a["vertices"]))
    if b["kind"] == "polygon":
        axes.extend(polygon_axes(b["vertices"]))
    if a["kind"] == "circle" and b["kind"] == "polygon":
        axes.extend(circle_vertex_axes(a, b["vertices"]))
    if b["kind"] == "circle" and a["kind"] == "polygon":
        axes.extend(circle_vertex_axes(b, a["vertices"]))

    best_depth = float("inf")
    for axis in axes:
        a0, a1 = project_shape(a, axis)
        b0, b1 = project_shape(b, axis)
        separation = max(a0 - b1, b0 - a1)
        if separation > 0.0:
            return -separation
        best_depth = min(best_depth, a1 - b0, b1 - a0)
    return best_depth


def signed_polygon_distance(poly: list[tuple[float, float]], point: tuple[float, float]) -> float:
    orientation = 1.0 if polygon_area(poly) >= 0.0 else -1.0
    x, y = point
    best = float("inf")
    for i, (x1, y1) in enumerate(poly):
        x2, y2 = poly[(i + 1) % len(poly)]
        ex = x2 - x1
        ey = y2 - y1
        length = math.hypot(ex, ey)
        if length <= 0.0:
            continue
        signed = orientation * (ex * (y - y1) - ey * (x - x1)) / length
        best = min(best, signed)
    return best


def boundary_excess(shape: dict[str, Any], container: dict[str, Any]) -> float:
    if container["kind"] == "circle":
        cx, cy = container["center"]
        radius = container["radius"]
        if shape["kind"] == "circle":
            x, y = shape["center"]
            return math.hypot(x - cx, y - cy) + shape["radius"] - radius
        return max(math.hypot(x - cx, y - cy) - radius for x, y in shape["vertices"])

    container_poly = container["vertices"]
    if shape["kind"] == "circle":
        return shape["radius"] - signed_polygon_distance(container_poly, shape["center"])
    return max(-signed_polygon_distance(container_poly, point) for point in shape["vertices"])


def compact_geometry_payload(solution: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "case": solution.get("case"),
        "setup": solution.get("setup"),
        "item": solution.get("item"),
        "container": solution.get("container"),
        "placements": solution.get("placements"),
    }
    return payload


def canonical_json(solution: dict[str, Any]) -> str:
    return json.dumps(compact_geometry_payload(solution), sort_keys=True, separators=(",", ":"))


def solution_hash(solution: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(solution).encode("utf-8")).hexdigest()[:16]


def normalize_solution(solution: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(solution)
    normalized["case"] = solution_case(normalized)
    normalized["setup"] = solution_setup(normalized)
    return normalized


def verify_solution(solution: dict[str, Any], tolerance: float = DEFAULT_TOLERANCE) -> VerificationResult:
    errors: list[str] = []
    warnings: list[str] = []
    case = str(solution.get("case") or "")
    setup = str(solution.get("setup") or "")
    side: float | None = None
    metric_symbol: str | None = None
    metric_value: float | None = None
    density: float | None = None
    n = 0

    try:
        tolerance = finite_float(tolerance, "tolerance")
        if tolerance < 0.0:
            raise ValueError("tolerance must be non-negative")

        placements = solution.get("placements")
        if not isinstance(placements, list):
            raise ValueError("placements must be a list")
        n = len(placements)
        if n == 0:
            raise ValueError("placements must not be empty")
        expected_n = parsed_case_count(case)
        if expected_n is not None and expected_n != n:
            errors.append(f"case says n={expected_n}, but placements contains {n} item(s)")

        item = solution["item"]
        container_spec = solution["container"]
        if not isinstance(item, dict) or not isinstance(container_spec, dict):
            raise ValueError("item and container must be objects")

        actual_setup = inferred_setup(item, container_spec)
        if not setup:
            setup = parsed_case_setup(case) or actual_setup
        if not case:
            case = f"{actual_setup}@{n}"
        if not CASE_PATTERN.fullmatch(case):
            errors.append("case must have form '<item>in<container>@<positive integer>'")
        case_setup = parsed_case_setup(case)
        if case_setup is not None and case_setup != actual_setup:
            errors.append(f"case setup {case_setup!r} does not match item/container geometry {actual_setup!r}")
        if setup != actual_setup:
            errors.append(f"setup {setup!r} does not match item/container geometry {actual_setup!r}")
        setup = actual_setup

        container = make_container_shape(container_spec)
        validate_shape_finite(container, "container")
        side = container["side"]
        metric_symbol, metric_value = container_metric(container)
        shapes = [make_item_shape(item, placement) for placement in placements]
        for index, shape in enumerate(shapes, start=1):
            validate_shape_finite(shape, f"placement {index}")
        item_area = sum(shape["area"] for shape in shapes)
        density = item_area / container["area"] if container["area"] > 0.0 else None
        if density is None or not math.isfinite(density):
            errors.append("density is not finite")

        max_boundary = max(boundary_excess(shape, container) for shape in shapes)
        max_overlap = -float("inf")
        for i in range(n):
            for j in range(i + 1, n):
                max_overlap = max(max_overlap, pair_overlap_depth(shapes[i], shapes[j]))
        if max_overlap == -float("inf"):
            max_overlap = 0.0

        if max_boundary > tolerance:
            errors.append(f"boundary protrusion {max_boundary:.6g} exceeds tolerance {tolerance:.3g}")
        if max_overlap > tolerance:
            errors.append(f"pair overlap depth {max_overlap:.6g} exceeds tolerance {tolerance:.3g}")

        return VerificationResult(
            ok=not errors,
            case=case,
            setup=setup,
            n=n,
            side=side,
            metric_symbol=metric_symbol,
            metric_value=metric_value,
            density=density,
            max_boundary_excess=max_boundary,
            max_pair_overlap_depth=max_overlap,
            tolerance=tolerance,
            errors=errors,
            warnings=warnings,
        )
    except Exception as exc:
        errors.append(str(exc))
        return VerificationResult(
            ok=False,
            case=case,
            setup=setup,
            n=n,
            side=side,
            metric_symbol=metric_symbol,
            metric_value=metric_value,
            density=density,
            max_boundary_excess=float("nan"),
            max_pair_overlap_depth=float("nan"),
            tolerance=tolerance,
            errors=errors,
            warnings=warnings,
        )


def close_enough(a: Any, b: Any, tolerance: float) -> bool:
    try:
        left = float(a)
        right = float(b)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(left + right):
        return False
    return abs(left - right) <= max(tolerance, abs(right) * tolerance)


def verify_record_solution(
    record: dict[str, Any],
    solution: dict[str, Any],
    tolerance: float = DEFAULT_TOLERANCE,
) -> list[str]:
    """Verify that a stored leaderboard row agrees with its coordinate JSON."""

    result = verify_solution(solution, tolerance=tolerance)
    errors = list(result.errors)
    if str(record.get("case") or "") != result.case:
        errors.append(f"record case {record.get('case')!r} does not match verified case {result.case!r}")
    if str(record.get("setup") or "") != result.setup:
        errors.append(f"record setup {record.get('setup')!r} does not match verified setup {result.setup!r}")
    try:
        record_n = int(record.get("n"))
    except (TypeError, ValueError):
        record_n = -1
    if record_n != result.n:
        errors.append(f"record n {record.get('n')!r} does not match verified n {result.n}")

    if record.get("side") is not None and not close_enough(record.get("side"), result.side, tolerance):
        errors.append(f"record side {record.get('side')!r} does not match verified side {result.side!r}")

    record_symbol = record.get("metric_symbol")
    if record_symbol is not None and str(record_symbol) != str(result.metric_symbol):
        errors.append(f"record metric_symbol {record_symbol!r} does not match verified metric_symbol {result.metric_symbol!r}")

    record_metric = record.get("metric_value")
    if record_metric is not None and not close_enough(record_metric, result.metric_value, tolerance):
        errors.append(f"record metric_value {record_metric!r} does not match verified metric_value {result.metric_value!r}")
    return errors


def load_solution_json(text: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"invalid JSON numeric constant {value}")

    payload = json.loads(text, parse_constant=reject_constant)
    if not isinstance(payload, dict):
        raise ValueError("submission JSON must be an object")
    return payload
