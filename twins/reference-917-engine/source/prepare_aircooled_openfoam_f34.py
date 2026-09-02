#!/usr/bin/env python3
"""Prepare les cas OpenFOAM F34 d'air force autour de la culasse complete."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def header(name: str, class_name: str = "dictionary", location: str | None = None) -> str:
    location_line = f'    location    "{location}";\n' if location else ""
    return (
        "FoamFile\n{\n    format ascii;\n"
        f"    class {class_name};\n{location_line}    object {name};\n}}\n\n"
    )


def write_field(case: Path, name: str, dimensions: str, internal: str, boundaries: str, class_name: str = "volScalarField") -> None:
    (case / "0" / name).write_text(
        header(name, class_name, "0")
        + f"dimensions {dimensions};\ninternalField uniform {internal};\nboundaryField\n{{\n{boundaries}\n}}\n",
        encoding="utf-8",
    )


def prepare_case(case: Path, stl: Path, cells: tuple[int, int, int], level: tuple[int, int], velocity: float, wall_temperature_k: float) -> None:
    for directory in (case / "0", case / "constant/triSurface", case / "system"):
        directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(stl, case / "constant/triSurface/head.stl")
    nx, ny, nz = cells
    block = header("blockMeshDict") + f"""convertToMeters 1;
vertices
(
    (-0.30 -0.18 -0.08)
    ( 0.30 -0.18 -0.08)
    ( 0.30  0.18 -0.08)
    (-0.30  0.18 -0.08)
    (-0.30 -0.18  0.18)
    ( 0.30 -0.18  0.18)
    ( 0.30  0.18  0.18)
    (-0.30  0.18  0.18)
);
blocks (hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1));
edges ();
boundary
(
    inlet {{ type patch; faces ((0 3 7 4)); }}
    outlet {{ type patch; faces ((1 2 6 5)); }}
    farfield {{ type patch; faces ((0 1 5 4) (3 2 6 7) (0 1 2 3) (4 5 6 7)); }}
);
"""
    (case / "system/blockMeshDict").write_text(block, encoding="utf-8")

    lower, upper = level
    snappy = header("snappyHexMeshDict") + f"""castellatedMesh true;
snap true;
addLayers false;
geometry
{{
    head.stl
    {{
        type triSurfaceMesh;
        file "head.stl";
        name head;
        scale 0.001;
    }}
}}
castellatedMeshControls
{{
    maxLocalCells 2500000;
    maxGlobalCells 5000000;
    minRefinementCells 0;
    nCellsBetweenLevels 3;
    features ();
    refinementSurfaces
    {{
        head
        {{
            level ({lower} {upper});
            patchInfo {{ type wall; }}
        }}
    }}
    resolveFeatureAngle 30;
    refinementRegions
    {{
        head
        {{
            mode distance;
            levels ((0.012 {lower}));
        }}
    }}
    locationInMesh (-0.27 0 0.12);
    allowFreeStandingZoneFaces true;
}}
snapControls
{{
    nSmoothPatch 5;
    tolerance 2.0;
    nSolveIter 80;
    nRelaxIter 8;
    nFeatureSnapIter 10;
    implicitFeatureSnap true;
    explicitFeatureSnap false;
    multiRegionFeatureSnap false;
}}
addLayersControls
{{
    relativeSizes true;
    layers {{}}
    expansionRatio 1.2;
    finalLayerThickness 0.3;
    minThickness 0.1;
    nGrow 0;
    featureAngle 60;
    nRelaxIter 5;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedialAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
}}
meshQualityControls
{{
    #include "meshQualityDict"
    relaxed {{ maxNonOrtho 75; }}
}}
mergeTolerance 1e-6;
"""
    (case / "system/snappyHexMeshDict").write_text(snappy, encoding="utf-8")
    (case / "system/meshQualityDict").write_text(
        """maxNonOrtho 70;
maxBoundarySkewness 4;
maxInternalSkewness 4;
maxConcave 80;
minVol 1e-18;
minTetQuality 1e-15;
minArea -1;
minTwist 0.02;
minDeterminant 0.001;
minFaceWeight 0.02;
minVolRatio 0.01;
minTriangleTwist -1;
nSmoothScale 4;
errorReduction 0.75;
""",
        encoding="utf-8",
    )

    control = header("controlDict", location="system") + """solver fluid;
