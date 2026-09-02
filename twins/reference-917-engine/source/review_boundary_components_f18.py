#!/usr/bin/env python3
"""Inventory every open-boundary component for human 3D review.

F18 is deliberately geometric.  A high score means only that a boundary looks
planar and circular enough to review; it never names or confirms an engine
interface.
"""

from __future__ import annotations

import argparse
import colorsys
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any


SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
PLY_NAME = "boundary-components-f18.ply"
REPORT_NAME = "boundary-review-f18.json"
CANDIDATE_THRESHOLDS = {
    "minimum_vertex_count": 12,
    "maximum_relative_circle_fit_p95": 0.12,
    "maximum_planarity_ratio": 0.05,
    "minimum_angular_coverage": 0.65,
    "minimum_candidate_score": 0.80,
}
RELEASE_GATES = {
    "engine_identity_confirmed": False,
    "scale_confirmed": False,
    "units_confirmed": False,
    "axis_semantics_confirmed": False,
    "semantic_interfaces_confirmed": False,
    "cad_reconstruction_released": False,
    "classical_solver_released": False,
    "physicsnemo_dataset_released": False,
    "physicsnemo_training_released": False,
    "omniverse_simready_released": False,
    "fabrication_released": False,
    "engine_start_released": False,
}


class ReviewError(ValueError):
    """Raised when the F18 fail-closed input contract is not satisfied."""


def _runtime_module() -> Any:
    """Import NumPy lazily so repository-only checks stay light."""

    try:
        import numpy as np
    except ImportError as error:  # pragma: no cover - exercised in the F17 image
        raise ReviewError(
            "F18 requires the NumPy runtime from the scan-mesh F17 image"
        ) from error
    return np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_triangular_mesh(path: Path, np: Any) -> tuple[Any, Any]:
    try:
        import trimesh
    except ImportError as error:  # pragma: no cover - runtime contract error
        raise ReviewError(
            "F18 mesh loading requires Trimesh from the scan-mesh F17 image"
        ) from error

    loaded = trimesh.load(path, force="mesh", process=False, maintain_order=True)
    if not isinstance(loaded, trimesh.Trimesh) or not len(loaded.faces):
        raise ReviewError("input must resolve to one non-empty triangular mesh")
    vertices = np.asarray(loaded.vertices, dtype=np.float64)
    faces = np.asarray(loaded.faces, dtype=np.int64)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.all(np.isfinite(vertices)):
        raise ReviewError("input vertices must be a finite N x 3 array")
    if faces.ndim != 2 or faces.shape[1] != 3:
        raise ReviewError("input faces must be triangulated")
    if len(vertices) >= 2**32:
        raise ReviewError("F18 packed edge keys require fewer than 2^32 vertices")
    if len(faces) and (int(faces.min()) < 0 or int(faces.max()) >= len(vertices)):
        raise ReviewError("input face index is outside the vertex array")
    return vertices, faces


def _edge_incidence(faces: Any, np: Any) -> tuple[Any, dict[str, int]]:
    """Return incidence-one edges using compact uint64 keys."""

    keys = np.empty(len(faces) * 3, dtype=np.uint64)
    cursor = 0
    for left_column, right_column in ((0, 1), (1, 2), (2, 0)):
        left = faces[:, left_column].astype(np.uint64, copy=False)
        right = faces[:, right_column].astype(np.uint64, copy=False)
        low = np.minimum(left, right)
        high = np.maximum(left, right)
        batch = (low << np.uint64(32)) | high
        keys[cursor : cursor + len(batch)] = batch
        cursor += len(batch)
    keys = keys[(keys >> np.uint64(32)) != (keys & np.uint64(0xFFFFFFFF))]
    keys.sort()
    if not len(keys):
        return np.empty((0, 2), dtype=np.int64), {
            "edge_occurrences": 0,
            "unique_edges": 0,
            "manifold_edges": 0,
            "non_manifold_edges": 0,
        }
    starts = np.flatnonzero(np.r_[True, keys[1:] != keys[:-1]])
    ends = np.r_[starts[1:], len(keys)]
    incidence = ends - starts
    unique_keys = keys[starts]
    boundary_keys = unique_keys[incidence == 1]
    boundary_edges = np.column_stack(
        (
            boundary_keys >> np.uint64(32),
            boundary_keys & np.uint64(0xFFFFFFFF),
        )
    ).astype(np.int64, copy=False)
    return boundary_edges, {
        "edge_occurrences": int(len(keys)),
        "unique_edges": int(len(unique_keys)),
        "manifold_edges": int(np.count_nonzero(incidence == 2)),
        "non_manifold_edges": int(np.count_nonzero(incidence > 2)),
    }


