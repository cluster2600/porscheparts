#!/usr/bin/env python3
"""Construit et valide les entrees soupapes, cames et conduit FIA de F20.

Le PDF officiel reste externe au depot. Le generateur ne conserve que des faits
lisibles, leur page et leur position de formulaire. Il ne libere aucune CAO,
condition limite, simulation, fabrication ou impression.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


F13_RELATIVE_PATH = Path("twins/reference-917-engine/classical-solver-cases-f13.json")
SOURCE_RELATIVE_PATH = Path("catalog/sources/src-fia-917-homologation-250.json")
OUTPUT_RELATIVE_PATH = Path("twins/reference-917-engine/valvetrain-flow-inputs-f20.json")

EXPECTED_F13_SHA256 = "1ec8a0c49e95f8f2c8185d4c0f4074d1ed4b36477996ba590cc9f92eccf42a97"
EXPECTED_SOURCE_SHA256 = "f253d07d178fecdb62f6c79d6fa94764ebd8f60048f1d019fa7873c62cad69a1"
EXPECTED_PDF_SHA256 = "92a03ecef96a68cd227d0ef9f5f7413a7519a04ef24796330fbee4874b2226cd"
EXPECTED_PDF_BYTES = 9_430_508
EXPECTED_PDF_PAGES = 17
SOURCE_ID = "SRC-FIA-917-HOMOLOGATION-250"
BASE_VARIANT = "type_912_4_5_na"
EXTENSION_VARIANT = "type_912_4_907_na_homologation_extension_1_1E"

REQUIRED_FALSE_GATES = (
    "cad_ready",
    "cfd_ready",
    "combustion_ready",
    "manufacturing_ready",
    "print_ready",
    "physicsnemo_ready",
)


class InputContractError(ValueError):
    """Le registre amont ne correspond pas au contrat F20 attendu."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputContractError(f"expected_json_object:{path.name}")
    return value


