#!/usr/bin/env python3
"""Synthetic witness: bores, valve seats, drafted bosses and fillets.

The plane witness beside this file left cylinders, cones and fillets uncovered.
This one builds a scene of the features a cylinder head carries, each with a
known axis, radius and half-angle, meshes it at scan pitch with scan-like
noise, and asks ``primitive_fit.detect`` to recover them:

* cylinders: full bores and bosses, two parallel guides, partial arcs;
* cones: 45 and 30 degree valve seats, each 45 degree seat coaxial with a
  guide, and bores and bosses drafted by 0.5, 1 and 2 degrees;
* fillets: 3 and 6 mm radii, a quarter turn between two planes;
* planes: the four fillet flanks and a deck.

The ground truth is generated here and never comes from a detector. A
cylinder-only run of the same detector is the negative control: it shows what
is lost when draft is assumed away. The detector was developed on seeds 1 to 3;
the acceptance below and the primary seed were fixed before its first run on
the primary seed. Further seeds are reported as run, never selected.

This qualifies the software chain on synthetic, isolated features. It says
nothing about any real scan, part or fit.
"""
import argparse
import hashlib
import json
import math
import runpy
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SEED = 20261110
DEVELOPMENT_SEEDS = tuple(range(1, 13))
PITCH_MM = 1.0                    # vertex spacing, close to a 1 mm scan pitch
NOISE_MM = 0.03                   # normal noise, the same order as the plane witness
CELL_MM = 140.0                   # features sit in separate cells of a grid

# Acceptance fixed before the first run on the primary seed.
MATCH = {"axis_deg": 3.0, "position_mm": 2.0, "radius_mm": 2.0, "plane_deg": 1.0, "plane_offset_mm": 0.5}
ACCEPT = {
    # bores, bosses and drafted features: what a mating or machined feature needs
    "axial": {"axis_deg": 0.2, "position_mm": 0.05, "radius_mm": 0.05, "half_angle_deg": 0.25},
    # a 3 mm seat band fixes its radius and angle, but only weakly its axis:
    # tilting the axis and shifting it sideways change the band alike
    "narrow-seat": {"axis_deg": 0.5, "position_mm": 0.15, "radius_mm": 0.05, "half_angle_deg": 0.25},
    # fillets: a quarter turn of a small radius is less determined; nominal radii step by 0.5 mm or more
    "fillet": {"axis_deg": 0.5, "position_mm": 0.3, "radius_mm": 0.2, "half_angle_deg": 0.25},
    "plane": {"tilt_deg": 0.1, "offset_mm": 0.05},
}
MAX_SIGMAS = 5.0                  # an error may not exceed this many of the detector's own reported sigmas
# Not resolvable at this pitch: between its flanks' shared zones a 3 mm fillet
# keeps two columns of vertices. The detector must say so, not report a radius.
LIMIT_PROBES = ("fillet-3",)

# name, class, mid radius, axial length, arc, half-angle, tilt from +Z, side
AXIAL = (
    ("bore-50", "axial", 50.0, 40.0, 360.0, 0.0, 0.0, "concave"),
    ("port-15-arc120", "axial", 15.0, 40.0, 120.0, 0.0, 60.0, "concave"),
    ("boss-9", "axial", 9.0, 25.0, 360.0, 0.0, 0.0, "convex"),
    ("saddle-25-arc180", "axial", 25.0, 30.0, 180.0, 0.0, 90.0, "concave"),
    ("seat-30deg", "axial", 16.0, 4.0 / math.tan(math.radians(30.0)), 360.0, 30.0, 10.0, "concave"),
    ("drafted-boss-1deg", "axial", 12.0, 30.0, 360.0, 1.0, 0.0, "convex"),
    ("drafted-boss-2deg", "axial", 20.0, 30.0, 360.0, 2.0, 5.0, "convex"),
    ("drafted-bore-0.5deg", "axial", 30.0, 40.0, 360.0, 0.5, 0.0, "concave"),
)
GUIDE = {"radius": 4.0, "length": 30.0, "tilt": 15.0, "spacing": 46.0}
SEAT = {"radius": 18.5, "length": 3.0, "half_angle": 45.0, "station": 26.5}   # coaxial with its guide
FILLETS = (3.0, 6.0)
FLANK_MM, FILLET_LENGTH_MM, DECK_MM = 40.0, 60.0, 150.0


