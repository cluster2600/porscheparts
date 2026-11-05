"""One registered periodic cubic surface fit; no parameter sweep or CAD release."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import BSpline


CONTRACT_SHA256 = "49fc806e1f9d6f129892d1cdd15505b4ed304a68ee84f37bcbf1fd1c8461f779"
PARTITIONS_SHA256 = "bca11c2633ed6fae331b9bd47d420f07f170b6f34d4ba232d68c87f37f1aa824"
REGION = "stud_passage_1_wall_candidate"
DEGREE = 3
U_POLES = 16
V_POLES = 6
LIMIT_MM = 0.01


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, data):
    with path.open("x") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def knots():
    u = np.arange(-DEGREE, U_POLES + DEGREE + 1, dtype=float) / U_POLES
    v = np.r_[np.zeros(DEGREE + 1), np.arange(1, 3) / 3, np.ones(DEGREE + 1)]
    return u, v


def design(uv):
    u, v = knots()
    extended = BSpline.design_matrix(uv[:, 0], u, DEGREE).toarray()
    angular = np.zeros((len(uv), U_POLES))
    for index in range(extended.shape[1]):
        angular[:, index % U_POLES] += extended[:, index]
    axial = BSpline.design_matrix(uv[:, 1], v, DEGREE).toarray()
    return np.einsum("ni,nj->nij", angular, axial).reshape(len(uv), -1)


def solve(uv, points):
    matrix = design(uv)
    poles, _, rank, values = np.linalg.lstsq(matrix, points, rcond=None)
    condition = float(values[0] / values[-1]) if values[-1] else None
    return poles.reshape(U_POLES, V_POLES, 3), int(rank), condition


def evaluate(uv, poles):
    return design(uv) @ poles.reshape(-1, 3)


def scores(error):
    return {"points": len(error), "p95_mm": float(np.quantile(error, 0.95)),
            "maximum_mm": float(error.max()), "over_limit": int((error > LIMIT_MM).sum())}


def controls():
    # Independent analytic geometry supplies the expected points, never fitted output.
    angle, height = np.meshgrid(np.arange(80) / 80, np.linspace(0, 1, 12), indexing="ij")
    train = np.column_stack((angle.ravel(), height.ravel()))
    evaluation = np.column_stack((np.arange(193) / 193 + 0.001,
                                  np.linspace(0.013, 0.987, 193)))

    def known(uv):
        theta = 2 * np.pi * uv[:, 0]
        radius = 5 + 0.08 * np.cos(3 * theta) + 0.03 * uv[:, 1]
        return np.column_stack((radius * np.cos(theta), radius * np.sin(theta),
                                3 * uv[:, 1]))

    poles, rank, condition = solve(train, known(train))
    maximum = float(np.linalg.norm(evaluate(evaluation, poles) - known(evaluation), axis=1).max())
    seam = np.column_stack((np.zeros(19), np.linspace(0, 1, 19)))
    opposite = seam.copy()
    opposite[:, 0] = 1
    seam_error = float(np.linalg.norm(evaluate(seam, poles) - evaluate(opposite, poles), axis=1).max())
    checks = {"analytic_heldout_under_0p01mm": maximum < LIMIT_MM,
              "periodic_position_under_1e_minus_12mm": seam_error < 1e-12,
              "full_rank": rank == U_POLES * V_POLES,
              "condition_under_1e8": condition is not None and condition < 1e8}
    if not all(checks.values()):
        raise ValueError("Analytic spline controls failed")
    return {"checks": checks, "analytic_heldout_maximum_mm": maximum,
            "seam_maximum_mm": seam_error, "rank": rank, "condition": condition}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("arrays", "paper", "preparation", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Existing trial refused")
    contract_path = args.paper / "registered-contract.json"
    partitions_path = args.paper / "registered-partitions.json"
    if digest(contract_path) != CONTRACT_SHA256 or digest(partitions_path) != PARTITIONS_SHA256:
        raise SystemExit("Frozen source contract mismatch")
    contract = json.loads(contract_path.read_text())
    partitions = json.loads(partitions_path.read_text())["partitions"]
    part = next(item for item in partitions if item["id"] == REGION)
    partition_path = args.paper / part["file"]
    if digest(partition_path) != part["sha256"] or digest(args.arrays) != contract["arrays_sha256"]:
        raise SystemExit("Frozen source arrays or partition mismatch")
    with np.load(args.arrays, allow_pickle=False) as arrays:
        vertices, faces = arrays["vertices"], arrays["triangles"]
    with np.load(partition_path, allow_pickle=False) as data:
        train_ids = data["training_source_vertex_ids"]
        evaluation_ids = data["evaluation_source_vertex_ids"]
        face_ids = data["selected_source_face_ids"]
    ids = np.unique(faces[face_ids])
    if np.intersect1d(train_ids, evaluation_ids).size or not np.array_equal(np.union1d(train_ids, evaluation_ids), ids):
        raise SystemExit("Registered point coverage or disjoint split mismatch")
    models = json.loads((args.preparation / "cad-domains.json").read_text())
    model = next(item for item in models if item["id"] == REGION)
    admission = next(item for item in json.loads((args.preparation / "admissibility.json").read_text())["regions"] if item["id"] == REGION)
    for check in ("native_source_valid", "no_uv_fold", "no_uv_degeneracy", "no_projected_overlap"):
        if admission["checks"][check] is not True:
            raise SystemExit("Source parameterization is not admissible: " + check)
    args.output.mkdir(parents=True)
    plan = {"region": REGION, "input_sha256": {"arrays": digest(args.arrays),
            "contract": CONTRACT_SHA256, "partitions": PARTITIONS_SHA256,
            "partition": digest(partition_path), "preparation_models": digest(args.preparation / "cad-domains.json"),
            "preparation_admission": digest(args.preparation / "admissibility.json")},
            "source_sha256": digest(__file__), "degree": DEGREE,
            "independent_poles": [U_POLES, V_POLES], "periodic_angular_basis": True,
            "candidate_count": 1, "full_rank_required": U_POLES * V_POLES,
            "maximum_condition": 1e8, "point_correspondence_limit_mm": LIMIT_MM,
            "geometry_policy": "No scan edit, refit of baseline frame, extrapolated trim, or automatic acceptance; no knot/degree sweep.",
            "selection_policy": "First existing wall mask with valid injective UV coverage and rejected cylindrical projection; conditional within-scan evaluation.",
            "physical_tolerance_mm": None, "manufacturing_authorized": False}
    save(args.output / "plan.json", plan)
    save(args.output / "analytic-controls.json", controls())
    points = vertices[ids]
    delta = points - np.asarray(model["origin"])
    axis = np.asarray(model["axis"])
    x = np.asarray(model["x_direction"])
    y = np.cross(axis, x)
    theta = np.mod(np.arctan2(delta @ y, delta @ x), 2 * np.pi)
    height = delta @ axis
    axial_minimum, axial_span = float(height.min()), float(np.ptp(height))
    if axial_span <= 0:
        raise SystemExit("Zero source axial span")
    uv = np.column_stack((theta / (2 * np.pi), (height - axial_minimum) / axial_span))
    training = np.isin(ids, train_ids)
    evaluation = np.isin(ids, evaluation_ids)
    poles, rank, condition = solve(uv[training], points[training])
    prediction = evaluate(uv, poles)
    error = np.linalg.norm(prediction - points, axis=1)
    u, v = knots()
    np.savez_compressed(args.output / "candidate-private.npz", independent_poles=poles,
                        u_knots=u, v_knots=v, uv=uv, source_vertex_ids=ids,
                        training_source_ids=train_ids, evaluation_source_ids=evaluation_ids,
                        selected_source_faces=face_ids, parameters_origin=model["origin"],
                        parameters_axis=axis, parameters_x=x, axial_minimum=axial_minimum,
                        axial_span=axial_span)
    checks = {"full_rank": rank == U_POLES * V_POLES,
              "bounded_condition": condition is not None and condition <= 1e8,
              "all_correspondence_points": bool(np.all(error <= LIMIT_MM)),
              "heldout_correspondence_points": bool(np.all(error[evaluation] <= LIMIT_MM))}
    report = {"region": REGION, "source_faces": len(face_ids), "rank": rank,
              "condition": condition, "training": scores(error[training]),
              "evaluation": scores(error[evaluation]), "all_source": scores(error),
              "checks": checks, "correspondence_screen_passed": all(checks.values()),
              "trimmed_cad_exported": False, "baseline_replaced": False,
              "physical_acceptance": False, "manufacturing_authorized": False}
    save(args.output / "fit-report.json", report)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
