#!/usr/bin/env python3
"""Construit et valide le routage de fabrication F19 du moteur 917.

F19 classe des dispositions de route depuis les inventaires F12, F16 et F8.
Il ne selectionne ni nuance, ni procede, ni tolerance et ne libere aucune
piece. Une maquette imprimable n'est jamais une piece moteur fonctionnelle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


ASSET_ID = "porsche-917-whole-engine-manufacturing-routing-f19"
CONTRACT_REL = Path(
    "twins/reference-917-engine/manufacturing-routing-f19.json"
)
UPSTREAMS = {
    "whole_engine_f12": Path(
        "twins/reference-917-engine/whole-engine-reengineering-f12.json"
    ),
    "kinematic_interfaces_f16": Path(
        "twins/reference-917-engine/kinematic-interface-readiness-f16.json"
    ),
    "mechanical_connections_f8": Path(
        "twins/reference-917-engine/mechanical-connections-f8.json"
    ),
    "sealing_interfaces_f8": Path(
        "twins/reference-917-engine/sealing-interfaces-f8.json"
    ),
    "ducts_f8": Path("twins/reference-917-engine/ducts-f8.json"),
    "external_interfaces_f8": Path(
        "twins/reference-917-engine/external-interfaces-f8.json"
    ),
}

F12_ROUTE_CLASSES = {
    "lpbf": "metal_additive_candidate",
    "machined": "conventional_candidate",
    "forged": "conventional_candidate",
    "cast": "conventional_candidate",
    "fabricated": "conventional_candidate",
    "purchased": "purchased_non_printable",
    "not_printable": "purchased_non_printable",
    "route_not_selected": "unresolved",
}

F16_TO_F12_FAMILY = {
    "crankcase": "crankcase_half",
    "crankshaft": "crankshaft",
    "main_bearing": "main_bearing",
    "individual_cylinder": "individual_cylinder",
    "connecting_rod": "connecting_rod",
    "piston_pin": "piston_pin",
    "piston": "piston",
}

BACKLOG_ROUTE_CLASSES = {
    "fasteners_and_threaded_hardware": "purchased_non_printable",
    "gaskets_and_dynamic_seals": "purchased_non_printable",
    "retaining_hardware": "purchased_non_printable",
    "fluid_lines_and_fittings": "hybrid_candidate",
    "internal_fluid_passages": "not_a_part",
    "cooling_air_passages_and_baffles": "hybrid_candidate",
    "additional_bearings_bushings_and_thrust_elements": "purchased_non_printable",
    "valvetrain_small_parts": "hybrid_candidate",
    "piston_and_rod_small_parts": "hybrid_candidate",
    "sensors_and_instrumentation": "purchased_non_printable",
    "wiring_ignition_and_connectors": "purchased_non_printable",
    "controls_linkages_and_actuators": "hybrid_candidate",
    "filters_screens_and_flow_conditioners": "purchased_non_printable",
}

SPECIAL_MATERIAL_NULL_FIELDS = (
    "selected_grade",
    "selected_feedstock_or_product_form",
    "selected_process",
    "selected_build_orientation",
    "selected_heat_treatment",
    "selected_hip_decision_and_cycle",
    "selected_machining_allowance_mm",
    "selected_ndt_method_and_acceptance",
    "selected_ct_method_and_acceptance",
    "selected_fatigue_basis",
    "selected_galvanic_isolation_system",
)

SPECIAL_MATERIAL_TOPICS = (
    "grade_and_product_form_traceability",
    "process_and_parameter_qualification",
    "build_orientation_and_anisotropy",
    "heat_treatment_by_exact_grade_and_route",
    "hip_applicability_and_cycle_if_relevant",
    "machining_allowances_from_measured_distortion",
    "ndt_and_ct_detectability_with_acceptance_criteria",
    "hcf_lcf_thermal_fatigue_and_surface_condition",
    "galvanic_isolation_in_real_temperature_and_fluid",
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def false_release() -> dict[str, bool]:
    return {
        "prototype_print": False,
        "metal_additive": False,
        "functional": False,
        "engine_use": False,
        "assembly": False,
    }


def null_selections() -> dict[str, None]:
    return {
        "selected_material_grade": None,
        "selected_process": None,
        "selected_tolerance_set": None,
    }


def load_upstreams(project_root: Path) -> dict[str, dict[str, Any]]:
    return {
        source_id: load_json(project_root / relative_path)
        for source_id, relative_path in UPSTREAMS.items()
    }


def source_manifest(project_root: Path) -> list[dict[str, Any]]:
    completeness = {
        "whole_engine_f12": False,
        "kinematic_interfaces_f16": False,
        "mechanical_connections_f8": False,
        "sealing_interfaces_f8": False,
        "ducts_f8": False,
        "external_interfaces_f8": False,
    }
    return [
        {
            "id": source_id,
            "path": str(relative_path),
            "sha256": sha256(project_root / relative_path),
            "inventory_complete": completeness[source_id],
        }
        for source_id, relative_path in UPSTREAMS.items()
    ]


def family_record(source: dict[str, Any]) -> dict[str, Any]:
    source_route = source["manufacturing_route"]
    route_class = F12_ROUTE_CLASSES[source_route]
    return {
        "id": source["id"],
        "source_visual_count": source["visual_count"],
        "source_visual_variant": source["visual_variant"],
        "source_manufacturing_disposition": source_route,
        "source_disposition_status": source["manufacturing_status"],
        "prototype_disposition": {
            "route_class": "printable_prototype",
            "status": "geometry_only_candidate_not_released",
            "allowed_purpose": "forme_encombrement_accessibilite_assemblage_statique",
            "functional_use": False,
        },
        "functional_disposition": {
            "route_class": route_class,
            "status": "classification_only_route_not_selected_or_qualified",
            "hybrid_completion_may_be_required": source_route in {
                "lpbf",
                "machined",
                "forged",
                "cast",
                "fabricated",
            },
            "functional_3d_print_claim": False,
        },
        **null_selections(),
        "release": false_release(),
    }


def instance_records(
    f16: dict[str, Any], family_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for group in f16["component_instance_contract"]:
        f12_family_id = F16_TO_F12_FAMILY[group["family"]]
        family_route = family_by_id[f12_family_id]["functional_disposition"]
        route_class = family_route["route_class"]
        for ordinal in range(1, group["count"] + 1):
            records.append(
                {
                    "id": f"{group['id_prefix']}{ordinal:02d}",
                    "ordinal": ordinal,
                    "source_family": group["family"],
                    "source_id_prefix": group["id_prefix"],
                    "source_count_fact_ref": group["count_fact_ref"],
                    "f12_family_ref": f12_family_id,
                    "crosswalk_status": (
                        "semantic_assembly_to_visual_family_candidate"
                        if group["family"] == "crankcase"
                        else "same_named_family_candidate"
                    ),
                    "variant_scope": f16["work_branch"]["variant_id"],
                    "prototype_disposition": {
                        "route_class": "printable_prototype",
                        "status": "geometry_only_candidate_not_released",
                        "functional_use": False,
                    },
                    "route_class": route_class,
                    "route_status": "inherited_classification_only_not_selected",
                    "hybrid_completion_may_be_required": family_route[
                        "hybrid_completion_may_be_required"
                    ],
                    **null_selections(),
                    "release": false_release(),
                }
            )
    return records


def interface_records(
    records: Iterable[dict[str, Any]], route_class: str
) -> list[dict[str, Any]]:
    result = []
    for item in records:
        result.append(
            {
                "id": item["id"],
                "count": item["count"],
                "variant": item["variant"],
                "input_profile": item.get("input_profile"),
                "route_class": route_class,
                "route_status": "functional_requirement_only_not_selected",
                **null_selections(),
                "release": false_release(),
            }
        )
    return result


def material_policy(
    policy_id: str, candidate_scopes: list[dict[str, str]]
) -> dict[str, Any]:
    return {
        "id": policy_id,
        "status": "conditional_controls_only_no_material_or_route_selected",
        "candidate_scopes": candidate_scopes,
        **{field: None for field in SPECIAL_MATERIAL_NULL_FIELDS},
        "required_evidence_topics": list(SPECIAL_MATERIAL_TOPICS),
        "additive_build_authorized": False,
        "functional_use_authorized": False,
    }


def build_contract(project_root: Path) -> dict[str, Any]:
    upstream = load_upstreams(project_root)
    f12 = upstream["whole_engine_f12"]
    f16 = upstream["kinematic_interfaces_f16"]
    family_registry = [family_record(item) for item in f12["family_registry"]]
    family_by_id = {item["id"]: item for item in family_registry}

    interface_registry = {
        "mechanical_connections": interface_records(
            upstream["mechanical_connections_f8"]["mechanical_connections"],
            "hybrid_candidate",
        ),
        "sealing_interfaces": interface_records(
            upstream["sealing_interfaces_f8"]["sealing_interfaces"],
            "purchased_non_printable",
        ),
        "ducts": interface_records(
            upstream["ducts_f8"]["ducts"], "hybrid_candidate"
        ),
        "external_interfaces": interface_records(
            upstream["external_interfaces_f8"]["external_interfaces"],
            "not_a_part",
        ),
    }

    backlog = [
        {
            "id": item["id"],
            "source_status": item["status"],
            "quantity": item["quantity"],
            "dimensions": item["dimensions"],
            "route_class": BACKLOG_ROUTE_CLASSES[item["id"]],
            "route_status": "unbounded_requirement_not_selected",
            **null_selections(),
            "release": false_release(),
        }
        for item in f12["unbounded_bom_backlog"]
    ]

    return {
        "$comment": (
            "F19 classe les routes candidates des inventaires F12, F16 et F8. "
            "Aucune classification n'est une selection de nuance, procede, "
            "tolerance ou autorisation de fabrication."
        ),
        "schema_version": "1.0.0",
        "phase": "F19",
        "status": "manufacturing_routing_contract_ready_all_release_gates_blocked",
        "asset": {
            "id": ASSET_ID,
            "target": "moteur Porsche 917 complet sur banc, branches atmospherique et biturbo",
            "current_verified_level": "visual_and_semantic_inventories_only",
            "real_bom_complete": False,
            "functional_100_percent_means_100_percent_printed": False,
            "raw_scan_in_git": False,
        },
        "upstream_contracts": source_manifest(project_root),
        "routing_taxonomy": {
            "printable_prototype": "maquette geometrique inerte; aucune charge, pression, temperature ou rotation moteur",
            "metal_additive_candidate": "route additive metallique a etudier puis finir, inspecter et qualifier; non selectionnee",
            "conventional_candidate": "usinage, forge, fonderie ou fabrication assemblee a qualifier; non selectionne",
            "purchased_non_printable": "fonction a acheter ou a specifier; representation permise dans le jumeau, impression fonctionnelle interdite",
            "hybrid_candidate": "assemblage multiroute potentiel combinant corps fabriques, finitions et elements achetes; non selectionne",
            "unresolved": "aucune famille de route ne peut encore etre choisie",
            "not_a_part": "feature, passage ou condition aux limites, pas une piece imprimable autonome",
        },
        "routing_rules": {
            "f12_disposition_to_route_class": F12_ROUTE_CLASSES,
            "f16_to_f12_family_crosswalk": F16_TO_F12_FAMILY,
            "backlog_route_classes": BACKLOG_ROUTE_CLASSES,
            "classification_is_selection": False,
            "prototype_is_functional_part": False,
            "functional_engine_can_be_claimed_fully_printed": False,
        },
        "family_route_registry": family_registry,
        "instance_route_registry": instance_records(f16, family_by_id),
        "f8_interface_route_registry": interface_registry,
        "unbounded_bom_route_registry": backlog,
        "conditional_material_policies": {
            "titanium": material_policy(
                "titanium",
                [
                    {
                        "family_id": "connecting_rod",
                        "basis": "F12_source_confidence_mentions_titanium_but_no_grade_or_route_is_selected",
                    },
                    {
                        "family_id": "intake_valve",
                        "basis": "design_hypothesis_only_requires_new_source_and_qualification",
                    },
                    {
                        "family_id": "exhaust_valve",
                        "basis": "design_hypothesis_only_requires_temperature_and_fatigue_evidence",
                    },
                ],
            ),
            "inconel_nickel_superalloy": material_policy(
                "inconel_nickel_superalloy",
                [
                    {
                        "family_id": "exhaust_primary",
                        "basis": "hot_side_design_hypothesis_only_no_grade_or_process_selected",
                    },
                    {
                        "family_id": "exhaust_collector",
                        "basis": "hot_side_design_hypothesis_only_no_grade_or_process_selected",
                    },
                    {
                        "family_id": "turbocharger",
                        "basis": "purchased_assembly_hot_side_material_change_requires_supplier_and_test_evidence",
                    },
                ],
            ),
        },
        "functional_engine_policy": {
            "definition": (
                "100 percent fonctionnel signifie que chaque fonction est "
                "specifiee, integree, calculee, inspectee et validee au banc; "
                "cela ne signifie jamais 100 percent imprime."
            ),
            "fully_additively_manufactured": False,
            "purchased_functions_remain_mandatory": [
                "bearings_and_bushings",
                "gaskets_and_dynamic_seals",
                "springs",
                "piston_rings",
                "injectors",
                "spark_plugs",
                "sensors_and_instrumentation",
                "retaining_and_threaded_hardware",
            ],
            "mixed_route_required_before_functional_claim": True,
            "mixed_route_qualified": False,
        },
        "counts": {
            "f12_family_count": len(family_registry),
            "f16_semantic_instance_count": len(instance_records(f16, family_by_id)),
            "f8_mechanical_group_count": len(interface_registry["mechanical_connections"]),
            "f8_seal_group_count": len(interface_registry["sealing_interfaces"]),
            "f8_duct_group_count": len(interface_registry["ducts"]),
            "f8_external_interface_group_count": len(interface_registry["external_interfaces"]),
            "unbounded_bom_category_count": len(backlog),
        },
        "release_gates": {
            "prototype_print_authorized": False,
            "metal_additive_build_authorized": False,
            "conventional_manufacturing_authorized": False,
            "purchased_component_specification_released": False,
            "hybrid_assembly_authorized": False,
            "all_materials_and_routes_sourced": False,
            "all_tolerances_sourced_and_validated": False,
            "real_bom_complete": False,
            "functional_engine_authorized": False,
            "vehicle_use_authorized": False,
        },
        "prohibited_claims": [
            "scan_or_proxy_is_manufacturing_geometry",
            "candidate_route_is_selected_or_qualified",
            "prototype_is_engine_functional",
            "purchased_function_is_functionally_3d_printable",
            "100_percent_functional_means_100_percent_printed",
            "physicsnemo_or_omniverse_is_manufacturing_release",
        ],
    }


def _all_false(value: Any) -> bool:
    if isinstance(value, bool):
        return value is False
    if isinstance(value, dict):
        return all(_all_false(item) for item in value.values())
    if isinstance(value, list):
        return all(_all_false(item) for item in value)
    return True


def _selection_errors(value: Any, path: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else key
            if key.startswith("selected_") and item is not None:
                errors.append(f"selection_without_evidence:{child}")
            errors.extend(_selection_errors(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_selection_errors(item, f"{path}[{index}]"))
    return errors


def _by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in items if isinstance(item.get("id"), str)}


def validate_contract(project_root: Path, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    upstream = load_upstreams(project_root)
    expected = build_contract(project_root)

    if contract.get("schema_version") != "1.0.0":
        errors.append("schema_version_mismatch")
    if contract.get("phase") != "F19":
        errors.append("phase_mismatch")
    if contract.get("asset", {}).get("id") != ASSET_ID:
        errors.append("asset_id_mismatch")
    if contract.get("asset") != expected["asset"]:
        errors.append("asset_contract_mismatch")
    for field in (
        "status",
        "routing_taxonomy",
        "routing_rules",
        "prohibited_claims",
    ):
        if contract.get(field) != expected[field]:
            errors.append(f"immutable_contract_field_mismatch:{field}")

    actual_sources = _by_id(contract.get("upstream_contracts", []))
    for source_id, relative_path in UPSTREAMS.items():
        record = actual_sources.get(source_id)
        if record is None:
            errors.append(f"upstream_missing:{source_id}")
            continue
        if record.get("path") != str(relative_path):
            errors.append(f"upstream_path_mismatch:{source_id}")
        if record.get("sha256") != sha256(project_root / relative_path):
            errors.append(f"upstream_sha256_mismatch:{source_id}")
        if record.get("inventory_complete") is not False:
            errors.append(f"upstream_completeness_claim_forbidden:{source_id}")

    expected_families = _by_id(expected["family_route_registry"])
    actual_families = _by_id(contract.get("family_route_registry", []))
    if set(actual_families) != set(expected_families):
        errors.append("f12_family_coverage_mismatch")
    for family_id, wanted in expected_families.items():
        actual = actual_families.get(family_id)
        if actual is None:
            continue
        for field in (
            "source_visual_count",
            "source_visual_variant",
            "source_manufacturing_disposition",
            "source_disposition_status",
        ):
            if actual.get(field) != wanted[field]:
                errors.append(f"family_source_field_mismatch:{family_id}:{field}")
        if actual.get("functional_disposition") != wanted["functional_disposition"]:
            errors.append(f"family_route_class_mismatch:{family_id}")
        if actual.get("prototype_disposition") != wanted["prototype_disposition"]:
            errors.append(f"family_prototype_boundary_mismatch:{family_id}")
        if not _all_false(actual.get("release")):
            errors.append(f"family_release_must_be_false:{family_id}")

    expected_instances = _by_id(expected["instance_route_registry"])
    actual_instances = _by_id(contract.get("instance_route_registry", []))
    if set(actual_instances) != set(expected_instances):
        errors.append("f16_instance_coverage_mismatch")
    for instance_id, wanted in expected_instances.items():
        actual = actual_instances.get(instance_id)
        if actual is None:
            continue
        for field in (
            "ordinal",
            "source_family",
            "source_id_prefix",
            "source_count_fact_ref",
            "f12_family_ref",
            "crosswalk_status",
            "variant_scope",
            "prototype_disposition",
            "route_class",
            "route_status",
            "hybrid_completion_may_be_required",
        ):
            if actual.get(field) != wanted[field]:
                errors.append(f"instance_field_mismatch:{instance_id}:{field}")
        if not _all_false(actual.get("release")):
            errors.append(f"instance_release_must_be_false:{instance_id}")

    f8_specs = (
        ("mechanical_connections", "mechanical_connections_f8", "mechanical_connections", "hybrid_candidate"),
        ("sealing_interfaces", "sealing_interfaces_f8", "sealing_interfaces", "purchased_non_printable"),
        ("ducts", "ducts_f8", "ducts", "hybrid_candidate"),
        ("external_interfaces", "external_interfaces_f8", "external_interfaces", "not_a_part"),
    )
    actual_f8 = contract.get("f8_interface_route_registry", {})
    for target_key, source_id, source_key, route_class in f8_specs:
        source_items = upstream[source_id][source_key]
        expected_ids = {item["id"] for item in source_items}
        actual_items = _by_id(actual_f8.get(target_key, []))
        if set(actual_items) != expected_ids:
            errors.append(f"f8_group_coverage_mismatch:{target_key}")
        source_by_id = _by_id(source_items)
        for item_id, actual in actual_items.items():
            source = source_by_id[item_id]
            if actual.get("count") != source["count"]:
                errors.append(f"f8_count_mismatch:{target_key}:{item_id}")
            if actual.get("variant") != source["variant"]:
                errors.append(f"f8_variant_mismatch:{target_key}:{item_id}")
            if actual.get("input_profile") != source.get("input_profile"):
                errors.append(f"f8_profile_mismatch:{target_key}:{item_id}")
            if actual.get("route_class") != route_class:
                errors.append(f"f8_route_class_mismatch:{target_key}:{item_id}")
            if actual.get("route_status") != "functional_requirement_only_not_selected":
                errors.append(f"f8_route_status_mismatch:{target_key}:{item_id}")
            if not _all_false(actual.get("release")):
                errors.append(f"f8_release_must_be_false:{target_key}:{item_id}")

    expected_backlog = _by_id(expected["unbounded_bom_route_registry"])
    actual_backlog = _by_id(contract.get("unbounded_bom_route_registry", []))
    if set(actual_backlog) != set(expected_backlog):
        errors.append("unbounded_bom_coverage_mismatch")
    for item_id, wanted in expected_backlog.items():
        actual = actual_backlog.get(item_id)
        if actual is None:
            continue
        if actual.get("quantity") is not None or actual.get("dimensions") is not None:
            errors.append(f"invented_backlog_data:{item_id}")
        if actual.get("route_class") != wanted["route_class"]:
            errors.append(f"backlog_route_class_mismatch:{item_id}")
        for field in ("source_status", "route_status"):
            if actual.get(field) != wanted[field]:
                errors.append(f"backlog_field_mismatch:{item_id}:{field}")
        if not _all_false(actual.get("release")):
            errors.append(f"backlog_release_must_be_false:{item_id}")

    policies = contract.get("conditional_material_policies", {})
    for policy_id in ("titanium", "inconel_nickel_superalloy"):
        policy = policies.get(policy_id, {})
        wanted_policy = expected["conditional_material_policies"][policy_id]
        for field in ("id", "status", "candidate_scopes"):
            if policy.get(field) != wanted_policy[field]:
                errors.append(f"material_policy_field_mismatch:{policy_id}:{field}")
        for field in SPECIAL_MATERIAL_NULL_FIELDS:
            if policy.get(field) is not None:
                errors.append(f"material_selection_forbidden:{policy_id}:{field}")
        if policy.get("required_evidence_topics") != list(SPECIAL_MATERIAL_TOPICS):
            errors.append(f"material_evidence_topics_mismatch:{policy_id}")
        if policy.get("additive_build_authorized") is not False:
            errors.append(f"material_additive_release_forbidden:{policy_id}")
        if policy.get("functional_use_authorized") is not False:
            errors.append(f"material_functional_release_forbidden:{policy_id}")

    errors.extend(_selection_errors(contract))
    if not _all_false(contract.get("release_gates")):
        errors.append("all_release_gates_must_be_false")
    policy = contract.get("functional_engine_policy", {})
    if policy != expected["functional_engine_policy"]:
        errors.append("functional_engine_policy_mismatch")
    if policy.get("fully_additively_manufactured") is not False:
        errors.append("functional_engine_must_not_claim_fully_printed")
    if policy.get("mixed_route_qualified") is not False:
        errors.append("mixed_route_qualification_claim_forbidden")
    if contract.get("asset", {}).get(
        "functional_100_percent_means_100_percent_printed"
    ) is not False:
        errors.append("functional_equals_printed_claim_forbidden")
    if contract.get("counts") != expected["counts"]:
        errors.append("declared_counts_mismatch")
    return sorted(set(errors))


def evaluate(project_root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    errors = validate_contract(project_root, contract)
    return {
        "schema_version": "1.0.0",
        "phase": "F19",
        "asset_id": ASSET_ID,
        "report_status": "passed" if not errors else "failed",
        "contract_errors": errors,
        "counts": contract.get("counts", {}),
        "decision": (
            "routing_contract_consistent_all_manufacturing_and_functional_releases_blocked"
            if not errors
            else "routing_contract_invalid_all_releases_blocked"
        ),
        "release": {
            "prototype_print_authorized": False,
            "metal_additive_build_authorized": False,
            "conventional_manufacturing_authorized": False,
            "hybrid_assembly_authorized": False,
            "functional_engine_authorized": False,
            "vehicle_use_authorized": False,
        },
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--write-contract", action="store_true")
    parser.add_argument(
        "--check",
        action="store_true",
        help="valide le contrat existant sans le modifier (comportement par defaut)",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.write_contract and args.check:
        parser.error("--write-contract and --check are mutually exclusive")
    root = args.project_root.resolve()
    contract_path = args.contract or root / CONTRACT_REL
    if not contract_path.is_absolute():
        contract_path = root / contract_path
    if args.write_contract:
        contract = build_contract(root)
        write_json(contract_path, contract)
    else:
        contract = load_json(contract_path)
    report = evaluate(root, contract)
    if args.output:
        output_path = args.output
        if not output_path.is_absolute():
            output_path = root / output_path
        write_json(output_path, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["report_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
