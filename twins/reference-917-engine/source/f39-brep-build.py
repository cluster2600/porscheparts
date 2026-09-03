#!/usr/bin/env python3
"""Reconstruit une culasse F39 analytique depuis les seules conventions du scan.

Le script utilise OpenCASCADE via Gmsh. Le STEP obtenu est un proxy parametrique
maillable, pas une definition OEM ni une autorisation de fabrication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from collections import defaultdict

import gmsh


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def canonicalize_step(path: Path) -> None:
    payload = path.read_text(encoding="utf-8")
    payload, count = re.subn(
        r"(FILE_NAME\([^,]+,')[^']+(')",
        r"\g<1>1970-01-01T00:00:00\g<2>",
        payload,
        count=1,
    )
    require(count == 1, "STEP_timestamp_not_found")
    path.write_text(payload, encoding="utf-8", newline="\n")


def ellipse_volume(occ: object, x: float, y: float, z: float, rx: float, ry: float, height: float) -> int:
    """Extrusion d'une ellipse OCCT analytique continue."""

    if rx >= ry:
        surface = occ.addDisk(x, y, z, rx, ry)
    else:
        surface = occ.addDisk(x, y, z, ry, rx)
        occ.rotate([(2, surface)], x, y, z, 0.0, 0.0, 1.0, math.pi / 2.0)
    result = occ.extrude([(2, surface)], 0.0, 0.0, height)
    volumes = [tag for dim, tag in result if dim == 3]
    require(len(volumes) == 1, "ellipse_extrusion_failed")
    return volumes[0]


def fuse_all(occ: object, tags: list[int]) -> list[tuple[int, int]]:
    require(bool(tags), "empty_fusion")
    result = [(3, tags[0])]
    for tag in tags[1:]:
        result, _ = occ.fuse(result, [(3, tag)], removeObject=True, removeTool=True)
    return result


def vector_from_tilt(length: float, tilt_y_deg: float) -> tuple[float, float, float]:
    angle = math.radians(tilt_y_deg)
    return 0.0, length * math.sin(angle), length * math.cos(angle)


def add_outer(occ: object, contract: dict) -> list[tuple[int, int]]:
    outer = contract["outer_reconstruction"]
    z_min = contract["scan_reference_envelope_units"]["minimum"][2]
    z_max = contract["scan_reference_envelope_units"]["maximum"][2]
    centre_y = float(outer["body_centre_y_mm_by_convention"])
    solids: list[int] = [occ.addCylinder(0.0, 0.0, z_min, 0.0, 0.0, 15.0, float(outer["deck_outer_radius_mm"]))]
    lower_rx, lower_ry = map(float, outer["lower_core_radii_xy_mm"])
    upper_rx, upper_ry = map(float, outer["upper_core_radii_xy_mm"])
    solids.append(ellipse_volume(occ, 0.0, centre_y, -3.0, lower_rx, lower_ry, 58.0))
    solids.append(ellipse_volume(occ, 0.0, centre_y, 40.0, upper_rx, upper_ry, 35.0))

    count = int(outer["fin_count"])
    for index in range(count):
        fraction = index / max(1, count - 1)
        rx = (1.0 - fraction) * float(outer["fin_radii_xy_bottom_mm"][0]) + fraction * float(outer["fin_radii_xy_top_mm"][0])
        ry = (1.0 - fraction) * float(outer["fin_radii_xy_bottom_mm"][1]) + fraction * float(outer["fin_radii_xy_top_mm"][1])
        z = float(outer["fin_first_z_mm"]) + index * float(outer["fin_pitch_mm"])
        solids.append(ellipse_volume(occ, 0.0, centre_y, z, rx, ry, float(outer["fin_thickness_mm"])))

    studs = ((-43.3490155, 42.9033462), (-42.8471493, -42.7873019), (43.1002817, 43.1285358), (43.3937545, -42.4446394))
    for x, y in studs:
        solids.append(occ.addCylinder(x, y, 47.0, 0.0, 0.0, z_max - 47.0, 13.5))

    for x in (-18.0, 18.0):
        solids.append(occ.addCylinder(x, -89.625, 32.0, 0.0, 47.0, -12.0, float(outer["intake_boss_outer_radius_mm"])))
        solids.append(occ.addCylinder(x, 63.0, 23.0, 0.0, 53.625, 19.0, float(outer["exhaust_boss_outer_radius_mm"])))
    return fuse_all(occ, solids)


