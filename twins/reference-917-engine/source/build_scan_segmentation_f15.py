#!/usr/bin/env python3
"""Inventory an OBJ scan without copying geometry or inferring metric meaning.

The implementation intentionally uses only the Python standard library. Edge
incidence is computed by an external merge sort so the canonical scan does not
require an in-memory dictionary containing millions of edges.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import json
import math
import struct
import tempfile
from array import array
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator, TextIO


EXPECTED_SOURCE_SHA256 = "428c4143d073f8330022f2fecbd1ac1ee7784d4f1565f1160020448dbdffa0ae"
EXPECTED_DEFAULT_PATH = "raw-scans/917-engine/original/917-engine-case-with-cylinders.obj"
UINT32_MAX = (1 << 32) - 1
EDGE_RECORD = struct.Struct("=Q")
OUTPUT_NAMES = {
    "report": "scan-segmentation-f15-report.json",
    "surface_components": "surface-components-f15.csv",
    "boundary_components": "boundary-components-f15.csv",
    "declarations": "obj-declarations-f15.json",
}
RELEASE_KEYS = (
    "identity_confirmed",
    "scale_confirmed",
    "units_confirmed",
    "variant_confirmed",
    "semantic_segmentation_confirmed",
    "geometry_repaired",
    "watertight_manufacturing_geometry",
    "cad_reconstruction_complete",
    "cfd_geometry_released",
    "physics_simulation_released",
    "functional_release_authorized",
    "fabrication_release_authorized",
    "three_dimensional_print_release_authorized",
)


class DisjointSet:
    """Compact deterministic disjoint-set forest for OBJ vertex indices."""

    def __init__(self) -> None:
        self.parent = array("I")
        self.size = array("I")

    def add(self) -> int:
        index = len(self.parent)
        if index > UINT32_MAX:
            raise ValueError("OBJ exceeds the supported uint32 vertex index range")
        self.parent.append(index)
        self.size.append(1)
        return index

    def find(self, value: int) -> int:
        parent = self.parent
        root = value
        while parent[root] != root:
            root = parent[root]
        while parent[value] != value:
            next_value = parent[value]
            parent[value] = root
            value = next_value
        return root

    def union(self, left: int, right: int) -> int:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return left_root
        if self.size[left_root] < self.size[right_root] or (
            self.size[left_root] == self.size[right_root] and left_root > right_root
        ):
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        self.size[left_root] += self.size[right_root]
        return left_root


class EdgeSpool:
    """Buffered stream of encoded unordered uint32 edge pairs."""

    def __init__(self, stream: TextIO | Any, flush_records: int = 65536) -> None:
        self.stream = stream
        self.flush_records = flush_records
        self.buffer = array("Q")
        self.count = 0

    def add(self, left: int, right: int) -> None:
        low, high = (left, right) if left <= right else (right, left)
        self.buffer.append((low << 32) | high)
        self.count += 1
        if len(self.buffer) >= self.flush_records:
            self.flush()

    def flush(self) -> None:
        if self.buffer:
            self.buffer.tofile(self.stream)
            self.buffer = array("Q")


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _safe_inventory_increment(
    inventory: dict[Any, int], key: Any, maximum: int, overflow: Counter[str], kind: str
) -> None:
    if key in inventory:
        inventory[key] += 1
    elif len(inventory) < maximum:
        inventory[key] = 1
    else:
        overflow[kind] += 1


def _face_area(indices: list[int], xs: array, ys: array, zs: array) -> float:
    """Return fan-triangulated unsigned polygon area in raw coordinate units."""

    if len(indices) < 3:
        return 0.0
    first = indices[0]
    x0, y0, z0 = xs[first], ys[first], zs[first]
    doubled_area = 0.0
    for offset in range(1, len(indices) - 1):
        second = indices[offset]
        third = indices[offset + 1]
        ax, ay, az = xs[second] - x0, ys[second] - y0, zs[second] - z0
        bx, by, bz = xs[third] - x0, ys[third] - y0, zs[third] - z0
        cx = ay * bz - az * by
        cy = az * bx - ax * bz
        cz = ax * by - ay * bx
        doubled_area += math.sqrt(cx * cx + cy * cy + cz * cz)
    return doubled_area * 0.5


def _resolve_vertex_reference(token: str, vertex_count: int) -> int:
    vertex_token = token.split("/", 1)[0]
    if not vertex_token:
        raise ValueError("missing vertex index")
    raw_index = int(vertex_token)
    if raw_index == 0:
        raise ValueError("OBJ vertex index zero is invalid")
    resolved = raw_index - 1 if raw_index > 0 else vertex_count + raw_index
    if resolved < 0 or resolved >= vertex_count:
        raise ValueError("vertex index references an undeclared vertex")
    return resolved


def _iter_uint64(path: Path, block_records: int = 65536) -> Iterator[int]:
    with path.open("rb") as stream:
        while True:
            data = stream.read(block_records * EDGE_RECORD.size)
            if not data:
                break
            if len(data) % EDGE_RECORD.size:
                raise ValueError("truncated temporary edge run")
            values = array("Q")
            values.frombytes(data)
            yield from values


def _sorted_edge_runs(edge_path: Path, temp_dir: Path, chunk_records: int) -> list[Path]:
    runs: list[Path] = []
    with edge_path.open("rb") as stream:
        run_index = 0
        while True:
            data = stream.read(chunk_records * EDGE_RECORD.size)
            if not data:
                break
            if len(data) % EDGE_RECORD.size:
                raise ValueError("truncated temporary edge spool")
            values = array("Q")
            values.frombytes(data)
            ordered = array("Q", sorted(values))
            run_path = temp_dir / f"edge-run-{run_index:05d}.bin"
            with run_path.open("wb") as output:
                ordered.tofile(output)
            runs.append(run_path)
            run_index += 1
    return runs


def _finalize_edge_incidence(
    edge_path: Path,
    temp_dir: Path,
    chunk_records: int,
    vertex_count: int,
    xs: array,
    ys: array,
    zs: array,
    maximum_reported: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    runs = _sorted_edge_runs(edge_path, temp_dir, chunk_records)
    if not runs:
        return (
            {
                "edge_occurrences": 0,
                "unique_edges": 0,
                "boundary_edges": 0,
                "open_edges": 0,
                "manifold_edges": 0,
                "non_manifold_edges": 0,
                "maximum_edge_incidence": 0,
                "boundary_component_count": 0,
                "closed_boundary_loop_candidate_count": 0,
            },
            [],
        )

    boundary_keys = array("Q")
    unique_edges = 0
    manifold_edges = 0
    non_manifold_edges = 0
    maximum_incidence = 0
    current: int | None = None
    incidence = 0

    def consume(key: int, count: int) -> None:
        nonlocal unique_edges, manifold_edges, non_manifold_edges, maximum_incidence
        unique_edges += 1
        maximum_incidence = max(maximum_incidence, count)
        if count == 1:
            boundary_keys.append(key)
        elif count == 2:
            manifold_edges += 1
        else:
            non_manifold_edges += 1

    merged: Iterable[int] = heapq.merge(*(_iter_uint64(path) for path in runs))
    for key in merged:
        if current is None:
            current, incidence = key, 1
        elif key == current:
            incidence += 1
        else:
            consume(current, incidence)
            current, incidence = key, 1
    if current is not None:
        consume(current, incidence)

    boundary_dsu = DisjointSet()
    for _ in range(vertex_count):
        boundary_dsu.add()
    degrees: dict[int, int] = {}
    for key in boundary_keys:
        left, right = key >> 32, key & UINT32_MAX
        boundary_dsu.union(left, right)
        degrees[left] = degrees.get(left, 0) + 1
        degrees[right] = degrees.get(right, 0) + 1

    aggregates: dict[int, dict[str, Any]] = {}
    for vertex, degree in degrees.items():
        root = boundary_dsu.find(vertex)
        item = aggregates.setdefault(
            root,
            {
                "vertex_count": 0,
                "edge_count": 0,
                "endpoint_count": 0,
                "branched_vertex_count": 0,
                "min_vertex_index": vertex,
                "bounds_min_obj_units": [xs[vertex], ys[vertex], zs[vertex]],
                "bounds_max_obj_units": [xs[vertex], ys[vertex], zs[vertex]],
            },
        )
        item["vertex_count"] += 1
        item["endpoint_count"] += int(degree == 1)
        item["branched_vertex_count"] += int(degree > 2)
        item["min_vertex_index"] = min(item["min_vertex_index"], vertex)
        for axis, value in enumerate((xs[vertex], ys[vertex], zs[vertex])):
            item["bounds_min_obj_units"][axis] = min(item["bounds_min_obj_units"][axis], value)
            item["bounds_max_obj_units"][axis] = max(item["bounds_max_obj_units"][axis], value)
    for key in boundary_keys:
        root = boundary_dsu.find(key >> 32)
        aggregates[root]["edge_count"] += 1

    ordered = sorted(
        aggregates.values(),
        key=lambda item: (-item["edge_count"], -item["vertex_count"], item["min_vertex_index"]),
    )
    records: list[dict[str, Any]] = []
    for rank, item in enumerate(ordered[:maximum_reported], start=1):
        minimum = item.pop("min_vertex_index")
        item["component_id"] = f"boundary_{rank:04d}"
        item["minimum_source_vertex_index_1_based"] = minimum + 1
        item["closed_loop_candidate"] = bool(
            item["vertex_count"] >= 3
            and item["edge_count"] == item["vertex_count"]
            and item["endpoint_count"] == 0
            and item["branched_vertex_count"] == 0
        )
        item["semantic_status"] = "unclassified_scan_boundary"
        item["dimensions_obj_units"] = [
            high - low
            for low, high in zip(item["bounds_min_obj_units"], item["bounds_max_obj_units"])
        ]
        records.append(item)

    topology = {
        "edge_occurrences": edge_path.stat().st_size // EDGE_RECORD.size,
        "unique_edges": unique_edges,
        "boundary_edges": len(boundary_keys),
        "open_edges": len(boundary_keys),
        "manifold_edges": manifold_edges,
        "non_manifold_edges": non_manifold_edges,
        "maximum_edge_incidence": maximum_incidence,
        "boundary_component_count": len(ordered),
        "reported_boundary_component_count": len(records),
        "boundary_components_truncated": len(ordered) > len(records),
        "closed_boundary_loop_candidate_count": sum(
            1
            for item in ordered
            if item["vertex_count"] >= 3
            and item["edge_count"] == item["vertex_count"]
            and item["endpoint_count"] == 0
            and item["branched_vertex_count"] == 0
        ),
    }
    return topology, records


def _surface_components(
    dsu: DisjointSet,
    used_vertices: bytearray,
    face_representatives: array,
    xs: array,
    ys: array,
    zs: array,
    maximum_reported: int,
) -> tuple[int, list[dict[str, Any]]]:
    aggregates: dict[int, dict[str, Any]] = {}
    for vertex, used in enumerate(used_vertices):
        if not used:
            continue
        root = dsu.find(vertex)
        item = aggregates.setdefault(
            root,
            {
                "vertex_count": 0,
                "face_count": 0,
                "min_vertex_index": vertex,
                "bounds_min_obj_units": [xs[vertex], ys[vertex], zs[vertex]],
                "bounds_max_obj_units": [xs[vertex], ys[vertex], zs[vertex]],
            },
        )
        item["vertex_count"] += 1
        item["min_vertex_index"] = min(item["min_vertex_index"], vertex)
        for axis, value in enumerate((xs[vertex], ys[vertex], zs[vertex])):
            item["bounds_min_obj_units"][axis] = min(item["bounds_min_obj_units"][axis], value)
            item["bounds_max_obj_units"][axis] = max(item["bounds_max_obj_units"][axis], value)
    for representative in face_representatives:
        root = dsu.find(representative)
        aggregates[root]["face_count"] += 1

    ordered = sorted(
        aggregates.values(),
        key=lambda item: (-item["face_count"], -item["vertex_count"], item["min_vertex_index"]),
    )
    records: list[dict[str, Any]] = []
    for rank, item in enumerate(ordered[:maximum_reported], start=1):
        minimum = item.pop("min_vertex_index")
        item["component_id"] = f"surface_{rank:04d}"
        item["minimum_source_vertex_index_1_based"] = minimum + 1
        item["semantic_status"] = "unclassified_topological_component"
        item["dimensions_obj_units"] = [
            high - low
            for low, high in zip(item["bounds_min_obj_units"], item["bounds_max_obj_units"])
        ]
        records.append(item)
    return len(ordered), records


def analyze_obj(source: Path, policy: dict[str, Any], temp_parent: Path) -> dict[str, Any]:
    """Parse an OBJ and return counts/topology only; never return source geometry."""

    maximum_bytes = int(policy["maximum_source_bytes"])
    source_size = source.stat().st_size
    if source_size > maximum_bytes:
        raise ValueError(f"source exceeds maximum_source_bytes ({source_size} > {maximum_bytes})")

    parser = policy["parser_policy"]
    maximum_line = int(parser["maximum_line_bytes"])
    maximum_distinct = int(parser["maximum_distinct_declarations_per_kind"])
    maximum_arity = int(parser["maximum_face_arity"])
    zero_area_threshold = float(parser["zero_area_threshold_obj_units_squared"])
    chunk_records = int(parser["edge_sort_chunk_records"])

    dsu = DisjointSet()
    xs, ys, zs = array("d"), array("d"), array("d")
    valid_vertices = bytearray()
    used_vertices = bytearray()
    face_representatives = array("I")
    digest = hashlib.sha256()
    errors: list[str] = []
    warnings: list[str] = []
    counts: Counter[str] = Counter()
    face_arity: Counter[int] = Counter()
    directive_counts: Counter[str] = Counter()
    unknown_directives: Counter[str] = Counter()
    overflow: Counter[str] = Counter()
    objects: dict[str, int] = {}
    groups: dict[tuple[str, ...], int] = {}
    materials: dict[str, int] = {}
    material_libraries: dict[str, int] = {}
    current_object = ("default",)
    current_groups = ("default",)
    current_material = "none"
    global_min = [math.inf, math.inf, math.inf]
    global_max = [-math.inf, -math.inf, -math.inf]

    temp_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="f15-edge-sort-", dir=temp_parent) as temp_name:
        temp_dir = Path(temp_name)
        edge_path = temp_dir / "edge-occurrences.bin"
        with source.open("rb") as input_stream, edge_path.open("wb") as edge_stream:
            spool = EdgeSpool(edge_stream)
            for line_number, raw_line in enumerate(input_stream, start=1):
                digest.update(raw_line)
                counts["lines"] += 1
                if len(raw_line) > maximum_line:
                    errors.append(f"line_{line_number}_exceeds_maximum_line_bytes")
                    continue
                try:
                    line = raw_line.decode("utf-8")
                except UnicodeDecodeError:
                    errors.append(f"line_{line_number}_is_not_utf8")
                    continue
                stripped = line.strip()
                if not stripped:
                    counts["blank_lines"] += 1
                    continue
                if stripped.startswith("#"):
                    counts["comment_lines"] += 1
                    continue
                parts = stripped.split()
                directive = parts[0]
                directive_counts[directive] += 1

                if directive == "v":
                    dsu.add()
                    used_vertices.append(0)
                    if len(parts) < 4:
                        errors.append(f"line_{line_number}_vertex_requires_three_coordinates")
                        xs.append(0.0)
                        ys.append(0.0)
                        zs.append(0.0)
                        valid_vertices.append(0)
                        continue
                    try:
                        point = [float(parts[index]) for index in range(1, 4)]
                    except ValueError:
                        point = [math.nan, math.nan, math.nan]
                    if not all(math.isfinite(value) for value in point):
                        errors.append(f"line_{line_number}_vertex_has_non_finite_coordinate")
                        point = [0.0, 0.0, 0.0]
                        valid_vertices.append(0)
                    else:
                        valid_vertices.append(1)
                        for axis, value in enumerate(point):
                            global_min[axis] = min(global_min[axis], value)
                            global_max[axis] = max(global_max[axis], value)
                    xs.append(point[0])
                    ys.append(point[1])
                    zs.append(point[2])
                    counts["vertices"] += 1
                    continue

                if directive == "vt":
                    counts["texture_vertices"] += 1
                    continue
                if directive == "vn":
                    counts["normal_vertices"] += 1
                    continue
                if directive == "vp":
                    counts["parameter_vertices"] += 1
                    continue
                if directive == "o":
                    current_object = (stripped[len(directive) :].strip() or "default",)
                    counts["object_declarations"] += 1
                    continue
                if directive == "g":
                    current_groups = tuple(parts[1:]) or ("default",)
                    counts["group_declarations"] += 1
                    continue
                if directive == "usemtl":
                    current_material = stripped[len(directive) :].strip() or "none"
                    counts["material_assignments"] += 1
                    continue
                if directive == "mtllib":
                    counts["material_library_declarations"] += 1
                    for library in parts[1:] or ["missing"]:
                        _safe_inventory_increment(
                            material_libraries, library, maximum_distinct, overflow, "mtllib"
                        )
                    continue
                if directive == "f":
                    counts["polygon_faces"] += 1
                    tokens = parts[1:]
                    _safe_inventory_increment(
                        objects, current_object[0], maximum_distinct, overflow, "objects"
                    )
                    _safe_inventory_increment(
                        groups, current_groups, maximum_distinct, overflow, "groups"
                    )
                    _safe_inventory_increment(
                        materials, current_material, maximum_distinct, overflow, "materials"
                    )
                    if len(tokens) < 3 or len(tokens) > maximum_arity:
                        errors.append(f"line_{line_number}_invalid_face_arity_{len(tokens)}")
                        counts["invalid_faces"] += 1
                        continue
                    indices: list[int] = []
                    try:
                        indices = [
                            _resolve_vertex_reference(token, len(dsu.parent)) for token in tokens
                        ]
                    except (ValueError, TypeError) as exc:
                        errors.append(f"line_{line_number}_invalid_face_reference:{exc}")
                        counts["invalid_faces"] += 1
                        continue
                    if any(not valid_vertices[index] for index in indices):
                        errors.append(f"line_{line_number}_face_references_invalid_vertex")
                        counts["invalid_faces"] += 1
                        continue
                    face_arity[len(indices)] += 1
                    counts["valid_polygon_faces"] += 1
                    counts["triangulated_face_equivalent"] += len(indices) - 2
                    counts["triangle_faces"] += int(len(indices) == 3)
                    if len(set(indices)) != len(indices):
                        counts["faces_with_repeated_vertex_indices"] += 1
                    if _face_area(indices, xs, ys, zs) <= zero_area_threshold:
                        counts["zero_area_faces"] += 1
                    representative = indices[0]
                    face_representatives.append(representative)
                    for vertex in indices:
                        used_vertices[vertex] = 1
                        dsu.union(representative, vertex)
                    for offset, left in enumerate(indices):
                        right = indices[(offset + 1) % len(indices)]
                        if left == right:
                            counts["degenerate_edge_occurrences"] += 1
                        spool.add(left, right)
                    continue

                if directive in {"s", "l", "p"}:
                    counts[f"{directive}_statements"] += 1
                else:
                    unknown_directives[directive] += 1
            spool.flush()

        if overflow:
            errors.extend(
                f"{kind}_distinct_declaration_limit_exceeded:{count}"
                for kind, count in sorted(overflow.items())
            )
        if unknown_directives:
            warnings.append("unknown_obj_directives_are_inventoried_but_not_interpreted")
        if counts["vertices"] == 0:
            errors.append("obj_contains_no_vertices")
        if counts["valid_polygon_faces"] == 0:
            errors.append("obj_contains_no_valid_polygon_faces")

        surface_count, surface_records = _surface_components(
            dsu,
            used_vertices,
            face_representatives,
            xs,
            ys,
            zs,
            int(parser["maximum_reported_surface_components"]),
        )
        edge_topology, boundary_records = _finalize_edge_incidence(
            edge_path,
            temp_dir,
            chunk_records,
            len(dsu.parent),
            xs,
            ys,
            zs,
            int(parser["maximum_reported_boundary_components"]),
        )

    if counts["vertices"]:
        dimensions = [high - low for low, high in zip(global_min, global_max)]
        diagonal = math.sqrt(sum(value * value for value in dimensions))
    else:
        global_min, global_max, dimensions, diagonal = [], [], [], None

    declaration_inventory = {
        "objects": [
            {"name": name, "face_statement_count": count}
            for name, count in sorted(objects.items())
        ],
        "groups": [
            {"names": list(names), "face_statement_count": count}
            for names, count in sorted(groups.items())
        ],
        "materials": [
            {"name": name, "face_statement_count": count}
            for name, count in sorted(materials.items())
        ],
        "material_libraries": [
            {"name": name, "declaration_count": count}
            for name, count in sorted(material_libraries.items())
        ],
        "directive_counts": dict(sorted(directive_counts.items())),
        "unknown_directive_counts": dict(sorted(unknown_directives.items())),
    }
    return {
        "source_sha256": digest.hexdigest(),
        "source_bytes": source_size,
        "parse_errors": errors,
        "parse_warnings": warnings,
        "format_inventory": {
            **dict(sorted(counts.items())),
            "face_arity_histogram": {
                str(arity): count for arity, count in sorted(face_arity.items())
            },
            "unreferenced_vertices": int(len(used_vertices) - sum(used_vertices)),
        },
        "raw_coordinate_metrology": {
            "units": "OBJ coordinate units",
            "units_confirmed": False,
            "metric_conversion_applied": False,
            "coordinate_transform_applied": False,
            "bounds_min_obj_units": global_min,
            "bounds_max_obj_units": global_max,
            "dimensions_obj_units": dimensions,
            "diagonal_obj_units": diagonal,
        },
        "topology": {
            "surface_component_count": surface_count,
            "reported_surface_component_count": len(surface_records),
            "surface_components_truncated": surface_count > len(surface_records),
            **edge_topology,
            "watertight": bool(
                counts["valid_polygon_faces"]
                and edge_topology["boundary_edges"] == 0
                and edge_topology["non_manifold_edges"] == 0
            ),
        },
        "surface_components": surface_records,
        "boundary_components": boundary_records,
        "declaration_inventory": declaration_inventory,
    }


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("schema_version") != "1.0.0" or contract.get("phase") != "F15":
        errors.append("contract_schema_or_phase_changed")
    custody = contract.get("source_custody", {})
    if custody.get("default_path") != EXPECTED_DEFAULT_PATH:
        errors.append("contract_default_source_path_changed")
    if custody.get("expected_sha256") != EXPECTED_SOURCE_SHA256:
        errors.append("contract_expected_source_sha256_changed")
    if not isinstance(custody.get("maximum_source_bytes"), int) or custody["maximum_source_bytes"] <= 0:
        errors.append("contract_invalid_maximum_source_bytes")
    for key, expected in {
        "raw_geometry_must_remain_outside_git": True,
        "source_copy_allowed": False,
        "geometry_payload_allowed_in_reports": False,
        "synthetic_fixture_mode_allowed": True,
    }.items():
        if custody.get(key) is not expected:
            errors.append(f"contract_source_custody_{key}_changed")

    parser = contract.get("parser_policy", {})
    if parser.get("implementation") != "python_standard_library_only":
        errors.append("contract_parser_implementation_changed")
    if parser.get("edge_definition") != "unordered_consecutive_polygon_vertex_pair":
        errors.append("contract_edge_definition_changed")
    if parser.get("surface_component_definition") != "faces_connected_by_shared_vertex_index":
        errors.append("contract_surface_component_definition_changed")
    for key in (
        "maximum_line_bytes",
        "maximum_distinct_declarations_per_kind",
        "maximum_face_arity",
        "edge_sort_chunk_records",
        "maximum_reported_surface_components",
        "maximum_reported_boundary_components",
    ):
        if not isinstance(parser.get(key), int) or parser[key] <= 0:
            errors.append(f"contract_invalid_{key}")
    if not _finite(parser.get("zero_area_threshold_obj_units_squared")) or parser[
        "zero_area_threshold_obj_units_squared"
    ] < 0:
        errors.append("contract_invalid_zero_area_threshold")

    metrology = contract.get("metrology_policy", {})
    for key in (
        "metric_conversion_allowed",
        "scale_inference_allowed",
        "axis_semantics_inference_allowed",
        "identity_inference_allowed",
        "variant_selection_allowed",
        "dimensional_tolerance_claim_allowed",
        "coordinate_transform_applied",
    ):
        if metrology.get(key) is not False:
            errors.append(f"contract_metrology_{key}_must_remain_false")

    reconciliation = contract.get("canonical_reconciliation", {})
    expected_reconciliation = {
        "vertices": 1282880,
        "polygon_faces": 2465879,
        "triangles": 2465879,
        "surface_components": 3,
        "boundary_edges": 101809,
        "non_manifold_edges": 0,
        "zero_area_faces": 2,
    }
    for key, expected in expected_reconciliation.items():
        if reconciliation.get(key) != expected:
            errors.append(f"contract_reconciliation_{key}_changed")
    if reconciliation.get("bounds_min_obj_units") != [-416.154602, -515.711365, 250.128326]:
        errors.append("contract_reconciliation_min_bounds_changed")
    if reconciliation.get("bounds_max_obj_units") != [586.020447, 252.563721, 989.893677]:
        errors.append("contract_reconciliation_max_bounds_changed")
    if reconciliation.get("bounds_absolute_tolerance_obj_units") != 1e-06:
        errors.append("contract_reconciliation_bounds_tolerance_changed")

    outputs = contract.get("outputs", {})
    if any(outputs.get(key) != value for key, value in OUTPUT_NAMES.items()):
        errors.append("contract_output_filenames_changed")
    if outputs.get("default_directory") != "work/917-engine/scan-segmentation-f15":
        errors.append("contract_default_output_directory_changed")

    release = contract.get("release_authority", {})
    if set(release) != set(RELEASE_KEYS) or any(release.get(key) is not False for key in RELEASE_KEYS):
        errors.append("contract_release_authority_must_remain_exactly_fail_closed")
    return errors


def _reconcile_canonical(contract: dict[str, Any], analysis: dict[str, Any]) -> list[str]:
    expected = contract["canonical_reconciliation"]
    inventory = analysis["format_inventory"]
    topology = analysis["topology"]
    actual = {
        "vertices": inventory.get("vertices", 0),
        "polygon_faces": inventory.get("polygon_faces", 0),
        "triangles": inventory.get("triangle_faces", 0),
        "surface_components": topology["surface_component_count"],
        "boundary_edges": topology["boundary_edges"],
        "non_manifold_edges": topology["non_manifold_edges"],
        "zero_area_faces": inventory.get("zero_area_faces", 0),
    }
    errors = [
        f"canonical_reconciliation_{key}_mismatch:{actual[key]}!={expected[key]}"
        for key in actual
        if actual[key] != expected[key]
    ]
    tolerance = float(expected["bounds_absolute_tolerance_obj_units"])
    metrology = analysis["raw_coordinate_metrology"]
    for label in ("bounds_min_obj_units", "bounds_max_obj_units"):
        if len(metrology[label]) != 3 or any(
            abs(actual_value - expected_value) > tolerance
            for actual_value, expected_value in zip(metrology[label], expected[label])
        ):
            errors.append(f"canonical_reconciliation_{label}_mismatch")
    return errors


def _write_csv(path: Path, records: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            flattened = dict(record)
            for key in ("bounds_min_obj_units", "bounds_max_obj_units", "dimensions_obj_units"):
                if key in flattened:
                    flattened[key] = json.dumps(flattened[key], separators=(",", ":"))
            writer.writerow(flattened)


def write_outputs(output_dir: Path, contract: dict[str, Any], report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_name = OUTPUT_NAMES["report"]
    declarations_name = OUTPUT_NAMES["declarations"]
    surface_name = OUTPUT_NAMES["surface_components"]
    boundary_name = OUTPUT_NAMES["boundary_components"]
    (output_dir / report_name).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / declarations_name).write_text(
        json.dumps(report.get("declaration_inventory", {}), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_csv(
        output_dir / surface_name,
        report.get("surface_components", []),
        [
            "component_id",
            "semantic_status",
            "minimum_source_vertex_index_1_based",
            "vertex_count",
            "face_count",
            "bounds_min_obj_units",
            "bounds_max_obj_units",
            "dimensions_obj_units",
        ],
    )
    _write_csv(
        output_dir / boundary_name,
        report.get("boundary_components", []),
        [
            "component_id",
            "semantic_status",
            "minimum_source_vertex_index_1_based",
            "vertex_count",
            "edge_count",
            "endpoint_count",
            "branched_vertex_count",
            "closed_loop_candidate",
            "bounds_min_obj_units",
            "bounds_max_obj_units",
            "dimensions_obj_units",
        ],
    )


def evaluate(
    contract_path: Path,
    source_path: Path,
    output_dir: Path,
    *,
    synthetic_fixture_mode: bool = False,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract_errors = validate_contract(contract)
    release = {key: False for key in RELEASE_KEYS}
    base: dict[str, Any] = {
        "schema_version": "1.0.0",
        "phase": "F15",
        "asset_id": contract.get("asset_id"),
        "execution_scope": "synthetic_fixture" if synthetic_fixture_mode else "canonical_scan",
        "contract_integrity_errors": contract_errors,
        "source_custody_errors": [],
        "canonical_reconciliation_errors": [],
        "release": release,
        "limitations": [
            "Les composantes sont topologiques et sans semantique mecanique certifiee.",
            "Les cotes restent en unites OBJ; aucune conversion metrique n'est appliquee.",
            "Le rapport ne contient ni sommets, ni faces, ni copie du scan.",
            "Aucune liberation fonctionnelle, de simulation ou de fabrication n'est accordee.",
        ],
        "output_manifest": {
            key: value
            for key, value in contract.get("outputs", {}).items()
            if key in {"report", "surface_components", "boundary_components", "declarations"}
        },
    }
    if contract_errors:
        base["report_status"] = "failed"
        base["parse_errors"] = []
        base["parse_warnings"] = []
        write_outputs(output_dir, contract, base)
        return base

    if synthetic_fixture_mode and not contract["source_custody"]["synthetic_fixture_mode_allowed"]:
        base["source_custody_errors"].append("synthetic_fixture_mode_not_allowed")
        base["report_status"] = "failed"
        write_outputs(output_dir, contract, base)
        return base

    analysis = analyze_obj(
        source_path,
        {
            "maximum_source_bytes": contract["source_custody"]["maximum_source_bytes"],
            "parser_policy": contract["parser_policy"],
        },
        output_dir,
    )
    source_hash_matches = analysis["source_sha256"] == contract["source_custody"]["expected_sha256"]
    if not source_hash_matches and not synthetic_fixture_mode:
        base["source_custody_errors"].append("source_sha256_does_not_match_canonical_scan")
    if source_hash_matches and not synthetic_fixture_mode:
        base["canonical_reconciliation_errors"] = _reconcile_canonical(contract, analysis)

    base.update(
        {
            "source_custody": {
                "source_filename": source_path.name,
                "source_bytes": analysis["source_bytes"],
                "source_sha256": analysis["source_sha256"],
                "expected_sha256_matches": source_hash_matches,
                "source_copy_created": False,
                "raw_geometry_in_report": False,
            },
            "parse_errors": analysis["parse_errors"],
            "parse_warnings": analysis["parse_warnings"],
            "format_inventory": analysis["format_inventory"],
            "raw_coordinate_metrology": analysis["raw_coordinate_metrology"],
            "topology": analysis["topology"],
            "surface_components": analysis["surface_components"],
            "boundary_components": analysis["boundary_components"],
            "declaration_inventory": analysis["declaration_inventory"],
        }
    )
    failed = bool(
        base["source_custody_errors"]
        or base["canonical_reconciliation_errors"]
        or analysis["parse_errors"]
    )
    if failed:
        base["report_status"] = "failed"
    elif synthetic_fixture_mode:
        base["report_status"] = "passed_synthetic_fixture_only"
    else:
        base["report_status"] = "passed_inventory_only"
    write_outputs(output_dir, contract, base)
    return base


def main() -> int:
    project_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(
        description="Fail-closed OBJ topology and declaration inventory for the local 917 scan."
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=project_root / "twins/reference-917-engine/scan-segmentation-f15.json",
    )
    parser.add_argument("--source", type=Path, default=project_root / EXPECTED_DEFAULT_PATH)
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "work/917-engine/scan-segmentation-f15",
    )
    parser.add_argument(
        "--synthetic-fixture-mode",
        action="store_true",
        help="Accept a non-canonical SHA only for parser tests; every release remains false.",
    )
    args = parser.parse_args()
    report = evaluate(
        args.contract.resolve(),
        args.source.resolve(),
        args.output.resolve(),
        synthetic_fixture_mode=args.synthetic_fixture_mode,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["report_status"].startswith("passed_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
