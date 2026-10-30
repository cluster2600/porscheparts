#!/usr/bin/env python3
"""Read-only source-ID/export and held-out geometry checks; never fit a model."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_partition(selected, training, evaluation):
    selected, training, evaluation = (np.asarray(p) for p in (selected, training, evaluation))
    for values in [selected, training, evaluation]:
        if (values.ndim != 1 or values.dtype.kind not in "iu" or (values < 0).any()
                or len(np.unique(values)) != len(values)):
            raise ValueError("invalid source-ID partition")
    if (set(training) & set(evaluation) or (training % 5 == 0).any() or (evaluation % 5 != 0).any()
            or not np.array_equal(np.sort(np.r_[training, evaluation]), np.sort(selected))):
        raise ValueError("source-ID partition lost, duplicated or leaked evaluation points")


def verify_evaluation(model, points, record, limits, axis_seed):
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not len(points) or not np.isfinite(points).all():
        raise ValueError("invalid evaluation points")
    if record.get("physical_dimension_accepted") is not False:
        raise ValueError("scan fit cannot accept a physical dimension")
    if model["kind"] == "plane":
        normal = np.asarray(model["normal"], dtype=float)
        if normal.shape != (3,) or not np.isfinite(normal).all() or abs(np.linalg.norm(normal) - 1) > 1e-7:
            raise ValueError("invalid plane normal")
        error = abs(points @ normal - float(model["offset_mm"]))
        expected_retention = bool(np.quantile(error, .95) <= .25)
    elif model["kind"] == "cylinder":
        axis, origin = np.asarray(model["axis_direction"]), np.asarray(model["axis_origin_mm"])
        radius = float(model["radius_mm"])
        if (axis.shape != (3,) or origin.shape != (3,) or not np.isfinite(np.r_[axis, origin, radius]).all()
                or radius <= 0 or abs(np.linalg.norm(axis) - 1) > 1e-7):
            raise ValueError("invalid cylinder")
        delta = points - origin
        axial = delta @ axis
        # Different expression from both optimizer projection and inspector cross products.
        error = abs(np.sqrt(np.maximum(np.einsum("ij,ij->i", delta, delta) - axial ** 2, 0)) - radius)
        helper = np.array([1., 0., 0.]) if abs(axis[0]) < .8 else np.array([0., 1., 0.])
        first = np.cross(axis, helper)
        first /= np.linalg.norm(first)
        second = np.cross(axis, first)
        angle = np.mod(np.arctan2(delta @ second, delta @ first), 2 * np.pi)

        def coverage(mask):
            angles = np.sort(angle[mask])
            if len(angles) < 2:
                return 0.
            gaps = np.diff(np.append(angles, angles[0] + 2 * np.pi))
            return float(360 - np.rad2deg(gaps.max()))

        supported = error <= limits["p95_limit_mm"]
        bins = np.minimum(np.searchsorted(np.linspace(axial.min(), axial.max(), 4)[1:], axial, side="right"), 2)
        per_bin = [coverage(supported & (bins == i)) if (supported & (bins == i)).sum() >= 20 else 0. for i in range(3)]
        seed = np.asarray(axis_seed, dtype=float)
        seed /= np.linalg.norm(seed)
        angle_to_seed = float(np.rad2deg(np.arccos(np.clip(abs(seed @ axis), 0, 1))))
        expected_retention = bool(np.quantile(error, .95) <= limits["p95_limit_mm"]
                                  and np.ptp(axial) >= limits["minimum_span_mm"]
                                  and min(per_bin) >= limits["minimum_coverage_degrees"]
                                  and coverage(supported) >= limits["minimum_coverage_degrees"]
                                  and angle_to_seed <= limits["maximum_tilt_degrees"])
        if not np.allclose(per_bin, record["coverage_by_axial_third_degrees"], atol=1e-7, rtol=0):
            raise ValueError("reported angular support differs from source observations")
    else:
        raise ValueError("unsupported model type")
    if (not np.isfinite(error).all()
            or not np.isclose(float(np.quantile(error, .95)), record["p95_mm"], atol=1e-8, rtol=0)
            or not np.isclose(float(error.max()), record["max_mm"], atol=1e-8, rtol=0)):
        raise ValueError("reported evaluation distances differ from source observations")
    if bool(record["retained_as_scan_fit_candidate"]) != expected_retention:
        raise ValueError("reported retention violates registered geometric checks")
    return {"id": record["id"], "evaluation_points": len(points), "p95_mm": float(np.quantile(error, .95)),
            "retained_as_scan_fit_candidate": expected_retention, "passed": True}


SUPPORT_REJECTION = "insufficient source support"


def support_thresholds(contract):
    """Read the driver's registered support minima from the hash-pinned contract."""
    try:
        values = {key: int(contract[key]) for key in
                  ("minimum_training_points", "minimum_evaluation_points", "minimum_selected_points")}
    except (KeyError, TypeError, ValueError):
        raise ValueError("registered contract declares no support minima")
    if min(values.values()) <= 0:
        raise ValueError("registered support minima are not positive")
    return values


def admits_support(train, held, thresholds):
    """Mirror the driver's pre-fit support rule, including its minimum total selection."""
    return (len(train) >= thresholds["minimum_training_points"]
            and len(held) >= thresholds["minimum_evaluation_points"]
            and len(train) + len(held) >= thresholds["minimum_selected_points"])


