"""Build an explicit Cartesian derivative of native coolant for an isothermal CFD study."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def topology(cells, shape):
    if not cells or any(len(c) != 3 or any(type(v) is not int or not 0 <= v < n
           for v, n in zip(c, shape)) for c in cells):
        raise ValueError("Invalid occupied cells")
    occupied = set(map(tuple, cells))
    if len(occupied) != len(cells):
        raise ValueError("Duplicate occupied cells")
    steps = ((-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1))
    seen, pending = set(), [next(iter(occupied))]
    while pending:
        c = pending.pop()
        if c in seen:
            continue
        seen.add(c)
        for step in steps:
            neighbour = tuple(a + b for a, b in zip(c, step))
            if neighbour in occupied and neighbour not in seen:
                pending.append(neighbour)
    if len(seen) != len(occupied):
        raise ValueError(f"Analysis grid is disconnected: {len(seen)} of {len(occupied)} cells reached")
    # Outward quad orientation; shared faces use exactly the same node identities.
    corners = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
               (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))
    face_ids = ((0, 4, 7, 3), (1, 2, 6, 5), (0, 1, 5, 4),
                (3, 7, 6, 2), (0, 3, 2, 1), (4, 5, 6, 7))
    nodes, hexahedra, faces = {}, [], {"inlet": [], "outlet": [], "walls": []}
    for c in sorted(occupied):
        vertices = [tuple(a + b for a, b in zip(c, corner)) for corner in corners]
        for vertex in vertices:
            if vertex not in nodes:
                nodes[vertex] = len(nodes) + 1
        tags = [nodes[v] for v in vertices]
        hexahedra.append(tags)
        for step, indices in zip(steps, face_ids):
            if tuple(a + b for a, b in zip(c, step)) not in occupied:
                patch = "inlet" if c[0] == 0 and step == steps[0] else (
                    "outlet" if c[0] == shape[0] - 1 and step == steps[1] else "walls")
                faces[patch].append([tags[i] for i in indices])
    if not all(faces.values()):
        raise ValueError("Missing inlet, outlet or walls")
    return nodes, hexahedra, faces


def foam_header(name, kind="dictionary"):
    return f"FoamFile {{ format ascii; class {kind}; object {name}; }}\n"


def prepare(grid_path, geometry_report, budget_path, output):
    geometry = json.loads(geometry_report.read_text())
    if sha(grid_path) != geometry["grid_hashes"][grid_path.name]:
        raise ValueError("Grid differs from the independent geometry receipt")
    budget = json.loads(budget_path.read_text())
    if sha(budget_path) != geometry["source_hashes"]["twins/962-cylinder-head-f0/derived/mezger-sp95-budget.json"]:
        raise ValueError("Operating assumptions changed since geometry inspection")
    grid = json.loads(grid_path.read_text())
    h = grid["voxel_mm"]
    if (type(h) is not int or h not in (1, 2) or grid["origin_mm"] != [-76, -80, 0]
            or grid["shape"] != [152 // h, 160 // h, 56 // h]
            or grid["classification"] != "native_Voxels_bIsInside_at_cell_centres"
            or grid["analysis_derivative_not_native_surface"] is not True):
        raise ValueError("Unexpected native analysis-grid contract")
    if output.exists():
        raise ValueError("Output must be new")
    nodes, hexes, faces = topology(grid["cells"], grid["shape"])
    import gmsh
    output.mkdir(parents=True)
    gmsh.initialize([])
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.model.add("native_coolant_cartesian_derivative")
        for entity in (101, 102, 103):
            gmsh.model.addDiscreteEntity(2, entity)
        gmsh.model.addDiscreteEntity(3, 1, [101, 102, 103])
        coords = [(grid["origin_mm"][i] + h * p[i]) * .001 for p in nodes for i in range(3)]
        gmsh.model.mesh.addNodes(3, 1, list(nodes.values()), coords)
        gmsh.model.mesh.addElementsByType(1, 5, list(range(1, len(hexes) + 1)), [n for c in hexes for n in c])
        gmsh.model.addPhysicalGroup(3, [1], 1, "coolant")
        first = len(hexes) + 1
        for entity, (patch, quads) in zip((101, 102, 103), faces.items()):
            gmsh.model.mesh.addElementsByType(entity, 3, list(range(first, first + len(quads))),
                                              [n for face in quads for n in face])
            gmsh.model.addPhysicalGroup(2, [entity], entity, patch)
            first += len(quads)
        gmsh.write(str(output / "coolant.msh"))
        gmsh_version = gmsh.__version__
    finally:
        gmsh.finalize()
    for folder in ("0", "constant", "system"):
        (output / folder).mkdir()
    q = budget["nominal"]["results"]["water_each_head_l_min"] / 60000
    rho = budget["constants"]["water_density_kg_m3"]
    nu = .000315 / rho
    files = {
        "constant/physicalProperties": "viscosityModel constant;\nnu " + str(nu) + ";\n",
        "constant/momentumTransport": "simulationType RAS; RAS { model kOmegaSST; turbulence on; viscosityModel Newtonian; }\n",
        "system/fvSchemes": """ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes { default none; div(phi,U) bounded Gauss upwind; div(phi,k) bounded Gauss upwind;
div(phi,omega) bounded Gauss upwind; div((nuEff*dev2(T(grad(U))))) Gauss linear; }
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist { method meshWave; }
""",
        "system/fvSolution": """solvers {
p { solver GAMG; tolerance 1e-8; relTol 0.01; smoother GaussSeidel; }
"(U|k|omega)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-9; relTol 0.01; }
}
SIMPLE { nNonOrthogonalCorrectors 0; consistent yes;
residualControl { p 1e-5; U 1e-5; "(k|omega)" 1e-5; } }
relaxationFactors { fields { p 0.3; } equations { U 0.5; k 0.5; omega 0.5; } }
""",
        "system/controlDict": """application foamRun; solver incompressibleFluid;
