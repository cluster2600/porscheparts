#!/usr/bin/env python3
"""Verifie le rapport CalculiX F0 sans reutiliser les sorties brutes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


EXPECTED_PART = "993-ENG-PISTON-CP1-GALLERY-F0-0001"
EXPECTED_TWIN = "TWIN-993-M64-60-PISTON-GALLERY-F0"
EXPECTED_IMAGE_ID = (
    "sha256:22e5ea95954ede922b9666b74e0db1c7fdc34667abc2254ab37002ed4d90996b"
)
EXPECTED_MESHES = [5.0, 3.5, 2.5]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate_json_key:{key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"report_must_be_regular_file:{path}")
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
    if not isinstance(value, dict):
        raise ValueError("report_root_must_be_object")
    return value


def close(actual: float, expected: float, tolerance: float = 1.0e-9) -> None:
    if not math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance):
        raise ValueError(f"value_mismatch:{actual}:{expected}")


def finite_positive(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"not_numeric:{name}")
    converted = float(value)
    if not math.isfinite(converted) or converted <= 0.0:
        raise ValueError(f"not_finite_positive:{name}")
    return converted


def verify(root: Path, report_path: Path) -> dict[str, object]:
    report = load_json(report_path)
    if report.get("part_id") != EXPECTED_PART or report.get("twin_id") != EXPECTED_TWIN:
        raise ValueError("wrong_identity")
    if report.get("status") != "f0_real_calculix_six_case_screen_complete_no_design_selected":
        raise ValueError("wrong_status")

    inputs = report["inputs"]
    runner = root / inputs["runner_repository_path"]
    step = root / inputs["step_repository_path"]
    for path in (runner, step):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"input_must_be_regular:{path}")
    if sha256(runner) != inputs["runner_sha256"]:
        raise ValueError("runner_hash_mismatch")
    if sha256(step) != inputs["step_sha256"]:
        raise ValueError("step_hash_mismatch")

    loads = inputs["synthetic_loads"]
    area = math.pi * 100.0**2 / 4.0
    gas = 12.0 * area
    omega = 2.0 * math.pi * 6720.0 / 60.0
    acceleration = 0.0764 / 2.0 * omega**2 * (1.0 + (0.0764 / 2.0) / 0.127)
    inertia = (681.32 + 140.0) / 1000.0 * acceleration
    close(float(loads["piston_area_mm2"]), area)
    close(float(loads["gas_force_n"]), gas)
    close(float(loads["tdc_acceleration_m_s2"]), acceleration)
    close(float(loads["inertia_force_n"]), inertia)
    close(float(loads["conservative_axial_force_n"]), gas + inertia)

    solver = report["solver"]
    if solver["runtime_image_id"] != EXPECTED_IMAGE_ID:
        raise ValueError("wrong_runtime_image_id")
    if "Version 2.21" not in solver["calculix_version_output"]:
        raise ValueError("wrong_calculix_version")
    if solver["gmsh_version"] != "4.12.1" or solver["execution_count"] != 6:
        raise ValueError("wrong_solver_execution_contract")

    cases = report["cases"]
    if [case["mesh"]["mesh_size_mm"] for case in cases] != EXPECTED_MESHES:
        raise ValueError("wrong_mesh_sequence")
    nodes = [case["mesh"]["nodes"] for case in cases]
    elements = [case["mesh"]["quadratic_tetrahedra"] for case in cases]
    if nodes != sorted(nodes) or len(set(nodes)) != 3:
        raise ValueError("node_counts_not_strictly_increasing")
    if elements != sorted(elements) or len(set(elements)) != 3:
        raise ValueError("element_counts_not_strictly_increasing")

    for case in cases:
        mesh = case["mesh"]
        finite_positive(mesh["boundary_nodes"], "boundary_nodes")
        for name in ("CROWN_LOAD", "GALLERY_SINK", "PIN_BORE", "SKIRT_SINK"):
            finite_positive(mesh["boundary_set_counts"][name], name)
        for lane in ("cold_linear_static", "hot_sequential_thermomechanical"):
            result = case[lane]
            if result["return_code"] != 0:
                raise ValueError(f"nonzero_solver_receipt:{lane}")
            expected_names = {
                "piston-cold.inp",
                "piston-cold.dat",
                "piston-cold.frd",
                "piston-cold.log",
            } if lane == "cold_linear_static" else {
                "piston-hot.inp",
                "piston-hot.dat",
                "piston-hot.frd",
                "piston-hot.log",
            }
            if set(result["artifacts"]) != expected_names:
                raise ValueError(f"wrong_artifact_manifest:{lane}")
            for artifact in result["artifacts"].values():
                finite_positive(artifact["bytes"], "artifact_bytes")
                digest = artifact["sha256"]
                if not isinstance(digest, str) or len(digest) != 64:
                    raise ValueError("invalid_artifact_digest")
                int(digest, 16)
            for group in ("von_mises_mpa", "displacement_mm"):
                for name, value in result[group].items():
                    finite_positive(value, f"{lane}:{group}:{name}")
            if lane == "hot_sequential_thermomechanical":
                temperatures = result["temperature_c"]
                for name, value in temperatures.items():
                    finite_positive(value, f"temperature:{name}")
                if not (
                    temperatures["minimum"]
                    <= temperatures["p50"]
                    <= temperatures["p95"]
                    <= temperatures["maximum"]
                ):
                    raise ValueError("temperature_percentiles_not_ordered")

    previous, finest = cases[-2], cases[-1]
    comparisons = report["grid_comparison_fine_vs_previous"]
    quantities = {
        "cold_p95_stress_relative_change": (
            finest["cold_linear_static"]["von_mises_mpa"]["p95"],
            previous["cold_linear_static"]["von_mises_mpa"]["p95"],
        ),
        "hot_p95_stress_relative_change": (
            finest["hot_sequential_thermomechanical"]["von_mises_mpa"]["p95"],
            previous["hot_sequential_thermomechanical"]["von_mises_mpa"]["p95"],
        ),
        "hot_maximum_temperature_relative_change": (
            finest["hot_sequential_thermomechanical"]["temperature_c"]["maximum"],
            previous["hot_sequential_thermomechanical"]["temperature_c"]["maximum"],
        ),
    }
    for name, (current, prior) in quantities.items():
        expected = abs(current - prior) / abs(current)
        close(float(comparisons[name]), expected)

    numerical = report["numerical_gates"]
    if set(numerical) != {
        "six_solver_executions_complete",
        "cold_p95_grid_change_below_10_percent",
        "hot_p95_grid_change_below_10_percent",
        "hot_temperature_grid_change_below_10_percent",
    } or not all(value is True for value in numerical.values()):
        raise ValueError("numerical_gates_not_all_true")

    strength = report["ambient_reference_strength_ratios"]
    cold_p95 = finest["cold_linear_static"]["von_mises_mpa"]["p95"]
    cold_max = finest["cold_linear_static"]["von_mises_mpa"]["maximum"]
    hot_p95 = finest["hot_sequential_thermomechanical"]["von_mises_mpa"]["p95"]
    hot_max = finest["hot_sequential_thermomechanical"]["von_mises_mpa"]["maximum"]
    close(float(strength["cold_p95_yield_to_stress"]), 297.0 / cold_p95)
    close(float(strength["cold_maximum_yield_to_stress"]), 297.0 / cold_max)
    close(float(strength["hot_p95_yield_to_stress"]), 297.0 / hot_p95)
    close(float(strength["hot_maximum_yield_to_stress"]), 297.0 / hot_max)
    if strength["hot_p95_yield_to_stress"] >= 1.0:
        raise ValueError("expected_current_hot_screen_failure_missing")

    fatigue = report["fatigue_proxy"]
    close(float(fatigue["shaft_revolutions_at_100h"]), 40_320_000.0)
    close(float(fatigue["combustion_events_per_cylinder_at_100h"]), 20_160_000.0)
    if fatigue["cp1_hot_sn_curve_available"] is not False or fatigue["predicted_life_cycles"] is not None:
        raise ValueError("fatigue_life_must_remain_unavailable")

    if not report["engineering_gates"] or any(report["engineering_gates"].values()):
        raise ValueError("engineering_gates_must_all_be_false")
    if report["selected_variant"] is not None:
        raise ValueError("variant_must_not_be_selected")
    for name in ("manufacturing_authorized", "engine_operation_authorized", "release_authorized"):
        if report[name] is not False:
            raise ValueError(f"release_gate_open:{name}")

    return {
        "status": "PASS",
        "solver_executions": solver["execution_count"],
        "finest_nodes": nodes[-1],
        "finest_quadratic_tetrahedra": elements[-1],
        "finest_cold_p95_mpa": cold_p95,
        "finest_hot_p95_mpa": hot_p95,
        "finest_hot_maximum_c": finest["hot_sequential_thermomechanical"]["temperature_c"]["maximum"],
        "hot_ambient_reference_ratio": strength["hot_p95_yield_to_stress"],
        "release_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "twins/993-m64-60-piston-gallery-f0/evidence/calculix-f0/calculix-thermomechanical-screen.json"
        ),
    )
    args = parser.parse_args()
    result = verify(args.root.resolve(), args.report.resolve())
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
