#!/usr/bin/env python3
"""Generate a source-bound OpenUSD reference frame for the Porsche 993.

The stage derives seven documented dimensions from the existing editable
OpenSCAD envelope contract.  It is a datum and envelope visualization, not a
body surface, configured vehicle, fitted assembly, or simulation model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ENVELOPE = ROOT / "twin" / "993" / "reference-envelope.json"
MEASUREMENTS = ROOT / "catalog" / "measurements" / "MEAS-MANUAL-993-ALL.json"
PREFLIGHT = (
    ROOT
    / "twins"
    / "vehicle-993"
    / "functional-flow-simready-preflight-f0.json"
)
OUTPUT = ROOT / "twins" / "vehicle-993" / "usd" / "993-reference-frame-f1.usda"
CONTRACT = ROOT / "twins" / "vehicle-993" / "reference-frame-openusd-f1.json"

PARAMETERS = (
    "length_mm",
    "width_mm",
    "height_mm",
    "wheelbase_mm",
    "front_track_mm",
    "rear_track_mm",
    "ground_clearance_mm",
)
MASS_PARAMETERS = {
    "curb_mass_kg": "MNL-TECH-0037",
    "gross_vehicle_mass_kg": "MNL-TECH-0039",
    "max_front_axle_load_kg": "MNL-TECH-0040",
    "max_rear_axle_load_kg": "MNL-TECH-0041",
}


class ContractError(ValueError):
    """Raised when the reference frame would be stale or overclaim fidelity."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_object:{path}")
    return value


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def vector(value: tuple[float, float, float]) -> str:
    return f"({value[0]:.6f}, {value[1]:.6f}, {value[2]:.6f})"


def source_dimensions(envelope: dict[str, Any]) -> dict[str, float]:
    parameters = envelope.get("parameters", {})
    if set(parameters) != set(PARAMETERS):
        raise ContractError("reference_envelope_parameter_set")
    dimensions: dict[str, float] = {}
    for name in PARAMETERS:
        value = parameters.get(name, {}).get("value_mm")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            raise ContractError(f"invalid_dimension:{name}")
        dimensions[name] = float(value) / 1000.0
    if dimensions["wheelbase_mm"] >= dimensions["length_mm"]:
        raise ContractError("wheelbase_not_inside_length")
    if max(dimensions["front_track_mm"], dimensions["rear_track_mm"]) >= dimensions[
        "width_mm"
    ]:
        raise ContractError("track_not_inside_width")
    if dimensions["ground_clearance_mm"] >= dimensions["height_mm"]:
        raise ContractError("clearance_not_inside_height")
    return dimensions


def source_mass_constraints(
    measurements: dict[str, Any],
) -> tuple[dict[str, float], dict[str, dict[str, Any]]]:
    rows = measurements.get("declared_values", [])
    by_id = {
        str(row.get("value_id")): row
        for row in rows
        if isinstance(row, dict) and row.get("value_id")
    }
    values: dict[str, float] = {}
    evidence: dict[str, dict[str, Any]] = {}
    for name, value_id in MASS_PARAMETERS.items():
        row = by_id.get(value_id)
        if row is None:
            raise ContractError(f"missing_mass_constraint:{value_id}")
        numeric_values = row.get("numeric_values", [])
        if not isinstance(numeric_values, list) or not numeric_values:
            raise ContractError(f"missing_mass_value:{value_id}")
        value = numeric_values[0]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            raise ContractError(f"invalid_mass_value:{value_id}")
        if str(row.get("unit", "")).strip() != "kg":
            raise ContractError(f"invalid_mass_unit:{value_id}")
        values[name] = float(value)
        evidence[name] = {
            "source_measurement_id": value_id,
            "pdf_page": int(row.get("pdf_page", 0)),
            "value_text": str(row.get("value_text", "")),
            "extraction_status": str(row.get("extraction_status", "")),
        }
    if values["curb_mass_kg"] >= values["gross_vehicle_mass_kg"]:
        raise ContractError("curb_mass_not_below_gross_mass")
    if (
        values["max_front_axle_load_kg"] + values["max_rear_axle_load_kg"]
        < values["gross_vehicle_mass_kg"]
    ):
        raise ContractError("axle_capacity_below_gross_mass")
    return values, evidence


def curve(
    name: str,
    points: list[tuple[float, float, float]],
    counts: list[int],
    width: float,
    color: tuple[float, float, float],
    extra: list[str],
) -> list[str]:
    rendered_points = ", ".join(vector(point) for point in points)
    rendered_counts = ", ".join(str(count) for count in counts)
    lines = [
        f'        def BasisCurves "{name}"',
        "        {",
        '            uniform token type = "linear"',
        f"            int[] curveVertexCounts = [{rendered_counts}]",
        f"            point3f[] points = [{rendered_points}]",
        f"            float[] widths = [{width:.4f}]",
        f"            color3f[] primvars:displayColor = [{vector(color)}]",
        '            uniform token primvars:displayColor:interpolation = "constant"',
    ]
    lines.extend(f"            {item}" for item in extra)
    lines.append("        }")
    return lines


