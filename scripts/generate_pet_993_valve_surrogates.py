#!/usr/bin/env python3
"""Generate fail-closed F1 dimensional surrogates for PET-linked 993 valves.

The source pages provide only a few overall dimensions and candidate material
families.  The generated SCAD and OpenUSD guides therefore use an explicitly
simplified head/frustum/stem profile.  They are editable visual and arithmetic
surrogates, not seat, guide, keeper, thermal, fatigue or manufacturing geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "twins"
    / "reference-935-cylinder-head"
    / "source"
    / "valve_variants_f1.json"
)
INTAKE_PART = ROOT / "catalog" / "parts" / "993-eng-intake-valve-f1-0001.json"
EXHAUST_PART = ROOT / "catalog" / "parts" / "993-eng-exhaust-valve-f1-0001.json"
INTAKE_SOURCE = ROOT / "catalog" / "sources" / "src-fvd-993-inlet-valve-dimensions.json"
EXHAUST_SOURCE = (
    ROOT / "catalog" / "sources" / "src-partworks-993-exhaust-valve-dimensions.json"
)
CROSSWALK = ROOT / "twins" / "pet-993" / "catalog-crosswalk-f0.json"
REPORT = ROOT / "twins" / "catalogue-parts" / "valve-dimensional-surrogates-f1.json"
SCAD_OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering"
    / "993-valve-dimensional-surrogates-f1.scad"
)
USD_OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering"
    / "993-valve-dimensional-surrogates-f1.usda"
)

EXPECTED_VARIANTS = {
    "993-intake-49-f1": {
        "part_id": "993-ENG-INTAKE-VALVE-F1-0001",
        "service": "intake",
        "head_diameter_mm": 49.0,
        "stem_diameter_mm": 8.0,
        "overall_length_mm": 109.0,
        "length_status": "hypothesis_from_110_mm_product_envelope",
        "declared_reference_mass_g": 120.0,
        "source_id": "SRC-FVD-993-INLET-VALVE-DIMENSIONS",
        "oem_references": ["99310540902"],
        "dimensional_basis": "partial_supplier_declaration_plus_length_hypothesis",
    },
    "993-carrera-exhaust-42_5-f1": {
        "part_id": "993-ENG-EXHAUST-VALVE-F1-0001",
        "service": "exhaust",
        "head_diameter_mm": 42.5,
        "stem_diameter_mm": 8.0,
        "overall_length_mm": 109.0,
        "length_status": "supplier_declared",
        "declared_reference_mass_g": None,
        "source_id": "SRC-PARTWORKS-993-EXHAUST-VALVE-DIMENSIONS",
        "oem_references": ["99310541901"],
        "dimensional_basis": "three_supplier_declared_overall_dimensions",
    },
    "993-turbo-exhaust-43_5-f1": {
        "part_id": "993-ENG-EXHAUST-VALVE-F1-0001",
        "service": "exhaust",
        "head_diameter_mm": 43.5,
        "stem_diameter_mm": 8.0,
        "overall_length_mm": 108.9,
        "length_status": "supplier_declared",
        "declared_reference_mass_g": None,
        "source_id": "SRC-PARTWORKS-993-EXHAUST-VALVE-DIMENSIONS",
        "oem_references": ["99310541984", "99310541952", "99310541953"],
        "dimensional_basis": "three_supplier_declared_overall_dimensions",
    },
}


class ContractError(ValueError):
    """Raised when the surrogate would lose provenance or overclaim maturity."""


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load:{relative(path)}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_object:{relative(path)}")
    return value


def proxy_volume_mm3(variant: dict[str, Any], defaults: dict[str, Any]) -> float:
    head_r = float(variant["head_diameter_mm"]) / 2.0
    stem_r = float(variant["stem_diameter_mm"]) / 2.0
    face_h = float(defaults["face_thickness_mm"])
    neck_h = float(defaults["neck_length_mm"])
    stem_h = float(variant["overall_length_mm"]) - face_h
    if min(head_r, stem_r, face_h, neck_h, stem_h) <= 0.0 or neck_h > stem_h:
        raise ContractError(f"invalid_proxy_dimensions:{variant.get('id')}")
    head = math.pi * head_r**2 * face_h
    neck = math.pi * neck_h * (head_r**2 + head_r * stem_r + stem_r**2) / 3.0
    stem = math.pi * stem_r**2 * (stem_h - neck_h)
    return head + neck + stem


def pet_links(crosswalk: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for entry in crosswalk.get("parts", []):
        if not isinstance(entry, dict):
            raise ContractError("crosswalk_part")
        part_id = entry.get("part_id")
        if part_id not in {
            "993-ENG-INTAKE-VALVE-F1-0001",
            "993-ENG-EXHAUST-VALVE-F1-0001",
        }:
            continue
        by_reference: dict[str, set[str]] = {}
        for match in entry.get("pet_occurrence_matches", []):
            if not isinstance(match, dict):
                raise ContractError("crosswalk_match")
            reference = match.get("oem_reference")
            master_id = match.get("part_master_twin_id")
            if isinstance(reference, str) and isinstance(master_id, str):
                by_reference.setdefault(reference.replace(" ", ""), set()).add(master_id)
        result[str(part_id)] = {
            "by_reference": by_reference,
            "unmatched_oem_references": sorted(
                str(value).replace(" ", "")
                for value in entry.get("unmatched_oem_references", [])
            ),
        }
    if set(result) != {
        "993-ENG-INTAKE-VALVE-F1-0001",
        "993-ENG-EXHAUST-VALVE-F1-0001",
    }:
        raise ContractError("valve_crosswalk_coverage")
    return result


def derive() -> dict[str, Any]:
    config = load_json(CONFIG)
    defaults = config.get("geometry_defaults", {})
    if defaults != {
        "face_thickness_mm": 2.5,
        "neck_length_mm": 8.0,
        "seat_angle_deg": 45.0,
        "keeper_geometry": "omitted_pending_measurement",
    }:
        raise ContractError("geometry_defaults")
    materials = config.get("materials", {})
    expected_densities = {
        "ti64_grade5_lpbf": 4.43,
        "inconel_751_bar": 8.22,
        "steel_reference": 7.8,
    }
    if {
        key: value.get("density_g_cm3")
        for key, value in materials.items()
        if isinstance(value, dict)
    } != expected_densities:
        raise ContractError("material_density_hypotheses")

    variant_inputs = config.get("variants", [])
    if not isinstance(variant_inputs, list) or len(variant_inputs) != 3:
        raise ContractError("variant_count")
    links = pet_links(load_json(CROSSWALK))
    derived_variants: list[dict[str, Any]] = []
    for variant in variant_inputs:
        if not isinstance(variant, dict) or variant.get("id") not in EXPECTED_VARIANTS:
            raise ContractError("variant_identity")
        expected = EXPECTED_VARIANTS[str(variant["id"])]
        for field in (
            "service",
            "head_diameter_mm",
            "stem_diameter_mm",
            "overall_length_mm",
            "length_status",
            "declared_reference_mass_g",
            "source_id",
        ):
            if variant.get(field) != expected[field]:
                raise ContractError(f"variant_value:{variant['id']}:{field}")
        volume = proxy_volume_mm3(variant, defaults)
        part_id = str(expected["part_id"])
        master_ids = sorted(
            {
                master_id
                for reference in expected["oem_references"]
                for master_id in links[part_id]["by_reference"].get(reference, set())
            }
        )
        linked_references = sorted(
            reference
            for reference in expected["oem_references"]
            if reference in links[part_id]["by_reference"]
        )
        mass_comparisons = []
        for material_id in variant.get("material_variants", []):
            material = materials.get(material_id)
            if not isinstance(material, dict):
                raise ContractError(f"unknown_material:{variant['id']}:{material_id}")
            mass_comparisons.append(
                {
                    "material_id": material_id,
                    "density_g_cm3": material["density_g_cm3"],
                    "proxy_mass_g": round(
                        volume / 1000.0 * float(material["density_g_cm3"]), 9
                    ),
                    "role": material.get("role"),
                    "qualification_status": "candidate_or_placeholder_not_part_qualified",
                }
            )
        declared_mass = variant.get("declared_reference_mass_g")
        mass_consistency = None
        if isinstance(declared_mass, (int, float)):
            steel_mass = next(
                item["proxy_mass_g"]
                for item in mass_comparisons
                if item["material_id"] == "steel_reference"
            )
            mass_consistency = {
                "declared_reference_mass_g": float(declared_mass),
                "equivalent_density_g_cm3": round(float(declared_mass) / (volume / 1000.0), 9),
                "generic_steel_proxy_mass_g": steel_mass,
                "generic_steel_residual_g": round(steel_mass - float(declared_mass), 9),
                "generic_steel_relative_residual": round(
                    (steel_mass - float(declared_mass)) / float(declared_mass), 9
                ),
                "interpretation": "arithmetic_consistency_only_not_material_identification",
            }
        derived_variants.append(
            {
                "variant_id": variant["id"],
                "part_id": part_id,
                "service": variant["service"],
                "source_id": variant["source_id"],
                "dimensional_basis": expected["dimensional_basis"],
                "oem_references": expected["oem_references"],
                "linked_pet_oem_references": linked_references,
                "unmatched_pet_oem_references": sorted(
                    set(expected["oem_references"]) - set(linked_references)
                ),
                "pet_part_master_twin_ids": master_ids,
                "dimensions_mm": {
                    "head_diameter": float(variant["head_diameter_mm"]),
                    "stem_diameter": float(variant["stem_diameter_mm"]),
                    "overall_length": float(variant["overall_length_mm"]),
                    "overall_length_status": variant["length_status"],
                },
                "proxy_volume_mm3": round(volume, 9),
                "mass_comparisons": mass_comparisons,
                "declared_mass_consistency": mass_consistency,
            }
        )
    derived_variants.sort(key=lambda item: item["variant_id"])
    return {"defaults": defaults, "variants": derived_variants}


def render_scad(data: dict[str, Any]) -> str:
    defaults = data["defaults"]
    lines = [
        "// Generated PET-linked valve dimensional surrogates; not OEM geometry.",
        "// Seat, guide clearance, keeper, neck, tolerances and hot geometry are unresolved.",
        "$fn = 96;",
        f"face_thickness_mm = {defaults['face_thickness_mm']:.6f}; // hypothesis",
        f"neck_length_mm = {defaults['neck_length_mm']:.6f}; // hypothesis",
        "",
        "module valve_surrogate(head_d_mm, stem_d_mm, overall_length_mm) {",
        "    union() {",
        "        cylinder(h = face_thickness_mm, d = head_d_mm);",
        "        translate([0, 0, face_thickness_mm])",
        "            cylinder(h = neck_length_mm, d1 = head_d_mm, d2 = stem_d_mm);",
        "        translate([0, 0, face_thickness_mm])",
        "            cylinder(h = overall_length_mm - face_thickness_mm, d = stem_d_mm);",
        "    }",
        "}",
        "",
    ]
    offsets = (-60.0, 0.0, 60.0)
    for offset, variant in zip(offsets, data["variants"], strict=True):
        dims = variant["dimensions_mm"]
        lines.extend(
            [
                f"// {variant['variant_id']} — {variant['dimensional_basis']}",
                f"translate([{offset:.6f}, 0, 0])",
                "    valve_surrogate("
                f"{dims['head_diameter']:.6f}, {dims['stem_diameter']:.6f}, "
                f"{dims['overall_length']:.6f});",
                "",
            ]
        )
    return "\n".join(lines)


def render_usd_guide(variant: dict[str, Any], x_offset: float) -> str:
    dims = variant["dimensions_mm"]
    face_h = 2.5
    neck_h = 8.0
    stem_h = dims["overall_length"] - face_h
    name = "Valve" + "".join(
        part.capitalize()
        for part in variant["variant_id"].replace("_", "-").split("-")
    )
    references = ",".join(variant["oem_references"])
    masters = ",".join(variant["pet_part_master_twin_ids"])
    return f'''    def Xform "{name}" (
        kind = "component"
    )
    {{
        custom string fidelity = "F1_dimensional_surrogate_unvalidated"
        custom string dimensionalBasis = "{variant['dimensional_basis']}"
        custom string oemReferences = "{references}"
        custom string petPartMasterTwinIds = "{masters}"
        custom bool interfaceGeometryPresent = false
        custom bool analysisGeometryAvailable = false
        custom bool selectedMaterialPresent = false
        custom bool simReadyValidated = false
        double3 xformOp:translate = ({x_offset:.6f}, 0, 0)
        uniform token[] xformOpOrder = ["xformOp:translate"]

        def Cylinder "HeadGuide"
        {{
            uniform token axis = "Z"
            double height = {face_h:.6f}
            double radius = {dims['head_diameter'] / 2.0:.6f}
            uniform token purpose = "guide"
            double3 xformOp:translate = (0, 0, {face_h / 2.0:.6f})
            uniform token[] xformOpOrder = ["xformOp:translate"]
        }}
        def Cone "NeckGuide"
        {{
            uniform token axis = "Z"
            double height = {neck_h:.6f}
            double radius0 = {dims['head_diameter'] / 2.0:.6f}
            double radius1 = {dims['stem_diameter'] / 2.0:.6f}
            uniform token purpose = "guide"
            double3 xformOp:translate = (0, 0, {face_h + neck_h / 2.0:.6f})
            uniform token[] xformOpOrder = ["xformOp:translate"]
        }}
        def Cylinder "StemGuide"
        {{
            uniform token axis = "Z"
            double height = {stem_h:.6f}
            double radius = {dims['stem_diameter'] / 2.0:.6f}
            uniform token purpose = "guide"
            double3 xformOp:translate = (0, 0, {face_h + stem_h / 2.0:.6f})
            uniform token[] xformOpOrder = ["xformOp:translate"]
        }}
    }}'''


def render_usd(data: dict[str, Any]) -> str:
    guides = [
        render_usd_guide(variant, offset)
        for offset, variant in zip((-60.0, 0.0, 60.0), data["variants"], strict=True)
    ]
    return '''#usda 1.0
(
    defaultPrim = "ValveDimensionalSurrogatesF1"
    metersPerUnit = 0.001
    upAxis = "Z"
)

def Xform "ValveDimensionalSurrogatesF1" (
    kind = "assembly"
)
{
    custom string status = "F1_dimensional_surrogates_not_F2_or_analysis_geometry"
    custom bool physicsAssigned = false
    custom bool materialAssigned = false
    custom bool simReadyValidated = false
''' + "\n\n".join(guides) + '''
}
'''


def build_report(data: dict[str, Any], scad_text: str, usd_text: str) -> dict[str, Any]:
    variants = data["variants"]
    masters = sorted(
        {
            master_id
            for variant in variants
            for master_id in variant["pet_part_master_twin_ids"]
        }
    )
    linked_refs = sorted(
        {
            reference
            for variant in variants
            for reference in variant["linked_pet_oem_references"]
        }
    )
    unmatched_refs = sorted(
        {
            reference
            for variant in variants
            for reference in variant["unmatched_pet_oem_references"]
        }
    )
    return {
        "$comment": (
            "Surrogates F1 des soupapes 993 lies au PET. Les dimensions partielles "
            "et les hypotheses de profil ne constituent pas des interfaces ou une CAO moteur."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "status": "F1_valve_dimensional_surrogates_complete_no_component_CAE_credit",
        "source_boundary": {
            "files": [
                {"path": relative(CONFIG), "sha256": sha256_file(CONFIG), "role": "proxy_geometry_hypotheses_and_material_candidates"},
                {"path": relative(INTAKE_PART), "sha256": sha256_file(INTAKE_PART), "role": "intake_part_identity_and_claim_boundary"},
                {"path": relative(EXHAUST_PART), "sha256": sha256_file(EXHAUST_PART), "role": "exhaust_part_identity_and_claim_boundary"},
                {"path": relative(INTAKE_SOURCE), "sha256": sha256_file(INTAKE_SOURCE), "role": "supplier_declared_intake_dimensions_and_mass"},
                {"path": relative(EXHAUST_SOURCE), "sha256": sha256_file(EXHAUST_SOURCE), "role": "supplier_declared_exhaust_dimensions"},
                {"path": relative(CROSSWALK), "sha256": sha256_file(CROSSWALK), "role": "exact_OEM_identity_to_PET_master_links"},
            ],
            "third_party_geometry_redistributed": False,
            "llm_generated_dimensions_used": False,
            "independent_metrology_used": False,
        },
        "summary": {
            "dimensional_surrogate_variants": len(variants),
            "full_supplier_dimension_sets": sum(
                variant["dimensional_basis"] == "three_supplier_declared_overall_dimensions"
                for variant in variants
            ),
            "partial_dimension_sets_with_length_hypothesis": sum(
                "length_hypothesis" in variant["dimensional_basis"] for variant in variants
            ),
            "oem_references_in_scope": sum(len(variant["oem_references"]) for variant in variants),
            "pet_linked_oem_references": len(linked_refs),
            "pet_unmatched_oem_references": len(unmatched_refs),
            "pet_linked_part_masters": len(masters),
            "declared_mass_consistency_checks": sum(
                variant["declared_mass_consistency"] is not None for variant in variants
            ),
            "selected_interface_geometry": 0,
            "qualified_material_decisions": 0,
            "reference_solver_results": 0,
            "physicsnemo_results": 0,
            "simready_assets": 0,
            "manufacturing_releases": 0,
        },
        "geometry_model": {
            "model": "head_cylinder_plus_hypothetical_neck_frustum_plus_stem_cylinder",
            "hypotheses": {
                "face_thickness_mm": data["defaults"]["face_thickness_mm"],
                "neck_length_mm": data["defaults"]["neck_length_mm"],
                "seat_angle_deg_not_used_as_interface": data["defaults"]["seat_angle_deg"],
            },
            "unknowns": [
                "seat_angle_width_margin_and_contact_surface",
                "guide_clearance_and_hot_stem_diameter",
                "keeper_groove_tip_and_retainer_interfaces",
                "neck_fillet_underhead_profile_and_hollow_or_sodium_filled_construction",
                "tolerances_surface_finish_coatings_and_heat_treatment",
            ],
        },
        "variants": variants,
        "interface_readiness": {
            "interface_hypotheses": [
                "stem_to_guide",
                "head_to_seat",
                "tip_and_keeper_to_retainer_train",
            ],
            "selected_interface_coordinate_count": 0,
            "F2_interface_geometry": False,
        },
        "simulation_readiness": {
            "blocked_load_case_ids": [
                "LC-993-VALVE-THERMAL-STEADY",
                "LC-993-VALVE-DYNAMIC-CYCLE",
                "LC-993-CAMSHAFT-VALVETRAIN",
            ],
            "reference_solver": "not_run_missing_F2_interfaces_hot_properties_and_boundaries",
            "physicsnemo": "ineligible_without_converged_reference_solver_dataset",
        },
        "assets": {
            "editable_scad": relative(SCAD_OUTPUT),
            "editable_scad_sha256": sha256_bytes(scad_text.encode("utf-8")),
            "openusd_guide": relative(USD_OUTPUT),
            "openusd_guide_sha256": sha256_bytes(usd_text.encode("utf-8")),
            "openusd_variant_prim_count": len(variants),
            "openusd_guide_primitive_count": len(variants) * 3,
            "openusd_physics_schema_count": 0,
            "openusd_material_binding_count": 0,
        },
        "model_roles": {
            "llm": "source_routing_hypothesis_and_audit_only_no_dimensions_generated",
            "reference_solver": "not_run",
            "physicsnemo": "not_run",
            "omniverse": "OpenUSD_guides_authored_not_SimReady",
        },
        "claim_boundary": {
            "is_complete_OEM_geometry": False,
            "is_F2_interface_geometry": False,
            "is_analysis_geometry": False,
            "is_dimensionally_accurate": False,
            "is_fitment_validated": False,
            "is_qualified_material_selection": False,
            "is_reference_CAE_result": False,
            "is_physicsnemo_result": False,
            "is_simready_validated": False,
            "is_manufacturing_release": False,
        },
        "next_gate": (
            "source_or_reconstruct_seat_guide_keeper_and_hot_clearance_interfaces_with_"
            "explicit_uncertainty_before_any_thermal_or_dynamic_reference_case"
        ),
    }


def validate(data: dict[str, Any], scad_text: str, usd_text: str, report: dict[str, Any]) -> None:
    if report.get("status") != "F1_valve_dimensional_surrogates_complete_no_component_CAE_credit":
        raise ContractError("status")
    summary = report.get("summary", {})
    expected = {
        "dimensional_surrogate_variants": 3,
        "full_supplier_dimension_sets": 2,
        "partial_dimension_sets_with_length_hypothesis": 1,
        "oem_references_in_scope": 5,
        "pet_linked_oem_references": 3,
        "pet_unmatched_oem_references": 2,
        "pet_linked_part_masters": 3,
        "declared_mass_consistency_checks": 1,
        "selected_interface_geometry": 0,
        "qualified_material_decisions": 0,
        "reference_solver_results": 0,
        "physicsnemo_results": 0,
        "simready_assets": 0,
        "manufacturing_releases": 0,
    }
    if any(summary.get(field) != value for field, value in expected.items()):
        raise ContractError("summary")
    if len(data.get("variants", [])) != 3 or usd_text.count('kind = "component"') != 3:
        raise ContractError("variant_prims")
    if usd_text.count('purpose = "guide"') != 9:
        raise ContractError("guide_primitives")
    for prohibited in ("UsdPhysics", "RigidBodyAPI", "CollisionAPI", "MassAPI", "MaterialBindingAPI"):
        if prohibited in usd_text:
            raise ContractError(f"usd_overclaim:{prohibited}")
    assets = report.get("assets", {})
    if assets.get("editable_scad_sha256") != sha256_bytes(scad_text.encode("utf-8")):
        raise ContractError("scad_digest")
    if assets.get("openusd_guide_sha256") != sha256_bytes(usd_text.encode("utf-8")):
        raise ContractError("usd_digest")
    if any(value is not False for value in report.get("claim_boundary", {}).values()):
        raise ContractError("claim_boundary")
    for variant in report.get("variants", []):
        if not variant.get("pet_part_master_twin_ids"):
            raise ContractError(f"unlinked_variant:{variant.get('variant_id')}")
        if any(
            item.get("qualification_status") != "candidate_or_placeholder_not_part_qualified"
            for item in variant.get("mass_comparisons", [])
        ):
            raise ContractError(f"material_overclaim:{variant.get('variant_id')}")


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    args = parser.parse_args(argv)
    try:
        data = derive()
        scad_text = render_scad(data)
        usd_text = render_usd(data)
        report = build_report(data, scad_text, usd_text)
        validate(data, scad_text, usd_text, report)
        expected = {
            REPORT: render_json(report),
            SCAD_OUTPUT: scad_text,
            USD_OUTPUT: usd_text,
        }
        if args.write:
            for path, content in expected.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                print(f"wrote {relative(path)}")
            return 0
        for path in expected:
            if not path.is_file():
                print(f"missing:{relative(path)}")
                return 1
        if args.check:
            for path, content in expected.items():
                if path.read_text(encoding="utf-8") != content:
                    print(f"stale:{relative(path)}")
                    return 1
        checked_report = load_json(REPORT)
        checked_scad = SCAD_OUTPUT.read_text(encoding="utf-8")
        checked_usd = USD_OUTPUT.read_text(encoding="utf-8")
        validate(data, checked_scad, checked_usd, checked_report)
        if checked_report.get("source_boundary", {}).get("files") != report.get("source_boundary", {}).get("files"):
            raise ContractError("source_digests")
        print(f"valid {relative(REPORT)}")
        print(f"valid {relative(SCAD_OUTPUT)} and {relative(USD_OUTPUT)}")
        return 0
    except (ContractError, OSError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
