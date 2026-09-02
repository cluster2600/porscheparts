#!/usr/bin/env python3
"""Calcule les métriques analytiques et agrège la répétabilité du benchmark F25."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from generate_cases import load_contract  # noqa: E402


FLOAT_PATTERN = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
NONUNIFORM_VECTOR_RE = re.compile(
    r"internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;",
    re.DOTALL,
)
UNIFORM_VECTOR_RE = re.compile(
    rf"internalField\s+uniform\s+\(({FLOAT_PATTERN})\s+({FLOAT_PATTERN})\s+({FLOAT_PATTERN})\)\s*;"
)
VECTOR_RE = re.compile(
    rf"\(({FLOAT_PATTERN})\s+({FLOAT_PATTERN})\s+({FLOAT_PATTERN})\)"
)
RESIDUAL_RE = re.compile(
    rf"Solving for (?P<field>[^,]+), Initial residual = (?P<initial>{FLOAT_PATTERN}), "
    rf"Final residual = (?P<final>{FLOAT_PATTERN}), No Iterations (?P<iterations>\d+)"
)
CONTINUITY_RE = re.compile(
    rf"time step continuity errors : sum local = (?P<local>{FLOAT_PATTERN}), "
    rf"global = (?P<global>{FLOAT_PATTERN}), cumulative = (?P<cumulative>{FLOAT_PATTERN})"
)


class EvidenceError(RuntimeError):
    """Une preuve d'exécution attendue est absente ou illisible."""


def read_vector_field(path: Path, expected_count: int | None = None) -> list[tuple[float, float, float]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    nonuniform = NONUNIFORM_VECTOR_RE.search(text)
    if nonuniform:
        declared_count = int(nonuniform.group(1))
        vectors = [tuple(float(value) for value in match) for match in VECTOR_RE.findall(nonuniform.group(2))]
        if len(vectors) != declared_count:
            raise EvidenceError(
                f"vector_count_mismatch:{path}:{declared_count}:{len(vectors)}"
            )
        return vectors

    uniform = UNIFORM_VECTOR_RE.search(text)
    if uniform and expected_count is not None:
        value = tuple(float(component) for component in uniform.groups())
        return [value] * expected_count

    raise EvidenceError(f"unsupported_internal_vector_field:{path}")


def latest_time_dir(case_dir: Path) -> Path:
    candidates: list[tuple[float, Path]] = []
    for child in case_dir.iterdir():
        if not child.is_dir() or child.name == "0":
            continue
        try:
            candidates.append((float(child.name), child))
        except ValueError:
            continue
    if not candidates:
        raise EvidenceError(f"no_solution_time_directory:{case_dir}")
    return max(candidates, key=lambda item: item[0])[1]


def read_surface_sum(case_dir: Path, function_name: str) -> float:
    function_dir = case_dir / "postProcessing" / function_name
    data_files = sorted(function_dir.glob("*/surfaceFieldValue.dat"))
    if not data_files:
        raise EvidenceError(f"missing_surface_field_value:{function_name}:{case_dir}")

    rows: list[list[str]] = []
    for data_file in data_files:
        for line in data_file.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                rows.append(stripped.split())
    if not rows:
        raise EvidenceError(f"empty_surface_field_value:{function_name}:{case_dir}")
    return float(rows[-1][-1])


def read_check_mesh(case_dir: Path, expected_cells: int) -> dict[str, Any]:
    path = case_dir / "log.checkMesh"
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r"^\s*cells:\s+(\d+)\s*$", text, flags=re.MULTILINE)
    actual_cells = int(matches[-1]) if matches else None
    return {
        "passed": "Mesh OK." in text and "FOAM FATAL ERROR" not in text,
        "expected_cells": expected_cells,
        "actual_cells": actual_cells,
        "cell_count_matches": actual_cells == expected_cells,
        "log": "log.checkMesh",
    }


