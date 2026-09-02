#!/usr/bin/env python3
"""Construit et valide le contrat CAO parametrique fail-closed F22 du 917.

F22 ne genere aucune geometrie. Il transforme les registres F12, F13, F16,
F19 et F20 en un arbre d'assemblage non place, un registre de parametres nuls
et une campagne de mesures directement renseignable pour la branche Type 912
4 494 cm3 atmospherique. Les valeurs publiees restent des candidats separes :
elles ne deviennent jamais des cotes de conception ou de fabrication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_RELATIVE_PATH = Path(
    "twins/reference-917-engine/parametric-cad-assembly-contract-f22.json"
)
ASSET_ID = "porsche-917-type-912-4494-parametric-cad-assembly-f22"
BASE_VARIANT = "type_912_4_5_na"

UPSTREAMS: dict[str, dict[str, str]] = {
    "whole_engine_f12": {
        "path": "twins/reference-917-engine/whole-engine-reengineering-f12.json",
        "sha256": "8a2bf024badd0964b272d4b90a5432c912873d59b0821a6f31138fdf5b8c33fd",
    },
    "classical_solver_f13": {
        "path": "twins/reference-917-engine/classical-solver-cases-f13.json",
        "sha256": "1ec8a0c49e95f8f2c8185d4c0f4074d1ed4b36477996ba590cc9f92eccf42a97",
    },
    "kinematic_readiness_f16": {
        "path": "twins/reference-917-engine/kinematic-interface-readiness-f16.json",
        "sha256": "ec5e56cdd750071462e00dcec978182916ee4c266435bfea0720dea2fda2f2e2",
    },
    "manufacturing_routing_f19": {
        "path": "twins/reference-917-engine/manufacturing-routing-f19.json",
        "sha256": "f9fc00c4f51840bb5781ffc21078f7e30febecd6bef202e32e882f0da3130d6f",
    },
    "valvetrain_flow_f20": {
        "path": "twins/reference-917-engine/valvetrain-flow-inputs-f20.json",
        "sha256": "29a3fbe2d57b4e9961dfd7c7e1698dce01a31df0956db499fd3e1e9c87fcf288",
    },
    "scan_scale_orientation_f21": {
        "path": "twins/reference-917-engine/scan-scale-orientation-acquisition-f21.json",
        "sha256": "e958bc9188fb05dbe02e131cdc12f3e466eaa93aa2772e930bf91f733f2d924b",
    },
}

F13_GEOMETRY_FACT_BINDINGS = (
    ("P-CYLINDER-FINISHED-BORE", "FACT-45-BORE"),
    ("P-PISTON-STROKE", "FACT-45-STROKE"),
    ("P-PISTON-PIN-AXIS-TO-CROWN", "FACT-45-PISTON-COMPRESSION-HEIGHT"),
    ("P-CRANKPIN-BEARING-DIAMETER", "FACT-45-CRANKPIN-BEARING-DIAMETER"),
)

F13_REFERENCE_FACTS = (
    "FACT-CYLINDER-COUNT-45-NA",
    "FACT-45-DISPLACEMENT",
    "FACT-45-CRANKSHAFT-MASS",
    "FACT-45-CONNECTING-ROD-BIG-END-DIAMETER",
    "FACT-45-CONNECTING-ROD-MASS",
    "FACT-45-PISTON-GROUP-MASS",
    "FACT-45-CRANKSHAFT-CONSTRUCTION",
)

F20_GEOMETRY_FACT_BINDINGS = (
    ("P-INTAKE-VALVE-OUTER-DIAMETER", "F20-INTAKE-VALVE-OUTER-DIAMETER"),
    ("P-EXHAUST-VALVE-OUTER-DIAMETER", "F20-EXHAUST-VALVE-OUTER-DIAMETER"),
    ("P-INTAKE-PORT-DIAMETER", "F20-INTAKE-PORT-DIAMETER"),
)

F20_TOPOLOGY_FACTS = (
    "F20-CAMSHAFT-COUNT",
    "F20-CAMSHAFT-ARRANGEMENT",
    "F20-CAMSHAFT-DRIVE",
    "F20-VALVE-ACTUATION",
)

EXPECTED_F13_FACTS: dict[str, tuple[str, Any, str, str]] = {
    "FACT-CYLINDER-COUNT-45-NA": (
        "cylinder_count",
        12,
        "count",
        BASE_VARIANT,
    ),
    "FACT-45-BORE": ("cylinder_bore", 85.0, "mm", BASE_VARIANT),
    "FACT-45-STROKE": ("piston_stroke", 66.0, "mm", BASE_VARIANT),
    "FACT-45-DISPLACEMENT": (
        "engine_displacement",
        4494.0,
        "cm3",
        BASE_VARIANT,
    ),
    "FACT-45-PISTON-COMPRESSION-HEIGHT": (
        "piston_pin_axis_to_crown_height",
        43.0,
        "mm",
        BASE_VARIANT,
    ),
    "FACT-45-CRANKPIN-BEARING-DIAMETER": (
        "crankpin_bearing_diameter",
        52.0,
        "mm",
        BASE_VARIANT,
    ),
    "FACT-45-CONNECTING-ROD-BIG-END-DIAMETER": (
        "fia_article_159_dimension_ambiguous",
        56.0,
        "mm",
        BASE_VARIANT,
    ),
    "FACT-45-CRANKSHAFT-MASS": ("crankshaft_mass", 23.75, "kg", BASE_VARIANT),
    "FACT-45-CONNECTING-ROD-MASS": (
        "connecting_rod_mass",
        0.42,
        "kg",
        BASE_VARIANT,
    ),
    "FACT-45-PISTON-GROUP-MASS": (
        "piston_pin_ring_group_mass",
        0.46,
        "kg",
        BASE_VARIANT,
    ),
    "FACT-45-CRANKSHAFT-CONSTRUCTION": (
        "crankshaft_construction",
        "forged_assembled",
        "categorical",
        BASE_VARIANT,
    ),
}

EXPECTED_F20_FACTS: dict[str, tuple[str, Any, str]] = {
    "F20-CAMSHAFT-COUNT": ("camshaft_count", 4, "count"),
    "F20-CAMSHAFT-ARRANGEMENT": ("camshaft_arrangement", "ohc", "categorical"),
    "F20-CAMSHAFT-DRIVE": ("camshaft_drive", "gears", "categorical"),
    "F20-VALVE-ACTUATION": ("valve_actuation", "bucket_tappets", "categorical"),
    "F20-INTAKE-VALVE-OUTER-DIAMETER": (
        "intake_valve_outer_diameter",
        47.5,
        "mm",
    ),
    "F20-EXHAUST-VALVE-OUTER-DIAMETER": (
        "exhaust_valve_outer_diameter",
        40.5,
        "mm",
    ),
    "F20-INTAKE-PORT-DIAMETER": ("intake_port_diameter", 41.0, "mm"),
}


class ContractError(ValueError):
    """Le contrat amont ou F22 ne respecte pas la frontiere d'autorite."""


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