def _fit_circle(projected: Any, np: Any) -> dict[str, Any] | None:
    if len(projected) < 3:
        return None
    matrix = np.column_stack((2.0 * projected, np.ones(len(projected))))
    rhs = np.einsum("ij,ij->i", projected, projected)
    solution, *_ = np.linalg.lstsq(matrix, rhs, rcond=None)
    centre = solution[:2]
    radius_squared = float(solution[2] + centre @ centre)
    if not math.isfinite(radius_squared) or radius_squared <= 0.0:
        return None
    radius = math.sqrt(radius_squared)
    residuals = np.abs(np.linalg.norm(projected - centre, axis=1) - radius)
    angles = np.sort(
        np.mod(
            np.arctan2(projected[:, 1] - centre[1], projected[:, 0] - centre[0]),
            2.0 * math.pi,
        )
    )
    gaps = np.diff(np.r_[angles, angles[0] + 2.0 * math.pi])
    coverage = float(1.0 - float(gaps.max()) / (2.0 * math.pi))
    p95 = float(np.percentile(residuals, 95))
    rms = float(np.sqrt(np.mean(residuals * residuals)))
    return {
        "centre_2d": centre,
        "radius": radius,
        "rms": rms,
        "p95": p95,
        "relative_p95": p95 / radius,
        "angular_coverage": coverage,
    }


def _ordered_closed_loop(
    compact_vertex_ids: Any, compact_edges: Any, active_vertices: Any
) -> list[int] | None:
    adjacency: dict[int, list[int]] = {int(item): [] for item in compact_vertex_ids}
    for left, right in compact_edges:
        adjacency[int(left)].append(int(right))
        adjacency[int(right)].append(int(left))
    if not adjacency or any(len(neighbours) != 2 for neighbours in adjacency.values()):
        return None
    start = min(adjacency, key=lambda item: int(active_vertices[item]))
    order = [start]
    previous: int | None = None
    current = start
    while True:
        neighbours = sorted(adjacency[current], key=lambda item: int(active_vertices[item]))
        following = neighbours[0] if neighbours[0] != previous else neighbours[1]
        if following == start:
            return order if len(order) == len(adjacency) else None
        if following in order:
            return None
        order.append(following)
        previous, current = current, following


def _convex_hull_area(projected: Any) -> float | None:
    """Return a dependency-free 2D convex-hull area proxy."""

    points = sorted({(float(point[0]), float(point[1])) for point in projected})
    if len(points) < 3:
        return None

    def cross(origin: tuple[float, float], left: tuple[float, float], right: tuple[float, float]) -> float:
        return (left[0] - origin[0]) * (right[1] - origin[1]) - (
            left[1] - origin[1]
        ) * (right[0] - origin[0])

    lower: list[tuple[float, float]] = []
    for point in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0.0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[float, float]] = []
    for point in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0.0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        return None
    twice_area = sum(
        left[0] * right[1] - left[1] * right[0]
        for left, right in zip(hull, hull[1:] + hull[:1])
    )
    return 0.5 * abs(twice_area)


def _projected_area(
    projected: Any,
    compact_vertex_ids: Any,
    compact_edges: Any,
    active_vertices: Any,
    closed_loop: bool,
    np: Any,
) -> tuple[float | None, str]:
    if len(projected) < 3:
        return None, "undefined_degenerate"
    if closed_loop:
        ordered = _ordered_closed_loop(compact_vertex_ids, compact_edges, active_vertices)
        if ordered is not None:
            positions = {int(item): index for index, item in enumerate(compact_vertex_ids)}
            polygon = projected[[positions[item] for item in ordered]]
            area = 0.5 * abs(
                float(
                    np.dot(polygon[:, 0], np.roll(polygon[:, 1], -1))
                    - np.dot(polygon[:, 1], np.roll(polygon[:, 0], -1))
                )
            )
            return area, "closed_loop_pca_plane_shoelace"
    area = _convex_hull_area(projected)
    if area is None:
        return None, "undefined_degenerate"
    return area, "pca_plane_convex_hull_proxy"


