#!/usr/bin/env python3
"""Valide le registre F13 des solveurs classiques du moteur 917.

Le validateur controle la provenance, les unites, les plages derivees, les
inconnues et les frontieres d'autorite. Il ne lance aucun solveur et ne cree
aucune preuve de convergence, de correlation ou de fabrication.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EXPECTED_CASES = {
    "CASE-917-F13-001": "engine_cycle_0d_1d",
    "CASE-917-F13-002": "lubrication_0d_1d_and_local_3d",
    "CASE-917-F13-003": "air_cooling_1d_and_3d_cfd",
    "CASE-917-F13-004": "internal_duct_cfd",
    "CASE-917-F13-005": "conjugate_heat_transfer_head_cylinder",
    "CASE-917-F13-006": "structural_thermomechanical_fea_crankcase",
    "CASE-917-F13-007": "structural_fatigue_fea_connecting_rods",
    "CASE-917-F13-008": "structural_thermomechanical_fea_head_studs",
    "CASE-917-F13-009": "multibody_valvetrain_dynamics",
    "CASE-917-F13-010": "crankshaft_gear_rotordynamics",
    "CASE-917-F13-011": "turbocharger_1d_cfd_and_rotordynamics",
    "CASE-917-F13-012": "electrical_ignition_and_safety_network",
}

REQUIRED_GATE_SECTIONS = (
    "discretization",
    "convergence",
    "correlation",
    "acceptance",
)

ALLOWED_CANDIDATE_KINDS = {
    "published_point",
    "published_point_ambiguous_reference",
    "published_sequence",
    "published_approximation",
    "reported_claim",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _unique_objects(
    items: Any, key: str, label: str, errors: list[str]
) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list) or not items:
        errors.append(f"{label}_missing_or_empty")
        return {}
    index: dict[str, dict[str, Any]] = {}
    for position, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{label}_{position}_not_object")
            continue
        identifier = item.get(key)
        if not isinstance(identifier, str) or not identifier:
            errors.append(f"{label}_{position}_{key}_missing")
            continue
        if identifier in index:
            errors.append(f"{label}_duplicate:{identifier}")
            continue
        index[identifier] = item
    return index


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _validate_authority(contract: dict[str, Any], errors: list[str]) -> None:
    authority = contract.get("authority_boundary")
    if not isinstance(authority, dict):
        errors.append("authority_boundary_missing")
        return
    required_false = (
        "solver_execution_authorized",
        "results_present",
        "correlation_complete",
        "engine_start_authorized",
        "fabrication_authorized",
        "metal_print_authorized",
        "physicsnemo_training_authorized",
    )
    for key in required_false:
        if authority.get(key) is not False:
            errors.append(f"authority_must_be_false:{key}")
    if authority.get("specification_only") is not True:
        errors.append("authority_specification_only_must_be_true")


def _validate_sources(
    contract: dict[str, Any], root: Path, errors: list[str]
) -> dict[str, dict[str, Any]]:
    sources = _unique_objects(
        contract.get("source_registry"), "source_id", "source", errors
    )
    for source_id, source in sources.items():
        if source.get("rights") != "reference_only":
            errors.append(f"source_not_reference_only:{source_id}")
        raw_path = source.get("catalog_path")
        if not isinstance(raw_path, str) or not raw_path:
            errors.append(f"source_catalog_path_missing:{source_id}")
            continue
        path = (root / raw_path).resolve()
        if not _inside(path, root):
            errors.append(f"source_catalog_path_outside_project:{source_id}")
            continue
        if not path.is_file():
            errors.append(f"source_catalog_missing:{source_id}")
            continue
        try:
            catalog = load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"source_catalog_invalid:{source_id}:{exc}")
            continue
        if catalog.get("source_id") != source_id:
            errors.append(f"source_catalog_identity_mismatch:{source_id}")
        rights = catalog.get("rights")
        if not isinstance(rights, dict) or not rights.get("license"):
            errors.append(f"source_catalog_rights_missing:{source_id}")
        declared_level = source.get("catalog_declared_evidence_level")
        if declared_level is not None:
            catalog_level = catalog.get("quality", {}).get("evidence_level")
            if catalog_level != declared_level:
                errors.append(f"source_catalog_evidence_level_mismatch:{source_id}")
    return sources


def _validate_facts(
    contract: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    contradictions: dict[str, dict[str, Any]],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    facts = _unique_objects(contract.get("fact_registry"), "id", "fact", errors)
    for fact_id, fact in facts.items():
        candidate = fact.get("candidate")
        if not isinstance(candidate, dict):
            errors.append(f"fact_candidate_missing:{fact_id}")
            continue
        if candidate.get("kind") not in ALLOWED_CANDIDATE_KINDS:
            errors.append(f"fact_candidate_kind_invalid:{fact_id}")
        if "value" not in candidate:
            errors.append(f"fact_candidate_value_missing:{fact_id}")
        if not isinstance(candidate.get("unit"), str) or not candidate.get("unit"):
            errors.append(f"fact_unit_missing:{fact_id}")
        source_refs = fact.get("source_refs")
        if not isinstance(source_refs, list) or not source_refs:
            errors.append(f"fact_source_refs_missing:{fact_id}")
        else:
            for source_ref in source_refs:
                if source_ref not in sources:
                    errors.append(f"fact_source_unknown:{fact_id}:{source_ref}")
        if fact.get("design_lock") is not False:
            errors.append(f"fact_design_lock_must_be_false:{fact_id}")
        usage = fact.get("usage")
        if not isinstance(usage, str) or not usage:
            errors.append(f"fact_usage_missing:{fact_id}")
        contradiction_refs = fact.get("contradiction_refs")
        if not isinstance(contradiction_refs, list):
            errors.append(f"fact_contradiction_refs_invalid:{fact_id}")
        else:
            for ref in contradiction_refs:
                if ref not in contradictions:
                    errors.append(f"fact_contradiction_unknown:{fact_id}:{ref}")
    return facts


def _validate_ranges(
    contract: dict[str, Any], facts: dict[str, dict[str, Any]], errors: list[str]
) -> dict[str, dict[str, Any]]:
    ranges = _unique_objects(
        contract.get("candidate_ranges"), "id", "candidate_range", errors
    )
    for range_id, item in ranges.items():
        refs = item.get("component_fact_refs")
        if not isinstance(refs, list) or len(refs) < 2:
            errors.append(f"range_component_refs_missing:{range_id}")
            continue
        values: list[float] = []
        for ref in refs:
            fact = facts.get(ref)
            if fact is None:
                errors.append(f"range_fact_unknown:{range_id}:{ref}")
                continue
            candidate = fact.get("candidate", {})
            value = candidate.get("value")
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"range_fact_non_numeric:{range_id}:{ref}")
                continue
            if fact.get("quantity") != item.get("quantity"):
                errors.append(f"range_quantity_mismatch:{range_id}:{ref}")
            if candidate.get("unit") != item.get("unit"):
                errors.append(f"range_unit_mismatch:{range_id}:{ref}")
            values.append(float(value))
        if values:
            if float(item.get("minimum", float("nan"))) != min(values):
                errors.append(f"range_minimum_not_derived:{range_id}")
            if float(item.get("maximum", float("nan"))) != max(values):
                errors.append(f"range_maximum_not_derived:{range_id}")
        if item.get("derivation") != "min_max_of_published_variant_points":
            errors.append(f"range_derivation_invalid:{range_id}")
        if "not_continuous" not in str(item.get("semantics", "")):
            errors.append(f"range_semantics_must_block_interpolation:{range_id}")
        if item.get("design_lock") is not False:
            errors.append(f"range_design_lock_must_be_false:{range_id}")
    return ranges


def _validate_gate_profiles(
    contract: dict[str, Any], errors: list[str]
) -> dict[str, dict[str, Any]]:
    profiles = contract.get("gate_profiles")
    if not isinstance(profiles, dict) or not profiles:
        errors.append("gate_profiles_missing_or_empty")
        return {}
    for profile_id, profile in profiles.items():
        if not isinstance(profile, dict):
            errors.append(f"gate_profile_not_object:{profile_id}")
            continue
        for section_name in REQUIRED_GATE_SECTIONS:
            section = profile.get(section_name)
            if not isinstance(section, dict):
                errors.append(f"gate_section_missing:{profile_id}:{section_name}")
                continue
            if section.get("status") != "blocked":
                errors.append(f"gate_section_must_be_blocked:{profile_id}:{section_name}")
            requirements = section.get("requirements")
            if not isinstance(requirements, list) or not requirements:
                errors.append(
                    f"gate_section_requirements_missing:{profile_id}:{section_name}"
                )
            if section_name in {"convergence", "acceptance"}:
                if section.get("numeric_threshold") is not None:
                    errors.append(
                        f"gate_unsourced_numeric_threshold:{profile_id}:{section_name}"
                    )
                if not str(section.get("threshold_status", "")).endswith("required"):
                    errors.append(
                        f"gate_threshold_status_invalid:{profile_id}:{section_name}"
                    )
    return profiles


def _validate_cases(
    contract: dict[str, Any],
    facts: dict[str, dict[str, Any]],
    ranges: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    cases = _unique_objects(contract.get("solver_cases"), "id", "solver_case", errors)
    if set(cases) != set(EXPECTED_CASES):
        missing = sorted(set(EXPECTED_CASES) - set(cases))
        extra = sorted(set(cases) - set(EXPECTED_CASES))
        if missing:
            errors.append(f"solver_cases_missing:{','.join(missing)}")
        if extra:
            errors.append(f"solver_cases_unexpected:{','.join(extra)}")
    candidates = {**facts, **ranges}
    for case_id, case in cases.items():
        if case.get("domain") != EXPECTED_CASES.get(case_id):
            errors.append(f"solver_case_domain_mismatch:{case_id}")
        if case.get("gate_profile_ref") not in profiles:
            errors.append(f"solver_case_gate_profile_unknown:{case_id}")
        for secondary in case.get("secondary_gate_profile_refs", []):
            if secondary not in profiles:
                errors.append(f"solver_case_secondary_gate_unknown:{case_id}:{secondary}")
        inputs = _unique_objects(case.get("inputs"), "id", f"input_{case_id}", errors)
        blocking = case.get("blocking_unknowns")
        if not isinstance(blocking, list) or not blocking:
            errors.append(f"solver_case_blocking_unknowns_missing:{case_id}")
            blocking = []
        for input_id, input_spec in inputs.items():
            unit = input_spec.get("unit")
            if not isinstance(unit, str) or not unit:
                errors.append(f"solver_input_unit_missing:{case_id}:{input_id}")
            status = input_spec.get("status")
            candidate_ref = input_spec.get("candidate_ref")
            if status == "unknown":
                if candidate_ref is not None:
                    errors.append(
                        f"solver_unknown_input_has_candidate:{case_id}:{input_id}"
                    )
                if input_spec.get("required") is True and input_id not in blocking:
                    errors.append(
                        f"solver_required_unknown_not_blocking:{case_id}:{input_id}"
                    )
            elif isinstance(status, str) and status.startswith("candidate"):
                candidate = candidates.get(candidate_ref)
                if candidate is None:
                    errors.append(
                        f"solver_candidate_ref_unknown:{case_id}:{input_id}:{candidate_ref}"
                    )
                elif unit != (
                    candidate.get("candidate", {}).get("unit")
                    if "candidate" in candidate
                    else candidate.get("unit")
                ):
                    errors.append(f"solver_candidate_unit_mismatch:{case_id}:{input_id}")
            else:
                errors.append(f"solver_input_status_invalid:{case_id}:{input_id}")
        outputs = case.get("expected_outputs")
        if not isinstance(outputs, list) or not outputs:
            errors.append(f"solver_outputs_missing:{case_id}")
        else:
            for output_index, output in enumerate(outputs):
                if not isinstance(output, dict):
                    errors.append(f"solver_output_not_object:{case_id}:{output_index}")
                    continue
                if output.get("status") != "not_computed":
                    errors.append(f"solver_output_claims_result:{case_id}:{output_index}")
                if not output.get("quantity") or not output.get("unit"):
                    errors.append(f"solver_output_metadata_missing:{case_id}:{output_index}")
        requirements = case.get("case_acceptance_requirements")
        if not isinstance(requirements, list) or not requirements:
            errors.append(f"solver_case_acceptance_missing:{case_id}")
        execution = case.get("execution")
        if not isinstance(execution, dict):
            errors.append(f"solver_execution_missing:{case_id}")
        else:
            if execution.get("authorized") is not False:
                errors.append(f"solver_execution_must_be_false:{case_id}")
            if execution.get("results_present") is not False:
                errors.append(f"solver_results_present_must_be_false:{case_id}")
            if not str(execution.get("status", "")).startswith("blocked"):
                errors.append(f"solver_status_must_be_blocked:{case_id}")
    return cases


def _validate_scenarios(
    contract: dict[str, Any],
    facts: dict[str, dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    cases: dict[str, dict[str, Any]],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    scenarios = _unique_objects(
        contract.get("solver_scenarios"), "id", "solver_scenario", errors
    )
    baseline = scenarios.get("SCENARIO-917-5L-NA")
    if baseline is None:
        errors.append("five_litre_na_scenario_missing")
    else:
        required_facts = {
            "FACT-50-BORE",
            "FACT-50-STROKE",
            "FACT-50-DISPLACEMENT",
            "FACT-50-COMPRESSION",
            "FACT-NA-POWER",
            "FACT-50-RATED-SPEED",
        }
        if not required_facts.issubset(set(baseline.get("fact_refs", []))):
            errors.append("five_litre_na_scenario_facts_incomplete")
        if baseline.get("variant") != "type_912_5_0_na":
            errors.append("five_litre_na_scenario_variant_invalid")
    for scenario_id, scenario in scenarios.items():
        for ref in scenario.get("fact_refs", []):
            if ref not in facts:
                errors.append(f"scenario_fact_unknown:{scenario_id}:{ref}")
        for ref in scenario.get("source_refs", []):
            if ref not in sources:
                errors.append(f"scenario_source_unknown:{scenario_id}:{ref}")
        for ref in scenario.get("case_refs", []):
            if ref not in cases:
                errors.append(f"scenario_case_unknown:{scenario_id}:{ref}")
        relationship = scenario.get("scan_relationship")
        if not isinstance(relationship, dict):
            errors.append(f"scenario_scan_relationship_missing:{scenario_id}")
        else:
            for key in (
                "identity_verified",
                "scale_verified",
                "dimensional_fit_verified",
            ):
                if relationship.get(key) is not False:
                    errors.append(f"scenario_scan_claim_must_be_false:{scenario_id}:{key}")
        if scenario.get("execution_authorized") is not False:
            errors.append(f"scenario_execution_must_be_false:{scenario_id}")
        if not str(scenario.get("status", "")).startswith("blocked"):
            errors.append(f"scenario_status_must_be_blocked:{scenario_id}")
    return scenarios


def _validate_coupling(
    contract: dict[str, Any], cases: dict[str, dict[str, Any]], errors: list[str]
) -> None:
    couplings = contract.get("coupling_contract")
    if not isinstance(couplings, list) or not couplings:
        errors.append("coupling_contract_missing")
        return
    for index, coupling in enumerate(couplings):
        if not isinstance(coupling, dict):
            errors.append(f"coupling_not_object:{index}")
            continue
        source = coupling.get("from")
        if source not in cases:
            errors.append(f"coupling_source_unknown:{index}:{source}")
        targets = coupling.get("to")
        if not isinstance(targets, list) or not targets:
            errors.append(f"coupling_targets_missing:{index}")
        else:
            for target in targets:
                if target not in cases:
                    errors.append(f"coupling_target_unknown:{index}:{target}")
        if coupling.get("status") != "blocked":
            errors.append(f"coupling_status_must_be_blocked:{index}")


def _validate_physicsnemo(
    contract: dict[str, Any], cases: dict[str, dict[str, Any]], errors: list[str]
) -> None:
    transition = contract.get("physicsnemo_transition")
    if not isinstance(transition, dict):
        errors.append("physicsnemo_transition_missing")
        return
    if transition.get("training_authorized") is not False:
        errors.append("physicsnemo_training_must_be_false")
    if transition.get("dataset_ready") is not False:
        errors.append("physicsnemo_dataset_ready_must_be_false")
    if transition.get("classical_cases_passed") != 0:
        errors.append("physicsnemo_classical_cases_passed_must_be_zero")
    if transition.get("required_case_count") != len(cases):
        errors.append("physicsnemo_required_case_count_mismatch")
    requirements = transition.get("requirements")
    if not isinstance(requirements, list) or len(requirements) < 6:
        errors.append("physicsnemo_requirements_incomplete")
    families = transition.get("candidate_model_families")
    if not isinstance(families, list) or len(families) < 2:
        errors.append("physicsnemo_candidate_menu_incomplete")
    else:
        for family in families:
            if not isinstance(family, dict):
                errors.append("physicsnemo_candidate_not_object")
                continue
            name = family.get("name")
            if family.get("status") != "discovery_candidate_not_selected":
                errors.append(f"physicsnemo_candidate_status_invalid:{name}")
            repo_path = family.get("official_repo_path")
            if not isinstance(repo_path, str) or not repo_path.startswith(
                "https://github.com/NVIDIA/physicsnemo/tree/v2.2.1/physicsnemo/models/"
            ):
                errors.append(f"physicsnemo_candidate_path_invalid:{name}")
            for case_ref in family.get("candidate_cases", []):
                if case_ref not in cases:
                    errors.append(f"physicsnemo_candidate_case_unknown:{name}:{case_ref}")


def evaluate(project_root: Path, registry_path: Path) -> dict[str, Any]:
    root = project_root.resolve()
    contract = load_json(registry_path.resolve())
    errors: list[str] = []

    if contract.get("phase") != "F13":
        errors.append("phase_must_be_F13")
    if contract.get("asset_id") != "porsche-917-classical-solver-cases-f13":
        errors.append("asset_id_must_identify_F13_solver_registry")
    if contract.get("parent_asset_id") != "porsche-917-whole-engine-reengineering-f12":
        errors.append("parent_asset_id_must_reference_F12_whole_engine")
    if contract.get("status") != (
        "reference_solver_case_definitions_ready_all_execution_and_release_gates_blocked"
    ):
        errors.append("contract_status_invalid")
    _validate_authority(contract, errors)

    contradictions = _unique_objects(
        contract.get("contradictions"), "id", "contradiction", errors
    )
    for contradiction_id, contradiction in contradictions.items():
        if contradiction.get("resolution_status") != "open":
            errors.append(f"contradiction_must_remain_open:{contradiction_id}")
        if not contradiction.get("statement") or not contradiction.get("solver_rule"):
            errors.append(f"contradiction_metadata_missing:{contradiction_id}")

    sources = _validate_sources(contract, root, errors)
    facts = _validate_facts(contract, sources, contradictions, errors)
    ranges = _validate_ranges(contract, facts, errors)
    profiles = _validate_gate_profiles(contract, errors)
    cases = _validate_cases(contract, facts, ranges, profiles, errors)
    scenarios = _validate_scenarios(contract, facts, sources, cases, errors)
    _validate_coupling(contract, cases, errors)
    _validate_physicsnemo(contract, cases, errors)

    return {
        "schema_version": "1.0.0",
        "phase": "F13",
        "report_status": "passed" if not errors else "failed",
        "specification_only": True,
        "source_count": len(sources),
        "fact_count": len(facts),
        "candidate_range_count": len(ranges),
        "contradiction_count": len(contradictions),
        "gate_profile_count": len(profiles),
        "solver_case_count": len(cases),
        "scenario_count": len(scenarios),
        "solver_execution_authorized": False,
        "results_present": False,
        "physicsnemo_training_authorized": False,
        "fabrication_authorized": False,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valide le registre F13 des solveurs classiques du moteur 917."
    )
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = evaluate(args.project_root, args.registry)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["report_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