def _by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        item["id"]: item
        for item in items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def _f13_fact_index(f13: dict[str, Any]) -> dict[str, dict[str, Any]]:
    facts = f13.get("fact_registry")
    if not isinstance(facts, list):
        raise ContractError("f13_fact_registry_missing")
    return _by_id(facts)


def _f20_fact_index(f20: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for key in (
        "topology_candidates",
        "cad_dimension_candidates",
        "boundary_condition_candidates",
    ):
        value = f20.get(key)
        if not isinstance(value, list):
            raise ContractError(f"f20_registry_missing:{key}")
        records.extend(value)
    return _by_id(records)


def load_and_validate_upstreams(root: Path) -> dict[str, dict[str, Any]]:
    root = root.resolve()
    result: dict[str, dict[str, Any]] = {}
    for source_id, specification in UPSTREAMS.items():
        path = root / specification["path"]
        if sha256(path) != specification["sha256"]:
            raise ContractError(f"upstream_sha256_mismatch:{source_id}")
        result[source_id] = load_json(path)

    f12 = result["whole_engine_f12"]
    f13 = result["classical_solver_f13"]
    f16 = result["kinematic_readiness_f16"]
    f19 = result["manufacturing_routing_f19"]
    f20 = result["valvetrain_flow_f20"]
    f21 = result["scan_scale_orientation_f21"]

    if f12.get("phase") != "F12" or len(f12.get("family_registry", [])) != 31:
        raise ContractError("f12_contract_mismatch")
    if not _all_false(f12.get("whole_engine_gates", {})):
        raise ContractError("f12_gates_must_remain_false")
    if f13.get("phase") != "F13" or BASE_VARIANT not in f13.get("variants", []):
        raise ContractError("f13_branch_mismatch")
    for key in (
        "solver_execution_authorized",
        "results_present",
        "correlation_complete",
        "engine_start_authorized",
        "fabrication_authorized",
        "metal_print_authorized",
        "physicsnemo_training_authorized",
    ):
        if f13.get("authority_boundary", {}).get(key) is not False:
            raise ContractError(f"f13_authority_must_remain_false:{key}")
    if f16.get("phase") != "F16-001":
        raise ContractError("f16_contract_mismatch")
    if f16.get("work_branch", {}).get("variant_id") != "type_912_5_0_na":
        raise ContractError("f16_expected_foreign_branch_mismatch")
    if not _all_false(f16.get("release_gates", {})):
        raise ContractError("f16_gates_must_remain_false")
    if f19.get("phase") != "F19" or not _all_false(f19.get("release_gates", {})):
        raise ContractError("f19_contract_or_gate_mismatch")
    if f20.get("phase") != "F20" or not _all_false(f20.get("release_gates", {})):
        raise ContractError("f20_contract_or_gate_mismatch")
    if f21.get("phase") != "F21" or f21.get("asset", {}).get(
        "source_scan_sha256"
    ) != "428c4143d073f8330022f2fecbd1ac1ee7784d4f1565f1160020448dbdffa0ae":
        raise ContractError("f21_contract_or_scan_mismatch")
    if not _all_false(f21.get("release_gates", {})):
        raise ContractError("f21_gates_must_remain_false")
    for key in ("identity_ready", "scale_ready", "orientation_ready", "cad_input_ready"):
        if f21.get("current_readiness", {}).get(key) is not False:
            raise ContractError(f"f21_readiness_must_remain_false:{key}")

    f13_facts = _f13_fact_index(f13)
    for fact_id, (quantity, value, unit, variant) in EXPECTED_F13_FACTS.items():
        fact = f13_facts.get(fact_id)
        if not isinstance(fact, dict):
            raise ContractError(f"f13_fact_missing:{fact_id}")
        if fact.get("quantity") != quantity or fact.get("variant") != variant:
            raise ContractError(f"f13_fact_scope_mismatch:{fact_id}")
        if fact.get("candidate", {}).get("value") != value:
            raise ContractError(f"f13_fact_value_mismatch:{fact_id}")
        if fact.get("candidate", {}).get("unit") != unit:
            raise ContractError(f"f13_fact_unit_mismatch:{fact_id}")
        if fact.get("design_lock") is not False:
            raise ContractError(f"f13_design_lock_forbidden:{fact_id}")
    ambiguous_fia_159 = f13_facts["FACT-45-CONNECTING-ROD-BIG-END-DIAMETER"]
    if (
        ambiguous_fia_159.get("candidate", {}).get("kind")
        != "published_point_ambiguous_reference"
        or ambiguous_fia_159.get("usage") != "ambiguous_label_not_geometry_input"
        or "CONTRADICTION-FIA-ARTICLE-159-LABEL"
        not in ambiguous_fia_159.get("contradiction_refs", [])
    ):
        raise ContractError("f13_fia_article_159_ambiguity_contract_mismatch")

    f20_facts = _f20_fact_index(f20)
    for fact_id, (quantity, value, unit) in EXPECTED_F20_FACTS.items():
        fact = f20_facts.get(fact_id)
        if not isinstance(fact, dict):
            raise ContractError(f"f20_fact_missing:{fact_id}")
        if fact.get("quantity") != quantity:
            raise ContractError(f"f20_fact_quantity_mismatch:{fact_id}")
        if fact.get("candidate") != {
            "kind": "published_point",
            "value": value,
            "unit": unit,
        }:
            raise ContractError(f"f20_fact_value_mismatch:{fact_id}")
        if fact.get("direct_variant") != BASE_VARIANT or fact.get("design_lock") is not False:
            raise ContractError(f"f20_fact_authority_mismatch:{fact_id}")

    f12_ids = {item["id"] for item in f12["family_registry"]}
    f19_ids = {item["id"] for item in f19["family_route_registry"]}
    if f12_ids != f19_ids:
        raise ContractError("f12_f19_family_coverage_mismatch")
    return result


def source_manifest(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "id": source_id,
            "path": specification["path"],
            "sha256": sha256(root / specification["path"]),
            "reuse_scope": (
                "schema_and_null_policy_only_no_variant_values_transferred"
                if source_id == "kinematic_readiness_f16"
                else "fail_closed_identity_scale_orientation_gates_only"
                if source_id == "scan_scale_orientation_f21"
                else "traceable_candidates_or_registry_only"
            ),
            "geometry_authority": False,
            "manufacturing_authority": False,
        }
        for source_id, specification in UPSTREAMS.items()
    ]


