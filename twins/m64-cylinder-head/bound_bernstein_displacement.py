#!/usr/bin/env python3
"""Bound a stored displacement polynomial on the complete normalized UV square.

Every subdivision operation is rational and exact for the input IEEE floats.
This checks the stored scalar polynomial, not OCCT evaluation, trimmed-face
embedding, thickness, solid validity, fitment, or manufacturing readiness.
"""
import argparse
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path


def coefficient_grid(rows):
    if not rows or not rows[0] or len(rows) > 26 or len(rows[0]) > 26:
        raise ValueError("expected nonempty degree-at-most-25 coefficient grid")
    width = len(rows[0])
    result = []
    for row in rows:
        if len(row) != width:
            raise ValueError("ragged coefficient grid")
        converted = []
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("expected finite numeric coefficients")
            if not math.isfinite(value):
                raise ValueError("expected finite numeric coefficients")
            converted.append(Fraction(value))
        result.append(tuple(converted))
    return tuple(result)


def split_curve(values):
    """Exact de Casteljau subdivision at one half."""
    level = tuple(values)
    left, right = [level[0]], [level[-1]]
    while len(level) > 1:
        level = tuple((a + b) / 2 for a, b in zip(level, level[1:]))
        left.append(level[0])
        right.append(level[-1])
    return tuple(left), tuple(reversed(right))


def split_square(grid):
    columns = [split_curve(column) for column in zip(*grid)]
    left_u = tuple(zip(*(column[0] for column in columns)))
    right_u = tuple(zip(*(column[1] for column in columns)))
    children = []
    for half in (left_u, right_u):
        rows = [split_curve(row) for row in half]
        children.extend((tuple(row[0] for row in rows), tuple(row[1] for row in rows)))
    return children


def prove_bound(rows, limit=1.0, max_depth=10, max_boxes=4096):
    if isinstance(limit, bool) or not isinstance(limit, (int, float)) or not math.isfinite(limit) or limit <= 0:
        raise ValueError("limit must be positive and finite")
    if type(max_depth) is not int or not 0 <= max_depth <= 20:
        raise ValueError("max_depth must be an integer from 0 to 20")
    if type(max_boxes) is not int or not 1 <= max_boxes <= 100000:
        raise ValueError("max_boxes must be an integer from 1 to 100000")
    grid = coefficient_grid(rows)
    exact_limit = Fraction(limit)
    pending, accepted, unresolved = [(grid, 0)], [], []
    visited, deepest = 0, 0
    status = "proven"
    while pending:
        if visited == max_boxes:
            status = "inconclusive_resource_limit"
            break
        patch, depth = pending.pop()
        visited += 1
        deepest = max(deepest, depth)
        absolute_hull = max(abs(value) for row in patch for value in row)
        if absolute_hull <= exact_limit:
            accepted.append(absolute_hull)
            continue
        # Corners interpolate actual polynomial values, unlike interior poles.
        corners = [patch[0][0], patch[0][-1], patch[-1][0], patch[-1][-1]]
        if max(abs(value) for value in corners) > exact_limit:
            status = "outside_bound_on_full_square"
            break
        if depth == max_depth:
            unresolved.append(absolute_hull)
            status = "inconclusive_depth_limit"
            continue
        pending.extend((child, depth + 1) for child in split_square(patch))
    proven = status == "proven" and not pending and not unresolved
    result = {
        "status": status,
        "proven_on_full_square": proven,
        "domain": "complete_normalized_UV_square_0_1_including_untrimmed_regions",
        "coefficient_interpretation": "exact_rational_value_of_each_stored_IEEE_float",
        "arithmetic": "exact_rational_de_Casteljau_at_one_half",
        "limit_exact": str(exact_limit),
        "polynomial_bidegree": [len(grid) - 1, len(grid[0]) - 1],
        "visited_boxes": visited,
        "accepted_boxes": len(accepted),
        "unresolved_boxes": len(unresolved) + len(pending),
        "deepest_subdivision": deepest,
        "max_depth": max_depth,
        "max_boxes": max_boxes,
        "native_OCCT_roundoff_bound_included": False,
        "geometry_or_manufacturing_authorized": False,
    }
    if proven:
        bound = max(accepted)
        displayed = float(bound)
        if Fraction(displayed) < bound:
            displayed = math.nextafter(displayed, math.inf)
        result.update(max_absolute_value_bound_exact=str(bound),
                      max_absolute_value_bound_rounded_outward=displayed)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coefficients", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=float, default=1.0)
    parser.add_argument("--max-depth", type=int, default=10)
    parser.add_argument("--max-boxes", type=int, default=4096)
    args = parser.parse_args()
    import numpy as np
    # Hash exactly the immutable byte snapshot from which coefficients are read.
    payload = args.coefficients.read_bytes()
    with np.load(io.BytesIO(payload), allow_pickle=False) as data:
        amplitude = data["amplitude"]
        if amplitude.ndim != 2 or amplitude.dtype.kind not in "fiu":
            raise ValueError("amplitude must be a real two-dimensional array")
        result = prove_bound(amplitude.tolist(), args.limit, args.max_depth, args.max_boxes)
    result["input_sha256"] = hashlib.sha256(payload).hexdigest()
    result["implementation_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
