"""Independent volume check of a synthetic linear tetrahedral mesh."""
import json
import gmsh
import numpy as np

gmsh.initialize()
try:
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("unit-box")
    gmsh.model.occ.addBox(0, 0, 0, 1, 1, 1)
    gmsh.model.occ.synchronize()
    gmsh.option.setNumber("Mesh.MeshSizeMin", 0.25)
    gmsh.option.setNumber("Mesh.MeshSizeMax", 0.25)
    gmsh.model.mesh.generate(3)
    tags, coordinates, _ = gmsh.model.mesh.getNodes()
    points = dict(zip(tags, np.asarray(coordinates).reshape(-1, 3)))
    elements, nodes = gmsh.model.mesh.getElementsByType(4)
    tetrahedra = np.asarray([points[tag] for tag in nodes]).reshape(-1, 4, 3)
    volumes = np.abs(np.linalg.det(tetrahedra[:, 1:] - tetrahedra[:, :1])) / 6
    assert len(elements) > 0 and (volumes > 0).all()
    assert abs(float(volumes.sum()) - 1.0) < 1e-9
    print(json.dumps({"status": "synthetic_unit_volume_passed", "tetrahedra": len(elements),
                      "volume": float(volumes.sum()), "physical_qualification": False}))
finally:
    gmsh.finalize()
