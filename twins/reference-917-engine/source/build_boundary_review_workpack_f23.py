#!/usr/bin/env python3
"""Build a local-only human-review workpack from the F18 boundary inventory.

F23 never promotes a geometric boundary to an engine interface.  It only makes
two deterministic review cohorts easier to inspect: every F18 circular
candidate and an equally sized control cohort of large unclassified boundaries.
All point coordinates remain in the ignored work directory.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import html
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
from typing import Any, Callable


SCHEMA = "porsche-917-boundary-review-workpack/f23-v1"
REPORT_NAME = "boundary-review-workpack-f23.json"
CSV_NAME = "boundary-review-queue-f23.csv"
SVG_NAME = "boundary-review-atlas-f23.svg"
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
COMPONENT_ID_PATTERN = re.compile(r"boundary_[0-9]{4}")
ALLOWED_REVIEW_STATES = ("artifact", "physical_boundary", "undetermined")
ALLOWED_EVIDENCE_KINDS = (
    "scan_observation",
    "physical_measurement",
    "primary_source",
    "photograph",
    "other_local_reference",
)
SECONDARY_SCORE_WEIGHTS = {
    "projected_area": 0.35,
    "bbox_diagonal": 0.30,
    "perimeter": 0.25,
    "boundary_vertex_count": 0.10,
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
PLY_PROPERTIES = (
    "property double x",
    "property double y",
    "property double z",
    "property uchar red",
    "property uchar green",
    "property uchar blue",
    "property uchar alpha",
    "property uint component_rank",
    "property uchar candidate",
)
PLY_RECORD = struct.Struct("<dddBBBBIB")
MAX_RENDER_POINTS_PER_COMPONENT = 360
MAX_JSON_BYTES = 32 * 1024 * 1024
MAX_PLY_BYTES = 128 * 1024 * 1024
MAX_PLY_HEADER_BYTES = 64 * 1024
MAX_PLY_HEADER_LINE_BYTES = 4096
MAX_PLY_VERTICES = 3_500_000
MAX_COMPONENTS = 9999
MAX_ABS_COORDINATE = 1.0e12
MAX_ABS_JSON_NUMBER = 1.0e100


class WorkpackError(ValueError):
    """Raised when an F23 fail-closed contract is not satisfied."""


def _read_regular_file(path: Path, *, maximum_bytes: int, label: str) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    elif path.is_symlink():  # pragma: no cover - POSIX CI uses O_NOFOLLOW
        raise WorkpackError(f"{label} cannot be a symbolic link")
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise WorkpackError(f"cannot open {label}") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise WorkpackError(f"{label} must be a regular file")
        if metadata.st_size > maximum_bytes:
            raise WorkpackError(f"{label} exceeds the {maximum_bytes}-byte limit")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, maximum_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum_bytes:
                raise WorkpackError(f"{label} exceeds the {maximum_bytes}-byte limit")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _validate_json_numbers(value: Any) -> None:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, int):
        if abs(value) > int(MAX_ABS_JSON_NUMBER):
            raise WorkpackError("JSON integer magnitude exceeds the F23 limit")
        return
    if isinstance(value, float):
        if not math.isfinite(value) or abs(value) > MAX_ABS_JSON_NUMBER:
            raise WorkpackError("JSON numbers must be finite and bounded")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_numbers(item)
        return
    if isinstance(value, dict):
        for item in value.values():
            _validate_json_numbers(item)


def _load_json_bytes(payload: bytes, *, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise WorkpackError(f"non-finite JSON constant is forbidden: {value}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        document: dict[str, Any] = {}
        for key, value in pairs:
            if key in document:
                raise WorkpackError("duplicate JSON object keys are forbidden")
            document[key] = value
        return document

    try:
        text = payload.decode("utf-8")
        document = json.loads(
            text,
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WorkpackError(f"cannot read JSON input: {label}") from error
    if not isinstance(document, dict):
        raise WorkpackError("JSON root must be an object")
    _validate_json_numbers(document)
    return document


def _load_json(path: Path, *, maximum_bytes: int = MAX_JSON_BYTES) -> dict[str, Any]:
    payload = _read_regular_file(path, maximum_bytes=maximum_bytes, label=path.name)
    return _load_json_bytes(payload, label=path.name)


def _finite_number(
    value: Any,
    field: str,
    *,
    positive: bool = False,
    maximum_abs: float = MAX_ABS_JSON_NUMBER,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WorkpackError(f"{field} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        raise WorkpackError(f"{field} must be a bounded finite number") from error
    if (
        not math.isfinite(result)
        or abs(result) > maximum_abs
        or (positive and result <= 0.0)
    ):
        raise WorkpackError(
            f"{field} must be bounded and finite" + (" and positive" if positive else "")
        )
    return result


def _positive_integer(value: Any, field: str, *, maximum: int | None = None) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or (maximum is not None and value > maximum)
    ):
        raise WorkpackError(f"{field} must be a positive integer")
    return value


def _validate_sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise WorkpackError(f"{field} must be a lowercase SHA-256")
    return value


def validate_f18_report(
    report: dict[str, Any], expected_candidate_count: int, expected_component_count: int
) -> list[dict[str, Any]]:
    _positive_integer(
        expected_component_count,
        "expected component count",
        maximum=MAX_COMPONENTS,
    )
    _positive_integer(
        expected_candidate_count,
        "expected candidate count",
        maximum=expected_component_count,
    )
    if report.get("schema") != "porsche-917-boundary-human-review/f18-v1":
        raise WorkpackError("input report is not the F18 boundary inventory")
    if report.get("phase") != "F18":
        raise WorkpackError("input report phase must be F18")
    coordinate_policy = report.get("coordinate_policy")
    if not isinstance(coordinate_policy, dict):
        raise WorkpackError("F18 coordinate policy is missing")
    for field in (
        "metric_conversion_applied",
        "scale_inference_applied",
        "axis_semantics_inferred",
    ):
        if coordinate_policy.get(field) is not False:
            raise WorkpackError(f"F18 {field} must remain false")
    source_gates = report.get("release_gates")
    if source_gates != RELEASE_GATES:
        raise WorkpackError("F18 release gates must exactly match the closed F23 gate set")

    components = report.get("components")
    topology = report.get("topology")
    summary = report.get("summary")
    if not isinstance(components, list) or not components:
        raise WorkpackError("F18 components must be a non-empty list")
    if len(components) != expected_component_count:
        raise WorkpackError(
            "F18 component count mismatch: "
            f"expected {expected_component_count}, got {len(components)}"
        )
    if not isinstance(topology, dict) or not isinstance(summary, dict):
        raise WorkpackError("F18 topology and summary are required")
    if topology.get("boundary_components_truncated") is not False:
        raise WorkpackError("F18 component inventory must not be truncated")
    if topology.get("boundary_components") != len(components):
        raise WorkpackError("F18 component count does not match topology")
    if topology.get("reported_boundary_components") != len(components):
        raise WorkpackError("F18 reported component count is incomplete")

    component_ids: set[str] = set()
    component_ranks: set[int] = set()
    candidate_count = 0
    for component in components:
        if not isinstance(component, dict):
            raise WorkpackError("every F18 component must be an object")
        component_id = component.get("component_id")
        rank = _positive_integer(
            component.get("component_rank"),
            "component_rank",
            maximum=MAX_COMPONENTS,
        )
        if not isinstance(component_id, str) or COMPONENT_ID_PATTERN.fullmatch(component_id) is None:
            raise WorkpackError("component_id must match boundary_####")
        if component_id in component_ids or rank in component_ranks:
            raise WorkpackError("F18 component identifiers and ranks must be unique")
        component_ids.add(component_id)
        component_ranks.add(rank)
        review_class = component.get("review_class")
        if review_class not in ("candidate", "unclassified"):
            raise WorkpackError("F18 review class is outside its closed vocabulary")
        candidate_count += int(review_class == "candidate")
        if component.get("semantic_label") is not None:
            raise WorkpackError("F18 semantic labels must remain unset")
        if component.get("interface_confirmed") is not False:
            raise WorkpackError("F18 must not confirm an interface")
        if component.get("human_review_state") != "pending":
            raise WorkpackError("F18 input must remain pending human review")
        _positive_integer(
            component.get("boundary_vertex_count"),
            "boundary_vertex_count",
            maximum=MAX_PLY_VERTICES,
        )
        _positive_integer(
            component.get("boundary_edge_count"),
            "boundary_edge_count",
            maximum=MAX_PLY_VERTICES,
        )
        _finite_number(component.get("perimeter_obj_units"), "perimeter_obj_units", positive=True)
        extent = component.get("bbox_extent_obj_units")
        if not isinstance(extent, list) or len(extent) != 3:
            raise WorkpackError("bbox_extent_obj_units must contain three values")
        for value in extent:
            if _finite_number(
                value,
                "bbox extent",
                maximum_abs=MAX_ABS_COORDINATE,
            ) < 0.0:
                raise WorkpackError("bbox extents cannot be negative")
        area = component.get("projected_area_obj_units_squared")
        if area is not None and _finite_number(area, "projected area") < 0.0:
            raise WorkpackError("projected area cannot be negative")
        _finite_number(component.get("candidate_score"), "candidate_score")
    if candidate_count != expected_candidate_count:
        raise WorkpackError(
            f"F18 candidate count mismatch: expected {expected_candidate_count}, got {candidate_count}"
        )
    if summary.get("candidate_count") != candidate_count:
        raise WorkpackError("F18 summary candidate count is inconsistent")
    if summary.get("unclassified_count") != len(components) - candidate_count:
        raise WorkpackError("F18 summary unclassified count is inconsistent")
    if summary.get("confirmed_interface_count") != 0:
        raise WorkpackError("F18 summary must contain zero confirmed interfaces")
    if summary.get("human_review_pending_count") != len(components):
        raise WorkpackError("F18 pending review count is inconsistent")
    return components


def _descending_percentiles(
    components: list[dict[str, Any]], value: Callable[[dict[str, Any]], float]
) -> dict[int, float]:
    values = {component["component_rank"]: value(component) for component in components}
    distinct = sorted(set(values.values()), reverse=True)
    if len(distinct) == 1:
        score_by_value = {distinct[0]: 1.0}
    else:
        score_by_value = {
            item: 1.0 - index / (len(distinct) - 1)
            for index, item in enumerate(distinct)
        }
    return {rank: score_by_value[item] for rank, item in values.items()}


def _bbox_diagonal(component: dict[str, Any]) -> float:
    diagonal = math.hypot(
        *(float(value) for value in component["bbox_extent_obj_units"])
    )
    return _finite_number(diagonal, "bbox diagonal", maximum_abs=MAX_ABS_JSON_NUMBER)


def select_review_cohorts(
    components: list[dict[str, Any]], secondary_count: int
) -> list[dict[str, Any]]:
    primary = [item for item in components if item["review_class"] == "candidate"]
    unclassified = [item for item in components if item["review_class"] == "unclassified"]
    if not primary:
        raise WorkpackError("at least one F18 candidate is required")
    if secondary_count <= 0 or secondary_count > len(unclassified):
        raise WorkpackError("secondary count must fit inside the unclassified cohort")

    accessors: dict[str, Callable[[dict[str, Any]], float]] = {
        "projected_area": lambda item: float(item["projected_area_obj_units_squared"] or 0.0),
        "bbox_diagonal": _bbox_diagonal,
        "perimeter": lambda item: float(item["perimeter_obj_units"]),
        "boundary_vertex_count": lambda item: float(item["boundary_vertex_count"]),
    }
    percentiles = {
        name: _descending_percentiles(unclassified, accessor)
        for name, accessor in accessors.items()
    }
    secondary_scores: dict[int, float] = {}
    for item in unclassified:
        rank = item["component_rank"]
        secondary_scores[rank] = sum(
            SECONDARY_SCORE_WEIGHTS[name] * percentiles[name][rank]
            for name in SECONDARY_SCORE_WEIGHTS
        )
    primary.sort(key=lambda item: (-float(item["candidate_score"]), item["component_rank"]))
    unclassified.sort(
        key=lambda item: (
            -secondary_scores[item["component_rank"]],
            -float(item["projected_area_obj_units_squared"] or 0.0),
            -_bbox_diagonal(item),
            -float(item["perimeter_obj_units"]),
            item["component_rank"],
        )
    )

    selected: list[dict[str, Any]] = []
    for priority, item in enumerate(primary, start=1):
        selected.append(
            {
                "component": item,
                "selection_tier": "primary_circular_candidate",
                "selection_reason_code": "all_f18_geometric_candidates",
                "selection_priority_within_tier": priority,
                "selection_score": float(item["candidate_score"]),
            }
        )
    for priority, item in enumerate(unclassified[:secondary_count], start=1):
        selected.append(
            {
                "component": item,
                "selection_tier": "secondary_large_unclassified",
                "selection_reason_code": "top_composite_dimensionless_size_rank",
                "selection_priority_within_tier": priority,
                "selection_score": secondary_scores[item["component_rank"]],
            }
        )
    return selected


def read_selected_ply_points(
    payload: bytes,
    expected_sha256: str,
    report: dict[str, Any],
    components: list[dict[str, Any]],
    selected_ranks: set[int],
) -> dict[int, list[tuple[float, float, float]]]:
    if len(payload) > MAX_PLY_BYTES:
        raise WorkpackError(f"PLY exceeds the {MAX_PLY_BYTES}-byte limit")
    if _sha256_bytes(payload) != expected_sha256:
        raise WorkpackError("PLY SHA-256 mismatch")
    visualization = report.get("visualization")
    if not isinstance(visualization, dict):
        raise WorkpackError("F18 visualization contract is missing")
    if visualization.get("sha256") != expected_sha256:
        raise WorkpackError("F18 report does not bind the supplied PLY")
    if visualization.get("bytes") != len(payload):
        raise WorkpackError("F18 PLY byte count mismatch")

    expected_by_rank = {item["component_rank"]: item for item in components}
    points = {rank: [] for rank in selected_ranks}
    counts = {rank: 0 for rank in expected_by_rank}
    sample_steps = {
        rank: max(
            1,
            math.ceil(
                expected_by_rank[rank]["boundary_vertex_count"]
                / MAX_RENDER_POINTS_PER_COMPONENT
            ),
        )
        for rank in selected_ranks
    }
    with io.BytesIO(payload) as stream:
        header_lines: list[str] = []
        header_bytes = 0
        for _ in range(128):
            raw_line = stream.readline(MAX_PLY_HEADER_LINE_BYTES + 1)
            if not raw_line:
                raise WorkpackError("PLY header is incomplete")
            if len(raw_line) > MAX_PLY_HEADER_LINE_BYTES:
                raise WorkpackError("PLY header line exceeds the F23 limit")
            header_bytes += len(raw_line)
            if header_bytes > MAX_PLY_HEADER_BYTES:
                raise WorkpackError("PLY header exceeds the F23 byte limit")
            try:
                line = raw_line.decode("ascii").rstrip("\r\n")
            except UnicodeDecodeError as error:
                raise WorkpackError("PLY header must be ASCII") from error
            header_lines.append(line)
            if line == "end_header":
                break
        else:
            raise WorkpackError("PLY header exceeds the F18 contract")
        if header_lines[:2] != ["ply", "format binary_little_endian 1.0"]:
            raise WorkpackError("PLY must use the F18 binary little-endian format")
        element_lines = [line for line in header_lines if line.startswith("element ")]
        if len(element_lines) != 1 or not element_lines[0].startswith("element vertex "):
            raise WorkpackError("PLY must contain only the F18 vertex element")
        try:
            vertex_count = int(element_lines[0].split()[2])
        except (IndexError, ValueError) as error:
            raise WorkpackError("PLY vertex count is invalid") from error
        properties = tuple(line for line in header_lines if line.startswith("property "))
        if properties != PLY_PROPERTIES:
            raise WorkpackError("PLY properties differ from the F18 contract")
        expected_vertex_count = _positive_integer(
            report["topology"].get("boundary_vertices"),
            "F18 boundary_vertices",
            maximum=MAX_PLY_VERTICES,
        )
        if expected_vertex_count != sum(
            item["boundary_vertex_count"] for item in components
        ):
            raise WorkpackError("F18 boundary vertex total is inconsistent")
        if vertex_count != expected_vertex_count or visualization.get("point_count") != vertex_count:
            raise WorkpackError("PLY vertex count does not match the F18 report")

        for _ in range(vertex_count):
            record = stream.read(PLY_RECORD.size)
            if len(record) != PLY_RECORD.size:
                raise WorkpackError("PLY payload is truncated")
            x, y, z, _red, _green, _blue, _alpha, rank, candidate = PLY_RECORD.unpack(record)
            if not all(
                math.isfinite(value) and abs(value) <= MAX_ABS_COORDINATE
                for value in (x, y, z)
            ):
                raise WorkpackError("PLY contains non-finite or out-of-range coordinates")
            if rank not in expected_by_rank:
                raise WorkpackError("PLY component rank is absent from the F18 report")
            expected_candidate = int(expected_by_rank[rank]["review_class"] == "candidate")
            if candidate != expected_candidate:
                raise WorkpackError("PLY candidate flag disagrees with the F18 report")
            point_index = counts[rank]
            counts[rank] += 1
            if rank in points and point_index % sample_steps[rank] == 0:
                points[rank].append((x, y, z))
        if stream.read(1):
            raise WorkpackError("PLY contains trailing bytes outside the F18 vertex element")
    for rank, component in expected_by_rank.items():
        if counts[rank] != component["boundary_vertex_count"]:
            raise WorkpackError("PLY per-component point count disagrees with F18")
    if any(not values for values in points.values()):
        raise WorkpackError("every selected boundary must have PLY points")
    return points


def _indicator(component: dict[str, Any], selection: dict[str, Any]) -> dict[str, Any]:
    planarity = component.get("planarity")
    circularity = component.get("circularity")
    return {
        "boundary_vertex_count": component["boundary_vertex_count"],
        "boundary_edge_count": component["boundary_edge_count"],
        "closed_loop": component.get("closed_loop") is True,
        "endpoint_count": component.get("endpoint_count"),
        "branched_vertex_count": component.get("branched_vertex_count"),
        "perimeter_input_units": component["perimeter_obj_units"],
        "projected_area_input_units_squared": component.get("projected_area_obj_units_squared"),
        "bbox_diagonal_input_units": _bbox_diagonal(component),
        "candidate_score": component["candidate_score"],
        "planarity_ratio": planarity.get("planarity_ratio") if isinstance(planarity, dict) else None,
        "relative_circle_fit_p95": (
            circularity.get("relative_circle_fit_p95") if isinstance(circularity, dict) else None
        ),
        "angular_coverage": (
            circularity.get("angular_coverage") if isinstance(circularity, dict) else None
        ),
        "selection_score": selection["selection_score"],
    }


def build_workpack(
    report: dict[str, Any],
    report_sha256: str,
    ply_sha256: str,
    selected: list[dict[str, Any]],
    points: dict[int, list[tuple[float, float, float]]],
) -> dict[str, Any]:
    items = []
    for queue_index, selection in enumerate(selected, start=1):
        component = selection["component"]
        rank = component["component_rank"]
        items.append(
            {
                "queue_index": queue_index,
                "component_id": component["component_id"],
                "component_rank": rank,
                "source_review_class": component["review_class"],
                "selection_tier": selection["selection_tier"],
                "selection_reason_code": selection["selection_reason_code"],
                "selection_priority_within_tier": selection["selection_priority_within_tier"],
                "geometry_indicators": _indicator(component, selection),
                "rendered_point_count": len(points[rank]),
                "review": {
                    "state": "undetermined",
                    "reviewer": {
                        "name": None,
                        "organization": None,
                        "reviewed_at_utc": None,
                    },
                    "evidence": [],
                },
                "semantic_interface_confirmed": False,
                "release_authority": False,
            }
        )
    primary_count = sum(item["selection_tier"] == "primary_circular_candidate" for item in items)
    secondary_count = len(items) - primary_count
    return {
        "schema": SCHEMA,
        "phase": "F23",
        "status": "review_queue_generated_all_decisions_undetermined",
        "inputs": {
            "f18_report": {"name": "boundary-review-f18.json", "sha256": report_sha256},
            "f18_ply": {"name": "boundary-components-f18.ply", "sha256": ply_sha256},
            "raw_or_derived_coordinates_embedded_in_tracked_contract": False,
        },
        "selection_policy": {
            "primary": "all F18 components whose review_class is candidate",
            "secondary": "top unclassified components by a dimensionless composite size rank",
            "secondary_score_weights": SECONDARY_SCORE_WEIGHTS,
            "secondary_batch_size_equals_primary_batch_size": secondary_count == primary_count,
            "circularity_used_for_secondary_selection": False,
            "component_rank_is_only_a_final_tie_breaker": True,
            "semantic_inference_applied": False,
        },
        "review_contract": {
            "allowed_states": list(ALLOWED_REVIEW_STATES),
            "allowed_evidence_kinds": list(ALLOWED_EVIDENCE_KINDS),
            "decided_state_requires_reviewer_timestamp_and_evidence": True,
            "physical_boundary_means_interface_confirmed": False,
            "decisions_open_release_gates": False,
        },
        "summary": {
            "f18_component_count": len(report["components"]),
            "primary_circular_candidate_count": primary_count,
            "secondary_large_unclassified_count": secondary_count,
            "selected_for_current_workpack": len(items),
            "not_selected_but_still_pending_f18_review": len(report["components"]) - len(items),
            "all_f18_candidates_included": primary_count == report["summary"]["candidate_count"],
            "confirmed_interface_count": 0,
        },
        "items": items,
        "release_gates": RELEASE_GATES,
        "limitations": [
            "Selection priority is geometric and does not identify an engine part or interface.",
            "The secondary cohort reduces classifier tunnel vision but cannot eliminate false negatives.",
            "Views use unscaled scan coordinates with no physical axis semantics.",
            "Artifact and physical_boundary are human review states, not dimensional evidence.",
            "No F23 decision authorizes CAD, simulation, PhysicsNeMo, fabrication or engine start.",
            "The JSON, CSV and SVG are derived scan work products and must stay outside Git.",
        ],
    }


def _valid_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def validate_review_document(document: dict[str, Any]) -> None:
    if document.get("schema") != SCHEMA or document.get("phase") != "F23":
        raise WorkpackError("review document is not an F23 workpack")
    gates = document.get("release_gates")
    if gates != RELEASE_GATES or any(value is not False for value in gates.values()):
        raise WorkpackError("all F23 release gates must remain exactly false")
    inputs = document.get("inputs")
    if not isinstance(inputs, dict):
        raise WorkpackError("F23 input fingerprints are missing")
    for key in ("f18_report", "f18_ply"):
        item = inputs.get(key)
        if not isinstance(item, dict):
            raise WorkpackError(f"{key} fingerprint is missing")
        _validate_sha(item.get("sha256"), f"{key} sha256")
    if inputs.get("raw_or_derived_coordinates_embedded_in_tracked_contract") is not False:
        raise WorkpackError("tracked coordinate policy must remain false")
    selection_policy = document.get("selection_policy")
    review_contract = document.get("review_contract")
    if not isinstance(selection_policy, dict) or not isinstance(review_contract, dict):
        raise WorkpackError("F23 selection and review contracts are required")
    if selection_policy.get("semantic_inference_applied") is not False:
        raise WorkpackError("F23 cannot apply semantic inference")
    if selection_policy.get("circularity_used_for_secondary_selection") is not False:
        raise WorkpackError("F23 secondary selection must remain independent of circularity")
    if review_contract.get("physical_boundary_means_interface_confirmed") is not False:
        raise WorkpackError("physical_boundary cannot mean a confirmed interface")
    if review_contract.get("decisions_open_release_gates") is not False:
        raise WorkpackError("F23 decisions cannot open release gates")
    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise WorkpackError("F23 review items must be non-empty")
    seen_ids: set[str] = set()
    seen_ranks: set[int] = set()
    queue_indices: set[int] = set()
    tier_counts = {
        "primary_circular_candidate": 0,
        "secondary_large_unclassified": 0,
    }
    for item in items:
        if not isinstance(item, dict):
            raise WorkpackError("F23 review item must be an object")
        component_id = item.get("component_id")
        rank = _positive_integer(
            item.get("component_rank"),
            "F23 component_rank",
            maximum=MAX_COMPONENTS,
        )
        if not isinstance(component_id, str) or COMPONENT_ID_PATTERN.fullmatch(component_id) is None:
            raise WorkpackError("F23 component_id must match boundary_####")
        if component_id in seen_ids or rank in seen_ranks:
            raise WorkpackError("F23 review items must be unique")
        seen_ids.add(component_id)
        seen_ranks.add(rank)
        queue_index = _positive_integer(item.get("queue_index"), "F23 queue_index")
        if queue_index in queue_indices:
            raise WorkpackError("F23 queue indices must be unique")
        queue_indices.add(queue_index)
        tier = item.get("selection_tier")
        if tier not in tier_counts:
            raise WorkpackError("F23 selection tier is invalid")
        tier_counts[tier] += 1
        expected_source_class = (
            "candidate" if tier == "primary_circular_candidate" else "unclassified"
        )
        if item.get("source_review_class") != expected_source_class:
            raise WorkpackError("F23 selection tier disagrees with the F18 review class")
        if item.get("semantic_interface_confirmed") is not False:
            raise WorkpackError("F23 cannot confirm a semantic interface")
        if item.get("release_authority") is not False:
            raise WorkpackError("F23 review items have no release authority")
        review = item.get("review")
        if not isinstance(review, dict) or review.get("state") not in ALLOWED_REVIEW_STATES:
            raise WorkpackError("F23 review state is invalid")
        if set(review) != {"state", "reviewer", "evidence"}:
            raise WorkpackError("F23 review fields differ from the closed review schema")
        reviewer = review.get("reviewer")
        evidence = review.get("evidence")
        if not isinstance(reviewer, dict) or not isinstance(evidence, list):
            raise WorkpackError("F23 reviewer and evidence fields are required")
        if set(reviewer) != {"name", "organization", "reviewed_at_utc"}:
            raise WorkpackError("F23 reviewer fields differ from the closed reviewer schema")
        state = review["state"]
        if state == "undetermined":
            if any(reviewer.get(field) is not None for field in ("name", "organization", "reviewed_at_utc")):
                raise WorkpackError("undetermined reviews cannot carry a completed reviewer record")
            if evidence:
                raise WorkpackError("undetermined reviews cannot carry decision evidence")
            continue
        if not isinstance(reviewer.get("name"), str) or not reviewer["name"].strip():
            raise WorkpackError("a decided review requires the reviewer name")
        if reviewer.get("organization") is not None and not isinstance(reviewer["organization"], str):
            raise WorkpackError("reviewer organization must be text or null")
        if not _valid_utc_timestamp(reviewer.get("reviewed_at_utc")):
            raise WorkpackError("a decided review requires a UTC timestamp")
        if not evidence:
            raise WorkpackError("a decided review requires at least one evidence record")
        for record in evidence:
            if not isinstance(record, dict):
                raise WorkpackError("evidence records must be objects")
            if set(record) != {"kind", "reference", "sha256", "notes"}:
                raise WorkpackError("evidence fields differ from the closed evidence schema")
            if record.get("kind") not in ALLOWED_EVIDENCE_KINDS:
                raise WorkpackError("evidence kind is invalid")
            if not isinstance(record.get("reference"), str) or not record["reference"].strip():
                raise WorkpackError("evidence reference is required")
            evidence_sha = record.get("sha256")
            if evidence_sha is not None:
                _validate_sha(evidence_sha, "evidence sha256")
            if record.get("notes") is not None and not isinstance(record["notes"], str):
                raise WorkpackError("evidence notes must be text or null")
    if queue_indices != set(range(1, len(items) + 1)):
        raise WorkpackError("F23 queue indices must be contiguous from one")
    summary = document.get("summary")
    if not isinstance(summary, dict):
        raise WorkpackError("F23 summary is required")
    if summary.get("primary_circular_candidate_count") != tier_counts["primary_circular_candidate"]:
        raise WorkpackError("F23 primary summary count is inconsistent")
    if summary.get("secondary_large_unclassified_count") != tier_counts["secondary_large_unclassified"]:
        raise WorkpackError("F23 secondary summary count is inconsistent")
    if summary.get("selected_for_current_workpack") != len(items):
        raise WorkpackError("F23 selected summary count is inconsistent")
    if summary.get("confirmed_interface_count") != 0:
        raise WorkpackError("F23 summary cannot confirm an interface")
    if summary.get("all_f18_candidates_included") is not True:
        raise WorkpackError("F23 workpack must include every F18 candidate")


def validate_immutable_workpack(
    document: dict[str, Any], expected: dict[str, Any]
) -> None:
    def without_reviews(workpack: dict[str, Any]) -> dict[str, Any]:
        projection = {key: value for key, value in workpack.items() if key != "items"}
        items = workpack.get("items")
        if not isinstance(items, list):
            raise WorkpackError("F23 review items must be a list")
        projection["items"] = [
            {key: value for key, value in item.items() if key != "review"}
            if isinstance(item, dict)
            else item
            for item in items
        ]
        return projection

    if without_reviews(document) != without_reviews(expected):
        raise WorkpackError("F23 immutable content differs from the supplied F18 inputs")


def _sample_points(points: list[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    step = max(1, math.ceil(len(points) / MAX_RENDER_POINTS_PER_COMPONENT))
    return points[::step]


def _render_projection(
    points: list[tuple[float, float, float]],
    axes: tuple[int, int],
    left: float,
    top: float,
    width: float,
    height: float,
    color: str,
) -> str:
    projected = [(point[axes[0]], point[axes[1]]) for point in _sample_points(points)]
    min_x = min(point[0] for point in projected)
    max_x = max(point[0] for point in projected)
    min_y = min(point[1] for point in projected)
    max_y = max(point[1] for point in projected)
    span_x = max_x - min_x
    span_y = max_y - min_y
    scale = min((width - 20.0) / max(span_x, 1e-12), (height - 20.0) / max(span_y, 1e-12))
    centre_x = 0.5 * (min_x + max_x)
    centre_y = 0.5 * (min_y + max_y)
    output = [
        f'<rect x="{left:.2f}" y="{top:.2f}" width="{width:.2f}" height="{height:.2f}" rx="5" fill="#101820" stroke="#52606d"/>',
    ]
    for x_value, y_value in projected:
        x = left + width / 2.0 + (x_value - centre_x) * scale
        y = top + height / 2.0 - (y_value - centre_y) * scale
        output.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="1.15" fill="{color}" fill-opacity="0.78"/>'
        )
    return "".join(output)


def render_svg(workpack: dict[str, Any], points: dict[int, list[tuple[float, float, float]]]) -> str:
    width = 1500
    header_height = 90
    card_height = 236
    height = header_height + card_height * len(workpack["items"]) + 30
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#07111b"/>',
        '<style>text{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}.title{font-size:22px;font-weight:700;fill:#f4f7fa}.meta{font-size:13px;fill:#bdc7d1}.label{font-size:12px;fill:#e5ebf0}</style>',
        '<text class="title" x="24" y="34">F23 — atlas local de revue des frontières 917</text>',
        '<text class="meta" x="24" y="58">Projections normalisées par composante; unités et axes physiques non confirmés; aucune interface confirmée.</text>',
        '<text class="meta" x="24" y="78">Décisions autorisées: artifact | physical_boundary | undetermined — les sorties restent hors Git.</text>',
    ]
    view_specs = (((0, 1), "XY scan"), ((0, 2), "XZ scan"), ((1, 2), "YZ scan"))
    for index, item in enumerate(workpack["items"]):
        top = header_height + index * card_height
        tier = item["selection_tier"]
        color = "#34d399" if tier == "primary_circular_candidate" else "#f59e0b"
        component_id = html.escape(item["component_id"])
        title = (
            f'{item["queue_index"]:02d}. {component_id} — {html.escape(tier)} '
            f'— état: undetermined'
        )
        indicators = item["geometry_indicators"]
        subtitle = (
            f'points={item["rendered_point_count"]} closed={str(indicators["closed_loop"]).lower()} '
            f'candidate_score={indicators["candidate_score"]:.4f} selection_score={indicators["selection_score"]:.4f}'
        )
        parts.extend(
            [
                f'<rect x="16" y="{top + 4}" width="1468" height="226" rx="8" fill="#0b1724" stroke="#263849"/>',
                f'<text class="label" x="28" y="{top + 26}" fill="{color}">{title}</text>',
                f'<text class="meta" x="28" y="{top + 46}">{html.escape(subtitle)}</text>',
            ]
        )
        for view_index, (axes, label) in enumerate(view_specs):
            left = 28 + view_index * 482
            panel_top = top + 60
            parts.append(
                _render_projection(points[item["component_rank"]], axes, left, panel_top, 454, 142, color)
            )
            parts.append(
                f'<text class="label" x="{left + 8}" y="{panel_top + 17}">{label}</text>'
            )
        parts.append(
            f'<text class="meta" x="28" y="{top + 220}">[ ] artifact   [ ] physical_boundary   [x] undetermined   reviewer: __________________   evidence: __________________</text>'
        )
    parts.append("</svg>\n")
    return "".join(parts)


def render_csv(workpack: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    fieldnames = [
        "queue_index",
        "component_id",
        "component_rank",
        "selection_tier",
        "selection_reason_code",
        "source_review_class",
        "selection_score",
        "review_state",
        "reviewer_name",
        "reviewer_organization",
        "reviewed_at_utc",
        "evidence_kind",
        "evidence_reference",
        "evidence_sha256",
        "evidence_notes",
        "semantic_interface_confirmed",
        "release_authority",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for item in workpack["items"]:
        writer.writerow(
            {
                "queue_index": item["queue_index"],
                "component_id": item["component_id"],
                "component_rank": item["component_rank"],
                "selection_tier": item["selection_tier"],
                "selection_reason_code": item["selection_reason_code"],
                "source_review_class": item["source_review_class"],
                "selection_score": f'{item["geometry_indicators"]["selection_score"]:.12g}',
                "review_state": "undetermined",
                "reviewer_name": "",
                "reviewer_organization": "",
                "reviewed_at_utc": "",
                "evidence_kind": "",
                "evidence_reference": "",
                "evidence_sha256": "",
                "evidence_notes": "",
                "semantic_interface_confirmed": "false",
                "release_authority": "false",
            }
        )
    return output.getvalue()


def _build_expected_workpack(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[int, list[tuple[float, float, float]]]]:
    for field in ("report", "ply", "report_sha256", "ply_sha256"):
        if getattr(args, field) is None:
            raise WorkpackError(f"--{field.replace('_', '-')} is required")
    report_hash = _validate_sha(args.report_sha256, "report sha256")
    ply_hash = _validate_sha(args.ply_sha256, "PLY sha256")
    report_payload = _read_regular_file(
        args.report,
        maximum_bytes=MAX_JSON_BYTES,
        label="F18 report",
    )
    if _sha256_bytes(report_payload) != report_hash:
        raise WorkpackError("F18 report SHA-256 mismatch")
    report = _load_json_bytes(report_payload, label="F18 report")
    components = validate_f18_report(
        report,
        args.expected_candidate_count,
        args.expected_component_count,
    )
    if args.secondary_count != args.expected_candidate_count:
        raise WorkpackError("canonical F23 requires a secondary cohort equal to the primary cohort")
    selected = select_review_cohorts(components, args.secondary_count)
    selected_ranks = {item["component"]["component_rank"] for item in selected}
    ply_payload = _read_regular_file(
        args.ply,
        maximum_bytes=MAX_PLY_BYTES,
        label="F18 PLY",
    )
    points = read_selected_ply_points(
        ply_payload, ply_hash, report, components, selected_ranks
    )
    workpack = build_workpack(report, report_hash, ply_hash, selected, points)
    validate_review_document(workpack)
    return workpack, points


def _reject_symlink_components(path: Path, label: str) -> Path:
    absolute = Path(os.path.abspath(os.fspath(path)))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            continue
        except OSError as error:
            raise WorkpackError(f"cannot inspect {label}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise WorkpackError(f"{label} cannot contain symbolic links")
    return absolute


def _write_new_outputs(output: Path, payloads: dict[str, bytes]) -> None:
    output = _reject_symlink_components(output, "F23 output path")
    try:
        output.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as error:
        raise WorkpackError("cannot create F23 output directory") from error
    output = _reject_symlink_components(output, "F23 output path")
    if not output.is_dir():
        raise WorkpackError("F23 output path must be a directory")
    for name in payloads:
        if os.path.lexists(output / name):
            raise WorkpackError("F23 output already exists; overwriting is forbidden")

    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    try:
        directory_descriptor = os.open(output, directory_flags)
    except OSError as error:
        raise WorkpackError("cannot securely open F23 output directory") from error

    temporary_names: list[str] = []
    try:
        for index, (name, payload) in enumerate(payloads.items()):
            temporary_name = (
                f".{name}.tmp-{os.getpid()}-{index}-{_sha256_bytes(payload)[:12]}"
            )
            temporary_names.append(temporary_name)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(
                temporary_name,
                flags,
                0o600,
                dir_fd=directory_descriptor,
            )
            try:
                remaining = memoryview(payload)
                while remaining:
                    written = os.write(descriptor, remaining)
                    if written <= 0:
                        raise WorkpackError("cannot write complete F23 output")
                    remaining = remaining[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

        for temporary_name, name in zip(temporary_names, payloads, strict=True):
            os.link(
                temporary_name,
                name,
                src_dir_fd=directory_descriptor,
                dst_dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
        for temporary_name in temporary_names:
            os.unlink(temporary_name, dir_fd=directory_descriptor)
        temporary_names.clear()
    except (OSError, WorkpackError) as error:
        for temporary_name in temporary_names:
            try:
                os.unlink(temporary_name, dir_fd=directory_descriptor)
            except OSError:
                pass
        if isinstance(error, WorkpackError):
            raise
        raise WorkpackError("cannot atomically publish F23 outputs") from error
    finally:
        os.close(directory_descriptor)


def generate(args: argparse.Namespace) -> dict[str, Any]:
    if args.output is None:
        raise WorkpackError("--output is required for generation")
    if args.overwrite:
        raise WorkpackError("--overwrite is forbidden; preserve the existing workpack")
    workpack, points = _build_expected_workpack(args)

    payloads = {
        REPORT_NAME: (
            json.dumps(workpack, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        ).encode("utf-8"),
        CSV_NAME: render_csv(workpack).encode("utf-8"),
        SVG_NAME: render_svg(workpack, points).encode("utf-8"),
    }
    _write_new_outputs(args.output, payloads)
    return {
        "status": "generated_local_only",
        "primary_count": workpack["summary"]["primary_circular_candidate_count"],
        "secondary_count": workpack["summary"]["secondary_large_unclassified_count"],
        "selected_count": len(workpack["items"]),
        "confirmed_interface_count": 0,
        "release_gates_open": [],
        "outputs": list(payloads),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    parser.add_argument("--ply", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report-sha256")
    parser.add_argument("--ply-sha256")
    parser.add_argument("--expected-component-count", type=int, default=944)
    parser.add_argument("--expected-candidate-count", type=int, default=19)
    parser.add_argument("--secondary-count", type=int, default=19)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--validate-review-file", type=Path)
    args = parser.parse_args()
    try:
        if args.validate_review_file is not None:
            if args.output is not None or args.overwrite:
                raise WorkpackError("review validation cannot write or overwrite outputs")
            expected, _points = _build_expected_workpack(args)
            document = _load_json(args.validate_review_file)
            validate_review_document(document)
            validate_immutable_workpack(document, expected)
            result = {"status": "valid_review_workpack", "release_gates_open": []}
        else:
            result = generate(args)
    except WorkpackError as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
