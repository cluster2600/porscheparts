"""Reparametrize the screened water surface before generating a new volume mesh."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quality_passes(qualities, volumes):
    return (len(qualities) > 0 and len(qualities) == len(volumes)
            and all(math.isfinite(v) and v >= .1 for v in qualities)
            and all(math.isfinite(v) and v > 0 for v in volumes))


def mesh(surface, output):
    receipt = json.loads((surface / "surface-report.json").read_text())
    if not receipt["geometry_admitted"] or sha(surface / "coolant.stl") != receipt["candidate_sha256"]:
        raise ValueError("Surface derivative has not passed its recorded screen")
    if output.exists():
        raise ValueError("Output must be new")
    import gmsh
    import numpy as np
    output.mkdir(parents=True)
    report = dict(status="meshing_incomplete", surface_receipt_sha256=sha(surface / "surface-report.json"),
                  source_sha256=sha(Path(__file__)), gmsh_version=gmsh.__version__,
                  volume_quality_passed=False, openfoam_mesh_accepted=False,
                  hydraulic_performance_validated=False, manufacturing_authorized=False)
    gmsh.initialize([])
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("General.NumThreads", 2)
        report["gmsh_build_options"] = gmsh.option.getString("General.BuildOptions")
        gmsh.merge(str(surface / "coolant.stl"))
        print("CLASSIFY", flush=True)
        gmsh.model.mesh.classifySurfaces(math.radians(40), True, True, math.pi)
        print("PARAMETRIZE", flush=True)
        gmsh.model.mesh.createGeometry()
        faces = gmsh.model.getEntities(2)
        patches = dict(inlet=[], outlet=[], walls=[])
        for _, tag in faces:
            _, xyz, _ = gmsh.model.mesh.getNodes(2, tag, includeBoundary=True)
            x = np.asarray(xyz).reshape(-1, 3)[:, 0]
            name = "inlet" if np.all(np.abs(x + 76) < 1e-5) else (
                "outlet" if np.all(np.abs(x - 76) < 1e-5) else "walls")
            patches[name].append(tag)
        if not all(patches.values()):
            raise ValueError("Missing native terminal or water wall")
        loop = gmsh.model.geo.addSurfaceLoop([tag for _, tag in faces])
        volume = gmsh.model.geo.addVolume([loop]); gmsh.model.geo.synchronize()
        gmsh.model.addPhysicalGroup(3, [volume], 1, "coolant")
        for tag, (name, entities) in zip((101, 102, 103), patches.items()):
            gmsh.model.addPhysicalGroup(2, entities, tag, name)
        # Coarse diagnostic sizes: two to four native 0.5 mm voxels, not a convergence study.
        gmsh.option.setNumber("Mesh.MeshSizeMin", 1.)
        gmsh.option.setNumber("Mesh.MeshSizeMax", 2.)
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.option.setNumber("Mesh.Binary", 0)
        print("GENERATE", len(faces), flush=True)
        gmsh.model.mesh.generate(3)
        print("OPTIMIZE_NETGEN", flush=True)
        gmsh.model.mesh.optimize("Netgen", force=True, niter=5)
        types, tags, _ = gmsh.model.mesh.getElements(3)
        if list(types) != [4]:
            raise ValueError("Expected linear tetrahedra")
        q = gmsh.model.mesh.getElementQualities(tags[0], "minSICN")
        volumes = gmsh.model.mesh.getElementQualities(tags[0], "volume")
        report.update(cells=len(q), minimum_sicn=float(min(q)),
                      below_sicn_01=int(np.count_nonzero(q < .1)),
                      minimum_volume_mm3=float(min(volumes)), volume_mm3=float(sum(volumes)),
                      volume_quality_passed=quality_passes(q, volumes),
                      patch_entities=patches, mesh_size_request_mm=[1, 2])
        # OpenFOAM reads SI coordinates; the retained surface and receipt use mm.
        gmsh.model.mesh.affineTransform([.001, 0, 0, 0, 0, .001, 0, 0, 0, 0, .001, 0, 0, 0, 0, 1])
        gmsh.write(str(output / "coolant.msh"))
        report.update(status="volume_screen_only_not_openfoam_acceptance", mesh_coordinates="m",
                      mesh_sha256=sha(output / "coolant.msh"))
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        gmsh.finalize()
        (output / "mesh-report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("surface", type=Path); parser.add_argument("output", type=Path)
    args = parser.parse_args(); mesh(args.surface.resolve(), args.output.resolve())