def add_gas_cutters(occ: object, contract: dict) -> list[tuple[int, int]]:
    cfg = contract["functional_geometry"]
    cutters: list[tuple[int, int]] = []
    chamber = cfg["chamber_conical_frustum_mm"]
    cutters.append(
        (
            3,
            occ.addCone(
                0.0,
                0.0,
                float(chamber["start_z"]),
                0.0,
                0.0,
                float(chamber["height"]),
                float(chamber["opening_radius"]),
                float(chamber["roof_radius"]),
            ),
        )
    )
    families = (
        (cfg["intake_centres_mm"], -18.0, float(cfg["intake_seat_pocket_radius_mm"]), float(cfg["intake_port_radius_mm"]), (-96.0, 33.0)),
        (cfg["exhaust_centres_mm"], 18.0, float(cfg["exhaust_seat_pocket_radius_mm"]), float(cfg["exhaust_port_radius_mm"]), (122.0, 44.0)),
    )
    for centres, tilt, seat_radius, port_radius, exterior in families:
        for x, y, z in centres:
            seat_axis = vector_from_tilt(21.0, tilt)
            guide_axis = vector_from_tilt(92.0, tilt)
            cutters.append((3, occ.addCylinder(float(x), float(y), -3.0, *seat_axis, seat_radius)))
            cutters.append((3, occ.addCylinder(float(x), float(y), -2.0, *guide_axis, float(cfg["guide_clearance_radius_mm"]))))
            if float(y) < 0.0:
                start_y, start_z = exterior
                cutters.append((3, occ.addCylinder(float(x), start_y, start_z, 0.0, float(y) - start_y, 5.0 - start_z, port_radius)))
            else:
                start_y, start_z = exterior
                cutters.append((3, occ.addCylinder(float(x), start_y, start_z, 0.0, float(y) - start_y, 5.0 - start_z, port_radius)))
    for x in (-37.0, 37.0):
        dx = math.copysign(13.0, x)
        cutters.append((3, occ.addCylinder(x, 0.0, -2.0, dx, 0.0, 84.0, float(cfg["twin_spark_pilot_radius_mm"]))))
    return cutters


def add_oil_cutters(occ: object, contract: dict) -> list[tuple[int, int]]:
    cfg = contract["functional_geometry"]
    cutters = [(3, occ.addCylinder(-67.0, 8.0, 45.0, 134.0, 0.0, 0.0, float(cfg["oil_header_radius_mm"])))]
    for x in (-36.0, 36.0):
        cutters.append((3, occ.addCylinder(x, 8.0, 42.0, 0.0, 0.0, 40.0, float(cfg["oil_riser_radius_mm"]))))
    for x in (-50.0, 50.0):
        cutters.append((3, occ.addCylinder(x, 25.0, -12.0, 0.0, 0.0, 98.0, float(cfg["oil_drain_radius_mm"]))))
        cutters.append((3, occ.addCylinder(x, 8.0, 45.0, 0.0, 17.0, 0.0, float(cfg["oil_header_radius_mm"]))))
    return cutters


def add_stud_cutters(occ: object, contract: dict) -> list[tuple[int, int]]:
    radius = float(contract["functional_geometry"]["stud_hole_radius_mm"])
    studs = ((-43.3490155, 42.9033462), (-42.8471493, -42.7873019), (43.1002817, 43.1285358), (43.3937545, -42.4446394))
    return [(3, occ.addCylinder(x, y, -12.0, 0.0, 0.0, 103.0, radius)) for x, y in studs]


def configure_mesh(mesh_size: float) -> None:
    gmsh.option.setNumber("Mesh.MeshSizeMin", 0.55 * mesh_size)
    gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size)
    gmsh.option.setNumber("Mesh.Algorithm", 6)
    # Le Delaunay classique est plus tolerant aux sommets de raccord capsule
    # que HXT, tout en restant un maillage tetraedrique Gmsh standard.
    gmsh.option.setNumber("Mesh.Algorithm3D", 1)
    gmsh.option.setNumber("Mesh.Optimize", 1)


def boundary_shell_components() -> int:
    """Compte les composantes connexes de la peau du solide importe."""

    surfaces = [tag for dim, tag in gmsh.model.getEntities(2)]
    curve_surfaces: dict[int, list[int]] = defaultdict(list)
    for surface in surfaces:
        for dim, curve in gmsh.model.getBoundary([(2, surface)], oriented=False, recursive=False):
            if dim == 1:
                curve_surfaces[curve].append(surface)
    adjacency: dict[int, set[int]] = defaultdict(set)
    for connected in curve_surfaces.values():
        for surface in connected:
            adjacency[surface].update(other for other in connected if other != surface)
    remaining = set(surfaces)
    component_count = 0
    while remaining:
        component_count += 1
        pending = [remaining.pop()]
        while pending:
            current = pending.pop()
            for neighbour in adjacency[current]:
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    pending.append(neighbour)
    return component_count


