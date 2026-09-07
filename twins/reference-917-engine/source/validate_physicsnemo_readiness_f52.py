#!/usr/bin/env python3
"""Valide la porte PhysicsNeMo F52 sans lancer de modèle ni modifier la CAO."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
OCI_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
EXPECTED_MODELS = {"DoMINO_CFD_CHT": "DoMINO", "GeoTransolver_thermomechanical": "GeoTransolver"}
REQUIRED_GROUP_KEYS = {
    "geometry_family_id",
    "operating_regime_family_id",
    "solver_campaign_id",
    "physical_test_campaign_id",
}
REQUIRED_FALSE_GATES = {
    "DoMINO_dataset_ready",
    "GeoTransolver_dataset_ready",
    "split_manifest_locked",
    "gpu_model_runtime_verified",
    "physicsnemo_training_authorized",
    "physicsnemo_model_trained",
    "holdout_metrics_passed",
    "UQ_calibration_passed",
    "OOD_abstention_passed",
    "reference_solver_replaced",
    "physical_validation_replaced",
    "manufacturing_authorized",
    "metal_print_authorized",
    "engine_start_authorized",
}
REQUIRED_RELEASE_GATES = REQUIRED_FALSE_GATES | {"all_declared_input_hashes_verified"}
F50_AUDIT_KEYS = {
    "source_schema",
    "source_status",
    "declared_cases",
    "executed_cases_with_solver_receipt",
    "flow_numerical_gate_pass_cases",
    "flow_numerical_gate_fail_cases",
    "energy_gate_applicable_cases",
    "energy_gate_pass_cases",
    "case_validation_gate_pass_cases",
    "energy_equation_solved",
    "conjugate_CHT_executed",
    "all_flow_gates_passed",
    "all_energy_gates_passed",
    "validation_claim",
    "accepted_training_samples",
    "training_blocker",
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"objet JSON attendu: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_path(root: Path, relative: Any) -> Path | None:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        return None
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _audit_f50_cfd_recovery(report: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Recalcule les compteurs F50 depuis les 12 cas, sans croire le résumé."""

    errors: list[str] = []
    if report.get("schema_version") != "porsche-917-f50-cfd-recovery-public/v1":
        errors.append("f50_source_schema_invalid")
    if report.get("status") != "CFD_RECOVERY_FAIL_CLOSED":
        errors.append("f50_source_status_invalid")
    if report.get("validation_claim") is not False:
        errors.append("f50_validation_claim_must_be_false")

    case_index = report.get("case_index")
    if not isinstance(case_index, dict):
        case_index = {}
        errors.append("f50_case_index_invalid")
    expected_ids = {
        f"{variant.lower()}-{level}-{screen}"
        for variant in ("2V", "4V")
        for level in ("coarse", "medium", "fine")
        for screen in ("intake", "exhaust")
    }
    if set(case_index) != expected_ids:
        errors.append("f50_case_matrix_invalid")
    if report.get("case_count") != 12:
        errors.append("f50_declared_case_count_invalid")

    executed = 0
    flow_pass = 0
    energy_applicable = 0
    energy_pass = 0
    validation_pass = 0
    for case_id in sorted(expected_ids):
        case = case_index.get(case_id)
        if not isinstance(case, dict):
            errors.append(f"f50_case_missing:{case_id}")
            continue
        if case.get("case_id") != case_id:
            errors.append(f"f50_case_id_mismatch:{case_id}")
        for key in ("flow_numerical_gate_pass", "energy_gate_applicable", "case_validation_gate_pass"):
            if not isinstance(case.get(key), bool):
                errors.append(f"f50_case_boolean_invalid:{case_id}:{key}")
        gates = case.get("gates")
        if not isinstance(gates, dict) or not isinstance(gates.get("energy"), bool):
            errors.append(f"f50_case_energy_gate_invalid:{case_id}")
            gates = {}
        solver_step = case.get("solver_step")
        receipt_ok = (
            case.get("execution_status") == "EXECUTED"
            and isinstance(solver_step, dict)
            and solver_step.get("return_code") == 0
            and isinstance(solver_step.get("elapsed_s"), (int, float))
            and not isinstance(solver_step.get("elapsed_s"), bool)
            and solver_step.get("elapsed_s", 0) > 0
            and SHA256_RE.fullmatch(str(solver_step.get("log_sha256", ""))) is not None
        )
        if receipt_ok:
            executed += 1
        else:
            errors.append(f"f50_execution_receipt_invalid:{case_id}")
        flow_pass += case.get("flow_numerical_gate_pass") is True
        energy_applicable += case.get("energy_gate_applicable") is True
        energy_pass += gates.get("energy") is True
        validation_pass += case.get("case_validation_gate_pass") is True
        values = case.get("values")
        if not isinstance(values, dict) or values.get("energy_balance") is not None:
            errors.append(f"f50_energy_balance_must_be_unavailable:{case_id}")
        if case.get("validation_claim") is not False:
            errors.append(f"f50_case_validation_claim_must_be_false:{case_id}")

    if executed != 12:
        errors.append("f50_executed_case_count_not_12")
    if flow_pass != 7:
        errors.append("f50_flow_pass_count_not_7")
    if energy_applicable != 0:
        errors.append("f50_energy_applicable_count_not_0")
    if energy_pass != 0:
        errors.append("f50_energy_pass_count_not_0")
    if validation_pass != 0:
        errors.append("f50_case_validation_pass_count_not_0")

    method = report.get("method", {})
    gates = report.get("gates", {})
    if not isinstance(method, dict):
        method = {}
        errors.append("f50_method_schema_invalid")
    if not isinstance(gates, dict):
        gates = {}
        errors.append("f50_gates_schema_invalid")
    if method.get("energy_equation_solved") is not False:
        errors.append("f50_energy_equation_claim_invalid")
    for key in (
        "all_12_flow_numerical_gates_pass",
        "conjugate_CHT_executed",
        "cross_method_agreement_below_5_percent",
        "energy_balance_below_1_percent",
    ):
        if gates.get(key) is not False:
            errors.append(f"f50_aggregate_gate_must_be_false:{key}")

    summary = {
        "source_schema": report.get("schema_version"),
        "source_status": report.get("status"),
        "declared_cases": report.get("case_count"),
        "executed_cases_with_solver_receipt": executed,
        "flow_numerical_gate_pass_cases": flow_pass,
        "flow_numerical_gate_fail_cases": len(case_index) - flow_pass,
        "energy_gate_applicable_cases": energy_applicable,
        "energy_gate_pass_cases": energy_pass,
        "case_validation_gate_pass_cases": validation_pass,
        "energy_equation_solved": method.get("energy_equation_solved"),
        "conjugate_CHT_executed": gates.get("conjugate_CHT_executed"),
        "all_flow_gates_passed": gates.get("all_12_flow_numerical_gates_pass"),
        "all_energy_gates_passed": gates.get("energy_balance_below_1_percent"),
        "validation_claim": report.get("validation_claim"),
        "accepted_training_samples": 0,
        "training_blocker": "energy_and_CHT_are_required_by_the_DoMINO_lane_but_absent",
    }
    return summary, errors