def render_stage(envelope: dict[str, Any], measurements: dict[str, Any]) -> str:
    dimensions = source_dimensions(envelope)
    mass_constraints, mass_evidence = source_mass_constraints(measurements)
    length = dimensions["length_mm"]
    width = dimensions["width_mm"]
    height = dimensions["height_mm"]
    wheelbase = dimensions["wheelbase_mm"]
    front_track = dimensions["front_track_mm"]
    rear_track = dimensions["rear_track_mm"]
    clearance = dimensions["ground_clearance_mm"]
    front_axle_x = (length - wheelbase) / 2.0
    rear_axle_x = front_axle_x + wheelbase
    xs = (0.0, length)
    ys = (-width / 2.0, width / 2.0)
    zs = (0.0, height)
    envelope_points: list[tuple[float, float, float]] = []
    for y in ys:
        for z in zs:
            envelope_points.extend([(xs[0], y, z), (xs[1], y, z)])
    for x in xs:
        for z in zs:
            envelope_points.extend([(x, ys[0], z), (x, ys[1], z)])
    for x in xs:
        for y in ys:
            envelope_points.extend([(x, y, zs[0]), (x, y, zs[1])])
    parameters = envelope["parameters"]
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "ReferenceFrame993"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        ")",
        "",
        'def Xform "ReferenceFrame993" (',
        "    customData = {",
        '        string fidelity = "F1_documented_reference_envelope"',
        '        string purpose = "datum_cage_not_vehicle_body_geometry"',
        "        int sourcedDimensionCount = 7",
        "        int positionedVehiclePartCount = 0",
        "        bool axleLongitudinalPositionsAreSourced = false",
        "        bool materialAssigned = false",
        "        bool physicsAssigned = false",
        "        bool simreadyValidated = false",
        "        bool functioningVehicle = false",
        "    }",
        ")",
        "{",
        '    def Scope "DocumentedValues"',
        "    {",
    ]
    for name in PARAMETERS:
        source = parameters[name]
        lines.extend(
            [
                f'        def Scope "{name}"',
                "        {",
                f"            custom double valueMeters = {dimensions[name]:.6f}",
                f'            custom string sourceMeasurementId = {json.dumps(source["source_measurement_id"])}',
                f"            custom int sourcePdfPage = {int(source['pdf_page'])}",
                "        }",
            ]
        )
    lines.extend(["", '        def Scope "MassConstraints"', "        {"])
    for name in MASS_PARAMETERS:
        source = mass_evidence[name]
        lines.extend(
            [
                f'            def Scope "{name}"',
                "            {",
                f"                custom double valueKilograms = {mass_constraints[name]:.3f}",
                f'                custom string sourceMeasurementId = {json.dumps(source["source_measurement_id"])}',
                f"                custom int sourcePdfPage = {source['pdf_page']}",
                "                custom bool isUsdMassProperty = false",
                "            }",
            ]
        )
    lines.extend(["        }"])
    lines.extend(["    }", "", '    def Scope "ReferenceGeometry"', "    {"])
    lines.extend(
        curve(
            "EnvelopeCage",
            envelope_points,
            [2] * 12,
            0.008,
            (0.20, 0.55, 0.95),
            [
                'custom string fidelity = "F1_documented_envelope"',
                "custom bool isBodySurface = false",
                "custom bool collisionGeometry = false",
            ],
        )
    )
    lines.extend(
        curve(
            "FrontAxleDatum",
            [
                (front_axle_x, -front_track / 2.0, 0.0),
                (front_axle_x, front_track / 2.0, 0.0),
            ],
            [2],
            0.014,
            (0.90, 0.15, 0.15),
            [
                'custom string longitudinalPosition = "display_centered_assumption"',
                "custom bool longitudinalPositionSourced = false",
                "custom bool trackWidthSourced = true",
            ],
        )
    )
    lines.extend(
        curve(
            "RearAxleDatum",
            [
                (rear_axle_x, -rear_track / 2.0, 0.0),
                (rear_axle_x, rear_track / 2.0, 0.0),
            ],
            [2],
            0.014,
            (0.90, 0.15, 0.15),
            [
                'custom string longitudinalPosition = "display_centered_assumption"',
                "custom bool longitudinalPositionSourced = false",
                "custom bool trackWidthSourced = true",
            ],
        )
    )
    lines.extend(
        curve(
            "GroundClearanceDatum",
            [(0.0, -width / 2.0, clearance), (0.0, width / 2.0, clearance)],
            [2],
            0.012,
            (1.00, 0.70, 0.10),
            [
                'custom string longitudinalPosition = "display_only"',
                "custom bool undersideSurfacePresent = false",
            ],
        )
    )
    lines.extend(
        curve(
            "VehicleCenterline",
            [(0.0, 0.0, 0.0), (length, 0.0, 0.0)],
            [2],
            0.006,
            (0.65, 0.65, 0.65),
            ["custom bool vehicleDatumValidated = false"],
        )
    )
    lines.extend(["    }", "}", ""])
    return "\n".join(lines)