def _fact_index(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    facts = registry.get("fact_registry")
    if not isinstance(facts, list):
        raise InputContractError("f13_fact_registry_missing")
    index: dict[str, dict[str, Any]] = {}
    for item in facts:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise InputContractError("f13_fact_registry_invalid")
        if item["id"] in index:
            raise InputContractError(f"f13_fact_duplicate:{item['id']}")
        index[item["id"]] = item
    return index


def validate_upstream(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    f13_path = root / F13_RELATIVE_PATH
    source_path = root / SOURCE_RELATIVE_PATH
    if not f13_path.is_file() or not source_path.is_file():
        raise InputContractError("required_upstream_file_missing")
    if sha256(f13_path) != EXPECTED_F13_SHA256:
        raise InputContractError("f13_sha256_mismatch")
    if sha256(source_path) != EXPECTED_SOURCE_SHA256:
        raise InputContractError("fia_source_record_sha256_mismatch")

    f13 = load_json(f13_path)
    source = load_json(source_path)
    if f13.get("asset_id") != "porsche-917-classical-solver-cases-f13":
        raise InputContractError("f13_asset_identity_mismatch")
    if f13.get("phase") != "F13":
        raise InputContractError("f13_phase_mismatch")
    variants = f13.get("variants")
    if not isinstance(variants, list) or not {BASE_VARIANT, EXTENSION_VARIANT}.issubset(variants):
        raise InputContractError("f13_required_variants_missing")
    authority = f13.get("authority_boundary")
    if not isinstance(authority, dict):
        raise InputContractError("f13_authority_missing")
    for key in (
        "solver_execution_authorized",
        "results_present",
        "fabrication_authorized",
        "metal_print_authorized",
        "physicsnemo_training_authorized",
    ):
        if authority.get(key) is not False:
            raise InputContractError(f"f13_authority_must_remain_false:{key}")

    fia_source = next(
        (
            item
            for item in f13.get("source_registry", [])
            if isinstance(item, dict) and item.get("source_id") == SOURCE_ID
        ),
        None,
    )
    if fia_source != {
        "source_id": SOURCE_ID,
        "catalog_path": str(SOURCE_RELATIVE_PATH),
        "language": "fr_de_en",
        "rights": "reference_only",
        "catalog_declared_evidence_level": "A",
        "usage_note": "Valeurs declarees propres aux variantes 4 494,2 cm3 et extension 1/1E 4 907,28 cm3; aucune tolerance ni autorite de fabrication.",
    }:
        raise InputContractError("f13_fia_source_contract_mismatch")

    facts = _fact_index(f13)
    expected_extension_facts = {
        "FACT-4907-BORE": ("cylinder_bore", 86.0, "mm"),
        "FACT-4907-STROKE": ("piston_stroke", 70.4, "mm"),
        "FACT-4907-DISPLACEMENT": ("engine_displacement", 4907.28, "cm3"),
    }
    for fact_id, (quantity, value, unit) in expected_extension_facts.items():
        fact = facts.get(fact_id)
        if not isinstance(fact, dict):
            raise InputContractError(f"f13_fact_missing:{fact_id}")
        if fact.get("quantity") != quantity or fact.get("variant") != EXTENSION_VARIANT:
            raise InputContractError(f"f13_fact_scope_mismatch:{fact_id}")
        if fact.get("candidate") != {"kind": "published_point", "value": value, "unit": unit}:
            raise InputContractError(f"f13_fact_candidate_mismatch:{fact_id}")
        if fact.get("source_refs") != [SOURCE_ID] or fact.get("design_lock") is not False:
            raise InputContractError(f"f13_fact_authority_mismatch:{fact_id}")

    if source.get("source_id") != SOURCE_ID or source.get("source_type") != "official":
        raise InputContractError("fia_source_identity_mismatch")
    if source.get("publisher") != "Federation Internationale de l'Automobile":
        raise InputContractError("fia_source_publisher_mismatch")
    if source.get("rights") != {
        "license": "fia-copyright-reference-only",
        "redistribution": "prohibited",
        "attribution": "Federation Internationale de l'Automobile",
    }:
        raise InputContractError("fia_source_rights_mismatch")
    if source.get("quality", {}).get("evidence_level") != "A":
        raise InputContractError("fia_source_evidence_level_mismatch")
    coverage_variants = source.get("coverage", {}).get("variants")
    if coverage_variants != ["917_type_912_4_494", "917_type_912_4_907_extension_1_1E"]:
        raise InputContractError("fia_source_variant_coverage_mismatch")
    notes = source.get("notes")
    for token in (EXPECTED_PDF_SHA256, "page PDF 8", "page PDF 14", "4 907,28 cm3"):
        if not isinstance(notes, str) or token not in notes:
            raise InputContractError(f"fia_source_note_missing:{token}")
    forbidden_pdf = root / "catalog/sources/homologation_form_number_250_group_4.pdf"
    if forbidden_pdf.exists():
        raise InputContractError("proprietary_pdf_must_not_be_in_repository")
    return f13, source


def _evidence(page: int, position: int) -> dict[str, Any]:
    return {
        "source_id": SOURCE_ID,
        "pdf_page": page,
        "printed_page": str(page),
        "form_position": position,
    }


def _candidate(
    identifier: str,
    quantity: str,
    value: Any,
    unit: str,
    page: int,
    position: int,
    usage: str,
) -> dict[str, Any]:
    return {
        "id": identifier,
        "quantity": quantity,
        "candidate": {"kind": "published_point", "value": value, "unit": unit},
        "source_evidence": _evidence(page, position),
        "direct_variant": BASE_VARIANT,
        "usage": usage,
        "design_lock": False,
        "declared_tolerance_ref": None,
    }


def build_document(root: Path) -> dict[str, Any]:
    validate_upstream(root)
    topology = [
        _candidate("F20-CAMSHAFT-COUNT", "camshaft_count", 4, "count", 9, 170, "topology_candidate_only"),
        _candidate("F20-CAMSHAFT-ARRANGEMENT", "camshaft_arrangement", "ohc", "categorical", 9, 171, "topology_candidate_only"),
        _candidate("F20-CAMSHAFT-DRIVE", "camshaft_drive", "gears", "categorical", 9, 172, "topology_candidate_only"),
        _candidate("F20-VALVE-ACTUATION", "valve_actuation", "bucket_tappets", "categorical", 9, 173, "topology_candidate_only"),
    ]
    cad = [
        _candidate("F20-INTAKE-VALVE-OUTER-DIAMETER", "intake_valve_outer_diameter", 47.5, "mm", 9, 181, "cad_dimension_candidate_only"),
        _candidate("F20-EXHAUST-VALVE-OUTER-DIAMETER", "exhaust_valve_outer_diameter", 40.5, "mm", 9, 196, "cad_dimension_candidate_only"),
        _candidate("F20-INTAKE-PORT-DIAMETER", "intake_port_diameter", 41.0, "mm", 10, 225, "cad_and_cfd_geometry_candidate_only"),
    ]
    cad[-1]["declared_tolerance_ref"] = "F20-TOL-INTAKE-PORT-DIAMETER"
    boundary_conditions = [
        _candidate("F20-INTAKE-VALVE-MAX-LIFT", "intake_valve_max_lift", 12.1, "mm", 9, 182, "boundary_condition_candidate_only"),
        _candidate("F20-EXHAUST-VALVE-MAX-LIFT", "exhaust_valve_max_lift", 10.5, "mm", 9, 197, "boundary_condition_candidate_only"),
        _candidate("F20-INTAKE-COLD-CLEARANCE", "intake_valve_cold_clearance", 0.1, "mm", 9, 186, "mechanical_setup_candidate_only"),
        _candidate("F20-EXHAUST-COLD-CLEARANCE", "exhaust_valve_cold_clearance", 0.1, "mm", 9, 201, "mechanical_setup_candidate_only"),
        _candidate("F20-INTAKE-OPENS-BTDC", "intake_valve_opening", 104.0, "deg_crank_btdc", 9, 187, "boundary_condition_candidate_only"),
        _candidate("F20-INTAKE-CLOSES-ABDC", "intake_valve_closing", 104.0, "deg_crank_abdc", 9, 188, "boundary_condition_candidate_only"),
        _candidate("F20-EXHAUST-OPENS-BBDC", "exhaust_valve_opening", 105.0, "deg_crank_bbdc", 9, 202, "boundary_condition_candidate_only"),
        _candidate("F20-EXHAUST-CLOSES-ATDC", "exhaust_valve_closing", 75.0, "deg_crank_atdc", 9, 203, "boundary_condition_candidate_only"),
    ]
    fact_refs = [item["id"] for item in topology + cad + boundary_conditions]
    return {
        "$comment": "F20 enregistre des faits FIA lisibles et leurs pages. Ces points ne sont ni une loi de levee, ni une CAO, ni une condition limite liberee, ni une tolerance de fabrication.",
        "schema_version": "1.0.0",
        "phase": "F20",
        "status": "fia_source_facts_registered_all_solver_and_release_gates_blocked",
        "asset_id": "porsche-917-valvetrain-flow-inputs-f20",
        "parent_asset_id": "porsche-917-classical-solver-cases-f13",
        "source_contract": {
            "source_id": SOURCE_ID,
            "catalog_path": str(SOURCE_RELATIVE_PATH),
            "f13_registry_path": str(F13_RELATIVE_PATH),
            "f13_registry_sha256": EXPECTED_F13_SHA256,
            "catalog_record_sha256": EXPECTED_SOURCE_SHA256,
            "pdf": {
                "title": "FIA Porsche 917 homologation form number 250 group 4",
                "sha256": EXPECTED_PDF_SHA256,
                "bytes": EXPECTED_PDF_BYTES,
                "page_count": EXPECTED_PDF_PAGES,
                "redistribution": "prohibited",
                "repository_copy_allowed": False,
                "reviewed_pdf_pages": [8, 9, 10, 14],
                "review_method": "manual_visual_review_of_rendered_scanned_pages",
                "ocr_used_as_authority": False,
            },
        },
        "branch_bindings": [
            {
                "variant_id": BASE_VARIANT,
                "homologation_branch": "917_type_912_4_494",
                "identity_anchor": {
                    "displacement_cm3": 4494.2,
                    "bore_mm": 85.0,
                    "stroke_mm": 66.0,
                    "source_evidence": {
                        "source_id": SOURCE_ID,
                        "pdf_page": 8,
                        "printed_page": "8",
                        "form_positions": [133, 134, 136],
                    },
                },
                "binding_mode": "direct_base_homologation_form",
                "direct_fact_refs": fact_refs,
                "candidate_inherited_fact_refs": [],
                "adoption_as_cad_authorized": False,
                "adoption_as_boundary_conditions_authorized": False,
            },
            {
                "variant_id": EXTENSION_VARIANT,
                "homologation_branch": "917_type_912_4_907_extension_1_1E",
                "identity_anchor": {
                    "displacement_cm3": 4907.28,
                    "bore_mm": 86.0,
                    "stroke_mm": 70.4,
                    "source_evidence": {
                        "source_id": SOURCE_ID,
                        "pdf_page": 14,
                        "printed_page": "extension_1_1E_sheet_1",
                        "form_positions": [133, 134, 136],
                    },
                    "f13_fact_refs": [
                        "FACT-4907-BORE",
                        "FACT-4907-STROKE",
                        "FACT-4907-DISPLACEMENT",
                    ],
                },
                "binding_mode": "candidate_inheritance_from_base_form_not_repeated_by_extension_1_1E",
                "extension_changed_form_positions": [25, 133, 134, 135, 136, 147],
                "direct_fact_refs": [],
                "candidate_inherited_fact_refs": fact_refs,
                "inheritance_requires_measurement_confirmation": True,
                "adoption_as_cad_authorized": False,
                "adoption_as_boundary_conditions_authorized": False,
            },
        ],
        "topology_candidates": topology,
        "cad_dimension_candidates": cad,
        "boundary_condition_candidates": boundary_conditions,
        "declared_tolerances": [
            {
                "id": "F20-TOL-INTAKE-PORT-DIAMETER",
                "applies_to": "F20-INTAKE-PORT-DIAMETER",
                "kind": "published_plus_minus",
                "plus_minus": {"value": 0.8, "unit": "mm"},
                "source_evidence": _evidence(10, 225),
                "semantics": "homologation_declared_tolerance_not_manufacturing_tolerance",
                "manufacturing_tolerance": False,
                "design_lock": False,
            }
        ],
        "unresolved_required_inputs": [
            {
                "id": "F20-MISSING-INJECTION-PRESSURE",
                "quantity": "fuel_injection_pressure",
                "value": None,
                "unit": None,
                "status": "not_published_on_reviewed_fia_engine_page",
                "reviewed_evidence": {"source_id": SOURCE_ID, "pdf_page": 10, "form_positions": [220, 221, 222, 223, 224, 225]},
                "default_forbidden": True,
                "blocks": ["fuel_injection_model", "combustion", "physicsnemo"],
            },
            {
                "id": "F20-MISSING-OIL-PRESSURE",
                "quantity": "engine_oil_pressure",
                "value": None,
                "unit": None,
                "status": "not_published_on_reviewed_fia_engine_page",
                "reviewed_evidence": {"source_id": SOURCE_ID, "pdf_page": 8, "form_positions": [151, 152, 153]},
                "default_forbidden": True,
                "blocks": ["lubrication_model", "bearing_load_case", "physicsnemo"],
            },
            {
                "id": "F20-MISSING-CAM-LOBE-PROFILE",
                "quantity": "cam_lobe_profile_or_lift_curve",
                "value": None,
                "unit": None,
                "status": "not_published_as_profile_only_max_lift_and_events_are_readable",
                "reviewed_evidence": {"source_id": SOURCE_ID, "pdf_page": 9, "form_positions": [170, 171, 172, 173, 182, 187, 188, 197, 202, 203]},
                "default_forbidden": True,
                "blocks": ["valvetrain_dynamics", "transient_cfd", "combustion", "physicsnemo"],
            },
            {
                "id": "F20-MISSING-VALVE-SEAT-AND-PORT-INTERNAL-GEOMETRY",
                "quantity": "valve_seat_throat_and_internal_port_geometry",
                "value": None,
                "unit": None,
                "status": "not_published_only_outer_valve_and_intake_port_diameters_are_readable",
                "reviewed_evidence": {"source_id": SOURCE_ID, "pdf_pages": [9, 10], "form_positions": [181, 196, 225]},
                "default_forbidden": True,
                "blocks": ["cad", "cfd", "print", "physicsnemo"],
            },
        ],
        "upstream_reconciliation": [
            {
                "id": "F20-RECONCILE-F13-TOLERANCE-SUMMARY",
                "upstream_registry": str(F13_RELATIVE_PATH),
                "upstream_statement": "aucune tolerance ni autorite de fabrication",
                "observed_fia_fact": "intake_port_diameter_41_plus_minus_0_8_mm",
                "source_evidence": _evidence(10, 225),
                "resolution": "record_only_as_homologation_declared_tolerance_not_manufacturing_tolerance",
                "upstream_edit_required_in_this_phase": False,
                "blocks_release": True,
            }
        ],
        "separation_policy": {
            "topology_candidates_are_not_geometry": True,
            "cad_dimension_candidates_are_not_released_cad": True,
            "boundary_condition_candidates_are_not_solver_inputs": True,
            "declared_homologation_tolerance_is_not_manufacturing_tolerance": True,
            "unknown_pressures_remain_null_without_defaults": True,
            "extension_inheritance_is_not_direct_variant_measurement": True,
        },
        "authority_boundary": {
            "source_fact_registration_only": True,
            "external_pdf_redistribution_authorized": False,
            "cad_dimension_release_authorized": False,
            "boundary_condition_release_authorized": False,
            "solver_execution_authorized": False,
            "engine_start_authorized": False,
            "manufacturing_authorized": False,
            "metal_print_authorized": False,
            "physicsnemo_training_authorized": False,
        },
        "release_gates": {key: False for key in REQUIRED_FALSE_GATES},
    }


def verify_external_pdf(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return ["external_pdf_missing"]
    if path.stat().st_size != EXPECTED_PDF_BYTES:
        errors.append("external_pdf_size_mismatch")
    if sha256(path) != EXPECTED_PDF_SHA256:
        errors.append("external_pdf_sha256_mismatch")
    try:
        completed = subprocess.run(
            ["pdfinfo", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        errors.append("pdfinfo_unavailable_or_failed")
    else:
        match = re.search(r"^Pages:\s+(\d+)\s*$", completed.stdout, re.MULTILINE)
        if match is None or int(match.group(1)) != EXPECTED_PDF_PAGES:
            errors.append("external_pdf_page_count_mismatch")
    return errors


def _diff(expected: Any, actual: Any, path: str = "$") -> list[str]:
    if type(expected) is not type(actual):
        return [f"type_mismatch:{path}"]
    if isinstance(expected, dict):
        errors: list[str] = []
        if set(expected) != set(actual):
            errors.append(f"keys_mismatch:{path}")
        for key in sorted(set(expected) & set(actual)):
            errors.extend(_diff(expected[key], actual[key], f"{path}/{key}"))
        return errors
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return [f"length_mismatch:{path}"]
        errors: list[str] = []
        for index, (left, right) in enumerate(zip(expected, actual)):
            errors.extend(_diff(left, right, f"{path}/{index}"))
        return errors
    return [] if expected == actual else [f"value_mismatch:{path}"]


def evaluate(root: Path, output_path: Path, source_pdf: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    try:
        expected = build_document(root)
    except (OSError, json.JSONDecodeError, InputContractError) as exc:
        return {
            "report_status": "failed",
            "errors": [f"upstream_contract_error:{exc}"],
            "external_pdf_verified": False,
        }
    try:
        actual = load_json(output_path)
    except (OSError, json.JSONDecodeError, InputContractError) as exc:
        errors.append(f"output_invalid:{exc}")
        actual = {}
    errors.extend(_diff(expected, actual))
    external_pdf_verified = False
    if source_pdf is not None:
        pdf_errors = verify_external_pdf(source_pdf)
        errors.extend(pdf_errors)
        external_pdf_verified = not pdf_errors
    return {
        "report_status": "passed" if not errors else "failed",
        "errors": errors,
        "external_pdf_verified": external_pdf_verified,
        "fact_count": sum(
            len(expected[key])
            for key in ("topology_candidates", "cad_dimension_candidates", "boundary_condition_candidates")
        ),
        "branch_count": len(expected["branch_bindings"]),
        "declared_tolerance_count": len(expected["declared_tolerances"]),
        "unresolved_input_count": len(expected["unresolved_required_inputs"]),
        "all_release_gates_blocked": all(value is False for value in expected["release_gates"].values()),
    }


def main() -> int:
    default_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--output", type=Path, default=default_root / OUTPUT_RELATIVE_PATH)
    parser.add_argument("--source-pdf", type=Path)
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args()

    if args.generate:
        if args.source_pdf is None:
            print(json.dumps({"report_status": "failed", "errors": ["generate_requires_external_source_pdf"]}, indent=2))
            return 2
        pdf_errors = verify_external_pdf(args.source_pdf)
        if pdf_errors:
            print(json.dumps({"report_status": "failed", "errors": pdf_errors}, indent=2))
            return 2
        try:
            document = build_document(args.root)
        except (OSError, json.JSONDecodeError, InputContractError) as exc:
            print(json.dumps({"report_status": "failed", "errors": [f"upstream_contract_error:{exc}"]}, indent=2))
            return 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = evaluate(args.root, args.output, args.source_pdf)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["report_status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