def _component_metrics(
    points: Any,
    compact_vertex_ids: Any,
    compact_edges: Any,
    active_vertices: Any,
    vertices: Any,
    np: Any,
) -> dict[str, Any]:
    source_edges = active_vertices[compact_edges]
    edge_vectors = vertices[source_edges[:, 1]] - vertices[source_edges[:, 0]]
    perimeter = float(np.linalg.norm(edge_vectors, axis=1).sum())
    local_degrees = np.bincount(
        compact_edges.reshape(-1), minlength=len(active_vertices)
    )[compact_vertex_ids]
    closed_loop = bool(
        len(points) >= 3
        and len(compact_edges) == len(points)
        and np.all(local_degrees == 2)
    )
    centroid = points.mean(axis=0)
    bounds_min = points.min(axis=0)
    bounds_max = points.max(axis=0)

    plane_rms: float | None = None
    planarity_ratio: float | None = None
    normal: Any = None
    circle: dict[str, Any] | None = None
    projected = None
    if len(points) >= 3:
        centred = points - centroid
        covariance = (centred.T @ centred) / float(len(points))
        values, vectors = np.linalg.eigh(covariance)
        order = np.argsort(values)[::-1]
        values = np.maximum(values[order], 0.0)
        vectors = vectors[:, order]
        normal = vectors[:, 2]
        dominant = int(np.argmax(np.abs(normal)))
        if normal[dominant] < 0.0:
            normal = -normal
        plane_rms = float(np.sqrt(np.mean((centred @ normal) ** 2)))
        if float(values[1]) > np.finfo(np.float64).eps:
            planarity_ratio = float(values[2] / values[1])
            projected = centred @ vectors[:, :2]
            circle = _fit_circle(projected, np)

    area: float | None = None
    area_method = "undefined_degenerate"
    if projected is not None:
        area, area_method = _projected_area(
            projected,
            compact_vertex_ids,
            compact_edges,
            active_vertices,
            closed_loop,
            np,
        )

    relative_p95 = None if circle is None else float(circle["relative_p95"])
    angular_coverage = None if circle is None else float(circle["angular_coverage"])
    topology_gate = closed_loop
    vertex_gate = len(points) >= CANDIDATE_THRESHOLDS["minimum_vertex_count"]
    circle_gate = bool(
        relative_p95 is not None
        and relative_p95
        <= CANDIDATE_THRESHOLDS["maximum_relative_circle_fit_p95"]
    )
    plane_gate = bool(
        planarity_ratio is not None
        and planarity_ratio <= CANDIDATE_THRESHOLDS["maximum_planarity_ratio"]
    )
    coverage_gate = bool(
        angular_coverage is not None
        and angular_coverage >= CANDIDATE_THRESHOLDS["minimum_angular_coverage"]
    )
    planarity_factor = (
        0.0
        if planarity_ratio is None
        else max(0.0, 1.0 - planarity_ratio / 0.10)
    )
    circularity_factor = (
        0.0 if relative_p95 is None else max(0.0, 1.0 - relative_p95 / 0.20)
    )
    coverage_factor = 0.0 if angular_coverage is None else angular_coverage
    score = float(
        0.30 * float(closed_loop)
        + 0.25 * planarity_factor
        + 0.30 * circularity_factor
        + 0.15 * coverage_factor
    )
    score_gate = score >= CANDIDATE_THRESHOLDS["minimum_candidate_score"]
    gates = {
        "closed_simple_boundary_loop": topology_gate,
        "minimum_vertex_count": vertex_gate,
        "relative_circle_fit_p95": circle_gate,
        "planarity_ratio": plane_gate,
        "angular_coverage": coverage_gate,
        "candidate_score": score_gate,
    }
    review_class = "candidate" if all(gates.values()) else "unclassified"

    return {
        "boundary_edge_count": int(len(compact_edges)),
        "boundary_vertex_count": int(len(points)),
        "minimum_source_vertex_index_1_based": int(active_vertices[compact_vertex_ids].min())
        + 1,
        "endpoint_count": int(np.count_nonzero(local_degrees == 1)),
        "branched_vertex_count": int(np.count_nonzero(local_degrees > 2)),
        "closed_loop": closed_loop,
        "centroid_obj_units": [float(value) for value in centroid],
        "bounds_min_obj_units": [float(value) for value in bounds_min],
        "bounds_max_obj_units": [float(value) for value in bounds_max],
        "bbox_extent_obj_units": [float(value) for value in bounds_max - bounds_min],
        "perimeter_obj_units": perimeter,
        "projected_area_obj_units_squared": area,
        "projected_area_method": area_method,
        "planarity": {
            "normal_unoriented_scan_coordinates": (
                None if normal is None else [float(value) for value in normal]
            ),
            "plane_rms_obj_units": plane_rms,
            "planarity_ratio": planarity_ratio,
        },
        "circularity": {
            "fit_center_obj_units": (
                None
                if circle is None or projected is None
                else [
                    float(value)
                    for value in (
                        centroid
                        + vectors[:, :2] @ circle["centre_2d"]
                    )
                ]
            ),
            "diameter_obj_units": None if circle is None else 2.0 * float(circle["radius"]),
            "circle_fit_rms_obj_units": None if circle is None else float(circle["rms"]),
            "circle_fit_p95_obj_units": None if circle is None else float(circle["p95"]),
            "relative_circle_fit_p95": relative_p95,
            "angular_coverage": angular_coverage,
            "circularity_factor": circularity_factor,
        },
        "candidate_score": score,
        "candidate_gates": gates,
        "review_class": review_class,
        "semantic_label": None,
        "interface_confirmed": False,
        "human_review_state": "pending",
    }


