"""Synthetic CAD and tetrahedral meshing check; no vehicle qualification."""
import json
import math
import tempfile
from pathlib import Path

import build123d as cad
import gmsh
import meshio
import networkx
import pymeshlab
import rtree
import scipy
import shapely
import skimage
import trimesh

box = cad.Box(10, 20, 30)
assert math.isclose(box.volume, 6000, rel_tol=1e-10)
with tempfile.TemporaryDirectory() as directory:
    mesh = Path(directory) / "unit-box.msh"
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("synthetic-unit-box")
        gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)
        gmsh.model.occ.synchronize()
        gmsh.option.setNumber("Mesh.MeshSizeMin", 0.25)
        gmsh.option.setNumber("Mesh.MeshSizeMax", 0.25)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(mesh))
    finally:
        gmsh.finalize()
    result = meshio.read(mesh)
    cells = result.cells_dict["tetra"]
    assert len(cells) > 0
    import numpy as np
    points = result.points[cells]
    volumes = np.abs(np.linalg.det(points[:, 1:] - points[:, :1])) / 6
    assert (volumes > 0).all()
    assert math.isclose(float(volumes.sum()), 1.0, rel_tol=1e-9)
print(json.dumps({"status": "synthetic_geometry_and_mesh_passed", "tetrahedra": len(cells), "unit_box_volume": float(volumes.sum()), "manufacturing_authorized": False}))
