#!/usr/bin/env python3
"""Build a mass-constrained F1 structural surrogate for the 993 Turbo carrier.

The surrogate combines a declared bounding envelope and mass with generic steel
properties.  It is deliberately not OEM geometry or F2 interface geometry; it
exists to make analytic sensitivity studies and future inverse-design sampling
reproducible while the actual section and attachment coordinates remain unknown.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DECLARED_DATA = ROOT / "catalog" / "reference" / "993-declared-part-data.json"
MATERIAL_SCREENING = (
    ROOT / "twins" / "catalogue-parts" / "engine-carrier-material-screening-f1.json"
)
LOAD_CASE_EVIDENCE = (
    ROOT / "parts" / "993-eng-carrier-0001" / "evidence" / "load-cases.md"
)
REPORT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engine-carrier-mass-constrained-surrogate-f1.json"
)
SCAD_OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering"
    / "993-engine-carrier-mass-constrained-surrogate-f1.scad"
)
USD_OUTPUT = (
    ROOT
    / "twins"
    / "catalogue-parts"
    / "engineering"
    / "993-engine-carrier-mass-constrained-surrogate-f1.usda"
)

OEM_REFERENCE = "993 115 021 53"
POWERTRAIN_MASS_CANDIDATE_KG = 195.0
GRAVITY_M_S2 = 9.80665


class ContractError(ValueError):
    """Raised when the surrogate would overclaim or lose source closure."""


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


def declared_inputs(payload: dict[str, Any]) -> tuple[float, float, float, float]:
    matches = [
        item
        for item in payload.get("entries", [])
        if isinstance(item, dict) and item.get("oem_reference") == OEM_REFERENCE
    ]
    if len(matches) != 1:
        raise ContractError(f"declared_carrier_count:{len(matches)}")
    record = matches[0]
    dimensions = record.get("dimensions_mm")
    mass = record.get("mass_kg")
    if dimensions != [600, 50, 50] or mass != 1.96:
        raise ContractError("declared_carrier_values")
    return float(dimensions[0]), float(dimensions[1]), float(dimensions[2]), float(mass)


def generic_steel(payload: dict[str, Any]) -> tuple[float, float, float]:
    steel = payload.get("material_hypotheses", {}).get("steel", {})
    density = steel.get("density_kg_m3")
    modulus = steel.get("elastic_modulus_MPa")
    poisson = steel.get("poisson_ratio")
    if (density, modulus, poisson) != (7850.0, 210000.0, 0.3):
        raise ContractError("generic_steel_properties")
    if steel.get("qualification_status") != (
        "generic_handbook_value_not_supplier_qualified"
    ):
        raise ContractError("generic_steel_qualification")
    return float(density), float(modulus), float(poisson)


def derive() -> dict[str, float]:
    declared = load_json(DECLARED_DATA)
    screening = load_json(MATERIAL_SCREENING)
    load_text = LOAD_CASE_EVIDENCE.read_text(encoding="utf-8")
    if "environ 195 kg" not in load_text:
        raise ContractError("documentary_powertrain_mass_anchor")
    length, width, height, target_mass = declared_inputs(declared)
    if width != height:
        raise ContractError("square_outer_envelope_required")
    density, modulus, poisson = generic_steel(screening)
    target_area = target_mass / (density * length * 1e-3) * 1e6
    discriminant = width**2 - target_area
    if discriminant <= 0:
        raise ContractError("mass_cannot_fit_hollow_square_section")
    wall = (width - math.sqrt(discriminant)) / 2.0
    inner = width - 2.0 * wall
    area = width * height - inner**2
    inertia = (width * height**3 - inner**4) / 12.0
    reconstructed_mass = area * length * 1e-9 * density
    force = POWERTRAIN_MASS_CANDIDATE_KG * GRAVITY_M_S2
    c = height / 2.0
    simply_supported_moment = force * length / 4.0
    cantilever_moment = force * length
    return {
        "length_mm": length,
        "width_mm": width,
        "height_mm": height,
        "target_mass_kg": target_mass,
        "steel_density_kg_m3": density,
        "steel_elastic_modulus_MPa": modulus,
        "steel_poisson_ratio": poisson,
        "target_area_mm2": target_area,
        "equivalent_wall_mm": wall,
        "inner_square_mm": inner,
        "section_area_mm2": area,
        "fill_fraction": area / (width * height),
        "second_moment_mm4": inertia,
        "reconstructed_mass_kg": reconstructed_mass,
        "mass_error_kg": reconstructed_mass - target_mass,
        "documentary_force_upper_N": force,
        "simply_supported_stress_MPa": simply_supported_moment * c / inertia,
        "simply_supported_deflection_mm": force
        * length**3
        / (48.0 * modulus * inertia),
        "cantilever_stress_MPa": cantilever_moment * c / inertia,
        "cantilever_deflection_mm": force * length**3 / (3.0 * modulus * inertia),
    }


def render_scad(values: dict[str, float]) -> str:
    return f"""// Generated mass-constrained structural surrogate, not OEM geometry.