def _connected_components(compact_edges: Any, vertex_count: int, np: Any) -> tuple[int, Any]:
    """Connected components for the small incidence-one graph."""

    parent = list(range(vertex_count))
    size = [1] * vertex_count

    def find(vertex: int) -> int:
        root = vertex
        while parent[root] != root:
            root = parent[root]
        while parent[vertex] != vertex:
            following = parent[vertex]
            parent[vertex] = root
            vertex = following
        return root

    for left_value, right_value in compact_edges:
        left, right = find(int(left_value)), find(int(right_value))
        if left == right:
            continue
        if size[left] < size[right]:
            left, right = right, left
        parent[right] = left
        size[left] += size[right]
    roots = np.asarray([find(vertex) for vertex in range(vertex_count)], dtype=np.int64)
    _, labels = np.unique(roots, return_inverse=True)
    return int(labels.max()) + 1 if len(labels) else 0, labels


def analyze_boundary_components(vertices: Any, faces: Any, np: Any) -> dict[str, Any]:
    boundary_edges, incidence = _edge_incidence(faces, np)
    if not len(boundary_edges):
        return {
            "incidence": incidence,
            "boundary_edges": boundary_edges,
            "active_vertices": np.empty(0, dtype=np.int64),
            "labels": np.empty(0, dtype=np.int64),
            "stable_ranks": np.empty(0, dtype=np.int64),
            "candidate_flags": np.empty(0, dtype=np.uint8),
            "components": [],
        }

    active_vertices, inverse = np.unique(boundary_edges, return_inverse=True)
    compact_edges = inverse.reshape((-1, 2))
    component_count, labels = _connected_components(
        compact_edges, len(active_vertices), np
    )
    edge_labels = labels[compact_edges[:, 0]]
    if not np.array_equal(edge_labels, labels[compact_edges[:, 1]]):
        raise ReviewError("boundary graph contains a cross-component edge")

    edge_counts = np.bincount(edge_labels, minlength=component_count)
    vertex_counts = np.bincount(labels, minlength=component_count)
    minimum_source_vertex = np.full(component_count, len(vertices), dtype=np.int64)
    np.minimum.at(minimum_source_vertex, labels, active_vertices)
    ordered_labels = sorted(
        range(component_count),
        key=lambda label: (
            -int(edge_counts[label]),
            -int(vertex_counts[label]),
            int(minimum_source_vertex[label]),
        ),
    )

    components = []
    raw_to_rank = np.empty(component_count, dtype=np.int64)
    raw_candidate = np.zeros(component_count, dtype=np.uint8)
    for rank, raw_label in enumerate(ordered_labels, start=1):
        compact_vertex_ids = np.flatnonzero(labels == raw_label)
        component_edges = compact_edges[edge_labels == raw_label]
        points = vertices[active_vertices[compact_vertex_ids]]
        metrics = _component_metrics(
            points,
            compact_vertex_ids,
            component_edges,
            active_vertices,
            vertices,
            np,
        )
        metrics["component_id"] = f"boundary_{rank:04d}"
        metrics["component_rank"] = rank
        metrics["source_graph_component_id"] = int(raw_label)
        components.append(metrics)
        raw_to_rank[raw_label] = rank
        raw_candidate[raw_label] = int(metrics["review_class"] == "candidate")

    return {
        "incidence": incidence,
        "boundary_edges": boundary_edges,
        "active_vertices": active_vertices,
        "labels": labels,
        "stable_ranks": raw_to_rank[labels],
        "candidate_flags": raw_candidate[labels],
        "components": components,
    }


