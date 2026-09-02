#!/usr/bin/env python3
"""Run the sourced F14-001A algebraic mechanical benchmark for the 917."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "twins/reference-917-engine/mechanical-benchmark-f14.json"

EXPECTED_CASES = {
    "CASE-917-F14-001A-5L-NA": {
        "variant": "type_912_5_0_na",
        "fact_refs": {
            "cylinder_count": "FACT-CYLINDER-COUNT",
            "bore": "FACT-50-BORE",
            "stroke": "FACT-50-STROKE",
            "published_displacement": "FACT-50-DISPLACEMENT",
            "reported_power": "FACT-NA-POWER",
            "reported_power_speed": "FACT-50-RATED-SPEED",
        },
        "pair_source_refs": {"SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS"},
    },
    "CASE-917-F14-001A-5374-TURBO-1973": {
        "variant": "917_30_1973_turbo_5374",
        "fact_refs": {
            "cylinder_count": "FACT-CYLINDER-COUNT-91730-1973",
            "bore": "FACT-5374-BORE",
            "stroke": "FACT-5374-STROKE",
            "published_displacement": "FACT-5374-DISPLACEMENT",
            "reported_power": "FACT-TURBO-POWER-1100",
            "reported_power_speed": "FACT-5374-RATED-SPEED",
        },
        "pair_source_refs": {
            "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS",
            "SRC-PORSCHE-NEWSROOM-91730-AM-LIMIT",
        },
    },
}

EXPECTED_FIELDS = {
    "cylinder_count": ("cylinder_count", "count"),
    "bore": ("cylinder_bore", "mm"),
    "stroke": ("piston_stroke", "mm"),
    "published_displacement": ("engine_displacement", "cm3"),
    "reported_power": ("reported_engine_power", "PS"),
    "reported_power_speed": ("reported_power_speed", "rpm"),
}

REQUIRED_FALSE_AUTHORITY_FLAGS = (
    "thermodynamic_solver_execution_authorized",
    "combustion_simulation_authorized",
    "turbo_simulation_authorized",
    "physicsnemo_training_authorized",
    "performance_claim_authorized",
    "fabrication_authorized",
    "engine_start_authorized",
)

REQUIRED_PROHIBITIONS = {
    "claim_that_a_thermodynamic_or_combustion_solver_ran",
    "claim_that_turbo_airflow_boost_or_efficiency_was_computed",
    "claim_that_630_PS_or_1100_PS_was_reproduced_or_proven",
    "claim_that_1600_hp_was_computed_simulated_or_proven",
    "interpolate_or_extrapolate_a_power_or_torque_curve",
    "use_as_physicsnemo_training_data",
    "engine_hardware_or_manufacturing_release",
    "physical_engine_start_or_dyno_release",
}


def _positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path, project_root: Path = ROOT) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path.resolve())


def _index_by_id(values: Any, field: str) -> dict[str, dict[str, Any]]:
    if not isinstance(values, list):
        return {}
    return {
        item[field]: item
        for item in values
        if isinstance(item, dict) and isinstance(item.get(field), str)
    }


def validate_contract(
    payload: Any,
    registry: Any,
    project_root: Path = ROOT,
) -> list[str]:
    """Validate that the benchmark resolves only the two approved source pairs."""

    if not isinstance(payload, dict):
        return ["root: expected an object"]
    if not isinstance(registry, dict):
        return ["fact_registry: expected an object"]

    errors: list[str] = []
    if payload.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    if payload.get("phase") != "F14-001A":
        errors.append("phase: expected F14-001A")
    if payload.get("status") != "sourced_algebraic_mechanical_benchmark_only":
        errors.append("status: must remain sourced_algebraic_mechanical_benchmark_only")
    if payload.get("fact_registry_path") != "twins/reference-917-engine/classical-solver-cases-f13.json":
        errors.append("fact_registry_path: unexpected source registry")

    authority = payload.get("authority_boundary")
    if not isinstance(authority, dict):
        errors.append("authority_boundary: expected an object")
    else:
        if authority.get("algebraic_benchmark_execution_authorized") is not True:
            errors.append("authority_boundary.algebraic_benchmark_execution_authorized: expected true")
        for flag in REQUIRED_FALSE_AUTHORITY_FLAGS:
            if authority.get(flag) is not False:
                errors.append(f"authority_boundary.{flag}: must remain false")

    conversions = payload.get("power_unit_conversions")
    if not isinstance(conversions, dict):
        errors.append("power_unit_conversions: expected an object")
    else:
        if conversions.get("PS_to_W") != 735.49875:
            errors.append("power_unit_conversions.PS_to_W: unexpected definition")
        if conversions.get("hp_to_W") != 745.6998715822702:
            errors.append("power_unit_conversions.hp_to_W: unexpected definition")
        if conversions.get("role") != "unit_definition_not_engine_input":
            errors.append("power_unit_conversions.role: unexpected role")

    facts = _index_by_id(registry.get("fact_registry"), "id")
    sources = _index_by_id(registry.get("source_registry"), "source_id")
    if not facts:
        errors.append("fact_registry.fact_registry: expected sourced facts")
    if not sources:
        errors.append("fact_registry.source_registry: expected registered sources")

    cases = payload.get("cases")
    if not isinstance(cases, list):
        errors.append("cases: expected an array")
        cases = []
    case_ids = [item.get("id") for item in cases if isinstance(item, dict)]
    if len(cases) != len(EXPECTED_CASES) or set(case_ids) != set(EXPECTED_CASES):
        errors.append("cases: expected exactly the sourced 5.0L NA and 5.374L turbo 1973 cases")

    for index, case in enumerate(cases):
        label = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{label}: expected an object")
            continue
        case_id = case.get("id")
        expected = EXPECTED_CASES.get(case_id)
        if expected is None:
            errors.append(f"{label}.id: unauthorized case {case_id}")
            continue
        if case.get("variant") != expected["variant"]:
            errors.append(f"{label}.variant: does not match {case_id}")
        if case.get("fact_refs") != expected["fact_refs"]:
            errors.append(f"{label}.fact_refs: must match the approved F13 facts")
            continue
        if case.get("role") != "documentary_mechanical_consistency_anchor":
            errors.append(f"{label}.role: unexpected role")
        if case.get("claim_status") != "not_a_dyno_measurement_not_a_prediction":
            errors.append(f"{label}.claim_status: must remain fail-closed")

        resolved: dict[str, dict[str, Any]] = {}
        for field_name, fact_ref in case["fact_refs"].items():
            fact = facts.get(fact_ref)
            field_label = f"{label}.fact_refs.{field_name}"
            if fact is None:
                errors.append(f"{field_label}: unknown fact {fact_ref}")
                continue
            resolved[field_name] = fact
            expected_quantity, expected_unit = EXPECTED_FIELDS[field_name]
            candidate = fact.get("candidate")
            if not isinstance(candidate, dict):
                errors.append(f"{field_label}: fact has no candidate object")
                continue
            if fact.get("quantity") != expected_quantity:
                errors.append(f"{field_label}: expected quantity {expected_quantity}")
            if candidate.get("unit") != expected_unit:
                errors.append(f"{field_label}: expected unit {expected_unit}")
            if not _positive_number(candidate.get("value")):
                errors.append(f"{field_label}: expected a positive published value")
            if fact.get("design_lock") is not False:
                errors.append(f"{field_label}: fact must remain an unlocked candidate")
            source_refs = fact.get("source_refs")
            if not isinstance(source_refs, list) or not source_refs:
                errors.append(f"{field_label}: fact must retain source references")
            else:
                for source_ref in source_refs:
                    if source_ref not in sources:
                        errors.append(f"{field_label}: unregistered source {source_ref}")

        pair_source_refs = case.get("power_speed_pair_source_refs")
        if not isinstance(pair_source_refs, list) or not pair_source_refs:
            errors.append(f"{label}.power_speed_pair_source_refs: expected common sources")
        elif set(pair_source_refs) != expected["pair_source_refs"]:
            errors.append(f"{label}.power_speed_pair_source_refs: unexpected pair provenance")
        elif "reported_power" in resolved and "reported_power_speed" in resolved:
            common_sources = set(resolved["reported_power"].get("source_refs", [])) & set(
                resolved["reported_power_speed"].get("source_refs", [])
            )
            if not set(pair_source_refs) <= common_sources:
                errors.append(f"{label}.power_speed_pair_source_refs: not common to power and speed facts")

    claims = payload.get("documentary_uncomputed_claims")
    if not isinstance(claims, list) or len(claims) != 1 or not isinstance(claims[0], dict):
        errors.append("documentary_uncomputed_claims: expected exactly the reported 1600 hp claim")
    else:
        claim = claims[0]
        if claim.get("id") != "CLAIM-917-F14-1600-HP-REPORTED":
            errors.append("documentary_uncomputed_claims[0].id: unexpected claim")
        if claim.get("reported_power_fact_ref") != "FACT-TURBO-POWER-1600-REPORTED":
            errors.append("documentary_uncomputed_claims[0].reported_power_fact_ref: unexpected fact")
        power_fact = facts.get(claim.get("reported_power_fact_ref"))
        if power_fact is None:
            errors.append("documentary_uncomputed_claims[0]: missing registered 1600 hp fact")
        else:
            candidate = power_fact.get("candidate", {})
            if candidate.get("value") != 1600.0 or candidate.get("unit") != "hp":
                errors.append("documentary_uncomputed_claims[0]: expected the registered 1600 hp wording")
            if power_fact.get("usage") != "documentary_claim_not_calibration_target":
                errors.append("documentary_uncomputed_claims[0]: power fact must remain documentary only")
        if claim.get("reported_power_speed_fact_ref") is not None:
            errors.append("documentary_uncomputed_claims[0].reported_power_speed_fact_ref: must remain null")
        if claim.get("reported_power_speed_rpm") is not None:
            errors.append("documentary_uncomputed_claims[0].reported_power_speed_rpm: must remain null")
        if claim.get("derived_mechanical_quantities") is not None:
            errors.append("documentary_uncomputed_claims[0].derived_mechanical_quantities: must remain null")
        if claim.get("proof_status") != "not_proven":
            errors.append("documentary_uncomputed_claims[0].proof_status: must remain not_proven")
        if not isinstance(claim.get("status"), str) or not claim["status"].startswith("blocked_missing_"):
            errors.append("documentary_uncomputed_claims[0].status: must remain blocked")

    output = payload.get("output")
    if not isinstance(output, dict):
        errors.append("output: expected an object")
    else:
        if output.get("tracked") is not False:
            errors.append("output.tracked: work result must remain untracked")
        if output.get("dataset_role") != "two_documentary_anchors_only_not_training_data":
            errors.append("output.dataset_role: must not authorize training")

    prohibited = payload.get("prohibited_use")
    if not isinstance(prohibited, list) or not REQUIRED_PROHIBITIONS <= set(prohibited):
        errors.append("prohibited_use: missing fail-closed claim limits")

    for source_id, source in sources.items():
        catalog_path = source.get("catalog_path")
        if not isinstance(catalog_path, str):
            errors.append(f"source_registry.{source_id}: missing catalog_path")
            continue
        path = project_root / catalog_path
        if not path.is_file():
            errors.append(f"source_registry.{source_id}: missing catalog record {catalog_path}")
            continue
        try:
            catalog_record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            errors.append(f"source_registry.{source_id}: unreadable catalog record {catalog_path}")
            continue
        if catalog_record.get("source_id") != source_id:
            errors.append(f"source_registry.{source_id}: catalog source id mismatch")

    return errors


def _fact_field(fact: dict[str, Any]) -> dict[str, Any]:
    candidate = fact["candidate"]
    return {
        "value": candidate["value"],
        "unit": candidate["unit"],
        "fact_ref": fact["id"],
        "fact_variant": fact["variant"],
        "source_refs": fact["source_refs"],
        "usage": fact["usage"],
        "design_lock": fact["design_lock"],
    }


def _round(value: float) -> float:
    return round(float(value), 12)


def _build_case(
    case: dict[str, Any],
    facts: dict[str, dict[str, Any]],
    conversions: dict[str, Any],
) -> dict[str, Any]:
    resolved = {
        field_name: _fact_field(facts[fact_ref])
        for field_name, fact_ref in case["fact_refs"].items()
    }
    cylinder_count = int(resolved["cylinder_count"]["value"])
    bore_m = float(resolved["bore"]["value"]) / 1000.0
    stroke_m = float(resolved["stroke"]["value"]) / 1000.0
    published_displacement_m3 = float(resolved["published_displacement"]["value"]) * 1e-6
    calculated_displacement_m3 = math.pi / 4.0 * bore_m**2 * stroke_m * cylinder_count
    displacement_difference_m3 = calculated_displacement_m3 - published_displacement_m3
    displacement_relative_difference = displacement_difference_m3 / published_displacement_m3

    reported_power = float(resolved["reported_power"]["value"])
    reported_power_w = reported_power * float(conversions["PS_to_W"])
    reported_power_speed_rpm = float(resolved["reported_power_speed"]["value"])
    angular_speed_rad_s = 2.0 * math.pi * reported_power_speed_rpm / 60.0
    torque_nm = reported_power_w / angular_speed_rad_s
    bmep_published_pa = 4.0 * math.pi * torque_nm / published_displacement_m3
    bmep_calculated_pa = 4.0 * math.pi * torque_nm / calculated_displacement_m3
    mean_piston_speed_m_s = 2.0 * stroke_m * reported_power_speed_rpm / 60.0

    return {
        "id": case["id"],
        "variant": case["variant"],
        "label": case["label"],
        "status": "computed_documentary_algebra_only",
        "resolved_inputs": resolved,
        "power_speed_pair_provenance": {
            "source_refs": case["power_speed_pair_source_refs"],
            "role": case["role"],
            "claim_status": case["claim_status"],
        },
        "derived": {
            "calculated_displacement_m3": _round(calculated_displacement_m3),
            "calculated_displacement_cm3": _round(calculated_displacement_m3 * 1e6),
            "published_displacement_m3": _round(published_displacement_m3),
            "displacement_difference_cm3": _round(displacement_difference_m3 * 1e6),
            "displacement_relative_difference": _round(displacement_relative_difference),
            "displacement_relative_difference_percent": _round(
                displacement_relative_difference * 100.0
            ),
            "reported_power_w": _round(reported_power_w),
            "reported_power_kw": _round(reported_power_w / 1000.0),
            "angular_speed_rad_s": _round(angular_speed_rad_s),
            "torque_nm": _round(torque_nm),
            "four_stroke_bmep_using_published_displacement_pa": _round(
                bmep_published_pa
            ),
            "four_stroke_bmep_using_published_displacement_bar": _round(
                bmep_published_pa / 1e5
            ),
            "four_stroke_bmep_using_calculated_displacement_pa": _round(
                bmep_calculated_pa
            ),
            "four_stroke_bmep_using_calculated_displacement_bar": _round(
                bmep_calculated_pa / 1e5
            ),
            "mean_piston_speed_m_s": _round(mean_piston_speed_m_s),
        },
        "claim_limits": {
            "power_predicted": False,
            "power_reproduced": False,
            "thermodynamic_cycle_simulated": False,
            "turbo_simulated": False,
            "dyno_correlation_complete": False,
        },
    }


def build_report(
    payload: dict[str, Any],
    registry: dict[str, Any],
    config_path: Path = DEFAULT_CONFIG,
    registry_path: Path | None = None,
    project_root: Path = ROOT,
) -> dict[str, Any]:
    errors = validate_contract(payload, registry, project_root)
    if errors:
        raise ValueError("invalid F14-001A contract:\n" + "\n".join(f"- {error}" for error in errors))

    if registry_path is None:
        registry_path = project_root / payload["fact_registry_path"]
    facts = _index_by_id(registry["fact_registry"], "id")
    claim = payload["documentary_uncomputed_claims"][0]
    reported_power_fact = facts[claim["reported_power_fact_ref"]]
    uncomputed_fields = {
        "angular_speed_rad_s": None,
        "torque_nm": None,
        "four_stroke_bmep_pa": None,
        "mean_piston_speed_m_s": None,
    }

    return {
        "$comment": "Sortie F14-001A: identites algebriques sourcées, sans simulation thermodynamique, turbo ou preuve de puissance.",
        "schema_version": "1.0.0",
        "phase": payload["phase"],
        "status": "passed_sourced_algebraic_benchmark_not_physics_simulation",
        "generated_from": {
            "contract_path": _display_path(config_path, project_root),
            "contract_sha256": _sha256(config_path),
            "fact_registry_path": _display_path(registry_path, project_root),
            "fact_registry_sha256": _sha256(registry_path),
        },
        "model": {
            "kind": "deterministic_closed_form_mechanical_consistency_benchmark",
            "algebraic_benchmark_executed": True,
            "thermodynamic_solver_executed": False,
            "combustion_simulated": False,
            "turbo_simulated": False,
            "curve_fit_or_interpolation_executed": False,
            "generic_engine_defaults_used": False,
        },
        "cases": [
            _build_case(case, facts, payload["power_unit_conversions"])
            for case in payload["cases"]
        ],
        "documentary_uncomputed_claims": [
            {
                "id": claim["id"],
                "variant": claim["variant"],
                "reported_power": _fact_field(reported_power_fact),
                "reported_power_speed_rpm": None,
                "status": claim["status"],
                "missing_required_evidence": [
                    "reported_power_speed_rpm",
                    "test_conditions",
                    "measurement_basis_and_correction_standard",
                    "measurement_uncertainty",
                    "validated_thermodynamic_and_turbo_inputs",
                ],
                "derived_mechanical_quantities": uncomputed_fields,
                "proof_status": "not_proven",
            }
        ],
        "physicsnemo_dataset_gate": {
            "dataset_ready": False,
            "training_authorized": False,
            "reason": "Deux points documentaires ne constituent ni un DOE solveur, ni un dataset correle.",
        },
        "release_gates": {
            "performance_claim_authorized": False,
            "dyno_correlation_complete": False,
            "engine_simulation_validated": False,
            "fabrication_authorized": False,
            "engine_start_authorized": False,
        },
        "prohibited_use": payload["prohibited_use"],
    }


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(arguments)

    project_root = args.project_root.resolve()
    config_path = args.config.resolve()
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"F14-001A: cannot read contract: {exc}")
    registry_path = (
        args.registry.resolve()
        if args.registry is not None
        else (project_root / payload.get("fact_registry_path", "")).resolve()
    )
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"F14-001A: cannot read fact registry: {exc}")

    errors = validate_contract(payload, registry, project_root)
    if errors:
        raise SystemExit("F14-001A: invalid contract\n" + "\n".join(f"  - {error}" for error in errors))
    output_path = (
        args.output.resolve()
        if args.output is not None
        else (project_root / payload["output"]["default_path"]).resolve()
    )
    report = build_report(
        payload,
        registry,
        config_path=config_path,
        registry_path=registry_path,
        project_root=project_root,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"F14-001A OK: {len(report['cases'])} sourced mechanical anchors; "
        f"1600 hp remains uncomputed; output={_display_path(output_path, project_root)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