startFrom latestTime;
startTime 0;
stopAt endTime;
endTime 800;
deltaT 1;
writeControl timeStep;
writeInterval 20;
purgeWrite 2;
writeFormat binary;
writePrecision 10;
runTimeModifiable false;
functions
{
    residuals
    {
        type residuals;
        libs ("libutilityFunctionObjects.so");
        writeControl timeStep;
        writeInterval 10;
        fields (p U T k omega);
    }
    outletMassFlow
    {
        type surfaceFieldValue;
        libs ("libfieldFunctionObjects.so");
        writeControl timeStep;
        writeInterval 10;
        writeFields false;
        patch outlet;
        operation sum;
        fields (phi);
    }
    outletTemperature
    {
        type surfaceFieldValue;
        libs ("libfieldFunctionObjects.so");
        writeControl timeStep;
        writeInterval 10;
        writeFields false;
        patch outlet;
        operation areaAverage;
        weightField phi;
        fields (T p);
    }
    weightedOutletTemperature
    {
        type surfaceFieldValue;
        libs ("libfieldFunctionObjects.so");
        writeControl timeStep;
        writeInterval 10;
        writeFields false;
        patch outlet;
        operation average;
        weightField phi;
        fields (T);
    }
    velocityMagnitudeSquared
    {
        type magSqr;
        libs ("libfieldFunctionObjects.so");
        field U;
        result UMagSqr;
        executeControl timeStep;
        executeInterval 1;
        writeControl timeStep;
        writeInterval 10;
    }
    outletTotalEnergyTerms
    {
        type surfaceFieldValue;
        libs ("libfieldFunctionObjects.so");
        writeControl timeStep;
        writeInterval 10;
        writeFields false;
        patch outlet;
        operation average;
        weightField phi;
        fields (T UMagSqr);
    }
    inletPressure
    {
        type surfaceFieldValue;
        libs ("libfieldFunctionObjects.so");
        writeControl timeStep;
        writeInterval 10;
        writeFields false;
        patch inlet;
        operation areaAverage;
        fields (p);
    }
    headHeatFlux
    {
        type wallHeatFlux;
        libs ("libfieldFunctionObjects.so");
        writeControl timeStep;
        writeInterval 10;
        patches (head);
    }
}
"""
    (case / "system/controlDict").write_text(control, encoding="utf-8")
    (case / "system/postProcessDict").write_text(
        header("postProcessDict", location="system")
        + """weightedOutletTemperature
{
    type surfaceFieldValue;
    libs ("libfieldFunctionObjects.so");
    writeFields false;
    patch outlet;
    operation average;
    weightField phi;
    fields (T);
}
inletPressurePost
{
    type surfaceFieldValue;
    libs ("libfieldFunctionObjects.so");
    writeFields false;
    patch inlet;
    operation areaAverage;
    fields (p);
}
outletPressurePost
{
    type surfaceFieldValue;
    libs ("libfieldFunctionObjects.so");
    writeFields false;
    patch outlet;
    operation areaAverage;
    fields (p);
}
""",
        encoding="utf-8",
    )
    (case / "system/fvSchemes").write_text(
        header("fvSchemes", location="system")
        + """ddtSchemes { default steadyState; }
