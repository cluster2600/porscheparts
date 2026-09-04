#!/usr/bin/env python3
"""Assemble the public, fail-closed F50 additive-print qualification record."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PRIVATE_SUFFIXES = {".brep", ".step", ".stp", ".stl", ".obj", ".msh", ".inp", ".frd", ".vtk", ".vtp"}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_manifest(directory: Path, manifest: dict[str, Any]) -> None:
    for entry in manifest.values():
        if not isinstance(entry, dict) or "path" not in entry or "sha256" not in entry:
            continue
        path = directory / entry["path"]
        if not path.is_file() or sha256(path) != entry["sha256"]:
            raise SystemExit(f"manifest_mismatch:{path}")


def relative(root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    evidence = args.evidence.resolve()
    lock_path = root / "twins/reference-917-engine/f50-private-master-hash-lock.json"
    lock = load(lock_path)
    geometries = {}
    entries: list[dict[str, Any]] = []
    for variant in ("2v", "4v"):
        directory = evidence / f"geometry-{variant}"
        report_path = directory / f"917-head-f50-{variant}-lpbf-geometry-report.json"
        manifest_path = directory / f"917-head-f50-{variant}-lpbf-geometry-manifest.json"
        report = load(report_path)
        manifest = load(manifest_path)
        verify_manifest(directory, manifest)
        if report["master"]["sha256"] != lock["master_hashes"][variant]:
            raise SystemExit(f"master_binding_mismatch:{variant}")
        if report["geometry_invariants"] != {
            "absolute_scale_certified": False,
            "analysis_transform": "rigid rotation and translation only",
            "anisotropic_scaling_used": False,
            "elliptic_or_oval_exterior_used": False,
            "envelope_proxy_used": False,
            "scan_skin_modified": False,
            "source_bbox_contract_verified": True,
            "source_bbox_coordinates_published": False,
            "units_interpreted_as_mm_for_candidate_screen_only": True,
        }:
            raise SystemExit(f"skin_policy_mismatch:{variant}")
        geometries[variant] = report
        for artifact in directory.iterdir():
            if artifact.is_file():
                entries.append({"path": relative(root, artifact), "sha256": sha256(artifact), "bytes": artifact.stat().st_size})
    coupon_dir = evidence / "additivefoam-coupons"
    coupon_report_path = coupon_dir / "917-head-f50-additivefoam-report.json"
    coupon_manifest_path = coupon_dir / "917-head-f50-additivefoam-manifest.json"
    coupon_report = load(coupon_report_path)
    coupon_manifest = load(coupon_manifest_path)
    verify_manifest(coupon_dir, coupon_manifest)
    if coupon_report["master_hashes"] != lock["master_hashes"]:
        raise SystemExit("coupon_master_binding_mismatch")
    media_dir = evidence / "media"
    media_manifest_path = media_dir / "917-head-f50-lpbf-process-media-manifest.json"
    media_manifest = load(media_manifest_path)
    verify_manifest(media_dir, media_manifest)
    for directory in (coupon_dir, media_dir):
        for artifact in directory.iterdir():
            if artifact.is_file():
                entries.append({"path": relative(root, artifact), "sha256": sha256(artifact), "bytes": artifact.stat().st_size})
    readme_path = evidence / "README.md"
    entries.append({"path": relative(root, readme_path), "sha256": sha256(readme_path), "bytes": readme_path.stat().st_size})
    entries.append({"path": relative(root, lock_path), "sha256": sha256(lock_path), "bytes": lock_path.stat().st_size})
    leaked = [entry["path"] for entry in entries if Path(entry["path"]).suffix.lower() in PRIVATE_SUFFIXES]
    if leaked:
        raise SystemExit(f"private_geometry_publication_forbidden:{leaked}")

    comparison = {}
    for metric, key in (
        ("support_proxy_volume_cm3", "support_proxy_volume_cm3"),
        ("thin_probe_fraction_below_1p5_mm", "sample_fraction_below_1p5_mm"),
        ("thickness_p01_mm", "p01_mm"),
        ("new_island_count", "new_island_count"),
    ):
        if metric in ("support_proxy_volume_cm3", "new_island_count"):
            values = {variant: geometries[variant]["full_build_slicing"][key] for variant in geometries}
        else:
            values = {variant: geometries[variant]["thickness_screen"][key] for variant in geometries}
        comparison[metric] = values

    contract = {
        "$comment": "Qualification virtuelle F50 fail-closed. Les deux methodes sont complementaires; aucune n'autorise une impression metal ou un demarrage moteur.",
        "schema_version": "1.0.0",
        "phase": "F50",
        "asset_id": "917_head_scan_locked_2v_4v_additive_print_qualification_f50",
        "classification": "executed_full_piece_geometric_slicing_plus_local_AdditiveFOAM_process_witness_not_manufacturing_release",
        "private_master_hash_lock": {"path": relative(root, lock_path), "sha256": sha256(lock_path), "master_hashes": lock["master_hashes"]},
        "geometry_policy": {
            "private_F50_native_masters_used": True,
            "private_geometry_published": False,
            "scan_skin_modified": False,
            "envelope_proxy_used": False,
            "global_oval_or_ellipse_used": False,
            "anisotropic_scaling_used": False,
            "analysis_transforms": "rigid rotations and translations only",
            "absolute_scale_certified": False,
        },
        "machine_candidate": geometries["2v"]["machine"],
        "method_1_full_piece_macro_geometry": {
            "classification": "actual triangle-plane slicing of private same-master tessellation; aggregate results only",
            "layer_thickness_mm": 0.05,
            "orientation_rule": geometries["2v"]["orientation_selection_rule"],
            "support_model": "conservative vertical-column raster proxy, not supplier supports",
            "thickness_model": geometries["2v"]["thickness_screen"]["method"],
            "closed_volume_model": geometries["2v"]["powder_escape_screen"]["method"],
            "results": {
                variant: {
                    "report": relative(root, evidence / f"geometry-{variant}" / f"917-head-f50-{variant}-lpbf-geometry-report.json"),
                    "selected_orientation": geometries[variant]["selected_candidate_orientation"],
                    "full_build_slicing": geometries[variant]["full_build_slicing"],
                    "thickness_screen": geometries[variant]["thickness_screen"],
                    "powder_escape_screen": geometries[variant]["powder_escape_screen"],
                }
                for variant in geometries
            },
        },
        "method_2_local_process_physics": {
            "classification": coupon_report["classification"],
            "report": relative(root, coupon_report_path),
            "software": coupon_report["software"],
            "governing_equation": coupon_report["method"]["governing_equation"],
            "material": coupon_report["material_model"],
            "representativity": coupon_report["representativity"],
            "resolution_convergence": coupon_report["resolution_convergence"],
            "gates": coupon_report["gates"],
        },
        "comparison_2v_4v": comparison,
        "full_piece_thermomechanical_distortion": {
            "executed": False,
            "reason": "No complete CP1 temperature-dependent elastic-plastic, creep, relaxation and calibrated LPBF inherent-strain card is available. A result would fabricate material evidence.",
            "existing_local_witness_reference": "twins/reference-917-engine/thermomechanical-screen-f50.json",
        },
        "process_media": {"manifest": relative(root, media_manifest_path), "classification": media_manifest["classification"]},
        "release_gates": {
            "native_master_topology_locked": True,
            "full_piece_50um_macro_slicing_completed_both_variants": True,
            "nominal_bare_part_machine_envelope_fit_both_variants": True,
            "minimum_wall_1p5mm_everywhere": False,
            "supplier_support_topology_validated": False,
            "support_removal_access_validated": False,
            "recoater_collision_with_distorted_part_validated": False,
            "powder_removal_physically_validated": False,
            "target_CP1_hot_material_card_used": False,
            "full_piece_thermomechanical_distortion_converged": False,
            "supplier_machine_file_signed": False,
            "physical_coupon_qualified": False,
            "ct_or_endoscopy_completed": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
        "verdict": "F50 virtual screens executed and traceable; both variants remain prohibited for metal printing and engine start",
    }
    args.output.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    entries.append({"path": relative(root, args.output), "sha256": sha256(args.output), "bytes": args.output.stat().st_size})
    args.manifest.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "phase": "F50",
                "classification": "public_aggregate_evidence_manifest_no_private_geometry",
                "entries": sorted(entries, key=lambda entry: entry["path"]),
                "private_geometry_published": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"contract": str(args.output), "entries": len(entries), "release_gates": contract["release_gates"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
