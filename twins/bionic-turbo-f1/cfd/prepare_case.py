#!/usr/bin/env python3
"""Prepare a hypothesis-only OpenCFD 2406 compressible MRF case."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

IMAGE = "docker.io/opencfd/openfoam-run@sha256:1db0df068a490178efda0e30831a34f8ebdfa9ba06c7413f4063a46dc0887532"
PATCHES = ("inlet", "outlet", "rotor", "stator")
LEVELS = {"coarse": 0.0016, "medium": 0.0012, "fine": 0.0009}
GAP_LEVEL = (4, 1, 3)
GAP_SOURCE = "https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/tutorials/mesh/snappyHexMesh/gap_detection/system/snappyHexMeshDict"
CRITERIA = {
    "window_iterations": 100,
    "relative_mass_imbalance_max": 0.001,
    "relative_wall_flux_max": 1e-6,
    "port_reverse_flow_fraction_max": 0.01,
    "relative_mean_change_max": 0.01,
    "relative_stddev_max": 0.02,
    "relative_peak_to_peak_max": 0.05,
    "relative_energy_imbalance_max": 0.05,
    "initial_residual_max": 1e-4,
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def closed_boundary_topology(records):
    """Count edge-connected shells and their patch provenance, without repair."""
    parents, labels, edges, vertices = [], [], {}, set()
    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    for face, label in records:
        index = len(parents)
        parents.append(index)
        labels.append(label)
        if len(face) < 3 or len(set(face)) != len(face):
            raise ValueError("Invalid boundary polygon")
        vertices.update(face)
        for a, b in zip(face, (*face[1:], face[0])):
            edge = (a, b) if a < b else (b, a)
            if edge in edges:
                previous = edges[edge]
                previous[1] += 1
                parents[root(index)] = root(previous[0])
            else:
                edges[edge] = [index, 1]
    if not parents or any(count != 2 for _, count in edges.values()):
        raise ValueError("Boundary must have exactly two faces per edge")
    groups, group_faces, group_edges, group_vertices = {}, Counter(), Counter(), {}
    for index, label in enumerate(labels):
        component = root(index)
        groups.setdefault(component, set()).add(label)
        group_faces[component] += 1
    for edge, (owner, _) in edges.items():
        component = root(owner)
        group_edges[component] += 1
        group_vertices.setdefault(component, set()).update(edge)
    invariants = [{"patches":sorted(group),
                   "euler_characteristic":len(group_vertices[component])-group_edges[component]+group_faces[component]}
                  for component, group in groups.items()]
    invariants.sort(key=lambda item:(item["patches"], item["euler_characteristic"]))
    return {"surface_components":len(groups),
            "component_patch_sets":sorted(sorted(group) for group in groups.values()),
            "component_invariants":invariants,
            "face_count":len(parents), "unique_edges":len(edges),
            "unique_vertices":len(vertices),
            "euler_characteristic":len(vertices)-len(edges)+len(parents)}


def surface_info(path):
    """Validate the strict four-region ASCII input without moving/removing faces."""
    text = path.read_text(encoding="ascii")
    number = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
    vector = rf"({number})\s+({number})\s+({number})"
    facet = re.compile(rf"\s*facet\s+normal\s+{vector}\s+outer\s+loop\s+vertex\s+{vector}\s+vertex\s+{vector}\s+vertex\s+{vector}\s+endloop\s+endfacet\s*")
    solids = list(re.finditer(r"solid\s+(\w+)\s*\n(.*?)endsolid\s+\1\s*(?:\n|$)", text, re.S))
    if [s[1] for s in solids] != list(PATCHES) and set(s[1] for s in solids) != set(PATCHES):
        raise ValueError("Exactly inlet, outlet, rotor and stator regions required")
    if len(solids) != 4 or re.sub(r"solid\s+(\w+)\s*\n(.*?)endsolid\s+\1\s*(?:\n|$)", "", text, flags=re.S).strip():
        raise ValueError("Unexpected STL text or duplicate regions")
    edges, directions, triangles, counts, bounds = Counter(), Counter(), {}, {}, {}
    for solid in solids:
        name, body = solid[1], solid[2]
        matches = list(facet.finditer(body))
        if not matches or facet.sub("", body).strip():
            raise ValueError("Malformed or empty ASCII STL region: " + name)
        lo, hi = [math.inf]*3, [-math.inf]*3
        for match in matches:
            values = list(map(float, match.groups()))
            if not all(math.isfinite(v) for v in values):
                raise ValueError("Nonfinite STL coordinate")
            points = tuple(tuple(values[i:i+3]) for i in (3, 6, 9))
            a, b, c = points
            u, v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
            cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
            key = tuple(sorted(points))
            if not any(cross) or key in triangles:
                raise ValueError("Degenerate or duplicate STL face")
            triangles[key] = name
            for point in points:
                lo = [min(lo[i], point[i]) for i in range(3)]
                hi = [max(hi[i], point[i]) for i in range(3)]
            for start, end in ((a, b), (b, c), (c, a)):
                edge = tuple(sorted((start, end)))
                edges[edge] += 1
                directions[edge] += 1 if start < end else -1
        counts[name], bounds[name] = len(matches), [lo, hi]
    if any(n != 2 for n in edges.values()) or any(directions.values()):
        raise ValueError("Combined surface must have closed, consistently wound edges")
    lo = [min(b[0][i] for b in bounds.values()) for i in range(3)]
    hi = [max(b[1][i] for b in bounds.values()) for i in range(3)]
    if max(hi[i]-lo[i] for i in range(3)) > 0.5 or max(abs(v) for v in lo+hi) > 1:
        raise ValueError("Metre input required within the declared concept envelope")
    if abs(bounds["inlet"][1][2]-bounds["inlet"][0][2]) > 1e-9 or abs(bounds["outlet"][1][1]-bounds["outlet"][0][1]) > 1e-9:
        raise ValueError("Inlet must be a Z plane and outlet a Y plane")
    if bounds["inlet"][0][2] <= 0.033 or bounds["outlet"][0][1] <= 0.032:
        raise ValueError("Open ports must lie outside the MRF cylinder")
    topology = closed_boundary_topology(triangles.items())
    return {"sha256": sha(path), "bounds_m": [lo, hi], "region_bounds_m": bounds,
            "region_triangles": counts, "closed_edges": True,
            "boundary_topology":topology,
            "self_intersections_checked": False, "seed_occupancy_checked": False}


def header(name, kind="dictionary"):
    return f"FoamFile {{version 2.0; format ascii; class {kind}; object {name};}}\n"


def field(name, dimensions, value, patches, vector=False):
    return header(name, "volVectorField" if vector else "volScalarField") + f"dimensions [{dimensions}];\ninternalField uniform {value};\nboundaryField {{\n" + "\n".join(f"{p} {{{patches[p]}}}" for p in PATCHES) + "\n}\n"


def case_files(info, level, rpm, rotation_sign, pressure_ratio, iterations):
    if level not in LEVELS or rotation_sign not in (-1, 1):
        raise ValueError("Unknown mesh level or rotation sign")
    if not math.isfinite(rpm) or not 1000 <= rpm <= 150000 or not math.isfinite(pressure_ratio) or not 0.8 <= pressure_ratio <= 2.5:
        raise ValueError("RPM or outlet/inlet-pressure ratio outside hypothesis bounds")
    if isinstance(iterations, bool) or not isinstance(iterations, int) or not 200 <= iterations <= 5000:
        raise ValueError("Iterations must be 200..5000")
    step = LEVELS[level]
    lo, hi = info["bounds_m"]
    lo, hi = [v-0.003 for v in lo], [v+0.003 for v in hi]
    vertices = [(lo[0],lo[1],lo[2]),(hi[0],lo[1],lo[2]),(hi[0],hi[1],lo[2]),(lo[0],hi[1],lo[2]),
                (lo[0],lo[1],hi[2]),(hi[0],lo[1],hi[2]),(hi[0],hi[1],hi[2]),(lo[0],hi[1],hi[2])]
    vec = lambda p: "("+" ".join(f"{v:.12g}" for v in p)+")"
    cells = [math.ceil((hi[i]-lo[i])/step) for i in range(3)]
    files = {}
    def dictionary(name, body):
        files[name] = header(Path(name).name)+body+"\n"
    dictionary("system/blockMeshDict", "vertices ("+" ".join(map(vec, vertices))+f");\nblocks (hex (0 1 2 3 4 5 6 7) ({' '.join(map(str,cells))}) simpleGrading (1 1 1));\nedges ();\nboundary (background {{type patch; faces ((0 3 2 1)(4 5 6 7)(0 1 5 4)(1 2 6 5)(2 3 7 6)(3 0 4 7));}});")
    regions = "\n".join(f"{p} {{level (1 1); patchInfo {{type {'patch' if p in ('inlet','outlet') else 'wall'};}}}}" for p in PATCHES)
    dictionary("system/snappyHexMeshDict", """
