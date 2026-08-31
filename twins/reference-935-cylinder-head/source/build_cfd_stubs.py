#!/usr/bin/env python3
"""Build watertight, scan-derived near-flange CFD stubs.

These short domains validate the meshing and solver pipeline. They are not full
intake/exhaust ports and must not be used to claim engine performance.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import Delaunay


def disk_cap(
    boundary: np.ndarray,
    plane_b: float,
    expected_normal_b: float,
    first_global_index: int,
    vertices: list[list[float]],
    spacing: float = 3.0,
) -> list[tuple[int, int, int]]:
    """Triangulate a circular cap without the poor-quality central fan."""

    centre = boundary.mean(axis=0)
    radius = float(np.mean(np.linalg.norm(boundary - centre, axis=1)))
    axis = np.arange(-radius + spacing, radius, spacing)
    grid_a, grid_c = np.meshgrid(axis, axis)
    interior = np.column_stack((grid_a.ravel(), grid_c.ravel())) + centre
    interior = interior[np.linalg.norm(interior - centre, axis=1) < radius - spacing * 0.75]
    points = np.vstack((boundary, interior))
    interior_start = len(vertices)
    vertices.extend([[float(a), float(plane_b), float(c)] for a, c in interior])
    local_to_global = np.concatenate(
        (
            np.arange(first_global_index, first_global_index + len(boundary)),
            np.arange(interior_start, interior_start + len(interior)),
        )
    )
    faces = []
    all_vertices = np.asarray(vertices)
    for local_face in Delaunay(points).simplices:
        face = local_to_global[local_face]
        p0, p1, p2 = all_vertices[face]
        normal_b = np.cross(p1 - p0, p2 - p0)[1]
        if normal_b * expected_normal_b < 0:
            face = face[[0, 2, 1]]
        faces.append(tuple(int(value) for value in face))
    return faces


def loft(rings: list[dict[str, object]], segments: int = 64) -> tuple[trimesh.Trimesh, dict[str, np.ndarray]]:
    theta = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
    vertices: list[list[float]] = []
    for ring in rings:
        centre_a, centre_c = ring["center"]
        radius = ring["diameter_obj_units"] / 2.0
        vertices.extend(
            np.column_stack(
                (
                    centre_a + radius * np.cos(theta),
                    np.full(segments, ring["plane_B"]),
                    centre_c + radius * np.sin(theta),
                )
            ).tolist()
        )
    wall_faces = []
    for row in range(len(rings) - 1):
        first = row * segments
        second = (row + 1) * segments
        for index in range(segments):
            nxt = (index + 1) % segments
            wall_faces.extend(
                ((first + index, second + index, second + nxt), (first + index, second + nxt, first + nxt))
            )
    last_start = (len(rings) - 1) * segments
    first_boundary = np.asarray(vertices[:segments])[:, [0, 2]]
    last_boundary = np.asarray(vertices[last_start : last_start + segments])[:, [0, 2]]
    inlet_faces = disk_cap(
        first_boundary, float(rings[0]["plane_B"]), -1.0, 0, vertices
    )
    outlet_faces = disk_cap(
        last_boundary, float(rings[-1]["plane_B"]), 1.0, last_start, vertices
    )
    all_faces = np.asarray(wall_faces + inlet_faces + outlet_faces)
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=all_faces, process=False)
    groups = {
        "wall": np.asarray(wall_faces),
        "inlet": np.asarray(inlet_faces),
        "outlet": np.asarray(outlet_faces),
    }
    return mesh, groups


def export_patch(vertices: np.ndarray, faces: np.ndarray, path: Path) -> None:
    trimesh.Trimesh(vertices=vertices, faces=faces, process=False).export(path)


def mesh_with_gmsh(rings: list[dict[str, object]], output: Path) -> dict[str, object]:
    import gmsh

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add(output.stem)
        wires = []
        for ring in rings:
            centre_a, centre_c = ring["center"]
            circle = gmsh.model.occ.addCircle(
                float(centre_a),
                float(ring["plane_B"]),
                float(centre_c),
                float(ring["diameter_obj_units"]) / 2.0,
                zAxis=[0.0, 1.0, 0.0],
                xAxis=[1.0, 0.0, 0.0],
            )
            wires.append(gmsh.model.occ.addWire([circle], checkClosed=True))
        entities = gmsh.model.occ.addThruSections(
            wires, makeSolid=True, makeRuled=False, continuity="C2", smoothing=True
        )
        gmsh.model.occ.synchronize()
        volumes = [tag for dim, tag in entities if dim == 3]
        if len(volumes) != 1:
            raise RuntimeError(f"expected one lofted volume, found {len(volumes)}")
        boundary = gmsh.model.getBoundary([(3, volumes[0])], oriented=False, recursive=False)
        surfaces = [tag for dim, tag in boundary if dim == 2]
        gmsh.model.addPhysicalGroup(3, volumes, 1, "fluid")
        gmsh.model.addPhysicalGroup(2, surfaces, 2, "boundary")
        gmsh.option.setNumber("Mesh.MeshSizeMin", 1.2)
        gmsh.option.setNumber("Mesh.MeshSizeMax", 3.0)
        # OpenFOAM 13's gmshToFoam converter reliably reads the legacy 2.2
        # ASCII layout; Gmsh otherwise defaults to MSH 4.1.
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.option.setNumber("Mesh.Binary", 0)
        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.optimize("Relocate3D")
        node_count = len(gmsh.model.mesh.getNodes()[0])
        element_types, element_tags, _ = gmsh.model.mesh.getElements(3)
        element_count = sum(len(tags) for tags in element_tags)
        gmsh.write(str(output))
        return {
            "status": "generated",
            "path": str(output.resolve()),
            "nodes": int(node_count),
            "volume_elements": int(element_count),
            "element_types": [int(value) for value in element_types],
        }
    except Exception as error:
        return {"status": "blocked", "reason": str(error)}
    finally:
        gmsh.finalize()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("interfaces", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.interfaces.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    report = {
        "units": data["units"],
        "coordinate_system": "X=A, Y=B, Z=C",
        "domains": {},
        "limitations": [
            "Domains cover only the near-flange circular portions visible in reliable scan slabs.",
            "They omit valve seats, guide bosses, chamber junctions and the full curved ports.",
            "Boundary conditions are intentionally not invented.",
            "Use is limited to pipeline validation and local stub-flow comparisons.",
        ],
    }
    for name in ("low_B", "high_B"):
        rings = [item for item in data["port_sections"][name] if "diameter_obj_units" in item]
        rings.sort(key=lambda item: item["plane_B"])
        if len(rings) < 2:
            report["domains"][name] = {"status": "blocked", "reason": "fewer than two reliable rings"}
            continue
        domain_dir = args.output / name
        domain_dir.mkdir(exist_ok=True)
        mesh, patches = loft(rings)
        stl = domain_dir / "fluid-domain.stl"
        mesh.export(stl)
        for patch_name, faces in patches.items():
            export_patch(mesh.vertices, faces, domain_dir / f"{patch_name}.stl")
        gmsh_report = mesh_with_gmsh(rings, domain_dir / "fluid-domain.msh")
        report["domains"][name] = {
            "status": "provisional_cfd_stub",
            "ring_count": len(rings),
            "plane_B_range": [rings[0]["plane_B"], rings[-1]["plane_B"]],
            "surface": {
                "path": str(stl.resolve()),
                "vertices": int(len(mesh.vertices)),
                "triangles": int(len(mesh.faces)),
                "watertight": bool(mesh.is_watertight),
                "volume_obj_units_cubed": float(abs(mesh.volume)),
            },
            "gmsh": gmsh_report,
        }
    (args.output / "cfd-stubs.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
