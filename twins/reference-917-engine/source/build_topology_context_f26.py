#!/usr/bin/env python3
"""Build deterministic, local-only topological context for every F18 boundary.

F26 is a visualization aid for human review.  It recomputes the F18 boundary
identity from the source mesh, then extracts faces incident to each open edge
loop and exactly two edge-adjacent face rings.  It never classifies a physical
interface and never releases CAD, CAE, PhysicsNeMo or fabrication.
"""

from __future__ import annotations

import argparse
from array import array
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import sys
from typing import Any, BinaryIO, Iterable


sys.dont_write_bytecode = True


PHASE = "F26"
MANIFEST_NAME = "topology-context-manifest-f26.json"
INVENTORY_NAME = "topology-context-inventory-f26.csv"
MAX_BATCH_SIZE = 48
MAX_FIXTURE_COMPONENTS = 128
MAX_CONTEXT_FACES_PER_COMPONENT = 2_000_000
MAX_SVG_BYTES_PER_COMPONENT = 256 * 1024 * 1024
MAX_TOTAL_OUTPUT_BYTES = 8 * 1024 * 1024 * 1024
MAX_OBJ_LINE_BYTES = 4096
MAX_ABS_COORDINATE = 1_000_000_000_000.0
MAX_REPORT_BYTES = 32 * 1024 * 1024
MAX_CONTRACT_BYTES = 1024 * 1024
MAX_MESH_BYTES = 2 * 1024 * 1024 * 1024
MAX_VERTICES = 10_000_000
MAX_FACES = 20_000_000
MAX_POLYGON_VERTICES = 64
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
COMPONENT_ID_PATTERN = re.compile(r"boundary_[0-9]{4,6}")
CANONICAL_VIEWS = (
    "scan_xy_plus_z",
    "scan_xy_minus_z",
    "scan_xz_plus_y",
    "scan_yz_plus_x",
)
VIEW_SPECS = (
    ("scan_xy_plus_z", 0, 1, 2, 1.0, 1.0, 1.0),
    ("scan_xy_minus_z", 0, 1, 2, -1.0, 1.0, -1.0),
    ("scan_xz_plus_y", 0, 2, 1, -1.0, 1.0, 1.0),
    ("scan_yz_plus_x", 1, 2, 0, 1.0, 1.0, 1.0),
)
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


