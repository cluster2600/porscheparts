#!/usr/bin/env python3
"""Build the F9 917/30 power requirement envelopes without claiming proof."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "twins" / "reference-917-engine" / "performance-target-f9.json"
DEFAULT_OUTPUT = ROOT / "work" / "917-performance-f9" / "power-requirement-envelopes.json"
SOURCES = ROOT / "catalog" / "sources"

POWER_TO_W = {
    "kW": 1000.0,
    "PS": 735.49875,
    "hp": 745.6998715822702,
}
REQUIRED_PROOF_FLAGS = (
    "thermodynamic_solver_ready",
    "calibration_ready",
    "held_out_validation_ready",
    "physical_dyno_proof_ready",
    "performance_claim_authorized",
)
REQUIRED_FALSE_MODEL_POLICIES = (
    "allow_default_engine_operating_values",
    "allow_airflow_prediction",
    "allow_pressure_prediction",
    "allow_temperature_prediction",
    "allow_turbo_matching",
    "allow_performance_extrapolation",
)


def _positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _known_source_ids() -> set[str]:
    known: set[str] = set()
    for path in SOURCES.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(record, dict) and isinstance(record.get("source_id"), str):
            known.add(record["source_id"])
    return known


def power_w(value: float, unit: str) -> float:
    return float(value) * POWER_TO_W[unit]


def displacement_m3(bore_mm: float, stroke_mm: float, cylinder_count: int) -> float:
    bore_m = float(bore_mm) / 1000.0
    stroke_m = float(stroke_mm) / 1000.0
    return math.pi * bore_m**2 * stroke_m * int(cylinder_count) / 4.0


def torque_nm(required_power_w: float, rpm: float) -> float:
    return required_power_w * 60.0 / (2.0 * math.pi * rpm)


def bmep_bar(required_torque_nm: float, swept_volume_m3: float, strokes: int) -> float:
    cycle_revolutions = strokes / 2.0
    return 2.0 * math.pi * cycle_revolutions * required_torque_nm / swept_volume_m3 / 100000.0


def mean_piston_speed_m_s(stroke_mm: float, rpm: float) -> float:
    return 2.0 * (stroke_mm / 1000.0) * rpm / 60.0


def missing_evidence_paths(values: dict[str, Any], prefix: str = "") -> list[str]:
    missing: list[str] = []
    for key, value in values.items():
        path = f"{prefix}.{key}" if prefix else key
        if value is None or value == "" or value == [] or value == {}:
            missing.append(path)
        elif isinstance(value, dict):
            missing.extend(missing_evidence_paths(value, path))
    return missing


def validate_contract(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["root: expected an object"]

    errors: list[str] = []
    required_fields = (
        "schema_version",
        "phase",
        "status",
        "units",
        "variant_id",
        "scope",
        "geometry",
        "source_evidence",
        "analysis_scenarios",
        "analysis_assumptions",
        "required_solver_and_calibration_evidence",
        "proof_gate",
        "model_policy",
        "prohibited_use",
    )
    for field in required_fields:
        if field not in payload:
            errors.append(f"root: missing {field}")

    if payload.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if payload.get("phase") != "F9":
        errors.append("phase: expected F9")
    if payload.get("status") != "documentary_target_and_algebraic_envelope_only":
        errors.append("status: must remain documentary_target_and_algebraic_envelope_only")
    if payload.get("units") != "SI":
        errors.append("units: expected SI")
    if payload.get("variant_id") != "917_30_turbo_5374":
        errors.append("variant_id: expected 917_30_turbo_5374")

    scope = payload.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope: expected an object")
    else:
        if scope.get("model_kind") != "deterministic_zero_dimensional_algebraic_requirement_envelope":
            errors.append("scope.model_kind: unexpected model kind")
        if scope.get("not_a_thermodynamic_solver") is not True:
            errors.append("scope.not_a_thermodynamic_solver: must be true")
        if scope.get("not_a_dyno_result") is not True:
            errors.append("scope.not_a_dyno_result: must be true")

    known_sources = _known_source_ids()
    geometry = payload.get("geometry")
    if not isinstance(geometry, dict):
        errors.append("geometry: expected an object")
    else:
        for field in ("cylinder_count", "strokes", "bore_mm", "stroke_mm", "documented_displacement_cm3"):
            if not _positive_number(geometry.get(field)):
                errors.append(f"geometry.{field}: expected a positive number")
        if geometry.get("cylinder_count") != 12:
            errors.append("geometry.cylinder_count: expected 12")
        if geometry.get("strokes") != 4:
            errors.append("geometry.strokes: expected a four-stroke engine")
        field_evidence = geometry.get("field_evidence")
        if not isinstance(field_evidence, dict):
            errors.append("geometry.field_evidence: expected an object")
        else:
            for field in ("cylinder_count", "bore_mm", "stroke_mm", "documented_displacement_cm3"):
                source_ids = field_evidence.get(field)
                if not isinstance(source_ids, list) or not source_ids:
                    errors.append(f"geometry.field_evidence.{field}: expected registered source ids")
                    continue
                for source_id in source_ids:
                    if source_id not in known_sources:
                        errors.append(f"geometry.field_evidence.{field}: unregistered source {source_id}")

    claims = payload.get("source_evidence")
    claim_ids: set[str] = set()
    if not isinstance(claims, list) or not claims:
        errors.append("source_evidence: expected a non-empty array")
        claims = []
    for index, claim in enumerate(claims):
        label = f"source_evidence[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{label}: expected an object")
            continue
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id:
            errors.append(f"{label}.claim_id: expected text")
        elif claim_id in claim_ids:
            errors.append(f"{label}.claim_id: duplicate {claim_id}")
        else:
            claim_ids.add(claim_id)
        if claim.get("source_id") not in known_sources:
            errors.append(f"{label}.source_id: source is not registered")
        if not _positive_number(claim.get("power_value")) or claim.get("power_unit") not in POWER_TO_W:
            errors.append(f"{label}: invalid power value or unit")
        if claim.get("calibration_role") != "documentary_only":
            errors.append(f"{label}.calibration_role: must remain documentary_only")
        if claim.get("used_for_calibration") is not False:
            errors.append(f"{label}.used_for_calibration: must remain false")

    scenarios = payload.get("analysis_scenarios")
    if not isinstance(scenarios, dict):
        errors.append("analysis_scenarios: expected an object")
    else:
        for scenario_role in ("primary", "alternative_unit_sensitivity"):
            scenario = scenarios.get(scenario_role)
            label = f"analysis_scenarios.{scenario_role}"
            if not isinstance(scenario, dict):
                errors.append(f"{label}: expected an object")
                continue
            if not _positive_number(scenario.get("power_value")) or scenario.get("power_unit") not in POWER_TO_W:
                errors.append(f"{label}: invalid power value or unit")
            if scenario.get("proof_status") != "not_proven":
                errors.append(f"{label}.proof_status: must remain not_proven")
            related_claim_id = scenario.get("related_claim_id")
            if related_claim_id is not None and related_claim_id not in claim_ids:
                errors.append(f"{label}.related_claim_id: unknown claim")
        primary = scenarios.get("primary", {})
        if isinstance(primary, dict) and primary.get("power_unit") != "hp":
            errors.append("analysis_scenarios.primary.power_unit: expected mechanical hp")
        alternative = scenarios.get("alternative_unit_sensitivity", {})
        if isinstance(alternative, dict) and alternative.get("power_unit") != "PS":
            errors.append("analysis_scenarios.alternative_unit_sensitivity.power_unit: expected metric PS")

    assumptions = payload.get("analysis_assumptions")
    if not isinstance(assumptions, dict):
        errors.append("analysis_assumptions: expected an object")
    else:
        rpm_grid = assumptions.get("rpm_grid")
        if not isinstance(rpm_grid, list) or not rpm_grid or any(not _positive_number(rpm) for rpm in rpm_grid):
            errors.append("analysis_assumptions.rpm_grid: expected positive evaluation points")
        elif rpm_grid != sorted(set(rpm_grid)):
            errors.append("analysis_assumptions.rpm_grid: expected sorted unique points")
        if assumptions.get("operating_range_claimed") is not False:
            errors.append("analysis_assumptions.operating_range_claimed: must remain false")
        if assumptions.get("constant_power_curve_claimed") is not False:
            errors.append("analysis_assumptions.constant_power_curve_claimed: must remain false")
        if assumptions.get("points_are_independent_candidate_requirements") is not True:
            errors.append("analysis_assumptions.points_are_independent_candidate_requirements: must be true")

    required_evidence = payload.get("required_solver_and_calibration_evidence")
    if not isinstance(required_evidence, dict) or not required_evidence:
        errors.append("required_solver_and_calibration_evidence: expected an object")

    proof_gate = payload.get("proof_gate")
    if not isinstance(proof_gate, dict):
        errors.append("proof_gate: expected an object")
    else:
        for flag in REQUIRED_PROOF_FLAGS:
            if proof_gate.get(flag) is not False:
                errors.append(f"proof_gate.{flag}: must remain false in F9")

    model_policy = payload.get("model_policy")
    if not isinstance(model_policy, dict):
        errors.append("model_policy: expected an object")
    else:
        for flag in REQUIRED_FALSE_MODEL_POLICIES:
            if model_policy.get(flag) is not False:
                errors.append(f"model_policy.{flag}: must remain false in F9")
        physicsnemo_role = model_policy.get("physicsnemo_role")
        if not isinstance(physicsnemo_role, str) or "surrogate_only_after" not in physicsnemo_role:
            errors.append("model_policy.physicsnemo_role: expected a post-validation surrogate role")

    prohibited_use = payload.get("prohibited_use")
    required_prohibitions = {
        "claim_that_1600_ch_has_been_simulated_or_proven",
        "claim_that_1600_hp_has_been_simulated_or_proven",
        "claim_that_1600_ps_has_been_simulated_or_proven",
    }
    if not isinstance(prohibited_use, list) or not required_prohibitions <= set(prohibited_use):
        errors.append("prohibited_use: missing explicit 1600 ch, hp or PS proof prohibition")
    return errors


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _normalized_documentary_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for claim in claims:
        watts = power_w(claim["power_value"], claim["power_unit"])
        normalized.append(
            {
                "claim_id": claim["claim_id"],
                "source_id": claim["source_id"],
                "reported_power_value": claim["power_value"],
                "reported_power_unit": claim["power_unit"],
                "normalized_power_kw": round(watts / 1000.0, 6),
                "qualifier": claim["qualifier"],
                "rpm": claim["rpm"],
                "test_conditions": claim["test_conditions"],
                "calibration_role": claim["calibration_role"],
                "used_for_calibration": claim["used_for_calibration"],
            }
        )
    return normalized


def _scenario_envelope(
    scenario_role: str,
    scenario: dict[str, Any],
    rpm_grid: list[float],
    swept_volume_m3: float,
    stroke_mm: float,
    strokes: int,
) -> dict[str, Any]:
    target_w = power_w(scenario["power_value"], scenario["power_unit"])
    points: list[dict[str, Any]] = []
    for rpm in rpm_grid:
        required_torque = torque_nm(target_w, rpm)
        points.append(
            {
                "rpm": rpm,
                "target_power_kw": round(target_w / 1000.0, 6),
                "required_torque_nm": round(required_torque, 6),
                "required_bmep_bar": round(bmep_bar(required_torque, swept_volume_m3, strokes), 6),
                "mean_piston_speed_m_s": round(mean_piston_speed_m_s(stroke_mm, rpm), 6),
            }
        )
    return {
        "scenario_role": scenario_role,
        "scenario": scenario,
        "normalized_target_power_kw": round(target_w / 1000.0, 6),
        "points_are_independent_candidate_requirements": True,
        "envelope": points,
    }


def build_report(payload: dict[str, Any], source_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    geometry = payload["geometry"]
    swept_volume_m3 = displacement_m3(
        geometry["bore_mm"],
        geometry["stroke_mm"],
        geometry["cylinder_count"],
    )
    calculated_cm3 = swept_volume_m3 * 1_000_000.0
    documented_cm3 = geometry["documented_displacement_cm3"]
    missing_evidence = missing_evidence_paths(payload["required_solver_and_calibration_evidence"])
    scenarios = payload["analysis_scenarios"]
    rpm_grid = payload["analysis_assumptions"]["rpm_grid"]
    scenario_envelopes = [
        _scenario_envelope(
            scenario_role,
            scenarios[scenario_role],
            rpm_grid,
            swept_volume_m3,
            geometry["stroke_mm"],
            geometry["strokes"],
        )
        for scenario_role in ("primary", "alternative_unit_sensitivity")
    ]
    primary_kw = scenario_envelopes[0]["normalized_target_power_kw"]
    alternative_kw = scenario_envelopes[1]["normalized_target_power_kw"]

    return {
        "$comment": "Enveloppes de besoins algébriques F9. Aucun résultat de solveur, de calibration ou de banc n'est produit.",
        "schema_version": "1.0.0",
        "phase": "F9",
        "status": "envelopes_generated_performance_proof_blocked",
        "generated_from": _display_path(source_path),
        "variant_id": payload["variant_id"],
        "evidence_separation": {
            "source_evidence": payload["source_evidence"],
            "documentary_power_normalization": _normalized_documentary_claims(payload["source_evidence"]),
            "analysis_scenarios": payload["analysis_scenarios"],
            "analysis_assumptions": payload["analysis_assumptions"],
        },
        "geometry": {
            "cylinder_count": geometry["cylinder_count"],
            "strokes": geometry["strokes"],
            "bore_mm": geometry["bore_mm"],
            "stroke_mm": geometry["stroke_mm"],
            "documented_displacement_cm3": documented_cm3,
            "calculated_displacement_cm3": round(calculated_cm3, 6),
            "calculated_displacement_m3": round(swept_volume_m3, 12),
            "difference_from_documented_cm3": round(calculated_cm3 - documented_cm3, 6),
            "field_evidence": geometry["field_evidence"],
        },
        "model": {
            "kind": payload["scope"]["model_kind"],
            "algebraic_envelope_model_executed": True,
            "thermodynamic_solver_executed": False,
            "calibration_executed": False,
            "held_out_validation_executed": False,
            "physical_dyno_test_executed": False,
            "performance_proven": False,
            "constants": {
                "mechanical_hp_to_w": POWER_TO_W["hp"],
                "metric_ps_to_w": POWER_TO_W["PS"],
            },
            "equations": {
                "displacement": "pi/4 * bore_m^2 * stroke_m * cylinder_count",
                "torque": "power_w * 60 / (2*pi*rpm)",
                "four_stroke_bmep": "4*pi*torque_nm / displacement_m3",
                "mean_piston_speed": "2*stroke_m*rpm / 60",
            },
        },
        "unit_sensitivity": {
            "primary_1600_hp_kw": primary_kw,
            "alternative_1600_ps_kw": alternative_kw,
            "difference_kw": round(primary_kw - alternative_kw, 6),
            "difference_percent_relative_to_primary": round((primary_kw - alternative_kw) / primary_kw * 100.0, 6),
            "note": "Les enveloppes hp et PS sont calculées séparément et ne représentent pas deux mesures moteur.",
        },
        "scenario_envelopes": scenario_envelopes,
        "proof_gate": {
            "status": "blocked_missing_solver_and_calibration_evidence",
            "missing_evidence_count": len(missing_evidence),
            "missing_evidence": missing_evidence,
            **payload["proof_gate"],
        },
        "not_calculated_quantities": [
            "air_mass_flow_kg_s",
            "fuel_mass_flow_kg_s",
            "boost_pressure_pa",
            "compressor_outlet_temperature_k",
            "turbine_inlet_temperature_k",
            "turbo_shaft_speed_rpm",
            "brake_specific_fuel_consumption",
            "thermal_or_mechanical_durability",
        ],
        "model_policy": payload["model_policy"],
        "prohibited_use": payload["prohibited_use"],
    }


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(arguments)

    try:
        payload = json.loads(args.config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"917-performance-f9: cannot read {args.config}: {exc}")

    errors = validate_contract(payload)
    if errors:
        raise SystemExit("917-performance-f9: invalid contract\n" + "\n".join(f"  - {error}" for error in errors))

    report = build_report(payload, args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"OK   {_display_path(args.config)} "
        f"({len(report['scenario_envelopes'])} separate envelopes; performance proof blocked)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