def unit(v):
    return v / np.linalg.norm(v)


def frame(a):
    e1 = unit(np.cross(a, np.eye(3)[np.argmin(np.abs(a))]))
    return e1, np.cross(a, e1)


def tilted_axis(tilt_deg, rng):
    t, az = math.radians(tilt_deg), rng.uniform(0, 2 * math.pi)
    return np.array([math.sin(t) * math.cos(az), math.sin(t) * math.sin(az), math.cos(t)])


def grid_triangles(rows, cols, closed):
    idx = np.arange(rows * cols).reshape(rows, cols)
    nxt = np.roll(idx, -1, axis=1) if closed else idx[:, 1:]
    cur = idx if closed else idx[:, :-1]
    a, b, c, d = cur[:-1].ravel(), cur[1:].ravel(), nxt[1:].ravel(), nxt[:-1].ravel()
    return np.vstack([np.column_stack([a, b, c]), np.column_stack([a, c, d])])


def axial_patch(truth, rng):
    """Vertices, triangles and true normals of one cylinder or cone patch."""
    c, a, k = truth["centre"], truth["axis"], math.tan(math.radians(truth["half_angle_deg"]))
    e1, e2 = frame(a)
    half = truth["length_mm"] / 2
    rows = max(2, round(truth["length_mm"] * math.sqrt(1 + k * k) / PITCH_MM)) + 1
    closed = truth["arc_deg"] >= 360.0
    arc = math.radians(truth["arc_deg"])
    cols = max(3, round(arc * truth["radius_mm"] / PITCH_MM)) + (0 if closed else 1)
    start = rng.uniform(0, 2 * math.pi)
    theta = start + np.linspace(0, arc, cols, endpoint=not closed)
    t = np.linspace(-half, half, rows)
    tt, th = np.meshgrid(t, theta, indexing="ij")
    radial = np.cos(th)[..., None] * e1 + np.sin(th)[..., None] * e2
    normal = (radial - k * a) / math.sqrt(1 + k * k)
    vertices = c + tt[..., None] * a + (truth["radius_mm"] + k * tt)[..., None] * radial
    vertices = vertices + rng.normal(0, NOISE_MM, tt.shape)[..., None] * normal
    sign = 1.0 if truth["side"] == "convex" else -1.0
    return vertices.reshape(-1, 3), grid_triangles(rows, cols, closed), (sign * normal).reshape(-1, 3)


def plane_patch(truth, rng):
    u, v, n = truth["u"], truth["v"], truth["normal"]
    su = np.linspace(0, truth["size_mm"][0], round(truth["size_mm"][0] / PITCH_MM) + 1)
    sv = np.linspace(0, truth["size_mm"][1], round(truth["size_mm"][1] / PITCH_MM) + 1)
    gu, gv = np.meshgrid(su, sv, indexing="ij")
    vertices = truth["corner"] + gu[..., None] * u + gv[..., None] * v
    vertices = vertices + rng.normal(0, NOISE_MM, gu.shape)[..., None] * n
    return vertices.reshape(-1, 3), grid_triangles(len(su), len(sv), False), np.broadcast_to(n, vertices.shape).reshape(-1, 3)


