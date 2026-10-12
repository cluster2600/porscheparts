#!/usr/bin/env python3
"""Reuse the recorded PicoGK prototype generator with reviewed FIA references."""
import argparse
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location("prototype917",HERE.parent/"hypothesis/run.py")
PROTOTYPE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROTOTYPE)


def validate_reference(config, review):
    d = PROTOTYPE.validate(config)
    if review["variant"] != "917_type_912_4_494" or config["variant_seed"] != "type_912_4_494_fia_documentary_reference_candidate":
        raise ValueError("FIA base and extension variants must not be mixed")
    for fact in review["facts"].values():
        if isinstance(fact["value"],bool) or not math.isfinite(fact["value"]) or fact["value"] <= 0:
            raise ValueError("Invalid documentary reference")
        if "declared_plus_minus_kg" in fact and not 0 <= fact["declared_plus_minus_kg"] < fact["value"]:
            raise ValueError("Invalid documentary mass interval")
    if review["facts"]["cylinder_count"]["value"] != 12:
        raise ValueError("Preserved generator requires twelve cylinders")
    if d["rod_length"] not in config["rod_length_sensitivity_mm"]:
        raise ValueError("Actual rod length must be present in the coverage experiment grid")
    for name,fact in (("bore","bore"),("stroke","stroke"),("crankpin_diameter","crankpin_bearing_diameter"),
                      ("piston_pin_axis_to_crown","pin_axis_to_crown")):
        if d[name] != review["facts"][fact]["value"] or review["facts"][fact]["unit"] != "mm":
            raise ValueError("Candidate differs from reviewed FIA reference: "+name)
    # shortcut: preserved native generator has a symmetric piston; use asymmetric CAD when skirt data is established.
    if d["piston_height"] != 2*d["piston_pin_axis_to_crown"] or d["piston_skirt_below_pin"] != d["piston_pin_axis_to_crown"]:
        raise ValueError("Preserved symmetric generator cannot represent this piston")
    if d["rod_big_bore"] != d["crankpin_diameter"]+2*d["assumed_bearing_radial_thickness"]:
        raise ValueError("Rod housing must retain the explicit bearing allowance hypothesis")
    if (review["ambiguous_excluded"]["geometry_binding_allowed"]
            or review["extension_1_1E"]["applied_to_current_candidate"]):
        raise ValueError("Excluded FIA reference promoted to geometry")
    for path,key in (("catalog/sources/src-fia-917-homologation-250.json","catalog_sha256"),
                     ("twins/reference-917-engine/classical-solver-cases-f13.json","existing_fact_registry_sha256")):
        if PROTOTYPE.sha256(ROOT/path) != review[key]:
            raise ValueError("Existing source registry differs from reviewed snapshot")
    registry = {f["id"]:f for f in json.loads((ROOT/"twins/reference-917-engine/classical-solver-cases-f13.json").read_text())["fact_registry"]}
    for fact,identifier in (("pin_axis_to_crown","FACT-45-PISTON-COMPRESSION-HEIGHT"),
                            ("crankpin_bearing_diameter","FACT-45-CRANKPIN-BEARING-DIAMETER"),
                            ("rod_mass","FACT-45-CONNECTING-ROD-MASS"),
                            ("piston_pin_ring_group_mass","FACT-45-PISTON-GROUP-MASS")):
        if registry[identifier]["candidate"]["value"] != review["facts"][fact]["value"]:
            raise ValueError("Review differs from existing source fact: "+fact)
    return d


def documentary_mass_cases(config, review):
    d = validate_reference(config,review)
    group,rod = (review["facts"][key] for key in ("piston_pin_ring_group_mass","rod_mass"))
    fraction = config["rod_reciprocating_mass_fraction"]
    mass = group["value"]+fraction*rod["value"]
    uncertainty = group["declared_plus_minus_kg"]+fraction*rod["declared_plus_minus_kg"]
    cases = []
    for rpm in config["rpm_cases"]:
        accel = max(abs(PROTOTYPE.acceleration(d,a,1)) for a in range(361))*1e-3*(rpm*2*math.pi/60)**2
        for pressure in config["peak_pressure_bar_cases"]:
            gas = pressure*1e5*math.pi/4*(d["bore"]*1e-3)**2
            cases.append({"rpm":rpm,"assumed_peak_pressure_bar":pressure,"documentary_reciprocating_mass_kg":mass,
                          "declared_mass_bound_kg":[mass-uncertainty,mass+uncertainty],
                          "gas_force_N":gas,"nominal_peak_inertia_N":mass*accel,
                          "independent_peak_sum_bound_N":[gas+(mass-uncertainty)*accel,gas+(mass+uncertainty)*accel]})
    return cases


def run(output, dotnet):
    config_path,review_path = HERE/"reference-assumptions.json",HERE/"source-review.json"
    config,review = (json.loads(p.read_text()) for p in (config_path,review_path))
    validate_reference(config,review)
    hashes = {name:PROTOTYPE.sha256(HERE/name) for name in ("run.py","source-review.json","reference-assumptions.json")}
    result = PROTOTYPE.run(config_path,output,dotnet,[1,.5])
    if any(PROTOTYPE.sha256(HERE/name) != value for name,value in hashes.items()):
        PROTOTYPE.save(Path(output)/"source-review-status.json",{"status":"rejected_fia_inputs_changed","manufacturing_authorized":False})
        raise ValueError("FIA experiment inputs changed during execution")
    result["classification"] = "documentary_reference_bound_geometry_plus_explicit_unmeasured_hypotheses"
    result["fia_input_sha256"] = hashes
    result["fia_reference"] = review
    result["documentary_mass_cases"] = documentary_mass_cases(config,review)
    result["documentary_mass_scope"] = "original_4_494_piston_pin_rings_and_rod_masses_not_new_material_or_mesh_mass; pressure_and_rod_mass_fraction_remain_hypothetical"
    result["geometry_coverage_criterion_pass"] = all(row["hypothesis_consistent_with_full_skirt_coverage"] for row in result["motion"]["rod_length_sensitivity"] if row["rod_length_mm"]==config["dimensions_mm"]["rod_length"])
    result["status"] = "reference_reconciled_provisional_barrel_coverage_rejected_no_release" if not result["geometry_coverage_criterion_pass"] else "reference_reconciled_partial_screen_only_no_release"
    PROTOTYPE.save(Path(output)/"fia-reference-report.json",result)
    PROTOTYPE.save(Path(output)/"source-review-status.json",{"status":result["status"],"manufacturing_authorized":False})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--dotnet",required=True)
    a = parser.parse_args()
    run(a.output,a.dotnet)