def build_contract(
    envelope: dict[str, Any],
    measurements: dict[str, Any],
    preflight: dict[str, Any],
    stage: str,
) -> dict[str, Any]:
    dimensions = source_dimensions(envelope)
    mass_constraints, mass_evidence = source_mass_constraints(measurements)
    return {
        "$comment": (
            "Repere OpenUSD F1 derive de sept dimensions documentees. La cage "
            "n'est ni une carrosserie, ni un assemblage positionne, ni un actif SimReady."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "reference_envelope": relative(REFERENCE_ENVELOPE),
            "reference_envelope_sha256": sha256_file(REFERENCE_ENVELOPE),
            "measurement_registry": relative(MEASUREMENTS),
            "measurement_registry_sha256": sha256_file(MEASUREMENTS),
            "simready_preflight": relative(PREFLIGHT),
            "simready_preflight_sha256": sha256_file(PREFLIGHT),
            "simready_preflight_status": preflight.get("status"),
        },
        "scope": {
            "fidelity": "F1_documented_reference_envelope",
            "variant_scope": envelope.get("variant"),
            "sourced_dimensions": 7,
            "sourced_mass_constraints": 4,
            "reference_curve_prims": 5,
            "positioned_vehicle_parts": 0,
            "body_surface_count": 0,
            "interface_geometry_count": 0,
            "mass_property_count": 0,
            "physics_schema_count": 0,
            "material_assignment_count": 0,
        },
        "mathematical_sanity_checks": {
            "wheelbase_inside_overall_length": dimensions["wheelbase_mm"]
            < dimensions["length_mm"],
            "front_track_inside_overall_width": dimensions["front_track_mm"]
            < dimensions["width_mm"],
            "rear_track_inside_overall_width": dimensions["rear_track_mm"]
            < dimensions["width_mm"],
            "ground_clearance_inside_overall_height": dimensions[
                "ground_clearance_mm"
            ]
            < dimensions["height_mm"],
            "wheelbase_to_length_ratio": round(
                dimensions["wheelbase_mm"] / dimensions["length_mm"], 9
            ),
            "front_track_to_width_ratio": round(
                dimensions["front_track_mm"] / dimensions["width_mm"], 9
            ),
            "rear_track_to_width_ratio": round(
                dimensions["rear_track_mm"] / dimensions["width_mm"], 9
            ),
            "curb_mass_below_gross_vehicle_mass": mass_constraints[
                "curb_mass_kg"
            ]
            < mass_constraints["gross_vehicle_mass_kg"],
            "combined_axle_capacity_not_below_gross_vehicle_mass": (
                mass_constraints["max_front_axle_load_kg"]
                + mass_constraints["max_rear_axle_load_kg"]
                >= mass_constraints["gross_vehicle_mass_kg"]
            ),
            "declared_payload_difference_kg": round(
                mass_constraints["gross_vehicle_mass_kg"]
                - mass_constraints["curb_mass_kg"],
                3,
            ),
            "combined_axle_capacity_margin_kg": round(
                mass_constraints["max_front_axle_load_kg"]
                + mass_constraints["max_rear_axle_load_kg"]
                - mass_constraints["gross_vehicle_mass_kg"],
                3,
            ),
        },
        "documented_mass_constraints": {
            name: {
                "value_kg": mass_constraints[name],
                **mass_evidence[name],
                "is_mass_distribution_measurement": False,
                "is_usd_mass_property": False,
            }
            for name in MASS_PARAMETERS
        },
        "stage": {
            "path": relative(OUTPUT),
            "format": "OpenUSD_ASCII",
            "sha256": sha256_bytes(stage.encode("utf-8")),
            "meters_per_unit": 1,
            "up_axis": "Z",
        },
        "uncertainty_boundary": {
            "dimensional_tolerance_mm": None,
            "body_surface_unknown": True,
            "body_to_axle_longitudinal_transform": None,
            "axle_longitudinal_positions_in_stage": "display_centered_assumption",
            "part_transforms_known": 0,
        },
        "validation": {
            "deterministic_ascii_contract": "passed",
            "minimum_usd_validation": "not_run_preflight_blocked",
            "content_agents_material_physics": "not_run_preflight_blocked",
            "asset_validator": "not_run_preflight_blocked",
            "simready_foundation": "not_run_preflight_blocked",
            "property_assignment_intent": "run_for_end_to_end_request",
            "current_status": "authored_pending_ready_cad_to_simready_preflight",
        },
        "claim_boundary": {
            "is_vehicle_body_geometry": False,
            "is_part_geometry": False,
            "is_fitted_assembly": False,
            "is_material_assigned": False,
            "is_physics_assigned": False,
            "is_simready_validated": False,
            "is_virtual_mission_pass": False,
            "is_functioning_vehicle": False,
            "is_manufacturing_release": False,
        },
        "next_gate": (
            "source_variant_specific_body_to_axle_datums_tolerances_and_F2_interfaces_"
            "then_rerun_ready_CAD_to_SimReady_preflight_before_property_assignment"
        ),
    }


