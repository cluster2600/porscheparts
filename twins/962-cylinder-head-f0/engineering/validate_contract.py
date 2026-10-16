"""Validate engineering inputs without granting head or LPBF qualification."""
import argparse
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
UNITS = {
    "young_modulus_GPa": "GPa", "poisson_ratio": "1", "thermal_expansion_1_K": "1/K",
    "reference_temperature_C": "degC", "metal_temperature_C": "degC",
    "chamber_pressure_bar": "bar", "coolant_pressure_bar": "bar",
}
MATERIAL_UNITS = dict(test_temperature_C="degC", yield_MPa="MPa", ultimate_MPa="MPa",
    elongation_pct="percent", modulus_GPa="GPa", thermal_conductivity_W_mK="W/(m*K)",
    electrical_conductivity_IACS_pct="percent_IACS", density_kg_m3="kg/m3", layer_thickness_um="um")
LPBF_REQUIRED = set("machine_and_parameter_set powder_batch_and_reuse material_recipe_and_state orientation_transform "
    "plate_and_support_geometry clamping_and_contact layer_thickness_and_deposition_history "
    "scan_path_or_calibrated_heat_source temperature_dependent_properties phase_change_model "
    "plasticity_and_stress_reference thermal_boundary_conditions cooldown_history heat_treatment_history "
    "support_release_and_cutoff calibration_coupon_measurements held_out_validation_measurements "
    "mesh_and_time_convergence_protocol".split())
QUALIFICATION_REQUIRED = set("measured_interfaces_and_load_path material_process_card_and_allowables "
    "cylinder_pressure_and_thermal_cycle seat_guide_thread_and_seal_definitions mesh_and_time_convergence "
    "process_calibration independent_physical_correlation professional_engineering_review approved_validation_plan".split())
LAWS_REQUIRED = set("conductivity_vs_temperature youngs_modulus_vs_temperature poisson_ratio_vs_temperature "
    "thermal_expansion_vs_temperature heat_capacity_vs_temperature plastic_stress_strain_vs_temperature "
    "fatigue_and_TMF creep_and_relaxation phase_change_and_latent_heat powder_and_liquid_properties".split())


def number(value, minimum=0, strict=False):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid or (value <= minimum if strict else value < minimum):
        raise ValueError("Invalid finite numeric input")