def build(contract: dict, output: Path, mesh_size: float) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("Geometry.Tolerance", 1.0e-7)
        gmsh.option.setNumber("Geometry.OCCFixSmallEdges", 1)
        gmsh.option.setNumber("Geometry.OCCFixSmallFaces", 1)
        gmsh.model.add("f39_brep_scan_only")
        occ = gmsh.model.occ
        outer = add_outer(occ, contract)
        cutters = add_gas_cutters(occ, contract) + add_oil_cutters(occ, contract) + add_stud_cutters(occ, contract)
        head, _ = occ.cut(outer, cutters, removeObject=True, removeTool=True)
        occ.removeAllDuplicates()
        occ.synchronize()
        volumes = gmsh.model.getEntities(3)
        require(len(volumes) == 1 and bool(head), f"expected_one_solid_got:{len(volumes)}")
        step_path = output / "f39-brep-scan-only-head.step"
        gmsh.write(str(step_path))
        canonicalize_step(step_path)

        gmsh.clear()
        gmsh.model.add("f39_brep_scan_only_reimport")
        occ = gmsh.model.occ
        imported = occ.importShapes(str(step_path), highestDimOnly=True)
        occ.synchronize()
        reimported_volumes = gmsh.model.getEntities(3)
        require(len(reimported_volumes) == 1, f"STEP_reimport_volume_count:{len(reimported_volumes)}")
        shell_components = boundary_shell_components()
        configure_mesh(mesh_size)
        gmsh.model.mesh.generate(3)
        stl_path = output / "f39-brep-scan-only-head.local.stl"
        msh_path = output / "f39-brep-scan-only-head.local.msh"
        gmsh.write(str(stl_path))
        gmsh.write(str(msh_path))
        nodes = gmsh.model.mesh.getNodes()[0]
        element_types, element_tags, _ = gmsh.model.mesh.getElements(3)
        volume_elements = sum(len(tags) for tags in element_tags)
        all_tags = [int(tag) for tags in element_tags for tag in tags]
        qualities = gmsh.model.mesh.getElementQualities(all_tags, "minSICN") if all_tags else []
        quality_values = sorted(float(value) for value in qualities)

        def quantile(fraction: float) -> float | None:
            if not quality_values:
                return None
            index = min(len(quality_values) - 1, max(0, round(fraction * (len(quality_values) - 1))))
            return quality_values[index]
        tag = reimported_volumes[0][1]
        bbox = gmsh.model.getBoundingBox(3, tag)
        volume = occ.getMass(3, tag)
        surface_area = sum(occ.getMass(dim, entity) for dim, entity in gmsh.model.getEntities(2))
    finally:
        gmsh.finalize()
    report = {
        "schema_version": "1.0.0",
        "phase": "F39",
        "status": "analytic_scan_only_STEP_reimported_and_volume_meshed_mesh_quality_release_blocked",
        "classification": contract["classification"],
        "geometry": {
            "solid_count": 1,
            "step_reimport_volume_count": len(reimported_volumes),
            "boundary_shell_components": shell_components,
            "closed_internal_shells_detected": max(0, shell_components - 1),
            "volume_mm3_if_scan_unit_is_mm": volume,
            "surface_area_mm2_if_scan_unit_is_mm": surface_area,
            "bounds_if_scan_unit_is_mm": {"minimum": list(bbox[:3]), "maximum": list(bbox[3:])},
            "fin_count": int(contract["outer_reconstruction"]["fin_count"]),
            "valve_count": int(contract["functional_geometry"]["valve_count"]),
        },
        "volume_mesh": {
            "gmsh_success": True,
            "mesh_size_max_mm_if_convention": mesh_size,
            "nodes": len(nodes),
            "volume_elements": volume_elements,
            "element_types": [int(value) for value in element_types],
            "minimum_minSICN": quality_values[0] if quality_values else None,
            "p01_minSICN": quantile(0.01),
            "p05_minSICN": quantile(0.05),
            "median_minSICN": quantile(0.50),
            "mean_minSICN": float(sum(quality_values) / len(quality_values)) if quality_values else None,
            "elements_minSICN_le_0": sum(value <= 0.0 for value in quality_values),
            "elements_minSICN_lt_0_01": sum(value < 0.01 for value in quality_values),
            "elements_minSICN_lt_0_05": sum(value < 0.05 for value in quality_values),
            "elements_minSICN_lt_0_1": sum(value < 0.1 for value in quality_values),
            "quality_gate_minSICN_above_0_1": bool(quality_values and quality_values[0] > 0.1),
        },
        "files": {
            "step": {"path": step_path.name, "bytes": step_path.stat().st_size, "sha256": sha256(step_path)},
            "surface_stl_local": {"path": stl_path.name, "bytes": stl_path.stat().st_size, "sha256": sha256(stl_path)},
            "volume_mesh_local": {"path": msh_path.name, "bytes": msh_path.stat().st_size, "sha256": sha256(msh_path)},
        },
        "unit_convention": contract["unit_convention"],
        "release_gates": contract["release_gates"],
    }
    report_path = output / "f39-brep-build-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--f37-mesh", type=Path, required=True)
    parser.add_argument("--f36-geometry", type=Path, required=True)
    parser.add_argument("--f38-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh-size-mm", type=float, default=3.0)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    require(contract["phase"] == "F39", "contract_phase_not_F39")
    require(sha256(args.f37_mesh) == contract["inputs"]["f37_local_scan_derived_mesh_sha256"], "F37_mesh_hash_mismatch")
    require(sha256(args.f36_geometry) == contract["inputs"]["f36_geometry_report_sha256"], "F36_geometry_hash_mismatch")
    require(sha256(args.f38_report) == contract["inputs"]["f38_brep_report_sha256"], "F38_report_hash_mismatch")
    require(args.mesh_size_mm > 0.0, "mesh_size_must_be_positive")
    report = build(contract, args.output.resolve(), args.mesh_size_mm)
    print(json.dumps({"status": report["status"], "geometry": report["geometry"], "volume_mesh": report["volume_mesh"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
