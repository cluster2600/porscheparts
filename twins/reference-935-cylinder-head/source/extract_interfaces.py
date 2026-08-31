#!/usr/bin/env python3
"""Extract provisional interface measurements from the accepted light mesh."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh
from skimage.measure import CircleModel, ransac

from scan_frame import A_AXIS, B_AXIS, C_AXIS, FRAME, scan_to_abc


def section_points(mesh: trimesh.Trimesh, axis: np.ndarray, offset: float) -> np.ndarray:
    section = mesh.section(plane_origin=axis * offset, plane_normal=axis)
    if section is None:
        raise ValueError(f"empty section at {offset}")
    return scan_to_abc(np.vstack(section.discrete))


def vertex_slab(mesh: trimesh.Trimesh, coordinate: int, offset: float, half_width: float = 0.35) -> np.ndarray:
    points = scan_to_abc(mesh.vertices)
    return points[np.abs(points[:, coordinate] - offset) < half_width]


def robust_circle(
    points: np.ndarray,
    centre_hint: tuple[float, float],
    radius_range: tuple[float, float],
    residual_threshold: float = 0.7,
) -> dict[str, object]:
    distance = np.linalg.norm(points - np.asarray(centre_hint), axis=1)
    selected = points[(distance > radius_range[0]) & (distance < radius_range[1])]
    if len(selected) < 12:
        raise ValueError("not enough points for a circle fit")
    model, inliers = ransac(
        selected,
        CircleModel,
        min_samples=3,
        residual_threshold=residual_threshold,
        max_trials=3000,
        rng=935,
    )
    residual = np.abs(np.linalg.norm(selected[inliers] - model.center, axis=1) - model.radius)
    return {
        "center": np.asarray(model.center).tolist(),
        "diameter_obj_units": float(2.0 * model.radius),
        "inliers": int(np.count_nonzero(inliers)),
        "fit_p95_obj_units": float(np.percentile(residual, 95)),
    }


def stud_holes(mesh: trimesh.Trimesh) -> list[dict[str, object]]:
    section = mesh.section(plane_origin=C_AXIS * -91.0, plane_normal=C_AXIS)
    holes = []
    for curve in section.discrete:
        points = scan_to_abc(curve)[:, :2]
        if np.linalg.norm(points[0] - points[-1]) > 0.2:
            continue
        try:
            model = CircleModel.from_estimate(points)
        except ValueError:
            continue
        centre = np.asarray(model.center)
        if not (75 < centre[0] < 180 and -220 < centre[1] < -120 and 4 < model.radius < 7):
            continue
        residual = np.abs(model.residuals(points))
        holes.append(
            {
                "center_A_B": centre.tolist(),
                "diameter_obj_units": float(2.0 * model.radius),
                "fit_p95_obj_units": float(np.percentile(residual, 95)),
            }
        )
    holes.sort(key=lambda item: (item["center_A_B"][0], item["center_A_B"][1]))
    return holes[:4]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    mesh = trimesh.load_mesh(args.input, process=False)

    combustion = {}
    for offset, label, radii in [(-88.0, "outer_register", (48.0, 62.0)), (-91.0, "chamber_step", (38.0, 50.0))]:
        points = section_points(mesh, C_AXIS, offset)[:, :2]
        combustion[label] = {"plane_C": offset, **robust_circle(points, (128.0, -169.0), radii)}

    ports: dict[str, list[dict[str, object]]] = {"low_B": [], "high_B": []}
    for label, offsets, hint in [
        ("low_B", [-251.0, -245.0, -240.0], (128.0, -122.0)),
        ("high_B", [-62.0, -65.0, -70.0, -75.0, -80.0, -85.0, -90.0], (128.0, -133.0)),
    ]:
        for offset in offsets:
            try:
                # A thin vertex slab is more robust than traced section paths
                # where scan gaps interrupt the port wall.
                points = vertex_slab(mesh, 1, offset)[:, [0, 2]]
                fit = robust_circle(points, hint, (17.0, 24.0))
            except ValueError as error:
                fit = {"status": "unresolved", "reason": str(error)}
            ports[label].append({"plane_B": offset, **fit})

    holes = stud_holes(mesh)
    pattern = None
    if len(holes) == 4:
        centres = np.asarray([item["center_A_B"] for item in holes])
        pattern = {
            "span_A_obj_units": float(centres[:, 0].max() - centres[:, 0].min()),
            "span_B_obj_units": float(centres[:, 1].max() - centres[:, 1].min()),
            "mean_hole_diameter_obj_units": float(
                np.mean([item["diameter_obj_units"] for item in holes])
            ),
        }

    report = {
        "input": str(args.input.resolve()),
        "frame_rows_A_B_C": FRAME.tolist(),
        "units": "OBJ units; millimetres plausible but unconfirmed",
        "accepted_mesh_simplification_p95_obj_units": 0.059,
        "combustion_interface": combustion,
        "head_stud_holes_at_C_minus_91": holes,
        "head_stud_pattern": pattern,
        "port_sections": ports,
        "comparison_993": {
            "status": "blocked_missing_reference_geometry",
            "available_repo_fact": "993 nominal bore 100 from OCR record TD-CE78EA5FED2C; unverified transcription",
            "conclusion": "No compatibility claim can be made from bore versus register/chamber features.",
            "required": [
                "authoritative or directly measured 993 stud pattern",
                "993 cylinder register and chamber geometry for a named engine variant",
                "993 intake and exhaust flange geometry",
                "physical scale control dimension on this scan",
            ],
        },
        "limitations": [
            "Circle-fit residual is not total metrology uncertainty.",
            "The unconfirmed OBJ scale is the dominant systematic uncertainty.",
            "Fits describe visible scan sections and not hidden oil galleries, seats or guide bores.",
            "All values remain provisional until checked on the physical part.",
        ],
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
