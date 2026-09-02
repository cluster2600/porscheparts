#!/usr/bin/env python3
"""Construit la culasse F34 4V a ailettes; prototype CAO, jamais release moteur."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import gmsh


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vector_from_tilt_y(length: float, tilt_deg: float) -> tuple[float, float, float]:
    angle = math.radians(tilt_deg)
    return (0.0, length * math.sin(angle), length * math.cos(angle))


def fuse_all(occ, volumes: list[int]) -> list[tuple[int, int]]:
    if not volumes:
        raise ValueError("aucun volume a fusionner")
    result = [(3, volumes[0])]
    for tag in volumes[1:]:
        result, _ = occ.fuse(result, [(3, tag)], removeObject=True, removeTool=True)
    return result


def build_head(contract: dict, output: Path, mesh_size_mm: float) -> dict:
    cfg = contract["cad"]
    fin = cfg["fin"]
    valves = cfg["valves"]
    output.mkdir(parents=True, exist_ok=False)

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.option.setNumber("Geometry.Tolerance", 1e-7)
        gmsh.option.setNumber("Geometry.OCCFixSmallEdges", 1)
        gmsh.option.setNumber("Geometry.OCCFixSmallFaces", 1)
        gmsh.model.add("f34_aircooled_4v_head")
        occ = gmsh.model.occ

        width = cfg["body_width_mm"]
        depth = cfg["body_depth_mm"]
        height = cfg["body_height_mm"]
        deck = cfg["deck_thickness_mm"]
        register_radius = cfg["register_diameter_mm"] / 2.0

        solids: list[int] = []
        solids.append(occ.addCylinder(0.0, 0.0, 0.0, 0.0, 0.0, deck + 9.0, register_radius + 3.0))
        solids.append(occ.addBox(-width / 2.0, -depth / 2.0, deck - 2.0, width, depth, height - deck + 2.0))
        solids.append(occ.addCylinder(0.0, 0.0, deck, 0.0, 0.0, height - deck, 67.0))

        for index in range(fin["count"]):
            z = 10.0 + index * fin["pitch_mm"]
            taper = max(0.0, (z - 70.0) * 0.16)
            fin_width = fin["maximum_width_mm"] - taper
            fin_depth = fin["maximum_depth_mm"] - 0.75 * taper
            solids.append(
                occ.addBox(
                    -fin_width / 2.0,
                    -fin_depth / 2.0,
                    z,
                    fin_width,
                    fin_depth,
                    fin["thickness_mm"],
                )
            )

        # Bossages lateraux conformes a la morphologie generale du scan 935.
        for x, _ in valves["intake"]["positions_xy_mm"]:
            solids.append(occ.addCylinder(x, 54.0, 37.0, 0.0, 48.0, -7.0, 20.0))
        for x, _ in valves["exhaust"]["positions_xy_mm"]:
            solids.append(occ.addCylinder(x, -54.0, 33.0, 0.0, -45.0, -9.0, 17.5))

        # Plateau superieur separe conceptuellement du futur porte-arbres usine.
        solids.append(occ.addBox(-61.0, -56.0, 88.0, 122.0, 112.0, 17.0))
        outer = fuse_all(occ, solids)

        # Domaine CFD de refroidissement: même peau extérieure et mêmes ailettes,
        # mais conduits, guides, bougie, goujons et retours sont obturés. L'air
        # de refroidissement ne doit jamais être confondu avec les fluides moteur.
        occ.removeAllDuplicates()
        occ.synchronize()
        external_surface_area_mm2 = sum(
            occ.getMass(dim, tag) for dim, tag in gmsh.model.getEntities(2)
        )
        external_stl_path = output / "917-head-aircooled-4v-f34-external-cooling-envelope.stl"
        gmsh.option.setNumber("Mesh.MeshSizeMin", 0.55 * mesh_size_mm)
        gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size_mm)
        gmsh.option.setNumber("Mesh.Algorithm", 6)
        gmsh.model.mesh.generate(2)
        gmsh.write(str(external_stl_path))
        external_node_count = len(gmsh.model.mesh.getNodes()[0])
        external_element_count = sum(
            len(tags) for tags in gmsh.model.mesh.getElements(2)[1]
        )
        gmsh.model.mesh.clear()

        cuts: list[tuple[int, int]] = []
        chamber_radius = 57.0
        chamber_center_z = -(chamber_radius - cfg["combustion_chamber"]["depth_mm"])
        cuts.append((3, occ.addSphere(0.0, 0.0, chamber_center_z, chamber_radius)))
        cuts.append((3, occ.addCylinder(0.0, 0.0, -2.0, 0.0, 0.0, height + 12.0, 5.2)))

        for kind in ("intake", "exhaust"):
            data = valves[kind]
            guide_radius = data["stem_diameter_mm"] / 2.0 + 0.18
            tilt = data["axis_tilt_y_deg"]
            axis = vector_from_tilt_y(125.0, tilt)
            seat_axis = vector_from_tilt_y(18.0, tilt)
            seat_radius = 0.485 * data["head_diameter_mm"]
            throat_radius = 0.42 * data["head_diameter_mm"]
            for x, y in data["positions_xy_mm"]:
                cuts.append((3, occ.addCylinder(x, y, -2.0, *seat_axis, seat_radius)))
                cuts.append((3, occ.addCylinder(x, y, 2.0, *axis, guide_radius)))
                throat_axis = vector_from_tilt_y(34.0, tilt)
                cuts.append((3, occ.addCylinder(x, y, -1.0, *throat_axis, throat_radius)))

        for x, y in valves["intake"]["positions_xy_mm"]:
            cuts.append((3, occ.addCylinder(x, 101.0, 39.0, 0.0, -88.0, -25.0, 11.8)))
        for x, y in valves["exhaust"]["positions_xy_mm"]:
            cuts.append((3, occ.addCylinder(x, -101.0, 34.0, 0.0, 88.0, -23.0, 9.8)))

        half_x = cfg["stud_span_x_mm"] / 2.0
        half_y = cfg["stud_span_y_mm"] / 2.0
        for x in (-half_x, half_x):
            for y in (-half_y, half_y):
                cuts.append(
                    (
                        3,
                        occ.addCylinder(
                            x,
                            y,
                            -3.0,
                            0.0,
                            0.0,
                            height + 14.0,
                            cfg["stud_hole_diameter_mm"] / 2.0,
                        ),
                    )
                )

        # Retours d'huile et evacuations de poudre, ouverts sur deux faces.
        for x in (-54.0, 54.0):
            cuts.append((3, occ.addCylinder(x, 0.0, -3.0, 0.0, 0.0, height + 14.0, 4.5)))
        cuts.append((3, occ.addCylinder(0.0, 49.0, -3.0, 0.0, 0.0, height + 14.0, 4.0)))

        head, _ = occ.cut(outer, cuts, removeObject=True, removeTool=True)
        occ.removeAllDuplicates()
        occ.synchronize()
        volumes = gmsh.model.getEntities(3)
        if len(volumes) != 1 or not head:
            raise RuntimeError(f"la CAO F34 doit etre un solide unique, obtenu={len(volumes)}")

        bbox = gmsh.model.getBoundingBox(3, volumes[0][1])
        volume_mm3 = occ.getMass(3, volumes[0][1])
        surface_area_mm2 = sum(occ.getMass(dim, tag) for dim, tag in gmsh.model.getEntities(2))

        step_path = output / "917-head-aircooled-4v-f34.step"
        stl_path = output / "917-head-aircooled-4v-f34.stl"
        gmsh.write(str(step_path))
        gmsh.model.mesh.generate(2)
        gmsh.write(str(stl_path))
        node_count = len(gmsh.model.mesh.getNodes()[0])
        element_count = sum(len(tags) for tags in gmsh.model.mesh.getElements(2)[1])
    finally:
        gmsh.finalize()

    report = {
        "schema_version": "1.0.0",
        "phase": "F34",
        "status": "editable_aircooled_4v_process_prototype_generated_not_engine_release_cad",
        "classification": cfg["classification"],
        "geometry": {
            "solid_count": 1,
            "volume_mm3": volume_mm3,
            "external_and_internal_surface_area_m2": surface_area_mm2 * 1e-6,
            "bounding_box_mm": {
                "min": list(bbox[:3]),
                "max": list(bbox[3:]),
                "size": [bbox[3] - bbox[0], bbox[4] - bbox[1], bbox[5] - bbox[2]],
            },
            "surface_nodes": node_count,
            "surface_elements": element_count,
            "external_cooling_envelope": {
                "classification": "sealed_external_air_domain_surface_not_functional_part_mesh",
                "surface_area_m2": external_surface_area_mm2 * 1e-6,
                "surface_nodes": external_node_count,
                "surface_elements": external_element_count,
                "internal_engine_openings_sealed": True,
            },
            "mesh_size_max_mm": mesh_size_mm,
            "fin_count": fin["count"],
            "valve_count": valves["intake"]["count"] + valves["exhaust"]["count"],
            "stud_pattern_mm": [cfg["stud_span_x_mm"], cfg["stud_span_y_mm"]],
            "register_diameter_mm": cfg["register_diameter_mm"],
        },
        "interfaces": {
            "scan_seeded": ["register_diameter", "chamber_step_diameter", "stud_pattern", "stud_hole_diameter"],
            "design_hypotheses": ["all_4v_internal_geometry", "ports", "guides", "fins", "top_deck", "oil_returns"],
            "absolute_scale_confirmed": False,
            "porsche_917_fit_confirmed": False,
        },
        "manufacturing": {
            "sealed_internal_cavities": 0,
            "minimum_powder_escape_diameter_mm": cfg["powder_strategy"]["minimum_escape_diameter_mm"],
            "machining_allowance_target_mm": cfg["minimum_wall_targets_mm"]["machining_allowance_on_datums"],
            "metal_print_authorized": False,
            "engine_use_authorized": False,
        },
        "files": {
            "step": {"path": step_path.name, "bytes": step_path.stat().st_size, "sha256": sha256(step_path)},
            "stl": {"path": stl_path.name, "bytes": stl_path.stat().st_size, "sha256": sha256(stl_path)},
            "external_cooling_envelope_stl": {
                "path": external_stl_path.name,
                "bytes": external_stl_path.stat().st_size,
                "sha256": sha256(external_stl_path),
            },
        },
        "excluded_from_release_cad": cfg["excluded_from_release_cad"],
        "release_gates": contract["release_gates"],
    }
    report_path = output / "geometry-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh-size-mm", type=float, default=2.4)
    args = parser.parse_args()
    contract = load_json(args.contract)
    if contract.get("phase") != "F34":
        raise SystemExit("phase F34 requise")
    if args.mesh_size_mm <= 0.0:
        raise SystemExit("mesh size must be positive")
    report = build_head(contract, args.output.resolve(), args.mesh_size_mm)
    print(json.dumps({"status": report["status"], "geometry": report["geometry"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
