"""Mesh a screened native surface with Gmsh; retain the recorded operating-point dictionaries."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare(surface, template, sampling_grid, output):
    import gmsh
    import numpy as np
    report = json.loads((surface / "surface-report.json").read_text())
    if sha(surface / "surface.npz") != report["hashes"]["surface.npz"]:
        raise ValueError("Surface input changed")
    inputs = json.loads((template / "case-report.json").read_text())
    for name, digest in inputs["case_hashes"].items():
        if sha(template / name) != digest:
            raise ValueError("Recorded template changed")
    if output.exists():
        raise ValueError("Output must be new")
    data = np.load(surface / "surface.npz", allow_pickle=False)
    points = data["points_mm"] * .001; triangles = data["triangles"] + 1
    faces = dict(inlet=triangles[np.all(np.abs(points[triangles - 1, 0] + .076) < 1e-8, axis=1)],
                 outlet=triangles[np.all(np.abs(points[triangles - 1, 0] - .076) < 1e-8, axis=1)])
    mask = np.any(np.abs(points[triangles - 1, 0] + .076) >= 1e-8, axis=1) & np.any(np.abs(points[triangles - 1, 0] - .076) >= 1e-8, axis=1)
    faces["walls"] = triangles[mask]
    if not all(len(v) for v in faces.values()) or sum(map(len, faces.values())) != len(triangles):
        raise ValueError("Surface patch partition failed")
    output.mkdir(parents=True)
    for name in ("0", "constant", "system"):
        shutil.copytree(template / name, output / name, ignore=shutil.ignore_patterns("polyMesh"))
    shutil.copyfile(sampling_grid, output / "native-sampling-grid.json")
    gmsh.initialize([])
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.option.setNumber("Mesh.MeshOnlyEmpty", 1)
        gmsh.option.setNumber("Mesh.MeshSizeMin", .0008)
        gmsh.option.setNumber("Mesh.MeshSizeMax", .002)
        gmsh.model.add("screened_native_coolant_surface")
        for tag in (101, 102, 103): gmsh.model.addDiscreteEntity(2, tag)
        gmsh.model.mesh.addNodes(2, 103, list(range(1, len(points) + 1)), points.flatten().tolist())
        first = 1
        for tag, (name, tris) in zip((101, 102, 103), faces.items()):
            gmsh.model.mesh.addElementsByType(tag, 2, list(range(first, first + len(tris))), tris.flatten().tolist())
            gmsh.model.addPhysicalGroup(2, [tag], tag, name)
            first += len(tris)
        loop = gmsh.model.geo.addSurfaceLoop([101, 102, 103])
        volume = gmsh.model.geo.addVolume([loop]); gmsh.model.geo.synchronize()
        gmsh.model.addPhysicalGroup(3, [volume], 1, "coolant")
        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.optimize("", niter=10)
        types, tags, _ = gmsh.model.mesh.getElements(3)
        if list(types) != [4]: raise ValueError("Expected linear tetrahedra")
        cells = len(tags[0])
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        order = np.argsort(node_tags)
        xyz = np.asarray(coordinates).reshape(-1, 3)[order]
        connectivity = gmsh.model.mesh.getElements(3)[2][0]
        xyz = xyz[np.searchsorted(node_tags[order], connectivity)].reshape(-1, 4, 3)
        a, b, c = (xyz[:, i] - xyz[:, 3] for i in range(3))
        volume_mm3 = float(np.abs(np.einsum("ij,ij->i", a, np.cross(b, c))).sum() / 6 * 1e9)
        gmsh.write(str(output / "coolant.msh"))
    finally:
        gmsh.finalize()
    (output / "system/createPatchDict").write_text('FoamFile { format ascii; class dictionary; object createPatchDict; }\npointSync false; patches ( { name walls; patchInfo { type wall; } constructFrom patches; patches (walls); } );\n')
    (output / "case.foam").touch()
    areas = {}
    for name, tris in faces.items():
        xyz = points[tris - 1]
        areas[name] = float(np.linalg.norm(np.cross(xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0]), axis=1).sum() / 2 * 1e6)
    speed = inputs["flow_m3_s"] / (areas["inlet"] * 1e-6)
    result = {**inputs, "status": "unstructured_native_surface_rans_research_case", "cells": cells,
        "nodes": len(node_tags), "boundary_faces": {k: len(v) for k, v in faces.items()},
        "fluid_volume_mm3": volume_mm3, "inlet_area_mm2": areas["inlet"], "outlet_area_mm2": areas["outlet"],
        "inlet_mean_speed_m_s": speed,
        "inlet_turbulence_intensity": .05 * inputs["inlet_mean_speed_m_s"] / speed,
        "grid_mm": None, "meshing": "Gmsh tetrahedralisation of screened native surface derivative",
        "surface_derivative": report, "sampling_grid": "native-sampling-grid.json",
        "sampling_grid_sha256": sha(sampling_grid), "geometry_is_a_cartesian_analysis_derivative": False,
        "template_case_sha256": sha(template / "case-report.json"),
        "source_hashes": {p.name: sha(p) for p in (Path(__file__), surface / "surface-report.json")},
        "case_hashes": {str(p.relative_to(output)): sha(p) for p in output.glob("**/*") if p.is_file() and p.name != "case.foam"}}
    (output / "case-report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(cells=cells, surface_triangles=len(triangles))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("surface", "template", "sampling_grid", "output"): parser.add_argument(name, type=Path)
    a = parser.parse_args(); prepare(*(p.resolve() for p in (a.surface, a.template, a.sampling_grid, a.output)))