gradSchemes
{
    default Gauss linear;
    limited cellLimited Gauss linear 1;
    grad(U) $limited;
    grad(k) $limited;
    grad(omega) $limited;
}
divSchemes
{
    default none;
    div(phi,U) bounded Gauss linearUpwind limited;
    div(div(phi,U)) Gauss linear;
    energy bounded Gauss upwind;
    div(phi,K) $energy;
    div(phi,h) $energy;
    turbulence bounded Gauss upwind;
    div(phi,k) $turbulence;
    div(phi,omega) $turbulence;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist { method meshWave; }
fluxRequired { default no; p; }
""",
        encoding="utf-8",
    )
    (case / "system/fvSolution").write_text(
        header("fvSolution", location="system")
        + """solvers
{
    Phi { solver GAMG; smoother DIC; tolerance 1e-8; relTol 0.01; }
    p { solver GAMG; smoother DIC; tolerance 1e-8; relTol 0.01; }
    "(U|h|k|omega)" { solver PBiCGStab; preconditioner DILU; tolerance 1e-10; relTol 0.1; }
}
potentialFlow { nNonOrthogonalCorrectors 3; }
PIMPLE
{
    nNonOrthogonalCorrectors 0;
    residualControl
    {
        p 1e-5;
        U 1e-5;
        "(k|omega|h)" 1e-5;
    }
}
relaxationFactors
{
    fields { p 0.3; rho 0.01; }
    equations { U 0.35; h 0.35; "(k|omega)" 0.5; }
}
""",
        encoding="utf-8",
    )
    (case / "constant/physicalProperties").write_text(
        header("physicalProperties", location="constant")
        + """thermoType
{
    type hePsiThermo;
    mixture pureMixture;
    transport const;
    thermo hConst;
    equationOfState perfectGas;
    specie specie;
    energy sensibleEnthalpy;
}
mixture
{
    specie { molWeight 28.97; }
    thermodynamics { Cp 1007; hf 0; }
    transport { mu 2.05e-5; Pr 0.70; }
}
""",
        encoding="utf-8",
    )
    (case / "constant/momentumTransport").write_text(
        header("momentumTransport", location="constant")
        + """simulationType RAS;
RAS
{
    model kOmegaSST;
    turbulence on;
    printCoeffs on;
}
""",
        encoding="utf-8",
    )
    write_field(
        case,
        "U",
        "[0 1 -1 0 0 0 0]",
        f"({velocity} 0 0)",
        f"""    inlet {{ type fixedValue; value uniform ({velocity} 0 0); }}
    outlet {{ type pressureInletOutletVelocity; value uniform ({velocity} 0 0); }}
    farfield {{ type slip; }}
    head {{ type noSlip; }}""",
        "volVectorField",
    )
    write_field(
        case,
        "p",
        "[1 -1 -2 0 0 0 0]",
        "100000",
        """    inlet { type zeroGradient; }
    outlet { type fixedValue; value uniform 100000; }
    farfield { type zeroGradient; }
    head { type zeroGradient; }""",
    )
    write_field(
        case,
        "T",
        "[0 0 0 1 0 0 0]",
        "308.15",
        f"""    inlet {{ type fixedValue; value uniform 308.15; }}
    outlet {{ type inletOutlet; inletValue uniform 308.15; value uniform 308.15; }}
    farfield {{ type zeroGradient; }}
    head {{ type fixedValue; value uniform {wall_temperature_k}; }}""",
    )
    write_field(
        case,
        "k",
        "[0 2 -2 0 0 0 0]",
        "4.0",
        """    inlet { type fixedValue; value uniform 4.0; }
    outlet { type inletOutlet; inletValue uniform 4.0; value uniform 4.0; }
    farfield { type zeroGradient; }
    head { type kqRWallFunction; value uniform 1e-10; }""",
    )
    write_field(
        case,
        "omega",
        "[0 0 -1 0 0 0 0]",
        "900",
        """    inlet { type fixedValue; value uniform 900; }
    outlet { type inletOutlet; inletValue uniform 900; value uniform 900; }
    farfield { type zeroGradient; }
    head { type omegaWallFunction; value uniform 900; }""",
    )
    write_field(
        case,
        "nut",
        "[0 2 -1 0 0 0 0]",
        "0",
        """    inlet { type calculated; value uniform 0; }
    outlet { type calculated; value uniform 0; }
    farfield { type calculated; value uniform 0; }
    head { type nutkWallFunction; value uniform 0; }""",
    )
    write_field(
        case,
        "alphat",
        "[1 -1 -1 0 0 0 0]",
        "1e-3",
        """    inlet { type calculated; value uniform 1e-3; }
    outlet { type calculated; value uniform 1e-3; }
    farfield { type calculated; value uniform 1e-3; }
    head { type compressible::alphatWallFunction; value uniform 1e-3; }""",
    )
    metadata = {
        "cells": list(cells),
        "surface_refinement": list(level),
        "velocity_m_s": velocity,
        "wall_temperature_k": wall_temperature_k,
        "classification": "full_head_external_airflow_fixed_wall_temperature_FVM_case",
    }
    (case / "case-metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--stl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = load_json(args.contract)
    if args.output.exists():
        raise SystemExit(f"output exists: {args.output}")
    specs = {
        "coarse": ((42, 24, 24), (1, 2)),
        "medium": ((56, 32, 32), (1, 3)),
        "fine": ((70, 40, 40), (2, 3)),
    }
    velocity = 77.0
    wall_temperature_k = contract["cooling_design"]["maximum_burst_chamber_bridge_c"] + 273.15
    cases = []
    for name, (cells, level) in specs.items():
        case = args.output / name
        prepare_case(case, args.stl, cells, level, velocity, wall_temperature_k)
        cases.append({"mesh_id": name, "path": str(case), "cells": list(cells), "surface_refinement": list(level)})
    (args.output / "cases.json").write_text(json.dumps(cases, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "openfoam_cases_prepared", "case_count": len(cases)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