def truth_scene(rng):
    """Every feature with its exact parameters. No detector is involved."""
    cells = [np.array([i * CELL_MM, j * CELL_MM, 0.0]) for j in range(3) for i in range(4)]
    cells = [cells[i] for i in rng.permutation(len(cells))]

    def place():
        return cells.pop() + rng.uniform(-5, 5, 3)

    truths = []
    for name, cls, radius, length, arc, half_angle, tilt, side in AXIAL:
        truths.append({"name": name, "class": cls, "type": "cone" if half_angle else "cylinder", "centre": place(),
                       "axis": tilted_axis(tilt, rng), "radius_mm": radius, "length_mm": length, "arc_deg": arc,
                       "half_angle_deg": half_angle, "side": side})
    # Two parallel guides, each with a coaxial 45 degree seat.
    origin, axis = place(), tilted_axis(GUIDE["tilt"], rng)
    across = frame(axis)[0]
    for tag, offset in (("a", -GUIDE["spacing"] / 2), ("b", GUIDE["spacing"] / 2)):
        centre = origin + offset * across
        truths.append({"name": f"guide-{tag}", "class": "axial", "type": "cylinder", "centre": centre, "axis": axis,
                       "radius_mm": GUIDE["radius"], "length_mm": GUIDE["length"], "arc_deg": 360.0,
                       "half_angle_deg": 0.0, "side": "concave"})
        truths.append({"name": f"seat-45deg-{tag}", "class": "narrow-seat", "type": "cone",
                       "centre": centre + SEAT["station"] * axis, "axis": axis, "radius_mm": SEAT["radius"],
                       "length_mm": SEAT["length"], "arc_deg": 360.0, "half_angle_deg": SEAT["half_angle"],
                       "side": "concave"})
    # A fillet joins two perpendicular flanks; its axis runs along the corner.
    for radius in FILLETS:
        origin, x = place(), tilted_axis(rng.uniform(0, 90), rng)
        y, z = frame(x)
        centre = origin + radius * y + radius * z
        truths.append({"name": f"fillet-{radius:g}", "class": "fillet", "type": "cylinder",
                       "centre": centre + (FILLET_LENGTH_MM / 2) * x, "axis": x, "radius_mm": radius,
                       "length_mm": FILLET_LENGTH_MM, "arc_deg": 90.0, "half_angle_deg": 0.0, "side": "concave",
                       "arc_start": (y, z, math.pi)})
        for tag, corner, v, n in (("a", origin + radius * y, y, z), ("b", origin + radius * z, z, y)):
            truths.append({"name": f"fillet-{radius:g}-flank-{tag}", "class": "plane", "type": "plane",
                           "corner": corner, "u": x, "v": v, "normal": n, "size_mm": (FILLET_LENGTH_MM, FLANK_MM)})
    normal = tilted_axis(rng.uniform(0, 5), rng)
    u, v = frame(normal)
    truths.append({"name": "deck", "class": "plane", "type": "plane", "corner": place() - DECK_MM / 2 * (u + v),
                   "u": u, "v": v, "normal": normal, "size_mm": (DECK_MM, DECK_MM)})
    return truths


def fillet_patch(truth, rng):
    """A quarter cylinder from flank a to flank b, with the same sampling as ``axial_patch``."""
    y, z, start = truth["arc_start"]
    a, r = truth["axis"], truth["radius_mm"]
    rows = round(truth["length_mm"] / PITCH_MM) + 1
    cols = max(3, round(math.pi / 2 * r / PITCH_MM)) + 1
    theta = start + np.linspace(0, math.pi / 2, cols)
    t = np.linspace(-truth["length_mm"] / 2, truth["length_mm"] / 2, rows)
    tt, th = np.meshgrid(t, theta, indexing="ij")
    radial = np.cos(th)[..., None] * y + np.sin(th)[..., None] * z
    vertices = truth["centre"] + tt[..., None] * a + r * radial
    vertices = vertices + rng.normal(0, NOISE_MM, tt.shape)[..., None] * radial
    return vertices.reshape(-1, 3), grid_triangles(rows, cols, False), (-radial).reshape(-1, 3)


def build(seed):
    """The scene as a scan would deliver it: vertices and mesh vertex normals."""
    import open3d as o3d

    rng = np.random.default_rng(seed)
    truths = truth_scene(rng)
    points, normals, labels = [], [], []
    for i, truth in enumerate(truths):
        make = plane_patch if truth["type"] == "plane" else fillet_patch if truth["class"] == "fillet" else axial_patch
        vertices, triangles, outward = make(truth, rng)
        mesh = o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(vertices), o3d.utility.Vector3iVector(triangles))
        mesh.compute_vertex_normals()
        n = np.asarray(mesh.vertex_normals)
        # A scan mesh is consistently oriented out of the material; only the sign comes from the truth.
        n = n * np.sign(np.einsum("ij,ij->i", n, outward))[:, None]
        points.append(vertices), normals.append(n), labels.append(np.full(len(vertices), i))
    return truths, np.vstack(points), np.vstack(normals), np.concatenate(labels)