def verify_rejection(record, train, held, thresholds):
    """Verify a record that carries no model: a documented refusal, not a silent gap.

    Point counts alone do not prove that fitting succeeded. A degenerate or
    non-convergent fit on well-supported points is a legitimate recorded
    outcome, so what gets checked is the stated reason against the frozen
    counts: a support failure may be claimed only when support really is short,
    and admitted support demands some other reason.
    """
    if record["retained_as_scan_fit_candidate"]:
        raise ValueError("region retained as a scan-fit candidate without a model")
    reasons = record.get("rejection_reasons")
    if (not isinstance(reasons, list) or not reasons
            or not all(isinstance(reason, str) and reason.strip() for reason in reasons)):
        raise ValueError("model missing without a recorded rejection reason")
    admitted = admits_support(train, held, thresholds)
    if (SUPPORT_REJECTION in reasons) != (not admitted):
        raise ValueError("recorded rejection reason contradicts the registered point counts")
    return {"id": record["id"], "training_points": len(train), "evaluation_points": len(held),
            "admitted_support": admitted, "rejection_reasons": list(reasons),
            "retained_as_scan_fit_candidate": False, "passed": True}


def validate(study, arrays, baseline, contract_sha256, partitions_sha256):
    if digest(study / "registered-contract.json") != contract_sha256:
        raise ValueError("registered contract changed")
    if digest(study / "registered-partitions.json") != partitions_sha256:
        raise ValueError("registered source partitions changed")
    contract = json.loads((study / "registered-contract.json").read_text())
    summary = json.loads((study / "summary.json").read_text())
    if (contract["physical_acceptance"] or contract["manufacturing_acceptance"]
            or summary["functional_head_created"] or summary["physics_run"]
            or summary["physical_acceptance"] or summary["manufacturing_acceptance"]):
        raise ValueError("unsupported engineering promotion")
    if digest(arrays) != contract["arrays_sha256"]:
        raise ValueError("source arrays changed")
    raw = np.load(arrays, allow_pickle=False)
    vertices, faces = raw["vertices"], raw["triangles"]
    for key, dtype in [("vertices", "<f8"), ("triangles", "<i8")]:
        actual = hashlib.sha256(raw[key].astype(dtype, copy=False).tobytes()).hexdigest()
        if actual != contract["source_array_hashes"][key]:
            raise ValueError("decoded source hash mismatch")
    axis_seed = np.load(baseline / "geometry/source-frame-ABC.npy")[2]
    if digest(baseline / "geometry/source-frame-ABC.npy") != contract["baseline_inputs"]["geometry/source-frame-ABC.npy"]:
        raise ValueError("axis-frame input changed")
    thresholds = support_thresholds(contract)
    partitions = json.loads((study / "registered-partitions.json").read_text())["partitions"]
    records = json.loads((study / "primitive-fits.json").read_text())["records"]
    if {p["id"] for p in partitions} != {r["id"] for r in records} or len(partitions) != len(records):
        raise ValueError("fit ledger does not cover every registered region")
    membership = np.zeros(len(vertices), dtype=int)
    selected = {}
    for part in partitions:
        path = study / part["file"]
        if path.parent.resolve() != study.resolve() or digest(path) != part["sha256"]:
            raise ValueError("registered source-ID file changed")
        data = np.load(path, allow_pickle=False)
        selected[part["id"]] = np.unique(faces[data["selected_source_face_ids"]])
        membership[selected[part["id"]]] += 1
    reports, rejections = [], []
    expected_export_ids, expected_export_labels = [], []
    for part, record in zip(partitions, records):
        if part["id"] != record["id"]:
            raise ValueError("region order mismatch")
        if part["kind"] != record["kind"] or "model" in record and record["model"]["kind"] != part["kind"]:
            raise ValueError("registered surface type changed")
        data = np.load(study / part["file"], allow_pickle=False)
        train, held = data["training_source_vertex_ids"], data["evaluation_source_vertex_ids"]
        ids = selected[part["id"]]
        verify_partition(ids[membership[ids] == 1], train, held)
        if record["training_points"] != len(train) or record["evaluation_points"] != len(held):
            raise ValueError("reported point counts differ from the registered partition")
        if "model" in record:
            reports.append(verify_evaluation(record["model"], vertices[held], record,
                                             contract["cylinder_evaluation_limits"], axis_seed))
        else:
            rejections.append(verify_rejection(record, train, held, thresholds))
        if record["retained_as_scan_fit_candidate"]:
            expected_export_ids.append(train)
            expected_export_labels.append(np.full(len(train), len(expected_export_ids) - 1, dtype=int))
    original = np.load(study / "labelled-training-source-ids.npz", allow_pickle=False)
    ids, labels = original["source_vertex_ids"], original["labels"]
    # A study may retain nothing at all; that exports an empty selection rather than failing.
    expected_ids = np.concatenate(expected_export_ids) if expected_export_ids else np.empty(0, dtype=ids.dtype)
    expected_labels = (np.concatenate(expected_export_labels) if expected_export_labels
                       else np.empty(0, dtype=labels.dtype))
    if not np.array_equal(ids, expected_ids) or not np.array_equal(labels, expected_labels):
        raise ValueError("export selector differs from retained training regions")
    export = study / "labelled-training-xyzc.txt"
    # An empty retained set exports an empty file, which np.loadtxt cannot shape on its own.
    cloud = np.loadtxt(export, ndmin=2) if export.stat().st_size else np.empty((0, 4))
    if (cloud.shape != (len(ids), 4) or not np.array_equal(cloud[:, :3], vertices[ids])
            or not np.array_equal(cloud[:, 3], labels)):
        raise ValueError("export coordinates or labels changed")
    return {"passed": True, "source_ID_partitions_verified": len(partitions), "heldout_checks": reports,
            "rejected_attempts": rejections,
            "exported_original_training_vertices_verified": len(ids), "coordinates_unchanged": True,
            "physical_acceptance": False, "manufacturing_acceptance": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--arrays", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--partitions-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.study, args.arrays, args.baseline, args.contract_sha256, args.partitions_sha256), indent=2))