castellatedMesh true; snap true; addLayers false;
geometry {domain {type triSurfaceMesh; file "domain.stl";
 regions {inlet {name inlet;} outlet {name outlet;} rotor {name rotor;} stator {name stator;}}}
 backgroundRefinement {type searchableBox; min BOXMIN; max BOXMAX;}}
castellatedMeshControls {
 maxLocalCells 6000000; maxGlobalCells 6000000; minRefinementCells 0;
 maxLoadUnbalance .1; nCellsBetweenLevels 3; features ();
 refinementSurfaces {domain {level (1 1); regions {REGIONS}}}
 resolveFeatureAngle 30; refinementRegions {backgroundRefinement {mode inside; levels ((1e15 1));
 gapLevel GAPLEVEL; gapMode mixed; gapSelf true;}}
 locationInMesh (0.015 0 0.040); allowFreeStandingZoneFaces true;
}
snapControls {nSmoothPatch 3; nSmoothInternal 3; tolerance 1.5; nSolveIter 100; nRelaxIter 8;
 nFeatureSnapIter 0; implicitFeatureSnap false; explicitFeatureSnap false; multiRegionFeatureSnap false;
 strictRegionSnap true;}
addLayersControls {}
meshQualityControls {#includeEtc "caseDicts/mesh/generation/meshQualityDict.cfg"
 maxBoundarySkewness 3.5; minTetQuality 1e-12;}
