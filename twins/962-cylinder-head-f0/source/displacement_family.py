"""Six-cylinder swept-volume arithmetic; no replica geometry or fitment approval."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

FAMILY = Path(__file__).resolve().parents[1]
CONFIG = FAMILY / "replica-family.json"
RETAINED_REPORT = FAMILY / "derived/replica-family-report.json"
TARGETS = (2994, 3164, 3400, 3600, 3800, 4000)


def positive_number(value):
    try:
        valid = (type(value) in (int, float) and math.isfinite(value)
                 and value >= sys.float_info.min)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError("Expected a positive finite normal number, not a boolean")
    return value


def calculate(displacement_cm3, bore_mm=None, stroke_mm=None):
    """Solve one dimension only when the other is supplied as an assumption."""
    displacement_cm3 = positive_number(displacement_cm3)
    if not 2994 <= displacement_cm3 <= 4000:
        raise ValueError("Displacement must be between 2994 and 4000 cm3")
    if bore_mm is not None and stroke_mm is not None:
        raise ValueError("Supply at most one assumed bore or stroke")
    assumptions = {key: value for key, value in (
        ("bore_mm", bore_mm), ("stroke_mm", stroke_mm)) if value is not None}
    for value in assumptions.values():
        positive_number(value)
    try:
        if bore_mm is not None:
            stroke_mm = displacement_cm3 * 4000 / (math.pi * bore_mm ** 2 * 6)
        elif stroke_mm is not None:
            bore_mm = math.sqrt(displacement_cm3 * 4000 / (math.pi * stroke_mm * 6))
        if assumptions:
            positive_number(bore_mm)
            positive_number(stroke_mm)
            reconstructed = math.pi / 4 * bore_mm ** 2 * stroke_mm * 6 / 1000
            if not math.isfinite(reconstructed) or not math.isclose(
                    reconstructed, displacement_cm3, rel_tol=1e-12):
                raise ValueError("Swept-volume arithmetic lost precision")
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Swept-volume arithmetic overflow or underflow") from exc
    return dict(displacement_cm3=displacement_cm3, cylinder_count=6,
                swept_volume_per_cylinder_cm3=displacement_cm3 / 6,
                bore_mm=bore_mm, stroke_mm=stroke_mm,
                dimension_basis="algebra_from_assumed_dimension" if assumptions else None,
                input_assumptions=assumptions, geometry_generated=False,
                fitment_validated=False, manufacturing_authorized=False)


def report(config=None):
    config = json.loads(CONFIG.read_text()) if config is None else config
    if (config["schema_version"] != "1.0.0"
            or config["status"] != "reference_definition_and_displacement_sizing_only"
            or config["reference"]["published_displacement_cm3"] != 2994
            or any(config["reference"][key] is not None for key in (
                "selected_engine_type", "selected_year", "part_reference", "bore_mm",
                "stroke_mm", "spark_plugs_per_cylinder", "cylinder_head_joint_for_selected_variant",
                "alloy_and_heat_treatment"))
            or config["envelope"] != {"min_cm3": 2994, "max_cm3": 4000}
            or config["architecture"]["cylinder_count"] != 6
            or config["design_policy"]["uniform_head_scaling_allowed"] is not False
            or config["design_policy"]["historical_master_available"] is not False
            or not config["required_measured_inputs"]
            or any(value is not None for value in config["required_measured_inputs"].values())
            or not config["qualification"]
            or any(value is not False for value in config["qualification"].values())):
        raise ValueError("Replica family reference, envelope or qualification changed")
    variants = config["variants"]
    if (tuple(v["target_displacement_cm3"] for v in variants) != TARGETS
            or len({v["id"] for v in variants}) != len(variants)):
        raise ValueError("Replica family must retain its six distinct targets")
    outputs = []
    for variant in variants:
        expected_basis = "published" if variant["target_displacement_cm3"] in TARGETS[:2] else "proposed_target"
        if (variant["basis"] != expected_basis or variant["bore_mm"] is not None
                or variant["stroke_mm"] is not None):
            raise ValueError("Historical targets cannot grant unmeasured dimensions")
        outputs.append(dict(**variant, calculation=calculate(variant["target_displacement_cm3"])))
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return dict(status="displacement_family_definition_without_replica_geometry",
                reference=config["reference"], envelope=config["envelope"],
                variants=outputs, qualification=config["qualification"],
                config_canonical_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-cm3", type=float)
    dimensions = parser.add_mutually_exclusive_group()
    dimensions.add_argument("--bore-mm", type=float)
    dimensions.add_argument("--stroke-mm", type=float)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.target_cm3 is None and (args.bore_mm is not None or args.stroke_mm is not None):
        parser.error("An assumed dimension requires --target-cm3")
    if args.check and (args.target_cm3 is not None or args.output is not None):
        parser.error("--check accepts no calculation or output arguments")
    try:
        result = (report() if args.target_cm3 is None else
                  calculate(args.target_cm3, args.bore_mm, args.stroke_mm))
        if args.check:
            if json.loads(RETAINED_REPORT.read_text()) != result:
                raise ValueError("Retained family report differs from its config or source")
            print("Replica family report matches its configuration and calculator")
        else:
            text = json.dumps(result, indent=2, allow_nan=False) + "\n"
            if args.output is None:
                print(text, end="")
            else:
                with args.output.open("x") as output:
                    output.write(text)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
