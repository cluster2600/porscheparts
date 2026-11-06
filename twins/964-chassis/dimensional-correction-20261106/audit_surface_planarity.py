#!/usr/bin/env python3
"""Independent whole-control-net intrinsic planarity audit of frozen F2.

No generator/CAD imports. Mathematical EPS is not an OEM or metrology tolerance.
A tilted plane is planar. A non-coplanar net is not reported as a measured
surface error: control-pole residuals bound a Bezier surface, not conversely.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

EPS_MM = 1e-8
F2_SHA = "1d323e7441c31ef8e5e5b26b895a2a0629bbf97402a274ccd416bc82a95444a2"


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def norm(v):
    return math.sqrt(sum(x*x for x in v))


def bezier_segment(points, i, closed=False):
    at = lambda j: points[j % len(points) if closed else min(max(j, 0), len(points)-1)]
    before, start, end, after = [at(j) for j in (i-1, i, i+1, i+2)]
    return [start, [start[k]+(end[k]-before[k])/6 for k in range(3)],
            [end[k]-(after[k]-start[k])/6 for k in range(3)], end]


def tensor_poles(component, span=None):
    rows = component["sections_mm"]
    if component.get("profile_z_tangents_mm") is not None:
        raise ValueError("This frozen-F2 audit supports Catmull-Rom, not a new interpolation law")
    lo, hi = span or component.get("v_range", [0, len(rows[0])-int(not component["closed_profile"])])
    poles = []
    for v in range(lo, hi):
        profiles = [bezier_segment(row, v, component["closed_profile"]) for row in rows]
        for u in range(len(rows)-1):
            for j in range(4):
                poles.extend(bezier_segment([profile[j] for profile in profiles], u))
    return poles, (len(rows)-1)*(hi-lo)


def plane_certificate(points):
    if not points or any(len(p) != 3 or not all(math.isfinite(x) for x in p) for p in points):
        raise ValueError("Require finite XYZ poles")
    origin = points[0]
    arm = max((sub(p, origin) for p in points), key=norm)
    width = norm(arm)
    normal = max((cross(arm, sub(p, origin)) for p in points), key=norm)
    height = norm(normal)/width if width > EPS_MM else 0
    if height <= EPS_MM:
        return {"control_net_coplanar": False, "degenerate_point_or_line": True,
                "horizontal_level": False, "passed": False}
    normal = [x/norm(normal) for x in normal]
    residual = max(abs(sum(x*y for x, y in zip(normal, sub(p, origin)))) for p in points)
    coplanar = residual <= EPS_MM
    return {"control_net_coplanar": coplanar, "degenerate_point_or_line": False,
        "reference_plane_unit_normal": normal, "reference_plane_point_mm": origin,
        "maximum_control_pole_distance_to_reference_plane_mm": residual,
        "horizontal_level": coplanar and max(p[2] for p in points)-min(p[2] for p in points) <= EPS_MM,
        "reference_plane_method": "Longest origin baseline and widest control-pole arm; not a least-squares fit",
        "passed": coplanar}


def audit(model):
    components = {c["name"]: c for c in model["components"]}
    selections = [(name, components[name]["v_range"]) for name in ("floor_bay_right", "floor_bay_left")]
    selections += [(name, [15, 16]) for name in ("sill_right", "sill_left")]
    selections += [("tunnel_lower_return", [1, 2])]
    results = []
    for name, span in selections:
        poles, count = tensor_poles(components[name], span)
        results.append({"component": name, "global_V_span": span,
                        "whole_bicubic_patches": count, "control_poles_checked_with_repeats": len(poles),
                        **plane_certificate(poles)})
    return {"regions": results, "intrinsic_planarity_passed": all(r["passed"] for r in results)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=Path(__file__).resolve().parents[1]/"sculpted-cell-f2-20261106/canonical-model.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    if args.output.exists() or sha(args.model) != F2_SHA:
        parser.error("Require exact frozen F2 and a fresh output file")
    result = audit(json.loads(args.model.read_text()))
    result.update({"classification": "whole_control_net_intrinsic_shape_audit_not_OEM_comparison",
        "model_sha256": sha(args.model), "audit_source_sha256": sha(Path(__file__)), "mathematical_EPS_mm": EPS_MM,
        "EPS_is_OEM_or_measurement_tolerance": False, "coordinate_registration_required_for_intrinsic_planarity": False,
        "certificate_scope": "All tensor Bezier poles checked. A coplanar net bounds the whole surface within EPS of this plane. Non-coplanar coefficients reject exact planarity; their maximum residual is not an actual surface-error lower bound.",
        "surface_regularity_or_injectivity_proven": False, "original_Porsche_dimensional_delta_mm": None,
        "physical_or_manufacturing_admission": False})
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"intrinsic_planarity_passed": result["intrinsic_planarity_passed"], "regions": len(result["regions"])}))
    return 0 if result["intrinsic_planarity_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