mergeTolerance 1e-7;
""".replace("REGIONS", regions).replace("BOXMIN", vec(lo)).replace("BOXMAX", vec(hi)).replace("GAPLEVEL", vec(GAP_LEVEL)))
    dictionary("system/topoSetDict", """actions (
 {name rotorCells; type cellSet; action new; source cylinderToCell; p1 (0 0 -.004); p2 (0 0 .033); radius .032;}
 {name rotorZone; type cellZoneSet; action new; source setToCellZone; set rotorCells;}
);""")
    dictionary("constant/MRFProperties", f"MRF {{active yes; cellZone rotorZone; origin (0 0 0); axis (0 0 1); omega constant {rpm*rotation_sign*math.pi/30:.15g}; nonRotatingPatches (stator inlet outlet);}}")
    # OpenCFD MRF corrects included rotor patch velocities; fixed walls are excluded above.
    files["0/U"] = field("U", "0 1 -1 0 0 0 0", "(0 0 0)", {
        "inlet":"type pressureInletOutletVelocity; value uniform (0 0 0);", "outlet":"type pressureInletOutletVelocity; value uniform (0 0 0);",
        "rotor":"type noSlip;", "stator":"type noSlip;"}, True)
    p0, temperature, gamma, gas_r = 101325., 298.15, 1.4, 287.05
    files["0/p"] = field("p", "1 -1 -2 0 0 0 0", str(p0), {
        "inlet":f"type totalPressure; psi psi; gamma {gamma}; p0 uniform {p0}; value uniform {p0};",
        "outlet":f"type fixedValue; value uniform {p0*pressure_ratio:.12g};", "rotor":"type zeroGradient;", "stator":"type zeroGradient;"})
    files["0/T"] = field("T", "0 0 0 1 0 0 0", str(temperature), {
        "inlet":f"type totalTemperature; psi psi; gamma {gamma}; T0 uniform {temperature}; value uniform {temperature};",
        "outlet":f"type inletOutlet; inletValue uniform {temperature}; value uniform {temperature};", "rotor":"type zeroGradient;", "stator":"type zeroGradient;"})
    for name, dims, value, wall, inlet in (
        ("k", "0 2 -2 0 0 0 0", 1, "kqRWallFunction", "type turbulentIntensityKineticEnergyInlet; intensity .05; value uniform 1;"),
        ("omega", "0 0 -1 0 0 0 0", 200, "omegaWallFunction", "type turbulentMixingLengthFrequencyInlet; mixingLength .003; value uniform 200;"),
        ("nut", "0 2 -1 0 0 0 0", 0, "nutkWallFunction", "type calculated; value uniform 0;"),
        ("alphat", "1 -1 -1 0 0 0 0", 0, "compressible::alphatWallFunction", "type calculated; value uniform 0;")):
        files["0/"+name] = field(name, dims, str(value), {"inlet":inlet,
            "outlet":f"type {'inletOutlet; inletValue uniform '+str(value) if name in ('k','omega') else 'calculated'}; value uniform {value};",
            "rotor":f"type {wall}; value uniform {value};", "stator":f"type {wall}; value uniform {value};"})
    dictionary("constant/thermophysicalProperties", f"""thermoType {{type hePsiThermo; mixture pureMixture; transport const; thermo hConst; equationOfState perfectGas; specie specie; energy sensibleEnthalpy;}}
