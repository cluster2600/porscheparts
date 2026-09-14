#!/usr/bin/env python3
"""Vérifie et résume les preuves numériques du crochet de phare F0."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


PART_ID = "993-ELEC-HEADLAMP-SPRING-HOOK-F0-0001"
TWIN_ID = "TWIN-993-HEADLAMP-SPRING-HOOK-ALSI10MG-F0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()

    step = root / "parts/993-elec-headlamp-spring-hook-f0-0001/derived/headlamp_spring_hook_f0.step"
    math_report = root / "parts/993-elec-headlamp-spring-hook-f0-0001/evidence/engineering-screen.json"
    evidence = root / "twins/993-headlamp-spring-hook-alsi10mg-f0/evidence"
    lpbf = evidence / "lpbf-f0/993-elec-headlamp-spring-hook-f0-0001-lpbf-geometry-report.json"
    fea = evidence / "calculix-f0/calculix-thermomechanical-screen.json"
    simready = evidence / "simready-f0"
    asset = simready / "headlamp_spring_hook_f0.usd"
    scene = simready / "headlamp-hook-rigid-screen.usd"
    asset_validation = simready / "binary-validation.json"
    scene_validation = simready / "rigid-scene-validation.json"
    scene_authoring = simready / "scene-authoring-report.json"
    rigid = simready / "ovphysx-rigid-screen.json"
    dockerfile = root / "containers/ov-libraries-cpu.Dockerfile"

    documents = {
        "math": load(math_report),
        "lpbf": load(lpbf),
        "fea": load(fea),
        "asset_validation": load(asset_validation),
        "scene_validation": load(scene_validation),
        "scene_authoring": load(scene_authoring),
        "rigid": load(rigid),
    }
    if documents["math"]["part_id"] != PART_ID:
        raise SystemExit("Le rapport analytique ne correspond pas à la pièce.")
    if documents["lpbf"]["part_id"] != PART_ID:
        raise SystemExit("Le rapport LPBF ne correspond pas à la pièce.")
    if documents["fea"]["part_id"] != PART_ID:
        raise SystemExit("Le rapport CalculiX ne correspond pas à la pièce.")
    if documents["asset_validation"] != {"status": "PASS", "rules": []}:
        raise SystemExit("La validation NVIDIA de l'asset binaire n'est pas verte.")
    if documents["scene_validation"] != {"status": "PASS", "rules": []}:
        raise SystemExit("La validation NVIDIA de la scène rigide n'est pas verte.")
    if documents["rigid"]["status"] != "PASS":
        raise SystemExit("Le témoin ovphysx n'est pas vert.")
    if documents["fea"]["release_authorized"] is not False:
        raise SystemExit("Le rapport CalculiX ne doit jamais libérer le F0.")
    if documents["lpbf"]["gates"]["metal_print_authorized"] is not False:
        raise SystemExit("Le rapport LPBF ne doit jamais libérer le F0.")
    if documents["rigid"]["gates"]["manufacturing_release"] is not False:
        raise SystemExit("Le témoin rigide ne doit jamais libérer le F0.")

    expected = {
        step: documents["fea"]["inputs"]["step_sha256"],
        asset: documents["scene_authoring"]["asset"]["sha256"],
        scene: documents["rigid"]["inputs"]["scene"]["sha256"],
    }
    for path, digest in expected.items():
        if sha256(path) != digest:
            raise SystemExit(f"Empreinte incohérente: {path}")

    artifact_paths = [
        step,
        math_report,
        lpbf,
        evidence / "lpbf-f0/993-elec-headlamp-spring-hook-f0-0001-layer-metrics.csv",
        evidence / "lpbf-f0/993-elec-headlamp-spring-hook-f0-0001-lpbf-geometry-screen.png",
        fea,
        asset,
        scene,
        asset_validation,
        scene_validation,
        scene_authoring,
        rigid,
        dockerfile,
    ]
    artifacts = {
        str(path.relative_to(root)): {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in artifact_paths
    }

    report = {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "twin_id": TWIN_ID,
        "status": "virtual_screen_complete_release_blocked",
        "executed_stack": {
            "cad": {
                "build123d": "0.11.1",
                "occt": "7.9.3.1",
                "image_id": "sha256:2e02e3aa96eb1375cbc1a230664a08bafb89d461f4caeae8fe3501df6c9d84",
                "image_digest": "ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:7155af27ddd4c909c29bbd599dbe18472661c0c5d6575906371a16e7420b7fce",
            },
            "lpbf_geometry": {
                "trimesh": "5.1.0",
                "numpy": "2.5.2",
                "image_id": "sha256:49979f46f421459dae4bf21aaa898e2253b07301c3e5b2cabaa6eaf06f54d696",
                "image_digest": "ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f",
            },
            "thermomechanical": documents["fea"]["solver"],
            "cad_to_usd": {
                "usd_convert_cad": "0.2.0",
                "openusd": "26.8",
                "validation": "usd-validation-nvidia 1.21.0",
                "image_id": "sha256:3f97e71ebf07ee38b5729fa61858578d9c759dfa212f757e7286f3f09f7dc02d",
                "image_digest": "ghcr.io/cluster2600/3dprinting993-simready-m64-runtime@sha256:a07ee46d5dbfe73193cfd0d3829c0dc3e69aed95ab82841a89c18828cea85f44",
            },
            "rigid_body": documents["rigid"]["runtime"],
        },
        "headline_results": {
            "screening_mass_g": documents["math"]["results"]["screening_mass_g"],
            "lpbf_layers": documents["lpbf"]["full_build_slicing"]["layer_count"],
            "lpbf_orientation": documents["lpbf"]["selected_candidate_orientation"],
            "lpbf_support_proxy_mm3": documents["lpbf"]["full_build_slicing"]["support_proxy_volume_mm3"],
            "fea_execution_count": documents["fea"]["solver"]["execution_count"],
            "fine_cold_p95_mpa": documents["fea"]["cases"][-1]["cold_linear_static"]["von_mises_mpa"]["p95"],
            "fine_hot_p95_mpa": documents["fea"]["cases"][-1]["hot_sequential_thermomechanical"]["von_mises_mpa"]["p95"],
            "ovphysx_steps": documents["rigid"]["synthetic_case"]["steps"],
            "ovphysx_final_witness_z_mm": documents["rigid"]["synthetic_case"]["final_position_mm"][2],
        },
        "gates": {
            "exact_step_hash_linked": True,
            "lpbf_geometry_screen_executed": True,
            "six_case_calculix_screen_executed": True,
            "nvidia_usd_asset_validation": True,
            "nvidia_usd_rigid_scene_validation": True,
            "ovstage_ovphysx_integration": True,
            "ovrtx_render_for_this_revision": False,
            "measured_headlamp_interface": False,
            "qualified_hot_material_card": False,
            "qualified_adhesive_joint": False,
            "functional_vehicle_assembly": False,
            "physical_correlation": False,
            "manufacturing_release": False,
        },
        "artifacts": artifacts,
    }
    output = args.output
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("HEADLAMP_HOOK_EVIDENCE_SUMMARY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