startFrom startTime; startTime 0; stopAt endTime; endTime 2000; deltaT 1;
writeControl timeStep; writeInterval 100; purgeWrite 2; writeFormat ascii;
writePrecision 12; writeCompression off; runTimeModifiable false;
functions {
inletFlux { type surfaceFieldValue; libs (fieldFunctionObjects); writeControl timeStep;
writeInterval 10; regionType patch; name inlet; operation sum; fields (phi); }
outletFlux { type surfaceFieldValue; libs (fieldFunctionObjects); writeControl timeStep;
writeInterval 10; regionType patch; name outlet; operation sum; fields (phi); }
inletPressure { type surfaceFieldValue; libs (fieldFunctionObjects); writeControl timeStep;
writeInterval 10; regionType patch; name inlet; operation areaAverage; fields (p); }
outletPressure { type surfaceFieldValue; libs (fieldFunctionObjects); writeControl timeStep;
writeInterval 10; regionType patch; name outlet; operation areaAverage; fields (p); }
}
""",
    }
    velocity = q / (len(faces["inlet"]) * (h * .001) ** 2)
    k = 1.5 * (.05 * velocity) ** 2
    omega = math.sqrt(k) / (.09 ** .25 * .00154)
    for name, kind, dims, initial, inlet, outlet, wall in (
        ("U", "volVectorField", "0 1 -1 0 0 0 0", f"({velocity} 0 0)",
         f"type flowRateInletVelocity; volumetricFlowRate constant {q}; value uniform ({velocity} 0 0);",
         "type zeroGradient;", "type noSlip;"),
        ("p", "volScalarField", "0 2 -2 0 0 0 0", "0", "type zeroGradient;",
         "type fixedValue; value uniform 0;", "type zeroGradient;"),
        ("k", "volScalarField", "0 2 -2 0 0 0 0", str(k), f"type fixedValue; value uniform {k};",
         "type zeroGradient;", "type kqRWallFunction; value uniform 1e-6;"),
        ("omega", "volScalarField", "0 0 -1 0 0 0 0", str(omega), f"type fixedValue; value uniform {omega};",
         "type zeroGradient;", "type omegaWallFunction; value uniform 1;"),
        ("nut", "volScalarField", "0 2 -1 0 0 0 0", "0", "type calculated; value uniform 0;",
         "type calculated; value uniform 0;", "type nutkWallFunction; value uniform 0;"),
    ):
        files["0/" + name] = (foam_header(name, kind) + f"dimensions [{dims}]; internalField uniform {initial};\n"
             + f"boundaryField {{ inlet {{ {inlet} }} outlet {{ {outlet} }} walls {{ {wall} }} }}\n")
    for relative, text in files.items():
        p = Path(relative)
        if p.parts[0] != "0":
            text = foam_header(p.name) + text
        (output / relative).write_text(text)
    (output / "case.foam").touch()
    report = dict(status="isothermal_rans_research_case_not_a_cht_or_engine_validation",
        grid_mm=h, nodes=len(nodes), cells=len(hexes), boundary_faces={k: len(v) for k, v in faces.items()},
        fluid_volume_mm3=len(hexes) * h**3, inlet_area_mm2=len(faces["inlet"]) * h*h,
        outlet_area_mm2=len(faces["outlet"]) * h*h, flow_m3_s=q, inlet_mean_speed_m_s=velocity,
        water_density_kg_m3=rho, assumed_dynamic_viscosity_pa_s=.000315,
        turbulence_model="kOmegaSST", inlet_turbulence_intensity=.05, inlet_length_scale_m=.00154,
        discretisation="first_order_upwind_diagnostic", gmsh_version=gmsh_version,
        geometry_is_a_cartesian_analysis_derivative=True, wall_roughness_modelled=False,
        source_hashes={str(p.name): sha(p) for p in (Path(__file__), grid_path, geometry_report, budget_path)},
        case_hashes={p: sha(output / p) for p in [*files, "coolant.msh"]},
        manufacturing_authorized=False, hydraulic_performance_validated=False)
    (output / "case-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("grid_mm", "cells", "boundary_faces", "inlet_mean_speed_m_s")}))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("grid", "geometry_report", "budget", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    prepare(*(p.resolve() for p in (args.grid, args.geometry_report, args.budget, args.output)))
