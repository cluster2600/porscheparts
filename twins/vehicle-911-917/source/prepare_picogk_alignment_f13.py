#!/usr/bin/env python3
"""Corrige le repère F12 par ajustement commun des deux rangées de cylindres."""

import argparse
import json
from pathlib import Path

import numpy as np

from prepare_picogk_scan_f10 import sha256
import prepare_picogk_scan_f10 as scan


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "work/911-917-picogk-f13"
STL = ROOT / "work/911-917-picogk-f10/917-engine-oriented-f10.stl"


def input_hashes():
    paths = (
        "work/911-917-packaging-f1/packaging-report-f1.json",
        "work/917-engine/scan-metrology-f13-report.json",
        "twins/vehicle-911-917/picogk-mechanical-f13.json",
        "work/911-917-picogk-f10/scan-preparation-report-f10.json",
        "twins/vehicle-911-917/source/prepare_picogk_scan_f10.py",
        "twins/vehicle-911-917/source/prepare_picogk_alignment_f13.py",
    )
    return {path: sha256(ROOT / path) for path in paths}


def validate_alignment(report):
    scan.check()
    if (report.get("phase") != "F13"
            or report.get("status") != "scan_row_alignment_corrected_not_physical_datum_validation"
            or any(report.get(key) is not False for key in (
                "crankshaft_axis_measured", "mounting_face_measured", "scale_verified", "physical_orientation_verified"))):
        raise ValueError("unqualified F13 alignment receipt required")
    if report.get("inputs_sha256") != input_hashes() or report.get("input_stl_sha256") != sha256(STL):
        raise ValueError("F13 alignment inputs changed or are unrecorded; rebuild the alignment")
    matrix = np.asarray(report["matrix4x4_row_vector"], dtype=float)
    if (matrix.shape != (4, 4) or not np.isfinite(matrix).all()
            or not np.allclose(matrix[:, 3], [0, 0, 0, 1], rtol=0, atol=1e-6)
            or not np.allclose(matrix[:3, :3] @ matrix[:3, :3].T, np.eye(3), rtol=0, atol=1e-6)
            or not np.isclose(np.linalg.det(matrix[:3, :3]), 1, rtol=0, atol=1e-6)):
        raise ValueError("finite rigid row-vector alignment required")


def bank_frame(registry):
    banks = [np.asarray([v["center_scan_coordinates_obj_units"] for v in registry
                         if v["bank"] == bank], dtype=float) for bank in ("positive", "negative")]
    if any(bank.shape != (6, 3) or not np.isfinite(bank).all() for bank in banks):
        raise ValueError("six centres finis requis par rangée")
    # Le centrage par rangée retire le décalage entre bancs de l'ajustement axial.
    centred = np.concatenate([bank - bank.mean(axis=0) for bank in banks])
    _, singular, vectors = np.linalg.svd(centred, full_matrices=False)
    if singular[0] <= 0 or singular[1] / singular[0] > 0.1:
        raise ValueError("les centres ne définissent pas deux rangées longitudinales")
    x = vectors[0]
    ordered = sorted((v for v in registry if v["bank"] == "positive"),
                     key=lambda v: v["geometric_index"])
    direction = np.subtract(ordered[-1]["center_scan_coordinates_obj_units"],
                            ordered[0]["center_scan_coordinates_obj_units"])
    if x @ direction < 0:
        x = -x
    y = banks[0].mean(axis=0) - banks[1].mean(axis=0)
    y -= x * (y @ x)
    if np.linalg.norm(y) < 1e-6:
        raise ValueError("rangées confondues")
    y /= np.linalg.norm(y)
    return np.vstack((x, y, np.cross(x, y)))


def build():
    scan.check()
    inputs = input_hashes()
    packaging = json.loads((ROOT / "work/911-917-packaging-f1/packaging-report-f1.json").read_text())
    registry = json.loads((ROOT / "work/917-engine/scan-metrology-f13-report.json").read_text())["interface_registry"]
    config = json.loads((ROOT / "twins/vehicle-911-917/picogk-mechanical-f13.json").read_text())
    frame = packaging["scan_screening"]["screening_frame"]
    old = np.asarray(frame["basis_columns_in_scan_coordinates"], dtype=float)
    new = bank_frame(registry)
    layout = next(v for v in packaging["layout_screening"]["trials"]
                  if v["layout_id"] == packaging["layout_screening"]["selected_layout_id"])
    minimum = np.asarray(frame["oriented_bounds_obj_units"]["minimum"])
    old_offset = np.array([layout["engine_scan_bounds_x_mm"][0],
                           -frame["screening_size_mm"][1] / 2, 300.0]) - minimum * frame["scale_mm_per_obj_unit"]
    rotation = old @ new.T
    count = int.from_bytes(STL.open("rb").read(84)[80:84], "little")
    if STL.stat().st_size != 84 + count * 50:
        raise ValueError("STL binaire incohérent")
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    triangles = np.memmap(STL, dtype=dtype, mode="r", offset=84, shape=(count,))
    lower, upper = np.full(3, np.inf), np.full(3, -np.inf)
    for start in range(0, count, 100000):
        points = triangles[start:start + 100000]["vertices"].reshape(-1, 3)
        aligned = (points - old_offset) @ rotation
        lower, upper = np.minimum(lower, aligned.min(0)), np.maximum(upper, aligned.max(0))
    placement = np.array([layout["engine_mating_plane_x_mm"] - upper[0], 0,
                          config["shaft_reference_z_mm"]])
    matrix = np.eye(4)
    matrix[:3, :3] = rotation
    matrix[3, :3] = placement - old_offset @ rotation
    corrected_axis = (new[0] @ old.T) @ rotation
    report = {
        "phase": "F13", "status": "scan_row_alignment_corrected_not_physical_datum_validation",
        "input_stl_sha256": sha256(STL), "triangle_count": count,
        "inputs_sha256": inputs,
        "matrix4x4_row_vector": matrix.tolist(),
        "old_axis_deviation_deg": float(np.degrees(np.arccos(np.clip(old[0] @ new[0], -1, 1)))),
        "fitted_longitudinal_axis_in_vehicle": corrected_axis.tolist(),
        "bounds_min_mm": (lower + placement).tolist(), "bounds_max_mm": (upper + placement).tolist(),
        "axis_reference": "common_direction_fitted_after_centring_each_bank_separately",
        "crankshaft_axis_measured": False, "mounting_face_measured": False,
        "scale_verified": False, "physical_orientation_verified": False,
    }
    validate_alignment(report)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "scan-alignment-f13.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("old_axis_deviation_deg", "fitted_longitudinal_axis_in_vehicle", "bounds_min_mm", "bounds_max_mm")}, indent=2))


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    build()
