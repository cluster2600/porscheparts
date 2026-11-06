#!/usr/bin/env python3
"""Screen complete display triangles against assumed static wheel cylinders.

Clipping each triangle to the wheel's lateral slab catches intersections missed
by a vertex-only test. This is a tessellation diagnostic, not a swept suspension
envelope, CAD containment proof or vehicle fitment check.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def clip_y(polygon, limit, keep_above):
    result = []
    if not polygon:
        return result
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        inside_a = a[1] >= limit if keep_above else a[1] <= limit
        inside_b = b[1] >= limit if keep_above else b[1] <= limit
        if inside_a:
            result.append(a)
        if inside_a != inside_b:
            t = (limit - a[1]) / (b[1] - a[1])
            result.append([a[k] + t*(b[k] - a[k]) for k in range(3)])
    return result


def distance_squared_to_segment(a, b):
    v = [b[k] - a[k] for k in range(2)]
    length2 = sum(x*x for x in v)
    t = min(1., max(0., -sum(a[k]*v[k] for k in range(2))/length2)) if length2 else 0.
    return sum((a[k] + t*v[k])**2 for k in range(2))


def minimum_radius(triangle, centre, half_width):
    """Minimum axis radius of the triangle portion inside the finite Y slab."""
    polygon = clip_y(triangle, centre[1] - half_width, True)
    polygon = clip_y(polygon, centre[1] + half_width, False)
    if not polygon:
        return None
    p = [[q[0] - centre[0], q[2] - centre[2]] for q in polygon]
    area2 = sum(a[0]*b[1] - a[1]*b[0] for a, b in zip(p, p[1:] + p[:1]))
    signs = [(b[0]-a[0])*(-a[1]) - (b[1]-a[1])*(-a[0])
             for a, b in zip(p, p[1:] + p[:1])]
    if abs(area2) > 1e-12 and (all(x >= 0 for x in signs) or all(x <= 0 for x in signs)):
        return 0.
    return math.sqrt(min(distance_squared_to_segment(a, b) for a, b in zip(p, p[1:] + p[:1])))


def controls():
    centre = [0., 0., 0.]
    # All three vertices lie outside radius 1, but the face covers its axis.
    face = [[-2., 0., -2.], [2., 0., -2.], [0., 0., 2.]]
    assert all(math.hypot(p[0], p[2]) > 1 for p in face)
    assert minimum_radius(face, centre, .5) == 0
    assert minimum_radius([[x, 2., z] for x, _, z in face], centre, .5) is None
    assert math.isclose(minimum_radius([[2., 0., -1.], [2., 0., 1.], [3., 0., 0.]], centre, .5), 2.)
    # Projection is a line; it must not be mistaken for an axis-containing area.
    assert math.isclose(minimum_radius([[2., -.25, 0.], [2., .25, 0.], [3., 0., 0.]], centre, .5), 2.)
    # A triangle can cross the lateral slab even when all its vertices are outside.
    assert minimum_radius([[-2., -2., 0.], [2., 2., 0.], [2., -2., 0.]], centre, .5) == 0
    return 5


def audit(display, parameters):
    if parameters["status"] != "assumed" or parameters["physical_interfaces_admitted"]:
        raise ValueError("This screen only accepts the explicit hypothetical design frame")
    d = parameters["assembly_proxy_parameters"]
    result = []
    axles = d.get("axles") or [
        {"id": name, "x_mm": x, "half_track_mm": d["wheel_centre_y_mm"],
         "centre_z_mm": d["wheel_centre_z_mm"], "tyre_width_mm": d["tyre_width_mm"],
         "tyre_outer_radius_mm": d["tyre_outer_radius_mm"]}
        for name, x in zip(("front", "rear"), d["axle_x_mm"])]
    for axle in axles:
        for side in (-1, 1):
            centre = [axle["x_mm"], side*axle["half_track_mm"], axle["centre_z_mm"]]
            components = []
            for component in display["components"]:
                if component["scope"] != "structural_cell":
                    continue
                points = component["vertices_mm"]
                minimum, hits, candidates = None, 0, 0
                for indices in component["triangles"]:
                    radius = minimum_radius([points[i] for i in indices], centre, axle["tyre_width_mm"]/2)
                    if radius is None:
                        continue
                    candidates += 1
                    minimum = radius if minimum is None else min(minimum, radius)
                    hits += radius < axle["tyre_outer_radius_mm"] - 1e-7
                components.append({"name": component["name"], "triangles_in_lateral_slab": candidates,
                                   "minimum_axis_radius_in_slab_mm": minimum,
                                   "intersecting_triangle_count": hits})
            result.append({"wheel": axle["id"] + ("_left" if side > 0 else "_right"),
                           "centre_mm": centre, "radius_mm": axle["tyre_outer_radius_mm"],
                           "width_mm": axle["tyre_width_mm"], "components": components,
                           "surface_intersection_detected": any(c["intersecting_triangle_count"] for c in components)})
    return result


def envelope(display, parameters):
    budget = parameters.get("programme_envelope")
    if not budget:
        return None
    points = [p for c in display["components"] if c["scope"] == "structural_cell"
              for p in c["vertices_mm"]]
    low = [min(p[k] for p in points) for k in range(3)]
    high = [max(p[k] for p in points) for k in range(3)]
    ground = parameters["assembly_proxy_parameters"]["ground_z_mm"]
    height, width, clearance = high[2]-ground, high[1]-low[1], low[2]-ground
    return {"bounds_mm": [low, high], "assumed_ground_z_mm": ground,
            "frame_height_mm": height, "width_mm": width, "ground_clearance_mm": clearance,
            "height_within_design_budget": height <= budget["assumed_structural_frame_height_limit_mm"],
            "width_within_design_budget": width <= budget["assumed_structural_width_limit_mm"],
            "clearance_within_design_budget": clearance >= budget["assumed_static_ground_clearance_budget_mm"],
            "scope": "Bounds of the supplied display vertices only; no continuous CAD bound, loading condition, body fit or compliance admission."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--display-manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--parameters", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a fresh output path")
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    if sha(args.display_manifest) != args.manifest_sha256:
        parser.error("Display manifest hash mismatch")
    checks = controls()
    display, parameters = json.loads(args.display_manifest.read_text()), json.loads(args.parameters.read_text())
    wheels = audit(display, parameters)
    result = {"classification": "complete_triangle_static_proxy_cylinder_intersection_diagnostic",
              "source_sha256": sha(__file__), "display_manifest_sha256": args.manifest_sha256,
              "parameter_sha256": sha(args.parameters), "synthetic_controls_passed": checks,
              "wheels": wheels, "surface_intersection_detected": any(w["surface_intersection_detected"] for w in wheels),
              "sampled_programme_envelope": envelope(display, parameters),
              "limits": ["Piecewise-linear input surfaces only; no BRep tessellation error bound or solid-containment test.",
                         "Fixed assumed wheel cylinders; no steering, suspension travel, tyre deformation or tolerance reserve.",
                         "Counts depend on tessellation. An intersection is a rejection witness; no intersection is not vehicle-fitment admission."],
              "physical_or_manufacturing_validation": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"surface_intersection_detected": result["surface_intersection_detected"],
                      "intersecting_triangles_by_wheel": {w["wheel"]: sum(c["intersecting_triangle_count"] for c in w["components"]) for w in wheels}}))


if __name__ == "__main__":
    main()
