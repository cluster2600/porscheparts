#!/usr/bin/env python3
"""Construit les quatre solides conceptuels de culasse F29 avec build123d/OCCT."""

from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import math
from pathlib import Path
import platform
import re
from typing import Any


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected_json_object:{path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def portable_path(path: Path) -> str:
    workspace_root = Path("/workspace")
    try:
        return str(path.relative_to(workspace_root))
    except ValueError:
        return path.name


def canonicalize_step_header(path: Path) -> None:
    payload = path.read_text(encoding="utf-8")
    canonical, replacement_count = re.subn(
        r"(FILE_NAME\([^,]+,')[^']+(')",
        r"\g<1>1970-01-01T00:00:00\g<2>",
        payload,
        count=1,
    )
    require(replacement_count == 1, f"step_header_timestamp_not_found:{path}")
    path.write_text(canonical, encoding="utf-8", newline="\n")


def vector(values: Any) -> list[float]:
    return [round(float(values.X), 6), round(float(values.Y), 6), round(float(values.Z), 6)]


def shape_metrics(shape: Any) -> dict[str, Any]:
    solids = list(shape.solids())
    bounding_box = shape.bounding_box()
    closed = [
        bool(
            solid.is_valid
            and solid.is_manifold
            and len(solid.shells()) == 1
            and solid.shells()[0].is_manifold
            and solid.volume > 0.0
        )
        for solid in solids
    ]
    return {
        "valid": bool(shape.is_valid),
        "manifold": bool(shape.is_manifold),
        "solid_count": len(solids),
        "all_solids_closed": bool(solids) and all(closed),
        "shell_counts": [len(solid.shells()) for solid in solids],
        "face_count": len(shape.faces()),
        "edge_count": len(shape.edges()),
        "volume_mm3": round(sum(solid.volume for solid in solids), 6),
        "bounds_min_mm": vector(bounding_box.min),
        "bounds_max_mm": vector(bounding_box.max),
        "bounds_size_mm": vector(bounding_box.size),
    }


def vertical_cylinder(radius_mm: float, height_mm: float, x_mm: float, y_mm: float, z_mm: float) -> Any:
    from build123d import Align, Cylinder, Pos

    return Pos(x_mm, y_mm, z_mm) * Cylinder(
        radius_mm,
        height_mm,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )


def horizontal_port(
    x_mm: float,
    y_start_mm: float,
    z_mm: float,
    radius_mm: float,
    length_mm: float,
    toward_positive_y: bool,
) -> Any:
    from build123d import Align, Cylinder, Pos, Rot

    rotation_degrees = -90.0 if toward_positive_y else 90.0
    return (
        Pos(x_mm, y_start_mm, z_mm)
        * Rot(rotation_degrees, 0.0, 0.0)
        * Cylinder(
            radius_mm,
            length_mm,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
    )


def build_variant(variant: dict[str, Any]) -> Any:
    from build123d import Align, Cylinder, Pos, Sphere

    params = variant["cad_parameters"]
    bore_mm = float(variant["bore_mm"])
    outer_radius_mm = float(params["outer_radius_mm"])
    height_mm = float(params["head_height_mm"])
    deck_thickness_mm = float(params["deck_thickness_mm"])
    chamber_depth_mm = float(params["chamber_depth_mm"])
    fin_count = int(params["fin_count"])
    fin_thickness_mm = float(params["fin_thickness_mm"])
    fin_overhang_mm = float(params["fin_overhang_mm"])

    body = Cylinder(
        outer_radius_mm,
        height_mm,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    fin_z_values = [
        deck_thickness_mm + 5.0 + index * (height_mm - deck_thickness_mm - 10.0) / max(1, fin_count - 1)
        for index in range(fin_count)
    ]
    for z_mm in fin_z_values:
        body = body + vertical_cylinder(
            outer_radius_mm + fin_overhang_mm,
            fin_thickness_mm,
            0.0,
            0.0,
            z_mm,
        )

    chamber_radius_mm = bore_mm / 2.0
    chamber_centre_z_mm = -chamber_radius_mm + chamber_depth_mm
    body = body - Pos(0.0, 0.0, chamber_centre_z_mm) * Sphere(chamber_radius_mm)

    spark_radius_mm = float(params["spark_plug_bore_diameter_mm"]) / 2.0
    body = body - vertical_cylinder(spark_radius_mm, height_mm + 6.0, 0.0, 0.0, -3.0)

    fastener_radius_mm = float(params["fastener_hole_diameter_mm"]) / 2.0
    fastener_ring_mm = bore_mm / 2.0 + 10.0
    for angle_degrees in (45.0, 135.0, 225.0, 315.0):
        angle = math.radians(angle_degrees)
        body = body - vertical_cylinder(
            fastener_radius_mm,
            height_mm + 6.0,
            fastener_ring_mm * math.cos(angle),
            fastener_ring_mm * math.sin(angle),
            -3.0,
        )

    port_length_mm = 2.0 * (outer_radius_mm + fin_overhang_mm + 3.0)
    port_z_mm = deck_thickness_mm + 4.0
    for valve_type, diameter_key in (
        ("intake", "intake_diameter_mm"),
        ("exhaust", "exhaust_diameter_mm"),
    ):
        valve_diameter_mm = float(variant[diameter_key])
        throat_radius_mm = 0.43 * valve_diameter_mm
        stem_radius_mm = max(2.75, 0.058 * valve_diameter_mm)
        port_radius_mm = (
            float(params["port_to_valve_diameter_ratio"]) * valve_diameter_mm / 2.0
        )
        for x_mm, y_mm in variant["valve_positions_xy_mm"][valve_type]:
            body = body - vertical_cylinder(
                throat_radius_mm,
                deck_thickness_mm + 8.0,
                x_mm,
                y_mm,
                -3.0,
            )
            body = body - vertical_cylinder(
                stem_radius_mm,
                height_mm - deck_thickness_mm + 8.0,
                x_mm,
                y_mm,
                deck_thickness_mm - 3.0,
            )
            if valve_type == "intake":
                port = horizontal_port(
                    x_mm=x_mm,
                    y_start_mm=outer_radius_mm + fin_overhang_mm + 3.0,
                    z_mm=port_z_mm,
                    radius_mm=port_radius_mm,
                    length_mm=port_length_mm,
                    toward_positive_y=False,
                )
            else:
                port = horizontal_port(
                    x_mm=x_mm,
                    y_start_mm=-outer_radius_mm - fin_overhang_mm - 3.0,
                    z_mm=port_z_mm,
                    radius_mm=port_radius_mm,
                    length_mm=port_length_mm,
                    toward_positive_y=True,
                )
            body = body - port

    return body


def export_and_verify(variant: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    from build123d import export_step, export_stl, import_step

    shape = build_variant(variant)
    created_metrics = shape_metrics(shape)
    require(created_metrics["valid"], f"invalid_created_shape:{variant['id']}")
    require(created_metrics["solid_count"] == 1, f"created_shape_not_one_solid:{variant['id']}")
    require(created_metrics["all_solids_closed"], f"created_shape_not_closed:{variant['id']}")

    step_path = output_dir / f"{variant['id']}.step"
    stl_path = output_dir / f"{variant['id']}.stl"
    export_step(shape, step_path)
    canonicalize_step_header(step_path)
    export_stl(shape, stl_path, tolerance=0.08, angular_tolerance=0.08)
    require(step_path.is_file() and step_path.stat().st_size > 1000, f"missing_step:{variant['id']}")
    require(stl_path.is_file() and stl_path.stat().st_size > 1000, f"missing_stl:{variant['id']}")

    reopened = import_step(step_path)
    reopened_metrics = shape_metrics(reopened)
    require(reopened_metrics["valid"], f"invalid_reopened_step:{variant['id']}")
    require(reopened_metrics["solid_count"] == 1, f"reopened_step_not_one_solid:{variant['id']}")
    require(reopened_metrics["all_solids_closed"], f"reopened_step_not_closed:{variant['id']}")
    relative_volume_difference = abs(
        reopened_metrics["volume_mm3"] - created_metrics["volume_mm3"]
    ) / created_metrics["volume_mm3"]
    require(
        relative_volume_difference <= 1.0e-5,
        f"step_roundtrip_volume_drift:{variant['id']}:{relative_volume_difference}",
    )
    return {
        "id": variant["id"],
        "architecture": variant["architecture"],
        "scenario_id": variant["scenario_id"],
        "source_classification": "f29_clean_sheet_design_hypotheses_not_scan_or_917_fitment_geometry",
        "created_shape": created_metrics,
        "reopened_step_shape": reopened_metrics,
        "step_roundtrip_relative_volume_difference": relative_volume_difference,
        "step": {
            "path": step_path.name,
            "bytes": step_path.stat().st_size,
            "sha256": sha256(step_path),
        },
        "stl": {
            "path": stl_path.name,
            "bytes": stl_path.stat().st_size,
            "sha256": sha256(stl_path),
            "role": "derived_visual_and_meshing_input_not_manufacturing_release",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--toolchain-lock", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    study_path = args.study.resolve()
    contract_path = args.contract.resolve()
    toolchain_lock_path = args.toolchain_lock.resolve()
    output_dir = args.output_dir.resolve()
    study = load_json(study_path)
    contract = load_json(contract_path)
    toolchain_lock = load_json(toolchain_lock_path)
    require(study.get("phase") == "F29", "study_phase_must_be_f29")
    require(contract.get("phase") == "F29", "contract_phase_must_be_f29")
    require(study.get("variant_count") == 4, "study_must_contain_four_variants")
    require(
        all(value is False for value in contract["release_gates"].values()),
        "release_gates_must_remain_false",
    )
    locked_platform = toolchain_lock["image"]["platform"]
    require(locked_platform["build123d_version"] == metadata.version("build123d"), "build123d_lock_mismatch")
    require(locked_platform["cadquery_ocp_novtk_version"] == metadata.version("cadquery-ocp-novtk"), "ocp_lock_mismatch")
    output_dir.mkdir(parents=True, exist_ok=True)
    variants = [export_and_verify(variant, output_dir) for variant in study["variants"]]
    report = {
        "schema_version": "1.0.0",
        "phase": "F29",
        "status": "four_closed_concept_solids_exported_and_step_roundtrip_verified_not_fitment_or_manufacturing_validated",
        "toolchain": {
            "python": platform.python_version(),
            "build123d": metadata.version("build123d"),
            "cadquery_ocp_novtk": metadata.version("cadquery-ocp-novtk"),
            "platform_requirement": "linux/amd64_cpu",
            "lock": {
                "path": portable_path(toolchain_lock_path),
                "sha256": sha256(toolchain_lock_path),
                "immutable_image_reference": toolchain_lock["image"]["immutable_reference"],
            },
        },
        "inputs": {
            "study": {"path": portable_path(study_path), "sha256": sha256(study_path)},
            "contract": {"path": portable_path(contract_path), "sha256": sha256(contract_path)},
        },
        "variant_count": len(variants),
        "variants": variants,
        "checks": {
            "all_created_shapes_valid": all(item["created_shape"]["valid"] for item in variants),
            "all_created_shapes_one_closed_solid": all(
                item["created_shape"]["solid_count"] == 1
                and item["created_shape"]["all_solids_closed"]
                for item in variants
            ),
            "all_step_roundtrips_one_closed_solid": all(
                item["reopened_step_shape"]["solid_count"] == 1
                and item["reopened_step_shape"]["all_solids_closed"]
                for item in variants
            ),
            "scan_used": False,
            "measured_917_dimensions_used": False,
            "fitment_verified": False,
            "manufacturing_verified": False,
        },
        "release_gates": contract["release_gates"],
    }
    report_path = output_dir / "geometry-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(report_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
