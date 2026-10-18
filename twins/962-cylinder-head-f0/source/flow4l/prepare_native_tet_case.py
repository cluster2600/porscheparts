"""Keep the rejected parent and test its positive, face-conforming native tet representation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(parent, mesh, export_log, template, grid, output):
    inputs = json.loads((template / "case-report.json").read_text())
    for name, digest in inputs["case_hashes"].items():
        if sha(template / name) != digest:
            raise ValueError("Operating-point template changed")
    log = export_log.read_text()
    count = re.search(r"Native tetrahedra: (\d+); minimum volume: (\S+); sum: (\S+); parent: (\S+); relative volume difference: (\S+)", log)
    if not count or "\nEnd\n" not in log or "FOAM FATAL" in log:
        raise ValueError("Native positive decomposition did not complete")
    if float(count[2]) <= 0 or float(count[5]) > .001:
        raise ValueError("Native representation failed positivity or volume conservation")
    if output.exists():
        raise ValueError("Output must be new")
    output.mkdir(parents=True)
    for name in ("0", "constant", "system"):
        shutil.copytree(template / name, output / name, ignore=shutil.ignore_patterns("polyMesh"))
    geometry = output / "constant/geometry"; geometry.mkdir()
    shutil.copyfile(parent / "constant/geometry/coolant.obj", geometry / "coolant.obj")
    shutil.copyfile(grid, output / "native-sampling-grid.json")
    shutil.copyfile(mesh, output / "coolant.msh")
    (output / "system/createPatchDict").write_text('FoamFile { format ascii; class dictionary; object createPatchDict; }\npointSync false; patches ( { name walls; patchInfo { type wall; } constructFrom patches; patches (walls); } );\n')
    (output / "system/decomposeParDict").write_text('FoamFile { format ascii; class dictionary; object decomposeParDict; }\nnumberOfSubdomains 4; method scotch;\n')
    (output / "case.foam").touch()
    result = {**inputs, "status": "native_positive_tet_research_case_quality_not_yet_accepted",
        "cells": int(count[1]), "nodes": None, "boundary_faces": None,
        "fluid_volume_mm3": float(count[3]) * 1e9,
        "inlet_area_mm2": None, "outlet_area_mm2": None, "inlet_mean_speed_m_s": None,
        "inlet_turbulence_intensity": None, "grid_mm": None,
        "meshing": "OpenFOAM cell-centre and shared native face-base tetrahedra; not VTK convex-hull tessellation",
        "minimum_tetrahedron_volume_m3": float(count[2]),
        "relative_volume_change_from_parent": float(count[5]),
        "parent_case_sha256": sha(parent / "case-report.json"),
        "parent_mesh_hashes_at_collection": {str(p.relative_to(parent)): sha(p) for p in (parent / "constant/polyMesh").iterdir() if p.is_file()},
        "sampling_grid": "native-sampling-grid.json", "sampling_grid_sha256": sha(grid),
        "geometry_is_a_cartesian_analysis_derivative": False,
        "source_hashes": {p.name: sha(p) for p in (Path(__file__), Path(__file__).parent / "native-tets/headTetExport.C", export_log)},
        "case_hashes": {str(p.relative_to(output)): sha(p) for p in output.glob("**/*") if p.is_file() and p.name != "case.foam"}}
    (output / "case-report.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("parent", "mesh", "export_log", "template", "grid", "output"): parser.add_argument(name, type=Path)
    a = parser.parse_args(); prepare(*(p.resolve() for p in (a.parent, a.mesh, a.export_log, a.template, a.grid, a.output)))
