#!/usr/bin/env python3
"""Construit les candidats internes F47 2V/4V dans une peau F43 privée.

La peau externe est importée octet pour octet et n'est jamais recréée. Toutes
les nouvelles géométries sont des cylindres circulaires fonctionnels : alésage,
chambre/deck de premier ordre, poches de sièges, gorges, guides, bougie,
conduits droits et galeries d'huile. Aucun corps, ailette, chambre ou raccord
elliptique/ovale n'est généré.

Les STEP produits sont dérivés du scan et restent locaux. Ce constructeur ne
ferme aucune porte de fabrication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import gmsh


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonicalize_step(path: Path) -> None:
    payload = path.read_text(encoding="utf-8")
    payload, count = re.subn(
        r"(FILE_NAME\([^,]+,')[^']+(')",
        r"\g<1>1970-01-01T00:00:00\g<2>",
        payload,
        count=1,
    )
    require(count == 1, "STEP_timestamp_missing")
    path.write_text(payload, encoding="utf-8", newline="\n")


def cylinder_between(start: list[float], end: list[float], radius: float) -> tuple[int, int]:
    vector = [end[index] - start[index] for index in range(3)]
    return (3, gmsh.model.occ.addCylinder(*start, *vector, radius))


def add_gas_tools(contract: dict, variant: dict) -> tuple[list[tuple[int, int]], list[dict]]:
    common = contract["common_candidate_geometry"]
    bore = common["bore"]
    tools = [
        (
            3,
            gmsh.model.occ.addCylinder(
                0.0,
                0.0,
                bore["z_start_mm"],
                0.0,
                0.0,
                bore["z_end_mm"] - bore["z_start_mm"],
                0.5 * bore["diameter_mm"],
            ),
        )
    ]
    features = [{"id": "circular_bore_chamber", "open_boundary": "deck_bottom"}]
    for valve in variant["valves"]:
        x, y = valve["centre_xy_mm"]
        seat_radius = 0.5 * valve["seat_envelope_diameter_mm"]
        throat_radius = 0.5 * valve["head_diameter_mm"] * valve["throat_ratio"]
        tools.append(
            (
                3,
                gmsh.model.occ.addCylinder(
                    x,
                    y,
                    common["seat_counterbore_z_start_mm"],
                    0.0,
                    0.0,
                    common["seat_counterbore_depth_mm"],
                    seat_radius,
                ),
            )
        )
        tools.append(
            (
                3,
                gmsh.model.occ.addCylinder(
                    x,
                    y,
                    common["throat_z_start_mm"],
                    0.0,
                    0.0,
                    common["throat_z_end_mm"] - common["throat_z_start_mm"],
                    throat_radius,
                ),
            )
        )
        tools.append(
            (
                3,
                gmsh.model.occ.addCylinder(
                    x,
                    y,
                    common["guide_bore_z_start_mm"],
                    0.0,
                    0.0,
                    common["guide_bore_z_end_mm"] - common["guide_bore_z_start_mm"],
                    0.5 * common["guide_bore_diameter_mm"],
                ),
            )
        )
        port_start = [x, y, 12.0]
        port_end = [x, valve["port_exit_y_mm"], valve["port_exit_z_mm"]]
        tools.append(cylinder_between(port_start, port_end, throat_radius))
        features.extend(
            [
                {"id": f"{valve['id']}_seat_and_throat", "open_boundary": "chamber"},
                {"id": f"{valve['id']}_guide", "open_boundary": "top"},
                {
                    "id": f"{valve['id']}_port",
                    "open_boundary": f"{valve['role']}_side",
                    "circular_section_radius_mm": throat_radius,
                },
            ]
        )
    plug = variant["spark_plug"]
    px, py = plug["centre_xy_mm"]
    tools.append(
        (
            3,
            gmsh.model.occ.addCylinder(
                px,
                py,
                common["spark_bore_z_start_mm"],
                0.0,
                0.0,
                common["spark_bore_z_end_mm"] - common["spark_bore_z_start_mm"],
                0.5 * plug["diameter_mm"],
            ),
        )
    )
    features.append({"id": "spark_plug_bore", "open_boundary": "top_and_chamber"})
    return tools, features


def add_oil_tools(contract: dict) -> tuple[list[tuple[int, int]], list[dict]]:
    oil = contract["common_candidate_geometry"]["oil_domain"]
    main = oil["main_gallery"]
    tools = [cylinder_between(main["start_xyz_mm"], main["end_xyz_mm"], 0.5 * main["diameter_mm"])]
    features = [{"id": "main_oil_gallery", "open_boundary": "both_x_sides"}]
    for index, access in enumerate(oil["vertical_cleanout_accesses"], start=1):
        x, y, z = access["xyz_mm"]
        tools.append(
            (
                3,
                gmsh.model.occ.addCylinder(
                    x,
                    y,
                    z,
                    0.0,
                    0.0,
                    access["z_end_mm"] - z,
                    0.5 * access["diameter_mm"],
                ),
            )
        )
        features.append({"id": f"oil_cleanout_{index}", "open_boundary": "top"})
    return tools, features


def write_current_model(path: Path) -> dict:
    gmsh.model.occ.synchronize()
    volumes = gmsh.model.getEntities(3)
    require(bool(volumes), "model_has_no_volume")
    gmsh.write(str(path))
    canonicalize_step(path)
    return {
        "filename": path.name,
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "solid_count": len(volumes),
        "volume_mm3_under_scan_unit_convention": sum(gmsh.model.occ.getMass(*volume) for volume in volumes),
        "repository_policy": "private_local_only",
    }


def build_closed_domain(
    contract: dict,
    variant: dict,
    domain: str,
    output_path: Path,
) -> tuple[dict, list[dict]]:
    gmsh.clear()
    gmsh.model.add(f"f47_{variant['variant_id']}_{domain}")
    if domain == "gas":
        tools, features = add_gas_tools(contract, variant)
    else:
        tools, features = add_oil_tools(contract)
    result, _ = gmsh.model.occ.fuse([tools[0]], tools[1:], removeObject=True, removeTool=True)
    gmsh.model.occ.removeAllDuplicates()
    gmsh.model.occ.synchronize()
    volumes = gmsh.model.getEntities(3)
    require(len(result) == 1 and len(volumes) == 1, f"{domain}_domain_not_one_closed_solid:{len(volumes)}")
    return write_current_model(output_path), features


def build_head(
    outer_step: Path,
    contract: dict,
    variant: dict,
    output_path: Path,
) -> dict:
    gmsh.clear()
    gmsh.model.add(f"f47_{variant['variant_id']}_head")
    outer = gmsh.model.occ.importShapes(str(outer_step), highestDimOnly=True)
    require(len(outer) == 1 and outer[0][0] == 3, "outer_F43_not_one_solid")
    gas, _ = add_gas_tools(contract, variant)
    oil, _ = add_oil_tools(contract)
    result, _ = gmsh.model.occ.cut(outer, gas + oil, removeObject=True, removeTool=True)
    gmsh.model.occ.removeAllDuplicates()
    gmsh.model.occ.synchronize()
    require(len(result) == 1 and len(gmsh.model.getEntities(3)) == 1, "head_boolean_not_one_solid")
    return write_current_model(output_path)


def ring(x: float, y: float, z: float, height: float, outer_radius: float, inner_radius: float) -> tuple[int, int]:
    outer = (3, gmsh.model.occ.addCylinder(x, y, z, 0.0, 0.0, height, outer_radius))
    inner = (3, gmsh.model.occ.addCylinder(x, y, z - 0.5, 0.0, 0.0, height + 1.0, inner_radius))
    result, _ = gmsh.model.occ.cut([outer], [inner], removeObject=True, removeTool=True)
    require(len(result) == 1, "insert_ring_boolean_failed")
    return result[0]


def build_components(contract: dict, variant: dict, output_path: Path) -> dict:
    common = contract["common_candidate_geometry"]
    gmsh.clear()
    gmsh.model.add(f"f47_{variant['variant_id']}_purchased_components")
    for valve in variant["valves"]:
        x, y = valve["centre_xy_mm"]
        seat_outer = 0.5 * valve["seat_envelope_diameter_mm"]
        seat_inner = 0.5 * valve["head_diameter_mm"]
        ring(x, y, 6.0, common["seat_counterbore_depth_mm"], seat_outer, seat_inner)
        ring(
            x,
            y,
            common["guide_bore_z_start_mm"],
            common["guide_insert_length_mm"],
            0.5 * common["guide_bore_diameter_mm"],
            0.5 * common["guide_insert_inner_diameter_mm"],
        )
        head = (3, gmsh.model.occ.addCylinder(x, y, 4.0, 0.0, 0.0, 2.5, 0.5 * valve["head_diameter_mm"]))
        stem = (3, gmsh.model.occ.addCylinder(x, y, 6.0, 0.0, 0.0, 64.0, 3.5))
        fused, _ = gmsh.model.occ.fuse([head], [stem], removeObject=True, removeTool=True)
        require(len(fused) == 1, "valve_boolean_failed")
    gmsh.model.occ.synchronize()
    expected = 3 * len(variant["valves"])
    require(len(gmsh.model.getEntities(3)) == expected, "component_solid_count_mismatch")
    result = write_current_model(output_path)
    result["seat_count"] = len(variant["valves"])
    result["guide_count"] = len(variant["valves"])
    result["valve_count"] = len(variant["valves"])
    result["component_route"] = "separate_purchased_finish_machined_not_printed"
    return result


def build_variant(outer_step: Path, contract: dict, variant_name: str, output_dir: Path) -> dict:
    variant = contract["variants"][variant_name]
    prefix = f"917-head-{variant_name}-f47"
    gas, gas_features = build_closed_domain(contract, variant, "gas", output_dir / f"{prefix}-gas-core.step")
    oil, oil_features = build_closed_domain(contract, variant, "oil", output_dir / f"{prefix}-oil-core.step")
    head = build_head(outer_step, contract, variant, output_dir / f"{prefix}-head.step")
    components = build_components(contract, variant, output_dir / f"{prefix}-components.step")
    return {
        "variant_id": variant["variant_id"],
        "head": head,
        "gas_core": gas,
        "oil_core": oil,
        "components": components,
        "gas_open_features": gas_features,
        "oil_open_features": oil_features,
        "release": {
            "BRep_validated": False,
            "minimum_wall_1_5_mm_verified": False,
            "powder_removal_verified": False,
            "metal_print_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-step", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    require(contract.get("phase") == "F47", "contract_not_F47")
    expected = contract["authority"]["outer_skin_f43_private"]["sha256"]
    require(sha256(args.outer_step) == expected, "outer_F43_SHA256_mismatch")
    args.output.mkdir(parents=True, exist_ok=True)

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.option.setNumber("Geometry.Tolerance", 1.0e-6)
        gmsh.option.setNumber("Geometry.OCCBooleanPreserveNumbering", 0)
        variants = {
            name: build_variant(args.outer_step, contract, name, args.output)
            for name in ("2v", "4v")
        }
    finally:
        gmsh.finalize()

    report = {
        "schema": "porsche-917-f47-private-build/v1",
        "phase": "F47",
        "outer_F43": {
            "sha256": expected,
            "same_source_bytes_for_both_variants": True,
            "surface_deformation_operation_used": False,
        },
        "construction": {
            "global_ellipse_used": False,
            "global_oval_used": False,
            "global_box_used": False,
            "functional_circular_cylinders_only": True,
        },
        "variants": variants,
        "repository_policy": "all_STEP_and_coordinate_bearing_private_reports_local_only",
        "metal_print_authorized": False,
    }
    report_path = args.output / "917-head-2v-4v-f47-private-build.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
