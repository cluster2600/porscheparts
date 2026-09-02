#!/usr/bin/env python3
"""Construit et valide le contrat fail-closed F24 des variantes 917 retenues.

F24 reconcilie les identifiants et les cas solveurs des branches 5,0 L
atmospherique, 917/30 1973 turbo et record 1975 avec echangeurs. Il ne
transfere aucune cote, ne lie pas le scan a une variante, ne genere aucune
geometrie ou deck solveur et n'ouvre aucune autorite d'execution, PhysicsNeMo,
fabrication ou demarrage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_RELATIVE_PATH = Path(
    "twins/reference-917-engine/dual-variant-functional-readiness-f24.json"
)
ASSET_ID = "porsche-917-dual-variant-functional-readiness-f24"
NA_VARIANT = "type_912_5_0_na"
TURBO_VARIANT = "917_30_1973_turbo_5374"
RECORD_VARIANT = "917_30_1975_record_turbo_5374"
TARGET_VARIANTS = (NA_VARIANT, TURBO_VARIANT, RECORD_VARIANT)
NA_SCENARIO = "SCENARIO-917-5L-NA"
TURBO_SCENARIO = "SCENARIO-91730-1973-TURBO"
RECORD_SCENARIO = "SCENARIO-91730-1975-RECORD"
CASE_008 = "CASE-917-F13-008"
CASE_011 = "CASE-917-F13-011"
EXPECTED_CASE_IDS = tuple(f"CASE-917-F13-{index:03d}" for index in range(1, 13))
EXPECTED_CASE_REFS = {
    NA_VARIANT: tuple(case_id for case_id in EXPECTED_CASE_IDS if case_id != CASE_011),
    TURBO_VARIANT: tuple(case_id for case_id in EXPECTED_CASE_IDS if case_id != CASE_008),
    RECORD_VARIANT: ("CASE-917-F13-001", CASE_011),
}
SCENARIO_BY_VARIANT = {
    NA_VARIANT: NA_SCENARIO,
    TURBO_VARIANT: TURBO_SCENARIO,
    RECORD_VARIANT: RECORD_SCENARIO,
}
CYLINDER_COUNT_INPUT_BY_VARIANT = {
    NA_VARIANT: ("cylinder_count", "FACT-CYLINDER-COUNT"),
    TURBO_VARIANT: (
        "cylinder_count_91730_1973",
        "FACT-CYLINDER-COUNT-91730-1973",
    ),
    RECORD_VARIANT: (
        "cylinder_count_91730_1975",
        "FACT-CYLINDER-COUNT-91730-1975",
    ),
}
EXPECTED_TEMPLATE_COUNT = sum(len(items) for items in EXPECTED_CASE_REFS.values())

UPSTREAMS: dict[str, dict[str, str]] = {
    "variant_geometry_f10": {
        "path": "twins/reference-917-engine/variant-configurations-f10.json",
        "sha256": "dfb6ee25f367c934b11ff020e34d9d77296d2b5a535030a73221696af7c7a640",
        "reuse_scope": "display_only_variant_name_crosswalk_no_geometry_transfer",
    },
    "scan_metrology_f13": {
        "path": "twins/reference-917-engine/scan-metrology-f13.json",
        "sha256": "578b4ffcf49be04c701b3a86ba0b04d9cd11fd9f39f11b757c2220a698731a5d",
        "reuse_scope": "candidate_names_and_closed_scan_selection_policy_only",
    },
    "classical_solver_f13": {
        "path": "twins/reference-917-engine/classical-solver-cases-f13.json",
        "sha256": "1ec8a0c49e95f8f2c8185d4c0f4074d1ed4b36477996ba590cc9f92eccf42a97",
        "reuse_scope": "case_pair_registry_and_null_input_schema_only",
    },
    "bench_skeleton_f14": {
        "path": "twins/reference-917-engine/bench-executable-skeleton-f14.json",
        "sha256": "718151c342b31ab918b7a02f4f2ae954b3ff5ff323757dd9158397f48e4dde59",
        "reuse_scope": "semantic_runtime_boundary_only_no_engine_physics",
    },
    "physicsnemo_dataset_f14": {
        "path": "twins/reference-917-engine/physicsnemo-dataset-f14.json",
        "sha256": "da0ad83ebc05aa7e5aafaf653ed3f16caebcdf1fb1bc0122e6079d1ca3784d5e",
        "reuse_scope": "dataset_schema_and_zero_sample_boundary_only",
    },
    "kinematic_readiness_f16": {
        "path": "twins/reference-917-engine/kinematic-interface-readiness-f16.json",
        "sha256": "ec5e56cdd750071462e00dcec978182916ee4c266435bfea0720dea2fda2f2e2",
        "reuse_scope": "na_engineering_branch_name_and_null_policy_only",
    },
    "scan_scale_orientation_f21": {
        "path": "twins/reference-917-engine/scan-scale-orientation-acquisition-f21.json",
        "sha256": "e958bc9188fb05dbe02e131cdc12f3e466eaa93aa2772e930bf91f733f2d924b",
        "reuse_scope": "closed_scan_identity_scale_orientation_gates_only",
    },
    "parametric_cad_f22": {
        "path": "twins/reference-917-engine/parametric-cad-assembly-contract-f22.json",
        "sha256": "87529899d643dd437f357c79fa4dd4fa5ac5ed95929c4fdf82c4985222fd6baa",
        "reuse_scope": "schema_and_null_policy_only_no_4494_values_or_geometry_transferred",
    },
}


class ContractError(ValueError):
    """Un amont suivi ou le contrat F24 franchit sa frontiere d'autorite."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"missing_input:{path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid_json:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_json_object:{path}")
    return value