def validate(root: Path, contract_path: Path, evidence_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    contract = _read_json(contract_path)
    evidence = _read_json(evidence_path)

    if contract.get("schema") != "porsche-917-physicsnemo-readiness-f52/v1":
        errors.append("contract_schema_invalid")
    if contract.get("phase") != "F52":
        errors.append("contract_phase_invalid")
    if evidence.get("schema") != "porsche-917-physicsnemo-readiness-f52-public/v1":
        errors.append("evidence_schema_invalid")
    if evidence.get("audit_status") != "PASS_FAIL_CLOSED":
        errors.append("evidence_audit_status_invalid")

    geometry = contract.get("geometry_policy", {})
    if geometry.get("geometry_modified_by_F52") is not False:
        errors.append("geometry_must_not_be_modified")
    if geometry.get("private_geometry_published") is not False:
        errors.append("private_geometry_must_not_be_published")
    if set(geometry.get("source_variants", [])) != {"2V", "4V"}:
        errors.append("source_variants_invalid")
    for key in ("2V_private_native_BREP_sha256", "4V_private_native_BREP_sha256"):
        if not SHA256_RE.fullmatch(str(geometry.get(key, ""))):
            errors.append(f"geometry_hash_invalid:{key}")

    runtime = contract.get("runtime_pin", {})
    lock_path = _safe_path(root, runtime.get("lock_path"))
    if lock_path is None or not lock_path.is_file():
        errors.append("runtime_lock_missing_or_unsafe")
        lock: dict[str, Any] = {}
    else:
        actual_lock_sha = _sha256(lock_path)
        if runtime.get("lock_sha256") != actual_lock_sha:
            errors.append("runtime_lock_sha256_mismatch")
        lock = _read_json(lock_path)
    image = lock.get("image", {})
    lock_smoke = lock.get("verification", {}).get("offline_smoke", {})
    if runtime.get("physicsnemo_version") != "2.2.1":
        errors.append("physicsnemo_version_not_pinned")
    if runtime.get("immutable_reference") != image.get("immutable_reference"):
        errors.append("runtime_immutable_reference_mismatch")
    if not OCI_RE.fullmatch(str(image.get("digest", ""))):
        errors.append("runtime_digest_invalid")
    if lock_smoke.get("physicsnemo_version") != "2.2.1":
        errors.append("runtime_smoke_version_mismatch")
    if set(lock_smoke.get("public_model_imports", {})) != {"DoMINO", "GeoTransolver", "MeshGraphNet"}:
        errors.append("runtime_import_set_invalid")
    if lock_smoke.get("gpu_runtime", {}).get("checked") is not False:
        errors.append("runtime_lock_gpu_claim_must_remain_false")

    execution = contract.get("execution_status", {})
    expected_execution = {
        "container_smoke_executed": True,
        "physicsnemo_imports_executed": True,
        "physicsnemo_model_forward_executed": False,
        "physicsnemo_training_executed": False,
        "physicsnemo_inference_evaluation_executed": False,
        "physicsnemo_dataset_curator_executed": False,
        "physicsnemo_model_executed": False,
        "model_weights_produced": False,
    }
    for key, expected in expected_execution.items():
        if execution.get(key) is not expected:
            errors.append(f"execution_claim_invalid:{key}")
    if execution.get("interpretation") != "IMPORT_SMOKE_ONLY_NOT_MODEL_EXECUTION":
        errors.append("execution_interpretation_invalid")

    artifact_results: list[dict[str, Any]] = []
    f50_report: dict[str, Any] | None = None
    for item in contract.get("audited_inputs", []):
        if not isinstance(item, dict):
            errors.append("audited_input_not_object")
            continue
        path = _safe_path(root, item.get("path"))
        availability = item.get("availability")
        if availability == "present_hash_verified":
            if path is None or not path.is_file():
                errors.append(f"audited_input_missing:{item.get('id')}")
                actual_sha = None
            else:
                actual_sha = _sha256(path)
                if item.get("sha256") != actual_sha:
                    errors.append(f"audited_input_sha256_mismatch:{item.get('id')}")
                elif item.get("id") == "f50_steady_incompressible_CFD_recovery":
                    f50_report = _read_json(path)
            status = "HASH_VERIFIED" if actual_sha == item.get("sha256") else "FAILED"
        else:
            errors.append(f"audited_input_availability_invalid:{item.get('id')}")
            actual_sha = None
            status = "FAILED"
        if item.get("eligible_training_sample") is not False:
            errors.append(f"training_sample_must_be_rejected:{item.get('id')}")
        artifact_results.append({"id": item.get("id"), "status": status})

    if len(contract.get("audited_inputs", [])) != 8:
        errors.append("audited_input_count_invalid")
    if f50_report is None:
        f50_audit: dict[str, Any] = {}
        errors.append("f50_recovery_not_consumed")
    else:
        f50_audit, f50_errors = _audit_f50_cfd_recovery(f50_report)
        errors.extend(f50_errors)
    source_audits = contract.get("source_audits", {})
    if not isinstance(source_audits, dict) or set(source_audits) != {"f50_CFD_recovery"}:
        errors.append("source_audits_schema_invalid")
        source_audits = {}
    declared_f50_audit = source_audits.get("f50_CFD_recovery", {})
    if set(declared_f50_audit) != F50_AUDIT_KEYS:
        errors.append("f50_contract_audit_schema_invalid")
    if declared_f50_audit != f50_audit:
        errors.append("f50_contract_audit_mismatch")
    public_f50_audit = evidence.get("input_audit", {}).get("F50_CFD_recovery", {})
    if set(public_f50_audit) != F50_AUDIT_KEYS:
        errors.append("f50_public_audit_schema_invalid")
    if public_f50_audit != f50_audit:
        errors.append("f50_public_audit_mismatch")

    lanes = contract.get("model_lanes", {})
    if set(lanes) != set(EXPECTED_MODELS):
        errors.append("model_lanes_invalid")
    for lane_name, model in EXPECTED_MODELS.items():
        lane = lanes.get(lane_name, {})
        if lane.get("model") != model:
            errors.append(f"lane_model_invalid:{lane_name}")
        if lane.get("dataset_ready") is not False:
            errors.append(f"lane_dataset_ready_must_be_false:{lane_name}")
        if lane.get("training_authorized") is not False:
            errors.append(f"lane_training_authorized_must_be_false:{lane_name}")
        if not lane.get("release_requirements"):
            errors.append(f"lane_release_requirements_missing:{lane_name}")
    domino = lanes.get("DoMINO_CFD_CHT", {})
    if domino.get("current_reference_case_count") != 12:
        errors.append("domino_current_case_count_invalid")
    if domino.get("current_executed_case_count") != f50_audit.get("executed_cases_with_solver_receipt"):
        errors.append("domino_executed_case_count_invalid")
    if domino.get("current_flow_numerical_gate_pass_count") != f50_audit.get("flow_numerical_gate_pass_cases"):
        errors.append("domino_flow_pass_count_invalid")
    if domino.get("current_flow_numerical_gate_fail_count") != f50_audit.get("flow_numerical_gate_fail_cases"):
        errors.append("domino_flow_fail_count_invalid")
    if domino.get("current_energy_gate_pass_count") != f50_audit.get("energy_gate_pass_cases"):
        errors.append("domino_energy_pass_count_invalid")
    if domino.get("current_energy_equation_available") is not False:
        errors.append("domino_energy_gate_must_be_false")
    if domino.get("current_all_cases_passed") is not False:
        errors.append("domino_case_gate_must_be_false")

    split = contract.get("split_policy", {})
    fractions = split.get("fractions_after_readiness", {})
    if abs(sum(float(fractions.get(key, 0.0)) for key in ("train", "validation", "test")) - 1.0) > 1e-12:
        errors.append("split_fractions_do_not_sum_to_one")
    if set(split.get("group_keys", [])) != REQUIRED_GROUP_KEYS:
        errors.append("split_group_keys_invalid")
    for key in (
        "same_geometry_across_splits_allowed",
        "same_operating_regime_family_across_splits_allowed",
        "same_physical_test_campaign_across_splits_allowed",
        "model_selection_uses_test_split",
    ):
        if split.get(key) is not False:
            errors.append(f"split_leakage_gate_invalid:{key}")

    guardrails = contract.get("evaluation_and_guardrails", {})
    uq = guardrails.get("uncertainty_quantification", {})
    ood = guardrails.get("out_of_distribution", {})
    if uq.get("deep_ensemble_members_min", 0) < 5:
        errors.append("UQ_ensemble_too_small")
    if ood.get("OOD_detection_AUROC_min", 0.0) < 0.95:
        errors.append("OOD_AUROC_gate_too_low")
    if ood.get("hard_OOD_abstention_recall_min", 0.0) < 0.95:
        errors.append("OOD_abstention_gate_too_low")
    if ood.get("in_distribution_false_abstention_max", 1.0) > 0.05:
        errors.append("OOD_false_abstention_gate_too_high")
    required_runtime_guards = {
        "abstain_on_unknown_geometry_hash",
        "abstain_outside_declared_operating_envelope",
        "reject_mass_or_energy_conservation_violation",
        "never_override_reference_solver_or_physical_test",
        "never_issue_manufacturing_or_engine_start_release",
    }
    if not required_runtime_guards.issubset(set(guardrails.get("runtime_guardrails", []))):
        errors.append("runtime_guardrails_incomplete")

    gates = contract.get("release_gates", {})
    if set(gates) != REQUIRED_RELEASE_GATES:
        errors.append("release_gate_set_invalid")
    if gates.get("all_declared_input_hashes_verified") is not True:
        errors.append("all_declared_input_hashes_verified_must_be_true")
    for key in REQUIRED_FALSE_GATES:
        if gates.get(key) is not False:
            errors.append(f"release_gate_must_be_false:{key}")

    evidence_execution = evidence.get("execution", {})
    if evidence_execution.get("imports_only") is not True:
        errors.append("evidence_import_scope_invalid")
    for key in (
        "physicsnemo_model_executed",
        "physicsnemo_training_executed",
        "physicsnemo_inference_evaluation_executed",
        "weights_produced",
    ):
        if evidence_execution.get(key) is not False:
            errors.append(f"evidence_execution_claim_invalid:{key}")
    if evidence.get("input_audit", {}).get("eligible_training_samples") != 0:
        errors.append("evidence_eligible_sample_count_must_be_zero")
    if evidence.get("input_audit", {}).get("present_hash_verified_artifacts") != 8:
        errors.append("evidence_verified_artifact_count_must_be_eight")
    if evidence.get("input_audit", {}).get("pending_artifacts") != 0:
        errors.append("evidence_pending_artifact_count_must_be_zero")
    for value in evidence.get("release", {}).values():
        if value is not False:
            errors.append("evidence_release_gate_must_be_false")

    return {
        "schema": "porsche-917-physicsnemo-readiness-f52-validation/v1",
        "status": "PASS" if not errors else "FAIL",
        "fail_closed": True,
        "errors": errors,
        "artifact_results": artifact_results,
        "f50_CFD_recovery": f50_audit,
        "physicsnemo_execution": "IMPORT_SMOKE_ONLY_NOT_MODEL_EXECUTION",
        "accepted_training_samples": 0,
        "training_authorized": False,
        "manufacturing_authorized": False,
        "engine_start_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("twins/reference-917-engine/physicsnemo-readiness-f52.json"),
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("twins/reference-917-engine/evidence/f52-physicsnemo-readiness/physicsnemo-readiness-f52.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.project_root.resolve()
    contract = args.contract if args.contract.is_absolute() else root / args.contract
    evidence = args.evidence if args.evidence.is_absolute() else root / args.evidence
    report = validate(root, contract, evidence)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
