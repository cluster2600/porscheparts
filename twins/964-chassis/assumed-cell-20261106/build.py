#!/usr/bin/env python3
"""Build a canonical assumed tub, shared by CAD and the layered-shell analysis.

Rectangular midplanes are the editable geometry contract, not observed surfaces.
The STEP and PicoGK representations thicken these same planes symmetrically.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def build(parameters: dict, variant: str = "baseline") -> dict:
    d = dict(parameters["dimensions_mm"])
    d.update(parameters["variants"][variant])
    length, half = d["length"], d["width"] / 2
    inner, tw = half - d["sill_width"], d["tunnel_width"] / 2
    sh, th, thickness = d["sill_height"], d["tunnel_height"], d["wall_thickness"]
    assert length > 0 and half > inner > tw > thickness > 0
    assert min(sh, th, d["seat_crossmember_height"]) > 2 * thickness
    assert min(d["front_bulkhead_height"], d["rear_bulkhead_height"]) > max(sh, th)
    panels = []

    def panel(name, component, normal, at, u0, u1, v0, v1):
        u, v = ((1, 2), (2, 0), (0, 1))[normal]
        assert u1 > u0 and v1 > v0
        panels.append(dict(name=name, component=component, normal_axis=normal,
                           at_mm=at, u_axis=u, v_axis=v,
                           u_mm=[u0, u1], v_mm=[v0, v1]))

    panel("floor", "floor", 2, 0, 0, length, -half, half)
    for sign, side in ((-1, "right"), (1, "left")):
        for y, name in ((sign * inner, "inner"), (sign * half, "outer")):
            panel(f"sill_{side}_{name}", "sills", 1, y, 0, sh, 0, length)
        lo, hi = sorted((sign * inner, sign * half))
        panel(f"sill_{side}_top", "sills", 2, sh, 0, length, lo, hi)
    if not d.get("omit_tunnel", False):
        for sign, side in ((-1, "right"), (1, "left")):
            panel(f"tunnel_{side}", "tunnel", 1, sign * tw, 0, th, 0, length)
        panel("tunnel_roof", "tunnel", 2, th, 0, length, -tw, tw)
    for x, height, name in ((0, d["front_bulkhead_height"], "front_bulkhead"),
                            (length, d["rear_bulkhead_height"], "rear_bulkhead")):
        # The lower central passage stays open through both end walls.
        panel(name + "_right", name, 0, x, -half, -tw, 0, th)
        panel(name + "_left", name, 0, x, tw, half, 0, th)
        panel(name + "_upper", name, 0, x, -half, half, th, height)
    ch = d["seat_crossmember_height"]
    for i, centre in enumerate(d["seat_crossmember_x"], 1):
        x0, x1 = centre - d["seat_crossmember_width"] / 2, centre + d["seat_crossmember_width"] / 2
        assert 0 < x0 < x1 < length
        for y0, y1, side in ((-inner, -tw, "right"), (tw, inner, "left")):
            prefix = f"seat_crossmember_{i}_{side}"
            panel(prefix + "_top", "seat_crossmembers", 2, ch, x0, x1, y0, y1)
            for x, end in ((x0, "front"), (x1, "rear")):
                panel(prefix + "_" + end, "seat_crossmembers", 0, x, y0, y1, 0, ch)
            # On the tunnel-omitted control, preserve closed beam end caps.
            if d.get("omit_tunnel", False):
                panel(prefix + "_inboard_cap", "seat_crossmembers", 1,
                      y1 if side == "right" else y0, 0, ch, x0, x1)

    axes = [set() for _ in range(3)]
    area = defaultdict(float)
    boxes = []
    for p in panels:
        n, u, v = p["normal_axis"], p["u_axis"], p["v_axis"]
        axes[n].add(p["at_mm"])
        axes[u].update(p["u_mm"]); axes[v].update(p["v_mm"])
        area[p["component"]] += (p["u_mm"][1] - p["u_mm"][0]) * (p["v_mm"][1] - p["v_mm"][0])
        lo, hi = [0.0] * 3, [0.0] * 3
        lo[n], hi[n] = p["at_mm"] - thickness / 2, p["at_mm"] + thickness / 2
        lo[u], hi[u] = p["u_mm"]; lo[v], hi[v] = p["v_mm"]
        boxes.append({"name": p["name"], "min_mm": lo, "max_mm": hi})
    for i, p in enumerate(panels):
        for q in panels[i + 1:]:
            if p["normal_axis"] == q["normal_axis"] and p["at_mm"] == q["at_mm"]:
                overlap = all(min(p[k][1], q[k][1]) > max(p[k][0], q[k][0]) for k in ("u_mm", "v_mm"))
                assert not overlap, ("Coplanar duplicate area", p["name"], q["name"])
    shell_area = sum(area.values())
    # Area*t is shell mass, distinct from intersecting CAD-plate union volume.
    result = dict(study_id=parameters["study_id"], variant=variant, units="mm", status="assumed",
                  donor_transform=None, physical_interfaces_admitted=False,
                  thickness_mm=thickness, dimensions_mm=d,
                  axis_breaks_mm={k: sorted(a) for k, a in zip("xyz", axes)},
                  panels=panels, plate_boxes=boxes, area_by_component_mm2=dict(area),
                  shell_area_mm2=shell_area,
                  nominal_shell_mass_kg=shell_area * thickness * parameters["laminate"]["density_kg_m3"] / 1e9,
                  tunnel_clear_reservation_mm=None if d.get("omit_tunnel", False) else
                  {"width": 2 * tw - thickness, "height": th - thickness, "length": length,
                   "status": "Assumed rectangular void only; no linkage/drivetrain fit or motion check."},
                  upstream_audit={"scope": "Explicit hypothesis-only synthetic geometry",
                                  "verdict": "admitted_for_conditional_linear_stiffness_study_only",
                                  "coplanar_area_duplicates": 0,
                                  "contact_or_scan_coordinates_used": False,
                                  "sharp_junctions": "Ideal plate intersections; no strength/peak-stress interpretation."})
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--parameters", type=Path, default=HERE / "assumptions.json")
    ap.add_argument("--variant", default="baseline")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("Output already exists; use a fresh run directory.")
    raw = args.parameters.read_bytes()
    result = build(json.loads(raw), args.variant)
    result["parameters_sha256"] = hashlib.sha256(raw).hexdigest()
    result["builder_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "panels": len(result["panels"]),
                      "variant": args.variant, "nominal_shell_mass_kg": result["nominal_shell_mass_kg"]}))


if __name__ == "__main__":
    main()