mixture {{specie {{molWeight {8314.46261815324/gas_r:.15g};}} thermodynamics {{Cp {gamma*gas_r/(gamma-1):.15g}; hf 0;}} transport {{mu 1.82e-5; Pr .71;}}}}""")
    dictionary("constant/turbulenceProperties", "simulationType RAS; RAS {RASModel kOmegaSST; turbulence on; printCoeffs on;}")
    dictionary("system/fvSchemes", """ddtSchemes {default steadyState;}
gradSchemes {default cellLimited Gauss linear 1;}
divSchemes {default none; div(phi,U) bounded Gauss linearUpwind grad(U);
 div(phi,h) bounded Gauss linearUpwind grad(h); div(phi,K) bounded Gauss linearUpwind grad(K);
 div(phi,k) bounded Gauss upwind; div(phi,omega) bounded Gauss upwind;
 div(phiMRF,p) Gauss limitedLinear 1;
 div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;}
laplacianSchemes {default Gauss linear limited .5;}
interpolationSchemes {default linear;}
snGradSchemes {default limited .5;} wallDist {method meshWave;}""")
    dictionary("system/fvSolution", """solvers {
 p {solver GAMG; smoother DIC; tolerance 1e-8; relTol .01;}
 "(U|k|omega|h)" {solver PBiCGStab; preconditioner DILU; tolerance 1e-9; relTol .05;}
}
SIMPLE {nNonOrthogonalCorrectors 2; consistent yes;}
relaxationFactors {fields {p .2; rho .1;} equations {U .5; h .5; "(k|omega)" .5;}}""")
    functions = ["""velocitySquared {type magSqr; libs ("libfieldFunctionObjects.so"); field U; result UMagSqr;
 executeControl timeStep; executeInterval 1; writeControl none;}
rotorForces {type forces; libs ("libforces.so"); patches (rotor); rho rho; CofR (0 0 0);
 writeControl timeStep; writeInterval 1; log false;}
yPlus {type yPlus; libs ("libfieldFunctionObjects.so"); writeControl writeTime;}
scalarMinima {type volFieldValue; libs ("libfieldFunctionObjects.so"); regionType all;
 operation min; fields (p T); writeFields false; writeControl timeStep; writeInterval 1;}