def f13_candidate(
    f13_facts: dict[str, dict[str, Any]], parameter_id: str, fact_id: str
) -> dict[str, Any]:
    fact = f13_facts[fact_id]
    candidate = fact["candidate"]
    return {
        "parameter_id": parameter_id,
        "source_contract": "classical_solver_f13",
        "source_fact_ref": fact_id,
        "quantity": fact["quantity"],
        "candidate": candidate,
        "classification": "published_source_candidate_not_verified_design_dimension",
        "variant_scope": fact["variant"],
        "usage": fact["usage"],
        "source_refs": fact["source_refs"],
        "design_lock": False,
        "cad_parameter_applied": False,
        "manufacturing_dimension": False,
        "manufacturing_tolerance": None,
    }


def f20_candidate(
    f20_facts: dict[str, dict[str, Any]],
    parameter_id: str | None,
    fact_id: str,
) -> dict[str, Any]:
    fact = f20_facts[fact_id]
    result = {
        "parameter_id": parameter_id,
        "source_contract": "valvetrain_flow_f20",
        "source_fact_ref": fact_id,
        "quantity": fact["quantity"],
        "candidate": fact["candidate"],
        "classification": "published_source_candidate_not_verified_design_dimension",
        "variant_scope": fact["direct_variant"],
        "usage": fact["usage"],
        "source_evidence": fact["source_evidence"],
        "design_lock": False,
        "cad_parameter_applied": False,
        "manufacturing_dimension": False,
        "manufacturing_tolerance": None,
    }
    tolerance_ref = fact.get("declared_tolerance_ref")
    if tolerance_ref is not None:
        result["homologation_declared_tolerance_ref"] = tolerance_ref
        result["homologation_tolerance_is_manufacturing_tolerance"] = False
    return result


def parameter(
    identifier: str,
    quantity: str,
    unit: str,
    measurement_method: str,
    *,
    cardinality: str = "one",
) -> dict[str, Any]:
    return {
        "id": identifier,
        "quantity": quantity,
        "unit": unit,
        "cardinality": cardinality,
        "value": None,
        "uncertainty": None,
        "datum_ref": None,
        "evidence_ref": None,
        "review_status": None,
        "status": "unknown_requires_traceable_measurement",
        "preferred_measurement_method": measurement_method,
        "design_lock": False,
        "manufacturing_dimension": False,
        "manufacturing_tolerance": None,
    }


