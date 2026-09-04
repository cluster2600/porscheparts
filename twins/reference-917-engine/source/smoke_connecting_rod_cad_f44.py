#!/usr/bin/env python3
"""Construit puis vérifie les livrables CAO display-only F44 dans Docker."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
import sys
from pathlib import Path
from typing import Any


SOURCE_DIR = Path(__file__).resolve().parent
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from build_connecting_rod_cad_f44 import (  # noqa: E402
    CAD_RUNTIME_IMAGE_DIGEST,
    CAD_RUNTIME_IMAGE_REPOSITORY,
    generate,
    load_contract,
    sha256,
    shape_metrics,
    source_provenance,
)
from validate_connecting_rod_cad_f44 import CONTRACT_RELATIVE_PATH, validate  # noqa: E402


STEP_VOLUME_REL_TOLERANCE = 1e-8
STEP_VOLUME_ABS_TOLERANCE_MM3 = 1e-4
STEP_BOUNDS_ABS_TOLERANCE_MM = 1e-6
CLEAN_EXPORT_VOLUME_REL_TOLERANCE = 1e-9
CLEAN_EXPORT_BOUNDS_ABS_TOLERANCE_MM = 1e-6
CANONICAL_VOLUME_REL_TOLERANCE = 1e-6
CANONICAL_BOUNDS_ABS_TOLERANCE_MM = 1e-5
STL_VOLUME_REL_TOLERANCE = 5e-3
STL_VOLUME_ABS_TOLERANCE_MM3 = 1.0
STL_BOUNDS_TOLERANCE_FACTOR = 1.5
INTERFERENCE_ABS_TOLERANCE_MM3 = 1e-9
BOOLEAN_RESIDUAL_ABS_TOLERANCE_MM3 = 1e-6
EXPECTED_GEOMETRY_CHECK_KEYS = {
    "minimum_ligament_mm",
    "bolt_hole_cutter_body_intersection_mm3",
    "bolt_hole_cutter_cap_intersection_mm3",
    "oil_channel_cutter_body_intersection_mm3",
    "unintended_fastener_interference_mm3",
    "spotface_cutter_minimum_intersection_mm3",
    "spotface_cutter_maximum_depth_delta_mm",
    "spotface_post_subtraction_maximum_residual_mm3",
    "oil_channel_cutter_bearing_upper_intersection_mm3",
    "oil_channel_cutter_bearing_lower_intersection_mm3",
    "oil_channel_cutter_bushing_intersection_mm3",
    "oil_channel_big_end_bore_opening_mm3",
    "oil_channel_small_end_bore_opening_mm3",
    "oil_channel_big_end_outer_exit_probe_mm3",
    "oil_channel_big_end_outer_exit_depth_delta_mm",
    "oil_channel_connected_component_count",
    "oil_channel_post_subtraction_maximum_residual_mm3",
    "bearing_cap_split_gap_delta_mm",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def finite_number(value: Any, message: str) -> float:
    require(
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value)),
        message,
    )
    return float(value)


def tracked_output_file(output: Path, relative: Path) -> Path:
    require(not relative.is_absolute() and ".." not in relative.parts, f"unsafe_output_path:{relative}")
    candidate = output / relative
    require(not candidate.is_symlink(), f"output_symlink_not_allowed:{candidate}")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(output.resolve())
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"invalid_output_file:{relative}:{exc}") from exc
    require(resolved.is_file(), f"output_regular_file_required:{relative}")
    return resolved


def _stl_triangles(path: Path) -> list[tuple[tuple[float, float, float], ...]]:
    """Rouvre un STL binaire ou ASCII et retourne ses triangles."""

    payload = path.read_bytes()
    triangles: list[tuple[tuple[float, float, float], ...]] = []
    if len(payload) >= 84:
        triangle_count = struct.unpack_from("<I", payload, 80)[0]
        if len(payload) == 84 + triangle_count * 50:
            for index in range(triangle_count):
                values = struct.unpack_from("<12fH", payload, 84 + index * 50)
                triangles.append(
                    (
                        (float(values[3]), float(values[4]), float(values[5])),
                        (float(values[6]), float(values[7]), float(values[8])),
                        (float(values[9]), float(values[10]), float(values[11])),
                    )
                )
            return triangles
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"invalid_stl_encoding:{path.name}") from exc
    vertices: list[tuple[float, float, float]] = []
    for line in text.splitlines():
        fields = line.strip().split()
        if len(fields) == 4 and fields[0].lower() == "vertex":
            try:
                vertices.append(tuple(float(value) for value in fields[1:4]))
            except ValueError as exc:
                raise RuntimeError(f"invalid_stl_vertex:{path.name}") from exc
    require(vertices and len(vertices) % 3 == 0, f"invalid_ascii_stl_triangles:{path.name}")
    for index in range(0, len(vertices), 3):
        triangles.append((vertices[index], vertices[index + 1], vertices[index + 2]))
    return triangles


def _cross(first: tuple[float, float, float], second: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def triangle_mesh_metrics(
    triangles: list[tuple[tuple[float, float, float], ...]],
    *,
    label: str,
) -> dict[str, Any]:
    """Prouve fermeture manifold et orientation cohérente d'un maillage STL."""

    require(triangles, f"empty_stl:{label}")
    parent = list(range(len(triangles)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first: int, second: int) -> None:
        left, right = find(first), find(second)
        if left != right:
            parent[right] = left

    def vertex_key(vertex: tuple[float, float, float]) -> tuple[int, int, int]:
        require(all(math.isfinite(value) for value in vertex), f"nonfinite_stl_vertex:{label}")
        return tuple(round(value * 1_000_000.0) for value in vertex)

    edge_incidence: dict[
        tuple[tuple[int, int, int], tuple[int, int, int]],
        list[tuple[int, int]],
    ] = {}
    signed_volumes: list[float] = []
    coordinates: list[tuple[float, float, float]] = []
    for triangle_index, triangle in enumerate(triangles):
        keys = [vertex_key(vertex) for vertex in triangle]
        require(len(set(keys)) == 3, f"degenerate_stl_triangle:{label}:{triangle_index}")
        coordinates.extend(triangle)
        for first, second in ((0, 1), (1, 2), (2, 0)):
            edge = tuple(sorted((keys[first], keys[second])))
            direction = 1 if (keys[first], keys[second]) == edge else -1
            edge_incidence.setdefault(edge, []).append((triangle_index, direction))
        cross = _cross(triangle[1], triangle[2])
        signed_volumes.append(sum(triangle[0][axis] * cross[axis] for axis in range(3)) / 6.0)

    for edge, incidences in edge_incidence.items():
        require(
            len(incidences) == 2,
            f"stl_non_manifold_edge:{label}:{edge}:incidence={len(incidences)}",
        )
        require(
            incidences[0][1] == -incidences[1][1],
            f"stl_inconsistent_edge_orientation:{label}:{edge}",
        )
        union(incidences[0][0], incidences[1][0])

    component_volumes: dict[int, float] = {}
    for triangle_index, volume in enumerate(signed_volumes):
        root = find(triangle_index)
        component_volumes[root] = component_volumes.get(root, 0.0) + volume
    signed_component_volumes = [component_volumes[root] for root in sorted(component_volumes)]
    require(
        all(value > 0.0 for value in signed_component_volumes),
        f"stl_inward_oriented_component:{label}",
    )
    manifold_closed = bool(edge_incidence) and all(len(value) == 2 for value in edge_incidence.values())
    consistently_oriented = all(
        value[0][1] == -value[1][1]
        for value in edge_incidence.values()
    )
    outward_oriented = bool(signed_component_volumes) and all(
        value > 0.0 for value in signed_component_volumes
    )
    return {
        "valid": manifold_closed and consistently_oriented and outward_oriented,
        "manifold_closed": manifold_closed,
        "consistently_oriented": consistently_oriented,
        "outward_oriented": outward_oriented,
        "edge_count": len(edge_incidence),
        "solid_count": len(component_volumes),
        "all_solids_positive_volume": outward_oriented,
        "volume_mm3": sum(signed_component_volumes),
        "bounds_min_mm": [min(vertex[axis] for vertex in coordinates) for axis in range(3)],
        "bounds_max_mm": [max(vertex[axis] for vertex in coordinates) for axis in range(3)],
    }


def stl_metrics(path: Path) -> dict[str, Any]:
    """Rouvre le STL puis prouve ses propriétés topologiques et métriques."""

    from build123d import import_stl

    reopened = import_stl(path)
    # ``import_stl`` retourne une face triangulée de référence, pas un BRep
    # cousu; sa validité est donc prouvée par les incidences du maillage.
    require(reopened is not None, f"stl_reopen_failed:{path.name}")
    return triangle_mesh_metrics(_stl_triangles(path), label=path.name)


def compare_metrics(
    actual: dict[str, Any],
    expected: dict[str, Any],
    *,
    label: str,
    volume_rel_tolerance: float,
    volume_abs_tolerance_mm3: float,
    bounds_abs_tolerance_mm: float,
) -> None:
    require(actual.get("valid") is True, f"invalid_reopened_metrics:{label}")
    require(actual.get("all_solids_positive_volume") is True, f"nonpositive_reopened_volume:{label}")
    require(actual.get("solid_count") == expected.get("solid_count"), f"solid_count_mismatch:{label}")
    actual_volume = finite_number(actual.get("volume_mm3"), f"invalid_volume:{label}")
    expected_volume = finite_number(expected.get("volume_mm3"), f"invalid_expected_volume:{label}")
    require(
        math.isclose(
            actual_volume,
            expected_volume,
            rel_tol=volume_rel_tolerance,
            abs_tol=volume_abs_tolerance_mm3,
        ),
        f"volume_mismatch:{label}:expected={expected_volume}:actual={actual_volume}",
    )
    for bound_name in ("bounds_min_mm", "bounds_max_mm"):
        actual_bound = actual.get(bound_name)
        expected_bound = expected.get(bound_name)
        require(
            isinstance(actual_bound, list)
            and isinstance(expected_bound, list)
            and len(actual_bound) == len(expected_bound) == 3,
            f"invalid_bounds:{label}:{bound_name}",
        )
        for axis, (actual_value, expected_value) in enumerate(zip(actual_bound, expected_bound)):
            difference = abs(
                finite_number(actual_value, f"invalid_bound:{label}:{bound_name}:{axis}")
                - finite_number(expected_value, f"invalid_expected_bound:{label}:{bound_name}:{axis}")
            )
            require(
                difference <= bounds_abs_tolerance_mm,
                f"bounds_mismatch:{label}:{bound_name}:{axis}:difference={difference}",
            )


def verify_geometry_checks(report: dict[str, Any]) -> None:
    checks = report.get("geometry_checks")
    require(isinstance(checks, dict), "geometry_checks_object_required")
    require(set(checks) == EXPECTED_GEOMETRY_CHECK_KEYS, "geometry_checks_schema_mismatch")
    for key in (
        "minimum_ligament_mm",
        "bolt_hole_cutter_body_intersection_mm3",
        "bolt_hole_cutter_cap_intersection_mm3",
        "oil_channel_cutter_body_intersection_mm3",
        "spotface_cutter_minimum_intersection_mm3",
        "oil_channel_cutter_bearing_upper_intersection_mm3",
        "oil_channel_cutter_bearing_lower_intersection_mm3",
        "oil_channel_cutter_bushing_intersection_mm3",
        "oil_channel_big_end_bore_opening_mm3",
        "oil_channel_small_end_bore_opening_mm3",
        "oil_channel_big_end_outer_exit_probe_mm3",
    ):
        require(finite_number(checks.get(key), f"invalid_geometry_check:{key}") > 0.0, f"geometry_check_not_positive:{key}")
    for key in (
        "unintended_fastener_interference_mm3",
        "spotface_cutter_maximum_depth_delta_mm",
        "bearing_cap_split_gap_delta_mm",
        "oil_channel_big_end_outer_exit_depth_delta_mm",
    ):
        residual = finite_number(checks.get(key), f"invalid_geometry_check:{key}")
        require(
            abs(residual) <= INTERFERENCE_ABS_TOLERANCE_MM3,
            f"geometry_check_residual_nonzero:{key}:{residual}",
        )
    for key in (
        "spotface_post_subtraction_maximum_residual_mm3",
        "oil_channel_post_subtraction_maximum_residual_mm3",
    ):
        residual = finite_number(checks.get(key), f"invalid_geometry_check:{key}")
        require(
            abs(residual) <= BOOLEAN_RESIDUAL_ABS_TOLERANCE_MM3,
            f"geometry_check_boolean_residual:{key}:{residual}",
        )
    component_count = checks.get("oil_channel_connected_component_count")
    require(
        type(component_count) is int and component_count == 1,
        "oil_channel_must_be_one_connected_component",
    )


def expected_relative_files(contract: dict[str, Any]) -> set[Path]:
    shape_ids = contract["output_policy"]["expected_shape_ids"]
    files = {Path("geometry-report.json")}
    files.update(Path("step") / f"{shape_id}.step" for shape_id in shape_ids)
    files.update(Path("stl") / f"{shape_id}-display-only.stl" for shape_id in shape_ids)
    return files


def verify_output(output: Path, contract_path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    require(output.is_dir() and not output.is_symlink(), f"output_directory_required:{output}")
    expected = expected_relative_files(contract)
    actual: set[Path] = set()
    for candidate in output.rglob("*"):
        require(not candidate.is_symlink(), f"output_symlink_not_allowed:{candidate}")
        if candidate.is_file():
            actual.add(candidate.relative_to(output))
    require(actual == expected, f"output_file_set_mismatch:expected={sorted(map(str, expected))}:actual={sorted(map(str, actual))}")

    report_path = tracked_output_file(output, Path("geometry-report.json"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    require(isinstance(report, dict), "geometry_report_object_required")
    require(report.get("phase") == "F44", "report_phase_mismatch")
    require(
        report.get("status") == "display_only_single_connecting_rod_geometry_built_pair_topology_blocked",
        "report_status_mismatch",
    )
    metadata = report.get("metadata", {})
    require(metadata.get("display_only") is True, "display_only_metadata_required")
    for key in (
        "physical_joint_enabled",
        "physics_enabled",
        "simulation_result",
        "manufacturing_geometry",
        "power_evidence",
    ):
        require(metadata.get(key) is False, f"report_metadata_must_be_false:{key}")
    require(report.get("physics_scene_authored") is False, "physics_scene_must_remain_absent")
    require(report.get("paired_rod_assembly_exported") is False, "paired_rod_assembly_must_remain_absent")
    require(report.get("property_assignment_intent") == "skip", "property_assignment_must_be_skipped")
    require(report.get("contract_path") == str(CONTRACT_RELATIVE_PATH), "report_contract_path_mismatch")
    require(report.get("contract_sha256") == sha256(contract_path), "report_contract_sha256_mismatch")
    expected_runtime = {
        "image_ref": f"{CAD_RUNTIME_IMAGE_REPOSITORY}@{CAD_RUNTIME_IMAGE_DIGEST}",
        "digest": CAD_RUNTIME_IMAGE_DIGEST,
    }
    require(report.get("cad_runtime_provenance") == expected_runtime, "report_cad_runtime_provenance_mismatch")
    expected_sources = source_provenance(contract_path.parents[2], contract_path)
    require(report.get("source_provenance") == expected_sources, "report_source_provenance_mismatch")
    require(report.get("release_gates") == contract["release_gates"], "report_release_gates_mismatch")
    require(all(value is False for value in report["release_gates"].values()), "report_release_gate_open")
    verify_geometry_checks(report)

    shape_ids = contract["output_policy"]["expected_shape_ids"]
    exports = report.get("exports")
    require(isinstance(exports, dict) and list(exports) == shape_ids, "report_export_ids_mismatch")
    from build123d import import_step

    stl_bounds_tolerance = max(
        finite_number(
            contract["parameter_register"]["stl_linear_tolerance_mm"]["value"],
            "invalid_stl_linear_tolerance",
        )
        * STL_BOUNDS_TOLERANCE_FACTOR,
        1e-6,
    )
    for shape_id in shape_ids:
        record = exports[shape_id]
        require(isinstance(record, dict), f"report_export_record_required:{shape_id}")
        step_relative = Path("step") / f"{shape_id}.step"
        stl_relative = Path("stl") / f"{shape_id}-display-only.stl"
        require(record.get("step") == str(step_relative), f"report_step_path_mismatch:{shape_id}")
        require(record.get("stl") == str(stl_relative), f"report_stl_path_mismatch:{shape_id}")
        step = tracked_output_file(output, step_relative)
        stl = tracked_output_file(output, stl_relative)
        require(step.stat().st_size > 0 and stl.stat().st_size > 0, f"empty_cad_file:{shape_id}")
        require(step.read_bytes().startswith(b"ISO-10303-21;"), f"invalid_step_header:{shape_id}")
        require(record.get("step_sha256") == sha256(step), f"step_sha256_mismatch:{shape_id}")
        require(record.get("stl_sha256") == sha256(stl), f"stl_sha256_mismatch:{shape_id}")
        authored = record.get("authored_metrics", {})
        created = record.get("created_metrics", {})
        canonical = record.get("canonical_metrics", {})
        reported_step = record.get("roundtrip_metrics", {})
        require(
            all(isinstance(metrics, dict) for metrics in (authored, created, canonical, reported_step)),
            f"invalid_shape_metrics:{shape_id}",
        )
        require(
            all(metrics.get("valid") is True for metrics in (authored, created, canonical, reported_step)),
            f"invalid_shape_metrics:{shape_id}",
        )
        require(
            all(
                metrics.get("all_solids_positive_volume") is True
                for metrics in (authored, created, canonical, reported_step)
            ),
            f"nonpositive_shape_volume:{shape_id}",
        )
        require(isinstance(record.get("clean_export_audit"), dict), f"clean_export_audit_required:{shape_id}")
        require(isinstance(record.get("canonicalization_audit"), dict), f"canonicalization_audit_required:{shape_id}")
        require(isinstance(record.get("roundtrip_audit"), dict), f"roundtrip_audit_required:{shape_id}")
        compare_metrics(
            created,
            authored,
            label=f"authored-to-cleaned:{shape_id}",
            volume_rel_tolerance=CLEAN_EXPORT_VOLUME_REL_TOLERANCE,
            volume_abs_tolerance_mm3=STEP_VOLUME_ABS_TOLERANCE_MM3,
            bounds_abs_tolerance_mm=CLEAN_EXPORT_BOUNDS_ABS_TOLERANCE_MM,
        )
        compare_metrics(
            canonical,
            created,
            label=f"cleaned-to-canonical:{shape_id}",
            volume_rel_tolerance=CANONICAL_VOLUME_REL_TOLERANCE,
            volume_abs_tolerance_mm3=STEP_VOLUME_ABS_TOLERANCE_MM3,
            bounds_abs_tolerance_mm=CANONICAL_BOUNDS_ABS_TOLERANCE_MM,
        )
        compare_metrics(
            reported_step,
            canonical,
            label=f"reported-step:{shape_id}",
            volume_rel_tolerance=STEP_VOLUME_REL_TOLERANCE,
            volume_abs_tolerance_mm3=STEP_VOLUME_ABS_TOLERANCE_MM3,
            bounds_abs_tolerance_mm=STEP_BOUNDS_ABS_TOLERANCE_MM,
        )
        reopened_step = shape_metrics(import_step(step))
        compare_metrics(
            reopened_step,
            canonical,
            label=f"reopened-step:{shape_id}",
            volume_rel_tolerance=STEP_VOLUME_REL_TOLERANCE,
            volume_abs_tolerance_mm3=STEP_VOLUME_ABS_TOLERANCE_MM3,
            bounds_abs_tolerance_mm=STEP_BOUNDS_ABS_TOLERANCE_MM,
        )
        reopened_stl = stl_metrics(stl)
        require(reopened_stl.get("manifold_closed") is True, f"stl_not_closed_manifold:{shape_id}")
        require(reopened_stl.get("consistently_oriented") is True, f"stl_orientation_mismatch:{shape_id}")
        require(reopened_stl.get("outward_oriented") is True, f"stl_inward_orientation:{shape_id}")
        compare_metrics(
            reopened_stl,
            canonical,
            label=f"reopened-stl:{shape_id}",
            volume_rel_tolerance=STL_VOLUME_REL_TOLERANCE,
            volume_abs_tolerance_mm3=STL_VOLUME_ABS_TOLERANCE_MM3,
            bounds_abs_tolerance_mm=stl_bounds_tolerance,
        )

    require(len(list((output / "step").glob("*.step"))) == contract["output_policy"]["expected_step_count"], "step_count_mismatch")
    require(len(list((output / "stl").glob("*.stl"))) == contract["output_policy"]["expected_stl_count"], "stl_count_mismatch")
    return {
        "status": "F44_DOCKER_CAD_SMOKE_OK",
        "step_count": contract["output_policy"]["expected_step_count"],
        "stl_count": contract["output_policy"]["expected_stl_count"],
        "report_sha256": sha256(report_path),
        "display_only": True,
        "physics_enabled": False,
        "paired_rod_assembly_exported": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    contract_path = args.contract.resolve()
    output = args.output.resolve()
    errors = validate(root, contract_path)
    if errors:
        for error in errors:
            print(f"F44 Docker CAD smoke contract error: {error}", file=sys.stderr)
        return 1
    contract = load_contract(contract_path)
    created = False
    try:
        generate(root, contract_path, contract, output)
        created = True
        result = verify_output(output, contract_path, contract)
    except Exception as exc:
        if created and output.is_dir() and not output.is_symlink() and output.parent == (root / "work").resolve():
            shutil.rmtree(output)
        print(f"F44 Docker CAD smoke failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
