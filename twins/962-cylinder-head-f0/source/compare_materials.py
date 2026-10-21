"""Compare sourced coupon points and conditional geometric mass, without qualification."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

FAMILY = Path(__file__).resolve().parents[1]
ROOT = FAMILY.parents[1]
MATERIALS = FAMILY / "engineering/materials.json"
CONTRACT = FAMILY / "engineering/input-contract.json"
DELIVERY = FAMILY / "derived/family/delivery-report.json"
VALIDATOR = FAMILY / "engineering/validate_contract.py"
HT1_IDS = {"ht1-treatment-1-m290-60um-vertical", "ht1-treatment-2-m290-60um-vertical"}

spec = importlib.util.spec_from_file_location("head_material_input_validator", VALIDATOR)
engineering = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engineering)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(materials, geometry):
    """Use only supplied density and discrete same-treatment yield points."""
    recipes = engineering.validate_materials(materials)
    if [item["bore_mm"] for item in geometry] != [95, 98, 100, 102]:
        raise ValueError("The four inspected bore geometries are required")
    for item in geometry:
        engineering.number(item["metal_volume_cm3"], strict=True)
    results = []
    for recipe in recipes.values():
        density = recipe["density_kg_m3"]
        if density is not None and density["bound"] not in {"minimum", "maximum", "nominal"}:
            raise ValueError("Unsupported published density bound")
        masses = []
        for item in geometry:
            value = None
            if density is not None:
                value = item["metal_volume_cm3"] * 1e-6 * density["value"]
                engineering.number(value, strict=True)
            masses.append(dict(bore_mm=item["bore_mm"], conditional_head_mass_kg=value,
                               bound_for_fixed_study_volume=None if density is None else density["bound"]))
        retention = None
        if recipe["id"] in HT1_IDS:
            points = {point["test_temperature_C"]: point for point in recipe["tensile_points"]}
            if len(recipe["tensile_points"]) != 3 or set(points) != {25, 200, 250}:
                raise ValueError("HT1 retention requires separate 25/200/250 C points in each treatment")
            reference = points[25]["yield_MPa"]
            retention = []
            for temperature in (200, 250):
                value = points[temperature]["yield_MPa"] / reference * 100
                engineering.number(value, strict=True)
                retention.append(dict(test_temperature_C=temperature,
                    yield_MPa=points[temperature]["yield_MPa"], reference_temperature_C=25,
                    same_recipe_reference_yield_MPa=reference, yield_retention_percent=value))
        results.append(dict(recipe_id=recipe["id"], alloy=recipe["alloy"],
            machine_model=recipe["machine_model"], layer_thickness_um=recipe["layer_thickness_um"],
            build_orientation=recipe["build_orientation"], heat_treatment=recipe["heat_treatment"],
            source_id=recipe["source_id"], locator=recipe["locator"],
            density_kg_m3=density, conditional_head_masses=masses,
            tensile_points=recipe["tensile_points"], ht1_yield_retention=retention,
            thermal_conductivity_W_mK=recipe["thermal_conductivity_W_mK"],
            electrical_conductivity_IACS_pct=recipe["electrical_conductivity_IACS_pct"],
            design_allowables=recipe["design_allowables"], limits=recipe["limits"]))
    return results


def report():
    paths = [MATERIALS, CONTRACT, DELIVERY, VALIDATOR, Path(__file__).resolve()]
    materials = json.loads(MATERIALS.read_text())
    contract = json.loads(CONTRACT.read_text())
    delivery = json.loads(DELIVERY.read_text())
    engineering.validate(contract, materials)
    if delivery["length_unit"] != "mm":
        raise ValueError("Retained geometry units changed")
    models = {model["bore_mm"]: model for model in delivery["models"]}
    if len(models) != 4 or len(delivery["models"]) != 4:
        raise ValueError("The four distinct retained head geometries are required")
    geometry = []
    for variant in contract["geometry_variants"]:
        model = models[variant["bore_mm"]]
        inspection_path = ROOT / variant["inspection_report"]
        inspection = json.loads(inspection_path.read_text())
        if (model["report_path"] != variant["inspection_report"]
                or sha256(inspection_path) != model["report_sha256"]
                or model["report_sha256"] != variant["inspection_report_sha256"]
                or model["metal_volume_cm3"] != inspection["mesh_metrics"]["solid"]["volume_mm3"] / 1000):
            raise ValueError("Retained delivery volume or inspection identity changed")
        geometry.append(dict(bore_mm=variant["bore_mm"],
            metal_volume_cm3=model["metal_volume_cm3"],
            inspection_report=variant["inspection_report"],
            metal_stl_sha256=variant["metal_stl_sha256"]))
        paths.extend([inspection_path, ROOT / variant["geometry_config"]])
    return dict(schema_version="1.0.0",
        status="conditional_mass_and_manufacturer_coupon_point_arithmetic_only",
        inputs=[dict(path=path.relative_to(ROOT).as_posix(), sha256=sha256(path)) for path in paths],
        formulas=dict(conditional_mass_kg="metal_volume_cm3 * 1e-6 * published_density_kg_m3",
            ht1_yield_retention_percent="100 * yield_at_published_temperature / yield_at_25_C_same_recipe"),
        geometry=geometry, sources=materials["sources"], recipes=compare(materials, geometry),
        missing_laws=materials["missing_laws"], selected_material_recipe_id=None,
        selected_service_temperature_C=None,
        limitations=[
            "Mass uses only the inspected study body's geometric volume; no installed assembly, machining, supports, seats, guides or fasteners are included.",
            "A published minimum density gives a conditional minimum mass at fixed geometric volume, not a measured mass or a bound accounting for geometry uncertainty.",
            "Missing density stays null; no aluminum density is inferred from another alloy or handbook.",
            "Yield retention divides discrete manufacturer coupon points within one HT1 treatment; no interpolation, constitutive law, design allowable or service-temperature selection is produced.",
            "Unknown EOS tensile-test temperatures stay null; heat-treatment temperatures are not tensile-test or service temperatures.",
            "Electrical conductivity is not thermal conductivity; scalar properties are not temperature-dependent material cards.",
        ], qualification=dict(material_process_qualified=False, strength_validated=False,
            fatigue_validated=False, manufacturing_authorized=False))


def verify_bound_inputs(result, root=ROOT):
    for item in result["inputs"]:
        relative = Path(item["path"])
        path = (root / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(root.resolve()) or sha256(path) != item["sha256"]:
            raise ValueError("Bound material-comparison input changed: " + item["path"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    outputs = parser.add_mutually_exclusive_group()
    outputs.add_argument("--output", type=Path, help="Write a new report; refuse an existing path")
    outputs.add_argument("--check", type=Path, help="Check a retained report and its bound inputs")
    args = parser.parse_args()
    try:
        if args.check is not None:
            retained = json.loads(args.check.read_text())
            verify_bound_inputs(retained)
            if retained != report():
                raise ValueError("Retained comparison differs from the current calculation")
            print("Material comparison matches its inputs and calculator; qualification remains false")
        else:
            text = json.dumps(report(), indent=2, allow_nan=False) + "\n"
            if args.output is None:
                print(text, end="")
            else:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open("x") as stream:
                    stream.write(text)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
