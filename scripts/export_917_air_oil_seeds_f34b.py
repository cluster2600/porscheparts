#!/usr/bin/env python3
"""Exporte les deux seeds forward air/huile F34 pour l'image F34b.

La génération vérifie le contrat F34, tous ses parents et le manifeste DOE
suivi avant d'extraire les entrées NA et TT. Le JSON produit est autonome :
le contrat et le solveur F33 ne sont pas requis dans l'image d'exécution.
Cette étape ne lance aucun solveur et ne crée aucune preuve physique.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TRACKED_OUTPUT = (
    ROOT
    / "twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json"
)

F34A_PATH = "twins/reference-917-engine/air-oil-core-controls-f34a.json"
F34_CONTRACT_PATH = "twins/reference-917-engine/doe-surrogate-f34.json"
F34_MANIFEST_PATH = (
    "twins/reference-917-engine/evidence/f34/doe-case-manifest.json"
)
F34_GENERATOR_PATH = "scripts/run_917_doe_f34.py"
F33_CONTRACT_PATH = "twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json"

PARENT_SPECS = (
    (
        "f34a_air_oil_core_controls",
        F34A_PATH,
        "selected_air_oil_core_and_modern_controls_authority",
    ),
    (
        "f34_doe_contract",
        F34_CONTRACT_PATH,
        "validated_seed_generation_contract",
    ),
    (
        "f34_doe_case_manifest",
        F34_MANIFEST_PATH,
        "verified_zero_execution_case_plan",
    ),
    (
        "f34_doe_generator",
        F34_GENERATOR_PATH,
        "verified_air_oil_seed_transform_source",
    ),
)

CONFIGURATIONS = ("naturally_aspirated", "twin_turbo")
VARIANT_IDS = {
    "naturally_aspirated": "917_2026_flat12_na_air_oil_f34b",
    "twin_turbo": "917_2026_flat12_twin_turbo_air_oil_f34b",
}
EXPECTED_FORWARD_KEYS = {
    "accessory_power_w",
    "bore_mm",
    "compression_ratio",
    "cylinder_count",
    "engine_management",
    "equivalence_ratio",
    "exhaust_pressure_pa_abs",
    "fmep_model",
    "fuel_lhv_j_kg",
    "fuel_surrogate",
    "indicated_work_retention",
    "manifold_pressure_pa_abs",
    "manifold_temperature_k",
    "selected_architecture",
    "speed_rpm",
    "stroke_mm",
    "thermal_hypotheses",
    "turbo_screening_input",
    "turbocharger_count",
    "unit_registry",
    "volumetric_efficiency",
}
EXPECTED_ENGINE_MANAGEMENT_COMMON = {
    "architecture_id": "917_2026_modern_ecu_twin_spark_sequential_efi",
    "electronic_fuel_injection_required": True,
    "sequential_port_injection_required": True,
    "staged_port_injection_candidate": True,
    "independent_injection_channels_target": 24,
    "dual_electronic_ignition_required": True,
    "independent_ignition_channels_required": 24,
    "drive_by_wire_required": True,
    "drive_by_wire_actuators_minimum": 2,
    "variable_cam_timing_candidate": True,
    "variable_valve_lift_candidate": True,
    "closed_loop_lambda_required": True,
    "cylinder_attributed_knock_control_candidate": True,
    "can_fd_required": True,
    "hardware_maps_thresholds_validated": False,
    "response_model_present_in_l0": False,
}
PHYSICAL_GATE_IDS = {
    "air_cooling_physically_validated",
    "oil_system_physically_validated",
    "auxiliary_liquid_isolation_physically_validated",
    "controls_physically_validated",
    "physical_correlation_complete",
    "target_power_proven",
    "engine_bench_start_authorized",
    "vehicle_installation_authorized",
    "metal_print_authorized",
    "manufacturing_authorized",
}
RELEASE_GATE_IDS = {
    "doe_execution_complete",
    "dataset_ready",
    "training_authorized",
    "surrogate_trained",
    "surrogate_validated_against_0d_solver",
    "ood_policy_calibrated",
    "one_dimensional_model_validated",
    "hydraulic_network_validated",
    "cfd_validated",
    "cht_validated",
    "physical_correlation_complete",
    "target_power_proven",
    "cooling_system_validated",
    "test_bench_start_authorized",
    "porsche_993_vehicle_installation_authorized",
    "metal_print_authorized",
    "manufacturing_authorized",
    "ecu_hardware_selected",
    "ecu_io_complete",
    "crank_cam_sync_validated",
    "injector_characterization_validated",
    "ignition_validated",
    "closed_loop_controls_validated",
    "vvt_vvl_validated",
    "lambda_control_validated",
    "knock_control_validated",
    "boost_failsafe_validated",
    "can_fd_architecture_validated",
    "sil_complete",
    "hil_complete",
}
FORBIDDEN_FORWARD_POWER_TARGET_TOKENS = (
    "requested_power",
    "target_power",
    "power_target",
    "delta_to_target",
    "distance_to_1600",
    "meets_1600",
    "1600hp",
    "1600_hp",
    "inverse_sizing_seed",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant rejected: {value}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key rejected: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=_reject_constant,
        object_pairs_hook=_reject_duplicate_pairs,
    )


def _canonical_json(value: Any) -> str:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )


def _canonical_payload_sha256(value: Any) -> str:
    payload = (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_source_file(root: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
        or "\\" in relative
    ):
        raise ValueError(f"unsafe source path: {relative}")
    root_resolved = root.resolve(strict=True)
    candidate = (root / Path(*pure.parts)).resolve(strict=True)
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"source path escapes project root: {relative}") from exc
    if not candidate.is_file():
        raise ValueError(f"source path is not a regular file: {relative}")
    return candidate


def _safe_cli_json_path(path: Path, *, project_root: Path, for_output: bool) -> Path:
    root = project_root.resolve(strict=True)
    lexical = path if path.is_absolute() else project_root / path
    if lexical.suffix.lower() != ".json":
        raise ValueError(f"JSON path required: {path}")

    existing_ancestor = lexical
    while not existing_ancestor.exists():
        if existing_ancestor.parent == existing_ancestor:
            raise ValueError(f"path has no existing ancestor: {path}")
        existing_ancestor = existing_ancestor.parent
    if existing_ancestor.is_symlink():
        raise ValueError(f"symlink path rejected: {path}")
    resolved_ancestor = existing_ancestor.resolve(strict=True)
    try:
        resolved_ancestor.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {path}") from exc

    resolved = lexical.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {path}") from exc

    cursor = lexical
    while cursor != project_root and cursor != cursor.parent:
        if cursor.exists() and cursor.is_symlink():
            raise ValueError(f"symlink path rejected: {path}")
        cursor = cursor.parent

    if for_output:
        protected = {
            _safe_source_file(project_root, relative)
            for _, relative, _ in PARENT_SPECS
        }
        if resolved in protected:
            raise ValueError(f"refusing to overwrite source parent: {path}")
        tracked = TRACKED_OUTPUT.resolve(strict=False)
        if resolved.exists() and resolved != tracked:
            raise ValueError(f"refusing to overwrite unrelated JSON: {path}")
    elif not resolved.is_file():
        raise ValueError(f"check file missing: {path}")
    return resolved


def _load_f34_generator(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("f34_seed_source_generator", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import F34 generator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _json_tree_error(value: Any, path: str = "bundle") -> str | None:
    if value is None or isinstance(value, (str, bool, int)):
        return None
    if isinstance(value, float):
        return None if math.isfinite(value) else f"non_finite:{path}"
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                return f"non_string_key:{path}"
            nested = _json_tree_error(item, f"{path}.{key}")
            if nested:
                return nested
        return None
    if isinstance(value, list):
        for index, item in enumerate(value):
            nested = _json_tree_error(item, f"{path}[{index}]")
            if nested:
                return nested
        return None
    return f"non_json_type:{path}:{type(value).__name__}"


def _forward_power_target_leak(value: Any, path: str = "forward_input") -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered_key = key.lower()
            if any(token in lowered_key for token in FORBIDDEN_FORWARD_POWER_TARGET_TOKENS):
                return f"{path}.{key}"
            nested = _forward_power_target_leak(item, f"{path}.{key}")
            if nested:
                return nested
    elif isinstance(value, list):
        for index, item in enumerate(value):
            nested = _forward_power_target_leak(item, f"{path}[{index}]")
            if nested:
                return nested
    elif isinstance(value, str):
        lowered = value.lower()
        if any(token in lowered for token in FORBIDDEN_FORWARD_POWER_TARGET_TOKENS):
            return path
    return None


def _validate_forward_input(
    configuration: str, forward: Any, errors: list[str]
) -> None:
    if not isinstance(forward, dict):
        errors.append(f"forward_input_not_object:{configuration}")
        return
    if set(forward) != EXPECTED_FORWARD_KEYS:
        errors.append(f"forward_input_key_set_invalid:{configuration}")

    leak = _forward_power_target_leak(forward)
    if leak:
        errors.append(f"requested_power_target_leak:{configuration}:{leak}")

    thermal = forward.get("thermal_hypotheses")
    units = forward.get("unit_registry")
    if not isinstance(thermal, dict) or not isinstance(units, dict):
        errors.append(f"thermal_or_unit_registry_missing:{configuration}")
    else:
        forbidden_thermal = {
            "coolant_cp_j_kg_k",
            "head_coolant_delta_t_k",
            "cylinder_air_heat_fraction_of_fuel_power",
        }
        if forbidden_thermal.intersection(thermal):
            errors.append(f"engine_core_liquid_thermal_field_present:{configuration}")
        if not {
            "cylinder_heat_fraction_of_fuel_power",
            "head_heat_to_oil_fraction",
            "cooling_air_cp_j_kg_k",
            "cooling_air_delta_t_k",
            "oil_cp_j_kg_k",
            "oil_delta_t_k",
        }.issubset(thermal):
            errors.append(f"air_oil_thermal_fields_missing:{configuration}")
        allowed_coolant_fields = (
            {"charge_coolant_cp_j_kg_k", "charge_coolant_delta_t_k"}
            if configuration == "twin_turbo"
            else set()
        )
        actual_coolant_fields = {key for key in thermal if "coolant" in key.lower()}
        if actual_coolant_fields != allowed_coolant_fields:
            errors.append(f"auxiliary_coolant_scope_invalid:{configuration}")
        forbidden_unit_fragments = (
            "thermal_hypotheses.coolant_cp_j_kg_k",
            "thermal_hypotheses.head_coolant_delta_t_k",
            "thermal_hypotheses.cylinder_air_heat_fraction_of_fuel_power",
        )
        if any(fragment in units for fragment in forbidden_unit_fragments):
            errors.append(f"engine_core_liquid_unit_present:{configuration}")
        actual_coolant_unit_fields = {
            key for key in units if "coolant" in key.lower()
        }
        expected_coolant_unit_fields = {
            f"thermal_hypotheses.{key}" for key in allowed_coolant_fields
        }
        if actual_coolant_unit_fields != expected_coolant_unit_fields:
            errors.append(f"auxiliary_coolant_unit_scope_invalid:{configuration}")

    architecture = forward.get("selected_architecture")
    expected_auxiliary = (
        ["charge_cooling", "turbo_chra_optional_unresolved"]
        if configuration == "twin_turbo"
        else []
    )
    expected_architecture = {
        "id": "F34A-AIR-OIL-CORE-2026-CONTROLS",
        "engine_core_liquid_coolant_present": False,
        "engine_core_heat_rejection": ["forced_air", "dry_sump_oil"],
        "auxiliary_liquid_scope": expected_auxiliary,
    }
    if architecture != expected_architecture:
        errors.append(f"selected_air_oil_architecture_invalid:{configuration}")

    expected_management = dict(EXPECTED_ENGINE_MANAGEMENT_COMMON)
    expected_management["electronic_wastegate_control_required"] = (
        configuration == "twin_turbo"
    )
    if forward.get("engine_management") != expected_management:
        errors.append(f"modern_engine_management_invalid:{configuration}")
    if forward.get("turbocharger_count") != (
        2 if configuration == "twin_turbo" else 0
    ):
        errors.append(f"turbocharger_count_invalid:{configuration}")
    if (forward.get("turbo_screening_input") is None) != (
        configuration == "naturally_aspirated"
    ):
        errors.append(f"turbo_screening_scope_invalid:{configuration}")


def validate_bundle(
    bundle: Any,
    *,
    expected_parent_hashes: dict[str, str] | None = None,
) -> list[str]:
    """Valide le bundle sans lire ses sources de génération."""

    if not isinstance(bundle, dict):
        return ["bundle_not_object"]
    errors: list[str] = []
    tree_error = _json_tree_error(bundle)
    if tree_error:
        errors.append(tree_error)

    top_level = {
        "$comment",
        "schema_version",
        "phase",
        "status",
        "architecture_id",
        "canonical_doe_cases_executed",
        "parents",
        "source_verification",
        "image_runtime_contract",
        "authority_boundary",
        "seeds",
        "execution_ledger",
        "physical_gates",
        "release_gates",
        "bundle_payload_sha256",
    }
    if set(bundle) != top_level:
        errors.append("bundle_key_set_invalid")
    if bundle.get("schema_version") != "1.0.0":
        errors.append("schema_version_invalid")
    if bundle.get("phase") != "F34b":
        errors.append("phase_invalid")
    if bundle.get("status") != (
        "deterministic_air_oil_forward_seed_bundle_zero_solver_cases_executed"
    ):
        errors.append("status_invalid")
    if bundle.get("architecture_id") != "F34A-AIR-OIL-CORE-2026-CONTROLS":
        errors.append("architecture_id_invalid")
    if bundle.get("canonical_doe_cases_executed") != 0:
        errors.append("canonical_doe_cases_executed_must_be_zero")

    parents = bundle.get("parents")
    if not isinstance(parents, list) or len(parents) != len(PARENT_SPECS):
        errors.append("parents_invalid")
        parents = []
    seen_paths: set[str] = set()
    for index, spec in enumerate(PARENT_SPECS):
        if index >= len(parents) or not isinstance(parents[index], dict):
            errors.append(f"parent_missing_or_not_object:{index}")
            continue
        parent = parents[index]
        expected_id, expected_path, expected_role = spec
        if set(parent) != {"id", "path", "sha256", "role"}:
            errors.append(f"parent_key_set_invalid:{index}")
        if parent.get("id") != expected_id:
            errors.append(f"parent_id_invalid:{index}")
        if parent.get("path") != expected_path:
            errors.append(f"parent_path_invalid:{index}")
        if parent.get("role") != expected_role:
            errors.append(f"parent_role_invalid:{index}")
        digest = parent.get("sha256")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"parent_sha_invalid:{index}")
        if expected_path in seen_paths:
            errors.append(f"parent_path_duplicate:{expected_path}")
        seen_paths.add(expected_path)
        if (
            expected_parent_hashes is not None
            and digest != expected_parent_hashes.get(expected_path)
        ):
            errors.append(f"parent_sha_mismatch:{expected_path}")

    source_expected = {
        "f34_contract_validated_against_pinned_parents": True,
        "tracked_manifest_rebuilt_byte_for_byte": True,
        "f34a_air_oil_controls_semantics_validated": True,
        "air_oil_seed_mapping_sha256_matches_manifest": True,
    }
    if bundle.get("source_verification") != source_expected:
        errors.append("source_verification_invalid")

    runtime_expected = {
        "bundle_is_self_contained_for_two_forward_inputs": True,
        "source_parents_required_only_at_bundle_generation": True,
        "f33_forward_solver_source_required_in_image": False,
        "f33_contract_required_in_image": False,
        "f34_generator_source_required_in_image": False,
        "network_required_to_load_bundle": False,
        "solver_execution_authorized": False,
    }
    if bundle.get("image_runtime_contract") != runtime_expected:
        errors.append("image_runtime_contract_invalid")

    authority_expected = {
        "classification": "unvalidated_numerical_screening_seeds_not_calibration",
        "requested_power_target_present_in_forward_inputs": False,
        "requested_power_target_used_as_feature": False,
        "requested_power_target_used_for_calibration": False,
        "inverse_sizing_seed_ancestry_present": True,
        "full_target_independence_proven": False,
        "engine_core_liquid_coolant_present": False,
        "auxiliary_liquid_limited_to_charge_cooling_and_optional_turbo_chra": True,
        "controls_response_modeled": False,
        "physical_evidence_created": False,
    }
    if bundle.get("authority_boundary") != authority_expected:
        errors.append("authority_boundary_invalid")

    seeds = bundle.get("seeds")
    if not isinstance(seeds, list) or len(seeds) != 2:
        errors.append("seeds_invalid")
        seeds = []
    for index, configuration in enumerate(CONFIGURATIONS):
        if index >= len(seeds) or not isinstance(seeds[index], dict):
            errors.append(f"seed_missing_or_not_object:{configuration}")
            continue
        seed = seeds[index]
        if set(seed) != {
            "variant_id",
            "configuration",
            "forward_input",
            "forward_input_sha256",
        }:
            errors.append(f"seed_key_set_invalid:{configuration}")
        if seed.get("variant_id") != VARIANT_IDS[configuration]:
            errors.append(f"variant_id_invalid:{configuration}")
        if seed.get("configuration") != configuration:
            errors.append(f"seed_configuration_invalid:{configuration}")
        forward = seed.get("forward_input")
        _validate_forward_input(configuration, forward, errors)
        try:
            actual_hash = _canonical_payload_sha256(forward)
        except (TypeError, ValueError):
            errors.append(f"forward_input_not_canonicalizable:{configuration}")
        else:
            if seed.get("forward_input_sha256") != actual_hash:
                errors.append(f"forward_input_sha_mismatch:{configuration}")

    ledger_expected = {
        "seed_count": 2,
        "solver_case_count": 0,
        "solver_executed": False,
        "labels_present": False,
        "calibration_executed": False,
        "training_executed": False,
        "physical_test_executed": False,
    }
    if bundle.get("execution_ledger") != ledger_expected:
        errors.append("execution_ledger_invalid")

    physical = bundle.get("physical_gates")
    if not isinstance(physical, dict) or set(physical) != PHYSICAL_GATE_IDS:
        errors.append("physical_gate_set_invalid")
    elif any(value is not False for value in physical.values()):
        errors.append("physical_gates_must_all_be_false")
    release = bundle.get("release_gates")
    if not isinstance(release, dict) or set(release) != RELEASE_GATE_IDS:
        errors.append("release_gate_set_invalid")
    elif any(value is not False for value in release.values()):
        errors.append("release_gates_must_all_be_false")

    claimed_payload_hash = bundle.get("bundle_payload_sha256")
    if not isinstance(claimed_payload_hash, str) or not SHA256_RE.fullmatch(
        claimed_payload_hash
    ):
        errors.append("bundle_payload_sha_invalid")
    else:
        payload = copy.deepcopy(bundle)
        payload.pop("bundle_payload_sha256", None)
        try:
            actual_payload_hash = _canonical_payload_sha256(payload)
        except (TypeError, ValueError):
            errors.append("bundle_payload_not_canonicalizable")
        else:
            if claimed_payload_hash != actual_payload_hash:
                errors.append("bundle_payload_sha_mismatch")
    return sorted(set(errors))


def _verify_zero_execution_manifest(manifest: Any) -> None:
    if not isinstance(manifest, dict):
        raise ValueError("tracked F34 manifest is not an object")
    counts = manifest.get("case_counts")
    ledger = manifest.get("execution_ledger")
    authority = manifest.get("authority_boundary")
    generator = manifest.get("generator")
    if (
        not isinstance(counts, dict)
        or counts.get("executed") != 0
        or counts.get("accepted") != 0
        or counts.get("rejected") != 0
        or not isinstance(ledger, dict)
        or ledger.get("executed") != 0
        or ledger.get("accepted") != 0
        or ledger.get("rejected") != 0
        or not isinstance(authority, dict)
        or authority.get("doe_executed") is not False
        or not isinstance(generator, dict)
        or generator.get("solver_executed") is not False
    ):
        raise ValueError("F34 manifest does not prove a zero-execution plan")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("F34 manifest cases missing")
    if any(
        not isinstance(case, dict)
        or case.get("execution_status") != "planned_not_executed"
        or case.get("training_eligible") is not False
        for case in cases
    ):
        raise ValueError("F34 manifest contains an executed or eligible case")


def build_bundle(*, project_root: Path = ROOT) -> dict[str, Any]:
    """Construit le bundle depuis les sources F34 vérifiées sur disque."""

    source_paths = {
        relative: _safe_source_file(project_root, relative)
        for _, relative, _ in PARENT_SPECS
    }
    generator_path = source_paths[F34_GENERATOR_PATH]
    module = _load_f34_generator(generator_path)
    contract_path = source_paths[F34_CONTRACT_PATH]
    contract = _read_json(contract_path)
    contract_errors = module.validate_contract(contract, project_root=project_root)
    if contract_errors:
        raise ValueError(
            "invalid F34 contract or parent set:\n- "
            + "\n- ".join(contract_errors)
        )

    manifest_path = source_paths[F34_MANIFEST_PATH]
    tracked_manifest_text = manifest_path.read_text(encoding="utf-8")
    tracked_manifest = _read_json(manifest_path)
    rebuilt_manifest = module.build_manifest(
        contract,
        contract_path=contract_path,
        project_root=project_root,
    )
    if tracked_manifest_text != _canonical_json(tracked_manifest):
        raise ValueError("tracked F34 manifest is not canonical JSON")
    if rebuilt_manifest != tracked_manifest:
        raise ValueError("tracked F34 manifest is stale")
    _verify_zero_execution_manifest(tracked_manifest)
    if tracked_manifest.get("contract_file_sha256") != _sha256(contract_path):
        raise ValueError("tracked F34 manifest contract hash mismatch")
    manifest_generator = tracked_manifest.get("generator")
    if (
        not isinstance(manifest_generator, dict)
        or manifest_generator.get("script_path") != F34_GENERATOR_PATH
        or manifest_generator.get("script_sha256") != _sha256(generator_path)
    ):
        raise ValueError("tracked F34 manifest generator hash mismatch")

    f34a_parent = next(
        (
            parent
            for parent in contract.get("parents", [])
            if isinstance(parent, dict) and parent.get("path") == F34A_PATH
        ),
        None,
    )
    if (
        not isinstance(f34a_parent, dict)
        or f34a_parent.get("sha256") != _sha256(source_paths[F34A_PATH])
    ):
        raise ValueError("F34a parent hash is not pinned by the F34 contract")

    f33_contract_path = _safe_source_file(project_root, F33_CONTRACT_PATH)
    expected_f33_path = module.F33_CONTRACT.relative_to(module.ROOT).as_posix()
    if expected_f33_path != F33_CONTRACT_PATH:
        raise ValueError("imported F34 generator changed its F33 parent path")
    f33_contract = _read_json(f33_contract_path)
    variants = module._index_variants(f33_contract)
    module._validate_f33_forward_schema(contract, variants)
    forward_inputs = {
        configuration: module._f34_base_forward_input(
            variants[configuration]["forward_solver_input"], configuration
        )
        for configuration in CONFIGURATIONS
    }
    if tracked_manifest.get("f34_air_oil_forward_seed_inputs_sha256") != (
        _canonical_payload_sha256(forward_inputs)
    ):
        raise ValueError("air/oil seed mapping hash does not match F34 manifest")

    parent_hashes = {
        relative: _sha256(source_paths[relative])
        for _, relative, _ in PARENT_SPECS
    }
    release_gates = contract.get("release_gates")
    if (
        not isinstance(release_gates, dict)
        or set(release_gates) != RELEASE_GATE_IDS
        or any(value is not False for value in release_gates.values())
    ):
        raise ValueError("F34 release gates are not fail-closed")

    bundle: dict[str, Any] = {
        "$comment": (
            "Bundle autonome de seeds air/huile F34 pour construction de "
            "l'image F34b; aucune exécution solveur ni preuve physique."
        ),
        "schema_version": "1.0.0",
        "phase": "F34b",
        "status": (
            "deterministic_air_oil_forward_seed_bundle_zero_solver_cases_executed"
        ),
        "architecture_id": "F34A-AIR-OIL-CORE-2026-CONTROLS",
        "canonical_doe_cases_executed": 0,
        "parents": [
            {
                "id": parent_id,
                "path": relative,
                "sha256": parent_hashes[relative],
                "role": role,
            }
            for parent_id, relative, role in PARENT_SPECS
        ],
        "source_verification": {
            "f34_contract_validated_against_pinned_parents": True,
            "tracked_manifest_rebuilt_byte_for_byte": True,
            "f34a_air_oil_controls_semantics_validated": True,
            "air_oil_seed_mapping_sha256_matches_manifest": True,
        },
        "image_runtime_contract": {
            "bundle_is_self_contained_for_two_forward_inputs": True,
            "source_parents_required_only_at_bundle_generation": True,
            "f33_forward_solver_source_required_in_image": False,
            "f33_contract_required_in_image": False,
            "f34_generator_source_required_in_image": False,
            "network_required_to_load_bundle": False,
            "solver_execution_authorized": False,
        },
        "authority_boundary": {
            "classification": (
                "unvalidated_numerical_screening_seeds_not_calibration"
            ),
            "requested_power_target_present_in_forward_inputs": False,
            "requested_power_target_used_as_feature": False,
            "requested_power_target_used_for_calibration": False,
            "inverse_sizing_seed_ancestry_present": True,
            "full_target_independence_proven": False,
            "engine_core_liquid_coolant_present": False,
            "auxiliary_liquid_limited_to_charge_cooling_and_optional_turbo_chra": True,
            "controls_response_modeled": False,
            "physical_evidence_created": False,
        },
        "seeds": [
            {
                "variant_id": VARIANT_IDS[configuration],
                "configuration": configuration,
                "forward_input": copy.deepcopy(forward_inputs[configuration]),
                "forward_input_sha256": _canonical_payload_sha256(
                    forward_inputs[configuration]
                ),
            }
            for configuration in CONFIGURATIONS
        ],
        "execution_ledger": {
            "seed_count": 2,
            "solver_case_count": 0,
            "solver_executed": False,
            "labels_present": False,
            "calibration_executed": False,
            "training_executed": False,
            "physical_test_executed": False,
        },
        "physical_gates": {gate: False for gate in sorted(PHYSICAL_GATE_IDS)},
        "release_gates": copy.deepcopy(release_gates),
    }
    bundle["bundle_payload_sha256"] = _canonical_payload_sha256(bundle)
    bundle_errors = validate_bundle(
        bundle,
        expected_parent_hashes=parent_hashes,
    )
    if bundle_errors:
        raise ValueError("invalid generated F34b bundle:\n- " + "\n- ".join(bundle_errors))
    return bundle


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output", type=Path)
    action.add_argument("--check", type=Path)
    args = parser.parse_args(argv)

    try:
        bundle = build_bundle(project_root=ROOT)
        rendered = _canonical_json(bundle)
        if args.output is not None:
            destination = _safe_cli_json_path(
                args.output, project_root=ROOT, for_output=True
            )
            _atomic_write(destination, rendered)
        else:
            tracked = _safe_cli_json_path(
                args.check, project_root=ROOT, for_output=False
            )
            existing = tracked.read_text(encoding="utf-8")
            parsed = _read_json(tracked)
            validation_errors = validate_bundle(parsed)
            if validation_errors:
                raise ValueError(
                    "invalid checked F34b bundle:\n- "
                    + "\n- ".join(validation_errors)
                )
            if existing != rendered:
                raise ValueError(f"stale F34b seed bundle: {tracked}")
    except (
        ImportError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        print(f"F34b seed export error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