def parameter_groups() -> list[dict[str, Any]]:
    cmm_ct = "traceable_CMM_or_CT_with_named_datums"
    teardown = "instrumented_teardown_plus_traceable_dimensional_metrology"
    profile = "CMM_or_optical_profile_metrology_plus_section_or_CT"
    return [
        {
            "id": "global_datums_and_layout",
            "parameters": [
                parameter("P-ENGINE-REFERENCE-FRAME", "engine_reference_frame", "frame", cmm_ct),
                parameter("P-CRANKSHAFT-AXIS", "crankshaft_axis", "line_in_frame", cmm_ct),
                parameter("P-CRANKCASE-SPLIT-PLANE", "crankcase_split_plane", "plane_in_frame", cmm_ct),
                parameter("P-POSITIVE-BANK-DECK", "positive_bank_deck_plane", "plane_in_frame", cmm_ct),
                parameter("P-NEGATIVE-BANK-DECK", "negative_bank_deck_plane", "plane_in_frame", cmm_ct),
                parameter("P-BANK-INCLUDED-ANGLE", "bank_included_angle", "deg", cmm_ct),
                parameter("P-PISTON-STROKE", "assembled_piston_stroke", "mm", teardown),
                parameter("P-CYLINDER-AXES", "cylinder_axis_frames", "frame", cmm_ct, cardinality="12_candidate"),
                parameter("P-CYLINDER-PITCHES", "successive_cylinder_axis_pitch", "mm", cmm_ct, cardinality="10_plus_central_relationship"),
            ],
        },
        {
            "id": "crankcase_and_main_bearings",
            "parameters": [
                parameter("P-MAIN-BEARING-STATIONS", "main_bearing_station_frames", "frame", cmm_ct, cardinality="8_candidate"),
                parameter("P-MAIN-BEARING-SEAT-DIAMETERS", "main_bearing_seat_diameter", "mm", "CMM_plus_calibrated_bore_gauge", cardinality="8_candidate"),
                parameter("P-MAIN-BEARING-SEAT-WIDTHS", "main_bearing_seat_width", "mm", "CMM", cardinality="8_candidate"),
                parameter("P-CASE-CYLINDER-REGISTERS", "crankcase_cylinder_register_geometry", "mm_and_frame", cmm_ct, cardinality="12_candidate"),
                parameter("P-CASE-STUD-PATTERNS", "crankcase_head_stud_thread_pattern", "mm_and_thread_spec", cmm_ct, cardinality="12_candidate"),
                parameter("P-CASE-OIL-GALLERIES", "crankcase_internal_oil_gallery_geometry", "mm", "CT_plus_sectioned_reference_if_available"),
                parameter("P-CASE-MOUNT-INTERFACES", "crankcase_mount_interface_frames", "frame_and_thread_spec", cmm_ct),
                parameter("P-CASE-OUTPUT-INTERFACE", "central_output_interface_geometry", "mm_and_frame", cmm_ct),
            ],
        },
        {
            "id": "crankshaft",
            "parameters": [
                parameter("P-CRANK-MAIN-JOURNALS", "crankshaft_main_journal_geometry", "mm", "CMM_plus_roundness_metrology", cardinality="8_candidate"),
                parameter("P-CRANKPIN-FRAMES", "crankpin_frames_and_phase", "frame_and_deg", "CMM_plus_degree_wheel_teardown", cardinality="12_candidate"),
                parameter("P-CRANKPIN-BEARING-DIAMETER", "crankpin_bearing_diameter", "mm", "CMM_plus_form_metrology", cardinality="12_candidate"),
                parameter("P-CRANKPIN-JOURNAL-WIDTHS", "crankpin_journal_width", "mm", "CMM", cardinality="12_candidate"),
                parameter("P-CRANK-FILLETS", "crankshaft_fillet_geometry", "mm", profile),
                parameter("P-CRANK-COUNTERWEIGHTS", "crankshaft_counterweight_geometry", "mm", cmm_ct),
                parameter("P-CRANK-OIL-DRILLINGS", "crankshaft_internal_oil_drillings", "mm", "CT_plus_borescope"),
                parameter("P-CRANK-OUTPUT-REGISTER", "crankshaft_output_register_and_fastener_pattern", "mm_and_thread_spec", cmm_ct),
            ],
        },
        {
            "id": "connecting_rod",
            "parameters": [
                parameter("P-ROD-CENTRE-DISTANCE", "rod_big_end_to_small_end_centre_distance", "mm", "CMM", cardinality="12_candidate"),
                parameter("P-ROD-BIG-END-BORES", "rod_big_end_finished_bore", "mm", "CMM_plus_bore_gauge", cardinality="12_candidate"),
                parameter("P-ROD-BIG-END-DIAMETER", "connecting_rod_big_end_diameter", "mm", "CMM_plus_optical_profile", cardinality="12_candidate"),
                parameter("P-ROD-SMALL-END-BORES", "rod_small_end_finished_bore", "mm", "CMM_plus_bore_gauge", cardinality="12_candidate"),
                parameter("P-ROD-END-WIDTHS", "rod_big_and_small_end_widths", "mm", "CMM", cardinality="12_candidate"),
                parameter("P-ROD-OFFSETS", "rod_end_lateral_offsets", "mm", "CMM", cardinality="12_candidate"),
                parameter("P-ROD-BOLT-INTERFACE", "rod_cap_bolt_and_register_geometry", "mm_and_thread_spec", teardown, cardinality="12_candidate"),
                parameter("P-ROD-PROFILE", "rod_beam_and_transition_profile", "mm", profile, cardinality="12_candidate"),
            ],
        },
        {
            "id": "piston_pin_and_rings",
            "parameters": [
                parameter("P-PISTON-PIN-DIAMETER", "piston_pin_outer_diameter", "mm", "micrometer_plus_CMM", cardinality="12_candidate"),
                parameter("P-PISTON-PIN-LENGTH", "piston_pin_length", "mm", "CMM", cardinality="12_candidate"),
                parameter("P-PISTON-PIN-BORE", "piston_pin_internal_bore_profile", "mm", "CT_plus_bore_metrology", cardinality="12_candidate"),
                parameter("P-PISTON-CROWN-PROFILE", "piston_crown_and_combustion_profile", "mm", profile, cardinality="12_candidate"),
                parameter("P-PISTON-PIN-AXIS-TO-CROWN", "piston_pin_axis_to_crown_height", "mm", "CMM", cardinality="12_candidate"),
                parameter("P-PISTON-SKIRT-PROFILE", "piston_skirt_profile_and_ovality", "mm", "CMM_plus_form_metrology", cardinality="12_candidate"),
                parameter("P-PISTON-PIN-BOSS", "piston_pin_boss_geometry", "mm", "CT_plus_CMM", cardinality="12_candidate"),
                parameter("P-PISTON-RING-GROOVES", "piston_ring_groove_geometry", "mm", profile, cardinality="36_candidate"),
                parameter("P-PISTON-DECK-CLEARANCE", "assembled_piston_to_deck_clearance", "mm", teardown, cardinality="12_candidate"),
            ],
        },
        {
            "id": "cylinder_and_head",
            "parameters": [
                parameter("P-CYLINDER-FINISHED-BORE", "cylinder_finished_bore", "mm", "CMM_plus_bore_form_metrology", cardinality="12_candidate"),
                parameter("P-CYLINDER-SPIGOTS", "cylinder_spigot_and_register_geometry", "mm", "CMM", cardinality="12_candidate"),
                parameter("P-CYLINDER-DECK-HEIGHT", "cylinder_deck_height", "mm", "CMM", cardinality="12_candidate"),
                parameter("P-CYLINDER-FIN-ENVELOPE", "cylinder_cooling_fin_geometry", "mm", "structured_light_plus_CMM", cardinality="12_candidate"),
                parameter("P-HEAD-REGISTER", "head_to_cylinder_register_geometry", "mm", "CMM", cardinality="12_candidate"),
                parameter("P-HEAD-STUD-INTERFACES", "head_stud_clearance_and_clamping_faces", "mm", "CMM", cardinality="12_candidate"),
                parameter("P-HEAD-COMBUSTION-CHAMBER", "combustion_chamber_surface", "mm3_and_surface", "CT_plus_CMM_plus_volume_metrology", cardinality="12_candidate"),
                parameter("P-INTAKE-PORT-SURFACE", "intake_port_internal_surface", "surface", "CT_plus_optical_scan", cardinality="12_candidate"),
                parameter("P-EXHAUST-PORT-SURFACE", "exhaust_port_internal_surface", "surface", "CT_plus_optical_scan", cardinality="12_candidate"),
                parameter("P-INTAKE-PORT-DIAMETER", "intake_port_diameter_at_declared_section", "mm", "CMM_or_calibrated_internal_metrology", cardinality="12_candidate"),
                parameter("P-HEAD-COOLING-FINS", "head_cooling_fin_geometry", "mm", "structured_light_plus_CMM", cardinality="12_candidate"),
                parameter("P-HEAD-OIL-PASSAGES", "head_internal_oil_passage_geometry", "mm", "CT_plus_borescope", cardinality="12_candidate"),
            ],
        },
        {
            "id": "valvetrain_and_cam_drive",
            "parameters": [
                parameter("P-INTAKE-VALVE-OUTER-DIAMETER", "intake_valve_outer_diameter", "mm", "CMM_plus_optical_profile", cardinality="12_candidate"),
                parameter("P-EXHAUST-VALVE-OUTER-DIAMETER", "exhaust_valve_outer_diameter", "mm", "CMM_plus_optical_profile", cardinality="12_candidate"),
                parameter("P-VALVE-STEMS", "valve_stem_diameter_length_and_profile", "mm", "CMM_plus_form_metrology", cardinality="24_candidate"),
                parameter("P-VALVE-SEATS", "valve_seat_cone_width_runout_and_location", "mm_and_deg", "CMM_plus_form_metrology", cardinality="24_candidate"),
                parameter("P-VALVE-GUIDES", "valve_guide_bore_length_and_location", "mm_and_frame", "CMM_plus_bore_gauge", cardinality="24_candidate"),
                parameter("P-CAMSHAFT-AXES", "camshaft_axis_frames", "frame", cmm_ct, cardinality="4_candidate"),
                parameter("P-CAM-JOURNALS", "camshaft_journal_geometry", "mm", "CMM_plus_form_metrology", cardinality="unknown"),
                parameter("P-CAM-LOBE-LAWS", "cam_lobe_surface_and_lift_law", "surface_and_deg", "cam_profiler_plus_CMM", cardinality="24_candidate"),
                parameter("P-BUCKET-TAPPETS", "bucket_tappet_geometry_and_clearance", "mm", "CMM_plus_bore_gauge", cardinality="24_candidate"),
                parameter("P-CAM-GEAR-TRAIN", "cam_gear_tooth_counts_profiles_centres_and_backlash", "mm_deg_and_count", teardown, cardinality="unknown"),
            ],
        },
        {
            "id": "intake_exhaust_and_accessories",
            "parameters": [
                parameter("P-INTAKE-TRUMPETS", "intake_trumpet_internal_and_mounting_geometry", "surface_and_mm", "CT_plus_CMM", cardinality="12_candidate"),
                parameter("P-INJECTOR-INTERFACES", "injector_mount_and_spray_axis_frame", "frame_and_thread_spec", cmm_ct, cardinality="12_candidate"),
                parameter("P-EXHAUST-PRIMARY-PORTS", "exhaust_primary_mounting_and_internal_geometry", "surface_and_mm", "CT_plus_CMM", cardinality="12_candidate"),
                parameter("P-EXHAUST-COLLECTORS", "exhaust_collector_internal_and_joint_geometry", "surface_and_mm", "CT_plus_CMM", cardinality="2_candidate"),
                parameter("P-BLOWER-INTERFACE", "cooling_blower_axis_mount_and_shroud_geometry", "frame_and_surface", cmm_ct),
                parameter("P-OIL-PUMP-INTERFACES", "pressure_and_scavenge_pump_mount_drive_and_ports", "frame_and_mm", teardown),
                parameter("P-ALTERNATOR-INTERFACE", "alternator_mount_and_drive_interface", "frame_and_mm", teardown),
            ],
        },
    ]