// No interface coordinates, tolerances, fitment or manufacturing credit.
// The uniform square tube is one mathematical witness compatible with envelope and mass.

$fn = 48;
length_mm = {values['length_mm']:.6f};
outer_mm = {values['width_mm']:.6f};
wall_mm = {values['equivalent_wall_mm']:.9f};
inner_mm = outer_mm - 2 * wall_mm;

difference() {{
    translate([-length_mm / 2, -outer_mm / 2, 0])
        cube([length_mm, outer_mm, outer_mm], center = false);
    translate([-length_mm / 2 - 1, -inner_mm / 2, wall_mm])
        cube([length_mm + 2, inner_mm, inner_mm], center = false);
}}
"""


def usd_cube(
    name: str,
    translate: tuple[float, float, float],
    scale: tuple[float, float, float],
) -> str:
    return f'''        def Xform "{name}"
        {{
            custom bool isInterfaceGeometry = false
            double3 xformOp:translate = ({translate[0]:.9f}, {translate[1]:.9f}, {translate[2]:.9f})
            double3 xformOp:scale = ({scale[0]:.9f}, {scale[1]:.9f}, {scale[2]:.9f})
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
            def Cube "Guide"
            {{
                double size = 1
                uniform token purpose = "guide"
            }}
        }}'''


def render_usd(values: dict[str, float]) -> str:
    length = values["length_mm"]
    outer = values["width_mm"]
    wall = values["equivalent_wall_mm"]
    inner = values["inner_square_mm"]
    cubes = [
        usd_cube("BottomWall", (0.0, 0.0, wall / 2.0), (length, outer, wall)),
        usd_cube(
            "TopWall", (0.0, 0.0, outer - wall / 2.0), (length, outer, wall)
        ),
        usd_cube(
            "LeftWall",
            (0.0, -outer / 2.0 + wall / 2.0, outer / 2.0),
            (length, wall, inner),
        ),
        usd_cube(
            "RightWall",
            (0.0, outer / 2.0 - wall / 2.0, outer / 2.0),
            (length, wall, inner),
        ),
    ]
    return '''#usda 1.0
(
    defaultPrim = "EngineCarrierMassConstrainedSurrogateF1"
    metersPerUnit = 0.001
    upAxis = "Z"
)

def Xform "EngineCarrierMassConstrainedSurrogateF1" (
    kind = "component"
)
{
    custom string fidelity = "F1_mass_constrained_structural_surrogate"
    custom string geometryStatus = "mathematical_witness_not_OEM_geometry"
    custom bool massConstraintMatched = true
    custom bool interfaceGeometryPresent = false
    custom bool componentCredit = false
    custom bool physicsAssigned = false
    custom bool simReadyValidated = false

    def Scope "SurrogateWalls"
    {
''' + "\n".join(cubes) + '''
    }

    def Scope "InterfaceSearchDomains"
    {
        custom string domain = "full_declared_envelope_only"
        custom bool interfacePointsSelected = false
        custom bool symmetryAssumed = false
    }
}
'''


def build_report(
    values: dict[str, float], scad_text: str, usd_text: str
) -> dict[str, Any]:
    return {
        "$comment": (
            "Surrogate F1 contraint par enveloppe et masse. La section creuse "
            "uniforme est un temoin mathematique, pas la geometrie OEM du berceau."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "status": "F1_mass_constrained_structural_surrogate_no_component_credit",
        "subject": {
            "part_id": "993-ENG-CARRIER-0001",
            "oem_reference": OEM_REFERENCE,
            "part_master_twin_id": "TWIN-PET-993-PART-F77CBF8A0C10743C3178",
            "variant": "993-turbo",
            "safety_class": "safety_critical",
        },
        "source_boundary": {
            "files": [
                {
                    "path": relative(DECLARED_DATA),
                    "sha256": sha256_file(DECLARED_DATA),
                    "role": "declared_bounding_envelope_and_mass",
                },
                {
                    "path": relative(MATERIAL_SCREENING),
                    "sha256": sha256_file(MATERIAL_SCREENING),
                    "role": "generic_unqualified_steel_properties",
                },
                {
                    "path": relative(LOAD_CASE_EVIDENCE),
                    "sha256": sha256_file(LOAD_CASE_EVIDENCE),
                    "role": "documentary_powertrain_mass_candidate",
                },
            ],
            "photogrammetry_or_scan_used": False,
            "interface_measurements_used": False,
            "llm_generated_dimensions_used": False,
        },
        "input_constraints": {
            "declared_envelope_mm": [
                values["length_mm"],
                values["width_mm"],
                values["height_mm"],
            ],
            "declared_mass_kg": values["target_mass_kg"],
            "material_family_observation": "acier",
            "generic_density_kg_m3": values["steel_density_kg_m3"],
            "generic_elastic_modulus_MPa": values[
                "steel_elastic_modulus_MPa"
            ],
            "material_properties_qualified": False,
        },
        "derived_section": {
            "model": "uniform_square_hollow_tube_using_full_declared_envelope",
            "equation": "A=m/(rho*L)=b^2-(b-2t)^2",
            "target_area_mm2": round(values["target_area_mm2"], 9),
            "equivalent_wall_mm": round(values["equivalent_wall_mm"], 9),
            "inner_square_mm": round(values["inner_square_mm"], 9),
            "fill_fraction": round(values["fill_fraction"], 9),
            "second_moment_mm4": round(values["second_moment_mm4"], 9),
            "reconstructed_mass_kg": round(values["reconstructed_mass_kg"], 12),
            "mass_error_kg": round(values["mass_error_kg"], 12),
            "mass_constraint_closed": abs(values["mass_error_kg"]) < 1e-9,
            "actual_section_known": False,
        },
        "interface_search_domains": [
            {
                "interface_id": "IF-993-EC-CARRIER-BRACKET",
                "x_mm": [-300.0, 300.0],
                "y_mm": [-25.0, 25.0],
                "z_mm": [0.0, 50.0],
                "selected_point_count": 0,
            },
            {
                "interface_id": "IF-993-EC-CARRIER-MOUNTS",
                "quantity_candidate": 2,
                "x_mm": [-300.0, 300.0],
                "y_mm": [-25.0, 25.0],
                "z_mm": [0.0, 50.0],
                "symmetry_assumed": False,
                "selected_point_count": 0,
            },
        ],
        "analytic_bookends": {
            "status": "sensitivity_bounds_not_reference_CAE_or_component_result",
            "documentary_force_upper_N": round(
                values["documentary_force_upper_N"], 6
            ),
            "force_assumption": (
                "195 kg documentary engine candidate, alpha_carrier=1, static gravity"
            ),
            "simply_supported_central_point_load": {
                "max_bending_stress_MPa": round(
                    values["simply_supported_stress_MPa"], 9
                ),
                "max_deflection_mm": round(
                    values["simply_supported_deflection_mm"], 9
                ),
                "boundary_condition_validated": False,
            },
            "cantilever_tip_load": {
                "max_bending_stress_MPa": round(
                    values["cantilever_stress_MPa"], 9
                ),
                "max_deflection_mm": round(
                    values["cantilever_deflection_mm"], 9
                ),
                "boundary_condition_validated": False,
            },
            "strength_or_life_conclusion": None,
            "acceptance_criteria_present": False,
        },
        "assets": {
            "editable_scad": relative(SCAD_OUTPUT),
            "editable_scad_sha256": sha256_bytes(scad_text.encode("utf-8")),
            "openusd_guide": relative(USD_OUTPUT),
            "openusd_guide_sha256": sha256_bytes(usd_text.encode("utf-8")),
            "openusd_geometry_prim_count": 4,
            "openusd_physics_schema_count": 0,
            "openusd_material_binding_count": 0,
        },
        "model_roles": {
            "llm": "hypothesis_and_audit_only_no_dimensions_generated",
            "reference_solver": "not_run_analytic_bookends_only",
            "physicsnemo": "ineligible_no_reference_CAE_dataset",
            "omniverse": "OpenUSD_guide_authored_not_SimReady",
        },
        "claim_boundary": {
            "is_oem_geometry": False,
            "is_F2_interface_geometry": False,
            "is_dimensionally_accurate": False,
            "is_fitment_validated": False,
            "is_qualified_material_selection": False,
            "is_reference_CAE_result": False,
            "is_physicsnemo_result": False,
            "is_simready_validated": False,
            "is_manufacturing_release": False,
        },
        "next_gate": (
            "infer_independent_interface_coordinate_candidates_from_licensed_multiview_"
            "evidence_with_scale_uncertainty_then_reject_candidates_that_do_not_fit_"
            "the_mass_constrained_search_domain"
        ),
    }


def validate(
    values: dict[str, float], scad_text: str, usd_text: str, report: dict[str, Any]
) -> None:
    if report.get("status") != (
        "F1_mass_constrained_structural_surrogate_no_component_credit"
    ):
        raise ContractError("status")
    section = report.get("derived_section", {})
    if section.get("mass_constraint_closed") is not True:
        raise ContractError("mass_constraint")
    if abs(float(section.get("mass_error_kg", 1.0))) >= 1e-9:
        raise ContractError("mass_error")
    if not 0.0 < values["equivalent_wall_mm"] < values["width_mm"] / 2.0:
        raise ContractError("equivalent_wall")
    domains = report.get("interface_search_domains", [])
    if len(domains) != 2 or any(item.get("selected_point_count") != 0 for item in domains):
        raise ContractError("interface_search_domain")
    if usd_text.count("def Cube \"Guide\"") != 4:
        raise ContractError("usd_wall_count")
    for prohibited in (
        "UsdPhysics",
        "RigidBodyAPI",
        "CollisionAPI",
        "MassAPI",
        "MaterialBindingAPI",
    ):
        if prohibited in usd_text:
            raise ContractError(f"usd_overclaim:{prohibited}")
    assets = report.get("assets", {})
    if assets.get("editable_scad_sha256") != sha256_bytes(scad_text.encode("utf-8")):
        raise ContractError("scad_digest")
    if assets.get("openusd_guide_sha256") != sha256_bytes(usd_text.encode("utf-8")):
        raise ContractError("usd_digest")
    if any(value is not False for value in report.get("claim_boundary", {}).values()):
        raise ContractError("claim_boundary")


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
        values = derive()
        scad_text = render_scad(values)
        usd_text = render_usd(values)
        report = build_report(values, scad_text, usd_text)
        validate(values, scad_text, usd_text, report)
        expected = {
            SCAD_OUTPUT: scad_text,
            USD_OUTPUT: usd_text,
            REPORT: render_json(report),
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
        checked = load_json(REPORT)
        checked_scad = SCAD_OUTPUT.read_text(encoding="utf-8")
        checked_usd = USD_OUTPUT.read_text(encoding="utf-8")
        validate(values, checked_scad, checked_usd, checked)
        if checked.get("source_boundary", {}).get("files") != report.get(
            "source_boundary", {}
        ).get("files"):
            raise ContractError("source_digests")
        print(f"valid {relative(REPORT)}")
        print(f"valid {relative(SCAD_OUTPUT)} and {relative(USD_OUTPUT)}")
        return 0
    except (ContractError, OSError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