"""]
    for patch in PATCHES:
        for label, operation, fields, weight in (("mass", "sum", "phi", ""), ("magnitude", "sumMag", "phi", "")):
            functions.append(f'{label}_{patch} {{type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); regionType patch; name {patch}; operation {operation}; fields ({fields}); {weight} writeFields false; writeControl timeStep; writeInterval 1; log false;}}')
        if patch in ("inlet", "outlet"):
            functions.append(f'energy_{patch} {{type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); regionType patch; name {patch}; operation weightedSum; weightField phi; fields (h UMagSqr); writeFields false; writeControl timeStep; writeInterval 1; log false;}}')
    dictionary("system/controlDict", f"""application rhoSimpleFoam;
startFrom startTime; startTime 0; stopAt endTime; endTime {iterations}; deltaT 1;
writeControl timeStep; writeInterval 100; purgeWrite 0; writeFormat ascii; writePrecision 12;
writeCompression off; timeFormat general; timePrecision 12; runTimeModifiable false;
functions {{ {''.join(functions)} }}""")
    return files


def prepare(surface, output, level, rpm, rotation_sign, pressure_ratio, iterations):
    info = surface_info(surface)
    files = case_files(info, level, rpm, rotation_sign, pressure_ratio, iterations)
    output.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        target = output/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    target = output/"constant/triSurface/domain.stl"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(surface.read_bytes())
    if sha(target) != info["sha256"]:
        raise ValueError("Surface changed during preparation")
    manifest = {"schema":"bionic-turbo-compressible-mrf/v1", "status":"prepared_not_meshed_or_solved",
        "image":IMAGE, "solver":"rhoSimpleFoam", "openfoam":"OpenCFD 2406", "surface":info,
        "solver_energy_source_url":"https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/applications/solvers/compressible/rhoSimpleFoam/EEqn.H",
        "solver_energy_source_sha256":"59f0cab95246ea9d88efff8e8455c03668b2acb576d5af24466ece21471101cf",
        "source_sha256":sha(Path(__file__)), "mesh_level":level, "background_cell_m":LEVELS[level],
        "gap_refinement":{"gap_level":list(GAP_LEVEL), "mode":"mixed", "same_surface_detection":True,
            "smallest_nominal_cell_m":LEVELS[level]/2**GAP_LEVEL[2], "actual_gap_cell_count_verified":False,
            "source_url":GAP_SOURCE},
        "rpm":rpm, "rotation_sign":rotation_sign, "inlet_total_pressure_pa":101325.,
        "inlet_total_temperature_k":298.15, "outlet_static_pressure_pa":101325.*pressure_ratio,
        "outlet_static_to_inlet_total_pressure_ratio":pressure_ratio, "steady_iterations":iterations,
        "seed_m":[.015,0,.040], "rotor_zone":{"radius_m":.032,"z_min_m":-.004,"z_max_m":.033},
        "criteria":CRITERIA, "file_sha256":{n:sha(output/n) for n in files}|{"constant/triSurface/domain.stl":info["sha256"]},
        "operating_conditions_measured":False, "wall_layers_present":False, "mesh_independence_established":False,
        "performance_ranking_authorized":False, "engineering_validated":False, "manufacturing_authorized":False,
        "limitations":["Idealized seals and geometrical assumptions belong to the supplied domain contract.",
            "Steady iterations are not physical transient time.", "A pressure-controlled point does not establish maximum flow or choking.",
            "No efficiency or installed-turbo performance claim; wall treatment and grid sensitivity remain to qualify."]}
    (output/"case-manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False)+"\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("surface", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--level", choices=LEVELS, required=True)
    parser.add_argument("--rpm", type=float, default=100000.)
    parser.add_argument("--rotation-sign", type=int, choices=(-1,1), required=True)
    parser.add_argument("--pressure-ratio", type=float, default=1.2)
    parser.add_argument("--iterations", type=int, default=800)
    args = parser.parse_args()
    manifest = prepare(args.surface, args.output, args.level, args.rpm, args.rotation_sign, args.pressure_ratio, args.iterations)
    print(json.dumps({"status":manifest["status"], "output":str(args.output)}))


if __name__ == "__main__":
    main()
