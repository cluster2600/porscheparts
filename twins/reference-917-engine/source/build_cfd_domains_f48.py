#!/usr/bin/env python3
"""Construit et maille les domaines fluides analytiques F48 avec Gmsh/OCC.

Ce script n'importe aucune peau de scan et ne construit aucun solide de culasse.
Toutes les primitives sont des cylindres circulaires fonctionnels repris du
contrat F47. Les fichiers BREP/MSH restent des artefacts locaux reproductibles;
le rapport JSON expurge peut être versionné.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import gmsh
import numpy as np


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cylinder_between(start: list[float], end: list[float], radius: float) -> tuple[int, int]:
    vector = [end[index] - start[index] for index in range(3)]
    return (3, gmsh.model.occ.addCylinder(*start, *vector, radius))


def add_physical(dimension: int, tags: list[int], name: str) -> int:
    require(bool(tags), f"patch_vide:{name}")
    group = gmsh.model.addPhysicalGroup(dimension, sorted(tags))
    gmsh.model.setPhysicalName(dimension, group, name)
    return group


def surface_record(tag: int) -> dict[str, Any]:
    bbox = [float(value) for value in gmsh.model.getBoundingBox(2, tag)]
    centre = [float(value) for value in gmsh.model.occ.getCenterOfMass(2, tag)]
    return {
        "tag": tag,
        "type": gmsh.model.getType(2, tag),
        "bbox": bbox,
        "centre": centre,
        "area": float(gmsh.model.occ.getMass(2, tag)),
    }


def constant_coordinate(record: dict[str, Any], axis: int, target: float, tolerance: float = 1.0e-5) -> bool:
    bbox = record["bbox"]
    return abs(bbox[axis] - target) <= tolerance and abs(bbox[axis + 3] - target) <= tolerance


def nearest_unused_plane(
    records: list[dict[str, Any]],
    point: list[float],
    used: set[int],
    maximum_distance: float,
) -> int:
    candidates = []
    for record in records:
        if record["tag"] in used or record["type"] != "Plane":
            continue
        distance = math.dist(record["centre"], point)
        candidates.append((distance, record["tag"]))
    require(bool(candidates), f"aucun_plan_pour:{point}")
    distance, tag = min(candidates)
    require(distance <= maximum_distance, f"plan_trop_loin:{point}:{distance}")
    return tag


def classify_gas_patches(volume: int, contract: dict, variant_name: str) -> tuple[dict[str, list[int]], list[dict[str, Any]]]:
    surfaces = sorted(tag for dimension, tag in gmsh.model.getBoundary([(3, volume)], oriented=False) if dimension == 2)
    records = [surface_record(tag) for tag in surfaces]
    used: set[int] = set()
    patches: dict[str, list[int]] = {name: [] for name in contract["patch_policy"]["required_gas_patches"]}
    variant = contract["gas_geometry_from_F47"]["variants"][variant_name]

    for valve in variant["valves"]:
        tag = nearest_unused_plane(records, valve["port_exit_xyz_scan_units"], used, 0.25)
        patches[valve["role"]].append(tag)
        used.add(tag)

    valve_z = contract["gas_geometry_from_F47"]["throat_z_end_scan_units"]
    for valve in variant["valves"]:
        x, y = valve["centre_xy_scan_units"]
        throat_radius = 0.5 * valve["head_diameter_scan_units"] * valve["throat_ratio"]
        tag = nearest_unused_plane(records, [x, y, valve_z], used, throat_radius)
        patches["valve"].append(tag)
        used.add(tag)

    bore = contract["gas_geometry_from_F47"]["bore_chamber"]
    deck_tags = [record["tag"] for record in records if record["tag"] not in used and constant_coordinate(record, 2, bore["z_start_scan_units"])]
    require(bool(deck_tags), "deck_patch_absent")
    patches["deck"].extend(deck_tags)
    used.update(deck_tags)

    chamber_tags = [record["tag"] for record in records if record["tag"] not in used and constant_coordinate(record, 2, bore["z_end_scan_units"])]
    require(bool(chamber_tags), "chamber_patch_absent")
    patches["chamber"].extend(chamber_tags)
    used.update(chamber_tags)

    radius = 0.5 * bore["diameter_scan_units"]
    bore_tags = []
    for record in records:
        if record["tag"] in used or record["type"] != "Cylinder":
            continue
        bbox = record["bbox"]
        if (
            abs(bbox[0] + radius) < 1.0e-4
            and abs(bbox[3] - radius) < 1.0e-4
            and abs(bbox[1] + radius) < 1.0e-4
            and abs(bbox[4] - radius) < 1.0e-4
        ):
            bore_tags.append(record["tag"])
    require(bool(bore_tags), "bore_patch_absent")
    patches["bore"].extend(bore_tags)
    used.update(bore_tags)

    patches["walls"] = sorted(set(surfaces) - used)
    require(bool(patches["walls"]), "walls_patch_absent")
    assigned = [tag for tags in patches.values() for tag in tags]
    require(len(assigned) == len(set(assigned)), "surface_dans_plusieurs_patches")
    require(set(assigned) == set(surfaces), "surface_non_assignee")
    return patches, records


def build_gas_geometry(contract: dict, variant_name: str) -> tuple[int, dict[str, list[int]], list[dict[str, Any]]]:
    geometry = contract["gas_geometry_from_F47"]
    bore = geometry["bore_chamber"]
    tools: list[tuple[int, int]] = [
        (
            3,
            gmsh.model.occ.addCylinder(
                0.0,
                0.0,
                bore["z_start_scan_units"],
                0.0,
                0.0,
                bore["z_end_scan_units"] - bore["z_start_scan_units"],
                0.5 * bore["diameter_scan_units"],
            ),
        )
    ]
    for valve in geometry["variants"][variant_name]["valves"]:
        x, y = valve["centre_xy_scan_units"]
        throat_radius = 0.5 * valve["head_diameter_scan_units"] * valve["throat_ratio"]
        tools.append(
            (
                3,
                gmsh.model.occ.addCylinder(
                    x,
                    y,
                    geometry["throat_z_start_scan_units"],
                    0.0,
                    0.0,
                    geometry["throat_z_end_scan_units"] - geometry["throat_z_start_scan_units"],
                    throat_radius,
                ),
            )
        )
        start = [x, y, geometry["port_start_z_scan_units"]]
        tools.append(cylinder_between(start, valve["port_exit_xyz_scan_units"], throat_radius))
    fused, _ = gmsh.model.occ.fuse([tools[0]], tools[1:], removeObject=True, removeTool=True)
    gmsh.model.occ.removeAllDuplicates()
    gmsh.model.occ.synchronize()
    volumes = gmsh.model.getEntities(3)
    require(len(fused) == 1 and len(volumes) == 1, f"domaine_gaz_pas_un_volume:{variant_name}:{volumes}")
    volume = volumes[0][1]
    patches, records = classify_gas_patches(volume, contract, variant_name)
    add_physical(3, [volume], f"fluid_gas_{variant_name}")
    for name, tags in patches.items():
        add_physical(2, tags, name)
    return volume, patches, records


def classify_oil_patches(volume: int) -> tuple[dict[str, list[int]], list[dict[str, Any]]]:
    surfaces = sorted(tag for dimension, tag in gmsh.model.getBoundary([(3, volume)], oriented=False) if dimension == 2)
    records = [surface_record(tag) for tag in surfaces]
    used: set[int] = set()
    patches = {"oil_x_minus": [], "oil_x_plus": [], "oil_cleanout": [], "oil_walls": []}
    for name, axis, target in (("oil_x_minus", 0, -70.0), ("oil_x_plus", 0, 70.0)):
        tags = [record["tag"] for record in records if constant_coordinate(record, axis, target)]
        require(len(tags) == 1, f"{name}_cap_count:{len(tags)}")
        patches[name] = tags
        used.update(tags)
    cleanout = [record["tag"] for record in records if record["tag"] not in used and constant_coordinate(record, 2, 85.0)]
    require(len(cleanout) == 2, f"oil_cleanout_cap_count:{len(cleanout)}")
    patches["oil_cleanout"] = cleanout
    used.update(cleanout)
    patches["oil_walls"] = sorted(set(surfaces) - used)
    assigned = [tag for tags in patches.values() for tag in tags]
    require(len(assigned) == len(set(assigned)) and set(assigned) == set(surfaces), "oil_patch_coverage_failed")
    return patches, records


def build_oil_geometry(contract: dict) -> tuple[int, dict[str, list[int]], list[dict[str, Any]]]:
    oil = contract["oil_geometry_from_F47"]
    main = oil["main_gallery"]
    tools = [cylinder_between(main["start_xyz_scan_units"], main["end_xyz_scan_units"], 0.5 * main["diameter_scan_units"])]
    for access in oil["vertical_cleanouts"]:
        start = access["start_xyz_scan_units"]
        tools.append(
            (
                3,
                gmsh.model.occ.addCylinder(
                    *start,
                    0.0,
                    0.0,
                    access["z_end_scan_units"] - start[2],
                    0.5 * access["diameter_scan_units"],
                ),
            )
        )
    fused, _ = gmsh.model.occ.fuse([tools[0]], tools[1:], removeObject=True, removeTool=True)
    gmsh.model.occ.removeAllDuplicates()
    gmsh.model.occ.synchronize()
    volumes = gmsh.model.getEntities(3)
    require(len(fused) == 1 and len(volumes) == 1, "domaine_huile_pas_un_volume")
    volume = volumes[0][1]
    patches, records = classify_oil_patches(volume)
    add_physical(3, [volume], "fluid_oil")
    for name, tags in patches.items():
        add_physical(2, tags, name)
    return volume, patches, records


def configure_mesh(characteristic_length: float) -> None:
    gmsh.option.setNumber("General.NumThreads", 1)
    gmsh.option.setNumber("Mesh.MaxNumThreads1D", 1)
    gmsh.option.setNumber("Mesh.MaxNumThreads2D", 1)
    gmsh.option.setNumber("Mesh.MaxNumThreads3D", 1)
    gmsh.option.setNumber("Mesh.Algorithm", 6)
    gmsh.option.setNumber("Mesh.Algorithm3D", 1)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", 0.35 * characteristic_length)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", characteristic_length)
    gmsh.option.setNumber("Mesh.CharacteristicLengthFromCurvature", 1)
    gmsh.option.setNumber("Mesh.MinimumCirclePoints", 18)
    gmsh.option.setNumber("Mesh.Optimize", 1)
    gmsh.option.setNumber("Mesh.RandomFactor", 1.0e-9)


def tetrahedron_tags() -> list[int]:
    result: list[int] = []
    types, tags_by_type, _ = gmsh.model.mesh.getElements(3)
    for element_type, tags in zip(types, tags_by_type):
        properties = gmsh.model.mesh.getElementProperties(element_type)
        if properties[0].startswith("Tetrahedron"):
            result.extend(int(tag) for tag in tags)
    return result


def surface_element_count(tags: list[int]) -> int:
    total = 0
    for tag in tags:
        _, element_tags, _ = gmsh.model.mesh.getElements(2, tag)
        total += sum(len(items) for items in element_tags)
    return int(total)


def mesh_metrics(volume: int, patches: dict[str, list[int]], mesh_path: Path) -> dict[str, Any]:
    gmsh.model.mesh.generate(3)
    gmsh.model.mesh.optimize("Relocate3D")
    tetrahedra = tetrahedron_tags()
    require(bool(tetrahedra), "aucun_tetraedre")
    quality = np.sort(np.asarray(gmsh.model.mesh.getElementQualities(tetrahedra, "minSICN"), dtype=float))
    determinant = np.asarray(gmsh.model.mesh.getElementQualities(tetrahedra, "minDetJac"), dtype=float)
    node_tags, _, _ = gmsh.model.mesh.getNodes()
    gmsh.write(str(mesh_path))
    return {
        "msh_sha256": sha256(mesh_path),
        "msh_bytes": mesh_path.stat().st_size,
        "node_count": int(len(node_tags)),
        "tetrahedron_count": int(len(tetrahedra)),
        "minimum_minSICN": float(quality[0]),
        "p01_minSICN": float(np.quantile(quality, 0.01)),
        "p05_minSICN": float(np.quantile(quality, 0.05)),
        "median_minSICN": float(np.quantile(quality, 0.5)),
        "mean_minSICN": float(np.mean(quality)),
        "count_minSICN_le_0": int(np.sum(quality <= 0.0)),
        "count_minSICN_lt_0_1": int(np.sum(quality < 0.1)),
        "minimum_minDetJac": float(np.min(determinant)),
        "volume_scan_units_cubed": float(gmsh.model.occ.getMass(3, volume)),
        "patches": {
            name: {
                "surface_count": len(tags),
                "surface_area_scan_units_squared": float(sum(gmsh.model.occ.getMass(2, tag) for tag in tags)),
                "triangle_count": surface_element_count(tags),
            }
            for name, tags in sorted(patches.items())
        },
    }


def build_case(contract: dict, kind: str, variant: str, level: str, output: Path) -> dict[str, Any]:
    gmsh.clear()
    gmsh.model.add(f"f48_{kind}_{variant}_{level}")
    if kind == "gas":
        volume, patches, records = build_gas_geometry(contract, variant)
    else:
        volume, patches, records = build_oil_geometry(contract)
    length = contract["mesh_matrix"]["levels"][level]["characteristic_length_max_scan_units"]
    configure_mesh(length)
    prefix = output / f"917-f48-{kind}-{variant.lower()}-{level}"
    brep_path = prefix.with_suffix(".brep")
    if level == "medium":
        gmsh.write(str(brep_path))
    mesh_path = prefix.with_suffix(".msh")
    metrics = mesh_metrics(volume, patches, mesh_path)
    metrics.update(
        {
            "kind": kind,
            "variant": variant,
            "level": level,
            "characteristic_length_max_scan_units": length,
            "one_volume": len(gmsh.model.getEntities(3)) == 1,
            "boundary_surface_count": len(records),
            "patch_surface_coverage_count": sum(len(tags) for tags in patches.values()),
            "all_boundary_surfaces_assigned_once": sum(len(tags) for tags in patches.values()) == len(records),
            "symmetry_patch": "not_applicable_full_domain",
            "geometry_brep": (
                {"sha256": sha256(brep_path), "bytes": brep_path.stat().st_size}
                if level == "medium"
                else None
            ),
            "repository_policy": "generated_analytic_BREP_and_MSH_local_not_committed",
        }
    )
    return metrics


def apply_quality_gates(contract: dict, report: dict[str, Any]) -> None:
    gates = contract["mesh_matrix"]["quality_gates"]
    for variant, meshes in report["gas_domains"].items():
        volumes = [mesh["volume_scan_units_cubed"] for mesh in meshes.values()]
        spread = (max(volumes) - min(volumes)) / max(volumes)
        report["comparability"][variant] = {
            "volume_relative_spread": spread,
            "volume_gate": spread <= gates["volume_relative_spread_at_most"],
            "same_characteristic_lengths_as_other_variant": True,
        }
        for mesh in meshes.values():
            mesh["quality_gates"] = {
                "no_inverted_tetrahedra": mesh["count_minSICN_le_0"] == gates["count_minSICN_le_0"],
                "minimum_positive": mesh["minimum_minSICN"] > gates["minimum_minSICN_strictly_above"],
                "p01_at_least_0_1": mesh["p01_minSICN"] >= gates["p01_minSICN_at_least"],
            }
            mesh["quality_gates"]["pass"] = all(mesh["quality_gates"].values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    require(contract["phase"] == "F48", "contrat_non_F48")
    require(sha256(Path(contract["authority"]["F47_contract"]["path"])) == contract["authority"]["F47_contract"]["sha256"], "hash_F47_incorrect")
    args.output.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("Geometry.Tolerance", 1.0e-7)
        report: dict[str, Any] = {
            "schema": "porsche-917-f48-cfd-domains/v1",
            "phase": "F48",
            "contract": {"sha256": sha256(args.contract)},
            "builder": {"sha256": sha256(Path(__file__))},
            "toolchain": {"gmsh": gmsh.__version__, "numpy": np.__version__},
            "construction": {
                "outer_scan_or_skin_imported": False,
                "solid_head_generated": False,
                "ellipse_or_oval_profile_or_surface_primitive_used": False,
                "OCC_generated_conic_intersection_edges_may_be_named_Ellipse": True,
                "proxy_envelope_used": False,
                "functional_circular_cylinders_only": True,
                "full_domain_no_symmetry_plane": True,
                "spark_plug_flow_volume_excluded": True,
            },
            "gas_domains": {"2V": {}, "4V": {}},
            "oil_domain": {},
            "comparability": {},
            "release_gates": contract["release_gates"],
        }
        for variant in ("2V", "4V"):
            for level in ("coarse", "medium", "fine"):
                report["gas_domains"][variant][level] = build_case(contract, "gas", variant, level, args.output)
        report["oil_domain"] = build_case(contract, "oil", "COMMON", "medium", args.output)
        apply_quality_gates(contract, report)
        report["oil_domain"]["liquid_coolant_jacket"] = False
        report["oil_domain"]["separate_lubrication_domain_only"] = True
        all_meshes = [mesh for variants in report["gas_domains"].values() for mesh in variants.values()]
        report["CFD_domain_gate"] = {
            "pass": all(mesh["quality_gates"]["pass"] for mesh in all_meshes),
            "does_not_open_fitment_or_manufacturing_gates": True,
        }
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, sort_keys=True))
    finally:
        gmsh.finalize()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