def read_solver_log(case_dir: Path) -> dict[str, Any]:
    path = case_dir / "log.simpleFoam"
    text = path.read_text(encoding="utf-8", errors="replace")
    residuals: dict[str, dict[str, float | int]] = {}
    for match in RESIDUAL_RE.finditer(text):
        residuals[match.group("field")] = {
            "initial": float(match.group("initial")),
            "final": float(match.group("final")),
            "iterations": int(match.group("iterations")),
        }
    continuity_matches = list(CONTINUITY_RE.finditer(text))
    continuity = None
    if continuity_matches:
        last = continuity_matches[-1]
        continuity = {
            "semantics": "openfoam_delta_t_times_volume_weighted_mean_abs_div_phi_dimensionless",
            "local_sum": float(last.group("local")),
            "global": float(last.group("global")),
            "cumulative": float(last.group("cumulative")),
        }
    return {
        "completed": "\nEnd\n" in text and "FOAM FATAL ERROR" not in text,
        "openfoam_13_observed": (
            "Version:  13" in text and "Build  : 13-" in text
        ),
        "simplefoam_delegation_observed": (
            "simpleFoam has been superseded" in text
            and "foamRun -solver incompressibleFluid" in text
        ),
        "last_linear_residuals": residuals,
        "continuity": continuity,
        "log": "log.simpleFoam",
    }


def analytic_velocity(y_m: float, height_m: float, acceleration_m_s2: float, nu_m2_s: float) -> float:
    return acceleration_m_s2 / (2.0 * nu_m2_s) * (
        height_m * height_m / 4.0 - y_m * y_m
    )


def analytic_volumetric_flow(
    height_m: float, depth_m: float, acceleration_m_s2: float, nu_m2_s: float
) -> float:
    return acceleration_m_s2 * depth_m * height_m**3 / (12.0 * nu_m2_s)


def analyze_case(contract: dict[str, Any], case_dir: Path, mesh: dict[str, Any]) -> dict[str, Any]:
    expected_cells = mesh["cells_x"] * mesh["cells_y"] * mesh["cells_z"]
    latest = latest_time_dir(case_dir)
    centres = read_vector_field(latest / "C")
    velocity = read_vector_field(latest / "U", expected_count=len(centres))
    if len(centres) != expected_cells or len(velocity) != expected_cells:
        raise EvidenceError(
            f"solution_cell_count_mismatch:{mesh['id']}:{expected_cells}:{len(centres)}:{len(velocity)}"
        )

    physics = contract["physics"]
    height = float(physics["channel_height_m"])
    depth = float(physics["channel_depth_m"])
    acceleration = float(physics["body_force_x_m_s2"])
    nu = float(physics["kinematic_viscosity_m2_s"])
    rho_ref = float(physics["density_reference_kg_m3"])

    exact_u = [analytic_velocity(point[1], height, acceleration, nu) for point in centres]
    errors = [computed[0] - exact for computed, exact in zip(velocity, exact_u)]
    exact_l2_norm = math.sqrt(sum(value * value for value in exact_u) / len(exact_u))
    exact_linf_norm = max(abs(value) for value in exact_u)
    l2_abs = math.sqrt(sum(value * value for value in errors) / len(errors))
    linf_abs = max(abs(value) for value in errors)
    transverse_abs = max(math.hypot(value[1], value[2]) for value in velocity)

    q_exact = analytic_volumetric_flow(height, depth, acceleration, nu)
    q_cell = sum(value[0] for value in velocity) / len(velocity) * height * depth
    q_min = read_surface_sum(case_dir, "streamwiseMinFlow")
    q_max = read_surface_sum(case_dir, "streamwiseMaxFlow")
    q_patch_mean = (abs(q_min) + abs(q_max)) / 2.0

    return {
        "mesh_id": mesh["id"],
        "cells": {
            "x": mesh["cells_x"],
            "y": mesh["cells_y"],
            "z": mesh["cells_z"],
            "total": expected_cells,
        },
        "mesh_spacing_y_m": height / mesh["cells_y"],
        "latest_time": latest.name,
        "mesh_check": read_check_mesh(case_dir, expected_cells),
        "solver": read_solver_log(case_dir),
        "velocity_error": {
            "sample_count": len(errors),
            "l2_absolute_m_s": l2_abs,
            "l2_relative": l2_abs / exact_l2_norm,
            "linf_absolute_m_s": linf_abs,
            "linf_relative": linf_abs / exact_linf_norm,
            "max_transverse_absolute_m_s": transverse_abs,
        },
        "mass_flow": {
            "density_reference_kg_m3": rho_ref,
            "density_semantics": physics["density_semantics"],
            "analytic_volumetric_m3_s": q_exact,
            "cell_integrated_volumetric_m3_s": q_cell,
            "streamwise_min_outward_volumetric_m3_s": q_min,
            "streamwise_max_outward_volumetric_m3_s": q_max,
            "patch_mean_absolute_volumetric_m3_s": q_patch_mean,
            "analytic_mass_kg_s": rho_ref * q_exact,
            "patch_mean_absolute_mass_kg_s": rho_ref * q_patch_mean,
            "analytic_relative_error": abs(q_patch_mean - q_exact) / q_exact,
            "cell_integrated_relative_error": abs(q_cell - q_exact) / q_exact,
            "cyclic_pair_antisymmetry_relative": abs(q_min + q_max) / q_exact,
        },
        "local_evidence": {
            "cell_centres_field": f"{latest.name}/C",
            "velocity_field": f"{latest.name}/U",
            "postprocess_log": "log.writeCellCentres",
        },
    }