def family_assembly_records(
    f12: dict[str, Any], f19: dict[str, Any]
) -> list[dict[str, Any]]:
    routes = _by_id(f19["family_route_registry"])
    records: list[dict[str, Any]] = []
    for family in f12["family_registry"]:
        if family["visual_variant"] == "917_30_only":
            continue
        route = routes[family["id"]]
        records.append(
            {
                "family_id": family["id"],
                "variant_scope": BASE_VARIANT,
                "occurrence_count_candidate": family["visual_count"],
                "occurrence_count_status": "visual_registry_candidate_not_real_bom",
                "cad_master": None,
                "cad_master_format": None,
                "placement_transform": None,
                "interface_definition_refs": [],
                "material_specification": None,
                "mass_kg": None,
                "inertia_kg_m2": None,
                "functional_route_class_candidate": route["functional_disposition"][
                    "route_class"
                ],
                "selected_material_grade": None,
                "selected_process": None,
                "selected_tolerance_set": None,
                "geometry_status": "not_authored",
                "release": {
                    "layout": False,
                    "solid": False,
                    "assembly": False,
                    "prototype_print": False,
                    "metal_print": False,
                    "functional": False,
                },
            }
        )
    return records


def interface_templates() -> list[dict[str, Any]]:
    specifications = (
        ("crankcase_supports_crankshaft", "crankcase_half", "main_bearing", "crankshaft", "revolute_bearing_candidate", "8_candidate"),
        ("crankshaft_to_connecting_rod", "crankshaft", None, "connecting_rod", "revolute_candidate", "12_candidate"),
        ("connecting_rod_to_piston_pin", "connecting_rod", None, "piston_pin", "revolute_candidate", "12_candidate"),
        ("piston_pin_to_piston", "piston_pin", None, "piston", "fit_definition_unknown", "12_candidate"),
        ("piston_to_cylinder", "piston", None, "individual_cylinder", "prismatic_candidate", "12_candidate"),
        ("cylinder_to_crankcase", "individual_cylinder", None, "crankcase_half", "fixed_interface_candidate", "12_candidate"),
        ("head_to_cylinder", "individual_head", None, "individual_cylinder", "fixed_clamped_candidate", "12_candidate"),
        ("valve_to_head_guide", "intake_valve_or_exhaust_valve", None, "individual_head", "prismatic_candidate", "24_candidate"),
        ("camshaft_to_carrier", "camshaft", None, "cam_carrier", "revolute_candidate", "4_candidate"),
        ("cam_drive_gear_meshes", "cam_drive_gear", None, "cam_drive_gear", "gear_mesh_candidate", "unknown"),
    )
    return [
        {
            "id": identifier,
            "from_family": body_a,
            "via_family": via,
            "to_family": body_b,
            "planned_relation": relation,
            "count": count,
            "count_is_verified_bom": False,
            "source_basis": "assembly_requirement_not_measured_interface",
            "frame_a": None,
            "frame_b": None,
            "mating_geometry": None,
            "fit_or_clearance": None,
            "fastener_or_retention": None,
            "surface_finish": None,
            "tolerance_stack": None,
            "evidence_ref": None,
            "active": False,
            "physics_joint_enabled": False,
            "manufacturing_released": False,
        }
        for identifier, body_a, via, body_b, relation, count in specifications
    ]


