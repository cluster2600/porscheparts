#!/usr/bin/env python3
"""Publie l'audit F49 sans exposer les STEP prives ni les coordonnees de defaut."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CONTRACT = Path("twins/reference-917-engine/internal-solid-repair-f49.json")
F47_REPORT = Path("twins/reference-917-engine/evidence/f47-internal-brep/f47-internal-brep-public-report.json")
F48_REPORT = Path("twins/reference-917-engine/evidence/f48-mesh-diagnostic/diagnostic-report.json")
FOUR_VIEWS = Path("twins/reference-917-engine/evidence/f49-solid/917-head-f49-scan-derived-exterior-four-views.png")
SECTIONS = Path("twins/reference-917-engine/evidence/f49-solid/917-head-f49-2v-4v-sections.png")
REPORT = Path("twins/reference-917-engine/evidence/f49-solid/f49-solid-public-report.json")
PUBLICATION = Path("twins/reference-917-engine/evidence/f49-solid/publication.json")

EXPECTED_HASHES = {
    CONTRACT: "PLACEHOLDER_CONTRACT",
    F47_REPORT: "73fde591801deee697a87a259374884ba06f7ec1f4acdb1f2ed678bf62d4b372",
    F48_REPORT: "71a9d58b3990ae54ad4e2780861c6c9fa1737230e520c2a3eddf8bb2164d7f3e",
    FOUR_VIEWS: "ce643978a51e7800a647d165dc2eef602f6d3af04ac7bb438210e44382760c13",
    SECTIONS: "cae09b938d7daf7f96de003a7cfd479b5551ddc9ad691858eef6f8cfc7021e7f",
}


def canonical(data: Any) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def build_report(root: Path) -> dict[str, Any]:
    for rel, expected in EXPECTED_HASHES.items():
        path = root / rel
        require(path.is_file(), f"missing input: {rel}")
        if expected != "PLACEHOLDER_CONTRACT":
            require(sha256(path) == expected, f"hash mismatch: {rel}")

    contract = json.loads((root / CONTRACT).read_text(encoding="utf-8"))
    f47 = json.loads((root / F47_REPORT).read_text(encoding="utf-8"))
    f48 = json.loads((root / F48_REPORT).read_text(encoding="utf-8"))
    require(contract["phase"] == "F49", "contract is not F49")
    require(contract["geometry_lock"]["ellipse_or_oval_primitive_allowed"] is False, "ellipse gate open")
    require(contract["geometry_lock"]["outer_skin_surface_edit_allowed"] is False, "outer skin edit gate open")
    require(f47["release_gates"]["same_locked_F43_source_used"] is True, "F43 source not locked")
    require(f48["release_gates"]["2v_zero_BOPAlgo_faults"] is False, "unexpected clean F48 2V candidate")
    require(f48["release_gates"]["4v_zero_BOPAlgo_faults"] is False, "unexpected clean F48 4V candidate")

    bbox = f47["common_outer_envelope_OCCT"]["bbox_scan_units"]
    variants = f47["variants"]
    report: dict[str, Any] = {
        "schema": "porsche-917-f49-internal-solid-repair-public-report/v1",
        "phase": "F49",
        "verdict": "FAIL_CLOSED_NO_ACCEPTED_F49_SOLID_NOT_CAE_READY_NOT_PRINTABLE",
        "scope": "non_deforming_internal_topology_repair_attempt_on_F47_2V_and_4V_heads",
        "authority": {
            "contract": {"path": str(CONTRACT), "sha256": sha256(root / CONTRACT)},
            "F47_public_report": {"path": str(F47_REPORT), "sha256": sha256(root / F47_REPORT)},
            "F48_diagnostic": {"path": str(F48_REPORT), "sha256": sha256(root / F48_REPORT)},
            "F43_private_outer_skin": {
                "sha256": contract["authority"]["outer_skin_F43_private"]["sha256"],
                "repository_policy": "private_local_only_scan_derived_geometry",
                "absolute_scale_certified": False,
                "fitment_OEM_certified": False,
            },
        },
        "locked_outer_skin": {
            "same_exact_F43_source_bytes_loaded": True,
            "source_bbox_scan_units": bbox,
            "surface_edit_operation_used": False,
            "anisotropic_scale_used": False,
            "ellipse_or_oval_primitive_used": False,
            "global_proxy_used": False,
            "functional_circular_features_only": True,
            "candidate_bbox_coordinate_max_delta_scan_units": 5.684341886080802e-14,
            "candidate_sampled_skin_max_distance_scan_units": 1.5943977756741603e-14,
            "sample_classification": "sparse_symmetric_OCCT_point_to_trimmed_BRep_samples_not_continuous_Hausdorff",
            "external_face_signature_equal_outside_openings": False,
            "external_face_signature_reason_false": "not_completed; exact bbox and sparse samples do not prove complete external-face identity",
        },
        "repair_attempts": {
            "2V": {
                "baseline_F47": {
                    "exact_BRepCheck_valid": True,
                    "solid_count": 1,
                    "shell_count": 1,
                    "free_edge_count": 0,
                    "nonmanifold_edge_count": 0,
                    "BOPAlgo_fault_count": 8,
                    "BOPAlgo_status_counts": {"BOPAlgo_InvalidCurveOnSurface": 8},
                    "Gmsh_3D_pass": False,
                    "private_STEP_sha256": variants["2V"]["head_private_STEP"]["sha256"],
                },
                "sequential_boolean_rebuild": {
                    "exact_BRepCheck_valid": True,
                    "solid_count": 1,
                    "shell_count": 1,
                    "free_edge_count": 0,
                    "nonmanifold_edge_count": 0,
                    "BOPAlgo_fault_count": 8,
                    "private_rejected_STEP_sha256": "2362f635cf62a4414466ff807d2fbbb9b744f4a6ab1e3cb2deb118d59f71caa4",
                    "private_audit_receipt_sha256": "ab74403dfffa096c3a2e1514f679ea68520ecfe9c1f6257697ea61a9c1804469",
                },
                "individual_boolean_rebuild": {
                    "exact_BRepCheck_valid": True,
                    "solid_count": 1,
                    "shell_count": 1,
                    "free_edge_count": 0,
                    "nonmanifold_edge_count": 0,
                    "BOPAlgo_fault_count": 8,
                    "faulty_face_count_private": 5,
                    "faulty_edge_count_private": 8,
                    "private_indices_and_coordinates_published": False,
                    "private_rejected_STEP_sha256": "e52fa3b4469de44b9aedc95eb08ad257212e9dc462b55566e243cb67b3b9a9bb",
                    "private_audit_receipt_sha256": "045436309fc723c3e0f48093fd9cc132db3473b8681ab85aa6f5e937b95c4d53",
                },
                "bounded_pcurve_reprojection_surfacecurve_mode_1": {
                    "pre_export_BOPAlgo_fault_count": 0,
                    "same_3D_surfaces_and_curves_before_export": True,
                    "roundtrip_exact_BRepCheck_valid": True,
                    "roundtrip_BOPAlgo_fault_count": 8,
                    "roundtrip_Gmsh_3D_attempted": False,
                    "roundtrip_Gmsh_reason_not_attempted": "fail_fast_BOPAlgo_nonzero",
                    "private_rejected_STEP_sha256": "1e3c3ba8b07eb49cb70986dcb1853d0b8cdc2d6a57910fe02b8369bcbe14aed4",
                    "private_audit_receipt_sha256": "9987e8f97935b905bf7b1dcb256692ee957b595ca69495f3362286b7816b210f",
                },
                "surfacecurve_mode_0": {
                    "roundtrip_exact_BRepCheck_valid": True,
                    "roundtrip_BOPAlgo_fault_count": 131,
                    "faulty_face_count_private": 61,
                    "faulty_edge_count_private": 69,
                    "roundtrip_Gmsh_3D_attempted": False,
                    "roundtrip_Gmsh_reason_not_attempted": "fail_fast_BOPAlgo_nonzero",
                    "private_rejected_STEP_sha256": "4675c4dfc7074159ff9a0635a12e105ccbc97ade7c483c1cdf96abba35ffa90a",
                    "private_audit_receipt_sha256": "ea5bdb9e5aad4c99db04eef07547716820664f9614c84a895e42e2f408dab984",
                },
                "accepted": False,
            },
            "4V": {
                "baseline_F47": {
                    "exact_BRepCheck_valid": True,
                    "solid_count": 1,
                    "shell_count": 1,
                    "free_edge_count": 0,
                    "nonmanifold_edge_count": 0,
                    "BOPAlgo_fault_count": 32,
                    "BOPAlgo_status_counts": {"BOPAlgo_InvalidCurveOnSurface": 32},
                    "Gmsh_3D_pass": False,
                    "private_STEP_sha256": variants["4V"]["head_private_STEP"]["sha256"],
                },
                "bounded_pcurve_reprojection_surfacecurve_mode_1": {
                    "pre_export_BOPAlgo_fault_count": 0,
                    "same_3D_surfaces_and_curves_before_export": True,
                    "roundtrip_exact_BRepCheck_valid": True,
                    "roundtrip_BOPAlgo_fault_count": 32,
                    "roundtrip_Gmsh_3D_attempted": False,
                    "roundtrip_Gmsh_reason_not_attempted": "fail_fast_BOPAlgo_nonzero",
                    "private_rejected_STEP_sha256": "0f2d2974f339fc56170ed96a133bf87d142e12bfbfc3ae09fa6f5db2d14c0a48",
                    "private_audit_receipt_sha256": "28eb5082d851e9a19c02f1bbb3419fd815f1900b99c3b9034124fe06fab0524c",
                    "accepted": False,
                },
                "accepted": False,
            },
            "rejected_alternatives": {
                "global_NURBS_conversion": {
                    "reason": "introduced_22_BOP_faults_and_changed_gas_core_volume_and_area",
                    "used": False,
                },
                "circular_tangent_sweep_prototype": {
                    "reason": "27_BOP_faults_including_21_self_intersections_and_nonmanifold_topology",
                    "used": False,
                },
            },
        },
        "Gmsh_policy": {
            "new_F49_head_mesh_created": False,
            "reason": "all_roundtrip_candidates_failed_the_BOPAlgo_zero_fault_precondition",
            "zero_inverted_tetrahedra_proved": False,
            "minSICN_proved": False,
        },
        "oil_core": {
            "unchanged_from_F47": True,
            "separate_from_gas": True,
            "liquid_coolant_jacket": False,
            "2V": variants["2V"]["oil_core"],
            "4V": variants["4V"]["oil_core"],
            "pressure_and_drainback_validated": False,
        },
        "wall_and_ligament_audit": {
            "target_mm_if_one_scan_unit_equals_one_mm": 1.5,
            "2V_minimum_nominal_ligament_scan_units": variants["2V"]["analytic_functional_packaging_screen"]["minimum_nominal_ligament_scan_units"],
            "4V_minimum_nominal_ligament_scan_units": variants["4V"]["analytic_functional_packaging_screen"]["minimum_nominal_ligament_scan_units"],
            "full_skin_to_void_map_completed": False,
            "minimum_wall_1_5_mm_verified": False,
            "reason_false": "nominal functional ligaments are not an exhaustive wall-thickness proof and absolute scan scale is uncertified",
        },
        "images": {
            "four_views": {"path": str(FOUR_VIEWS), "sha256": sha256(root / FOUR_VIEWS)},
            "sections": {"path": str(SECTIONS), "sha256": sha256(root / SECTIONS)},
            "classification": "annotated_F47_scan_derived_visual_evidence_of_rejected_candidates_not_new_F49_geometry",
        },
        "release_gates": {
            "same_locked_F43_source_used": True,
            "same_bbox_screen_passed": True,
            "complete_outer_face_identity_proved": False,
            "anti_ellipse_oval_and_global_proxy_gate": True,
            "2V_exact_BRepCheck": True,
            "4V_exact_BRepCheck": True,
            "2V_BOPAlgo_zero": False,
            "4V_BOPAlgo_zero": False,
            "2V_Gmsh_3D": False,
            "4V_Gmsh_3D": False,
            "oil_core_BOPAlgo_clean_both_variants": True,
            "minimum_wall_1_5_mm_verified": False,
            "no_trapped_powder_verified": False,
            "fitment_OEM_certified": False,
            "thermal_validated": False,
            "structural_validated": False,
            "fatigue_validated": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
        "repository_policy": {
            "raw_scan_committed": False,
            "private_STEP_STL_BREP_MSH_OBJ_committed": False,
            "private_fault_indices_or_coordinates_committed": False,
            "published": ["contract", "sanitized_metrics", "hashes", "annotated_images", "tests", "documentation"],
        },
    }
    return report


def build_publication(root: Path, report_bytes: bytes) -> dict[str, Any]:
    return {
        "schema": "porsche-917-f49-internal-solid-repair-publication/v1",
        "phase": "F49",
        "verdict": "FAIL_CLOSED_NO_ACCEPTED_F49_SOLID_NOT_CAE_READY_NOT_PRINTABLE",
        "artifacts": [
            {"path": str(REPORT), "sha256": hashlib.sha256(report_bytes).hexdigest()},
            {"path": str(FOUR_VIEWS), "sha256": sha256(root / FOUR_VIEWS)},
            {"path": str(SECTIONS), "sha256": sha256(root / SECTIONS)},
            {"path": str(CONTRACT), "sha256": sha256(root / CONTRACT)},
        ],
        "private_geometry_published": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.project_root.resolve()
    report_bytes = canonical(build_report(root))
    publication_bytes = canonical(build_publication(root, report_bytes))
    outputs = [(root / REPORT, report_bytes), (root / PUBLICATION, publication_bytes)]
    if args.check:
        for path, expected in outputs:
            require(path.is_file(), f"missing output: {path.relative_to(root)}")
            require(path.read_bytes() == expected, f"stale output: {path.relative_to(root)}")
    else:
        for path, payload in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    print("F49 internal solid repair evidence: OK (fail-closed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
