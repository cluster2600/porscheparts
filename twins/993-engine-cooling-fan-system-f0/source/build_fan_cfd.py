#!/usr/bin/env python3
"""Generate explicit isolated-rotor or parametric-alternator OpenFOAM pilots."""
import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path


def generate(out: Path, surface: Path, rpm: float, cells: int = 24, surface_level: int = 4,
             *, rotor_only: bool = False, with_alternator: bool = False, rotation_sign: int = 1):
    if rotor_only == with_alternator:
        raise ValueError("Installed assembly unsupported: alternator, supports, shaft and shroud "
                         "Choose --rotor-only or --with-alternator with audited stationary geometry.")
    if rotation_sign not in (-1, 1) or not math.isfinite(rpm) or rpm <= 0 or cells < 16 or surface_level not in (3, 4, 5):
        raise ValueError("Positive finite RPM, at least 16 cells and surface level 3..5 required")
    if out.exists():
        raise FileExistsError(out)
    report = json.loads(surface.with_name("picogk-report.json").read_text())
    audit = json.loads(surface.with_name("physicsnemo-surface-audit.json").read_text())
    if (audit["status"] != "surface_audit_passed" or
            not audit["metres_export_matches_mm"] or
            hashlib.sha256(surface.with_name("picogk-report.json").read_bytes()).hexdigest()
            != audit["picogk_report_sha256"] or
            hashlib.sha256(surface.read_bytes()).hexdigest() != audit["metres_surface_sha256"]):
        raise ValueError("Surface has no matching passed PhysicsNeMo audit")
    study = report["input_parameters"]
    # ponytail: fixed far-field box; reject envelopes that need a larger domain.
    diameter, housing, depth = (float(study[k]) / 1000 for k in
                               ("outer_diameter_mm", "housing_diameter_mm", "depth_mm"))
    if not (0 < diameter < housing < .29 and 0 < depth < .08):
        raise ValueError("Rotor envelope does not fit the pilot domain")
    half_zone = depth / 2 + .006
    stationary = surface.with_name("alternator-and-supports-metres.stl")
    if with_alternator:
        fixed_audit = json.loads(surface.with_name("alternator-surface-audit.json").read_text())
        if ("alternator" not in study or fixed_audit["status"] != "surface_audit_passed"
                or not fixed_audit["metres_export_matches_mm"]
                or fixed_audit["picogk_report_sha256"] != audit["picogk_report_sha256"]
                or hashlib.sha256(stationary.read_bytes()).hexdigest() != fixed_audit["metres_surface_sha256"]):
            raise ValueError("Stationary alternator has no matching passed surface audit")
    (out / "constant/geometry").mkdir(parents=True)
    shutil.copyfile(surface, out / "constant/geometry/rotor.stl")
    if with_alternator:
        shutil.copyfile(stationary, out / "constant/geometry/alternator.stl")
    (out / "fan-input.json").write_text(json.dumps({
        "picogk": report, "surface_audit": audit, "rpm": rpm * rotation_sign, "speed_rpm": rpm,
        "base_cells": cells, "surface_level": surface_level,
        "boundary_condition": "ambient_reservoir_totalPressure_at_both_openings",
        "model_scope": ("parametric_alternator_envelope_not_oem_validated" if with_alternator
                        else "isolated_rotor_without_alternator"),
        "alternator_envelope_included": with_alternator,
        "alternator_shaft_wall_model": "stationary_obstruction_approximation" if with_alternator else None,
        "stationary_surface_audit": fixed_audit if with_alternator else None,
        "missing_components": (["alternator_internal_passages", "bearing_seals", "installed_shroud"]
                               if with_alternator else ["alternator", "alternator_supports", "shaft", "installed_shroud"]),
        "installed_assembly_represented": False,
    }, indent=2) + "\n")

    def write(name, body, kind="dictionary"):
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"FoamFile {{ format ascii; class {kind}; object {path.name}; }}\n" + body + "\n")

    write("system/blockMeshDict", f"""vertices ((-.16 -.16 -.18) (.16 -.16 -.18) (.16 .16 -.18) (-.16 .16 -.18)
          (-.16 -.16 .18) (.16 -.16 .18) (.16 .16 .18) (-.16 .16 .18));
blocks (hex (0 1 2 3 4 5 6 7) ({cells} {cells} {round(cells * .36 / .32)}) simpleGrading (1 1 1));
edges ();
boundary (
 inlet {{type patch; faces ((0 3 2 1));}}
 outlet {{type patch; faces ((4 5 6 7));}}
 sides {{type wall; faces ((0 1 5 4) (1 2 6 5) (2 3 7 6) (3 0 4 7));}}
);
""")
    write("system/snappyHexMeshDict", """
castellatedMesh true; snap true; addLayers false;
geometry {
 rotor {type triSurface; file "rotor.stl";}
 duct {type cylinder; point1 (0 0 -.3); point2 (0 0 .4); radius .126;}
 nearRotor {type box; min (-.145 -.145 -.027); max (.145 .145 .027);}
}
castellatedMeshControls {
 maxLocalCells 2000000; maxGlobalCells 2000000; minRefinementCells 0;
 maxLoadUnbalance .1; nCellsBetweenLevels 3; features ();
 refinementSurfaces {
   rotor {level (3 3); patchInfo {type wall;}}
   duct {level (2 2); patchInfo {type wall;}}
 }
 resolveFeatureAngle 30;
 refinementRegions {nearRotor {mode inside; level 2;}}
 locationInMesh (.0521 .0123 -.1111);
 allowFreeStandingZoneFaces true;
}
snapControls {
 nSmoothPatch 3; tolerance 1.5; nSolveIter 100; nRelaxIter 8;
 nFeatureSnapIter 0; implicitFeatureSnap false; explicitFeatureSnap false;
 multiRegionFeatureSnap false;
}
addLayersControls {}
meshQualityControls {
 #includeEtc "caseDicts/mesh/generation/meshQualityDict"
 maxBoundarySkewness 3.5;
 minTetQuality 1e-12;
}
mergeTolerance 1e-6;
""".replace("level (3 3)", f"level ({surface_level} {surface_level})")
       .replace("radius .126", f"radius {housing / 2}")
       .replace(".027", str(half_zone)))
    write("system/topoSetDict", """
actions (
 {name rotorCells; type cellSet; action new; source boxToCell;
  box (-.15 -.15 -.027) (.15 .15 .027);}
 {name rotorZone; type cellZoneSet; action new; source setToCellZone; set rotorCells;}
);
""".replace(".027", str(half_zone)))
    write("system/decomposeParDict", "numberOfSubdomains 4; method scotch;")
    write("constant/MRFProperties", f"""
MRF {{cellZone rotorZone; origin (0 0 0); axis (0 0 1); omega {rpm * rotation_sign} [rpm];}}
""")
    write("constant/physicalProperties", "viscosityModel constant; nu 1.5e-5;")
    write("constant/momentumTransport", "simulationType RAS; RAS {model kOmegaSST; turbulence on;}")
    write("system/controlDict", """
application foamRun; solver incompressibleFluid;
startFrom startTime; startTime 0; stopAt endTime; endTime 1200; deltaT 1;
writeControl timeStep; writeInterval 1200; purgeWrite 1;
writeFormat binary; writePrecision 10; writeCompression off;
timeFormat general; timePrecision 6; runTimeModifiable true;
functions {
 inletFlow {type surfaceFieldValue; libs ("libfieldFunctionObjects.so");
   writeControl timeStep; writeInterval 1; patch inlet;
   operation sum; fields (phi); writeFields false;}
 outletFlow {type surfaceFieldValue; libs ("libfieldFunctionObjects.so");
   writeControl timeStep; writeInterval 1; patch outlet;
   operation sum; fields (phi); writeFields false;}
 inletFlowMagnitude {type surfaceFieldValue; libs ("libfieldFunctionObjects.so");
   writeControl timeStep; writeInterval 1; patch inlet;
   operation sumMag; fields (phi); writeFields false;}
 outletFlowMagnitude {type surfaceFieldValue; libs ("libfieldFunctionObjects.so");
   writeControl timeStep; writeInterval 1; patch outlet;
   operation sumMag; fields (phi); writeFields false;}
 rotorForces {type forces; libs ("libforces.so"); patches (rotor);
   rho rhoInf; rhoInf 1.2; CofR (0 0 0);
   writeControl timeStep; writeInterval 1;}
}
""")
    write("system/fvSchemes", """
ddtSchemes {default steadyState;}
gradSchemes {default Gauss linear; grad(U) cellLimited Gauss linear 1;}
divSchemes {
 // ponytail: first-order pilot; use second-order and wall layers before ranking designs.
 default none; div(phi,U) bounded Gauss upwind;
 div(phi,k) bounded Gauss upwind; div(phi,omega) bounded Gauss upwind;
 div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes {default Gauss linear limited .5;}
interpolationSchemes {default linear;}
snGradSchemes {default limited .5;}
wallDist {method meshWave;}
""")
    write("system/fvSolution", """
solvers {
 p {solver GAMG; smoother GaussSeidel; tolerance 1e-8; relTol .01;}
 "(U|k|omega)" {solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol .05;}
}
SIMPLE {nNonOrthogonalCorrectors 2; consistent no;}
relaxationFactors {fields {p .25;} equations {U .5; k .5; omega .5;}}
""")
    write("0/U", """
dimensions [0 1 -1 0 0 0 0]; internalField uniform (0 0 0);
boundaryField {
 "(inlet|outlet)" {type pressureInletOutletVelocity; value uniform (0 0 0);}
 rotor {type MRFnoSlip;}
 "(duct|sides)" {type noSlip;}
}
""", "volVectorField")
    write("0/p", """
dimensions [0 2 -2 0 0 0 0]; internalField uniform 0;
boundaryField {
 inlet {type totalPressure; p0 uniform 0; value uniform 0;}
 // Ambient static pressure on outflow, total pressure on return inflow.
 outlet {type totalPressure; p0 uniform 0; value uniform 0;}
 "(rotor|duct|sides)" {type zeroGradient;}
}
""", "volScalarField")

    for name, dim, value, wall in (("k", "0 2 -2", .01, "kqRWallFunction"),
                                  ("omega", "0 0 -1", 10, "omegaWallFunction"),
                                  ("nut", "0 2 -1", 0, "nutkWallFunction")):
        opening = (f"type calculated; value uniform {value};" if name == "nut" else
                   f"type inletOutlet; inletValue uniform {value}; value uniform {value};")
        write(f"0/{name}", f"""
dimensions [{dim} 0 0 0 0]; internalField uniform {value};
boundaryField {{
 "(inlet|outlet)" {{{opening}}}
 "(rotor|duct|sides)" {{type {wall}; value uniform {value};}}
}}
""", "volScalarField")

    if with_alternator:
        snappy = out / "system/snappyHexMeshDict"
        text = snappy.read_text().replace("geometry {", 'geometry {\n alternator {type triSurface; file "alternator.stl";}')
        text = text.replace("refinementSurfaces {", f"refinementSurfaces {{\n alternator {{level ({surface_level} {surface_level}); patchInfo {{type wall;}}}}")
        snappy.write_text(text)
        # OpenFOAM 14 uses MRFnoSlip only on rotating walls; ordinary noSlip stays fixed.
        for name in ("U", "p", "k", "omega", "nut"):
            path = out / "0" / name
            path.write_text(path.read_text().replace("duct|sides", "duct|sides|alternator"))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--surface", type=Path, required=True)
    p.add_argument("--rpm", type=float, default=3000)
    p.add_argument("--cells", type=int, default=24)
    p.add_argument("--surface-level", type=int, default=4)
    p.add_argument("--rotor-only", action="store_true",
                   help="Explicitly reproduce a pilot without the alternator or installed assembly")
    p.add_argument("--with-alternator", action="store_true",
                   help="Include the adjacent audited stationary alternator envelope and supports")
    a = p.parse_args()
    generate(a.out, a.surface, a.rpm, a.cells, a.surface_level,
             rotor_only=a.rotor_only, with_alternator=a.with_alternator)
