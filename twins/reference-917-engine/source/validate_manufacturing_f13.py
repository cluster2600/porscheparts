#!/usr/bin/env python3
"""Valide le registre F13 de fabrication du moteur 917 en mode fail-closed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = (
    ROOT / "twins/reference-917-engine/manufacturing-validation-f13.json"
)

EXPECTED_FAMILY_IDS = (
    "crankcase_magnesium_historical",
    "cylinder_nikasil_system",
    "piston_system",
    "connecting_rod_titanium",
    "valve_titanium_candidate",
    "camshaft_system",
    "dilavar_stud_system",
    "gas_ducts_and_manifolds",
    "turbocharger_system",
)
EXPECTED_MATURITY_IDS = (
    "polymer_prototype",
    "metal_mockup",
    "functional_engine_part",
)
EXPECTED_CONTROL_IDS = (
    "dfam",
    "machining",
    "heat_treatment",
    "hip",
    "ct",
    "ndt",
    "coupons",
)
EXPECTED_GLOBAL_RULE_IDS = EXPECTED_CONTROL_IDS + ("tolerances",)
EXPECTED_TITANIUM_TOPICS = (
    "alloy",
    "build_process",
    "orientation",
    "heat_treatment",
    "hip",
    "machining",
    "inspection",
    "fatigue",
    "galvanic_isolation",
)
TITANIUM_SELECTION_FIELDS = (
    "selected_alloy",
    "selected_build_process",
    "selected_orientation",
    "selected_heat_treatment",
    "selected_hip_cycle",
)
TITANIUM_EVIDENCE_FIELDS = (
    "machining",
    "inspection",
    "fatigue",
    "galvanic_isolation",
)
RUNTIME_AUTHORITY_IDS = (
    "material_selection_authority",
    "process_qualification_authority",
    "metrology_acceptance_authority",
    "engine_safety_release_authority",
    "professional_signoff_verifier",
)


def _nonempty_string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
    )


def _ids(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    return [item.get("id") for item in items if isinstance(item, dict)]


def validate_contract(contract: dict[str, Any]) -> list[str]:
    """Retourne des erreurs stables; une liste vide signifie contrat coherent."""

    errors: list[str] = []

    if contract.get("schema_version") != "1.0.0":
        errors.append("invalid_schema_version")
    if contract.get("phase") != "F13":
        errors.append("invalid_phase")
    if contract.get("status") != (
        "manufacturing_strategy_ready_all_part_and_engine_releases_blocked"
    ):
        errors.append("invalid_contract_status")

    asset = contract.get("asset")
    if not isinstance(asset, dict):
        errors.append("missing_asset")
        asset = {}
    if asset.get("id") != "porsche-917-engine-manufacturing-validation-f13":
        errors.append("invalid_asset_id")
    if asset.get("upstream_contract_reference") != (
        "twins/reference-917-engine/whole-engine-reengineering-f12.json"
    ):
        errors.append("invalid_upstream_contract_reference")
    for flag in (
        "identity_and_variant_confirmed",
        "scale_confirmed",
        "raw_scan_in_git",
        "geometry_embedded",
        "proprietary_payload_embedded",
    ):
        if asset.get(flag) is not False:
            errors.append(f"asset_boundary_must_be_false:{flag}")

    serialized = json.dumps(contract, ensure_ascii=False).lower()
    for forbidden in (".obj", ".stl", ".step", ".usd", "/raw-scans/"):
        if forbidden in serialized:
            errors.append(f"embedded_geometry_reference_forbidden:{forbidden}")

    claims = contract.get("claims_policy")
    if not isinstance(claims, dict):
        errors.append("missing_claims_policy")
        claims = {}
    for claim in (
        "hundred_percent_functional_claim",
        "print_ready_claim",
        "scan_to_part_direct_route",
        "physicsnemo_as_manufacturing_qualification",
    ):
        if claims.get(claim) != "prohibited":
            errors.append(f"claim_must_be_prohibited:{claim}")

    levels = contract.get("maturity_levels")
    level_ids = _ids(levels)
    if level_ids != list(EXPECTED_MATURITY_IDS):
        errors.append("maturity_levels_mismatch")
    if len(level_ids) != len(set(level_ids)):
        errors.append("duplicate_maturity_level_id")
    for level in levels if isinstance(levels, list) else []:
        if not isinstance(level, dict):
            errors.append("invalid_maturity_level")
            continue
        level_id = level.get("id", "unknown")
        if not _nonempty_string_list(level.get("prohibited_uses")):
            errors.append(f"missing_prohibited_uses:{level_id}")
        if not _nonempty_string_list(level.get("required_before_build")):
            errors.append(f"missing_prebuild_requirements:{level_id}")
        release = level.get("release")
        if not isinstance(release, dict):
            errors.append(f"missing_maturity_release:{level_id}")
            continue
        for field in ("printable", "functional", "engine_use"):
            if release.get(field) is not False:
                errors.append(f"maturity_release_must_be_false:{level_id}:{field}")

    authorities = contract.get("runtime_authorities")
    if not isinstance(authorities, dict):
        errors.append("missing_runtime_authorities")
        authorities = {}
    for authority_id in RUNTIME_AUTHORITY_IDS:
        if authorities.get(authority_id) != "not_implemented":
            errors.append(f"runtime_authority_must_be_absent:{authority_id}")
    if authorities.get("configuration_is_authority") is not False:
        errors.append("configuration_cannot_be_authority")

    rules = contract.get("global_qualification_rules")
    if not isinstance(rules, dict):
        errors.append("missing_global_qualification_rules")
        rules = {}
    if set(rules) != set(EXPECTED_GLOBAL_RULE_IDS):
        errors.append("global_rule_sets_mismatch")
    for rule_id in EXPECTED_GLOBAL_RULE_IDS:
        rule = rules.get(rule_id)
        if not isinstance(rule, dict) or not _nonempty_string_list(rule.get("required")):
            errors.append(f"missing_global_rule_requirements:{rule_id}")

    titanium_policy = contract.get("titanium_policy")
    if not isinstance(titanium_policy, dict):
        errors.append("missing_titanium_policy")
        titanium_policy = {}
    if titanium_policy.get("mandatory_topics") != list(EXPECTED_TITANIUM_TOPICS):
        errors.append("titanium_topics_mismatch")
    if not _nonempty_string_list(titanium_policy.get("rules")):
        errors.append("missing_titanium_rules")
    declared_titanium_ids = titanium_policy.get("candidate_family_ids")
    if not isinstance(declared_titanium_ids, list):
        declared_titanium_ids = []
        errors.append("missing_titanium_family_ids")

    families = contract.get("family_registry")
    family_ids = _ids(families)
    if set(family_ids) != set(EXPECTED_FAMILY_IDS):
        missing = sorted(set(EXPECTED_FAMILY_IDS) - set(family_ids))
        extra = sorted(set(family_ids) - set(EXPECTED_FAMILY_IDS))
        if missing:
            errors.append("missing_families:" + ",".join(missing))
        if extra:
            errors.append("unexpected_families:" + ",".join(extra))
    if len(family_ids) != len(set(family_ids)):
        errors.append("duplicate_family_id")

    detected_titanium_ids: list[str] = []
    for family in families if isinstance(families, list) else []:
        if not isinstance(family, dict):
            errors.append("invalid_family_entry")
            continue
        family_id = family.get("id", "unknown")
        materials = family.get("candidate_materials")
        if not isinstance(materials, list) or not materials:
            errors.append(f"missing_candidate_materials:{family_id}")
            materials = []
        material_ids = _ids(materials)
        if len(material_ids) != len(set(material_ids)):
            errors.append(f"duplicate_material_id:{family_id}")
        has_titanium = False
        for material in materials:
            if not isinstance(material, dict):
                errors.append(f"invalid_candidate_material:{family_id}")
                continue
            if material.get("status") != "candidate_unqualified":
                errors.append(
                    f"material_must_remain_unqualified:{family_id}:{material.get('id', 'unknown')}"
                )
            if material.get("material_family") == "titanium":
                has_titanium = True
        if family.get("selected_material_id") is not None:
            errors.append(f"selected_material_forbidden_without_evidence:{family_id}")

        routes = family.get("candidate_routes")
        if not isinstance(routes, list) or not routes:
            errors.append(f"missing_candidate_routes:{family_id}")
            routes = []
        route_ids = _ids(routes)
        if len(route_ids) != len(set(route_ids)):
            errors.append(f"duplicate_route_id:{family_id}")
        for route in routes:
            if not isinstance(route, dict):
                errors.append(f"invalid_candidate_route:{family_id}")
                continue
            if route.get("status") != "candidate_unqualified":
                errors.append(
                    f"route_must_remain_unqualified:{family_id}:{route.get('id', 'unknown')}"
                )
        if family.get("selected_route_id") is not None:
            errors.append(f"selected_route_forbidden_without_evidence:{family_id}")

        if not isinstance(family.get("additive_disposition"), str):
            errors.append(f"missing_additive_disposition:{family_id}")

        maturity = family.get("maturity_disposition")
        if not isinstance(maturity, dict) or set(maturity) != set(EXPECTED_MATURITY_IDS):
            errors.append(f"family_maturity_mismatch:{family_id}")
        elif maturity.get("functional_engine_part") != "blocked":
            errors.append(f"functional_maturity_must_be_blocked:{family_id}")

        controls = family.get("manufacturing_controls")
        if not isinstance(controls, dict) or set(controls) != set(EXPECTED_CONTROL_IDS):
            errors.append(f"manufacturing_controls_mismatch:{family_id}")
            controls = {}
        for control_id in EXPECTED_CONTROL_IDS:
            if not _nonempty_string_list(controls.get(control_id)):
                errors.append(f"missing_manufacturing_control:{family_id}:{control_id}")

        measurements = family.get("critical_measurements")
        if not isinstance(measurements, list) or not measurements:
            errors.append(f"missing_critical_measurements:{family_id}")
            measurements = []
        measurement_ids = _ids(measurements)
        if len(measurement_ids) != len(set(measurement_ids)):
            errors.append(f"duplicate_measurement_id:{family_id}")
        for measurement in measurements:
            if not isinstance(measurement, dict):
                errors.append(f"invalid_measurement:{family_id}")
                continue
            measurement_id = measurement.get("id", "unknown")
            if measurement.get("nominal") is not None:
                errors.append(f"invented_nominal:{family_id}:{measurement_id}")
            if measurement.get("tolerance") is not None:
                errors.append(f"invented_tolerance:{family_id}:{measurement_id}")
            for field in ("unit", "method", "condition"):
                value = measurement.get(field)
                if not isinstance(value, str) or not value.strip():
                    errors.append(
                        f"missing_measurement_metadata:{family_id}:{measurement_id}:{field}"
                    )

        release = family.get("release")
        if not isinstance(release, dict):
            errors.append(f"missing_family_release:{family_id}")
        else:
            if release.get("status") != "blocked":
                errors.append(f"family_release_status_must_be_blocked:{family_id}")
            for field in ("printable", "functional", "engine_use"):
                if release.get(field) is not False:
                    errors.append(f"family_release_must_be_false:{family_id}:{field}")

        titanium_controls = family.get("titanium_controls")
        if has_titanium:
            detected_titanium_ids.append(family_id)
            if not isinstance(titanium_controls, dict):
                errors.append(f"missing_titanium_controls:{family_id}")
                titanium_controls = {}
            for field in TITANIUM_SELECTION_FIELDS:
                if titanium_controls.get(field) is not None:
                    errors.append(f"titanium_selection_forbidden:{family_id}:{field}")
            for field in TITANIUM_EVIDENCE_FIELDS:
                if not _nonempty_string_list(titanium_controls.get(field)):
                    errors.append(f"missing_titanium_evidence_topic:{family_id}:{field}")
            if titanium_controls.get("additive_build_authorized") is not False:
                errors.append(f"titanium_additive_build_must_be_blocked:{family_id}")
        elif titanium_controls is not None:
            errors.append(f"unexpected_titanium_controls:{family_id}")

    if sorted(declared_titanium_ids) != sorted(detected_titanium_ids):
        errors.append("titanium_family_registry_mismatch")

    release = contract.get("whole_engine_release")
    if not isinstance(release, dict):
        errors.append("missing_whole_engine_release")
        release = {}
    boolean_release_fields = (
        "polymer_prototype_authorized",
        "metal_mockup_authorized",
        "functional_engine_part_authorized",
        "printable",
        "functional",
        "engine_assembly",
        "engine_start",
        "vehicle_use",
    )
    for field in boolean_release_fields:
        if release.get(field) is not False:
            errors.append(f"whole_engine_release_must_be_false:{field}")
    if not _nonempty_string_list(release.get("blocking_reasons")):
        errors.append("missing_whole_engine_blocking_reasons")

    return errors


def evaluate(contract: dict[str, Any]) -> dict[str, Any]:
    errors = validate_contract(contract)
    families = contract.get("family_registry", [])
    valid_families = [item for item in families if isinstance(item, dict)]
    return {
        "schema_version": "1.0.0",
        "phase": "F13",
        "report_status": "passed" if not errors else "failed",
        "contract_errors": errors,
        "counts": {
            "family_count": len(valid_families),
            "material_candidate_count": sum(
                len(item.get("candidate_materials", [])) for item in valid_families
            ),
            "route_candidate_count": sum(
                len(item.get("candidate_routes", [])) for item in valid_families
            ),
            "critical_measurement_count": sum(
                len(item.get("critical_measurements", [])) for item in valid_families
            ),
        },
        "release": {
            "polymer_prototype_authorized": False,
            "metal_mockup_authorized": False,
            "functional_engine_part_authorized": False,
            "printable": False,
            "functional": False,
            "engine_assembly": False,
            "engine_start": False,
            "vehicle_use": False,
        },
        "decision": (
            "strategy_contract_consistent_releases_still_blocked"
            if not errors
            else "contract_invalid_all_releases_blocked"
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    report = evaluate(contract)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["report_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
