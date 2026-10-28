"""Try one constrained Gmsh volume-node relocation on the rejected 935 mesh."""

import argparse
import hashlib
import json
from pathlib import Path
import time

import gmsh


SOURCE_SHA = "0f6d5cadd5b48c3345e8440c5a881018ca463b005641c46e0b376d9ecbcd8bb7"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def relocate(source, output, iterations):
    root = Path.cwd().resolve()
    if output.exists() or not output.is_relative_to(root / "work"):
        raise ValueError("Use a fresh private output under repository work/")
    if sha(source) != SOURCE_SHA:
        raise ValueError("Pinned 0.005 original-export-bounded fluid mesh required")
    output.mkdir(mode=0o700)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.open(str(source))
        before_nodes = len(gmsh.model.mesh.getNodes()[0])
        before_tets = len(gmsh.model.mesh.getElementsByType(4)[0])
        before_wall = [len(gmsh.model.mesh.getElementsByType(2, tag)[0])
                       for tag in (1, 2, 3, 4)]
        start = time.monotonic()
        gmsh.model.mesh.optimize("Relocate3D", force=False, niter=iterations)
        after_nodes = len(gmsh.model.mesh.getNodes()[0])
        after_tets = len(gmsh.model.mesh.getElementsByType(4)[0])
        after_wall = [len(gmsh.model.mesh.getElementsByType(2, tag)[0])
                      for tag in (1, 2, 3, 4)]
        mesh = output / "fluid.msh"
        gmsh.write(str(mesh))
        report = dict(status="Gmsh_Relocate3D_exploratory_not_CFD_admitted",
                      source_sha256=SOURCE_SHA, output_sha256=sha(mesh),
                      gmsh_version=gmsh.option.getString("General.Version"),
                      method="Relocate3D", force=False, niter=iterations,
                      before_nodes=before_nodes, after_nodes=after_nodes,
                      before_tets=before_tets, after_tets=after_tets,
                      before_wall_elements=before_wall,
                      after_wall_elements=after_wall,
                      elapsed_s=time.monotonic()-start,
                      boundary_geometry_independently_verified=False,
                      CFD_accepted=False, manufacturing_authorized=False)
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        return report
    finally:
        gmsh.finalize()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_mesh", type=Path)
    parser.add_argument("new_output", type=Path)
    parser.add_argument("--iterations", type=int, choices=(1, 5), default=1)
    args = parser.parse_args()
    print(json.dumps(relocate(args.source_mesh.resolve(), args.new_output.resolve(),
                              args.iterations)))
