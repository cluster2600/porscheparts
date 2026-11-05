"""Independently inspect a private periodic candidate with native OCCT geometry."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from OCP.Extrema import Extrema_ExtAlgo_Tree
from OCP.Geom import Geom_BSplineSurface
from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
from OCP.TColgp import TColgp_Array2OfPnt
from OCP.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger
from OCP.gp import gp_Pnt, gp_Vec


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def native_surface(poles, u_knots, v_knots):
    extended = np.concatenate((poles, poles[:3]), axis=0)
    control = TColgp_Array2OfPnt(1, len(extended), 1, poles.shape[1])
    for i, row in enumerate(extended, 1):
        for j, point in enumerate(row, 1):
            control.SetValue(i, j, gp_Pnt(*point))

    def native_knots(values):
        unique, multiplicity = np.unique(values, return_counts=True)
        positions = TColStd_Array1OfReal(1, len(unique))
        counts = TColStd_Array1OfInteger(1, len(unique))
        for index, (value, count) in enumerate(zip(unique, multiplicity), 1):
            positions.SetValue(index, float(value))
            counts.SetValue(index, int(count))
        return positions, counts

    uk, um = native_knots(u_knots)
    vk, vm = native_knots(v_knots)
    return Geom_BSplineSurface(control, uk, vk, um, vm, 3, 3, False, False)


def point(surface, u, v):
    result = surface.Value(float(u), float(v))
    return np.array([result.X(), result.Y(), result.Z()])


def projection_distance(surface, position):
    projector = GeomAPI_ProjectPointOnSurf(gp_Pnt(*position), surface,
                                           0.0, 1.0, 0.0, 1.0, 1e-9,
                                           Extrema_ExtAlgo_Tree)
    if not projector.IsDone() or projector.NbPoints() == 0:
        raise ValueError("Native point-to-surface projection failed")
    return float(projector.LowerDistance())


def statistics(values, limit):
    return {"points": len(values), "p95_mm": float(np.quantile(values, 0.95)),
            "maximum_mm": float(values.max()), "over_limit": int((values > limit).sum())}


def native_controls(u_knots, v_knots):
    # Uniform periodic cubic approximation to an independently specified R=5 circle.
    step = 2 * np.pi / 16
    angles = (np.arange(16) - 1) * step
    greville = np.array([np.mean(v_knots[j + 1:j + 4]) for j in range(6)])
    poles = np.zeros((16, 6, 3))
    radial_scale = 5 / (2 / 3 + np.cos(step) / 3)
    poles[:, :, 0] = radial_scale * np.cos(angles)[:, None]
    poles[:, :, 1] = radial_scale * np.sin(angles)[:, None]
    poles[:, :, 2] = 3 * greville[None, :]
    surface = native_surface(poles, u_knots, v_knots)
    radial_errors = []
    for u in np.linspace(0, 1, 97):
        p = point(surface, u, 0.43)
        radial_errors.append(abs(np.linalg.norm(p[:2]) - 5))
        if abs(p[2] - 1.29) > 1e-10:
            raise ValueError("Native tensor-product axial control failed")
    d = projection_distance(surface, [5.6 * np.cos(0.75), 5.6 * np.sin(0.75), 1.29])
    if max(radial_errors) > 0.002 or abs(d - 0.6) > 0.002 or d < 0.01:
        raise ValueError("Native known-radius or rejection control failed")
    return {"known_radius_maximum_error_mm": max(radial_errors),
            "known_0p6mm_distance_detected_mm": d, "checks_passed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("trial", "arrays", "paper", "preparation", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Existing verification directory refused")
    plan = json.loads((args.trial / "plan.json").read_text())
    files = {"arrays": args.arrays, "contract": args.paper / "registered-contract.json",
             "partitions": args.paper / "registered-partitions.json",
             "preparation_models": args.preparation / "cad-domains.json",
             "preparation_admission": args.preparation / "admissibility.json"}
    for key, path in files.items():
        if digest(path) != plan["input_sha256"][key]:
            raise SystemExit("Registered input mismatch: " + key)
    partitions = json.loads(files["partitions"].read_text())["partitions"]
    item = next(p for p in partitions if p["id"] == plan["region"])
    partition = args.paper / item["file"]
    if digest(partition) != item["sha256"] or digest(partition) != plan["input_sha256"]["partition"]:
        raise SystemExit("Registered partition mismatch")
    with np.load(partition, allow_pickle=False) as data:
        training, evaluation = data["training_source_vertex_ids"], data["evaluation_source_vertex_ids"]
        selected = data["selected_source_face_ids"]
    with np.load(args.arrays, allow_pickle=False) as data:
        vertices, faces = data["vertices"], data["triangles"]
    with np.load(args.trial / "candidate-private.npz", allow_pickle=False) as data:
        candidate = {key: data[key].copy() for key in data.files}
    ids = np.unique(faces[selected])
    for name, values in (("source_vertex_ids", ids), ("selected_source_faces", selected),
                         ("training_source_ids", training), ("evaluation_source_ids", evaluation)):
        if not np.array_equal(candidate[name], values):
            raise SystemExit("Source membership mismatch: " + name)
    if np.intersect1d(training, evaluation).size or not np.array_equal(np.union1d(training, evaluation), ids):
        raise SystemExit("Disjoint split or full source support mismatch")
    model = next(m for m in json.loads(files["preparation_models"].read_text()) if m["id"] == plan["region"])
    for name, expected in (("parameters_origin", model["origin"]), ("parameters_axis", model["axis"]),
                           ("parameters_x", model["x_direction"])):
        if not np.array_equal(candidate[name], expected):
            raise SystemExit("Frozen frame changed")
    delta = vertices[ids] - np.asarray(model["origin"])
    x, axis = np.asarray(model["x_direction"]), np.asarray(model["axis"])
    y = np.cross(axis, x)
    height = delta @ axis
    uv = np.column_stack((np.mod(np.arctan2(delta @ y, delta @ x), 2 * np.pi) / (2 * np.pi),
                          (height - height.min()) / np.ptp(height)))
    if not np.array_equal(candidate["uv"], uv):
        raise SystemExit("Source parameter coordinates changed")
    if candidate["independent_poles"].shape != (16, 6, 3):
        raise SystemExit("Registered pole count changed")
    expected_u = np.arange(-3, 20, dtype=float) / 16
    expected_v = np.array([0, 0, 0, 0, 1 / 3, 2 / 3, 1, 1, 1, 1])
    if not np.array_equal(candidate["u_knots"], expected_u) or not np.array_equal(candidate["v_knots"], expected_v):
        raise SystemExit("Registered knots changed")
    args.output.mkdir(parents=True)
    controls = native_controls(expected_u, expected_v)
    surface = native_surface(candidate["independent_poles"], expected_u, expected_v)
    prediction = np.array([point(surface, *parameter) for parameter in uv])
    correspondence = np.linalg.norm(prediction - vertices[ids], axis=1)
    distances = np.array([projection_distance(surface, p) for p in vertices[ids]])
    seam_position, seam_derivative = 0.0, 0.0
    for v in np.linspace(0, 1, 23):
        result = []
        for u in (0.0, 1.0):
            p, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
            surface.D1(u, float(v), p, du, dv)
            result.append((np.array([p.X(), p.Y(), p.Z()]), np.array([du.X(), du.Y(), du.Z()])))
        seam_position = max(seam_position, float(np.linalg.norm(result[0][0] - result[1][0])))
        seam_derivative = max(seam_derivative, float(np.linalg.norm(result[0][1] - result[1][1])))
    heldout = np.isin(ids, evaluation)
    limit = float(plan["point_correspondence_limit_mm"])
    fit = json.loads((args.trial / "fit-report.json").read_text())
    native_all = statistics(correspondence, limit)
    if abs(native_all["maximum_mm"] - fit["all_source"]["maximum_mm"]) > 1e-9:
        raise ValueError("Native geometry disagrees with the reported candidate")
    checks = {"source_membership_exact": True, "frame_unchanged": True,
              "training_evaluation_disjoint": True,
              "native_correspondence_matches_report": True,
              "periodic_position_under_1e_minus_10mm": seam_position < 1e-10,
              "periodic_derivative_under_1e_minus_9mm": seam_derivative < 1e-9}
    if not all(checks.values()):
        raise ValueError("Independent native verification failed")
    np.savez_compressed(args.output / "native-errors-private.npz", source_vertex_ids=ids,
                        correspondence_error_mm=correspondence,
                        native_projection_error_mm=distances,
                        heldout=heldout)
    report = {"region": plan["region"], "checks": checks, "native_controls": controls,
              "native_correspondence_all": native_all,
              "native_correspondence_heldout": statistics(correspondence[heldout], limit),
              "native_untrimmed_projection_all": statistics(distances, limit),
              "native_untrimmed_projection_heldout": statistics(distances[heldout], limit),
              "seam_position_maximum_mm": seam_position,
              "seam_derivative_maximum_mm": seam_derivative,
              "correspondence_gate_passed": native_all["over_limit"] == 0,
              "projection_domain": "Untrimmed parameter rectangle, diagnostic only; not an observed-surface CAD export or formal global-distance bound.",
              "candidate_sha256": digest(args.trial / "candidate-private.npz"),
              "verifier_source_sha256": digest(__file__), "fit_report_sha256": digest(args.trial / "fit-report.json"),
              "trimmed_cad_exported": False, "physical_acceptance": False,
              "manufacturing_authorized": False}
    with (args.output / "verification.json").open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
