#!/usr/bin/env python3
"""Verifie les preuves locales F29 et produit un rapport fail-closed consolide."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]


class ValidationError(ValueError):
    """Un artefact F29 est absent, obsolete ou sur-evalue."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"missing_input:{path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid_json:{path}:{exc}") from exc
    require(isinstance(value, dict), f"expected_json_object:{path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def exact_false_gate_map(value: Any, label: str) -> None:
    require(isinstance(value, dict) and bool(value), f"{label}_missing")
    require(
        all(item is False for item in value.values()),
        f"{label}_must_contain_exact_false_booleans",
    )


def artifact_record(path: Path, role: str) -> dict[str, Any]:
    require(path.is_file() and path.stat().st_size > 0, f"missing_artifact:{path}")
    return {
        "path": str(path.relative_to(ROOT)),
        "role": role,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def validate(
    contract_path: Path,
    study_path: Path,
    geometry_report_path: Path,
    preflight_path: Path,
    handoff_path: Path,
) -> dict[str, Any]:
    contract = load_json(contract_path)
    study = load_json(study_path)
    geometry = load_json(geometry_report_path)
    preflight = load_json(preflight_path)
    handoff = load_json(handoff_path)

    require(contract.get("phase") == "F29", "contract_phase_mismatch")
    require(study.get("phase") == "F29", "study_phase_mismatch")
    require(geometry.get("phase") == "F29", "geometry_phase_mismatch")
    require(handoff.get("phase") == "F29", "handoff_phase_mismatch")
    exact_false_gate_map(contract.get("release_gates"), "contract_release_gates")
    exact_false_gate_map(study.get("release_gates"), "study_release_gates")
    exact_false_gate_map(geometry.get("release_gates"), "geometry_release_gates")
    exact_false_gate_map(handoff.get("release_gates"), "handoff_release_gates")
    require(study["contract"]["sha256"] == sha256(contract_path), "study_contract_digest_stale")
    require(geometry["inputs"]["study"]["sha256"] == sha256(study_path), "geometry_study_digest_stale")
    require(geometry["inputs"]["contract"]["sha256"] == sha256(contract_path), "geometry_contract_digest_stale")

    expected_ids = {
        "type_912_5_0_na_2v",
        "type_912_5_0_na_4v",
        "917_30_1973_turbo_5374_2v",
        "917_30_1973_turbo_5374_4v",
    }
    require(study.get("variant_count") == 4, "study_variant_count_mismatch")
    require(geometry.get("variant_count") == 4, "geometry_variant_count_mismatch")
    require({item["id"] for item in study["variants"]} == expected_ids, "study_variant_ids_mismatch")
    require({item["id"] for item in geometry["variants"]} == expected_ids, "geometry_variant_ids_mismatch")
    checks = geometry["checks"]
    require(checks["all_created_shapes_valid"] is True, "created_shapes_invalid")
    require(checks["all_created_shapes_one_closed_solid"] is True, "created_shapes_not_closed")
    require(checks["all_step_roundtrips_one_closed_solid"] is True, "step_roundtrip_not_closed")
    require(checks["scan_used"] is False, "scan_must_not_be_claimed")
    require(checks["fitment_verified"] is False, "fitment_must_remain_unverified")
    require(checks["manufacturing_verified"] is False, "manufacturing_must_remain_unverified")

    cad_dir = geometry_report_path.parent
    cad_artifacts = []
    for item in geometry["variants"]:
        step_path = cad_dir / item["step"]["path"]
        stl_path = cad_dir / item["stl"]["path"]
        require(sha256(step_path) == item["step"]["sha256"], f"step_digest_mismatch:{item['id']}")
        require(sha256(stl_path) == item["stl"]["sha256"], f"stl_digest_mismatch:{item['id']}")
        require(item["created_shape"]["solid_count"] == 1, f"created_solid_count:{item['id']}")
        require(item["reopened_step_shape"]["solid_count"] == 1, f"step_solid_count:{item['id']}")
        require(item["step_roundtrip_relative_volume_difference"] <= 1.0e-5, f"step_volume_drift:{item['id']}")
        cad_artifacts.extend(
            [
                artifact_record(step_path, "editable_neutral_cad_concept"),
                artifact_record(stl_path, "derived_mesh_not_manufacturing_release"),
            ]
        )

    require(preflight.get("status") == "blocked", "omniverse_preflight_status_not_blocked")
    require(bool(preflight.get("blockers")), "omniverse_blockers_missing")
    require(handoff["current_preflight"]["status"] == "blocked", "handoff_preflight_status_mismatch")
    remote_attempt = handoff.get("remote_execution_attempt")
    require(isinstance(remote_attempt, dict), "remote_execution_attempt_missing")
    require(
        remote_attempt.get("status") == "blocked_instance_never_ready_no_remote_job_executed",
        "remote_execution_status_mismatch",
    )
    require(remote_attempt.get("remote_ready") is False, "remote_ready_must_remain_false")
    require(remote_attempt.get("cad_transferred") is False, "remote_cad_transfer_must_remain_false")
    require(remote_attempt.get("remote_preflight_executed") is False, "remote_preflight_must_remain_false")
    require(remote_attempt.get("usd_output_count") == 0, "remote_usd_output_count_must_be_zero")
    require(remote_attempt.get("rendered_image_count") == 0, "remote_rendered_image_count_must_be_zero")
    require(remote_attempt.get("instance_destroyed") is True, "remote_instance_destruction_not_proven")
    readiness_path = ROOT / remote_attempt["readiness_evidence"]["path"]
    destruction_path = ROOT / remote_attempt["destruction_evidence"]["path"]
    require(
        sha256(readiness_path) == remote_attempt["readiness_evidence"]["sha256"],
        "remote_readiness_digest_mismatch",
    )
    require(
        sha256(destruction_path) == remote_attempt["destruction_evidence"]["sha256"],
        "remote_destruction_digest_mismatch",
    )
    readiness = load_json(readiness_path)
    destruction = load_json(destruction_path)
    require(readiness.get("status") == "blocked", "remote_readiness_not_blocked")
    require(readiness.get("passed") is False, "remote_readiness_must_not_pass")
    require(readiness.get("remote_ready") is False, "remote_readiness_marker_must_be_false")
    require(destruction.get("status") == "passed", "remote_destruction_not_passed")
    require(destruction.get("verified_absent") is True, "remote_instance_absence_not_verified")
    require(destruction.get("simready_validated") is False, "remote_simready_must_remain_false")
    require(destruction.get("simulation_validated") is False, "remote_simulation_must_remain_false")
    published_bundle = handoff.get("published_evidence_bundle")
    require(isinstance(published_bundle, dict), "published_evidence_bundle_missing")
    require(published_bundle.get("contains_four_step_masters") is True, "published_step_masters_missing")
    require(published_bundle.get("contains_four_derived_stl_meshes") is True, "published_stl_meshes_missing")
    require(published_bundle.get("contains_cad_preview_figures") is True, "published_cad_figures_missing")
    require(published_bundle.get("contains_omniverse_render") is False, "omniverse_render_must_not_be_claimed")
    require(published_bundle.get("contains_cfd_or_fea_result") is False, "cfd_fea_result_must_not_be_claimed")
    published_root = ROOT / published_bundle["root"]
    published_artifacts = [
        artifact_record(published_root / "README.md", "published_evidence_readme"),
        artifact_record(
            published_root / "figures/cad-comparison-2v-4v.png",
            "cad_preview_not_omniverse_or_simulation",
        ),
        artifact_record(
            published_root / "figures/trade-study-4v-vs-2v.png",
            "analytical_trade_study_figure_not_engine_efficiency",
        ),
    ]
    omniverse_root = preflight_path.parent
    usd_outputs = sorted(
        path
        for suffix in ("*.usd", "*.usda", "*.usdc", "*.usdz")
        for path in omniverse_root.rglob(suffix)
    )
    require(not usd_outputs, "blocked_preflight_must_not_create_usd")

    comparison_by_scenario = {
        item["scenario_id"]: item for item in study["comparisons"]
    }
    require(set(comparison_by_scenario) == {"type_912_5_0_na", "917_30_1973_turbo_5374"}, "comparison_scenarios_mismatch")
    require(
        all(item["screening_lead"] in {"2v", "4v"} for item in comparison_by_scenario.values()),
        "invalid_screening_lead",
    )

    return {
        "schema_version": "1.0.0",
        "phase": "F29",
        "status": "local_concept_cad_and_analytical_screen_verified_omniverse_and_physical_validation_blocked",
        "verified_artifacts": [
            artifact_record(contract_path, "f29_fail_closed_contract"),
            artifact_record(study_path, "analytical_2v_4v_trade_study"),
            artifact_record(geometry_report_path, "cad_step_roundtrip_evidence"),
            artifact_record(preflight_path, "omniverse_preflight_evidence"),
            artifact_record(handoff_path, "nvidia_host_handoff"),
            artifact_record(readiness_path, "vast_remote_readiness_blocker_evidence"),
            artifact_record(destruction_path, "vast_instance_destruction_evidence"),
            *published_artifacts,
            *cad_artifacts,
        ],
        "comparisons": study["comparisons"],
        "geometry_checks": geometry["checks"],
        "omniverse": {
            "status": "blocked",
            "blockers": preflight["blockers"],
            "usd_output_count": 0,
            "simready_result_available": False,
            "physx_result_available": False,
            "rendered_image_count": 0,
            "remote_attempt": {
                "provider": remote_attempt["provider"],
                "job_id": remote_attempt["job_id"],
                "instance_id": remote_attempt["instance_id"],
                "status": remote_attempt["status"],
                "instance_destroyed": True,
            },
        },
        "conclusion": {
            "screening_lead_by_scenario": {
                scenario: item["screening_lead"]
                for scenario, item in comparison_by_scenario.items()
            },
            "head_material_screening_selection": study["material_screening_selection"],
            "digital_twin_validated": False,
            "manufacturing_authorized": False,
            "engine_operation_authorized": False,
        },
        "release_gates": contract["release_gates"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--geometry-report", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate(
        args.contract.resolve(),
        args.study.resolve(),
        args.geometry_report.resolve(),
        args.preflight.resolve(),
        args.handoff.resolve(),
    )
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