class ContextError(ValueError):
    """Raised when the F26 fail-closed contract is not satisfied."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContextError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Any:
    raise ContextError(f"non-finite JSON constant is forbidden: {value}")


def _load_json(payload: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContextError(f"{label} is not valid UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ContextError(f"{label} root must be an object")
    return value


def _open_regular_nofollow(path: Path, *, maximum_bytes: int, label: str) -> tuple[int, os.stat_result]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ContextError(f"cannot open {label} as a non-symlink regular file") from error
    information = os.fstat(descriptor)
    if not stat.S_ISREG(information.st_mode):
        os.close(descriptor)
        raise ContextError(f"{label} must be a regular file")
    if information.st_size <= 0 or information.st_size > maximum_bytes:
        os.close(descriptor)
        raise ContextError(f"{label} byte size is outside the bounded contract")
    return descriptor, information


def _read_small_bound_file(path: Path, expected_sha256: str, *, maximum_bytes: int, label: str) -> bytes:
    if SHA256_PATTERN.fullmatch(expected_sha256) is None:
        raise ContextError(f"{label} SHA-256 must be lowercase hexadecimal")
    descriptor, before = _open_regular_nofollow(path, maximum_bytes=maximum_bytes, label=label)
    try:
        payload = b""
        while len(payload) <= maximum_bytes:
            chunk = os.read(descriptor, min(1024 * 1024, maximum_bytes + 1 - len(payload)))
            if not chunk:
                break
            payload += chunk
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if len(payload) > maximum_bytes:
        raise ContextError(f"{label} exceeds its byte limit")
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise ContextError(f"{label} changed while it was read")
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected_sha256:
        raise ContextError(f"{label} SHA-256 mismatch")
    return payload


def _hash_open_file(descriptor: int) -> str:
    digest = hashlib.sha256()
    os.lseek(descriptor, 0, os.SEEK_SET)
    while True:
        chunk = os.read(descriptor, 1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
    os.lseek(descriptor, 0, os.SEEK_SET)
    return digest.hexdigest()


def _parse_obj_index(token: bytes, vertex_count: int) -> int:
    head = token.split(b"/", 1)[0]
    if not head:
        raise ContextError("OBJ face has an empty vertex index")
    try:
        value = int(head)
    except ValueError as error:
        raise ContextError("OBJ face has a non-integer vertex index") from error
    if value == 0:
        raise ContextError("OBJ indices are one-based and cannot be zero")
    resolved = value - 1 if value > 0 else vertex_count + value
    if resolved < 0 or resolved >= vertex_count:
        raise ContextError("OBJ face references a vertex outside the parsed prefix")
    return resolved


def _parse_obj_binary(binary: BinaryIO, source_size: int, np: Any) -> tuple[Any, Any, dict[str, int]]:
    vertices_buffer = array("d")
    faces_buffer = array("Q")
    polygon_count = 0
    ignored_record_count = 0
    for raw_line in binary:
        if len(raw_line) > MAX_OBJ_LINE_BYTES:
            raise ContextError("OBJ line exceeds the bounded byte contract")
        line = raw_line.lstrip()
        if not line or line.startswith(b"#"):
            continue
        if line.startswith(b"v ") or line.startswith(b"v\t"):
            fields = line.split()
            if len(fields) not in (4, 5):
                raise ContextError("OBJ vertex record must contain x y z and optional w")
            try:
                coordinates = [float(value) for value in fields[1:4]]
            except ValueError as error:
                raise ContextError("OBJ vertex coordinate is not numeric") from error
            if not all(math.isfinite(value) and abs(value) <= MAX_ABS_COORDINATE for value in coordinates):
                raise ContextError("OBJ vertex coordinates must be finite and bounded")
            vertices_buffer.extend(coordinates)
            if len(vertices_buffer) // 3 > MAX_VERTICES:
                raise ContextError("OBJ vertex count exceeds the bounded contract")
            continue
        if line.startswith(b"f ") or line.startswith(b"f\t"):
            fields = line.split()[1:]
            if len(fields) < 3 or len(fields) > MAX_POLYGON_VERTICES:
                raise ContextError("OBJ face polygon size is outside the bounded contract")
            vertex_count = len(vertices_buffer) // 3
            indices = [_parse_obj_index(token, vertex_count) for token in fields]
            if len(set(indices)) != len(indices):
                raise ContextError("OBJ face repeats a vertex index")
            for offset in range(1, len(indices) - 1):
                faces_buffer.extend((indices[0], indices[offset], indices[offset + 1]))
                if len(faces_buffer) // 3 > MAX_FACES:
                    raise ContextError("triangulated OBJ face count exceeds the bounded contract")
            polygon_count += 1
            continue
        ignored_record_count += 1
    vertex_count = len(vertices_buffer) // 3
    face_count = len(faces_buffer) // 3
    if not vertex_count or not face_count:
        raise ContextError("OBJ must contain vertices and polygon faces")
    vertices = np.frombuffer(vertices_buffer, dtype=np.float64).reshape((-1, 3))
    faces_unsigned = np.frombuffer(faces_buffer, dtype=np.uint64).reshape((-1, 3))
    if int(faces_unsigned.max()) > np.iinfo(np.int64).max:
        raise ContextError("OBJ index exceeds the signed topology runtime")
    faces = faces_unsigned.astype(np.int64, copy=False)
    return vertices, faces, {
        "source_bytes": source_size,
        "vertex_count": vertex_count,
        "source_polygon_count": polygon_count,
        "triangulated_face_count": face_count,
        "ignored_record_count": ignored_record_count,
    }


def _load_obj_from_descriptor(descriptor: int, source_size: int, np: Any) -> tuple[Any, Any, dict[str, int]]:
    os.lseek(descriptor, 0, os.SEEK_SET)
    with os.fdopen(os.dup(descriptor), "rb", closefd=True) as binary:
        return _parse_obj_binary(binary, source_size, np)


def _load_mesh(path: Path, expected_sha256: str, np: Any) -> tuple[Any, Any, dict[str, int]]:
    if path.suffix.lower() != ".obj":
        raise ContextError("F26 accepts only an external OBJ mesh")
    if SHA256_PATTERN.fullmatch(expected_sha256) is None:
        raise ContextError("mesh SHA-256 must be lowercase hexadecimal")
    descriptor, before = _open_regular_nofollow(path, maximum_bytes=MAX_MESH_BYTES, label="mesh")
    try:
        actual_sha256 = _hash_open_file(descriptor)
        if actual_sha256 != expected_sha256:
            raise ContextError("mesh SHA-256 mismatch")
        vertices, faces, parse = _load_obj_from_descriptor(descriptor, before.st_size, np)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise ContextError("mesh changed while it was parsed")
    return vertices, faces, parse


def _load_f18_module() -> Any:
    path = Path(__file__).with_name("review_boundary_components_f18.py")
    if not path.is_file():
        raise ContextError("the F18 topology implementation is missing beside F26")
    specification = importlib.util.spec_from_file_location("review_boundary_components_f18", path)
    if specification is None or specification.loader is None:
        raise ContextError("cannot load the F18 topology implementation")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _validate_contract(contract: dict[str, Any], *, expected_components: int, fixture_mode: bool) -> None:
    if contract.get("phase") != PHASE or contract.get("schema_version") != "1.0.0":
        raise ContextError("contract is not the F26 v1 contract")
    topology = contract.get("topology_context")
    visualization = contract.get("visualization")
    review = contract.get("review_policy")
    canonical = contract.get("canonical_input_expectations")
    fixture = contract.get("fixture_policy")
    parser_limits = contract.get("mesh_parser_limits")
    local_outputs = contract.get("local_outputs")
    if not isinstance(canonical, dict) or canonical.get("f18_boundary_component_count") != 944:
        raise ContextError("contract canonical F18 component count must remain exactly 944")
    if not isinstance(fixture, dict) or fixture != {
        "explicit_cli_flag_required": True,
        "maximum_boundary_component_count": MAX_FIXTURE_COMPONENTS,
        "synthetic_source_mode_prefix": "synthetic_",
        "canonical_count_override_allowed": False,
    }:
        raise ContextError("contract fixture policy differs from the closed F26 policy")
    if fixture_mode:
        if expected_components <= 0 or expected_components > MAX_FIXTURE_COMPONENTS:
            raise ContextError("fixture component count is outside its explicit bound")
    elif expected_components != canonical["f18_boundary_component_count"]:
        raise ContextError("canonical F26 execution requires exactly 944 F18 components")
    if parser_limits != {
        "maximum_obj_line_bytes": MAX_OBJ_LINE_BYTES,
        "maximum_absolute_coordinate": MAX_ABS_COORDINATE,
        "maximum_vertices": MAX_VERTICES,
        "maximum_triangles": MAX_FACES,
        "maximum_polygon_vertices": MAX_POLYGON_VERTICES,
    }:
        raise ContextError("contract mesh parser limits differ from the implementation")
    if not isinstance(local_outputs, dict) or local_outputs.get("maximum_total_output_bytes") != MAX_TOTAL_OUTPUT_BYTES:
        raise ContextError("contract total output bound differs from the implementation")
    if local_outputs.get("publication") != (
        "private_parent_0700_owned_by_runtime_uid_exclusive_new_directory_with_manifest_linked_last"
    ):
        raise ContextError("contract publication policy differs from the implementation")
    if not isinstance(topology, dict) or topology.get("topological_ring_count") != 2:
        raise ContextError("contract must require exactly two topological rings")
    if topology.get("rings_must_be_disjoint") is not True or topology.get("non_manifold_edges_accepted") is not False:
        raise ContextError("contract topology must remain fail closed")
    if topology.get("maximum_context_faces_per_component") != MAX_CONTEXT_FACES_PER_COMPONENT:
        raise ContextError("contract context-face bound differs from the implementation")
    if not isinstance(visualization, dict) or tuple(visualization.get("canonical_orthographic_views", [])) != CANONICAL_VIEWS:
        raise ContextError("contract canonical views differ from the F26 implementation")
    if visualization.get("maximum_components_per_batch") != MAX_BATCH_SIZE:
        raise ContextError("contract batch limit differs from the F26 implementation")
    if visualization.get("maximum_svg_bytes_per_component") != MAX_SVG_BYTES_PER_COMPONENT:
        raise ContextError("contract SVG byte bound differs from the implementation")
    if visualization.get("global_locator_required_in_every_view") is not True:
        raise ContextError("contract must require a global locator in every view")
    if not isinstance(review, dict) or any(
        review.get(key) is not expected
        for key, expected in (
            ("automatic_semantic_classification", False),
            ("automatic_interface_confirmation", False),
            ("release_authority", False),
        )
    ):
        raise ContextError("contract review policy opened an automatic decision")
    if contract.get("release_gates") != RELEASE_GATES:
        raise ContextError("contract release gates differ from the closed F26 gate set")


def _validate_f18_report(
    report: dict[str, Any],
    mesh_sha256: str,
    expected_components: int,
    *,
    fixture_mode: bool,
) -> list[dict[str, Any]]:
    if report.get("schema") != "porsche-917-boundary-human-review/f18-v1" or report.get("phase") != "F18":
        raise ContextError("input report is not the F18 v1 inventory")
    if report.get("status") != "complete_geometric_inventory_pending_human_review":
        raise ContextError("F18 report is not a complete pending-review inventory")
    source = report.get("source")
    if not isinstance(source, dict) or source.get("actual_sha256") != mesh_sha256:
        raise ContextError("F18 report does not bind the supplied mesh SHA-256")
    if source.get("expected_sha256") != mesh_sha256:
        raise ContextError("F18 expected SHA-256 does not bind the supplied mesh")
    if source.get("provenance_hash_matched") is not True:
        raise ContextError("F18 provenance hash must be explicitly matched")
    if source.get("raw_geometry_embedded_in_report") is not False:
        raise ContextError("F18 report must explicitly exclude embedded raw geometry")
    source_mode = source.get("mode")
    if fixture_mode:
        if not isinstance(source_mode, str) or not source_mode.startswith("synthetic_"):
            raise ContextError("fixture mode requires an explicitly synthetic F18 source mode")
    elif source_mode != "canonical_external_scan":
        raise ContextError("canonical mode requires the F18 canonical_external_scan source mode")
    coordinate_policy = report.get("coordinate_policy")
    if not isinstance(coordinate_policy, dict) or any(
        coordinate_policy.get(key) is not False
        for key in ("metric_conversion_applied", "scale_inference_applied", "axis_semantics_inferred")
    ):
        raise ContextError("F18 coordinate policy must remain unscaled and semantically unoriented")
    topology = report.get("topology")
    if not isinstance(topology, dict):
        raise ContextError("F18 topology is missing")
    for key in ("boundary_components", "reported_boundary_components"):
        if topology.get(key) != expected_components:
            raise ContextError(f"F18 {key} differs from the expected component count")
    if topology.get("boundary_components_truncated") is not False:
        raise ContextError("F18 component inventory is truncated")
    summary = report.get("summary")
    if not isinstance(summary, dict) or summary.get("confirmed_interface_count") != 0:
        raise ContextError("F18 report must contain zero confirmed interfaces")
    if summary.get("human_review_pending_count") != expected_components:
        raise ContextError("every F18 component must remain pending human review")
    if report.get("release_gates") != RELEASE_GATES:
        raise ContextError("F18 release gates differ from the closed F26 gate set")
    components = report.get("components")
    if not isinstance(components, list) or len(components) != expected_components:
        raise ContextError("F18 component list length differs from the expected count")
    for rank, item in enumerate(components, start=1):
        if not isinstance(item, dict):
            raise ContextError("every F18 component must be an object")
        expected_id = f"boundary_{rank:04d}"
        if item.get("component_id") != expected_id or item.get("component_rank") != rank:
            raise ContextError("F18 component identifiers are not the stable contiguous order")
        if COMPONENT_ID_PATTERN.fullmatch(expected_id) is None:
            raise ContextError("F18 component identifier is outside the closed vocabulary")
        if item.get("review_class") not in ("candidate", "unclassified"):
            raise ContextError("F18 geometric review class is outside its closed vocabulary")
        if item.get("semantic_label") is not None or item.get("interface_confirmed") is not False:
            raise ContextError("F18 component contains a semantic decision")
        if item.get("human_review_state") != "pending":
            raise ContextError("F18 component is not pending review")
    return components


def _compare_recomputed_f18(recomputed: list[dict[str, Any]], reported: list[dict[str, Any]]) -> None:
    if len(recomputed) != len(reported):
        raise ContextError("recomputed boundary component count differs from F18")
    exact_fields = (
        "component_id",
        "component_rank",
        "boundary_edge_count",
        "boundary_vertex_count",
        "minimum_source_vertex_index_1_based",
        "endpoint_count",
        "branched_vertex_count",
        "closed_loop",
        "review_class",
    )
    for calculated, observed in zip(recomputed, reported):
        for field in exact_fields:
            if calculated.get(field) != observed.get(field):
                raise ContextError(
                    f"recomputed F18 field mismatch for {observed.get('component_id')}: {field}"
                )


def _build_face_adjacency(faces: Any, np: Any) -> tuple[Any, Any, Any]:
    """Return sorted incidence-one edges, their owner faces and face neighbours."""

    face_count = len(faces)
    occurrence_count = face_count * 3
    keys = np.empty(occurrence_count, dtype=np.uint64)
    owners = np.tile(np.arange(face_count, dtype=np.int64), 3)
    slots = np.repeat(np.arange(3, dtype=np.int8), face_count)
    cursor = 0
    for left_column, right_column in ((0, 1), (1, 2), (2, 0)):
        left = faces[:, left_column].astype(np.uint64, copy=False)
        right = faces[:, right_column].astype(np.uint64, copy=False)
        low = np.minimum(left, right)
        high = np.maximum(left, right)
        batch = (low << np.uint64(32)) | high
        keys[cursor : cursor + face_count] = batch
        cursor += face_count
    valid = (keys >> np.uint64(32)) != (keys & np.uint64(0xFFFFFFFF))
    keys, owners, slots = keys[valid], owners[valid], slots[valid]
    order = np.argsort(keys, kind="stable")
    keys, owners, slots = keys[order], owners[order], slots[order]
    starts = np.flatnonzero(np.r_[True, keys[1:] != keys[:-1]])
    ends = np.r_[starts[1:], len(keys)]
    incidence = ends - starts
    if np.any(incidence > 2):
        raise ContextError("non-manifold mesh edges are not accepted by F26")
    neighbours = np.full((face_count, 3), -1, dtype=np.int64)
    manifold_starts = starts[incidence == 2]
    left_owner = owners[manifold_starts]
    left_slot = slots[manifold_starts]
    right_owner = owners[manifold_starts + 1]
    right_slot = slots[manifold_starts + 1]
    neighbours[left_owner, left_slot] = right_owner
    neighbours[right_owner, right_slot] = left_owner
    boundary_starts = starts[incidence == 1]
    boundary_keys = keys[boundary_starts]
    boundary_edges = np.column_stack(
        (
            boundary_keys >> np.uint64(32),
            boundary_keys & np.uint64(0xFFFFFFFF),
        )
    ).astype(np.int64, copy=False)
    boundary_owners = owners[boundary_starts]
    return boundary_edges, boundary_owners, neighbours


def _unique_nonnegative(values: Any, np: Any) -> Any:
    values = values.reshape(-1)
    return np.unique(values[values >= 0])


def _two_face_rings(incident_faces: Any, neighbours: Any, np: Any) -> tuple[Any, Any]:
    incident = np.unique(incident_faces)
    ring_1 = _unique_nonnegative(neighbours[incident], np)
    ring_1 = np.setdiff1d(ring_1, incident, assume_unique=True)
    ring_2 = _unique_nonnegative(neighbours[ring_1], np) if len(ring_1) else np.empty(0, dtype=np.int64)
    ring_2 = np.setdiff1d(ring_2, np.union1d(incident, ring_1), assume_unique=True)
    if np.intersect1d(incident, ring_1).size or np.intersect1d(incident, ring_2).size or np.intersect1d(ring_1, ring_2).size:
        raise ContextError("topological face layers are not disjoint")
    return ring_1, ring_2


def _require_bounded_context_face_count(count: int) -> None:
    if count <= 0 or count > MAX_CONTEXT_FACES_PER_COMPONENT:
        raise ContextError("component context face count is outside the bounded contract")


def _estimate_svg_bytes(context_face_count: int, boundary_edge_count: int) -> int:
    _require_bounded_context_face_count(context_face_count)
    if boundary_edge_count <= 0:
        raise ContextError("component boundary edge count must be positive")
    # Coordinates are bounded to 1e12, so 512 bytes per polygon and 320 bytes
    # per highlighted edge are conservative before constructing the SVG text.
    return 16_384 + 4 * (
        context_face_count * 512 + boundary_edge_count * 320 + 8_192
    )


def _reserve_output_bytes(current: int, addition: int, *, label: str) -> int:
    if addition < 0 or current < 0 or current + addition > MAX_TOTAL_OUTPUT_BYTES:
        raise ContextError(f"total output byte bound exceeded before writing {label}")
    return current + addition


def _component_topology_layers(
    rank: int,
    boundary_edges: Any,
    boundary_owners: Any,
    edge_ranks: Any,
    neighbours: Any,
    np: Any,
) -> tuple[Any, Any, Any, Any]:
    selection = edge_ranks == rank
    component_edges = boundary_edges[selection]
    incident = np.unique(boundary_owners[selection])
    if not len(component_edges) or not len(incident):
        raise ContextError(f"boundary rank {rank} has no recomputed incident faces")
    ring_1, ring_2 = _two_face_rings(incident, neighbours, np)
    _require_bounded_context_face_count(int(len(incident) + len(ring_1) + len(ring_2)))
    return component_edges, incident, ring_1, ring_2


def _array_sha256(values: Iterable[Any], np: Any) -> str:
    normalized = np.asarray(values, dtype="<u8")
    return hashlib.sha256(normalized.tobytes(order="C")).hexdigest()


def _fmt(value: float) -> str:
    if not math.isfinite(value):
        raise ContextError("SVG projection produced a non-finite coordinate")
    rounded = 0.0 if abs(value) < 0.0000005 else value
    return f"{rounded:.6f}"


def _projection_transform(points: Any, u_axis: int, v_axis: int, u_sign: float, v_sign: float, panel_x: float, panel_y: float, np: Any) -> tuple[Any, dict[str, float]]:
    width, height, margin = 760.0, 390.0, 34.0
    projected = np.column_stack((points[:, u_axis] * u_sign, points[:, v_axis] * v_sign))
    minimum = projected.min(axis=0)
    maximum = projected.max(axis=0)
    extent = maximum - minimum
    scale = min((width - 2 * margin) / max(float(extent[0]), 1e-12), (height - 2 * margin) / max(float(extent[1]), 1e-12))
    if not math.isfinite(scale) or scale <= 0.0:
        scale = 1.0
    centre = 0.5 * (minimum + maximum)
    output = np.empty_like(projected)
    output[:, 0] = panel_x + width / 2.0 + (projected[:, 0] - centre[0]) * scale
    output[:, 1] = panel_y + height / 2.0 - (projected[:, 1] - centre[1]) * scale
    return output, {"panel_width": width, "panel_height": height, "scale": scale}


def _locator_svg(mesh_bounds: Any, context_points: Any, view: tuple[Any, ...], panel_x: float, panel_y: float, np: Any) -> list[str]:
    _, u_axis, v_axis, _, u_sign, v_sign, _ = view
    locator_x, locator_y, width, height = panel_x + 620.0, panel_y + 28.0, 112.0, 76.0
    global_min = np.asarray([mesh_bounds[0][u_axis] * u_sign, mesh_bounds[0][v_axis] * v_sign])
    global_max = np.asarray([mesh_bounds[1][u_axis] * u_sign, mesh_bounds[1][v_axis] * v_sign])
    low = np.minimum(global_min, global_max)
    high = np.maximum(global_min, global_max)
    extent = np.maximum(high - low, 1e-12)
    local = np.column_stack((context_points[:, u_axis] * u_sign, context_points[:, v_axis] * v_sign))
    local_low = local.min(axis=0)
    local_high = local.max(axis=0)

    def map_point(point: Any) -> tuple[float, float]:
        x = locator_x + (float(point[0] - low[0]) / float(extent[0])) * width
        y = locator_y + height - (float(point[1] - low[1]) / float(extent[1])) * height
        return x, y

    x0, y1 = map_point(local_low)
    x1, y0 = map_point(local_high)
    rectangle_x = max(locator_x, min(min(x0, x1), locator_x + width - 1.5))
    rectangle_y = max(locator_y, min(min(y0, y1), locator_y + height - 1.5))
    rectangle_w = min(max(abs(x1 - x0), 1.5), locator_x + width - rectangle_x)
    rectangle_h = min(max(abs(y1 - y0), 1.5), locator_y + height - rectangle_y)
    return [
        f'<g class="global-locator" data-coordinate-policy="scan-axes-unconfirmed">',
        f'<rect x="{_fmt(locator_x)}" y="{_fmt(locator_y)}" width="{_fmt(width)}" height="{_fmt(height)}" fill="#0f172a" stroke="#94a3b8" stroke-width="1"/>',
        f'<rect x="{_fmt(rectangle_x)}" y="{_fmt(rectangle_y)}" width="{_fmt(rectangle_w)}" height="{_fmt(rectangle_h)}" fill="#22d3ee" fill-opacity="0.35" stroke="#22d3ee" stroke-width="1.2"/>',
        f'<text x="{_fmt(locator_x)}" y="{_fmt(locator_y - 6)}" class="locator-label">locator global</text>',
        "</g>",
    ]


def _render_component_svg(
    component_id: str,
    vertices: Any,
    faces: Any,
    boundary_edges: Any,
    incident: Any,
    ring_1: Any,
    ring_2: Any,
    mesh_bounds: Any,
    np: Any,
) -> str:
    context_faces = np.concatenate((incident, ring_1, ring_2)).astype(np.int64, copy=False)
    if not len(context_faces):
        raise ContextError("a boundary component has no incident faces")
    layers = np.concatenate(
        (
            np.zeros(len(incident), dtype=np.int8),
            np.ones(len(ring_1), dtype=np.int8),
            np.full(len(ring_2), 2, dtype=np.int8),
        )
    )
    context_vertex_ids = np.unique(faces[context_faces].reshape(-1))
    context_points = vertices[context_vertex_ids]
    vertex_position = {int(source): index for index, source in enumerate(context_vertex_ids)}
    local_faces = np.asarray(
        [[vertex_position[int(value)] for value in faces[int(face)]] for face in context_faces],
        dtype=np.int64,
    )
    local_boundary = np.asarray(
        [[vertex_position[int(value)] for value in edge] for edge in boundary_edges],
        dtype=np.int64,
    )
    face_colours = ("#e85d4a", "#f0a33a", "#64748b")
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">',
        '<metadata>F26 local derived scan context; no semantic classification; do not track in Git</metadata>',
        "<style>",
        ".title{font:700 22px sans-serif;fill:#e2e8f0}.view-label{font:600 14px monospace;fill:#e2e8f0}.locator-label{font:11px monospace;fill:#94a3b8}.legend{font:12px sans-serif;fill:#cbd5e1}",
        "</style>",
        '<rect width="1600" height="900" fill="#020617"/>',
        f'<text x="28" y="30" class="title">{component_id} — contexte F26, axes scan non qualifiés</text>',
    ]
    panel_origins = ((20.0, 52.0), (820.0, 52.0), (20.0, 462.0), (820.0, 462.0))
    for view, (panel_x, panel_y) in zip(VIEW_SPECS, panel_origins):
        name, _, _, depth_axis, _, _, depth_sign = view
        projected, dimensions = _projection_transform(
            context_points,
            view[1],
            view[2],
            view[4],
            view[5],
            panel_x,
            panel_y,
            np,
        )
        depths = vertices[faces[context_faces]].mean(axis=1)[:, depth_axis] * depth_sign
        draw_order = np.lexsort((context_faces, depths))
        lines.extend(
            (
                f'<g class="orthographic-view" data-view="{name}" data-projection="orthographic">',
                f'<rect x="{_fmt(panel_x)}" y="{_fmt(panel_y)}" width="{_fmt(dimensions["panel_width"])}" height="{_fmt(dimensions["panel_height"])}" fill="#0b1120" stroke="#334155"/>',
                f'<text x="{_fmt(panel_x + 14)}" y="{_fmt(panel_y + 22)}" class="view-label">{name}</text>',
            )
        )
        for index in draw_order:
            triangle = projected[local_faces[int(index)]]
            points = " ".join(f"{_fmt(float(point[0]))},{_fmt(float(point[1]))}" for point in triangle)
            colour = face_colours[int(layers[int(index)])]
            lines.append(
                f'<polygon points="{points}" fill="{colour}" fill-opacity="0.52" stroke="#cbd5e1" stroke-opacity="0.18" stroke-width="0.45"/>'
            )
        for edge in local_boundary:
            left, right = projected[edge]
            lines.append(
                f'<line x1="{_fmt(float(left[0]))}" y1="{_fmt(float(left[1]))}" x2="{_fmt(float(right[0]))}" y2="{_fmt(float(right[1]))}" stroke="#22d3ee" stroke-width="2.2"/>'
            )
        lines.extend(_locator_svg(mesh_bounds, context_points, view, panel_x, panel_y, np))
        lines.append("</g>")
    lines.extend(
        (
            '<rect x="30" y="866" width="14" height="14" fill="#e85d4a"/><text x="50" y="878" class="legend">faces incidentes</text>',
            '<rect x="190" y="866" width="14" height="14" fill="#f0a33a"/><text x="210" y="878" class="legend">anneau topologique 1</text>',
            '<rect x="390" y="866" width="14" height="14" fill="#64748b"/><text x="410" y="878" class="legend">anneau topologique 2</text>',
            '<line x1="600" y1="873" x2="630" y2="873" stroke="#22d3ee" stroke-width="2.2"/><text x="640" y="878" class="legend">frontière F18</text>',
            '<text x="930" y="878" class="legend">Aucune interface confirmée — revue humaine requise</text>',
            "</svg>",
        )
    )
    return "\n".join(lines) + "\n"


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise ContextError(f"refusing to overwrite output payload: {path.name}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o644)
    try:
        view = memoryview(payload)
        written = 0
        while written < len(view):
            count = os.write(descriptor, view[written:])
            if count <= 0:
                raise ContextError(f"short write for output payload: {path.name}")
            written += count
    finally:
        os.close(descriptor)


def _file_evidence(path: Path, root: Path, media_type: str) -> dict[str, Any]:
    information = path.stat(follow_symlinks=False)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": digest.hexdigest(),
        "bytes": information.st_size,
        "media_type": media_type,
        "contains_derived_coordinates": media_type == "image/svg+xml",
        "committed": False,
    }


def _open_private_output_parent(output: Path) -> tuple[int, tuple[int, int]]:
    if output.name in ("", ".", ".."):
        raise ContextError("output must name one direct child of its parent")
    parent = output.parent
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(parent, flags)
    except OSError as error:
        raise ContextError("output parent must be an existing non-symlink directory") from error
    information = os.fstat(descriptor)
    permissions = stat.S_IMODE(information.st_mode)
    if not stat.S_ISDIR(information.st_mode):
        os.close(descriptor)
        raise ContextError("output parent must be a directory")
    if information.st_uid != os.geteuid() or permissions != 0o700:
        os.close(descriptor)
        raise ContextError("output parent must be mode 0700 and owned by the runtime uid")
    try:
        os.stat(output.name, dir_fd=descriptor, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        os.close(descriptor)
        raise ContextError("output already exists; F26 never overwrites")
    return descriptor, (information.st_dev, information.st_ino)


def _require_parent_identity(parent_descriptor: int, expected: tuple[int, int]) -> None:
    information = os.fstat(parent_descriptor)
    if (information.st_dev, information.st_ino) != expected:
        raise ContextError("private output parent identity changed")
    if information.st_uid != os.geteuid() or stat.S_IMODE(information.st_mode) != 0o700:
        raise ContextError("private output parent ownership or mode changed")


def _directory_identity(path: Path) -> tuple[int, int]:
    information = path.stat(follow_symlinks=False)
    if not stat.S_ISDIR(information.st_mode):
        raise ContextError("guarded cleanup target is not a directory")
    return information.st_dev, information.st_ino


def _create_private_temporary_sibling(
    output: Path,
    *,
    parent_descriptor: int,
    parent_identity: tuple[int, int],
) -> tuple[Path, tuple[int, int]]:
    _require_parent_identity(parent_descriptor, parent_identity)
    for _ in range(32):
        name = f".{output.name}.tmp-{secrets.token_hex(12)}"
        try:
            os.mkdir(name, 0o700, dir_fd=parent_descriptor)
        except FileExistsError:
            continue
        information = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        path = output.parent / name
        path_information = path.stat(follow_symlinks=False)
        identity = (information.st_dev, information.st_ino)
        if (path_information.st_dev, path_information.st_ino) != identity:
            raise ContextError("private parent path changed while creating temporary output")
        return path, identity
    raise ContextError("could not allocate a unique private temporary output")


def _cleanup_guarded_directory(
    path: Path,
    *,
    expected_identity: tuple[int, int],
    parent_descriptor: int,
    parent_identity: tuple[int, int],
) -> None:
    _require_parent_identity(parent_descriptor, parent_identity)
    try:
        information = os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return
    if not stat.S_ISDIR(information.st_mode) or (information.st_dev, information.st_ino) != expected_identity:
        raise ContextError("guarded cleanup refused a replaced directory")
    shutil.rmtree(path)


def _publish_directory_exclusive(
    temporary_root: Path,
    output: Path,
    *,
    temporary_identity: tuple[int, int],
    parent_descriptor: int,
    parent_identity: tuple[int, int],
) -> tuple[int, int]:
    """Publish into a newly-created directory without replacing any path.

    The final manifest is linked last and is therefore the completion marker.
    A crash can leave an incomplete directory, but a later invocation refuses
    to overwrite it.  Hard links require the temporary sibling and output to be
    on the same filesystem, which is guaranteed by the caller.
    """

    _require_parent_identity(parent_descriptor, parent_identity)
    if _directory_identity(temporary_root) != temporary_identity:
        raise ContextError("temporary output identity changed before publication")
    try:
        os.mkdir(output.name, 0o700, dir_fd=parent_descriptor)
    except FileExistsError as error:
        raise ContextError("output appeared during publication; refusing to replace it") from error
    output_information = os.stat(output.name, dir_fd=parent_descriptor, follow_symlinks=False)
    output_identity = (output_information.st_dev, output_information.st_ino)
    created = True
    try:
        directories = sorted(
            (path for path in temporary_root.rglob("*") if path.is_dir()),
            key=lambda path: (len(path.relative_to(temporary_root).parts), path.as_posix()),
        )
        for directory in directories:
            target = output / directory.relative_to(temporary_root)
            os.mkdir(target, 0o700)
        files = sorted(
            (path for path in temporary_root.rglob("*") if path.is_file()),
            key=lambda path: path.relative_to(temporary_root).as_posix(),
        )
        manifest_source = temporary_root / MANIFEST_NAME
        if manifest_source not in files:
            raise ContextError("temporary output is missing its completion manifest")
        files.remove(manifest_source)
        files.append(manifest_source)
        for source in files:
            target = output / source.relative_to(temporary_root)
            os.link(source, target, follow_symlinks=False)
        created = False
    finally:
        if created:
            _cleanup_guarded_directory(
                output,
                expected_identity=output_identity,
                parent_descriptor=parent_descriptor,
                parent_identity=parent_identity,
            )
    return output_identity


def build_context(
    *,
    contract: dict[str, Any],
    contract_sha256: str,
    report: dict[str, Any],
    report_sha256: str,
    report_name: str,
    mesh_path: Path,
    mesh_sha256: str,
    expected_components: int,
    batch_size: int,
    fixture_mode: bool,
    output: Path,
    np: Any,
) -> dict[str, Any]:
    if Path(report_name).name != report_name or not report_name or len(report_name.encode("utf-8")) > 255:
        raise ContextError("F18 report name must be a bounded basename")
    if Path(mesh_path.name).name != mesh_path.name or len(mesh_path.name.encode("utf-8")) > 255:
        raise ContextError("mesh name must be a bounded basename")
    _validate_contract(contract, expected_components=expected_components, fixture_mode=fixture_mode)
    reported_components = _validate_f18_report(
        report,
        mesh_sha256,
        expected_components,
        fixture_mode=fixture_mode,
    )
    vertices, faces, parse = _load_mesh(mesh_path, mesh_sha256, np)
    f18 = _load_f18_module()
    analysis = f18.analyze_boundary_components(vertices, faces, np)
    recomputed_components = analysis["components"]
    _compare_recomputed_f18(recomputed_components, reported_components)
    boundary_edges, boundary_owners, neighbours = _build_face_adjacency(faces, np)
    if not np.array_equal(boundary_edges, analysis["boundary_edges"]):
        raise ContextError("F26 incidence-one edges differ from the F18 topology implementation")
    if report["topology"].get("boundary_edges") != int(len(boundary_edges)):
        raise ContextError("recomputed boundary edge count differs from F18")
    rank_by_vertex = np.zeros(len(vertices), dtype=np.int64)
    rank_by_vertex[analysis["active_vertices"]] = analysis["stable_ranks"]
    edge_ranks = rank_by_vertex[boundary_edges[:, 0]]
    if np.any(edge_ranks <= 0) or not np.array_equal(edge_ranks, rank_by_vertex[boundary_edges[:, 1]]):
        raise ContextError("boundary edge rank assignment is incomplete")
    mesh_bounds = np.asarray((vertices.min(axis=0), vertices.max(axis=0)), dtype=np.float64)
    parent_descriptor, parent_identity = _open_private_output_parent(output)
    temporary_root, temporary_identity = _create_private_temporary_sibling(
        output,
        parent_descriptor=parent_descriptor,
        parent_identity=parent_identity,
    )
    artifacts: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    batches: list[dict[str, Any]] = []
    total_output_bytes = 0
    try:
        for offset in range(0, expected_components, batch_size):
            batch_number = offset // batch_size + 1
            batch_id = f"batch_{batch_number:04d}"
            selected = reported_components[offset : offset + batch_size]
            if not selected or len(selected) > MAX_BATCH_SIZE:
                raise ContextError("batch cardinality is outside the bounded contract")
            batch_component_ids: list[str] = []
            for reported in selected:
                rank = int(reported["component_rank"])
                component_id = str(reported["component_id"])
                component_edges, incident, ring_1, ring_2 = _component_topology_layers(
                    rank,
                    boundary_edges,
                    boundary_owners,
                    edge_ranks,
                    neighbours,
                    np,
                )
                context_faces = np.concatenate((incident, ring_1, ring_2))
                estimated_svg_bytes = _estimate_svg_bytes(
                    int(len(context_faces)),
                    int(len(component_edges)),
                )
                if estimated_svg_bytes > MAX_SVG_BYTES_PER_COMPONENT:
                    raise ContextError(f"{component_id} SVG estimate exceeds the bounded byte contract")
                _reserve_output_bytes(
                    total_output_bytes,
                    estimated_svg_bytes,
                    label=f"{component_id} estimated SVG",
                )
                topology_fingerprint = hashlib.sha256(
                    b"F26\0"
                    + bytes.fromhex(_array_sha256(component_edges.reshape(-1), np))
                    + bytes.fromhex(_array_sha256(incident, np))
                    + bytes.fromhex(_array_sha256(ring_1, np))
                    + bytes.fromhex(_array_sha256(ring_2, np))
                ).hexdigest()
                component_record = {
                    "schema": "porsche-917-topology-context/f26-v1",
                    "phase": PHASE,
                    "component_id": component_id,
                    "component_rank": rank,
                    "source_binding": {
                        "contract_sha256": contract_sha256,
                        "mesh_name": mesh_path.name,
                        "mesh_sha256": mesh_sha256,
                        "f18_report_name": report_name,
                        "f18_report_sha256": report_sha256,
                    },
                    "coordinate_policy": {
                        "units": "input OBJ coordinate units",
                        "metric_conversion_applied": False,
                        "scale_inference_applied": False,
                        "axis_semantics_inferred": False,
                        "coordinates_local_only": True,
                    },
                    "f18_geometric_provenance": {
                        "review_class": reported["review_class"],
                        "boundary_edge_count": int(reported["boundary_edge_count"]),
                        "boundary_vertex_count": int(reported["boundary_vertex_count"]),
                        "semantic_label": None,
                        "interface_confirmed": False,
                    },
                    "topology_context": {
                        "incident_face_count": int(len(incident)),
                        "ring_1_face_count": int(len(ring_1)),
                        "ring_2_face_count": int(len(ring_2)),
                        "context_face_count": int(len(context_faces)),
                        "topological_ring_count": 2,
                        "rings_disjoint": True,
                        "incident_definition": "faces incident to F18 incidence-one edges",
                        "ring_adjacency": "shared full triangle edge",
                        "topology_fingerprint_sha256": topology_fingerprint,
                    },
                    "visualization": {
                        "format": "svg",
                        "projection": "orthographic",
                        "canonical_views": list(CANONICAL_VIEWS),
                        "global_locator_in_every_view": True,
                        "global_locator_kind": "projected context bounds inside projected whole-mesh bounds",
                    },
                    "review": {
                        "state": "undetermined",
                        "automatic_classification_applied": False,
                        "semantic_interface_confirmed": False,
                        "release_authority": False,
                    },
                    "release_gates": dict(RELEASE_GATES),
                    "limitations": [
                        "The context is derived from an unscaled scan and stays local.",
                        "F18 geometric review_class is provenance, not a semantic interface label.",
                        "Exactly two topological face rings are shown; this is not a physical wall-thickness or flow-domain definition.",
                        "No F26 artifact authorizes CAD, CAE, PhysicsNeMo, fabrication or engine start.",
                    ],
                }
                json_path = temporary_root / batch_id / f"{component_id}.json"
                svg_path = temporary_root / batch_id / f"{component_id}.svg"
                json_payload = _json_bytes(component_record)
                total_output_bytes = _reserve_output_bytes(
                    total_output_bytes,
                    len(json_payload),
                    label=f"{component_id} JSON",
                )
                _write_bytes(json_path, json_payload)
                svg = _render_component_svg(
                    component_id,
                    vertices,
                    faces,
                    component_edges,
                    incident,
                    ring_1,
                    ring_2,
                    mesh_bounds,
                    np,
                )
                svg_payload = svg.encode("utf-8")
                if len(svg_payload) > MAX_SVG_BYTES_PER_COMPONENT:
                    raise ContextError(f"{component_id} SVG exceeds the bounded byte contract")
                total_output_bytes = _reserve_output_bytes(
                    total_output_bytes,
                    len(svg_payload),
                    label=f"{component_id} SVG",
                )
                _write_bytes(svg_path, svg_payload)
                json_evidence = _file_evidence(json_path, temporary_root, "application/json")
                svg_evidence = _file_evidence(svg_path, temporary_root, "image/svg+xml")
                artifacts.extend((json_evidence, svg_evidence))
                rows.append(
                    {
                        "component_id": component_id,
                        "component_rank": rank,
                        "batch_id": batch_id,
                        "f18_geometric_review_class": reported["review_class"],
                        "boundary_edge_count": int(reported["boundary_edge_count"]),
                        "incident_face_count": int(len(incident)),
                        "ring_1_face_count": int(len(ring_1)),
                        "ring_2_face_count": int(len(ring_2)),
                        "context_face_count": int(len(context_faces)),
                        "review_state": "undetermined",
                        "semantic_interface_confirmed": "false",
                        "release_authority": "false",
                        "json_path": json_evidence["path"],
                        "json_sha256": json_evidence["sha256"],
                        "svg_path": svg_evidence["path"],
                        "svg_sha256": svg_evidence["sha256"],
                    }
                )
                batch_component_ids.append(component_id)
            batches.append(
                {
                    "batch_id": batch_id,
                    "component_count": len(batch_component_ids),
                    "maximum_component_count": MAX_BATCH_SIZE,
                    "component_ids": batch_component_ids,
                }
            )

        inventory_stream = io.StringIO(newline="")
        fieldnames = list(rows[0])
        writer = csv.DictWriter(inventory_stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        inventory_path = temporary_root / INVENTORY_NAME
        inventory_payload = inventory_stream.getvalue().encode("utf-8")
        total_output_bytes = _reserve_output_bytes(
            total_output_bytes,
            len(inventory_payload),
            label="inventory CSV",
        )
        _write_bytes(inventory_path, inventory_payload)
        artifacts.append(_file_evidence(inventory_path, temporary_root, "text/csv"))
        artifacts.sort(key=lambda item: item["path"])
        manifest = {
            "schema": "porsche-917-topology-context-manifest/f26-v1",
            "phase": PHASE,
            "status": "complete_local_topology_context_pending_human_review",
            "claim_scope": "deterministic_topological_visualization_only",
            "source_binding": {
                "contract_sha256": contract_sha256,
                "mesh_name": mesh_path.name,
                "mesh_sha256": mesh_sha256,
                "mesh_bytes": parse["source_bytes"],
                "f18_report_name": report_name,
                "f18_report_sha256": report_sha256,
            },
            "mesh_inventory": {
                "vertex_count": parse["vertex_count"],
                "source_polygon_count": parse["source_polygon_count"],
                "triangulated_face_count": parse["triangulated_face_count"],
                "boundary_edge_count": int(len(boundary_edges)),
                "boundary_component_count": expected_components,
                "non_manifold_edges_accepted": False,
            },
            "topology_policy": {
                "incident_faces": "incidence-one edge owners",
                "topological_ring_count": 2,
                "ring_adjacency": "shared full triangle edge",
                "rings_disjoint": True,
            },
            "visualization_policy": {
                "canonical_orthographic_views": list(CANONICAL_VIEWS),
                "global_locator_in_every_view": True,
                "axis_semantics_confirmed": False,
            },
            "review_policy": {
                "component_count": expected_components,
                "review_state": "undetermined",
                "automatic_semantic_classification": False,
                "confirmed_interface_count": 0,
                "release_authority": False,
            },
            "batches": batches,
            "hash_coverage": {
                "algorithm": "sha256",
                "payload_file_count": len(artifacts),
                "every_component_json_svg_and_inventory_csv_hashed": True,
                "root_manifest_excluded_to_avoid_recursive_self_hash": True,
            },
            "artifacts": artifacts,
            "coordinate_custody": {
                "derived_coordinates_present_only_in_local_svg_payloads": True,
                "absolute_source_paths_recorded": False,
                "git_tracking_allowed": False,
            },
            "output_bounds": {
                "maximum_svg_bytes_per_component": MAX_SVG_BYTES_PER_COMPONENT,
                "maximum_total_output_bytes": MAX_TOTAL_OUTPUT_BYTES,
                "payload_bytes_excluding_root_manifest": total_output_bytes,
                "publication": "private_parent_0700_owned_by_runtime_uid_exclusive_new_directory_with_manifest_linked_last",
            },
            "release_gates": dict(RELEASE_GATES),
            "limitations": [
                "This output must remain under ignored local work storage.",
                "The four views use scan coordinates whose physical axes and units remain unconfirmed.",
                "No component is automatically classified or confirmed as an interface.",
                "Image availability and a green synthetic smoke do not validate the canonical scan result.",
            ],
        }
        manifest_payload = _json_bytes(manifest)
        total_output_bytes = _reserve_output_bytes(
            total_output_bytes,
            len(manifest_payload),
            label="root manifest",
        )
        _write_bytes(temporary_root / MANIFEST_NAME, manifest_payload)
        _publish_directory_exclusive(
            temporary_root,
            output,
            temporary_identity=temporary_identity,
            parent_descriptor=parent_descriptor,
            parent_identity=parent_identity,
        )
        _cleanup_guarded_directory(
            temporary_root,
            expected_identity=temporary_identity,
            parent_descriptor=parent_descriptor,
            parent_identity=parent_identity,
        )
    except Exception:
        _cleanup_guarded_directory(
            temporary_root,
            expected_identity=temporary_identity,
            parent_descriptor=parent_descriptor,
            parent_identity=parent_identity,
        )
        raise
    finally:
        os.close(parent_descriptor)
    return {
        "status": manifest["status"],
        "component_count": expected_components,
        "batch_count": len(batches),
        "maximum_components_per_batch": max(item["component_count"] for item in batches),
        "payload_file_count": len(artifacts),
        "total_output_bytes": total_output_bytes,
        "manifest": MANIFEST_NAME,
        "inventory": INVENTORY_NAME,
        "confirmed_interface_count": 0,
        "release_gates": dict(RELEASE_GATES),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--mesh-sha256", required=True)
    parser.add_argument("--f18-report", type=Path, required=True)
    parser.add_argument("--f18-report-sha256", required=True)
    parser.add_argument("--expected-components", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=MAX_BATCH_SIZE)
    parser.add_argument("--fixture-mode", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.expected_components <= 0 or arguments.expected_components > 100_000:
        raise SystemExit("--expected-components is outside the bounded contract")
    if arguments.fixture_mode and arguments.expected_components > MAX_FIXTURE_COMPONENTS:
        raise SystemExit(f"fixture mode accepts at most {MAX_FIXTURE_COMPONENTS} components")
    if arguments.batch_size <= 0 or arguments.batch_size > MAX_BATCH_SIZE:
        raise SystemExit(f"--batch-size must be between 1 and {MAX_BATCH_SIZE}")
    try:
        import numpy as np
    except ImportError as error:
        raise SystemExit("F26 requires NumPy 2.2.6 from the dedicated image") from error
    if np.__version__ != "2.2.6":
        raise SystemExit("F26 requires exactly NumPy 2.2.6")
    try:
        contract_payload = _read_small_bound_file(
            arguments.contract,
            arguments.contract_sha256,
            maximum_bytes=MAX_CONTRACT_BYTES,
            label="contract",
        )
        report_payload = _read_small_bound_file(
            arguments.f18_report,
            arguments.f18_report_sha256,
            maximum_bytes=MAX_REPORT_BYTES,
            label="F18 report",
        )
        summary = build_context(
            contract=_load_json(contract_payload, label="contract"),
            contract_sha256=arguments.contract_sha256,
            report=_load_json(report_payload, label="F18 report"),
            report_sha256=arguments.f18_report_sha256,
            report_name=arguments.f18_report.name,
            mesh_path=arguments.mesh,
            mesh_sha256=arguments.mesh_sha256,
            expected_components=arguments.expected_components,
            batch_size=arguments.batch_size,
            fixture_mode=arguments.fixture_mode,
            output=arguments.output,
            np=np,
        )
    except ContextError as error:
        raise SystemExit(f"F26 topology context error: {error}") from error
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
