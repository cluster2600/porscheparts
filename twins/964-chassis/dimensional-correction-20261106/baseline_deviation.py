#!/usr/bin/env python3
"""Measure non-planarity witnesses in the frozen, assumed F2 control surfaces.

This independent stdlib calculation does not import the geometry generator,
measure images, identify Porsche surfaces or compute an OEM dimensional delta.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


F2_SHA256 = "1d323e7441c31ef8e5e5b26b895a2a0629bbf97402a274ccd416bc82a95444a2"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def polynomial(points):
    """Ascending scalar coefficients of the segment between points 1 and 2."""
    a, b, c, d = points
    return [b, (-a+c)/2, (2*a-5*b+4*c-d)/2, (-a+3*b-3*c+d)/2]


def value(coefficients, t):
    return sum(c*t**i for i, c in enumerate(coefficients))


def minimum(coefficients):
    _, b, c, d = coefficients
    candidates = [0., 1.]
    if d:
        discriminant = 4*c*c-12*d*b
        if discriminant >= 0:
            candidates += [(-2*c+sign*math.sqrt(discriminant))/(6*d) for sign in (-1, 1)]
    elif c:
        candidates.append(-b/(2*c))
    return min(((t, value(coefficients, t)) for t in candidates if 0 <= t <= 1), key=lambda p: p[1])


def row_at(component, x):
    rows = [r for r in component["sections_mm"] if all(p[0] == x for p in r)]
    if len(rows) != 1:
        raise ValueError("Require one actual control row at the named X station")
    return rows[0]


def audit(model):
    if model["study_id"] != "964-CENTRAL-CELL-SCULPTED-F2" or model["units"] != "mm":
        raise ValueError("Require the frozen F2 millimetre study")
    components = {c["name"]: c for c in model["components"]}
    sill = components["sill_left"]
    segment = sill["profile_landmarks"]["outer_lower_corner"]
    controls = [[r[(segment+k) % len(r)][2] for k in (-1, 0, 1, 2)] for r in sill["sections_mm"]]
    if any(r != controls[0] for r in controls):
        raise ValueError("Sill bottom segment differs between source stations")
    coefficients = polynomial(controls[0])
    t, z = minimum(coefficients)
    if controls[0][1] != controls[0][2]:
        raise ValueError("The two source bottom landmarks are not level")
    floor = components["floor_bay_left"]
    first, last = floor["v_range"]
    floor_row = row_at(floor, 600)
    floor_z = [p[2] for p in floor_row[first:last+1]]
    lowest_control = min(range(first, last+1), key=lambda i: floor_row[i][2])
    stations = [0, 600, 1400, 2100]
    longitudinal_z = [row_at(floor, x)[lowest_control][2] for x in stations]
    tunnel = components["tunnel_lower_return"]
    tunnel_z = {str(x): value(polynomial([p[2] for p in row_at(tunnel, x)]), .5)
                for x in (0, 600, 2100)}
    return {
        "sill": {"component": sill["name"], "segment_index": segment,
            "actual_four_control_Z_mm": controls[0], "station_rows_checked": len(controls),
            "polynomial_ascending_Z_mm": coefficients, "minimum_local_t": t,
            "minimum_midsurface_Z_mm": z, "level_landmarks_Z_mm": controls[0][1],
            "departure_below_landmark_plane_mm": controls[0][1]-z,
            "scope": "Algebraic extremum of this actual scalar cubic, not a whole-wall or native-mesh bound"},
        "floor": {"component": floor["name"], "station_X_mm": 600,
            "actual_active_control_Z_mm": floor_z, "control_height_spread_mm": max(floor_z)-min(floor_z),
            "longitudinal_control_index": lowest_control, "longitudinal_X_mm": stations,
            "longitudinal_Z_mm": longitudinal_z,
            "rear_rise_from_X600_mm": longitudinal_z[-1]-longitudinal_z[1],
            "scope": "Actual source control heights; not full interpolated surface extrema or original Porsche dimensions"},
        "tunnel_lower_return": {"component": tunnel["name"], "profile_parameter_v": 1.5,
            "centre_midsurface_Z_at_X_mm": tunnel_z,
            "scope": "Scalar cubic evaluated between the two central controls; no native thickness/voxel or continuous-clearance inference"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=Path(__file__).resolve().parents[1] /
                        "sculpted-cell-f2-20261106/canonical-model.json")
    parser.add_argument("--output", type=Path, required=True, help="Fresh output directory")
    args = parser.parse_args()
    if args.output.exists() or sha(args.model) != F2_SHA256:
        parser.error("Require a fresh output and the exact frozen F2 canonical bytes")
    result = {"classification": "frozen_F2_internal_nonplanarity_witness_not_OEM_comparison",
              "model_sha256": sha(args.model), "audit_source_sha256": sha(__file__),
              "units": "mm", "witnesses": audit(json.loads(args.model.read_text())),
              "OEM_model_comparison_delta_mm": None, "donor_frame_registered": False,
              "whole_surface_planarity_or_functional_admission": False,
              "scope": "Shows why level landmarks did not establish planar F2 surfaces. No donor geometry or replacement floor depth is inferred."}
    if sha(args.model) != F2_SHA256 or sha(__file__) != result["audit_source_sha256"]:
        raise ValueError("Audit input or implementation changed during execution")
    args.output.mkdir(parents=True)
    (args.output / "baseline-deviation.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(json.dumps(result["witnesses"]["sill"]))


if __name__ == "__main__":
    main()