def measurement_packages() -> list[dict[str, Any]]:
    specifications = (
        ("F22-MC-DATUM-01", "referentiel_moteur_et_deux_bancs", "global_datums_and_layout", "CMM_or_CT_with_named_datums", 1),
        ("F22-MC-CASE-01", "carter_et_ligne_de_paliers", "crankcase_and_main_bearings", "CMM_CT_bore_gauge", 1),
        ("F22-MC-CRANK-01", "vilebrequin_complet", "crankshaft", "CMM_form_metrology_CT", 1),
        ("F22-MC-ROD-01", "bielles_identifiees", "connecting_rod", "CMM_and_teardown", 12),
        ("F22-MC-PISTON-01", "pistons_axes_segments_identifies", "piston_pin_and_rings", "CMM_CT_form_metrology", 12),
        ("F22-MC-CYLHEAD-01", "cylindres_et_culasses_identifies", "cylinder_and_head", "CMM_CT_volume_metrology", 12),
        ("F22-MC-VALVE-01", "distribution_et_entrainement_de_cames", "valvetrain_and_cam_drive", "CMM_cam_profiler_degree_wheel", 1),
        ("F22-MC-DUCT-01", "admission_echappement_et_accessoires", "intake_exhaust_and_accessories", "CMM_CT_and_teardown", 1),
        ("F22-MC-STACK-01", "assemblage_a_blanc_instrumente", "all_groups", "measured_dry_build_and_tolerance_stack_review", 1),
    )
    return [
        {
            "id": identifier,
            "target": target,
            "parameter_group_ref": group,
            "preferred_method": method,
            "minimum_physical_occurrences": occurrences,
            "branch_identity_required": BASE_VARIANT,
            "values_registered": False,
            "evidence_package_ref": None,
            "review_status": None,
            "required_evidence_fields": [
                "physical_part_identity",
                "instrument_id",
                "calibration_certificate",
                "measurement_temperature_c",
                "datum_scheme",
                "raw_measurement_artifact_sha256",
                "uncertainty_budget",
                "operator_or_lab",
                "independent_review",
            ],
        }
        for identifier, target, group, method, occurrences in specifications
    ]


