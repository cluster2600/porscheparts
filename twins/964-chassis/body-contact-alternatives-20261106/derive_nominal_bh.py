#!/usr/bin/env python3
"""Derive a source-only Mi B/H pattern; never read or register donor geometry."""

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; use a fresh path.")

    here = Path(__file__).resolve().parent
    root = here.parents[2]
    source_path = root / "twins/964-chassis/owner-frame-data-20261105/source-data.json"
    raw = source_path.read_bytes()
    expected = "562b27859d7e717179b4d60f5dd501fd7641107f4180b50fdd17647596045a15"
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Original source-data digest mismatch.")
    source = json.loads(raw)["mi"]
    correction_path = here / "mi-b-width-correction.json"
    correction_raw = correction_path.read_bytes()
    correction = json.loads(correction_raw)
    if not (
        correction["classification"] == "independently_reviewed_documentary_reading_correction"
        and correction["point_id"] == "B"
        and correction["source_sha256"] == "9986c8e5db0827328f4fe38ed9b2655dc6bc1f6253ce55c071c7266b7ddfab1c"
        and correction["source_only_use_admitted"] is True
        and correction["combined_equal_opposed_span"] == 612
        and correction["scan_contact_admitted"] is False
    ):
        raise ValueError("Source-only B correction is not the reviewed input.")

    by_id = {row["point_id"]: row for row in source["points"]}

    def projection(a, b):
        rows = [r for r in source["longitudinal_projections"] if (r["from"], r["to"]) == (a, b)]
        if len(rows) != 1:
            raise ValueError("Source projection is missing or ambiguous.")
        return rows[0]["printed_value"]

    positions = {
        "B": -projection("B", "F"),
        "H": projection("F", "G") + projection("G", "H"),
    }
    widths = {
        "B": correction["combined_equal_opposed_span"],
        "H": by_id["H"]["combined_equal_left_right_width"],
    }
    points = {
        f"{letter}_{side}": [positions[letter], sign * widths[letter] / 2,
                              by_id[letter]["height_above_printed_datum_line"]["bolt_head"]]
        for letter in ("B", "H") for side, sign in (("plus", 1), ("minus", -1))
    }
    p = points["B_plus"]
    u = [b - a for a, b in zip(p, points["B_minus"])]
    v = [b - a for a, b in zip(p, points["H_plus"])]
    normal = [u[1] * v[2] - u[2] * v[1],
              u[2] * v[0] - u[0] * v[2],
              u[0] * v[1] - u[1] * v[0]]
    length = math.sqrt(sum(a * a for a in normal))
    if length == 0:
        raise ValueError("Source points are collinear.")

    def signed_distance(q):
        return sum(n * (b - a) for n, a, b in zip(normal, p, q)) / length

    if any(signed_distance(q) != 0 for q in points.values()):
        raise ValueError("This source-only two-station pattern is not coplanar.")

    holdouts = []
    for letter in ("A", "I", "J"):
        x = (-projection("A", "F") if letter == "A"
             else projection("F", "G") + projection("G", letter))
        q = [x, by_id[letter]["half_width_if_equal_sides"],
             by_id[letter]["height_above_printed_datum_line"]["bolt_head"]]
        holdouts.append({"source_point": letter, "source_plus_placeholder": q,
                         "distance_from_source_BH_plane": abs(signed_distance(q)),
                         "exact_donor_contact_observed": False,
                         "metric_holdout_admitted": False})

    result = {
        "classification": "nominal_source_only_Mi_BH_algebra_not_donor_registration",
        "source_data_sha256": expected,
        "B_correction_sha256": hashlib.sha256(correction_raw).hexdigest(),
        "derivation_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_families_used": ["Mi3, with the already-reviewed Mi4 I-width cross-reference"],
        "assembly_state": "bolt_head_only_not_parts_removed_frame",
        "frame": "F station X=0; X increases rearward; Z is above printed datum. Side signs are mathematical placeholders; donor side/handedness remains unassigned.",
        "unit": "interpreted_mm",
        "points": points,
        "pair_distances": [{"a": a, "b": b, "distance": math.dist(points[a], points[b])}
                           for a, b in itertools.combinations(points, 2)],
        "source_rank": 2,
        "source_plane": {"point": p, "unit_normal": [n / length for n in normal],
                         "independent_off_plane_check_supplied_by_quartet": False},
        "candidate_holdout_geometry_only": holdouts,
        "numeric_precision": "Calculator precision only; no measurement accuracy or tolerance inferred.",
        "source_uncertainty": None,
        "scan_localisation_uncertainty": None,
        "registration_acceptance_limits": None,
        "source_dimensions_used_to_identify_scan_features": False,
        "scan_geometry_read": False,
        "donor_transform": None,
        "scan_registration_admitted": False,
        "functional_geometry_admitted": False,
        "required_before_metric_use": "Independently identified acquired head patches and contact definitions, admitted units/uncertainty/application, physical side/handedness, at least one off-plane named holdout and a further unused body-contact or distance check.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(f"Wrote source-only nominal network: {args.output}")


if __name__ == "__main__":
    main()