def errors(truth, found):
    """Errors of one detection against one truth, or None when the kinds cannot be compared."""
    if (truth["type"] == "plane") != (found["type"] == "plane"):
        return None
    if truth["type"] == "plane":
        n = np.array(found["normal"])
        centre = truth["corner"] + truth["size_mm"][0] / 2 * truth["u"] + truth["size_mm"][1] / 2 * truth["v"]
        return {"tilt_deg": math.degrees(math.acos(min(abs(n @ truth["normal"]), 1.0))),
                "offset_mm": abs((centre - np.array(found["point"])) @ n)}
    a, p = np.array(found["axis_direction"]), np.array(found["axis_point"])
    v = truth["centre"] - p
    station = v @ a
    k = math.tan(math.radians(found.get("half_angle_deg", 0.0)))
    radius = found["radius_mm"] if found["type"] == "cylinder" else found["radius_at_axis_point_mm"] + k * station
    out = {"axis_deg": math.degrees(math.acos(min(abs(a @ truth["axis"]), 1.0))),
           "position_mm": float(np.linalg.norm(v - station * a)),
           "radius_mm": float(abs(radius - truth["radius_mm"])),
           "half_angle_deg": abs(found.get("half_angle_deg", 0.0) - truth["half_angle_deg"])}
    if truth["type"] == "cone" and found["type"] == "cone":
        k_true = math.tan(math.radians(truth["half_angle_deg"]))
        apex = truth["centre"] - truth["radius_mm"] / k_true * truth["axis"]
        out["apex_mm"] = float(np.linalg.norm(apex - np.array(found["apex"])))
    return out