def build_contract(root: Path) -> dict[str, Any]:
    root = root.resolve()
    upstream = load_and_validate_upstreams(root)
    f12 = upstream["whole_engine_f12"]
    f13 = upstream["classical_solver_f13"]
    f19 = upstream["manufacturing_routing_f19"]
    f20 = upstream["valvetrain_flow_f20"]
    f21 = upstream["scan_scale_orientation_f21"]
    f13_facts = _f13_fact_index(f13)
    f20_facts = _f20_fact_index(f20)

    geometry_candidates = [
        f13_candidate(f13_facts, parameter_id, fact_id)
        for parameter_id, fact_id in F13_GEOMETRY_FACT_BINDINGS
    ] + [
        f20_candidate(f20_facts, parameter_id, fact_id)
        for parameter_id, fact_id in F20_GEOMETRY_FACT_BINDINGS
    ]
    reference_candidates = [
        f13_candidate(f13_facts, "not_a_cad_parameter", fact_id)
        for fact_id in F13_REFERENCE_FACTS
    ]
    topology_candidates = [
        f20_candidate(f20_facts, None, fact_id) for fact_id in F20_TOPOLOGY_FACTS
    ]

    bore = EXPECTED_F13_FACTS["FACT-45-BORE"][1]
    stroke = EXPECTED_F13_FACTS["FACT-45-STROKE"][1]
    cylinder_count = EXPECTED_F13_FACTS["FACT-CYLINDER-COUNT-45-NA"][1]
    derived_displacement = cylinder_count * math.pi * bore**2 * stroke / 4.0 / 1000.0

    return {
        "$comment": (
            "F22 prepare la CAO parametrique de la branche Type 912 4 494 cm3 "
            "sans generer de geometrie. Aucune valeur publiee n'est une cote de "
            "conception; tous les parametres a mesurer restent null et tous les "
            "gates de CAO, simulation et fabrication restent fermes."
        ),
        "schema_version": "1.0.0",
        "phase": "F22",
        "status": "parametric_cad_assembly_contract_ready_no_geometry_all_release_gates_blocked",
        "asset": {
            "id": ASSET_ID,
            "target": "Porsche 917 Type 912 4 494 cm3 atmospherique",
            "variant_id": BASE_VARIANT,
            "current_verified_level": "source_candidates_and_measurement_schema_only",
            "geometry_generated": False,
            "raw_scan_in_git": False,
            "proprietary_source_in_git": False,
            "real_bom_complete": False,
        },
        "upstream_contracts": source_manifest(root),
        "f21_dependency": {
            "source_contract": "scan_scale_orientation_f21",
            "source_phase": "F21",
            "source_sha256": UPSTREAMS["scan_scale_orientation_f21"]["sha256"],
            "required_gate_results": {
                "scan_identity_verified": f21["release_gates"]["scan_identity_verified"],
                "scan_scale_verified": f21["release_gates"]["scan_scale_verified"],
                "scan_orientation_verified": f21["release_gates"]["scan_orientation_verified"],
                "f11_source_identity_and_scale_adapter_ready": f21["release_gates"][
                    "f11_source_identity_and_scale_adapter_ready"
                ],
            },
            "satisfied": False,
            "policy": (
                "F22 lit le contrat F21 exact par SHA-256. Ses gates identite, "
                "echelle, orientation et adaptateur F11 doivent tous etre valides "
                "avant toute coordonnee, solide ou superposition avec le scan."
            ),
        },
        "branch_scope": {
            "selected_variant": BASE_VARIANT,
            "other_variant_geometry_inheritance_authorized": False,
            "f16_source_variant": "type_912_5_0_na",
            "f16_reuse": "schema_and_null_policy_only",
            "f16_coordinates_or_dimensions_transferred": False,
            "turbo_parts_in_scope": False,
        },
        "dimension_authority": {
            "verified_design_dimensions": [],
            "verified_manufacturing_dimensions": [],
            "published_geometry_candidates": geometry_candidates,
            "published_reference_candidates_not_geometry": reference_candidates,
            "published_topology_candidates": topology_candidates,
            "f20_facts_explicitly_not_used_as_static_cad_dimensions": [
                {
                    "source_fact_ref": item["id"],
                    "candidate": item["candidate"],
                    "reason": (
                        "motion_or_setup_candidate_requires_a_measured_cam_law_and_"
                        "assembled_kinematic_validation"
                    ),
                    "cad_parameter_applied": False,
                }
                for item in f20["boundary_condition_candidates"]
            ],
            "f20_unresolved_inputs_preserved": [
                {
                    "source_fact_ref": item["id"],
                    "quantity": item["quantity"],
                    "value": None,
                    "status": item["status"],
                }
                for item in f20["unresolved_required_inputs"]
            ],
            "candidate_application_policy": (
                "Chaque candidat reste separe du parametre CAO null jusqu'a "
                "mesure tracable, incertitude, revue et verrouillage explicite."
            ),
        },
        "transparent_layout_guides": [
            {
                "id": "GUIDE-CANDIDATE-CRANK-RADIUS",
                "formula": "FACT-45-STROKE / 2",
                "source_fact_refs": ["FACT-45-STROKE"],
                "value": stroke / 2.0,
                "unit": "mm",
                "classification": "derived_layout_guide_not_design_dimension",
                "cad_parameter_applied": False,
                "manufacturing_dimension": False,
            },
            {
                "id": "CHECK-CANDIDATE-GEOMETRIC-DISPLACEMENT",
                "formula": "12 * pi * bore^2 * stroke / 4 / 1000",
                "source_fact_refs": [
                    "FACT-CYLINDER-COUNT-45-NA",
                    "FACT-45-BORE",
                    "FACT-45-STROKE",
                    "FACT-45-DISPLACEMENT",
                ],
                "value": round(derived_displacement, 9),
                "unit": "cm3",
                "published_comparison_value": 4494.0,
                "classification": "consistency_check_not_design_dimension",
                "cad_parameter_applied": False,
                "manufacturing_dimension": False,
            },
        ],
        "assembly_tree": family_assembly_records(f12, f19),
        "parameter_groups": parameter_groups(),
        "interface_templates": interface_templates(),
        "measurement_packages": measurement_packages(),
        "measurement_evidence_template": {
            "measurement_id": None,
            "parameter_id": None,
            "physical_part_identity": None,
            "value": None,
            "unit": None,
            "uncertainty": None,
            "instrument_id": None,
            "calibration_certificate": None,
            "measurement_temperature_c": None,
            "datum_scheme": None,
            "raw_measurement_artifact_sha256": None,
            "operator_or_lab": None,
            "independent_reviewer": None,
            "review_status": None,
        },
        "cad_authoring_policy": {
            "current_outputs_allowed": ["json_contract", "measurement_records"],
            "future_editable_master_candidates": ["FCStd", "STEP_AP242"],
            "future_derived_visualization_candidates": ["OpenUSD"],
            "current_geometry_generation_authorized": False,
            "coordinates_authorized": False,
            "solids_authorized": False,
            "meshes_authorized": False,
            "curves_authorized": False,
            "materials_authorized": False,
            "joints_authorized": False,
            "physics_schemas_authorized": False,
            "fabrication_exports_authorized": False,
            "stl_or_3mf_export_authorized": False,
            "unknown_values_must_be_null": True,
        },
        "physicsnemo_policy": {
            "role": "surrogate_only_after_qualified_geometry_and_correlated_classical_solvers",
            "training_authorized": False,
            "dataset_ready": False,
            "geometry_ready": False,
            "classical_solver_baseline_correlated": False,
            "instrumented_bench_correlation_complete": False,
        },
        "release_gates": {
            "f21_scale_and_orientation_validated": False,
            "physical_variant_identity_validated": False,
            "real_bom_enumerated": False,
            "datums_measured_and_reviewed": False,
            "all_critical_parameters_measured": False,
            "interface_graph_dimensioned": False,
            "tolerance_stacks_validated": False,
            "cad_layout_authorized": False,
            "cad_solids_authorized": False,
            "assembly_constraints_authorized": False,
            "materials_selected_and_sourced": False,
            "classical_solver_execution_authorized": False,
            "physicsnemo_training_authorized": False,
            "prototype_print_authorized": False,
            "metal_print_authorized": False,
            "functional_engine_authorized": False,
        },
        "prohibited_claims": [
            "published_candidate_is_verified_design_dimension",
            "f16_5_litre_coordinate_or_dimension_applies_to_4494_branch",
            "f21_gate_is_satisfied_or_bypassed",
            "visual_family_count_is_real_bom",
            "cad_geometry_exists_or_is_dimensionally_accurate",
            "route_class_is_selected_material_or_process",
            "scan_or_proxy_is_printable_engine_geometry",
            "physicsnemo_is_reference_solver_or_release_authority",
            "functional_engine_can_be_100_percent_additively_manufactured",
        ],
    }