def _component_color(rank: int, candidate: bool) -> tuple[int, int, int, int]:
    hue = (rank * 0.6180339887498949) % 1.0
    saturation = 0.88 if candidate else 0.58
    value = 1.0 if candidate else 0.86
    red, green, blue = colorsys.hsv_to_rgb(hue, saturation, value)
    return round(red * 255), round(green * 255), round(blue * 255), 255


def write_colored_ply(
    path: Path,
    points: Any,
    stable_ranks: Any,
    candidate_flags: Any,
    np: Any,
) -> None:
    records = np.empty(
        len(points),
        dtype=np.dtype(
            [
                ("x", "<f8"),
                ("y", "<f8"),
                ("z", "<f8"),
                ("red", "u1"),
                ("green", "u1"),
                ("blue", "u1"),
                ("alpha", "u1"),
                ("component_rank", "<u4"),
                ("candidate", "u1"),
            ],
            align=False,
        ),
    )
    if len(points):
        records["x"], records["y"], records["z"] = points.T
        for rank in np.unique(stable_ranks):
            mask = stable_ranks == rank
            candidate = bool(candidate_flags[mask][0])
            red, green, blue, alpha = _component_color(int(rank), candidate)
            records["red"][mask] = red
            records["green"][mask] = green
            records["blue"][mask] = blue
            records["alpha"][mask] = alpha
        records["component_rank"] = stable_ranks.astype(np.uint32, copy=False)
        records["candidate"] = candidate_flags.astype(np.uint8, copy=False)
    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        "comment F18 local human-review boundary point cloud; no semantic interfaces\n"
        f"element vertex {len(records)}\n"
        "property double x\nproperty double y\nproperty double z\n"
        "property uchar red\nproperty uchar green\nproperty uchar blue\nproperty uchar alpha\n"
        "property uint component_rank\nproperty uchar candidate\n"
        "end_header\n"
    ).encode("ascii")
    with path.open("wb") as stream:
        stream.write(header)
        records.tofile(stream)


def _synthetic_fixture(np: Any) -> tuple[Any, Any]:
    segment_count = 32
    vertices = [[0.0, 0.0, 0.0]]
    for index in range(segment_count):
        angle = 2.0 * math.pi * index / segment_count
        vertices.append([math.cos(angle), math.sin(angle), 0.0])
    faces = [
        [0, 1 + index, 1 + ((index + 1) % segment_count)]
        for index in range(segment_count)
    ]
    triangle_offset = len(vertices)
    vertices.extend([[3.0, 0.0, 0.0], [4.0, 0.0, 0.0], [3.0, 1.0, 0.0]])
    faces.append([triangle_offset, triangle_offset + 1, triangle_offset + 2])
    return np.asarray(vertices, dtype=np.float64), np.asarray(faces, dtype=np.int64)