def digest(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("Expected a SHA-256 digest")


def evidence(value):
    if not isinstance(value, dict) or any(not isinstance(value.get(key), str)
            or not value[key].strip() for key in ("reference", "locator")):
        raise ValueError("Evidence requires a reference and locator")
    if "sha256" in value:
        digest(value["sha256"])


def validate_materials(data):
    if data["units"] != MATERIAL_UNITS or set(data["missing_laws"]) != LAWS_REQUIRED:
        raise ValueError("Material units or required law names changed")
    sources = {source["id"]: source for source in data["sources"]}
    if len(sources) != len(data["sources"]):
        raise ValueError("Duplicate material source")
    for source in sources.values():
        if (urlparse(source["url"]).scheme != "https" or urlparse(source["url"]).hostname
                not in {"www.constellium.com", "assets.foleon.com", "www.eos.info"}
                or not source["publisher"] or not source["locator"]):
            raise ValueError("Material data must retain primary-manufacturer provenance")
        date.fromisoformat(source["accessed_on"])
        if source["sha256"] is not None:
            digest(source["sha256"])
    recipes, identities = {}, set()
    for recipe in data["recipes"]:
        identity = (recipe["alloy"], recipe["machine_model"], recipe["layer_thickness_um"],
                    recipe["build_orientation"], recipe["heat_treatment"]["label"])
        if recipe["id"] in recipes or identity in identities:
            raise ValueError("Recipe IDs and machine/treatment/orientation identities must be distinct")
        if recipe["source_id"] not in sources or not recipe["locator"]:
            raise ValueError("Missing recipe provenance")
        if recipe["qualified_for_962_head"] is not False:
            raise ValueError("Published coupon data cannot qualify the head")
        for point in recipe["tensile_points"]:
            for key in ("yield_MPa", "ultimate_MPa", "elongation_pct"):
                number(point[key], strict=True)
            if point["yield_MPa"] > point["ultimate_MPa"]:
                raise ValueError("Yield strength exceeds ultimate strength")
            if point["modulus_GPa"] is not None:
                number(point["modulus_GPa"], strict=True)
            if point["test_temperature_C"] is not None:
                number(point["test_temperature_C"], -273.15, strict=True)
        for key in ("thermal_conductivity_W_mK", "density_kg_m3"):
            if recipe[key] is not None:
                number(recipe[key]["value"], strict=True)
        recipes[recipe["id"]] = recipe
        identities.add(identity)
    if not recipes or not data["qualification"] or any(value is not False for value in data["qualification"].values()):
        raise ValueError("No material or manufacturing qualification is granted")
    return recipes


def validate(contract, materials, require_ready=False, require_qualification=False):
    recipes = validate_materials(materials)
    if (contract["schema_version"] != "1.0.0" or not contract["qualification"]
            or any(value is not False for value in contract["qualification"].values())):
        raise ValueError("Input preparation cannot grant qualification")
    if [v["bore_mm"] for v in contract["geometry_variants"]] != [95, 98, 100, 102]:
        raise ValueError("The four inspected bore geometries are required")
    for variant in contract["geometry_variants"]:
        if variant["length_unit"] != "mm":
            raise ValueError("Inspected STL units must remain millimetres")
        for key in ("config_sha256", "inspection_report_sha256", "metal_stl_sha256", "native_vdb_sha256"):
            digest(variant[key])
        for key, hash_key in (("geometry_config", "config_sha256"),
                              ("inspection_report", "inspection_report_sha256")):
            path = (ROOT / variant[key]).resolve()
            if not path.is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != variant[hash_key]:
                raise ValueError("Geometry evidence changed: " + variant[key])
        config = json.loads((ROOT / variant["geometry_config"]).read_text())
        report = json.loads((ROOT / variant["inspection_report"]).read_text())
        if (config["geometry"]["bore_mm"] != variant["bore_mm"]
                or report["mesh_metrics"]["solid"]["sha256"] != variant["metal_stl_sha256"]
                or report["vdb_sha256"] != variant["native_vdb_sha256"]):
            raise ValueError("Geometry identifiers do not match their inspection")
    selected = contract["material_recipe_id"]
    if selected is not None and selected not in recipes:
        raise ValueError("Unknown material recipe")
    missing = ["material_recipe_id"] if selected is None else []
    assumptions = []
    if set(contract["research_inputs"]) != set(UNITS):
        raise ValueError("Structural input names differ from the documented contract")
    for key, unit in UNITS.items():
        entry = contract["research_inputs"][key]
        if entry["unit"] != unit:
            raise ValueError("Wrong unit for " + key)
        value = entry["value"]
        if value is None:
            missing.append(key)
            continue
        number(value, -273.15 if key.endswith("temperature_C") else -1 if key == "poisson_ratio" else 0,
               strict=key in {"young_modulus_GPa", "poisson_ratio"} or key.endswith("temperature_C"))
        if key == "poisson_ratio" and value >= .5:
            raise ValueError("Poisson ratio must be below 0.5")
        if entry["basis"] not in {"research_assumption", "measured"}:
            raise ValueError("Executable constants need a measured value or explicit research assumption")
        evidence(entry["source"])
        if entry["basis"] == "measured" and "sha256" not in entry["source"]:
            raise ValueError("Measured inputs require an immutable evidence digest")
        if entry["basis"] == "research_assumption":
            if not isinstance(entry["reason"], str) or not entry["reason"].strip():
                raise ValueError("Research assumptions need a reason")
            assumptions.append(key)
    fixture = contract["fixture_definition"]
    if fixture is None:
        missing.append("fixture_definition")
    else:
        evidence(fixture)
        if fixture.get("basis") == "research_assumption" and fixture.get("reason"):
            assumptions.append("fixture_definition")
        elif fixture.get("basis") != "measured" or "sha256" not in fixture:
            raise ValueError("Fixture must identify measured evidence or a justified research assumption")
    for field, required in (("lpbf_inputs", LPBF_REQUIRED), ("qualification_evidence", QUALIFICATION_REQUIRED)):
        if set(contract[field]) != required:
            raise ValueError("Required engineering input names changed: " + field)
        for value in contract[field].values():
            if value is not None:
                evidence(value)
                if field == "qualification_evidence" and "sha256" not in value:
                    raise ValueError("Qualification evidence requires an immutable digest")
    qualification_missing = ["structural:" + key for key in missing]
    qualification_missing += ["assumption:" + key for key in assumptions]
    qualification_missing += ["lpbf:" + key for key, value in contract["lpbf_inputs"].items() if value is None]
    qualification_missing += ["evidence:" + key for key, value in contract["qualification_evidence"].items() if value is None]
    qualification_missing += ["material_law:" + key for key, value in materials["missing_laws"].items() if value is None]
    if selected is None or recipes[selected]["design_allowables"] is None:
        qualification_missing.append("material:design_allowables")
    if require_ready and missing:
        raise ValueError("Research inputs incomplete: " + ", ".join(missing))
    if require_qualification and qualification_missing:
        raise ValueError("Qualification inputs incomplete: " + ", ".join(qualification_missing))
    return dict(status="input_contract_checked_not_a_physics_result", material_recipes=len(recipes),
                geometry_variants=len(contract["geometry_variants"]), research_inputs_ready=not missing,
                missing_research_inputs=missing, explicit_research_assumptions=assumptions,
                missing_qualification_inputs=qualification_missing, qualification=contract["qualification"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=HERE / "input-contract.json")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--require-qualification", action="store_true")
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.contract.read_text()), json.loads((HERE / "materials.json").read_text()),
                          args.require_ready, args.require_qualification)
        print(json.dumps(result, indent=2, allow_nan=False))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