def observed_orders(mesh_metrics: list[dict[str, Any]], metric_key: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for coarse, fine in zip(mesh_metrics, mesh_metrics[1:]):
        coarse_error = float(coarse["velocity_error"][metric_key])
        fine_error = float(fine["velocity_error"][metric_key])
        h_ratio = float(coarse["mesh_spacing_y_m"]) / float(fine["mesh_spacing_y_m"])
        order = None
        if coarse_error > 0.0 and fine_error > 0.0 and h_ratio > 1.0:
            order = math.log(coarse_error / fine_error) / math.log(h_ratio)
        output.append(
            {
                "from": coarse["mesh_id"],
                "to": fine["mesh_id"],
                "refinement_ratio": h_ratio,
                "order": order,
            }
        )
    return output


def evaluate_repeat(contract: dict[str, Any], mesh_metrics: list[dict[str, Any]]) -> list[str]:
    acceptance = contract["acceptance"]
    failures: list[str] = []
    for metric in mesh_metrics:
        mesh_id = metric["mesh_id"]
        if not metric["mesh_check"]["passed"]:
            failures.append(f"mesh_check_failed:{mesh_id}")
        if not metric["mesh_check"]["cell_count_matches"]:
            failures.append(f"mesh_cell_count_mismatch:{mesh_id}")
        if not metric["solver"]["completed"]:
            failures.append(f"solver_incomplete:{mesh_id}")
        if not metric["solver"]["openfoam_13_observed"]:
            failures.append(f"openfoam_13_not_observed:{mesh_id}")
        if not metric["solver"]["simplefoam_delegation_observed"]:
            failures.append(f"simplefoam_delegation_not_observed:{mesh_id}")
        ux_residual = metric["solver"]["last_linear_residuals"].get("Ux")
        if (
            ux_residual is None
            or not math.isfinite(float(ux_residual.get("final", math.nan)))
            or float(ux_residual["final"]) < 0.0
            or float(ux_residual["final"])
            > float(acceptance["ux_linear_solver_final_residual_max"])
        ):
            failures.append(f"linear_solver_residual_exceeded:{mesh_id}:Ux")
        p_residual = metric["solver"]["last_linear_residuals"].get("p")
        if (
            p_residual is None
            or not math.isfinite(float(p_residual.get("final", math.nan)))
            or float(p_residual["final"]) < 0.0
            or float(p_residual["final"])
            > float(acceptance["p_linear_solver_final_residual_max"])
        ):
            failures.append(f"linear_solver_residual_exceeded:{mesh_id}:p")
        cyclic_antisymmetry = float(
            metric["mass_flow"]["cyclic_pair_antisymmetry_relative"]
        )
        if (
            not math.isfinite(cyclic_antisymmetry)
            or cyclic_antisymmetry
            > acceptance["cyclic_pair_antisymmetry_relative_max"]
        ):
            failures.append(f"cyclic_pair_antisymmetry_exceeded:{mesh_id}")
        continuity = metric["solver"].get("continuity")
        continuity_local = (
            math.nan if continuity is None else float(continuity.get("local_sum", math.nan))
        )
        if (
            not math.isfinite(continuity_local)
            or continuity_local > acceptance["continuity_local_sum_max"]
        ):
            failures.append(f"continuity_local_sum_exceeded:{mesh_id}")
        transverse = float(metric["velocity_error"]["max_transverse_absolute_m_s"])
        if not math.isfinite(transverse) or transverse > acceptance["transverse_velocity_abs_max_m_s"]:
            failures.append(f"transverse_velocity_exceeded:{mesh_id}")

    fine = mesh_metrics[-1]
    fine_mass = float(fine["mass_flow"]["analytic_relative_error"])
    fine_l2 = float(fine["velocity_error"]["l2_relative"])
    fine_linf = float(fine["velocity_error"]["linf_relative"])
    if not math.isfinite(fine_mass) or fine_mass > acceptance["fine_mass_flow_relative_error_max"]:
        failures.append("fine_mass_flow_error_exceeded")
    if not math.isfinite(fine_l2) or fine_l2 > acceptance["fine_l2_relative_max"]:
        failures.append("fine_l2_error_exceeded")
    if not math.isfinite(fine_linf) or fine_linf > acceptance["fine_linf_relative_max"]:
        failures.append("fine_linf_error_exceeded")
    return failures


def evaluate_convergence(
    contract: dict[str, Any], convergence: dict[str, list[dict[str, Any]]]
) -> list[str]:
    acceptance = contract["acceptance"]
    failures: list[str] = []
    for norm in ("l2", "linf"):
        pairs = convergence.get(norm, [])
        if len(pairs) != len(contract["meshes"]) - 1:
            failures.append(f"observed_order_pair_count_invalid:{norm}")
            continue
        for pair in pairs:
            order = pair.get("order")
            if (
                order is None
                or not math.isfinite(float(order))
                or float(order) < acceptance["observed_order_min"]
                or float(order) > acceptance["observed_order_max"]
            ):
                failures.append(
                    f"observed_order_out_of_bounds:{norm}:{pair.get('from')}:{pair.get('to')}"
                )
    return failures


def analyze_repeat(
    contract: dict[str, Any], cases_dir: Path, repeat_id: str
) -> dict[str, Any]:
    mesh_metrics = [
        analyze_case(contract, cases_dir / mesh["id"], mesh)
        for mesh in contract["meshes"]
    ]
    convergence = {
        "l2": observed_orders(mesh_metrics, "l2_absolute_m_s"),
        "linf": observed_orders(mesh_metrics, "linf_absolute_m_s"),
    }
    failures = evaluate_repeat(contract, mesh_metrics)
    failures.extend(evaluate_convergence(contract, convergence))

    return {
        "schema_version": "1.0",
        "benchmark_id": contract["benchmark_id"],
        "repeat_id": repeat_id,
        "report_status": "passed" if not failures else "failed",
        "failures": failures,
        "meshes": mesh_metrics,
        "convergence": convergence,
        "gates": contract["gates"],
    }


def repeatability_values(report: dict[str, Any]) -> dict[str, float]:
    values: dict[str, float] = {}

    def add(key: str, value: Any) -> None:
        numeric = float(value)
        if not math.isfinite(numeric):
            raise EvidenceError(f"non_finite_repeatability_metric:{key}")
        values[key] = numeric

    for mesh in report["meshes"]:
        prefix = mesh["mesh_id"]
        add(f"{prefix}.mesh_spacing_y_m", mesh["mesh_spacing_y_m"])
        add(f"{prefix}.mesh_check.passed", mesh["mesh_check"]["passed"])
        add(
            f"{prefix}.mesh_check.cell_count_matches",
            mesh["mesh_check"]["cell_count_matches"],
        )
        add(f"{prefix}.mesh_check.actual_cells", mesh["mesh_check"]["actual_cells"])
        add(f"{prefix}.solver.completed", mesh["solver"]["completed"])
        add(
            f"{prefix}.solver.openfoam_13_observed",
            mesh["solver"]["openfoam_13_observed"],
        )
        add(
            f"{prefix}.solver.simplefoam_delegation_observed",
            mesh["solver"]["simplefoam_delegation_observed"],
        )
        for field in ("Ux", "Uy", "p"):
            residual = mesh["solver"]["last_linear_residuals"][field]
            add(f"{prefix}.solver.{field}.initial", residual["initial"])
            add(f"{prefix}.solver.{field}.final", residual["final"])
            add(f"{prefix}.solver.{field}.iterations", residual["iterations"])
        continuity = mesh["solver"]["continuity"]
        for key in ("local_sum", "global", "cumulative"):
            add(f"{prefix}.solver.continuity.{key}", continuity[key])
        for key in (
            "l2_absolute_m_s",
            "l2_relative",
            "linf_absolute_m_s",
            "linf_relative",
            "max_transverse_absolute_m_s",
        ):
            add(f"{prefix}.velocity_error.{key}", mesh["velocity_error"][key])
        for key in (
            "cell_integrated_volumetric_m3_s",
            "streamwise_min_outward_volumetric_m3_s",
            "streamwise_max_outward_volumetric_m3_s",
            "patch_mean_absolute_volumetric_m3_s",
            "analytic_relative_error",
            "cell_integrated_relative_error",
            "cyclic_pair_antisymmetry_relative",
        ):
            add(f"{prefix}.mass_flow.{key}", mesh["mass_flow"][key])
    for norm in ("l2", "linf"):
        for pair in report["convergence"][norm]:
            add(f"convergence.{norm}.{pair['from']}.{pair['to']}", pair["order"])
    return values


def canonical_metrics_hash(report: dict[str, Any]) -> str:
    encoded = json.dumps(
        repeatability_values(report), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compare_repeats(reports: list[dict[str, Any]]) -> dict[str, Any]:
    baseline = repeatability_values(reports[0])
    maximum_absolute = 0.0
    maximum_relative = 0.0
    worst_key = None
    for report in reports[1:]:
        values = repeatability_values(report)
        if values.keys() != baseline.keys():
            raise EvidenceError("repeatability_metric_keys_differ")
        for key, reference in baseline.items():
            difference = abs(values[key] - reference)
            relative = difference / max(abs(reference), abs(values[key]), 1e-300)
            if difference > maximum_absolute:
                maximum_absolute = difference
                worst_key = key
            maximum_relative = max(maximum_relative, relative)
    hashes = [canonical_metrics_hash(report) for report in reports]
    return {
        "repeat_count": len(reports),
        "canonical_metrics_sha256": hashes,
        "canonical_metrics_identical": len(set(hashes)) == 1,
        "maximum_absolute_difference": maximum_absolute,
        "maximum_relative_difference": maximum_relative,
        "worst_absolute_metric": worst_key,
    }


def validate_repeat_report(
    contract: dict[str, Any], report: dict[str, Any]
) -> tuple[dict[str, Any] | None, list[str]]:
    failures: list[str] = []
    if not isinstance(report, dict):
        return None, ["report_not_an_object"]

    repeat_id = report.get("repeat_id")
    if not isinstance(repeat_id, str) or not repeat_id:
        failures.append("repeat_id_invalid")
    if report.get("schema_version") != "1.0":
        failures.append("repeat_schema_version_invalid")
    if report.get("benchmark_id") != contract["benchmark_id"]:
        failures.append("benchmark_id_mismatch")
    if report.get("gates") != contract["gates"]:
        failures.append("repeat_gates_mismatch")
    if report.get("report_status") != "passed":
        failures.append("repeat_declared_failed")

    meshes = report.get("meshes")
    if not isinstance(meshes, list):
        return None, failures + ["meshes_not_a_list"]
    expected_meshes = contract["meshes"]
    actual_ids = [mesh.get("mesh_id") if isinstance(mesh, dict) else None for mesh in meshes]
    expected_ids = [mesh["id"] for mesh in expected_meshes]
    if actual_ids != expected_ids:
        failures.append("mesh_ids_or_order_invalid")
    if len(meshes) != len(expected_meshes):
        return None, failures + ["mesh_count_invalid"]

    try:
        for metric, expected in zip(meshes, expected_meshes):
            expected_total = (
                expected["cells_x"] * expected["cells_y"] * expected["cells_z"]
            )
            cells = metric["cells"]
            if (
                cells["x"] != expected["cells_x"]
                or cells["y"] != expected["cells_y"]
                or cells["z"] != expected["cells_z"]
                or cells["total"] != expected_total
                or metric["mesh_check"]["actual_cells"] != expected_total
                or metric["mesh_check"]["expected_cells"] != expected_total
            ):
                failures.append(f"mesh_shape_mismatch:{expected['id']}")

        convergence = {
            "l2": observed_orders(meshes, "l2_absolute_m_s"),
            "linf": observed_orders(meshes, "linf_absolute_m_s"),
        }
        failures.extend(evaluate_repeat(contract, meshes))
        failures.extend(evaluate_convergence(contract, convergence))

        normalized = dict(report)
        normalized["convergence"] = convergence
        repeatability_values(normalized)
    except (KeyError, IndexError, TypeError, ValueError, EvidenceError) as error:
        failures.append(f"invalid_repeat_report_shape:{type(error).__name__}:{error}")
        return None, failures
    return normalized, failures


def aggregate_reports(
    contract: dict[str, Any], reports: list[dict[str, Any]], image_metadata: dict[str, Any]
) -> dict[str, Any]:
    failures: list[str] = []
    if len(reports) != contract["repetitions"]:
        failures.append("unexpected_repeat_count")
    if len({report.get("repeat_id") for report in reports if isinstance(report, dict)}) != len(reports):
        failures.append("repeat_ids_must_be_unique")
    normalized_reports: list[dict[str, Any]] = []
    repeat_validation: list[dict[str, Any]] = []
    for index, report in enumerate(reports):
        repeat_id = report.get("repeat_id", f"invalid-{index}") if isinstance(report, dict) else f"invalid-{index}"
        normalized, repeat_failures = validate_repeat_report(contract, report)
        repeat_validation.append(
            {
                "repeat_id": repeat_id,
                "recomputed_status": "passed" if not repeat_failures else "failed",
                "failures": repeat_failures,
            }
        )
        failures.extend(
            f"repeat_validation:{repeat_id}:{failure}"
            for failure in repeat_failures
        )
        if normalized is not None:
            normalized_reports.append(normalized)

    repeatability: dict[str, Any]
    if len(normalized_reports) == len(reports) and normalized_reports:
        try:
            repeatability = compare_repeats(normalized_reports)
        except (KeyError, TypeError, ValueError, EvidenceError) as error:
            failures.append(f"repeatability_invalid:{type(error).__name__}:{error}")
            repeatability = {
                "repeat_count": len(reports),
                "validation_complete": False,
                "canonical_metrics_sha256": [],
                "canonical_metrics_identical": False,
                "maximum_absolute_difference": None,
                "maximum_relative_difference": None,
                "worst_absolute_metric": None,
            }
    else:
        failures.append("repeatability_not_evaluated_invalid_repeat")
        repeatability = {
            "repeat_count": len(reports),
            "validation_complete": False,
            "canonical_metrics_sha256": [],
            "canonical_metrics_identical": False,
            "maximum_absolute_difference": None,
            "maximum_relative_difference": None,
            "worst_absolute_metric": None,
        }
    acceptance = contract["acceptance"]
    if (
        acceptance["repeatability_canonical_metrics_identical_required"]
        and not repeatability["canonical_metrics_identical"]
    ):
        failures.append("repeatability_canonical_metrics_differ")

    expected_image = contract["container"]["image"]
    expected_digest = expected_image.split("@", 1)[1]
    observed_digests = image_metadata.get("repo_digests", [])
    if not any(str(item).endswith(f"@{expected_digest}") for item in observed_digests):
        failures.append("pinned_image_digest_not_observed")
    if image_metadata.get("architecture") != "amd64":
        failures.append("image_architecture_not_amd64")
    if image_metadata.get("os") != "linux":
        failures.append("image_os_not_linux")

    passed = not failures
    return {
        "schema_version": "1.0",
        "benchmark_id": contract["benchmark_id"],
        "milestone": "F25",
        "report_status": "passed" if passed else "failed",
        "scope": contract["scope"],
        "container": {
            "requested_reference": expected_image,
            "observed": image_metadata,
            "requested_command": contract["container"]["requested_command"],
            "resolved_solver": contract["container"]["resolved_solver"],
            "network": contract["container"]["network"],
            "confinement": contract["container"]["confinement"],
        },
        "repeat_reports": [
            f"{report.get('repeat_id', f'invalid-{index}')}/metrics.json"
            if isinstance(report, dict)
            else f"invalid-{index}/metrics.json"
            for index, report in enumerate(reports)
        ],
        "repeat_validation": repeat_validation,
        "repeatability": repeatability,
        "convergence": (
            normalized_reports[0]["convergence"]
            if normalized_reports
            else {"l2": [], "linf": []}
        ),
        "finest_mesh_metrics": (
            normalized_reports[0]["meshes"][-1] if normalized_reports else None
        ),
        "claims": {
            "openfoam_tool_solver_benchmark_verified": passed,
            "porsche_917_engine_simulation_verified": False,
            "physicsnemo_dataset_sample_produced": False,
            "engine_design_verified": False,
            "fabrication_authorized": False,
            "vehicle_use_authorized": False,
        },
        "gates": contract["gates"],
        "failures": failures,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"output_already_exists:{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze")
    analyze.add_argument("--contract", required=True, type=Path)
    analyze.add_argument("--cases", required=True, type=Path)
    analyze.add_argument("--repeat-id", required=True)
    analyze.add_argument("--output", required=True, type=Path)

    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("--contract", required=True, type=Path)
    aggregate.add_argument("--repeat-report", required=True, action="append", type=Path)
    aggregate.add_argument("--image-metadata", required=True, type=Path)
    aggregate.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = load_contract(args.contract)
    if args.command == "analyze":
        report = analyze_repeat(contract, args.cases, args.repeat_id)
    else:
        reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.repeat_report]
        image_metadata = json.loads(args.image_metadata.read_text(encoding="utf-8"))
        report = aggregate_reports(contract, reports, image_metadata)
    write_json(args.output, report)
    print(json.dumps({"status": report["report_status"], "output": args.output.name}))
    return 0 if report["report_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