def _walk_strings(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, str):
        result.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            result.extend(_walk_strings(item))
    elif isinstance(value, list):
        for item in value:
            result.extend(_walk_strings(item))
    return result


def validate_contract(root: Path, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        expected = build_contract(root)
    except (ContractError, OSError, ValueError) as exc:
        return [str(exc)]

    if contract.get("phase") != "F22":
        errors.append("phase_mismatch")
    if contract.get("asset", {}).get("id") != ASSET_ID:
        errors.append("asset_id_mismatch")
    if contract.get("branch_scope", {}).get("selected_variant") != BASE_VARIANT:
        errors.append("branch_scope_mismatch")
    if contract.get("dimension_authority", {}).get("verified_design_dimensions") != []:
        errors.append("verified_design_dimension_claim_forbidden")
    if contract.get("dimension_authority", {}).get("verified_manufacturing_dimensions") != []:
        errors.append("verified_manufacturing_dimension_claim_forbidden")

    dependency = contract.get("f21_dependency", {})
    if dependency.get("source_sha256") != UPSTREAMS["scan_scale_orientation_f21"]["sha256"]:
        errors.append("f21_dependency_sha256_mismatch")
    if dependency.get("required_gate_results") != {
        "scan_identity_verified": False,
        "scan_scale_verified": False,
        "scan_orientation_verified": False,
        "f11_source_identity_and_scale_adapter_ready": False,
    }:
        errors.append("f21_required_gates_must_remain_false")
    if dependency.get("satisfied") is not False:
        errors.append("f21_gate_must_remain_closed")

    groups = contract.get("parameter_groups", [])
    parameter_records = [
        item
        for group in groups
        if isinstance(group, dict)
        for item in group.get("parameters", [])
        if isinstance(item, dict)
    ]
    if len(parameter_records) != 71:
        errors.append("parameter_registry_count_mismatch")
    if len({item.get("id") for item in parameter_records}) != len(parameter_records):
        errors.append("parameter_ids_not_unique")
    for item in parameter_records:
        if item.get("value") is not None:
            errors.append(f"unknown_parameter_value_must_be_null:{item.get('id')}")
        if item.get("design_lock") is not False or item.get("manufacturing_dimension") is not False:
            errors.append(f"parameter_authority_forbidden:{item.get('id')}")
        if item.get("manufacturing_tolerance") is not None:
            errors.append(f"manufacturing_tolerance_forbidden:{item.get('id')}")

    for candidate_group in (
        "published_geometry_candidates",
        "published_reference_candidates_not_geometry",
        "published_topology_candidates",
    ):
        for item in contract.get("dimension_authority", {}).get(candidate_group, []):
            if item.get("design_lock") is not False or item.get("cad_parameter_applied") is not False:
                errors.append(f"candidate_application_forbidden:{item.get('source_fact_ref')}")
            if item.get("manufacturing_dimension") is not False:
                errors.append(f"candidate_manufacturing_claim_forbidden:{item.get('source_fact_ref')}")
            if item.get("manufacturing_tolerance") is not None:
                errors.append(f"candidate_manufacturing_tolerance_forbidden:{item.get('source_fact_ref')}")

    expected_families = {item["family_id"] for item in expected["assembly_tree"]}
    actual_families = {
        item.get("family_id")
        for item in contract.get("assembly_tree", [])
        if isinstance(item, dict)
    }
    if actual_families != expected_families:
        errors.append("assembly_family_coverage_mismatch")
    for item in contract.get("assembly_tree", []):
        if item.get("cad_master") is not None or item.get("placement_transform") is not None:
            errors.append(f"assembly_geometry_or_placement_forbidden:{item.get('family_id')}")
        if not _all_false(item.get("release", {})):
            errors.append(f"family_release_must_remain_false:{item.get('family_id')}")
        for key in ("selected_material_grade", "selected_process", "selected_tolerance_set"):
            if item.get(key) is not None:
                errors.append(f"family_selection_forbidden:{item.get('family_id')}:{key}")

    for item in contract.get("interface_templates", []):
        for key in (
            "frame_a",
            "frame_b",
            "mating_geometry",
            "fit_or_clearance",
            "fastener_or_retention",
            "surface_finish",
            "tolerance_stack",
            "evidence_ref",
        ):
            if item.get(key) is not None:
                errors.append(f"interface_value_forbidden:{item.get('id')}:{key}")
        for key in ("active", "physics_joint_enabled", "manufacturing_released"):
            if item.get(key) is not False:
                errors.append(f"interface_authority_forbidden:{item.get('id')}:{key}")

    if not _all_false(contract.get("release_gates", {})):
        errors.append("release_gates_must_remain_false")
    if not _all_false(
        {
            key: value
            for key, value in contract.get("physicsnemo_policy", {}).items()
            if isinstance(value, bool)
        }
    ):
        errors.append("physicsnemo_authority_must_remain_false")

    strings = _walk_strings(contract)
    for forbidden in (".pdf", ".obj", ".stl", ".3mf", "work/"):
        if any(forbidden in value.lower() for value in strings):
            errors.append(f"restricted_artifact_reference_forbidden:{forbidden}")

    if contract != expected:
        errors.append("contract_differs_from_deterministic_source")
    return sorted(set(errors))


def evaluate(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    errors = validate_contract(root, contract)
    return {
        "schema_version": "1.0.0",
        "phase": "F22",
        "asset_id": ASSET_ID,
        "report_status": "passed" if not errors else "failed",
        "contract_errors": errors,
        "geometry_generated": False,
        "release": {
            "cad_layout": False,
            "cad_solids": False,
            "assembly": False,
            "simulation": False,
            "physicsnemo": False,
            "prototype_print": False,
            "metal_print": False,
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
