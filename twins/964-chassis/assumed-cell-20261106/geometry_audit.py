#!/usr/bin/env python3
"""Independent box-union and straight-pull tooling checks for the assumed tub.

This checks the stated synthetic contract. It supplies no measured interfaces,
laminate strength, draft-angle, draping or cure qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def overlap(a, b, axes=(0, 1, 2)):
    return all(min(a["max_mm"][k], b["max_mm"][k]) >
               max(a["min_mm"][k], b["min_mm"][k]) for k in axes)


def union_volume(boxes):
    """Exact Cartesian sweep, merging intervals instead of voxel sampling."""
    xs = sorted({b[k][0] for b in boxes for k in ("min_mm", "max_mm")})
    volume = 0.0
    for x0, x1 in zip(xs, xs[1:]):
        active = [b for b in boxes if b["min_mm"][0] < (x0 + x1) / 2 < b["max_mm"][0]]
        ys = sorted({b[k][1] for b in active for k in ("min_mm", "max_mm")})
        area = 0.0
        for y0, y1 in zip(ys, ys[1:]):
            intervals = sorted((b["min_mm"][2], b["max_mm"][2]) for b in active
                               if b["min_mm"][1] < (y0 + y1) / 2 < b["max_mm"][1])
            total, lo, hi = 0.0, None, None
            for start, end in intervals:
                if lo is None:
                    lo, hi = start, end
                elif start > hi:
                    total += hi - lo
                    lo, hi = start, end
                else:
                    hi = max(hi, end)
            if lo is not None:
                total += hi - lo
            area += (y1 - y0) * total
        volume += (x1 - x0) * area
    return volume


def pull(core, boxes, axis, sign, travel):
    """Continuous AABB translation: first strict overlap, not sampled frames."""
    obstacles = []
    others = [k for k in range(3) if k != axis]
    for box in boxes:
        if not overlap(core, box, others):
            continue
        a, b = core["min_mm"][axis], core["max_mm"][axis]
        c, d = box["min_mm"][axis], box["max_mm"][axis]
        entry, leave = (c - b, d - a) if sign > 0 else (a - d, b - c)
        entry = max(0.0, entry)
        if leave > entry and entry < travel:
            obstacles.append((entry, box["name"]))
    obstacles.sort()
    return {"direction": ("+" if sign > 0 else "-") + "XYZ"[axis],
            "travel_mm": travel, "collision_free": not obstacles,
            "first_collision_mm": obstacles[0][0] if obstacles else None,
            "first_obstacle": obstacles[0][1] if obstacles else None}


def audit(model):
    assert model["status"] == "assumed" and model["donor_transform"] is None
    assert model["upstream_audit"]["contact_or_scan_coordinates_used"] is False
    boxes, panels = model["plate_boxes"], model["panels"]
    assert len(boxes) == len(panels) and len({p["name"] for p in panels}) == len(panels)
    t, d = model["thickness_mm"], model["dimensions_mm"]
    graph = {i: set() for i in range(len(boxes))}
    for i, (box, panel) in enumerate(zip(boxes, panels)):
        n, u, v = panel["normal_axis"], panel["u_axis"], panel["v_axis"]
        assert sorted((n, u, v)) == [0, 1, 2]
        assert box["max_mm"][n] - box["min_mm"][n] == t
        for k, key in ((u, "u_mm"), (v, "v_mm")):
            assert [box["min_mm"][k], box["max_mm"][k]] == panel[key]
        assert (box["min_mm"][n] + box["max_mm"][n]) / 2 == panel["at_mm"]
        for j in range(i):
            if overlap(box, boxes[j]):
                graph[i].add(j); graph[j].add(i)
    seen, todo = set(), [0]
    while todo:
        node = todo.pop()
        if node not in seen:
            seen.add(node); todo.extend(graph[node] - seen)
    assert len(seen) == len(boxes), "Disconnected CAD plates"
    area = sum((p["u_mm"][1] - p["u_mm"][0]) * (p["v_mm"][1] - p["v_mm"][0]) for p in panels)
    assert area == model["shell_area_mm2"]
    volume = union_volume(boxes)
    half, inner = d["width"] / 2, d["width"] / 2 - d["sill_width"]
    clearance = 0.5  # Assumed tooling clearance, not measured shrinkage allowance.
    inset = t / 2 + clearance
    cores = []
    for lo, hi, name in ((-half, -inner, "right_sill"), (inner, half, "left_sill")):
        cores.append(dict(name=name, min_mm=[inset, lo + inset, inset],
                          max_mm=[d["length"] - inset, hi - inset, d["sill_height"] - inset]))
    if not d.get("omit_tunnel", False):
        cores.append(dict(name="tunnel", min_mm=[-10, -d["tunnel_width"] / 2 + inset, inset],
                          max_mm=[d["length"] + 10, d["tunnel_width"] / 2 - inset, d["tunnel_height"] - inset]))
    tooling = []
    travel = d["length"] + d["width"] + max(d["front_bulkhead_height"], d["rear_bulkhead_height"]) + 100
    for core in cores:
        assert not any(overlap(core, b) for b in boxes), "Core initially penetrates laminate"
        directions = [pull(core, boxes, k, sign, travel) for k in range(3) for sign in (-1, 1)]
        tooling.append({"core": core["name"], "box_mm": core, "directions": directions,
                        "any_axis_aligned_rigid_pull": any(x["collision_free"] for x in directions)})
    return {"classification": "independent_hypothesis_geometry_and_kinematic_tooling_audit",
            "variant": model["variant"], "panels_checked": len(panels),
            "all_plate_thicknesses_equal_physical_parameter": True,
            "connected_plate_union": True, "exact_box_union_volume_mm3": volume,
            "shell_area_times_thickness_mm3": area * t,
            "relative_CAD_union_vs_shell_volume_difference": volume / (area * t) - 1,
            "mass_difference_is_junction_volume_convention_not_weight_measurement": True,
            "tooling_clearance_assumed_mm": clearance, "straight_pull_trials": tooling,
            "kinematic_scope": "Rigid rectangular cores, fixed undeformed plates, six axis directions; excludes rotation, collapse, dissolution, draft, friction, thermal contraction and cure.",
            "tooling_verdict": "No single-piece rigid-core manufacturing route admitted where an assumed closed-section core remains trapped.",
            "functional_or_manufacturing_validation": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("Output already exists; preserve the earlier trial.")
    raw = args.model.read_bytes()
    result = audit(json.loads(raw))
    result["model_sha256"] = hashlib.sha256(raw).hexdigest()
    result["auditor_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"volume_mm3": result["exact_box_union_volume_mm3"],
                      "tooling": [{"core": x["core"], "axis_pull": x["any_axis_aligned_rigid_pull"]}
                                  for x in result["straight_pull_trials"]]}))


if __name__ == "__main__":
    main()
