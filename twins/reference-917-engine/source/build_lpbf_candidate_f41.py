#!/usr/bin/env python3
"""Construit le candidat B-Rep LPBF F41 depuis l'enveloppe F40 scan-conforme.

Le script conserve la peau exterieure du STEP fourni. Les seules modifications
geometriques sont les cavites fonctionnelles analytiques et les pilotes
sous-cotes destines a l'usinage apres impression. Les cotes F41 restent des
hypotheses de conception tant qu'elles ne sont pas confirmees sur une culasse
Porsche et sur la gamme du fondeur/imprimeur.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import gmsh
import numpy as np
import trimesh
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.StlAPI import StlAPI_Writer
from OCP.TopAbs import TopAbs_SHELL, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def unit(vector: np.ndarray) -> np.ndarray:
    length = float(np.linalg.norm(vector))
    require(length > 1.0e-9, "vecteur_nul")
    return vector / length


def add_cylinder(start: tuple[float, float, float], end: tuple[float, float, float], radius: float) -> int:
    a = np.asarray(start, dtype=float)
    b = np.asarray(end, dtype=float)
    d = b - a
    require(radius > 0.0 and float(np.linalg.norm(d)) > 0.0, "cylindre_invalide")
    return gmsh.model.occ.addCylinder(*a, *d, radius)


def add_path_tube(points: list[tuple[float, float, float]], radii: list[float]) -> list[int]:
    """Approxime un conduit lisse par cones raccordes et spheres tangentes.

    Cette construction est plus robuste pour les booleennes OCCT qu'un loft
    multi-sections dont les reperes locaux peuvent tourner de 180 degres.
    """
    require(len(points) == len(radii) and len(points) >= 2, "tube_invalide")
    vectors = [np.asarray(point, dtype=float) for point in points]
    tags: list[int] = []
    for start, end, radius_a, radius_b in zip(vectors[:-1], vectors[1:], radii[:-1], radii[1:], strict=True):
        direction = end - start
        tags.append(gmsh.model.occ.addCone(*start, *direction, radius_a, radius_b))
    for point, radius in zip(vectors[1:-1], radii[1:-1], strict=True):
        tags.append(gmsh.model.occ.addSphere(*point, radius))
    return tags


def valve_axis(centre: tuple[float, float, float], tilt_y_deg: float, length: float) -> tuple[np.ndarray, np.ndarray]:
    start = np.asarray(centre, dtype=float)
    angle = math.radians(tilt_y_deg)
    end = start + np.asarray([0.0, math.tan(angle) * length, length])
    return start, end


def build_cutters(interfaces: dict) -> tuple[list[tuple[str, list[tuple[int, int]]]], dict]:
    groups: list[tuple[str, list[tuple[int, int]]]] = []
    gas: list[int] = []

    # La sphere donne une chambre continue de rayon 45,3 mm au plan Z=0.
    gas.append(gmsh.model.occ.addSphere(0.0, 0.0, -66.0, 80.0))
    intake_paths = [
        [(-18.0, -17.0, 2.0), (-18.0, -26.0, 16.0), (-14.0, -42.0, 28.0), (-8.0, -57.0, 32.0), (0.0, -70.0, 31.0)],
        [(18.0, -17.0, 2.0), (18.0, -26.0, 16.0), (14.0, -42.0, 28.0), (8.0, -57.0, 32.0), (0.0, -70.0, 31.0)],
    ]
    exhaust_paths = [
        [(-18.0, 17.0, 2.0), (-18.0, 27.0, 18.0), (-14.0, 44.0, 31.0), (-8.0, 62.0, 40.0), (0.0, 78.0, 42.0)],
        [(18.0, 17.0, 2.0), (18.0, 27.0, 18.0), (14.0, 44.0, 31.0), (8.0, 62.0, 40.0), (0.0, 78.0, 42.0)],
    ]
    for path in intake_paths:
        gas.extend(add_path_tube(path, [12.8, 12.4, 12.0, 13.0, 16.0]))
    gas.extend(add_path_tube([(0.0, -68.0, 31.0), (0.0, -91.0, 31.0)], [18.5, 21.5]))
    for path in exhaust_paths:
        gas.extend(add_path_tube(path, [10.7, 10.5, 10.8, 12.0, 15.0]))
    gas.extend(add_path_tube([(0.0, 76.0, 42.0), (0.0, 120.0, 42.0)], [16.0, 19.5]))
    groups.append(("gas", [(3, tag) for tag in gas]))

    valve_data = {
        "intake": {
            "centres": [(-18.0, -17.0, 0.0), (18.0, -17.0, 0.0)],
            "tilt": -18.0,
            "seat_pilot_diameter": 33.98,
        },
        "exhaust": {
            "centres": [(-18.0, 17.0, 0.0), (18.0, 17.0, 0.0)],
            "tilt": 18.0,
            "seat_pilot_diameter": 28.50,
        },
    }
    valve_cutters: list[tuple[int, int]] = []
    for family in valve_data.values():
        for centre in family["centres"]:
            start, end = valve_axis(centre, family["tilt"], 96.0)
            direction = unit(end - start)
            seat_end = start + 7.0 * direction
            guide_start = start + 4.0 * direction
            guide_end = start + 68.0 * direction
            valve_cutters.append((3, add_cylinder(tuple(start - 1.4 * direction), tuple(seat_end), family["seat_pilot_diameter"] / 2.0)))
            valve_cutters.append((3, add_cylinder(tuple(guide_start), tuple(guide_end), 14.34 / 2.0)))
    groups.append(("valve_pilots", valve_cutters))

    # Deux pilotes de bougie lateraux. Le filetage M10x1 est usine apres LPBF.
    plug_centres = [(-37.0, 0.0, 0.0), (37.0, 0.0, 0.0)]
    plug_cutters: list[tuple[int, int]] = []
    for centre in plug_centres:
        sign = -1.0 if centre[0] < 0.0 else 1.0
        start = np.asarray(centre, dtype=float) - np.asarray([0.0, 0.0, 6.0])
        end = np.asarray([centre[0] + sign * 13.0, centre[1], 86.0])
        plug_cutters.append((3, add_cylinder(tuple(start), tuple(end), 4.10)))
    groups.append(("spark_plug_pilots", plug_cutters))

    # Poche ouverte a coins rayonnes et reserves verticales. La geometrie 2D
    # extrudee evite les tangences periodiques du grand cylindre precedent.
    bay_face = gmsh.model.occ.addRectangle(-44.0, -44.0, 45.0, 88.0, 88.0, roundedRadius=8.0)
    extrusion = gmsh.model.occ.extrude([(2, bay_face)], 0.0, 0.0, 44.0)
    bay_volumes = [item for item in extrusion if item[0] == 3]
    require(len(bay_volumes) == 1, f"baie_extrusion_count:{len(bay_volumes)}")
    bay = bay_volumes[0][1]
    protections = [
        (3, gmsh.model.occ.addCylinder(x, y, 43.0, 0.0, 0.0, 48.0, radius))
        for x, y, radius in (
            (-18.0, -37.5, 17.0),
            (18.0, -37.5, 17.0),
            (-18.0, 37.5, 17.0),
            (18.0, 37.5, 17.0),
            (-43.0, 0.0, 12.0),
            (43.0, 0.0, 12.0),
        )
    ]
    protected_bay, _ = gmsh.model.occ.cut([(3, bay)], protections, removeObject=True, removeTool=True)
    groups.append(("valvetrain_bay", [item for item in protected_bay if item[0] == 3]))

    chamber_centre = interfaces["combustion_interface"]["chamber_step"]["center"]
    stud_centres: list[list[float]] = []
    stud_cutters: list[tuple[int, int]] = []
    for item in interfaces["head_stud_holes_at_C_minus_91"]:
        x = float(item["center_A_B"][0]) - float(chamber_centre[0])
        y = float(item["center_A_B"][1]) - float(chamber_centre[1])
        stud_cutters.append((3, add_cylinder((x, y, -3.0), (x, y, 87.0), 5.05)))
        stud_centres.append([x, y])
    groups.append(("stud_pilots", stud_cutters))

    # Les galeries sont volontairement usinees apres impression. Les laisser
    # pleines dans le brut supprime la poudre piegee et rend leur etancheite
    # controlable par perçage, bouchonnage et epreuve hydraulique.
    oil_specs: list[tuple[tuple[float, float, float], tuple[float, float, float], float]] = [
        ((-65.0, 24.0, 44.0), (65.0, 24.0, 44.0), 2.70),
        ((-30.0, 0.0, 38.0), (-30.0, 0.0, 84.0), 3.60),
        ((30.0, 0.0, 38.0), (30.0, 0.0, 84.0), 3.60),
        ((-30.0, -96.0, 42.0), (-30.0, 0.0, 42.0), 3.60),
        ((30.0, -96.0, 42.0), (30.0, 0.0, 42.0), 3.60),
    ]
    for x in (-18.0, 18.0):
        for y in (-17.0, 17.0):
            oil_specs.append(((x, y, 44.0), (x, y, 84.0), 1.20))
            oil_specs.append(((x, min(y, 24.0), 44.0), (x, max(y, 24.0), 44.0), 1.20))
    return groups, {
        "architecture": "four_valve_twin_ignition_air_cooled",
        "valve_count": 4,
        "spark_plug_count": 2,
        "stud_count": len(stud_centres),
        "stud_centres_obj_units": stud_centres,
        "machining_stock": {
            "guide_bore_radial_mm_if_scale_is_mm": 0.30,
            "seat_bore_radial_mm_if_scale_is_mm": 0.30,
            "spark_plug_thread": "M10x1 candidate; printed pilot only",
            "stud_hole_radial_mm_if_scale_is_mm": 0.32,
        },
        "oil": {
            "printed_as_internal_cavity": False,
            "post_print_drilling_required": True,
            "straight_open_ended_after_machining": True,
            "drill_paths": [
                {"start": list(start), "end": list(end), "finished_diameter_mm_if_scale_is_mm": 2.0 * radius}
                for start, end, radius in oil_specs
            ],
        },
    }


def mesh_summary(stl_path: Path) -> dict:
    mesh = trimesh.load_mesh(stl_path, process=True)
    require(isinstance(mesh, trimesh.Trimesh), "stl_non_maillage")
    mesh.remove_unreferenced_vertices()
    return {
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "is_volume": bool(mesh.is_volume),
        "connected_components": len(mesh.split(only_watertight=False)),
        "vertices": len(mesh.vertices),
        "triangles": len(mesh.faces),
        "volume_obj_units3": float(abs(mesh.volume)),
        "surface_area_obj_units2": float(mesh.area),
        "bounds_obj_units": mesh.bounds.tolist(),
    }


def count_subshapes(shape, kind) -> int:
    explorer = TopExp_Explorer(shape, kind)
    count = 0
    while explorer.More():
        count += 1
        explorer.Next()
    return count


def tessellate_step(step_path: Path, stl_path: Path) -> dict:
    """Relit le STEP, verifie OCCT et exporte son composant surfacique utile.

    OCCT peut emettre quelques triangles nuls aux coutures d'une peau issue du
    scan. Ils sont supprimes deterministement; aucun lissage ni fermeture de
    trou n'est autorise ici.
    """
    reader = STEPControl_Reader()
    require(reader.ReadFile(str(step_path)) == IFSelect_RetDone, "relecture_STEP_echouee")
    require(reader.TransferRoots() > 0, "racine_STEP_absente")
    shape = reader.OneShape()
    roundtrip = {
        "valid": bool(BRepCheck_Analyzer(shape).IsValid()),
        "solid_count": count_subshapes(shape, TopAbs_SOLID),
        "shell_count": count_subshapes(shape, TopAbs_SHELL),
    }
    require(roundtrip == {"valid": True, "solid_count": 1, "shell_count": 1}, f"STEP_invalide:{roundtrip}")
    temporary = stl_path.with_suffix(".occt-unfiltered.stl")
    mesher = BRepMesh_IncrementalMesh(shape, 0.22, False, 0.35, True)
    mesher.Perform()
    require(bool(StlAPI_Writer().Write(shape, str(temporary))), "export_STL_OCCT_echoue")
    mesh = trimesh.load_mesh(temporary, process=True)
    require(isinstance(mesh, trimesh.Trimesh), "STL_OCCT_invalide")
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.update_faces(mesh.unique_faces())
    mesh.remove_unreferenced_vertices()
    components = mesh.split(only_watertight=False)
    require(bool(components), "STL_OCCT_vide")
    principal = max(components, key=lambda item: len(item.faces))
    discarded = [item for item in components if item is not principal]
    require(all(item.area <= 1.0e-10 for item in discarded), "composant_geometrique_non_nul_ecarte")
    require(principal.is_watertight and principal.is_volume and principal.is_winding_consistent, "STL_principal_non_etanche")
    principal.export(stl_path)
    temporary.unlink()
    roundtrip["discarded_zero_area_components"] = len(discarded)
    return roundtrip


def build(outer_step: Path, interfaces_path: Path, output: Path, mesh_size: float) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    interfaces = json.loads(interfaces_path.read_text(encoding="utf-8"))
    step_path = output / "917-head-lpbf-candidate-f41.step"
    stl_path = output / "917-head-lpbf-candidate-f41.stl"
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.option.setNumber("Geometry.OCCFixSmallEdges", 1)
        gmsh.option.setNumber("Geometry.OCCFixSmallFaces", 1)
        gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size * 0.45)
        gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size)
        gmsh.model.add("f41_lpbf_candidate")
        imported = gmsh.model.occ.importShapes(str(outer_step), highestDimOnly=True)
        outer = [item for item in imported if item[0] == 3]
        require(len(outer) == 1, f"outer_volume_count:{len(outer)}")
        cutter_groups, topology = build_cutters(interfaces)
        gmsh.model.occ.synchronize()
        current = outer
        boolean_history: list[dict] = []
        for index, (name, tools) in enumerate(cutter_groups, start=1):
            require(bool(tools), f"groupe_vide:{name}")
            result, _ = gmsh.model.occ.cut(current, tools, removeObject=True, removeTool=True)
            gmsh.model.occ.synchronize()
            present = set(gmsh.model.getEntities(3))
            volumes = [item for item in result if item[0] == 3 and item in present]
            require(bool(volumes), f"soustraction_sans_volume:{name}")
            masses = sorted(
                ((float(gmsh.model.occ.getMass(*item)), item) for item in volumes),
                reverse=True,
            )
            principal_mass, principal = masses[0]
            require(principal_mass > 500_000.0, f"volume_principal_incoherent:{name}:{principal_mass}")
            for _, item in masses[1:]:
                gmsh.model.occ.remove([item], recursive=True)
            gmsh.model.occ.synchronize()
            current = [principal]
            boolean_history.append({"group": name, "volume_obj_units3": principal_mass})
            gmsh.write(str(output / f"debug-{index:02d}-{name}.step"))
        volumes = current
        topology["boolean_history"] = boolean_history
        gmsh.write(str(step_path))
        brep = {
            "solid_count": len(volumes),
            "volume_obj_units3": float(gmsh.model.occ.getMass(*volumes[0])),
            "surface_area_obj_units2": float(sum(gmsh.model.occ.getMass(2, tag) for _, tag in gmsh.model.getEntities(2))),
        }
    finally:
        gmsh.finalize()

    step_roundtrip = tessellate_step(step_path, stl_path)
    mesh = mesh_summary(stl_path)
    require(mesh["watertight"] and mesh["is_volume"], "maillage_surface_non_etanche")
    density_g_mm3 = 2.67e-3
    report = {
        "schema_version": "1.0.0",
        "phase": "F41",
        "status": "scan_locked_functional_BRep_and_watertight_surface_complete_virtual_manufacturing_checks_pending",
        "classification": "lpbf_candidate_not_physical_release",
        "inputs": {
            "outer_step": {"path": str(outer_step), "sha256": sha256(outer_step)},
            "interfaces": {"path": str(interfaces_path), "sha256": sha256(interfaces_path)},
        },
        "topology": topology,
        "brep": brep,
        "step_roundtrip": step_roundtrip,
        "mesh": mesh,
        "material_candidate": {
            "alloy": "AlSi10Mg",
            "route": "PBF-LB/M plus stress relief, HIP conditional, solution/ageing route to be qualified",
            "density_g_cm3_assumed_for_mass_only": 2.67,
            "mass_kg_if_obj_unit_is_mm": mesh["volume_obj_units3"] * density_g_mm3 / 1000.0,
            "printed_hot_coupon_card_available": False,
        },
        "files": {
            "step": {"path": step_path.name, "sha256": sha256(step_path), "bytes": step_path.stat().st_size},
            "stl": {"path": stl_path.name, "sha256": sha256(stl_path), "bytes": stl_path.stat().st_size},
        },
        "release_gates": {
            "editable_functional_BRep_complete": True,
            "one_closed_solid_after_step_roundtrip": True,
            "continuous_wall_thickness_verified": False,
            "closed_powder_cavities_absent": False,
            "supports_generated_and_sliced": False,
            "lpbf_process_simulation_complete": False,
            "printed_hot_coupon_card_available": False,
            "ct_cnd_and_leak_test_passed": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        },
    }
    report_path = output / "917-head-lpbf-candidate-f41-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-step", type=Path, required=True)
    parser.add_argument("--interfaces", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh-size", type=float, default=3.0)
    args = parser.parse_args()
    require(1.0 <= args.mesh_size <= 6.0, "taille_maillage_hors_ecran")
    report = build(args.outer_step, args.interfaces, args.output, args.mesh_size)
    print(json.dumps({"status": report["status"], "brep": report["brep"], "mesh": report["mesh"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
