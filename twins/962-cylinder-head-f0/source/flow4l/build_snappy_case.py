"""Use OpenFOAM 13 surface snapping after rejecting Cartesian and raw-tet meshes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare(surface, template, sampling_grid, output):
    import numpy as np
    report = json.loads((surface / "surface-report.json").read_text())
    inputs = json.loads((template / "case-report.json").read_text())
    if sha(surface / "surface.npz") != report["hashes"]["surface.npz"]:
        raise ValueError("Surface changed")
    for name, digest in inputs["case_hashes"].items():
        if sha(template / name) != digest:
            raise ValueError("Template changed")
    if sha(sampling_grid) != inputs["source_hashes"][sampling_grid.name]:
        raise ValueError("Sampling grid changed")
    if output.exists():
        raise ValueError("Output must be new")
    output.mkdir(parents=True)
    for name in ("0", "constant", "system"):
        shutil.copytree(template / name, output / name, ignore=shutil.ignore_patterns("polyMesh"))
    shutil.copyfile(sampling_grid, output / "native-sampling-grid.json")
    geometry = output / "constant/geometry"; geometry.mkdir()
    data = np.load(surface / "surface.npz", allow_pickle=False)
    points, triangles = data["points_mm"] * .001, data["triangles"]
    x = points[triangles, 0]
    inlet = np.all(np.abs(x + .076) < 1e-8, axis=1)
    outlet = np.all(np.abs(x - .076) < 1e-8, axis=1)
    if not inlet.any() or not outlet.any():
        raise ValueError("Missing inlet/outlet surface")
    with (geometry / "coolant.obj").open("w") as f:
        f.write("# Coordinates in metres; bounded native surface derivative\n")
        for p in points: f.write("v " + " ".join(map(str, p)) + "\n")
        for name, mask in (("inlet", inlet), ("outlet", outlet), ("walls", ~(inlet | outlet))):
            f.write("g " + name + "\n")
            for face in triangles[mask] + 1: f.write("f " + " ".join(map(str, face)) + "\n")
    files = {
        "blockMeshDict": """convertToMeters 1;
vertices ((-.08 -.07 0) (.08 -.07 0) (.08 .07 0) (-.08 .07 0)
(-.08 -.07 .06) (.08 -.07 .06) (.08 .07 .06) (-.08 .07 .06));
blocks (hex (0 1 2 3 4 5 6 7) (80 70 30) simpleGrading (1 1 1));
edges (); boundary (outer { type patch; faces ((0 4 7 3) (1 2 6 5) (0 1 5 4) (3 7 6 2) (0 3 2 1) (4 5 6 7)); });
""",
        "snappyHexMeshDict": """#includeEtc "caseDicts/mesh/generation/snappyHexMeshDict.cfg"
castellatedMesh true; snap true; addLayers false;
geometry { coolant { type closedTriSurface; file "coolant.obj"; } }
castellatedMeshControls {
maxLocalCells 2000000; maxGlobalCells 2000000; minRefinementCells 0;
refinementSurfaces { coolant { level (1 1); patchInfo { type wall; } } }
refinementRegions {}; insidePoint (-.070 0 .024);
}
snapControls { nSolveIter 100; nRelaxIter 5; implicitFeatureSnap true; explicitFeatureSnap false; }
""",
        "meshQualityDict": """#includeEtc "caseDicts/mesh/generation/meshQualityDict"
minDeterminant 0.001;
minFaceWeight 0.05;
""",
        "createPatchDict": """pointSync false;
patches (
{ name inlet; patchInfo { type patch; } constructFrom patches; patches (".*inlet"); }
{ name outlet; patchInfo { type patch; } constructFrom patches; patches (".*outlet"); }
{ name walls; patchInfo { type wall; } constructFrom patches; patches (".*walls"); }
);
""",
    }
    for name, text in files.items():
        (output / "system" / name).write_text(f"FoamFile {{ format ascii; class dictionary; object {name}; }}\n" + text)
    (output / "case.foam").touch()
    result = {**inputs, "status": "surface_snapped_rans_research_case_mesh_not_yet_accepted",
        "cells": None, "nodes": None, "boundary_faces": None, "fluid_volume_mm3": None,
        "inlet_area_mm2": None, "outlet_area_mm2": None, "inlet_mean_speed_m_s": None,
        "inlet_turbulence_intensity": None,
        "initial_template_mean_speed_m_s": inputs["inlet_mean_speed_m_s"],
        "grid_mm": None, "base_background_cell_mm": 2, "wall_refinement_level": 1,
        "meshing": "OpenFOAM 13 snappyHexMesh; no prism layers; strict mesh gate before solve",
        "surface_derivative": report, "sampling_grid": "native-sampling-grid.json",
        "sampling_grid_sha256": sha(sampling_grid), "geometry_is_a_cartesian_analysis_derivative": False,
        "template_case_sha256": sha(template / "case-report.json"),
        "source_hashes": {p.name: sha(p) for p in (Path(__file__), surface / "surface-report.json")},
        "case_hashes": {str(p.relative_to(output)): sha(p) for p in output.glob("**/*") if p.is_file() and p.name != "case.foam"}}
    (output / "case-report.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("surface", "template", "sampling_grid", "output"): parser.add_argument(name, type=Path)
    a = parser.parse_args(); prepare(*(p.resolve() for p in (a.surface, a.template, a.sampling_grid, a.output)))