def _all_false(value: Any) -> bool:
    if isinstance(value, bool):
        return value is False
    if isinstance(value, dict):
        return all(_all_false(item) for item in value.values())
    if isinstance(value, list):
        return all(_all_false(item) for item in value)
    return True


def _by_id(items: Any, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        raise ContractError(f"{label}_missing")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ContractError(f"{label}_record_invalid")
        if item["id"] in result:
            raise ContractError(f"{label}_duplicate:{item['id']}")
        result[item["id"]] = item
    return result


def _validate_f13_solver_registry(f13: dict[str, Any]) -> None:
    if (
        f13.get("phase") != "F13"
        or f13.get("status")
        != "reference_solver_case_definitions_ready_all_execution_and_release_gates_blocked"
    ):
        raise ContractError("f13_solver_contract_mismatch")
    authority = f13.get("authority_boundary", {})
    for key in (
        "solver_execution_authorized",
        "results_present",
        "correlation_complete",
        "engine_start_authorized",
        "fabrication_authorized",
        "metal_print_authorized",
        "physicsnemo_training_authorized",
    ):
        if authority.get(key) is not False:
            raise ContractError(f"f13_solver_authority_must_remain_false:{key}")

    cases = _by_id(f13.get("solver_cases"), "f13_solver_cases")
    if tuple(cases) != EXPECTED_CASE_IDS:
        raise ContractError("f13_solver_case_ids_mismatch")
    scenarios = _by_id(f13.get("solver_scenarios"), "f13_solver_scenarios")
    for variant_id, scenario_id in SCENARIO_BY_VARIANT.items():
        scenario = scenarios.get(scenario_id)
        if not isinstance(scenario, dict) or scenario.get("variant") != variant_id:
            raise ContractError(f"f13_solver_scenario_mismatch:{variant_id}")
        if tuple(scenario.get("case_refs", [])) != EXPECTED_CASE_REFS[variant_id]:
            raise ContractError(f"f13_solver_scenario_case_refs_mismatch:{variant_id}")
        if scenario.get("execution_authorized") is not False:
            raise ContractError(f"f13_solver_scenario_execution_must_be_false:{variant_id}")
        for case_id in EXPECTED_CASE_REFS[variant_id]:
            case = cases[case_id]
            if variant_id not in case.get("variants", []):
                raise ContractError(f"f13_solver_pair_missing:{variant_id}:{case_id}")
            execution = case.get("execution", {})
            if execution.get("authorized") is not False or execution.get(
                "results_present"
            ) is not False:
                raise ContractError(f"f13_solver_case_gate_open:{case_id}")

    facts = _by_id(f13.get("fact_registry"), "f13_fact_registry")
    reported = facts.get("FACT-TURBO-POWER-1600-REPORTED", {})
    if (
        reported.get("usage") != "documentary_claim_not_calibration_target"
        or reported.get("design_lock") is not False
    ):
        raise ContractError("f13_reported_1600_scope_mismatch")
    record_intercooler = facts.get("FACT-INTERCOOLER-1975-STATUS", {})
    if (
        record_intercooler.get("variant") != RECORD_VARIANT
        or record_intercooler.get("candidate")
        != {
            "kind": "published_sequence",
            "value": "fitted_first_documented_use",
            "unit": "categorical",
        }
        or record_intercooler.get("source_refs")
        != ["SRC-PORSCHE-NEWSROOM-91730-AM-LIMIT"]
        or record_intercooler.get("usage")
        != "variant_separation_only_maps_geometry_and_count_unknown"
        or record_intercooler.get("design_lock") is not False
    ):
        raise ContractError("f13_record_1975_intercooler_scope_mismatch")

    valve_fact_refs = {
        "FACT-INTAKE-VALVE-DIAMETER-CANDIDATE",
        "FACT-EXHAUST-VALVE-DIAMETER-CANDIDATE",
    }
    duct_case = cases["CASE-917-F13-004"]
    duct_inputs = {
        item.get("id"): item
        for item in duct_case.get("inputs", [])
        if isinstance(item, dict)
    }
    for input_id in ("intake_valve_diameter", "exhaust_valve_diameter"):
        item = duct_inputs.get(input_id, {})
        if (
            item.get("status") != "unknown"
            or item.get("candidate_ref") is not None
            or item.get("required") is not True
            or input_id not in duct_case.get("blocking_unknowns", [])
        ):
            raise ContractError(f"f13_fia_valve_transfer_forbidden:{input_id}")
    if any(
        item.get("candidate_ref") in valve_fact_refs
        for case in cases.values()
        for item in case.get("inputs", [])
        if isinstance(item, dict)
    ):
        raise ContractError("f13_fia_valve_solver_transfer_forbidden")

    nonspecific_turbo_claim_refs = {
        "FACT-TURBO-BOOST-CANDIDATE",
        "FACT-TURBO-SPOOL-QUALITATIVE",
    }
    turbo_case = cases[CASE_011]
    if any(
        item.get("candidate_ref") in nonspecific_turbo_claim_refs
        for item in turbo_case.get("inputs", [])
        if isinstance(item, dict)
    ):
        raise ContractError("f13_nonspecific_boost_spool_solver_input_forbidden")
    record_scenario = scenarios[RECORD_SCENARIO]
    if nonspecific_turbo_claim_refs.intersection(record_scenario.get("fact_refs", [])):
        raise ContractError("f13_record_nonspecific_boost_spool_claim_forbidden")


def load_and_validate_upstreams(root: Path) -> dict[str, dict[str, Any]]:
    root = root.resolve()
    result: dict[str, dict[str, Any]] = {}
    for source_id, specification in UPSTREAMS.items():
        path = root / specification["path"]
        if sha256(path) != specification["sha256"]:
            raise ContractError(f"upstream_sha256_mismatch:{source_id}")
        result[source_id] = load_json(path)

    f10 = result["variant_geometry_f10"]
    if (
        f10.get("phase") != "F10"
        or f10.get("status")
        != "separate_sourced_variant_geometry_and_visual_kinematics_not_manufacturing_geometry"
    ):
        raise ContractError("f10_contract_mismatch")
    f10_variants = {
        item.get("variant_id"): item
        for item in f10.get("variants", [])
        if isinstance(item, dict)
    }
    if set(f10_variants) != {"type_912_4_5_na", "917_30_turbo_5374"}:
        raise ContractError("f10_variant_ids_mismatch")
    for variant_id, record in f10_variants.items():
        if record.get("kinematics", {}).get("physical_kinematics_ready") is not False:
            raise ContractError(f"f10_physical_kinematics_must_be_false:{variant_id}")
    for key in (
        "measured_variant_geometry_ready",
        "physical_kinematics_ready",
        "manufacturing_geometry_ready",
        "clearance_validation_ready",
        "combustion_simulation_ready",
        "performance_claim_authorized",
    ):
        if f10.get("release_gates", {}).get(key) is not False:
            raise ContractError(f"f10_physical_gate_must_remain_false:{key}")

    scan = result["scan_metrology_f13"]
    if (
        scan.get("phase") != "F13"
        or scan.get("status") != "hypothesis_only_physical_calibration_missing"
        or scan.get("derivation_policy", {}).get("selection_allowed") is not False
    ):
        raise ContractError("f13_scan_contract_mismatch")
    scan_candidates = {
        item.get("variant_id")
        for item in scan.get("public_facts", {}).get("candidate_bores", [])
        if isinstance(item, dict)
    }
    if "917_5_0_na" not in scan_candidates:
        raise ContractError("f13_scan_5l_candidate_missing")
    if not _all_false(
        {
            key: value
            for key, value in scan.get("release_authority", {}).items()
            if isinstance(value, bool)
        }
    ):
        raise ContractError("f13_scan_release_authority_must_remain_false")

    _validate_f13_solver_registry(result["classical_solver_f13"])

    bench = result["bench_skeleton_f14"]
    if (
        bench.get("phase") != "F14"
        or bench.get("status")
        != "bench_executable_skeleton_contract_ready_engine_physics_blocked"
    ):
        raise ContractError("f14_bench_contract_mismatch")
    authoring = bench.get("authoring_policy", {})
    for key in (
        "new_usd_physics_schemas",
        "new_physics_joint_count",
        "new_rigid_body_count",
        "new_collision_shape_count",
        "new_cfd_volume_count",
    ):
        if authoring.get(key) != 0:
            raise ContractError(f"f14_bench_physics_count_must_be_zero:{key}")
    for key in ("engine_physics_validated", "fluid_simulation_ready", "fired_run_authorized"):
        if bench.get("acceptance", {}).get(key) is not False:
            raise ContractError(f"f14_bench_gate_must_remain_false:{key}")

    dataset = result["physicsnemo_dataset_f14"]
    if (
        dataset.get("phase") != "F14"
        or dataset.get("status")
        != "dataset_contract_ready_zero_samples_training_blocked"
    ):
        raise ContractError("f14_dataset_contract_mismatch")
    authority = dataset.get("authority_boundary", {})
    if authority.get("accepted_sample_count") != 0 or authority.get(
        "classical_cases_passed"
    ) != 0:
        raise ContractError("f14_dataset_counts_must_be_zero")
    for key, value in authority.items():
        if key not in {"contract_only", "accepted_sample_count", "classical_cases_passed"} and isinstance(value, bool) and value is not False:
            raise ContractError(f"f14_dataset_authority_must_remain_false:{key}")

    f16 = result["kinematic_readiness_f16"]
    if (
        f16.get("phase") != "F16-001"
        or f16.get("work_branch", {}).get("variant_id") != NA_VARIANT
        or f16.get("work_branch", {}).get("scan_binding") is not False
        or not _all_false(f16.get("release_gates", {}))
    ):
        raise ContractError("f16_contract_or_gate_mismatch")

    f21 = result["scan_scale_orientation_f21"]
    if f21.get("phase") != "F21" or not _all_false(f21.get("release_gates", {})):
        raise ContractError("f21_contract_or_gate_mismatch")
    for key in ("identity_ready", "scale_ready", "orientation_ready", "cad_input_ready"):
        if f21.get("current_readiness", {}).get(key) is not False:
            raise ContractError(f"f21_readiness_must_remain_false:{key}")

    f22 = result["parametric_cad_f22"]
    if (
        f22.get("phase") != "F22"
        or f22.get("asset", {}).get("variant_id") != "type_912_4_5_na"
        or f22.get("branch_scope", {}).get("f16_reuse") != "schema_and_null_policy_only"
        or f22.get("branch_scope", {}).get("turbo_parts_in_scope") is not False
        or not _all_false(f22.get("release_gates", {}))
    ):
        raise ContractError("f22_contract_scope_or_gate_mismatch")
    return result


def _upstream_records() -> list[dict[str, Any]]:
    return [
        {
            "id": source_id,
            "path": specification["path"],
            "sha256": specification["sha256"],
            "reuse_scope": specification["reuse_scope"],
            "geometry_authority": False,
            "solver_execution_authority": False,
            "manufacturing_authority": False,
        }
        for source_id, specification in UPSTREAMS.items()
    ]


def _template(
    variant_id: str,
    scenario_id: str,
    case: dict[str, Any],
    facts: dict[str, dict[str, Any]],
    ranges: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inputs = []
    for source in case["inputs"]:
        source_variants = source.get("variants")
        if isinstance(source_variants, list) and variant_id not in source_variants:
            continue
        candidate_ref = source.get("candidate_ref")
        if candidate_ref is None:
            evidence_variants = []
        elif isinstance(source_variants, list):
            evidence_variants = list(source_variants)
        elif candidate_ref in facts:
            fact_variant = facts[candidate_ref].get("variant")
            evidence_variants = [fact_variant] if isinstance(fact_variant, str) else []
        elif candidate_ref in ranges:
            evidence_variants = []
            for fact_ref in ranges[candidate_ref].get("component_fact_refs", []):
                fact_variant = facts.get(fact_ref, {}).get("variant")
                if isinstance(fact_variant, str) and fact_variant not in evidence_variants:
                    evidence_variants.append(fact_variant)
        else:
            evidence_variants = []
        inputs.append(
            {
                "id": source["id"],
                "quantity": source["quantity"],
                "unit": source["unit"],
                "required": source["required"],
                "source_status": source["status"],
                "candidate_ref": candidate_ref,
                "input_variant_scope": [variant_id],
                "source_variant_scope": evidence_variants,
                "candidate_adopted": False,
                "value": None,
                "uncertainty": None,
                "evidence_manifest_ref": None,
                "review_status": None,
            }
        )
    outputs = [
        {
            "quantity": source["quantity"],
            "unit": source["unit"],
            "status": "not_computed",
            "value": None,
            "artifact_ref": None,
        }
        for source in case["expected_outputs"]
    ]
    return {
        "template_id": f"F24-{variant_id}-{case['id']}",
        "variant_id": variant_id,
        "scenario_ref": scenario_id,
        "case_id": case["id"],
        "domain": case["domain"],
        "gate_profile_ref": case["gate_profile_ref"],
        "status": "template_only_execution_blocked",
        "inputs": inputs,
        "blocking_unknowns": list(
            case.get("variant_blocking_unknowns", {}).get(
                variant_id, case["blocking_unknowns"]
            )
        ),
        "acceptance_requirements": list(case["case_acceptance_requirements"]),
        "expected_outputs": outputs,
        "geometry_state": {
            "cad_path": None,
            "cad_sha256": None,
            "variant_identity_verified": False,
            "scale_verified": False,
            "interface_fidelity_verified": False,
        },
        "solver_runtime": {
            "solver_name": None,
            "solver_version": None,
            "container_digest": None,
            "source_commit": None,
        },
        "boundary_conditions_manifest": None,
        "acceptance_criteria_manifest": None,
        "execution": {
            "authorized": False,
            "attempted": False,
            "results_present": False,
        },
        "physicsnemo_export": {
            "authorized": False,
            "sample_manifest": None,
        },
    }


def build_contract(root: Path) -> dict[str, Any]:
    upstreams = load_and_validate_upstreams(root)
    f13 = upstreams["classical_solver_f13"]
    cases = _by_id(f13["solver_cases"], "f13_solver_cases")
    facts = _by_id(f13["fact_registry"], "f13_fact_registry")
    ranges = _by_id(f13["candidate_ranges"], "f13_candidate_ranges")

    templates = [
        _template(
            variant_id,
            SCENARIO_BY_VARIANT[variant_id],
            cases[case_id],
            facts,
            ranges,
        )
        for variant_id in TARGET_VARIANTS
        for case_id in EXPECTED_CASE_REFS[variant_id]
    ]
    case_matrix = []
    for case_id in EXPECTED_CASE_IDS:
        case = cases[case_id]
        case_matrix.append(
            {
                "case_id": case_id,
                "domain": case["domain"],
                "gate_profile_ref": case["gate_profile_ref"],
                "applicability": {
                    NA_VARIANT: (
                        "not_applicable_turbo_only" if case_id == CASE_011 else "required"
                    ),
                    TURBO_VARIANT: (
                        "blocked_variant_scope_missing" if case_id == CASE_008 else "required"
                    ),
                    RECORD_VARIANT: (
                        "required"
                        if case_id in EXPECTED_CASE_REFS[RECORD_VARIANT]
                        else "not_in_record_documentary_scope"
                    ),
                },
                "input_template_status": "generated_null_only",
                "execution_authorized": False,
                "results_present": False,
                "physicsnemo_sample_authorized": False,
            }
        )

    return {
        "$comment": (
            "F24 materialise uniquement un crosswalk et 24 templates d'entrees nuls. "
            "Il ne lie pas le scan, ne transfere aucune cote F10/F22, ne lance aucun "
            "solveur et ne constitue aucune preuve fonctionnelle."
        ),
        "schema_version": "1.0.0",
        "phase": "F24",
        "status": "dual_variant_crosswalk_and_null_input_templates_ready_all_execution_and_release_gates_blocked",
        "asset": {
            "id": ASSET_ID,
            "target_roles": [
                "naturally_aspirated",
                "917_30_turbo_1973",
                "917_30_record_1975_intercooled",
            ],
            "functional_claim": False,
            "geometry_generated": False,
            "solver_decks_generated": False,
            "solver_results_present": False,
        },
        "upstream_contracts": _upstream_records(),
        "scan_evidence_boundary": {
            "tracked_contract_ref": "scan_metrology_f13",
            "local_report_path": "work/917-engine/scan-metrology-f13-report.json",
            "local_report_required_for_contract_validation": False,
            "selected_variant_id": None,
            "scan_binding_authorized": False,
            "visible_opening_semantics_verified": False,
            "closest_numerical_candidate_id": "917_5_0_na",
            "canonical_crosswalk_target": NA_VARIANT,
            "crosswalk_scope": "name_alignment_only_not_identity",
            "identity_verified": False,
            "scale_verified": False,
            "dimensional_fit_verified": False,
        },
        "variant_crosswalk": [
            {
                "role": "naturally_aspirated",
                "canonical_variant_id": NA_VARIANT,
                "solver_scenario_ref": NA_SCENARIO,
                "case_refs": list(EXPECTED_CASE_REFS[NA_VARIANT]),
                "case_count": len(EXPECTED_CASE_REFS[NA_VARIANT]),
                "selection_status": "engineering_reference_only_not_scan_identification",
                "selection_basis": [
                    "f13_first_classical_baseline_candidate",
                    "f16_engineering_reference_branch",
                ],
                "selection_basis_excludes": ["scan_numerical_proximity"],
                "scan_candidate_id": "917_5_0_na",
                "scan_candidate_mapping_scope": "name_crosswalk_only_not_identity",
                "f10_visual_variant_id": None,
                "f22_cad_variant_id": None,
                "nontransferable_contract_refs": [
                    {
                        "contract_id": "parametric_cad_f22",
                        "variant_id": "type_912_4_5_na",
                        "reuse_scope": "schema_and_null_policy_only",
                    }
                ],
                "geometry_ready": False,
                "solver_ready": False,
            },
            {
                "role": "917_30_turbo",
                "canonical_variant_id": TURBO_VARIANT,
                "solver_scenario_ref": TURBO_SCENARIO,
                "case_refs": list(EXPECTED_CASE_REFS[TURBO_VARIANT]),
                "case_count": len(EXPECTED_CASE_REFS[TURBO_VARIANT]),
                "selection_status": "engineering_reference_only_unbound",
                "f10_visual_variant_id": "917_30_turbo_5374",
                "f10_mapping_scope": "display_only_visual_lineage",
                "f10_identity_equivalent": False,
                "f22_cad_variant_id": None,
                "reported_1600_hp_fact_ref": "FACT-TURBO-POWER-1600-REPORTED",
                "reported_1600_hp_role": "documentary_only_not_boundary_condition",
                "geometry_ready": False,
                "solver_ready": False,
            },
            {
                "role": "917_30_record_1975_intercooled",
                "canonical_variant_id": RECORD_VARIANT,
                "solver_scenario_ref": RECORD_SCENARIO,
                "case_refs": list(EXPECTED_CASE_REFS[RECORD_VARIANT]),
                "case_count": len(EXPECTED_CASE_REFS[RECORD_VARIANT]),
                "selection_status": "separate_documentary_record_configuration_only",
                "parent_1973_variant_ref": TURBO_VARIANT,
                "hardware_identity_equivalent_to_1973": False,
                "intercooler_status_fact_ref": "FACT-INTERCOOLER-1975-STATUS",
                "intercooler_presence_role": "documentary_variant_separator_only",
                "intercooler_count": None,
                "intercooler_geometry": None,
                "intercooler_maps": None,
                "turbocharger_count": None,
                "geometry_ready": False,
                "solver_ready": False,
            },
        ],
        "case_matrix": case_matrix,
        "solver_input_templates": templates,
        "physicsnemo_boundary": {
            "source_contract_ref": "physicsnemo_dataset_f14",
            "accepted_samples": 0,
            "classical_cases_passed": 0,
            "dataset_ready": False,
            "model_selected": False,
            "training_authorized": False,
            "inference_authorized": False,
            "variant_case_pair_validation_required": True,
            "allowed_variant_case_pairs_source": "solver_input_templates",
            "raw_scan_or_f10_proxy_allowed": False,
        },
        "generated_outputs": {
            "tracked_contract_path": str(OUTPUT_RELATIVE_PATH),
            "generated_now": [
                "case_applicability_matrix",
                "24_null_solver_input_templates",
                "variant_crosswalk",
            ],
            "geometry_artifacts": [],
            "solver_decks": [],
            "solver_results": [],
            "physicsnemo_samples": [],
            "local_f14_outputs_modified": False,
        },
        "release_gates": {
            "scan_identity_verified": False,
            "na_variant_identity_verified": False,
            "turbo_variant_identity_verified": False,
            "record_1975_variant_identity_verified": False,
            "na_dimensioned_cad_ready": False,
            "turbo_dimensioned_cad_ready": False,
            "record_1975_dimensioned_cad_ready": False,
            "na_solver_execution_authorized": False,
            "turbo_solver_execution_authorized": False,
            "record_1975_solver_execution_authorized": False,
            "na_reference_cases_correlated": False,
            "turbo_reference_cases_correlated": False,
            "record_1975_reference_cases_correlated": False,
            "physicsnemo_dataset_ready": False,
            "physicsnemo_training_authorized": False,
            "instrumented_bench_validated": False,
            "functional_variants_authorized": False,
            "manufacturing_authorized": False,
        },
        "prohibited_claims": [
            "scan_numerical_proximity_proves_variant_identity",
            "f10_visual_stage_is_solver_or_manufacturing_geometry",
            "f22_4494_values_or_geometry_transfer_to_5l_or_turbo",
            "f10_generic_turbo_id_equals_f13_1973_identity",
            "1973_turbo_inherits_1975_intercoolers_or_maps",
            "1975_record_inherits_1973_hardware_identity_or_turbo_count",
            "reported_1600_hp_is_a_boundary_condition_or_result",
            "physicsnemo_import_or_sample_structure_proves_simulation",
            "f24_opens_any_execution_release_or_manufacturing_gate",
        ],
    }


def _validate_template_nulls(template: dict[str, Any], errors: list[str]) -> None:
    label = template.get("template_id")
    for item in template.get("inputs", []):
        input_id = item.get("id")
        for key in ("value", "uncertainty", "evidence_manifest_ref", "review_status"):
            if item.get(key) is not None:
                errors.append(f"template_input_value_must_be_null:{label}:{input_id}:{key}")
        if item.get("candidate_adopted") is not False:
            errors.append(f"template_candidate_adoption_forbidden:{label}:{input_id}")
    for item in template.get("expected_outputs", []):
        for key in ("value", "artifact_ref"):
            if item.get(key) is not None:
                errors.append(f"template_output_value_must_be_null:{label}:{key}")
    for section, keys in {
        "geometry_state": ("cad_path", "cad_sha256"),
        "solver_runtime": (
            "solver_name",
            "solver_version",
            "container_digest",
            "source_commit",
        ),
    }.items():
        for key in keys:
            if template.get(section, {}).get(key) is not None:
                errors.append(f"template_value_must_be_null:{label}:{section}:{key}")
    for key in ("boundary_conditions_manifest", "acceptance_criteria_manifest"):
        if template.get(key) is not None:
            errors.append(f"template_value_must_be_null:{label}:{key}")
    if template.get("physicsnemo_export", {}).get("sample_manifest") is not None:
        errors.append(f"template_value_must_be_null:{label}:physicsnemo_sample_manifest")
    if not _all_false(template.get("geometry_state", {})):
        errors.append(f"template_geometry_gate_open:{label}")
    if not _all_false(template.get("execution", {})):
        errors.append(f"template_execution_gate_open:{label}")
    if template.get("physicsnemo_export", {}).get("authorized") is not False:
        errors.append(f"template_physicsnemo_gate_open:{label}")


def _validate_template_scopes(
    template: dict[str, Any],
    expected_template: dict[str, Any],
    errors: list[str],
) -> None:
    label = template.get("template_id")
    variant_id = template.get("variant_id")
    expected_inputs = {
        item.get("id"): item
        for item in expected_template.get("inputs", [])
        if isinstance(item, dict)
    }
    for item in template.get("inputs", []):
        input_id = item.get("id")
        if item.get("input_variant_scope") != [variant_id]:
            errors.append(f"template_input_variant_scope_mismatch:{label}:{input_id}")
        expected_input = expected_inputs.get(input_id, {})
        if item.get("source_variant_scope") != expected_input.get(
            "source_variant_scope"
        ):
            errors.append(f"template_source_variant_scope_mismatch:{label}:{input_id}")


def validate_contract(root: Path, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        expected = build_contract(root)
    except (ContractError, OSError, ValueError) as exc:
        return [str(exc)]

    if contract.get("phase") != "F24":
        errors.append("phase_mismatch")
    if contract.get("asset", {}).get("id") != ASSET_ID:
        errors.append("asset_id_mismatch")
    if not _all_false(contract.get("release_gates", {})):
        errors.append("release_gates_must_remain_false")
    asset = contract.get("asset", {})
    for key in (
        "functional_claim",
        "geometry_generated",
        "solver_decks_generated",
        "solver_results_present",
    ):
        if asset.get(key) is not False:
            errors.append(f"asset_gate_must_remain_false:{key}")

    scan = contract.get("scan_evidence_boundary", {})
    if scan.get("selected_variant_id") is not None:
        errors.append("scan_selected_variant_must_be_null")
    for key in (
        "scan_binding_authorized",
        "visible_opening_semantics_verified",
        "identity_verified",
        "scale_verified",
        "dimensional_fit_verified",
    ):
        if scan.get(key) is not False:
            errors.append(f"scan_gate_must_remain_false:{key}")
    if scan.get("local_report_required_for_contract_validation") is not False:
        errors.append("local_scan_report_must_remain_optional")

    crosswalk = {
        item.get("canonical_variant_id"): item
        for item in contract.get("variant_crosswalk", [])
        if isinstance(item, dict)
    }
    if set(crosswalk) != set(TARGET_VARIANTS):
        errors.append("variant_crosswalk_mismatch")
    else:
        na = crosswalk[NA_VARIANT]
        turbo = crosswalk[TURBO_VARIANT]
        record = crosswalk[RECORD_VARIANT]
        if na.get("f10_visual_variant_id") is not None or na.get("f22_cad_variant_id") is not None:
            errors.append("na_geometry_lineage_forbidden")
        if turbo.get("f10_mapping_scope") != "display_only_visual_lineage":
            errors.append("turbo_f10_mapping_must_be_display_only")
        if turbo.get("f10_identity_equivalent") is not False:
            errors.append("turbo_f10_identity_equivalence_forbidden")
        if turbo.get("f22_cad_variant_id") is not None:
            errors.append("turbo_f22_geometry_lineage_forbidden")
        if turbo.get("reported_1600_hp_role") != "documentary_only_not_boundary_condition":
            errors.append("reported_1600_hp_boundary_or_result_forbidden")
        if (
            record.get("parent_1973_variant_ref") != TURBO_VARIANT
            or record.get("hardware_identity_equivalent_to_1973") is not False
            or record.get("intercooler_status_fact_ref")
            != "FACT-INTERCOOLER-1975-STATUS"
            or record.get("intercooler_presence_role")
            != "documentary_variant_separator_only"
            or any(
                record.get(key) is not None
                for key in (
                    "intercooler_count",
                    "intercooler_geometry",
                    "intercooler_maps",
                    "turbocharger_count",
                )
            )
        ):
            errors.append("record_1975_scope_mismatch")
        for variant_id, record in crosswalk.items():
            if record.get("geometry_ready") is not False or record.get("solver_ready") is not False:
                errors.append(f"variant_readiness_gate_open:{variant_id}")

    matrix = {
        item.get("case_id"): item
        for item in contract.get("case_matrix", [])
        if isinstance(item, dict)
    }
    if tuple(matrix) != EXPECTED_CASE_IDS:
        errors.append("case_matrix_mismatch")
    elif (
        matrix[CASE_008].get("applicability")
        != {
            NA_VARIANT: "required",
            TURBO_VARIANT: "blocked_variant_scope_missing",
            RECORD_VARIANT: "not_in_record_documentary_scope",
        }
        or matrix[CASE_011].get("applicability")
        != {
            NA_VARIANT: "not_applicable_turbo_only",
            TURBO_VARIANT: "required",
            RECORD_VARIANT: "required",
        }
    ):
        errors.append("special_case_applicability_mismatch")
    for case_id, record in matrix.items():
        for key in (
            "execution_authorized",
            "results_present",
            "physicsnemo_sample_authorized",
        ):
            if record.get(key) is not False:
                errors.append(f"case_matrix_gate_open:{case_id}:{key}")

    templates = contract.get("solver_input_templates", [])
    if not isinstance(templates, list) or len(templates) != EXPECTED_TEMPLATE_COUNT:
        errors.append("solver_input_template_count_mismatch")
        templates = []
    actual_pairs = [
        (item.get("variant_id"), item.get("case_id"))
        for item in templates
        if isinstance(item, dict)
    ]
    expected_pairs = [
        (variant_id, case_id)
        for variant_id in TARGET_VARIANTS
        for case_id in EXPECTED_CASE_REFS[variant_id]
    ]
    if actual_pairs != expected_pairs or len(set(actual_pairs)) != EXPECTED_TEMPLATE_COUNT:
        errors.append("solver_input_template_pairs_mismatch")
    expected_templates = {
        (item["variant_id"], item["case_id"]): item
        for item in expected["solver_input_templates"]
    }
    for template in templates:
        _validate_template_nulls(template, errors)
        variant_id = template.get("variant_id")
        expected_template = expected_templates.get(
            (variant_id, template.get("case_id")), {}
        )
        _validate_template_scopes(template, expected_template, errors)
        if template.get("case_id") == "CASE-917-F13-001" and variant_id in (
            CYLINDER_COUNT_INPUT_BY_VARIANT
        ):
            count_inputs = [
                item
                for item in template.get("inputs", [])
                if item.get("quantity") == "cylinder_count"
            ]
            input_id, fact_id = CYLINDER_COUNT_INPUT_BY_VARIANT[variant_id]
            if len(count_inputs) != 1 or (
                count_inputs[0].get("id"), count_inputs[0].get("candidate_ref")
            ) != (input_id, fact_id):
                errors.append(f"variant_cylinder_count_template_mismatch:{variant_id}")
        if variant_id == RECORD_VARIANT and template.get("case_id") == CASE_011:
            record_input_ids = {
                item.get("id")
                for item in template.get("inputs", [])
                if isinstance(item, dict)
            }
            if {"boost_claim", "spool_claim"}.intersection(record_input_ids):
                errors.append("record_1975_nonspecific_boost_spool_input_forbidden")

    physicsnemo = contract.get("physicsnemo_boundary", {})
    if physicsnemo.get("accepted_samples") != 0 or physicsnemo.get(
        "classical_cases_passed"
    ) != 0:
        errors.append("physicsnemo_counts_must_be_zero")
    for key in (
        "dataset_ready",
        "model_selected",
        "training_authorized",
        "inference_authorized",
        "raw_scan_or_f10_proxy_allowed",
    ):
        if physicsnemo.get(key) is not False:
            errors.append(f"physicsnemo_gate_must_remain_false:{key}")

    generated = contract.get("generated_outputs", {})
    for key in ("geometry_artifacts", "solver_decks", "solver_results", "physicsnemo_samples"):
        if generated.get(key) != []:
            errors.append(f"generated_artifacts_forbidden:{key}")
    if generated.get("local_f14_outputs_modified") is not False:
        errors.append("local_f14_output_mutation_forbidden")

    if contract != expected:
        errors.append("contract_differs_from_deterministic_source")
    return sorted(set(errors))


def evaluate(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    errors = validate_contract(root, contract)
    return {
        "schema_version": "1.0.0",
        "phase": "F24",
        "asset_id": ASSET_ID,
        "report_status": "passed" if not errors else "failed",
        "contract_errors": errors,
        "variant_count": len(TARGET_VARIANTS),
        "solver_input_template_count": EXPECTED_TEMPLATE_COUNT,
        "release": {
            "scan_binding": False,
            "geometry": False,
            "solver_execution": False,
            "physicsnemo": False,
            "fabrication": False,
            "functional_engine": False,
        },
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    root = arguments.root.resolve()
    output = arguments.output or (root / OUTPUT_RELATIVE_PATH)
    if arguments.check:
        contract = load_json(output)
    else:
        contract = build_contract(root)
        write_json(output, contract)

    report = evaluate(root, contract)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["report_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
