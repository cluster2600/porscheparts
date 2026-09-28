#!/usr/bin/env python3
"""Audit the evidence needed for a physics-backed cylinder-head twin.

The audit deliberately distinguishes generated geometry from validated
fidelity. Missing engineering inputs produce a useful blocked report rather
than guessed material properties, loads, boundary conditions, or release
claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def evidence_ready(reference: Any, base: Path) -> tuple[bool, str]:
    if not isinstance(reference, dict):
        return False, "missing evidence reference"
    raw_path = reference.get("path")
    expected = reference.get("sha256")
    if not is_present(raw_path) or not is_present(expected):
        return False, "evidence path and SHA-256 are required"
    path = Path(str(raw_path)).expanduser()
    if not path.is_absolute():
        path = (base / path).resolve()
    if not path.is_file():
        return False, f"evidence file not found: {path}"
    actual = sha256(path)
    if actual.lower() != str(expected).lower():
        return False, f"evidence SHA-256 mismatch: {path}"
    return True, f"verified: {path}"


def all_evidence_ready(items: list[Any], base: Path) -> tuple[bool, list[str]]:
    findings = [evidence_ready(item, base) for item in items]
    return all(item[0] for item in findings), [item[1] for item in findings]


def evaluate_scale(data: dict[str, Any], base: Path) -> tuple[bool, dict[str, Any]]:
    declared = data.get("mm_per_obj_unit")
    controls = data.get("controls", [])
    maximum_spread = data.get("maximum_relative_spread")
    if not is_positive_number(declared) or not is_positive_number(maximum_spread):
        return False, {"reason": "positive scale and spread threshold are required"}
    if len(controls) < 3:
        return False, {"reason": "at least three independent physical controls are required"}

    factors: list[float] = []
    evidence_findings: list[str] = []
    for control in controls:
        scan = control.get("scan_obj_units")
        physical = control.get("physical_mm")
        uncertainty = control.get("uncertainty_mm")
        if not all(is_positive_number(value) for value in (scan, physical, uncertainty)):
            return False, {"reason": f"incomplete physical control: {control.get('feature_id')}"}
        ready, finding = evidence_ready(control.get("evidence"), base)
        evidence_findings.append(finding)
        if not ready:
            return False, {"reason": finding, "evidence": evidence_findings}
        factors.append(float(physical) / float(scan))

    mean_factor = sum(factors) / len(factors)
    relative_spread = max(abs(value - mean_factor) / mean_factor for value in factors)
    declared_error = abs(float(declared) - mean_factor) / mean_factor
    passed = relative_spread <= float(maximum_spread) and declared_error <= float(maximum_spread)
    return passed, {
        "control_count": len(controls),
        "mean_mm_per_obj_unit": mean_factor,
        "declared_mm_per_obj_unit": declared,
        "maximum_relative_spread": relative_spread,
        "acceptance_maximum_relative_spread": maximum_spread,
        "evidence": evidence_findings,
        "reason": None if passed else "scale controls or declared scale are mutually inconsistent",
    }


def named_engine_ready(data: dict[str, Any], base: Path) -> tuple[bool, dict[str, Any]]:
    required = (
        "vehicle",
        "engine_code",
        "variant",
        "aspiration",
        "displacement_cm3",
        "compression_ratio",
        "rpm_limit",
    )
    missing = [key for key in required if not is_present(data.get(key))]
    target_evidence, finding = evidence_ready(data.get("power_and_torque_target_evidence"), base)
    if not target_evidence:
        missing.append("power_and_torque_target_evidence")
    return not missing, {"missing": missing, "evidence": finding}


def internal_geometry_ready(data: dict[str, Any], base: Path) -> tuple[bool, dict[str, Any]]:
    volume_ready, finding = evidence_ready(data.get("ct_volume"), base)
    required = set(data.get("required_domains", []))
    actual = set(data.get("segmented_domains", []))
    missing_domains = sorted(required - actual)
    passed = (
        volume_ready
        and is_positive_number(data.get("voxel_size_mm"))
        and is_present(data.get("resolution_justification"))
        and not missing_domains
    )
    return passed, {
        "ct_volume": finding,
        "missing_domains": missing_domains,
        "voxel_size_mm": data.get("voxel_size_mm"),
        "resolution_justification_present": is_present(data.get("resolution_justification")),
    }


def material_ready(
    data: dict[str, Any], contract: dict[str, Any], base: Path
) -> tuple[bool, dict[str, Any]]:
    candidates = {item["id"] for item in contract["head_material_candidates"]}
    selected = data.get("selected_head_material_id")
    references = [
        data.get("temperature_dependent_property_table"),
        data.get("coupon_test_report"),
        data.get("microstructure_and_porosity_report"),
        data.get("fatigue_data_report"),
    ]
    evidence_passed, findings = all_evidence_ready(references, base)
    passed = selected in candidates and evidence_passed
    return passed, {
        "selected_head_material_id": selected,
        "candidate_known": selected in candidates,
        "evidence": findings,
    }


def evidence_group_ready(
    data: dict[str, Any], required_keys: tuple[str, ...], base: Path
) -> tuple[bool, dict[str, str]]:
    findings: dict[str, str] = {}
    passed = True
    for key in required_keys:
        ready, finding = evidence_ready(data.get(key), base)
        findings[key] = finding
        passed = passed and ready
    return passed, findings


def valvetrain_ready(data: dict[str, Any], base: Path) -> tuple[bool, dict[str, Any]]:
    required_evidence = (
        "cam_lift_curve",
        "measured_valve_geometry",
        "moving_mass_report",
        "spring_force_displacement_curve",
        "guide_clearance_and_finish_report",
    )
    evidence_passed, findings = evidence_group_ready(data, required_evidence, base)
    dimensions_ready = is_positive_number(data.get("installed_height_mm")) and is_positive_number(
        data.get("coil_bind_height_mm")
    )
    clearance_ready = dimensions_ready and data["installed_height_mm"] > data["coil_bind_height_mm"]
    return evidence_passed and clearance_ready, {
        "evidence": findings,
        "installed_height_mm": data.get("installed_height_mm"),
        "coil_bind_height_mm": data.get("coil_bind_height_mm"),
        "positive_static_coil_bind_clearance": clearance_ready,
    }


def architecture_ready(data: dict[str, Any], base: Path) -> tuple[bool, dict[str, Any]]:
    findings: dict[str, Any] = {}
    passed = True
    expected_counts = {"baseline_2v": 2, "concept_4v": 4}
    for variant, expected_count in expected_counts.items():
        variant_data = data.get(variant, {})
        evidence_passed, evidence = evidence_group_ready(
            variant_data,
            ("parametric_cad", "chamber_and_port_geometry", "valve_layout_and_lift"),
            base,
        )
        count_ready = variant_data.get("valve_count") == expected_count
        findings[variant] = {
            "expected_valve_count": expected_count,
            "observed_valve_count": variant_data.get("valve_count"),
            "evidence": evidence,
        }
        passed = passed and evidence_passed and count_ready
    return passed, findings


def manufacturing_ready(data: dict[str, Any], base: Path) -> tuple[bool, dict[str, str]]:
    return evidence_group_ready(
        data,
        (
            "machine_and_parameter_set",
            "build_orientation_and_support_plan",
            "heat_treatment_and_hip_plan",
            "machining_and_datum_plan",
            "powder_removal_plan",
            "ndt_and_pressure_test_plan",
        ),
        base,
    )


def generated_geometry_ready(pipeline: Path) -> tuple[bool, dict[str, Any]]:
    interface = load_json(pipeline / "cad/interface-proxy.json")
    valves = load_json(pipeline / "cad/valves/valve-variants-f1.json")
    cfd = load_json(pipeline / "cfd/cfd-stubs.json")
    domain_findings = {
        name: {
            "status": domain.get("status"),
            "gmsh_status": domain.get("gmsh", {}).get("status"),
            "watertight": domain.get("surface", {}).get("watertight"),
        }
        for name, domain in cfd.get("domains", {}).items()
    }
    domains_ready = len(domain_findings) == 2 and all(
        item["status"] == "provisional_cfd_stub"
        and item["gmsh_status"] == "generated"
        and item["watertight"] is True
        for item in domain_findings.values()
    )
    passed = (
        interface.get("status") == "F1_interface_proxy"
        and valves.get("status") == "F1_hypothesis_only"
        and domains_ready
    )
    return passed, {
        "interface_proxy": interface.get("status"),
        "valve_proxies": valves.get("status"),
        "cfd_stub_domains": domain_findings,
        "scope": "generated geometry only; scale, fit and physics remain separate gates",
    }


def source_integrity_ready(
    pipeline: Path, contract: dict[str, Any]
) -> tuple[bool, dict[str, Any]]:
    report = load_json(pipeline / "reports/mesh-preparation.json")
    expected = contract["asset"]["source_sha256"]
    topology = report.get("topology", {}).get("head_with_studs", {})
    passed = report.get("source_sha256") == expected
    return passed, {
        "expected_sha256": expected,
        "observed_sha256": report.get("source_sha256"),
        "boundary_edges": topology.get("boundary_edges"),
        "watertight": topology.get("watertight"),
        "diagnosis": "open_reference_mesh" if topology.get("watertight") is False else "closed_mesh",
    }


def gate(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"id": name, "status": "passed" if passed else "blocked", "details": details}


def evaluate(
    pipeline: Path, contract_path: Path, inputs_path: Path
) -> dict[str, Any]:
    contract = load_json(contract_path)
    inputs = load_json(inputs_path)
    evidence_base = inputs_path.parent

    source_ok, source_details = source_integrity_ready(pipeline, contract)
    geometry_ok, geometry_details = generated_geometry_ready(pipeline)
    scale_ok, scale_details = evaluate_scale(inputs["scale_calibration"], evidence_base)
    target_ok, target_details = named_engine_ready(inputs["target_engine"], evidence_base)
    internal_ok, internal_details = internal_geometry_ready(inputs["internal_geometry"], evidence_base)
    material_ok, material_details = material_ready(
        inputs["material_characterization"], contract, evidence_base
    )
    loads_ok, loads_details = evidence_group_ready(
        inputs["operating_loads"],
        (
            "cylinder_pressure_vs_crank_angle",
            "intake_pressure_temperature_vs_crank_angle",
            "exhaust_pressure_temperature_vs_crank_angle",
            "stud_preload_report",
            "external_cooling_measurements",
            "duty_cycle_definition",
        ),
        evidence_base,
    )
    valvetrain_ok, valvetrain_details = valvetrain_ready(
        inputs["valvetrain_geometry"], evidence_base
    )
    architecture_ok, architecture_details = architecture_ready(
        inputs["architecture_comparison"], evidence_base
    )
    correlation_ok, correlation_details = evidence_group_ready(
        inputs["experimental_correlation"],
        (
            "flow_bench_results",
            "pressure_measurements",
            "temperature_measurements",
            "deformation_or_strain_measurements",
            "correlation_acceptance_plan",
        ),
        evidence_base,
    )
    manufacturing_ok, manufacturing_details = manufacturing_ready(
        inputs["manufacturing_qualification"], evidence_base
    )
    prototype_ok, prototype_details = evidence_group_ready(
        inputs["prototype_validation"],
        (
            "dimensional_report",
            "ct_and_ndt_report",
            "leak_and_pressure_test_report",
            "thermal_cycle_report",
        ),
        evidence_base,
    )
    engine_test_ok, engine_test_details = evidence_group_ready(
        inputs["engine_test_validation"],
        ("test_bench_protocol", "instrumentation_and_shutdown_plan", "test_results"),
        evidence_base,
    )
    review_ok, review_details = evidence_group_ready(
        inputs["professional_review"], ("signed_report",), evidence_base
    )
    review_ok = review_ok and is_present(inputs["professional_review"].get("reviewer")) and is_present(
        inputs["professional_review"].get("scope")
    )

    gate_results = [
        gate("source_integrity", source_ok, source_details),
        gate("generated_geometry", geometry_ok, geometry_details),
        gate("scale_calibration", scale_ok, scale_details),
        gate("target_engine", target_ok, target_details),
        gate("internal_geometry", internal_ok, internal_details),
        gate("material_characterization", material_ok, material_details),
        gate("operating_loads", loads_ok, loads_details),
        gate("valvetrain_geometry", valvetrain_ok, valvetrain_details),
        gate("architecture_comparison_geometry", architecture_ok, architecture_details),
        gate("experimental_correlation", correlation_ok, correlation_details),
        gate("manufacturing_qualification", manufacturing_ok, manufacturing_details),
        gate("prototype_validation", prototype_ok, prototype_details),
        gate("engine_test_validation", engine_test_ok, engine_test_details),
        gate("professional_review", review_ok, review_details),
    ]
    gate_status = {item["id"]: item["status"] == "passed" for item in gate_results}

    level_conditions = [
        ("F0_reference", source_ok),
        ("F1_envelope", source_ok and geometry_ok and scale_ok and target_ok),
        (
            "F2_internal_geometry",
            source_ok and geometry_ok and scale_ok and target_ok and internal_ok and valvetrain_ok,
        ),
        (
            "F3_coupled_physics",
            source_ok
            and geometry_ok
            and scale_ok
            and target_ok
            and internal_ok
            and valvetrain_ok
            and material_ok
            and loads_ok,
        ),
        (
            "F4_physical_correlation",
            source_ok
            and geometry_ok
            and scale_ok
            and target_ok
            and internal_ok
            and valvetrain_ok
            and material_ok
            and loads_ok
            and correlation_ok,
        ),
        ("F5_metal_prototype", correlation_ok and manufacturing_ok and prototype_ok),
        (
            "F6_engine_test",
            correlation_ok and manufacturing_ok and prototype_ok and engine_test_ok and review_ok,
        ),
    ]
    highest_level = "unverified"
    for level, condition in level_conditions:
        if condition:
            highest_level = level
        else:
            break

    model_readiness = []
    for model in contract["physics_models"]:
        missing = [name for name in model["required_gates"] if not gate_status.get(name, False)]
        model_readiness.append(
            {
                "id": model["id"],
                "status": "ready_for_solver_setup" if not missing else "blocked",
                "missing_gates": missing,
                "required_outputs": model["required_outputs"],
                "acceptance": model["acceptance"],
            }
        )

    release_authorized = (
        highest_level == "F6_engine_test"
        and all(item["status"] == "ready_for_solver_setup" for item in model_readiness)
        and manufacturing_ok
        and prototype_ok
        and engine_test_ok
        and review_ok
    )
    return {
        "schema_version": "1.0.0",
        "report_status": "passed",
        "asset_id": contract["asset"]["id"],
        "highest_verified_level": highest_level,
        "generated_geometry_level": "F1_hypothesis_artifacts" if geometry_ok else "blocked",
        "gates": gate_results,
        "physics_model_readiness": model_readiness,
        "design_space": {
            "head_material_candidates": contract["head_material_candidates"],
            "component_strategy": contract["component_strategy"],
            "architecture_variants": contract["architecture_variants"],
            "selection_status": "blocked_pending_coupled_physics_and_physical_correlation",
        },
        "manufacturing_release": {
            "authorized": release_authorized,
            "reason": (
                "all F6 gates passed"
                if release_authorized
                else "blocked until F6 evidence and professional review"
            ),
        },
        "next_required_evidence": [
            item["id"] for item in gate_results if item["status"] == "blocked"
        ],
        "scope": "evidence and solver-readiness audit; no CFD, thermal, structural or engine result is fabricated",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = evaluate(
        args.pipeline.resolve(), args.contract.resolve(), args.inputs.resolve()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