def build_report(
    analysis: dict[str, Any],
    source: dict[str, Any],
    ply_path: Path,
) -> dict[str, Any]:
    components = analysis["components"]
    return {
        "schema": "porsche-917-boundary-human-review/f18-v1",
        "phase": "F18",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_geometric_inventory_pending_human_review",
        "source": source,
        "coordinate_policy": {
            "reported_units": "input coordinate units",
            "metric_conversion_applied": False,
            "scale_inference_applied": False,
            "axis_semantics_inferred": False,
        },
        "topology": {
            **analysis["incidence"],
            "boundary_edges": int(len(analysis["boundary_edges"])),
            "boundary_vertices": int(len(analysis["active_vertices"])),
            "boundary_components": len(components),
            "reported_boundary_components": len(components),
            "boundary_components_truncated": False,
        },
        "classification_policy": {
            "allowed_review_classes": ["candidate", "unclassified"],
            "candidate_thresholds": CANDIDATE_THRESHOLDS,
            "candidate_score_weights": {
                "closed_loop": 0.30,
                "planarity": 0.25,
                "circularity": 0.30,
                "angular_coverage": 0.15,
            },
            "diameter_filter_applied": False,
            "semantic_identification_applied": False,
            "candidate_means": "geometric shape to inspect, never a confirmed engine interface",
        },
        "summary": {
            "candidate_count": sum(
                item["review_class"] == "candidate" for item in components
            ),
            "unclassified_count": sum(
                item["review_class"] == "unclassified" for item in components
            ),
            "confirmed_interface_count": 0,
            "human_review_pending_count": len(components),
        },
        "components": components,
        "visualization": {
            "path": ply_path.name,
            "sha256": sha256(ply_path),
            "bytes": ply_path.stat().st_size,
            "kind": "binary_little_endian_colored_boundary_vertex_point_cloud",
            "point_count": int(len(analysis["active_vertices"])),
            "color_mapping": "stable component rank; candidates use higher saturation",
            "embedded_properties": ["component_rank", "candidate"],
            "geometry_scope": "boundary vertices only; no faces and no source scan copy",
        },
        "release_gates": RELEASE_GATES,
        "limitations": [
            "Every component remains pending human review.",
            "Candidate is a geometric review class, not a semantic or functional identification.",
            "Projected area is a planar proxy and is not a physical port or sealing area.",
            "Normal direction is unoriented and has no engine-axis meaning.",
            "Input coordinate units are not converted to millimetres.",
            "The colored PLY is a local derived asset and must stay outside Git.",
            "No F18 result authorizes CAD, simulation, PhysicsNeMo, fabrication or engine start.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input-sha256")
    parser.add_argument("--expected-boundary-components", type=int)
    parser.add_argument("--synthetic-self-test", action="store_true")
    args = parser.parse_args()

    np = _runtime_module()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.synthetic_self_test:
        if args.input is not None or args.input_sha256 is not None:
            raise SystemExit("synthetic self-test does not accept an input or source hash")
        vertices, faces = _synthetic_fixture(np)
        source = {
            "mode": "synthetic_self_test",
            "input_path": None,
            "actual_sha256": None,
            "expected_sha256": None,
            "provenance_hash_matched": False,
            "raw_geometry_embedded_in_report": False,
        }
        expected_components = 2
    else:
        if args.input is None:
            raise SystemExit("--input is required outside synthetic self-test mode")
        if SHA256_PATTERN.fullmatch(args.input_sha256 or "") is None:
            raise SystemExit("--input-sha256 must be a lowercase 64-character SHA-256")
        if not args.expected_boundary_components or args.expected_boundary_components <= 0:
            raise SystemExit("--expected-boundary-components must be a positive integer")
        actual_sha256 = sha256(args.input)
        if actual_sha256 != args.input_sha256:
            raise SystemExit("input SHA-256 mismatch")
        vertices, faces = _load_triangular_mesh(args.input, np)
        source = {
            "mode": "canonical_external_scan",
            "input_path": str(args.input.resolve()),
            "input_bytes": args.input.stat().st_size,
            "actual_sha256": actual_sha256,
            "expected_sha256": args.input_sha256,
            "provenance_hash_matched": True,
            "input_read_only_mount_verified_by_process": False,
            "raw_geometry_embedded_in_report": False,
        }
        expected_components = args.expected_boundary_components

    analysis = analyze_boundary_components(vertices, faces, np)
    actual_components = len(analysis["components"])
    if actual_components != expected_components:
        raise SystemExit(
            f"boundary component count mismatch: expected {expected_components}, got {actual_components}"
        )
    ply_path = args.output / PLY_NAME
    write_colored_ply(
        ply_path,
        vertices[analysis["active_vertices"]],
        analysis["stable_ranks"],
        analysis["candidate_flags"],
        np,
    )
    report = build_report(analysis, source, ply_path)
    if report["summary"]["confirmed_interface_count"] != 0:
        raise SystemExit("F18 must not confirm any interface")
    report_path = args.output / REPORT_NAME
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"report": str(report_path), **report["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
