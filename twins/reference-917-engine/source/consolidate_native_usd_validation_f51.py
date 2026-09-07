#!/usr/bin/env python3
"""Consolide les preuves privées F51 dans un manifeste public expurgé.

Le script vérifie la chaîne de hashes et les gates géométriques avant d'émettre
un résumé. Il ne copie ni coordonnées, ni chemins absolus, ni géométrie.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validation_summary(path: Path) -> dict[str, object]:
    payload = load(path)
    return {
        "status": "PASS" if payload.get("passed") is True else payload.get("status", "FAIL"),
        "passed": payload.get("passed") is True,
        "issue_counts": payload.get("issue_counts", {}),
    }


def variant_summary(
    variant: str,
    f50: dict,
    tessellation_path: Path,
    usd_path: Path,
    validation_dir: Path,
) -> dict[str, object]:
    tessellation = load(tessellation_path)
    usd = load(usd_path)
    master = f50["native_OCCT_masters"][variant]
    require(tessellation["variant"] == variant, f"{variant}: tessellation variant mismatch")
    require(usd["variant"] == variant, f"{variant}: USD variant mismatch")
    require(
        tessellation["source"]["native_BREP_sha256"]
        == master["private_native_BREP_sha256"],
        f"{variant}: native BREP authority hash mismatch",
    )
    require(
        usd["source"]["native_BREP_sha256"] == master["private_native_BREP_sha256"],
        f"{variant}: USD source hash mismatch",
    )
    require(master["accepted_as_private_same_kernel_CAD_CAE_master"] is True, f"{variant}: F50 master red")
    require(master["roundtrip"]["bbox_maximum_coordinate_delta_scan_units"] == 0.0, f"{variant}: F50 bbox not F43 locked")
    require(tessellation["accepted_for_private_USD_authoring"] is True, f"{variant}: tessellation red")
    require(usd["accepted_for_external_USD_validators"] is True, f"{variant}: USD roundtrip red")

    operations = tessellation["operations"]
    usd_operations = usd["operations"]
    require(operations["direct_native_BREP_import"] is True, f"{variant}: STEP detour")
    require(operations["scale_transform"] == [1.0, 1.0, 1.0], f"{variant}: tessellation scale drift")
    require(usd_operations["point_scale_transform"] == [1.0, 1.0, 1.0], f"{variant}: USD scale drift")
    require(usd_operations["xform_op_count"] == 0, f"{variant}: USD transform present")
    for key in ("proxy_used", "ellipse_or_oval_used"):
        require(operations[key] is False and usd_operations[key] is False, f"{variant}: forbidden {key}")
    for key in ("OCC_heal_or_sew_used", "CAD_boolean_used", "geometry_transform_used"):
        require(operations[key] is False, f"{variant}: forbidden {key}")
    require(operations["triangle_winding_reorientation_changes_coordinates"] is False, f"{variant}: winding changed points")

    topo = usd["USD"]["topology"]
    require(topo["boundary_edge_count"] == 0, f"{variant}: open USD surface")
    require(topo["nonmanifold_edge_count"] == 0, f"{variant}: nonmanifold USD surface")
    require(topo["winding_conflict_edge_count"] == 0, f"{variant}: winding conflicts")
    require(topo["degenerate_triangle_count"] == 0, f"{variant}: degenerate triangles")
    require(usd["USD"]["component_count"] == 1, f"{variant}: component count")
    require(usd["USD"]["mesh_count"] == 1, f"{variant}: mesh count")
    require(usd["USD"]["meters_per_unit"] == 0.001, f"{variant}: stage units")
    require(usd["USD"]["up_axis"] == "Z", f"{variant}: up axis")

    brep_bbox = np.asarray(tessellation["tessellation"]["BRep_bbox_scan_units_private"], dtype=float)
    usd_bbox = np.asarray(usd["USD"]["roundtrip_bbox_scan_units_private"], dtype=float)
    require(brep_bbox.shape == (6,) and usd_bbox.shape == (6,), f"{variant}: private bbox shape")
    usd_bbox_delta_from_f43 = float(np.max(np.abs(usd_bbox - brep_bbox)))
    require(usd_bbox_delta_from_f43 <= 5.0e-6, f"{variant}: USD bbox drift from F43")

    validators = {
        name: validation_summary(validation_dir / f"{name}.json")
        for name in ("minimum", "asset", "geometry", "physics")
    }
    require(all(result["passed"] for result in validators.values()), f"{variant}: external validator red")
    simready = load(validation_dir / "simready.json")
    formal_profile_available = bool(simready.get("available_profiles"))
    require(simready.get("passed") is False, f"{variant}: unexpected unstamped profile pass")
    require(not formal_profile_available, f"{variant}: profile became available; rerun semantics required")

    tess = tessellation["tessellation"]
    usd_data = usd["USD"]
    return {
        "source_native_BREP_sha256": master["private_native_BREP_sha256"],
        "surface_archive_sha256": usd["source"]["surface_archive_sha256"],
        "private_USD_sha256": usd_data["sha256"],
        "private_USD_bytes": usd_data["bytes"],
        "tessellation": {
            "point_count": tess["point_count"],
            "triangle_count": tess["triangle_count"],
            "unique_edge_count": tess["unique_edge_count"],
            "boundary_edge_count": tess["boundary_edge_count"],
            "nonmanifold_edge_count": tess["nonmanifold_edge_count"],
            "winding_conflict_edge_count_before_index_reorientation": tess["winding_conflict_edge_count_before_reorientation"],
            "winding_conflict_edge_count_after_index_reorientation": tess["winding_conflict_edge_count"],
            "triangle_index_records_reoriented": tess["triangle_winding_reoriented_count"],
            "reorientation_changed_coordinates": operations["triangle_winding_reorientation_changes_coordinates"],
            "connected_component_count": tess["connected_component_count"],
            "degenerate_triangle_count": tess["degenerate_triangle_count"],
            "maximum_bbox_delta_from_native_BREP_scan_units": tess["maximum_bbox_delta_from_BRep_scan_units"],
            "absolute_volume_relative_delta_from_native_BREP": tess["absolute_volume_relative_delta_from_BRep"],
        },
        "USD_roundtrip": {
            "format": usd_data["format"],
            "stage_roundtrip_opened": usd_data["stage_roundtrip_opened"],
            "component_count": usd_data["component_count"],
            "mesh_count": usd_data["mesh_count"],
            "point_count": usd_data["point_count"],
            "triangle_count": usd_data["triangle_count"],
            "normal_count": usd_data["normal_count"],
            "normal_interpolation": usd_data["normal_interpolation"],
            "normal_length_maximum_error": usd_data["normal_length_maximum_error"],
            "normal_alignment_minimum": usd_data["normal_alignment_minimum"],
            "maximum_float32_coordinate_quantization_scan_units": usd_data["maximum_float32_coordinate_quantization_scan_units"],
            "maximum_bbox_delta_from_F43_scan_units": usd_bbox_delta_from_f43,
            "meters_per_unit": usd_data["meters_per_unit"],
            "up_axis": usd_data["up_axis"],
            "xform_op_count": usd_operations["xform_op_count"],
            "applied_schema_count": len(usd_data["applied_schemas"]),
        },
        "validators": validators,
        "formal_SimReady_profile": {
            "target": "Prop-Robotics-Neutral@2.1.0",
            "status": "BLOCKED_NEEDS_RERUN",
            "passed": False,
            "available_profile_count_reported_by_runtime": len(simready.get("available_profiles", [])),
            "reason": "upstream_checkout_does_not_expose_profiles/profiles.toml_to_reference_wrapper",
        },
        "geometry_validation_accepted": True,
        "simready_profile_accepted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--f50-public-evidence", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    for suffix in ("2v", "4v"):
        parser.add_argument(f"--tessellation-{suffix}", type=Path, required=True)
        parser.add_argument(f"--usd-{suffix}", type=Path, required=True)
        parser.add_argument(f"--validation-dir-{suffix}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    f50 = load(args.f50_public_evidence)
    preflight = load(args.preflight)
    require(preflight["status"] == "ready", "NVIDIA preflight not ready")
    require(preflight["runtimes"]["content_agents"]["status"] == "skipped", "Content Agents were not skipped")
    variants = {
        "2V": variant_summary("2V", f50, args.tessellation_2v, args.usd_2v, args.validation_dir_2v),
        "4V": variant_summary("4V", f50, args.tessellation_4v, args.usd_4v, args.validation_dir_4v),
    }
    evidence = {
        "$comment": "Preuve F51 expurgee; aucune geometrie, coordonnee ou chemin prive n'est publie.",
        "schema": "porsche-917-f51-native-brep-usd-public-evidence/v1",
        "phase": "F51",
        "workflow": {
            "classification": "validation_only",
            "property_assignment_intent": "skip",
            "source_geometry": "F50_private_native_OCCT_BREP_masters",
            "path": "native_OCCT_BREP_to_Gmsh_OCCT_surface_to_OpenUSD",
            "STEP_intermediate_used": False,
            "output_root": "private_not_committed",
            "render_output": "none",
        },
        "NVIDIA_preflight": {
            "status": "PASS",
            "platform": preflight["platform"],
            "openusd_status": preflight["runtimes"]["openusd_python"]["status"],
            "asset_validator_status": preflight["runtimes"]["asset_validator"]["status"],
            "simready_validate_runtime_status": preflight["runtimes"]["simready_validate"]["status"],
            "content_agents_status": preflight["runtimes"]["content_agents"]["status"],
            "simready_foundation_commit": preflight["upstreams"]["simready_foundation"]["commit"],
        },
        "authority": f50["authority"],
        "geometry_policy": {
            "scale_transform": [1.0, 1.0, 1.0],
            "point_displacement_used": False,
            "surface_deformation_used": False,
            "anisotropic_scale_used": False,
            "proxy_used": False,
            "ellipse_or_oval_used": False,
            "STEP_intermediate_used": False,
            "material_assignment_used": False,
            "physics_authoring_used": False,
            "private_geometry_committed": False,
        },
        "variants": variants,
        "ordered_stage_results": [
            {"stage": "NVIDIA_preflight_validation_only_skip_Content_Agents", "status": "PASS"},
            {"stage": "direct_native_BREP_tessellation", "status": "PASS"},
            {"stage": "OpenUSD_authoring_and_roundtrip", "status": "PASS"},
            {"stage": "validate_usd_minimum", "status": "PASS"},
            {"stage": "NVIDIA_Asset_Validator_generic", "status": "PASS"},
            {"stage": "NVIDIA_Asset_Validator_geometry", "status": "PASS"},
            {"stage": "NVIDIA_Asset_Validator_physics_diagnostics", "status": "PASS"},
            {"stage": "SimReady_formal_profile", "status": "BLOCKED_NEEDS_RERUN"},
            {"stage": "OVRTX_render", "status": "BLOCKED_NO_APPROVED_RUNTIME"},
        ],
        "blockers": [
            "SimReady Foundation profile discovery is blocked in the supplied runtime checkout; no profile result is claimed.",
            "No approved OVRTX runtime was available and Vast use was forbidden; no substitute render is published.",
            "F50 strict volumetric mesh gates remain red.",
            "Absolute scale and Porsche 917 interfaces remain uncertified.",
        ],
        "gates": {
            "private_native_BREP_authority_accepted": True,
            "private_surface_tessellation_accepted": True,
            "private_USD_geometry_roundtrip_accepted": True,
            "NVIDIA_minimum_and_asset_geometry_diagnostics_accepted": True,
            "formal_SimReady_profile_accepted": False,
            "OVRTX_render_validated": False,
            "manufacturing_authorized": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"variants": list(variants), "USD_geometry": "PASS", "SimReady_profile": "BLOCKED_NEEDS_RERUN"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