def score(truths, found):
    rows, claimed = [], set()
    for truth in truths:
        best = None
        for j, detection in enumerate(found):
            e = errors(truth, detection)
            if e is None or j in claimed:
                continue
            if truth["type"] == "plane":
                inside, rank = e["tilt_deg"] <= MATCH["plane_deg"] and e["offset_mm"] <= MATCH["plane_offset_mm"], e["offset_mm"]
            else:
                inside = (e["axis_deg"] <= MATCH["axis_deg"] and e["position_mm"] <= MATCH["position_mm"]
                          and e["radius_mm"] <= MATCH["radius_mm"])
                rank = e["position_mm"] + e["radius_mm"]
            if inside and (best is None or rank < best[2]):
                best = (j, e, rank)
        row = {"name": truth["name"], "class": truth["class"], "type": truth["type"],
               "limit_probe": truth["name"] in LIMIT_PROBES, "found": best is not None, "found_type": None,
               "determined": False, "within_limits": False, "max_sigmas": None, "within_acceptance": False,
               "errors": None}
        if best:
            claimed.add(best[0])
            detection, e = found[best[0]], best[1]
            limits = ACCEPT[truth["class"]]
            row.update(found_type=detection["type"], determined=detection["determined"],
                       errors={k: round(v, 5) for k, v in e.items()}, points=detection["points"],
                       fit_points=detection["fit_points"], rms_mm=round(detection["rms_mm"], 5),
                       within_limits=detection["type"] == truth["type"] and all(e[k] <= limits[k] for k in limits))
            if truth["type"] != "plane" and detection["determined"]:
                row["reported_sigma"] = {"axis_deg": round(detection["axis_direction_sigma_deg"], 5),
                                         "position_mm": round(detection["axis_point_sigma_mm"], 5),
                                         "radius_mm": round(detection["radius_sigma_mm"], 5)}
                row["max_sigmas"] = round(max(e[k] / row["reported_sigma"][k] for k in row["reported_sigma"]), 2)
            row["within_acceptance"] = (row["determined"] and row["within_limits"]
                                        and (row["max_sigmas"] is None or row["max_sigmas"] <= MAX_SIGMAS))
        rows.append(row)
    by_kind = {}
    for row in rows:
        key = "plane" if row["type"] == "plane" else "fillet" if row["class"] == "fillet" else row["type"]
        by_kind.setdefault(key, [0, 0])
        by_kind[key][0] += row["within_acceptance"]
        by_kind[key][1] += 1
    required = [r for r in rows if not r["limit_probe"]]
    # The worst failure is a confident wrong answer: determined, yet outside the limits.
    wrong = [r["name"] for r in rows if r["determined"] and not r["within_acceptance"]]
    spurious = len(found) - len(claimed)
    return {"features": len(rows), "required": len(required), "found": sum(r["found"] for r in rows),
            "within_acceptance": sum(r["within_acceptance"] for r in rows),
            "required_within_acceptance": sum(r["within_acceptance"] for r in required),
            "within_acceptance_by_kind": {k: f"{a}/{b}" for k, (a, b) in sorted(by_kind.items())},
            "limit_probes": {r["name"]: "determined, within acceptance" if r["within_acceptance"]
                             else "determined, outside acceptance" if r["determined"]
                             else "found, reported as not determined" if r["found"] else "not found"
                             for r in rows if r["limit_probe"]},
            "determined_outside_acceptance": wrong, "unmatched_detections": spurious,
            "passed": all(r["within_acceptance"] for r in required) and not wrong and spurious == 0, "rows": rows}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=SEED, help="scene seed; the receipt is only valid for the default")
    ap.add_argument("--further-seeds", type=int, default=10, help="extra scenes reported as run")
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    import open3d as o3d
    import scipy

    fit = runpy.run_path(str(HERE / "primitive_fit.py"))
    st = fit["settings"](NOISE_MM, PITCH_MM)

    def run(seed, **overrides):
        truths, points, normals, _ = build(seed)
        found, remaining = fit["detect"](points, normals, {**st, **overrides}, seed)
        return truths, points, score(truths, found), len(remaining)

    truths, points, primary, unassigned = run(args.seed)
    _, _, control, _ = run(args.seed, allow_cones=False)
    further = []
    for seed in range(args.seed + 1, args.seed + 1 + args.further_seeds):
        result = run(seed)[2]
        further.append({"seed": seed, "required_within_acceptance": result["required_within_acceptance"],
                        "required": result["required"], "limit_probes": result["limit_probes"],
                        "unmatched_detections": result["unmatched_detections"], "passed": result["passed"],
                        "outside_acceptance": [r["name"] for r in result["rows"]
                                               if not r["within_acceptance"] and not r["limit_probe"]],
                        "determined_outside_acceptance": result["determined_outside_acceptance"]})
    report = {
        "schema": "scan-primitive-fitting-witness/2",
        "witness": "synthetic bores, valve seats, drafted bosses and fillets; ground truth generated independently of any detector",
        "script_sha256": sha(Path(__file__)),
        "detector_sha256": sha(HERE / "primitive_fit.py"),
        "lock_sha256": sha(HERE / "requirements.lock.txt"),
        "open3d": o3d.__version__, "numpy": np.__version__, "scipy": scipy.__version__,
        "geometry": {"seed": args.seed, "development_seeds": list(DEVELOPMENT_SEEDS), "pitch_mm": PITCH_MM,
                     "noise_mm": NOISE_MM, "features": len(truths), "points": int(len(points)),
                     "kinds": {k: sum(t["type"] == k for t in truths) for k in ("plane", "cylinder", "cone")},
                     "fillets": sum(t["class"] == "fillet" for t in truths)},
        "settings": st,
        "acceptance": {"match_window": MATCH, "limits": ACCEPT, "max_sigmas": MAX_SIGMAS, "limit_probes": list(LIMIT_PROBES),
                       "rule": "every feature except the limit probes is determined, of the right type, within its limits "
                               "and within max_sigmas of the reported uncertainty; nothing is reported as determined "
                               "outside its acceptance; no unmatched detection"},
        "detector": {**primary, "unassigned_points": unassigned},
        "cylinder_only_negative_control": control,
        "further_seeds": {"passed": sum(f["passed"] for f in further), "run": len(further), "scenes": further},
        "passed": {"primitive_fit": primary["passed"], "cylinder_only_negative_control": control["passed"]},
        "claims": "software witness on synthetic, isolated features only; no real part, scan or fit is qualified",
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for name, r in (("primitive_fit", primary), ("cylinder_only_negative_control", control)):
        print(name, r["required_within_acceptance"], "/", r["required"], r["within_acceptance_by_kind"], "probes",
              r["limit_probes"], "determined outside acceptance", r["determined_outside_acceptance"], "spurious",
              r["unmatched_detections"])
    print("further seeds passed", report["further_seeds"]["passed"], "/", len(further))
    print(json.dumps(report["passed"]))


if __name__ == "__main__":
    main()
