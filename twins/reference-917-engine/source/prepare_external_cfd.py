#!/usr/bin/env python3
"""Prepare an aligned, closed 917 exterior surface and OpenFOAM snappy case."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pymeshlab
import trimesh


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n")


def foam_header(object_name: str) -> str:
    return f"""
FoamFile
{{
    format ascii;
    class dictionary;
    object {object_name};
}}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("surface", type=Path)
    parser.add_argument("interfaces", type=Path)
    parser.add_argument("case", type=Path)
    args = parser.parse_args()
    data = json.loads(args.interfaces.read_text())
    centroid = np.asarray(data["centroid_scan_coordinates"])
    frame = np.asarray(data["frame_rows_longitudinal_bank_axis_vertical"])

    raw = trimesh.load_mesh(args.surface, process=True)
    main = max(raw.split(only_watertight=False), key=lambda item: len(item.faces))
    main.vertices = (np.asarray(main.vertices) - centroid) @ frame.T
    main.apply_scale(0.001)  # provisional 1 OBJ unit = 1 mm assumption
    main.remove_unreferenced_vertices()
    main.fix_normals()
    if not main.is_volume:
        raise SystemExit("external CFD source is not a closed volume")

    args.case.mkdir(parents=True, exist_ok=True)
    tri_surface = args.case / "constant/triSurface"
    tri_surface.mkdir(parents=True, exist_ok=True)
    full_surface = tri_surface / "917-engine-exterior-full.stl"
    main.export(full_surface)
    light_surface = tri_surface / "917-engine-exterior.stl"
    mesh_set = pymeshlab.MeshSet()
    mesh_set.load_new_mesh(str(full_surface))
    mesh_set.apply_filter(
        "meshing_decimation_quadric_edge_collapse",
        targetfacenum=300_000,
        preserveboundary=True,
        preservenormal=True,
        preservetopology=True,
        optimalplacement=True,
        autoclean=True,
    )
    mesh_set.save_current_mesh(str(light_surface))
    light = trimesh.load_mesh(light_surface, process=True)
    if not light.is_volume:
        raise SystemExit("decimated external CFD surface is not a closed volume")

    lower, upper = np.asarray(light.bounds)
    domain_lower = lower - [0.10, 0.40, 0.10]
    domain_upper = upper + [0.10, 0.80, 0.30]
    lengths = domain_upper - domain_lower
    cells = np.maximum(8, np.ceil(lengths / 0.04).astype(int))
    location = domain_lower + [0.02, 0.02, lengths[2] - 0.02]
    xmin, ymin, zmin = domain_lower
    xmax, ymax, zmax = domain_upper

    write(
        args.case / "system/blockMeshDict",
        foam_header("blockMeshDict")
        + f"""
scale 1;
vertices
(
    ({xmin} {ymin} {zmin}) ({xmax} {ymin} {zmin})
    ({xmax} {ymax} {zmin}) ({xmin} {ymax} {zmin})
    ({xmin} {ymin} {zmax}) ({xmax} {ymin} {zmax})
    ({xmax} {ymax} {zmax}) ({xmin} {ymax} {zmax})
);
blocks (hex (0 1 2 3 4 5 6 7) ({cells[0]} {cells[1]} {cells[2]}) simpleGrading (1 1 1));
edges ();
boundary
(
    inlet {{ type patch; faces ((0 4 5 1)); }}
    outlet {{ type patch; faces ((3 2 6 7)); }}
    sides {{ type patch; faces ((0 3 7 4) (1 5 6 2) (0 1 2 3) (4 7 6 5)); }}
);
mergePatchPairs ();
""",
    )
    write(
        args.case / "system/snappyHexMeshDict",
        foam_header("snappyHexMeshDict")
        + f"""
castellatedMesh true;
snap true;
addLayers false;
geometry
{{
    engine {{ type triSurfaceMesh; file "917-engine-exterior.stl"; name engine; }}
}}
castellatedMeshControls
{{
    maxLocalCells 2000000;
    maxGlobalCells 6000000;
    minRefinementCells 10;
    maxLoadUnbalance 0.10;
    nCellsBetweenLevels 3;
    features ();
    refinementSurfaces {{ engine {{ level (1 2); patchInfo {{ type wall; }} }} }}
    resolveFeatureAngle 35;
    refinementRegions {{}}
    locationInMesh ({location[0]} {location[1]} {location[2]});
    allowFreeStandingZoneFaces true;
}}
snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 30;
    nRelaxIter 5;
    nFeatureSnapIter 10;
    implicitFeatureSnap true;
    explicitFeatureSnap false;
    multiRegionFeatureSnap false;
}}
addLayersControls {{ relativeSizes true; layers {{}}; expansionRatio 1.0; finalLayerThickness 0.3; minThickness 0.1; nGrow 0; featureAngle 60; nRelaxIter 3; nSmoothSurfaceNormals 1; nSmoothNormals 3; nSmoothThickness 10; maxFaceThicknessRatio 0.5; maxThicknessToMedialRatio 0.3; minMedialAxisAngle 90; nBufferCellsNoExtrude 0; nLayerIter 50; }}
meshQualityControls {{ #includeEtc "caseDicts/mesh/generation/meshQualityDict" }}
mergeTolerance 1e-6;
""",
    )
    write(
        args.case / "system/controlDict",
        foam_header("controlDict")
        + """
application snappyHexMesh;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 1;
deltaT 1;
writeControl timeStep;
writeInterval 1;
purgeWrite 0;
writeFormat ascii;
writePrecision 6;
writeCompression off;
timeFormat general;
timePrecision 6;
runTimeModifiable true;
""",
    )
    report = {
        "status": "provisional_external_cooling_mesh_case",
        "case": str(args.case.resolve()),
        "surface": str(light_surface.resolve()),
        "source_triangles": int(len(main.faces)),
        "surface_triangles": int(len(light.faces)),
        "surface_watertight": bool(light.is_watertight),
        "surface_is_volume": bool(light.is_volume),
        "coordinate_system": "X longitudinal, Y cross-bank airflow, Z vertical",
        "scale_assumption": "1 OBJ unit = 1 mm, converted to metres; unconfirmed",
        "domain_bounds_m": [domain_lower.tolist(), domain_upper.tolist()],
        "base_cells": cells.tolist(),
        "limitations": [
            "This case validates meshing around the exterior reconstruction only.",
            "No velocity, temperature, conjugate heat transfer or solver model is defined.",
            "Thin fins below the surface and mesh resolution are not resolved.",
            "A failed checkMesh blocks every solver run.",
        ],
    }
    write(args.case / "cfd-preparation.json", json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