def validate(
    envelope: dict[str, Any],
    measurements: dict[str, Any],
    preflight: dict[str, Any],
    stage: str,
    contract: dict[str, Any],
) -> None:
    source_dimensions(envelope)
    source_mass_constraints(measurements)
    if preflight.get("status") != "blocked":
        raise ContractError("unexpected_preflight_status")
    if stage.count("def BasisCurves") != 5:
        raise ContractError("reference_curve_count")
    if stage.count("sourceMeasurementId") != 11:
        raise ContractError("source_measurement_count")
    for prohibited in (
        "UsdPhysics",
        "RigidBodyAPI",
        "CollisionAPI",
        "MassAPI",
        "MaterialBindingAPI",
    ):
        if prohibited in stage:
            raise ContractError(f"prohibited_schema:{prohibited}")
    scope = contract.get("scope", {})
    if scope.get("sourced_dimensions") != 7:
        raise ContractError("sourced_dimension_count")
    if scope.get("sourced_mass_constraints") != 4:
        raise ContractError("sourced_mass_constraint_count")
    for key in (
        "positioned_vehicle_parts",
        "body_surface_count",
        "interface_geometry_count",
        "mass_property_count",
        "physics_schema_count",
        "material_assignment_count",
    ):
        if scope.get(key) != 0:
            raise ContractError(f"scope_overclaim:{key}")
    checks = contract.get("mathematical_sanity_checks", {})
    if not all(
        checks.get(key) is True
        for key in (
            "wheelbase_inside_overall_length",
            "front_track_inside_overall_width",
            "rear_track_inside_overall_width",
            "ground_clearance_inside_overall_height",
            "curb_mass_below_gross_vehicle_mass",
            "combined_axle_capacity_not_below_gross_vehicle_mass",
        )
    ):
        raise ContractError("mathematical_sanity_check")
    if contract.get("stage", {}).get("sha256") != sha256_bytes(stage.encode("utf-8")):
        raise ContractError("stage_digest")
    if any(value is not False for value in contract.get("claim_boundary", {}).values()):
        raise ContractError("claim_boundary")
    if contract.get("validation", {}).get("minimum_usd_validation") != (
        "not_run_preflight_blocked"
    ):
        raise ContractError("preflight_guardrail")


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
        envelope = load_json(REFERENCE_ENVELOPE)
        measurements = load_json(MEASUREMENTS)
        preflight = load_json(PREFLIGHT)
        stage = render_stage(envelope, measurements)
        contract = build_contract(envelope, measurements, preflight, stage)
        validate(envelope, measurements, preflight, stage, contract)
        expected_contract = render_json(contract)
        if args.write:
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(stage, encoding="utf-8")
            CONTRACT.write_text(expected_contract, encoding="utf-8")
            print(f"wrote {relative(OUTPUT)}")
            print(f"wrote {relative(CONTRACT)}")
            return 0
        for path in (OUTPUT, CONTRACT):
            if not path.is_file():
                print(f"missing:{path}")
                return 1
        if args.check:
            if OUTPUT.read_text(encoding="utf-8") != stage:
                print(f"stale:{OUTPUT}")
                return 1
            if CONTRACT.read_text(encoding="utf-8") != expected_contract:
                print(f"stale:{CONTRACT}")
                return 1
        checked_stage = OUTPUT.read_text(encoding="utf-8")
        checked_contract = load_json(CONTRACT)
        validate(
            envelope, measurements, preflight, checked_stage, checked_contract
        )
        boundary = checked_contract.get("source_boundary", {})
        if boundary.get("reference_envelope_sha256") != sha256_file(
            REFERENCE_ENVELOPE
        ):
            raise ContractError("reference_envelope_digest")
        if boundary.get("measurement_registry_sha256") != sha256_file(MEASUREMENTS):
            raise ContractError("measurement_registry_digest")
        if boundary.get("simready_preflight_sha256") != sha256_file(PREFLIGHT):
            raise ContractError("preflight_digest")
        print(f"valid {relative(OUTPUT)}")
        print(f"valid {relative(CONTRACT)}")
        return 0
    except ContractError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
