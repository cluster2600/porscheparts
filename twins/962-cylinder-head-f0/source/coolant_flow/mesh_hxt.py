"""Try native Netgen optimization on the screened, fixed water boundary."""
import argparse
import json
from pathlib import Path

from mesh_surface import quality_passes, sha


def partition(points, triangles):
    import numpy as np
    x = points[triangles, 0]
    inlet = np.all(np.abs(x + 76) < 1e-5, axis=1)
    outlet = np.all(np.abs(x - 76) < 1e-5, axis=1)
    if np.any(inlet & outlet):
        raise ValueError("Overlapping terminal patches")
    groups = dict(inlet=triangles[inlet], outlet=triangles[outlet], walls=triangles[~(inlet | outlet)])
    if not all(len(v) for v in groups.values()):
        raise ValueError("Missing terminal or wall triangles")
    return groups


def mesh(surface, output):
    import gmsh
    import numpy as np
    import trimesh
    receipt = json.loads((surface / "surface-report.json").read_text())
    if not receipt["geometry_admitted"] or sha(surface / "coolant.stl") != receipt["candidate_sha256"]:
        raise ValueError("Surface has not passed its recorded screen")
    if output.exists():
        raise ValueError("Output must be new")
    boundary = trimesh.load_mesh(surface / "coolant.stl", process=True)
    points, triangles = np.asarray(boundary.vertices), np.asarray(boundary.faces)
    groups = partition(points, triangles)
    output.mkdir(parents=True)
    report = dict(status="fixed_boundary_volume_incomplete", source_sha256=sha(Path(__file__)),
                  gate_source_sha256=sha(Path(__file__).with_name("mesh_surface.py")),
                  surface_receipt_sha256=sha(surface / "surface-report.json"), gmsh_version=gmsh.__version__, algorithm3d=10,
                  volume_quality_passed=False, openfoam_mesh_accepted=False,
                  hydraulic_performance_validated=False, manufacturing_authorized=False)
    gmsh.initialize([])
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("General.NumThreads", 2)
        gmsh.option.setNumber("Mesh.MeshOnlyEmpty", 1)
        gmsh.option.setNumber("Mesh.Algorithm3D", 10)
        gmsh.option.setNumber("Mesh.MeshSizeMax", 2)
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.option.setNumber("Mesh.Binary", 0)
        gmsh.model.add("fixed_water_boundary")
        for tag in (101, 102, 103): gmsh.model.addDiscreteEntity(2, tag)
        gmsh.model.mesh.addNodes(2, 103, np.arange(1, len(points) + 1), points.ravel())
        first = 1
        for tag, (name, faces) in zip((101, 102, 103), groups.items()):
            gmsh.model.mesh.addElementsByType(tag, 2, np.arange(first, first + len(faces)), (faces + 1).ravel())
            gmsh.model.addPhysicalGroup(2, [tag], tag, name)
            first += len(faces)
        loop = gmsh.model.geo.addSurfaceLoop([101, 102, 103])
        volume = gmsh.model.geo.addVolume([loop]); gmsh.model.geo.synchronize()
        gmsh.model.addPhysicalGroup(3, [volume], 1, "coolant")
        print("GENERATE_FIXED_BOUNDARY", flush=True)
        gmsh.model.mesh.generate(3)
        print("OPTIMIZE_NETGEN", flush=True)
        gmsh.model.mesh.optimize("Netgen", force=True, niter=5)
        types, tags, _ = gmsh.model.mesh.getElements(3)
        if list(types) != [4]: raise ValueError("Expected linear tetrahedra")
        q = gmsh.model.mesh.getElementQualities(tags[0], "minSICN")
        volumes = gmsh.model.mesh.getElementQualities(tags[0], "volume")
        report.update(cells=len(q), minimum_sicn=float(min(q)),
                      below_sicn_01=int(np.count_nonzero(q < .1)),
                      minimum_volume_mm3=float(min(volumes)), volume_mm3=float(sum(volumes)),
                      volume_quality_passed=quality_passes(q, volumes),
                      boundary_faces={k:len(v) for k,v in groups.items()}, mesh_size_max_request_mm=2)
        gmsh.model.mesh.affineTransform([.001,0,0,0,0,.001,0,0,0,0,.001,0,0,0,0,1])
        gmsh.write(str(output / "coolant.msh"))
        report.update(status="fixed_boundary_volume_screen_only", mesh_coordinates="m",
                      mesh_sha256=sha(output / "coolant.msh"))
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        gmsh.finalize()
        (output / "mesh-report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("surface", type=Path); parser.add_argument("output", type=Path)
    args = parser.parse_args(); mesh(args.surface.resolve(), args.output.resolve())
