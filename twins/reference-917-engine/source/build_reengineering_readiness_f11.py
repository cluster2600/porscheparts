#!/usr/bin/env python3
"""Audit F11 evidence for Porsche 917 engine reengineering.

The report is deliberately fail-closed. Existing scan, USD and visual variant
artifacts are inspected, but they never satisfy head geometry, material,
solver, manufacturing or engine-test gates by implication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


ASSET_ID = "porsche-917-engine-reengineering-f11"
ALL_VARIANTS = ("917_30_turbo_5374", "type_912_4_5_na")
SOURCE_VARIANTS = ("917_unspecified",)


@dataclass
class EvidenceRegistry:
    """Track manifests so one assertion cannot satisfy unrelated claims."""

    manifest_digests: dict[str, str] = field(default_factory=dict)
    evidence_ids: dict[str, str] = field(default_factory=dict)
    artifact_digests: dict[str, str] = field(default_factory=dict)


def evidence_requirement(
    claim_id: str,
    evidence_kind: str,
    variant_ids: tuple[str, ...] = ALL_VARIANTS,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "evidence_kind": evidence_kind,
        "asset_id": ASSET_ID,
        "variant_ids": list(variant_ids),
        **extra,
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    if not path.is_file():
        return None, f"artifact not found: {path}"
    try:
        return load_json(path), f"loaded: {path}"
    except (OSError, json.JSONDecodeError) as error:
        return None, f"artifact unreadable: {path}: {error}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def is_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def resolve_path(reference: str, base: Path) -> Path:
    path = Path(reference).expanduser()
    return path if path.is_absolute() else (base / path).resolve()


def _non_empty_strings(data: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return all(is_present(data.get(key)) for key in keys)


def _valid_issued_at(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _verify_manifest_artifacts(
    manifest: dict[str, Any], manifest_path: Path
) -> tuple[bool, list[str]]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return False, ["at least one hashed artifact is required"]
    findings: list[str] = []
    seen_paths: set[Path] = set()
    passed = True
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            findings.append("artifact entry is not an object")
            passed = False
            continue
        raw_path = artifact.get("path")
        expected = artifact.get("sha256")
        role = artifact.get("role")
        if not is_present(raw_path) or not is_present(expected) or not is_present(role):
            findings.append("artifact path, SHA-256 and role are required")
            passed = False
            continue
        path = resolve_path(str(raw_path), manifest_path.parent)
        if path in seen_paths:
            findings.append(f"duplicate artifact path: {path}")
            passed = False
            continue
        seen_paths.add(path)
        if not path.is_file():
            findings.append(f"artifact not found: {path}")
            passed = False
            continue
        actual = sha256(path)
        if actual.lower() != str(expected).lower():
            findings.append(f"artifact SHA-256 mismatch: {path}")
            passed = False
            continue
        findings.append(f"verified artifact: {path}")
    return passed, findings


def _validate_specialized_result(
    manifest: dict[str, Any], requirement: dict[str, Any]
) -> tuple[bool, str | None]:
    result = manifest.get("result", {})
    if requirement.get("source_scan_sha256"):
        expected = requirement["source_scan_sha256"].lower()
        artifact_hashes = {
            str(item.get("sha256", "")).lower()
            for item in manifest.get("artifacts", [])
            if isinstance(item, dict)
        }
        if expected not in artifact_hashes:
            return False, "source scan digest is not present in verified artifacts"

    if requirement.get("solver_validation"):
        validation = result.get("validation", {})
        required_strings = ("solver_name", "solver_version", "model_family")
        required_true = (
            "converged",
            "mesh_independence_passed",
            "balance_tolerance_passed",
            "boundary_conditions_defined",
        )
        if not isinstance(validation, dict) or not _non_empty_strings(
            validation, required_strings
        ):
            return False, "solver identity and model family are required"
        if not all(validation.get(key) is True for key in required_true):
            return False, "solver convergence, independence, balances and BC checks must pass"

    if requirement.get("bench_validation"):
        validation = result.get("validation", {})
        required_true = (
            "instrumentation_calibrated",
            "shutdown_system_verified",
            "data_complete",
            "acceptance_met",
        )
        if not isinstance(validation, dict) or not is_present(validation.get("test_id")):
            return False, "bench test id is required"
        if not all(validation.get(key) is True for key in required_true):
            return False, "bench calibration, safety, completeness and acceptance must pass"

    if requirement.get("professional_signature"):
        signature = manifest.get("signature", {})
        if not isinstance(signature, dict) or signature.get("status") != "verified":
            return False, "professional review signature is not verified"
        if not _non_empty_strings(signature, ("type", "key_id")):
            return False, "professional review signature type and key id are required"
        covered_levels = result.get("covered_levels", [])
        covered_releases = set(result.get("covered_releases", []))
        expected_releases = {
            "manufacturing",
            "metal_print",
            "engine_start",
            "performance_claim_1600_hp",
        }
        if "F6_instrumented_engine_bench" not in covered_levels:
            return False, "professional review does not cover F6"
        if not expected_releases.issubset(covered_releases):
            return False, "professional review does not cover all release decisions"
    return True, None


def evidence_ready(
    reference: Any,
    base: Path,
    requirement: dict[str, Any] | None = None,
    registry: EvidenceRegistry | None = None,
) -> tuple[bool, str]:
    if not isinstance(reference, dict):
        return False, "missing evidence reference"
    raw_path = reference.get("path")
    expected = reference.get("sha256")
    if not is_present(raw_path) or not is_present(expected):
        return False, "evidence path and SHA-256 are required"
    path = resolve_path(str(raw_path), base)
    if not path.is_file():
        return False, f"evidence file not found: {path}"
    actual = sha256(path)
    if actual.lower() != str(expected).lower():
        return False, f"evidence SHA-256 mismatch: {path}"
    try:
        manifest = load_json(path)
    except (OSError, json.JSONDecodeError) as error:
        return False, f"evidence manifest is not valid JSON: {path}: {error}"
    required_top_level = (
        "evidence_id",
        "evidence_kind",
        "claim_id",
        "asset_id",
        "revision",
    )
    if manifest.get("schema_version") != "1.0.0" or not _non_empty_strings(
        manifest, required_top_level
    ):
        return False, f"evidence manifest schema or identifiers are incomplete: {path}"
    if not _valid_issued_at(manifest.get("issued_at")):
        return False, f"evidence issued_at must be timezone-aware ISO-8601: {path}"
    variants = manifest.get("variant_ids")
    if not isinstance(variants, list) or not variants or not all(
        is_present(value) for value in variants
    ):
        return False, f"evidence variant_ids are required: {path}"
    producer = manifest.get("producer", {})
    method = manifest.get("method", {})
    if not isinstance(producer, dict) or not _non_empty_strings(
        producer, ("name", "role", "organization")
    ):
        return False, f"evidence producer identity is incomplete: {path}"
    if not isinstance(method, dict) or not _non_empty_strings(
        method, ("name", "description")
    ):
        return False, f"evidence method is incomplete: {path}"
    result = manifest.get("result", {})
    if not isinstance(result, dict) or result.get("status") != "passed":
        return False, f"evidence result must explicitly pass: {path}"
    if result.get("measured_or_simulated") not in {
        "measured",
        "simulated",
        "manufactured",
        "tested",
        "reviewed",
        "documented",
    }:
        return False, f"evidence result class is invalid: {path}"
    acceptance = result.get("acceptance_criteria")
    if not isinstance(acceptance, list) or not acceptance or not all(
        is_present(value) for value in acceptance
    ):
        return False, f"evidence acceptance criteria are required: {path}"

    artifacts_ok, artifact_findings = _verify_manifest_artifacts(manifest, path)
    if not artifacts_ok:
        return False, f"evidence artifacts invalid: {path}: {'; '.join(artifact_findings)}"

    if requirement is not None:
        for key in ("claim_id", "evidence_kind", "asset_id"):
            if manifest.get(key) != requirement.get(key):
                return False, f"evidence {key} mismatch for {requirement.get('claim_id')}: {path}"
        if set(variants) != set(requirement.get("variant_ids", [])):
            return False, f"evidence variant scope mismatch for {requirement.get('claim_id')}: {path}"
        specialized_ok, specialized_finding = _validate_specialized_result(
            manifest, requirement
        )
        if not specialized_ok:
            return False, f"evidence result invalid: {path}: {specialized_finding}"

    if registry is not None:
        claim = manifest["claim_id"]
        previous_claim = registry.manifest_digests.get(actual.lower())
        if previous_claim is not None and previous_claim != claim:
            return False, f"evidence manifest digest reused by incompatible claims: {previous_claim} and {claim}"
        evidence_id = manifest["evidence_id"]
        previous_id_claim = registry.evidence_ids.get(evidence_id)
        if previous_id_claim is not None and previous_id_claim != claim:
            return False, f"evidence id reused by incompatible claims: {previous_id_claim} and {claim}"
        for artifact in manifest["artifacts"]:
            artifact_digest = str(artifact["sha256"]).lower()
            previous_artifact_claim = registry.artifact_digests.get(artifact_digest)
            if previous_artifact_claim is not None and previous_artifact_claim != claim:
                return False, (
                    "evidence artifact digest reused by incompatible claims: "
                    f"{previous_artifact_claim} and {claim}"
                )
        registry.manifest_digests[actual.lower()] = claim
        registry.evidence_ids[evidence_id] = claim
        for artifact in manifest["artifacts"]:
            registry.artifact_digests[str(artifact["sha256"]).lower()] = claim
    return True, f"verified typed evidence: {path}"


def evidence_group_ready(
    data: dict[str, Any],
    required_keys: tuple[str, ...],
    base: Path,
    group: str,
    evidence_kind: str,
    registry: EvidenceRegistry,
    variant_ids: tuple[str, ...] = ALL_VARIANTS,
    variant_ids_by_key: dict[str, tuple[str, ...]] | None = None,
    **requirement_extras: Any,
) -> tuple[bool, dict[str, str]]:
    findings: dict[str, str] = {}
    passed = True
    for key in required_keys:
        ready, finding = evidence_ready(
            data.get(key),
            base,
            evidence_requirement(
                f"{group}.{key}",
                evidence_kind,
                (variant_ids_by_key or {}).get(key, variant_ids),
                **requirement_extras,
            ),
            registry,
        )
        findings[key] = finding
        passed = passed and ready
    return passed, findings


def gate(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"id": name, "status": "passed" if passed else "blocked", "details": details}


def inspect_repository_artifacts(
    project_root: Path, contract: dict[str, Any]
) -> tuple[bool, bool, dict[str, Any]]:
    loaded: dict[str, dict[str, Any] | None] = {}
    load_findings: dict[str, str] = {}
    for name, relative in contract["observed_artifacts"].items():
        data, finding = load_optional_json(resolve_path(relative, project_root))
        loaded[name] = data
        load_findings[name] = finding

    mesh = loaded["mesh_preparation"] or {}
    topology = mesh.get("topology", {}).get("source", {})
    source_ok = mesh.get("source_sha256") == contract["asset"]["source_scan_sha256"]

    output = loaded["output_verification"] or {}
    variants = loaded["variant_generation"] or {}
    run = loaded["variant_run"] or {}
    expected_variants = {item["id"] for item in contract["engine_variants"]}
    generated_variants = {
        item.get("variant_id") for item in variants.get("variants", []) if item.get("variant_id")
    }
    run_variants = set(run.get("variant_ids", []))
    variant_release_gates = variants.get("release_gates", variants)
    run_release_gates = run.get("release_gates", run)
    visual_variants_ok = (
        variants.get("status") == "passed"
        and run.get("status") == "passed"
        and generated_variants == expected_variants
        and run_variants == expected_variants
        and variant_release_gates.get("manufacturing_geometry_ready") is False
        and variant_release_gates.get("physical_kinematics_ready") is False
        and run_release_gates.get("manufacturing_geometry_ready") is False
        and run_release_gates.get("physical_kinematics_ready") is False
    )

    cfd = loaded["external_cfd_validation"] or {}
    bench = loaded["test_bench_preflight"] or {}
    observations = {
        "artifact_loading": load_findings,
        "scan": {
            "source_sha256_matches_contract": source_ok,
            "identity": mesh.get("identity"),
            "units": mesh.get("units"),
            "boundary_edges": topology.get("boundary_edges"),
            "watertight": topology.get("watertight"),
            "scope": contract["asset"]["source_scan_scope"],
            "contains_measured_head_geometry": contract["asset"]["head_geometry_in_source_scan"],
        },
        "derived_output_verification": {
            "status": output.get("status", "unavailable"),
            "scope": "geometry and deliverable checks only",
        },
        "visual_variants": {
            "status": "passed" if visual_variants_ok else "unavailable_or_inconsistent",
            "variant_ids": sorted(generated_variants),
            "manufacturing_geometry_ready": False,
            "physical_kinematics_ready": False,
        },
        "external_cooling_cfd": {
            "status": cfd.get("status", "unavailable"),
            "solver_allowed": cfd.get("solver_allowed", False),
            "failed_mesh_checks": cfd.get("failed_mesh_checks"),
            "duplicate_faces": cfd.get("duplicate_faces"),
            "non_consecutive_shared_point_faces": cfd.get(
                "non_consecutive_shared_point_faces"
            ),
            "scope": cfd.get(
                "scope", "no validated mesh, boundary conditions or flow solution available"
            ),
            "physics_result_available": False,
        },
        "test_bench": {
            "status": bench.get("status", "unavailable"),
            "highest_completed_stage": bench.get("highest_completed_stage"),
            "fired_run_executed": bench.get("fired_run_executed", False),
            "engine_test_evidence_available": False,
        },
    }
    return source_ok, visual_variants_ok, observations


def source_identity_and_scale_ready(
    data: dict[str, Any], base: Path, registry: EvidenceRegistry
) -> tuple[bool, dict[str, Any]]:
    identity_ok, identity_finding = evidence_ready(
        data.get("identity_report"),
        base,
        evidence_requirement(
            "source_identity_and_scale.identity_report",
            "identity_metrology_report",
            SOURCE_VARIANTS,
        ),
        registry,
    )
    declared = data.get("mm_per_obj_unit")
    threshold = data.get("maximum_relative_spread")
    controls = data.get("scale_controls", [])
    if not is_positive_number(declared) or not is_positive_number(threshold):
        return False, {
            "identity_report": identity_finding,
            "reason": "positive scale and spread threshold are required",
        }
    if len(controls) < 3:
        return False, {
            "identity_report": identity_finding,
            "reason": "at least three independent scale controls are required",
        }

    factors: list[float] = []
    control_findings: list[dict[str, Any]] = []
    controls_ok = True
    feature_ids: list[str] = []
    scan_regions: list[str] = []
    for control in controls:
        scan = control.get("scan_obj_units")
        physical = control.get("physical_mm")
        uncertainty = control.get("uncertainty_mm")
        feature_id = control.get("feature_id")
        scan_region = control.get("scan_region")
        identifiers_ok = is_present(feature_id) and is_present(scan_region)
        if identifiers_ok:
            feature_ids.append(str(feature_id))
            scan_regions.append(str(scan_region))
        evidence_ok, evidence_finding = evidence_ready(
            control.get("evidence"),
            base,
            evidence_requirement(
                f"source_identity_and_scale.scale_controls.{feature_id}",
                "scale_control_metrology_report",
                SOURCE_VARIANTS,
            ),
            registry,
        )
        numeric_ok = all(is_positive_number(value) for value in (scan, physical, uncertainty))
        controls_ok = controls_ok and evidence_ok and numeric_ok and identifiers_ok
        if numeric_ok:
            factors.append(float(physical) / float(scan))
        control_findings.append(
            {
                "feature_id": control.get("feature_id"),
                "scan_region": scan_region,
                "independent_identifiers_ready": identifiers_ok,
                "numeric_values_ready": numeric_ok,
                "evidence": evidence_finding,
            }
        )
    independent = (
        len(feature_ids) == len(set(feature_ids)) == len(controls)
        and len(scan_regions) == len(set(scan_regions)) == len(controls)
    )
    if not controls_ok or len(factors) != len(controls) or not independent:
        return False, {
            "identity_report": identity_finding,
            "controls": control_findings,
            "reason": "scale controls are incomplete or do not use three distinct features and scan regions",
        }

    mean_factor = sum(factors) / len(factors)
    spread = max(abs(value - mean_factor) / mean_factor for value in factors)
    declared_error = abs(float(declared) - mean_factor) / mean_factor
    consistent = spread <= float(threshold) and declared_error <= float(threshold)
    return identity_ok and consistent, {
        "identity_report": identity_finding,
        "control_count": len(controls),
        "mean_mm_per_obj_unit": mean_factor,
        "declared_mm_per_obj_unit": declared,
        "maximum_relative_spread": spread,
        "declared_relative_error": declared_error,
        "acceptance_threshold": threshold,
        "controls": control_findings,
        "reason": None if consistent else "scale controls or declared scale are inconsistent",
    }


def variant_selection_ready(
    data: dict[str, Any],
    contract: dict[str, Any],
    base: Path,
    registry: EvidenceRegistry,
) -> tuple[bool, dict[str, Any]]:
    expected = {item["id"] for item in contract["engine_variants"]}
    observed = set(data.get("selected_variant_ids", []))
    evidence_ok, finding = evidence_ready(
        data.get("selection_basis"),
        base,
        evidence_requirement(
            "variant_selection.selection_basis", "variant_selection_report"
        ),
        registry,
    )
    passed = observed == expected and evidence_ok
    return passed, {
        "expected_variant_ids": sorted(expected),
        "selected_variant_ids": sorted(observed),
        "selection_basis": finding,
    }


def architecture_geometry_ready(
    data: dict[str, Any],
    branch: str,
    expected_count: int,
    base: Path,
    registry: EvidenceRegistry,
) -> tuple[bool, dict[str, Any]]:
    branch_data = data.get(branch, {})
    evidence_ok, findings = evidence_group_ready(
        branch_data,
        (
            "parametric_cad",
            "chamber_ports_seats_and_guides",
            "valve_layout_lift_and_actuation",
            "clearance_and_tolerance_report",
        ),
        base,
        f"architecture_geometry.{branch}",
        "parametric_geometry_report",
        registry,
    )
    count_ok = branch_data.get("valves_per_cylinder") == expected_count
    return evidence_ok and count_ok, {
        "expected_valves_per_cylinder": expected_count,
        "observed_valves_per_cylinder": branch_data.get("valves_per_cylinder"),
        "independent_geometry_evidence": findings,
    }


def material_ready(
    data: dict[str, Any],
    contract: dict[str, Any],
    base: Path,
    registry: EvidenceRegistry,
) -> tuple[bool, dict[str, Any]]:
    known = {item["id"] for item in contract["head_material_candidates"]}
    selected = data.get("selected_head_material_id")
    evidence_ok, findings = evidence_group_ready(
        data,
        (
            "machine_parameter_orientation_and_heat_treatment",
            "temperature_dependent_thermal_properties",
            "temperature_dependent_elastic_plastic_properties",
            "fatigue_and_defect_sensitivity",
            "microstructure_porosity_and_surface_state",
            "machining_insert_and_galvanic_compatibility",
        ),
        base,
        "material_characterization",
        "material_characterization_report",
        registry,
    )
    return selected in known and evidence_ok, {
        "selected_head_material_id": selected,
        "candidate_known": selected in known,
        "evidence": findings,
    }


def professional_review_ready(
    data: dict[str, Any], base: Path, registry: EvidenceRegistry
) -> tuple[bool, dict[str, Any]]:
    report_ok, finding = evidence_ready(
        data.get("signed_report"),
        base,
        evidence_requirement(
            "professional_review.signed_report",
            "signed_professional_review",
            professional_signature=True,
        ),
        registry,
    )
    named = is_present(data.get("reviewer")) and is_present(data.get("scope"))
    return report_ok and named, {
        "reviewer_present": is_present(data.get("reviewer")),
        "scope_present": is_present(data.get("scope")),
        "signed_report": finding,
    }


def evaluate(project_root: Path, contract_path: Path, inputs_path: Path) -> dict[str, Any]:
    contract = load_json(contract_path)
    inputs = load_json(inputs_path)
    evidence_base = inputs_path.parent
    registry = EvidenceRegistry()

    source_report_ok, visual_variants_ok, artifact_observations = inspect_repository_artifacts(
        project_root, contract
    )
    source_manifest_ok, source_manifest_finding = evidence_ready(
        inputs.get("source_scan"),
        evidence_base,
        evidence_requirement(
            "source_scan.integrity",
            "source_scan_integrity",
            SOURCE_VARIANTS,
            source_scan_sha256=contract["asset"]["source_scan_sha256"],
        ),
        registry,
    )
    source_ok = source_report_ok and source_manifest_ok
    artifact_observations["scan"]["typed_source_evidence"] = source_manifest_finding
    artifact_observations["scan"]["source_bytes_rehashed"] = source_manifest_ok
    identity_ok, identity_details = source_identity_and_scale_ready(
        inputs["source_identity_and_scale"], evidence_base, registry
    )
    variant_ok, variant_details = variant_selection_ready(
        inputs["variant_selection"], contract, evidence_base, registry
    )
    head_ok, head_details = evidence_group_ready(
        inputs["measured_head_geometry"],
        (
            "variant_specific_head_scan_or_ct",
            "voxel_size_and_resolution_report",
            "datum_and_coordinate_system_report",
            "combustion_chamber_segmentation",
            "intake_and_exhaust_port_segmentation",
            "cooling_fin_and_external_surface_geometry",
            "oil_passage_geometry",
            "seats_guides_spark_plugs_fasteners_and_sealing_interfaces",
            "dimensional_uncertainty_report",
        ),
        evidence_base,
        "measured_head_geometry",
        "measured_head_geometry_report",
        registry,
    )
    baseline_ok, baseline_details = architecture_geometry_ready(
        inputs["architecture_geometry"], "baseline_2v", 2, evidence_base, registry
    )
    concept_ok, concept_details = architecture_geometry_ready(
        inputs["architecture_geometry"], "concept_4v", 4, evidence_base, registry
    )
    material_ok, material_details = material_ready(
        inputs["material_characterization"], contract, evidence_base, registry
    )

    group_definitions = {
        "operating_loads": (
            "duty_cycles_NA_and_turbo",
            "cylinder_pressure_vs_crank_angle",
            "intake_pressure_temperature_vs_crank_angle",
            "exhaust_pressure_temperature_vs_crank_angle",
            "cooling_fan_curve_and_air_distribution",
            "fastener_preload_and_contact_definition",
            "oil_temperature_pressure_and_heat_rejection",
            "ambient_fuel_ignition_and_control_definition",
        ),
        "valvetrain_inputs": (
            "cam_profiles_and_timing",
            "measured_valve_and_reciprocating_geometry",
            "moving_masses_and_inertias",
            "spring_force_displacement_and_dynamic_properties",
            "installed_and_coil_bind_heights",
            "guide_seat_clearance_finish_and_wear",
            "gas_loads_and_target_speed_envelope",
        ),
        "turbo_inputs": (
            "compressor_maps",
            "turbine_maps",
            "wheel_shaft_bearing_housing_geometry",
            "wastegate_and_bypass_characterization",
            "oil_and_thermal_boundary_conditions",
            "speed_temperature_and_containment_limits",
        ),
        "reference_solver_evidence": (
            "solver_names_versions_and_models",
            "geometry_mesh_and_boundary_condition_dataset",
            "mesh_and_time_step_independence",
            "mass_momentum_and_energy_balance",
            "numerical_uncertainty_report",
            "versioned_results_dataset",
        ),
        "experimental_correlation": (
            "flow_bench_2v_and_4v",
            "pressure_and_temperature_measurements",
            "strain_deformation_and_thermal_cycle_measurements",
            "valvetrain_dynamic_rig_results",
            "acceptance_thresholds_and_uncertainty_budget",
        ),
        "manufacturing_qualification": (
            "machine_material_parameter_set",
            "orientation_support_and_powder_removal_plan",
            "heat_treatment_HIP_and_stress_relief_plan",
            "datum_machining_insert_and_surface_finish_plan",
            "coupon_and_witness_specimen_plan",
            "CT_NDT_pressure_and_leak_test_plan",
        ),
        "prototype_validation": (
            "prototype_serial_and_build_record",
            "dimensional_and_surface_report",
            "CT_porosity_and_NDT_report",
            "pressure_leak_and_thermal_cycle_report",
            "post_test_metrology_report",
        ),
        "engine_bench_validation": (
            "bench_mount_coupling_and_guarding_review",
            "instrumentation_calibration_and_shutdown_plan",
            "oil_prime_and_dry_crank_results",
            "fired_NA_test_results",
            "fired_turbo_test_results",
            "dyno_speed_torque_fuel_air_temperature_pressure_data",
            "durability_and_post_test_inspection",
        ),
    }
    group_evidence_kinds = {
        "operating_loads": "operating_load_report",
        "valvetrain_inputs": "valvetrain_measurement_report",
        "turbo_inputs": "turbo_characterization_report",
        "reference_solver_evidence": "reference_solver_validation_report",
        "experimental_correlation": "experimental_correlation_report",
        "manufacturing_qualification": "manufacturing_qualification_report",
        "prototype_validation": "prototype_validation_report",
        "engine_bench_validation": "engine_bench_test_report",
    }
    group_results: dict[str, tuple[bool, dict[str, str]]] = {}
    for group, keys in group_definitions.items():
        extras: dict[str, Any] = {}
        variants = ALL_VARIANTS
        if group == "turbo_inputs":
            variants = ("917_30_turbo_5374",)
        if group == "reference_solver_evidence":
            extras["solver_validation"] = True
        if group == "engine_bench_validation":
            extras["bench_validation"] = True
        per_key_variants: dict[str, tuple[str, ...]] = {}
        if group == "engine_bench_validation":
            per_key_variants = {
                "fired_NA_test_results": ("type_912_4_5_na",),
                "fired_turbo_test_results": ("917_30_turbo_5374",),
            }
        group_results[group] = evidence_group_ready(
            inputs[group],
            keys,
            evidence_base,
            group,
            group_evidence_kinds[group],
            registry,
            variants,
            per_key_variants,
            **extras,
        )

    review_ok, review_details = professional_review_ready(
        inputs["professional_review"], evidence_base, registry
    )

    gate_results = [
        gate(
            "scan_source_integrity",
            source_ok,
            {
                "expected_sha256": contract["asset"]["source_scan_sha256"],
                "observations": artifact_observations["scan"],
            },
        ),
        gate(
            "visual_variant_separation",
            visual_variants_ok,
            artifact_observations["visual_variants"],
        ),
        gate("source_identity_and_scale", identity_ok, identity_details),
        gate("variant_selection", variant_ok, variant_details),
        gate("measured_head_geometry", head_ok, head_details),
        gate("baseline_2v_geometry", baseline_ok, baseline_details),
        gate("concept_4v_geometry", concept_ok, concept_details),
        gate("material_characterization", material_ok, material_details),
    ]
    for group in group_definitions:
        passed, details = group_results[group]
        gate_results.append(gate(group, passed, details))
    gate_results.append(gate("professional_review", review_ok, review_details))
    gate_status = {item["id"]: item["status"] == "passed" for item in gate_results}

    operating_ok = group_results["operating_loads"][0]
    valvetrain_ok = group_results["valvetrain_inputs"][0]
    turbo_ok = group_results["turbo_inputs"][0]
    solver_ok = group_results["reference_solver_evidence"][0]
    correlation_ok = group_results["experimental_correlation"][0]
    manufacturing_ok = group_results["manufacturing_qualification"][0]
    prototype_ok = group_results["prototype_validation"][0]
    bench_ok = group_results["engine_bench_validation"][0]

    level_conditions = [
        ("F0_source_integrity", source_ok),
        ("F1_identified_scaled_envelope", source_ok and identity_ok and variant_ok),
        (
            "F2_measured_head_and_valvetrain",
            source_ok
            and identity_ok
            and variant_ok
            and head_ok
            and baseline_ok
            and valvetrain_ok,
        ),
        (
            "F3_coupled_reference_physics",
            head_ok
            and baseline_ok
            and material_ok
            and operating_ok
            and valvetrain_ok
            and turbo_ok
            and solver_ok,
        ),
        (
            "F4_correlated_architecture_comparison",
            head_ok
            and baseline_ok
            and concept_ok
            and material_ok
            and operating_ok
            and valvetrain_ok
            and solver_ok
            and correlation_ok,
        ),
        (
            "F5_qualified_metal_prototype",
            correlation_ok and manufacturing_ok and prototype_ok,
        ),
        (
            "F6_instrumented_engine_bench",
            correlation_ok
            and manufacturing_ok
            and prototype_ok
            and bench_ok
            and review_ok,
        ),
    ]
    highest_level = "unverified"
    level_rank = -1
    for index, (level, condition) in enumerate(level_conditions):
        if not condition:
            break
        highest_level = level
        level_rank = index

    model_readiness = []
    for model in contract["physics_models"]:
        missing = [name for name in model["required_gates"] if not gate_status.get(name, False)]
        model_readiness.append(
            {
                "id": model["id"],
                "status": "ready_for_reference_solver_setup" if not missing else "blocked",
                "missing_gates": missing,
                "required_outputs": model["required_outputs"],
            }
        )

    evidence_package_complete = level_rank >= 6 and all(
        item["status"] == "ready_for_reference_solver_setup" for item in model_readiness
    )
    release_authority = contract.get("release_authority", {})
    release_authority_configuration_complete = (
        release_authority.get("verifier_implemented") is True
        and bool(release_authority.get("trusted_key_ids"))
        and release_authority.get("solver_result_parsers_qualified") is True
        and release_authority.get("bench_result_parsers_qualified") is True
    )
    # No cryptographic verifier or qualified solver/bench parser is implemented
    # in this repository yet. Configuration flags alone must never become an
    # authorization path.
    external_release_authority_ready = False
    manufacturing_release = (
        evidence_package_complete
        and external_release_authority_ready
        and release_authority.get("manufacturing_release_enabled") is True
    )
    material_selection_authorized = level_rank >= 4 and material_ok and correlation_ok
    architecture_selection_authorized = level_rank >= 4 and concept_ok and correlation_ok
    turbo_model_ready = next(
        item for item in model_readiness if item["id"] == "turbo_matching_and_rotordynamics_917_30"
    )
    performance_claim_authorized = (
        manufacturing_release
        and turbo_model_ready["status"] == "ready_for_reference_solver_setup"
    )
    physicsnemo_policy = contract["physicsnemo_surrogate_policy"]
    physicsnemo_training_configuration_complete = (
        level_rank >= 4
        and solver_ok
        and correlation_ok
        and release_authority.get("solver_result_parsers_qualified") is True
        and physicsnemo_policy.get("current_training_authorized") is True
        and physicsnemo_policy.get("dataset_parser_qualified") is True
        and physicsnemo_policy.get("holdout_validator_qualified") is True
        and physicsnemo_policy.get("ood_guard_qualified") is True
    )
    # Training remains disabled until the repository contains and exercises the
    # declared dataset parser, independent holdout validator and OOD guard.
    physicsnemo_training_authorized = False

    return {
        "schema_version": "1.0.0",
        "phase": "F11",
        "report_status": "passed",
        "asset_id": contract["asset"]["id"],
        "highest_verified_level": highest_level,
        "visual_model_level": (
            "F10_separate_variant_hypothesis_stages"
            if visual_variants_ok
            else "unavailable_or_inconsistent"
        ),
        "current_artifact_observations": artifact_observations,
        "gates": gate_results,
        "physics_model_readiness": model_readiness,
        "material_downselection": {
            "candidates": contract["head_material_candidates"],
            "selected_head_material_id": inputs["material_characterization"].get(
                "selected_head_material_id"
            ),
            "selection_authorized": material_selection_authorized,
            "reason": (
                "correlated F4 evidence available"
                if material_selection_authorized
                else "blocked pending route-specific coupons, coupled physics and correlation"
            ),
        },
        "component_strategy": contract["component_strategy"],
        "architecture_comparison": {
            "variants": contract["architecture_variants"],
            "metrics": contract["architecture_comparison"]["metrics"],
            "selection_authorized": architecture_selection_authorized,
            "winner": contract["architecture_comparison"]["winner"],
            "reason": (
                "F4 correlated comparison available"
                if architecture_selection_authorized
                else "no 2V or 4V winner before common-boundary-condition multiphysics and bench correlation"
            ),
        },
        "physicsnemo": {
            "policy": physicsnemo_policy,
            "training_configuration_complete": physicsnemo_training_configuration_complete,
            "training_authorized": physicsnemo_training_authorized,
            "reason": (
                "F4 dataset, qualified parsers, holdout and OOD gates passed"
                if physicsnemo_training_authorized
                else "blocked pending explicit policy enablement, qualified dataset/solver parsers, independent holdout and OOD guard"
            ),
        },
        "release": {
            "evidence_package_complete_for_external_review": evidence_package_complete,
            "release_authority_configuration_complete": release_authority_configuration_complete,
            "external_release_authority_ready": external_release_authority_ready,
            "manufacturing_authorized": manufacturing_release,
            "metal_print_authorized": manufacturing_release,
            "engine_start_authorized": (
                manufacturing_release
                and release_authority.get("engine_start_release_enabled") is True
                and bench_ok
                and review_ok
            ),
            "performance_claim_1600_hp_authorized": performance_claim_authorized,
            "reason": (
                "F6 evidence, qualified parsers and cryptographic release authority passed"
                if manufacturing_release
                else "blocked until F6 evidence, qualified result parsers and external cryptographic release authority"
            ),
        },
        "next_required_evidence": [
            item["id"] for item in gate_results if item["status"] == "blocked"
        ],
        "scope": "evidence and solver-readiness audit; no geometry, material, CFD, thermal, structural, power or durability result is fabricated",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = evaluate(
        args.project_root.resolve(), args.contract.resolve(), args.inputs.resolve()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
