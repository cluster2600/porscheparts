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


def loft(rings: list[dict[str, object]], segments: int = 96) -> tuple[trimesh.Trimesh, dict[str, np.ndarray]]:
    theta = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
    vertices = []
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
            )
        )
    vertices = np.asarray(vertices)
    wall_faces = []
    for row in range(len(rings) - 1):
        first = row * segments
        second = (row + 1) * segments
        for index in range(segments):
            nxt = (index + 1) % segments
            wall_faces.extend(
                ((first + index, second + index, second + nxt), (first + index, second + nxt, first + nxt))
            )
    first_centre = len(vertices)
    last_centre = first_centre + 1
    vertices = np.vstack(
        (
            vertices,
            [rings[0]["center"][0], rings[0]["plane_B"], rings[0]["center"][1]],
            [rings[-1]["center"][0], rings[-1]["plane_B"], rings[-1]["center"][1]],
        )
    )
    inlet_faces = []
    outlet_faces = []
    last_start = (len(rings) - 1) * segments
    for index in range(segments):
        nxt = (index + 1) % segments
        inlet_faces.append((first_centre, nxt, index))
        outlet_faces.append((last_centre, last_start + index, last_start + nxt))
    all_faces = np.asarray(wall_faces + inlet_faces + outlet_faces)
    mesh = trimesh.Trimesh(vertices=vertices, faces=all_faces, process=True)
    groups = {
        "wall": np.asarray(wall_faces),
        "inlet": np.asarray(inlet_faces),
        "outlet": np.asarray(outlet_faces),
    }
    return mesh, groups


def export_patch(vertices: np.ndarray, faces: np.ndarray, path: Path) -> None:
    trimesh.Trimesh(vertices=vertices, faces=faces, process=False).export(path)


def mesh_with_gmsh(stl: Path, output: Path) -> dict[str, object]:
    import gmsh

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add(stl.stem)
        gmsh.merge(str(stl))
        gmsh.model.mesh.classifySurfaces(np.deg2rad(40.0), True, True, np.pi)
        gmsh.model.mesh.createGeometry()
        surfaces = [tag for dim, tag in gmsh.model.getEntities(2)]
        loop = gmsh.model.geo.addSurfaceLoop(surfaces)
        gmsh.model.geo.addVolume([loop])
        gmsh.model.geo.synchronize()
        gmsh.option.setNumber("Mesh.MeshSizeMin", 1.2)
        gmsh.option.setNumber("Mesh.MeshSizeMax", 3.0)
        gmsh.model.mesh.generate(3)
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
        gmsh_report = mesh_with_gmsh(stl, domain_dir / "fluid-domain.msh")
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

