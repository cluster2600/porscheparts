#!/usr/bin/env python3
"""Detect the two rows of six cylinder openings in the 917 scan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh
from skimage.feature import canny
from skimage.measure import CircleModel, ransac
from skimage.transform import hough_circle, hough_circle_peaks


def principal_frame(vertices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    centroid = vertices.mean(axis=0)
    values, vectors = np.linalg.eigh(np.cov((vertices - centroid).T))
    frame = vectors[:, np.argsort(values)[::-1]].T
    # Deterministic signs make reports comparable between runs.
    if frame[0, np.argmax(np.abs(frame[0]))] > 0:
        frame[0] *= -1
    if frame[1, np.argmax(np.abs(frame[1]))] < 0:
        frame[1] *= -1
    frame[2] = np.cross(frame[0], frame[1])
    frame[2] /= np.linalg.norm(frame[2])
    return centroid, frame


def refine_circle(points: np.ndarray, initial: np.ndarray, radius: float) -> tuple[np.ndarray, float, float, np.ndarray]:
    distance = np.linalg.norm(points[:, [0, 2]] - initial, axis=1)
    selected = np.abs(distance - radius) < 6.0
    ring = points[selected]
    if len(ring) < 30:
        raise ValueError("not enough ring points")
    model, inliers = ransac(
        ring[:, [0, 2]],
        CircleModel,
        min_samples=3,
        residual_threshold=1.5,
        max_trials=2000,
        rng=917,
    )
    residuals = np.abs(model.residuals(ring[:, [0, 2]][inliers]))
    return np.asarray(model.center), float(model.radius), float(np.percentile(residuals, 95)), ring[inliers]


def depth_mode(values: np.ndarray) -> float:
    lower, upper = np.percentile(values, [2, 98])
    bins = max(4, int(np.ceil(upper - lower)))
    counts, edges = np.histogram(values, bins=bins, range=(lower, upper))
    index = int(np.argmax(counts))
    selected = values[(values >= edges[index]) & (values <= edges[index + 1])]
    return float(np.median(selected))


def detect_bank(coordinates: np.ndarray, sign: int) -> list[dict[str, object]]:
    slab = coordinates[sign * coordinates[:, 1] > 125.0]
    longitudinal_min, longitudinal_max = -450.0, 380.0
    vertical_min, vertical_max = -120.0, 110.0
    resolution = 1.0
    histogram, _, _ = np.histogram2d(
        slab[:, 0],
        slab[:, 2],
        bins=[int((longitudinal_max - longitudinal_min) / resolution), int((vertical_max - vertical_min) / resolution)],
        range=[[longitudinal_min, longitudinal_max], [vertical_min, vertical_max]],
    )
    image = np.log1p(histogram.T)
    image /= image.max() or 1.0
    edges = canny(image, sigma=1.2, low_threshold=0.05, high_threshold=0.2)
    radii = np.arange(38, 61, 2)
    transforms = hough_circle(edges, radii)
    accumulators, x_pixels, y_pixels, detected_radii = hough_circle_peaks(
        transforms,
        radii,
        total_num_peaks=18,
        min_xdistance=80,
        min_ydistance=20,
        threshold=0.25,
    )

    detections = []
    for accumulator, x_pixel, y_pixel, detected_radius in zip(
        accumulators, x_pixels, y_pixels, detected_radii
    ):
        initial = np.asarray(
            [
                longitudinal_min + (x_pixel + 0.5) * resolution,
                vertical_min + (y_pixel + 0.5) * resolution,
            ]
        )
        if not -90.0 < initial[1] < 70.0:
            continue
        if any(abs(initial[0] - item["center_longitudinal_vertical"][0]) < 80.0 for item in detections):
            continue
        try:
            centre, radius, fit_p95, ring = refine_circle(slab, initial, float(detected_radius))
        except ValueError:
            continue
        outward = sign * ring[:, 1]
        detections.append(
            {
                "hough_score": float(accumulator),
                "center_longitudinal_vertical": centre.tolist(),
                "diameter_obj_units": float(2.0 * radius),
                "circle_fit_p95_obj_units": fit_p95,
                "rim_outward_depth_mode_obj_units": depth_mode(outward),
                "ring_inliers": int(len(ring)),
            }
        )
        if len(detections) == 6:
            break
    if len(detections) != 6:
        raise RuntimeError(f"expected six openings on bank {sign:+d}, found {len(detections)}")
    detections.sort(key=lambda item: item["center_longitudinal_vertical"][0])
    return detections


def pitch(bank: list[dict[str, object]]) -> dict[str, object]:
    centres = np.asarray([item["center_longitudinal_vertical"] for item in bank])
    gaps = np.diff(centres[:, 0])
    central_index = int(np.argmax(gaps))
    regular = np.delete(gaps, central_index)
    return {
        "successive_longitudinal_gaps_obj_units": gaps.tolist(),
        "median_regular_pitch_obj_units": float(np.median(regular)),
        "central_split_gap_obj_units": float(gaps[central_index]),
        "central_split_after_cylinder": central_index + 1,
        "vertical_spread_obj_units": float(np.ptp(centres[:, 1])),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    mesh = trimesh.load_mesh(args.input, process=False)
    vertices = np.asarray(mesh.vertices)
    centroid, frame = principal_frame(vertices)
    coordinates = (vertices - centroid) @ frame.T
    positive = detect_bank(coordinates, 1)
    negative = detect_bank(coordinates, -1)

    for sign, bank in ((1, positive), (-1, negative)):
        for item in bank:
            longitudinal, vertical = item["center_longitudinal_vertical"]
            depth = sign * item["rim_outward_depth_mode_obj_units"]
            local = np.asarray([longitudinal, depth, vertical])
            item["center_scan_coordinates"] = (centroid + local @ frame).tolist()
            item["axis_scan_coordinates"] = (sign * frame[1]).tolist()

    positive_l = np.asarray([item["center_longitudinal_vertical"][0] for item in positive])
    negative_l = np.asarray([item["center_longitudinal_vertical"][0] for item in negative])
    all_diameters = [item["diameter_obj_units"] for item in positive + negative]
    report = {
        "input": str(args.input.resolve()),
        "status": "F1_detected_exterior_interfaces",
        "units": "OBJ units; 1 unit = 1 mm is plausible but unconfirmed",
        "centroid_scan_coordinates": centroid.tolist(),
        "frame_rows_longitudinal_bank_axis_vertical": frame.tolist(),
        "banks": {"positive": positive, "negative": negative},
        "pitch": {"positive": pitch(positive), "negative": pitch(negative)},
        "mean_visible_opening_diameter_obj_units": float(np.mean(all_diameters)),
        "opening_diameter_range_obj_units": [float(np.min(all_diameters)), float(np.max(all_diameters))],
        "bank_longitudinal_stagger_obj_units": float(np.median(negative_l - positive_l)),
        "comparison_993": {
            "status": "not_dimensionally_comparable",
            "available_repo_fact": "993 nominal bore 100 from unverified OCR record TD-CE78EA5FED2C",
            "conclusion": "The 917 scan is an architecture and pipeline reference, not a 993 fitment source.",
            "required_for_993": [
                "named 993 engine variant",
                "measured 993 cylinder spacing, spigot and stud pattern",
                "confirmed scale for both datasets",
            ],
        },
        "limitations": [
            "Detected circles are visible openings in a projected scan; they are not certified cylinder bores.",
            "The depth value is a modal rim estimate, not a machined datum plane.",
            "Hough and RANSAC residuals do not include scale or scanner calibration uncertainty.",
            "Visual and physical measurement confirmation is required before semantic release.",
        ],
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

