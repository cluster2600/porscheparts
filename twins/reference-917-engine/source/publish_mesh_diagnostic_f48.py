#!/usr/bin/env python3
"""Publie et verifie le diagnostic F48 sans charger les STEP prives."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CONTRACT_REL = Path("twins/reference-917-engine/mesh-diagnostic-f48.json")
EVIDENCE_REL = Path("twins/reference-917-engine/evidence/f48-mesh-diagnostic")
REPORT_REL = EVIDENCE_REL / "diagnostic-report.json"
SUMMARY_REL = EVIDENCE_REL / "summary.json"
MANIFEST_REL = EVIDENCE_REL / "manifest.json"
SCRIPT_REL = Path("twins/reference-917-engine/source/publish_mesh_diagnostic_f48.py")
DIAGNOSTIC_SCRIPT_REL = Path(
    "twins/reference-917-engine/source/diagnose_private_f47_step_mesh_f48.py"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("phase") != "F48":
        raise ValueError("phase_must_be_F48")
    policy = contract["locked_geometry_policy"]
    forbidden_true = (
        "external_scan_skin_modification_allowed",
        "global_healing_allowed",
        "proxy_geometry_allowed",
        "oval_or_ellipse_allowed",
        "geometry_created_by_f48",
        "mesh_committed_by_f48",
    )
    if any(policy[key] for key in forbidden_true):
        raise ValueError("locked_geometry_policy_open")
    if contract["private_evidence"]["coordinates_published"]:
        raise ValueError("private_coordinates_must_not_be_published")
    if contract["private_evidence"]["entity_indices_published"]:
        raise ValueError("private_entity_indices_must_not_be_published")
    expected = {
        "2v": (4, 0, 8, "PLC_segment_facet_intersection"),
        "4v": (22, 0, 32, "PLC_facet_facet_intersection"),
    }
    for variant, (gas, oil, head, error_class) in expected.items():
        observation = contract["observations"][variant]
        occt = observation["occt"]
        if (
            occt["gas_core"]["BOPAlgo_fault_count"],
            occt["oil_core"]["BOPAlgo_fault_count"],
            occt["head_after_subtraction"]["BOPAlgo_fault_count"],
            observation["gmsh"]["error_class"],
        ) != (gas, oil, head, error_class):
            raise ValueError(f"unexpected_diagnostic:{variant}")
        for item in occt.values():
            if not item["BRepCheck_exact_valid"]:
                raise ValueError(f"unexpected_BRepCheck_failure:{variant}")
        if observation["gmsh"]["volume_mesh_completed"]:
            raise ValueError(f"false_volume_mesh_claim:{variant}")
    if not contract["release_gates"] or any(contract["release_gates"].values()):
        raise ValueError("all_release_gates_must_remain_closed")
    if contract["required_outer_lock_checks"]["outer_face_geometric_signatures_equal_outside_declared_openings"]:
        raise ValueError("no_repaired_candidate_outer_lock_claim_allowed")


def build_report(
    contract: dict[str, Any], contract_sha256: str, diagnostic_script_sha256: str
) -> dict[str, Any]:
    return {
        "schema": "porsche-917-f48-public-step-mesh-diagnostic/v1",
        "phase": "F48",
        "verdict": "F47_STEP_MESH_REJECTED_INTERNAL_GAS_PCURVES_REPAIR_REQUIRED",
        "classification": contract["classification"],
        "contract": {"path": CONTRACT_REL.as_posix(), "sha256": contract_sha256},
        "private_diagnostic_harness": {
            "path": DIAGNOSTIC_SCRIPT_REL.as_posix(),
            "sha256": diagnostic_script_sha256,
            "coordinate_output_must_remain_outside_repository": True,
        },
        "locked_geometry_policy": contract["locked_geometry_policy"],
        "private_evidence": contract["private_evidence"],
        "toolchain": contract["toolchain"],
        "observations": contract["observations"],
        "causal_assessment": contract["causal_assessment"],
        "surgical_correction_plan": contract["surgical_correction_plan"],
        "required_outer_lock_checks": contract["required_outer_lock_checks"],
        "release_gates": contract["release_gates"],
        "claims": {
            "STEP_or_mesh_published": False,
            "geometry_repaired": False,
            "CAE_executed": False,
            "printability_validated": False,
            "manufacturing_release": False,
        },
    }


def build_summary(report: dict[str, Any]) -> dict[str, Any]:
    observations = report["observations"]
    return {
        "schema": "porsche-917-f48-public-step-mesh-diagnostic-summary/v1",
        "phase": "F48",
        "verdict": report["verdict"],
        "root_cause_domain": "internal_gas_core_pcurves",
        "2v": {
            "gas_BOP_faults": observations["2v"]["occt"]["gas_core"]["BOPAlgo_fault_count"],
            "oil_BOP_faults": observations["2v"]["occt"]["oil_core"]["BOPAlgo_fault_count"],
            "head_BOP_faults": observations["2v"]["occt"]["head_after_subtraction"]["BOPAlgo_fault_count"],
            "gmsh_error_class": observations["2v"]["gmsh"]["error_class"],
        },
        "4v": {
            "gas_BOP_faults": observations["4v"]["occt"]["gas_core"]["BOPAlgo_fault_count"],
            "oil_BOP_faults": observations["4v"]["occt"]["oil_core"]["BOPAlgo_fault_count"],
            "head_BOP_faults": observations["4v"]["occt"]["head_after_subtraction"]["BOPAlgo_fault_count"],
            "gmsh_error_class": observations["4v"]["gmsh"]["error_class"],
        },
        "next_operation": "local_internal_gas_pcurve_rebuild_then_locked_F43_resubtraction",
        "external_skin_change_allowed": False,
        "oval_or_ellipse_allowed": False,
        "all_release_gates_closed": not any(report["release_gates"].values()),
    }


def artifact(root: Path, rel: Path) -> dict[str, Any]:
    path = root / rel
    return {"path": rel.as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}


def build(root: Path) -> None:
    contract_path = root / CONTRACT_REL
    contract = load(contract_path)
    validate_contract(contract)
    report = build_report(contract, sha256(contract_path), sha256(root / DIAGNOSTIC_SCRIPT_REL))
    dump(root / REPORT_REL, report)
    dump(root / SUMMARY_REL, build_summary(report))
    manifest = {
        "schema": "porsche-917-f48-public-step-mesh-diagnostic-manifest/v1",
        "phase": "F48",
        "generator": {"path": SCRIPT_REL.as_posix(), "sha256": sha256(root / SCRIPT_REL)},
        "private_diagnostic_harness": {
            "path": DIAGNOSTIC_SCRIPT_REL.as_posix(),
            "sha256": sha256(root / DIAGNOSTIC_SCRIPT_REL),
        },
        "artifacts": [artifact(root, rel) for rel in (REPORT_REL, SUMMARY_REL)],
        "private_STEP_or_coordinates_in_manifest": False,
    }
    dump(root / MANIFEST_REL, manifest)


def check(root: Path) -> None:
    contract = load(root / CONTRACT_REL)
    validate_contract(contract)
    report = load(root / REPORT_REL)
    summary = load(root / SUMMARY_REL)
    manifest = load(root / MANIFEST_REL)
    if report != build_report(
        contract, sha256(root / CONTRACT_REL), sha256(root / DIAGNOSTIC_SCRIPT_REL)
    ):
        raise ValueError("diagnostic_report_not_reproducible")
    if summary != build_summary(report):
        raise ValueError("summary_not_reproducible")
    if manifest["generator"]["sha256"] != sha256(root / SCRIPT_REL):
        raise ValueError("generator_hash_mismatch")
    if manifest["private_diagnostic_harness"]["sha256"] != sha256(
        root / DIAGNOSTIC_SCRIPT_REL
    ):
        raise ValueError("diagnostic_harness_hash_mismatch")
    for item in manifest["artifacts"]:
        path = root / item["path"]
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise ValueError(f"artifact_hash_mismatch:{item['path']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.project_root.resolve()
    if args.check:
        check(root)
        print("F48 private STEP mesh diagnostic evidence: OK")
    else:
        build(root)
        print("F48 private STEP mesh diagnostic evidence: BUILT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
