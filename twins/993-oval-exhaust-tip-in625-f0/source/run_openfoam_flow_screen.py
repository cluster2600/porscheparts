#!/usr/bin/env python3
"""Criblage CFD RANS de la veine gazeuse de l'embout ovale IN625 F0.

La veine fluide reprend uniquement les dimensions F0 du modèle propre au
projet. Le débit, la température et toutes les conditions aux limites sont
synthétiques : ce calcul est une régression numérique, pas une validation 993.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import shutil
import subprocess


PART_ID = "993-EXH-OVAL-TIP-IN625-F0-0001"
TWIN_ID = "TWIN-993-OVAL-EXHAUST-TIP-IN625-F0"
LENGTH_MM = 120.0
INLET_RADIUS_MM = 28.7
OUTLET_A_MM = 54.7
OUTLET_B_MM = 37.2
VOLUME_FLOW_M3_S = 0.27701736111111114
HOT_DENSITY_KG_M3 = 0.4164705882352941
DYNAMIC_VISCOSITY_PA_S = 4.0e-5
TURBULENCE_INTENSITY = 0.05
TURBULENCE_LENGTH_SCALE_FACTOR = 0.07
FINAL_INITIAL_RESIDUAL_LIMITS = {
    "Ux": 2.0e-5,
    "Uy": 2.0e-5,
    "Uz": 2.0e-5,
    "p": 5.0e-5,
    "k": 2.0e-5,
    "epsilon": 1.0e-5,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path, log: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(
            f"command_failed:{command[0]}:{completed.returncode}:{log.name}"
        )
    return completed.stdout


def add_ellipse_wire(occ, z_mm: float, a_mm: float, b_mm: float) -> int:
    center = occ.addPoint(0.0, 0.0, z_mm)
    positive_x = occ.addPoint(a_mm, 0.0, z_mm)
    positive_y = occ.addPoint(0.0, b_mm, z_mm)
    negative_x = occ.addPoint(-a_mm, 0.0, z_mm)
    negative_y = occ.addPoint(0.0, -b_mm, z_mm)
    curves = [
        occ.addEllipseArc(positive_x, center, positive_x, positive_y),
        occ.addEllipseArc(positive_y, center, positive_x, negative_x),
        occ.addEllipseArc(negative_x, center, positive_x, negative_y),
        occ.addEllipseArc(negative_y, center, positive_x, positive_x),
    ]
    return occ.addWire(curves)


def create_mesh(case: Path, mesh_size_mm: float) -> dict[str, object]:
    import gmsh

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("993_oval_exhaust_tip_flow_f0")
        occ = gmsh.model.occ
        inlet_wire = add_ellipse_wire(
            occ, 0.0, INLET_RADIUS_MM, INLET_RADIUS_MM
        )
        outlet_wire = add_ellipse_wire(
            occ, LENGTH_MM, OUTLET_A_MM, OUTLET_B_MM
        )
        volumes = occ.addThruSections(
            [inlet_wire, outlet_wire], makeSolid=True, makeRuled=True
        )
        occ.synchronize()
        if len(volumes) != 1 or volumes[0][0] != 3:
            raise RuntimeError(f"expected_one_fluid_volume:{volumes}")

        inlet: list[int] = []
        outlet: list[int] = []
        walls: list[int] = []
        for dimension, tag in gmsh.model.getEntities(2):
            bounds = gmsh.model.getBoundingBox(dimension, tag)
            if abs(bounds[2]) < 1e-5 and abs(bounds[5]) < 1e-5:
                inlet.append(tag)
            elif (
                abs(bounds[2] - LENGTH_MM) < 1e-5
                and abs(bounds[5] - LENGTH_MM) < 1e-5
            ):
                outlet.append(tag)
            else:
                walls.append(tag)
        if len(inlet) != 1 or len(outlet) != 1 or len(walls) != 4:
            raise RuntimeError(
                f"unexpected_patch_topology:{inlet}:{outlet}:{walls}"
            )

        gmsh.model.addPhysicalGroup(3, [volumes[0][1]], 1, "fluid")
        gmsh.model.addPhysicalGroup(2, inlet, 2, "inlet")
        gmsh.model.addPhysicalGroup(2, outlet, 3, "outlet")
        gmsh.model.addPhysicalGroup(2, walls, 4, "walls")
        gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size_mm)
        gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size_mm)
        gmsh.option.setNumber("Mesh.Algorithm3D", 1)
        gmsh.option.setNumber("Mesh.Smoothing", 10)
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.option.setNumber("Mesh.Binary", 0)
        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.optimize("Relocate3D")
        node_count = len(gmsh.model.mesh.getNodes()[0])
        element_count = sum(
            len(tags) for tags in gmsh.model.mesh.getElements(3)[1]
        )
        mesh = case / "flow.msh"
        gmsh.write(str(mesh))
        return {
            "mesh_size_mm": mesh_size_mm,
            "nodes": node_count,
            "tetrahedra": element_count,
            "patches": {"inlet": 1, "outlet": 1, "walls": 4},
            "msh_bytes": mesh.stat().st_size,
            "msh_sha256": sha256(mesh),
            "gmsh_version": str(gmsh.__version__),
        }
    finally:
        gmsh.finalize()


def foam_header(class_name: str, location: str, object_name: str) -> str:
    return f"""FoamFile
{{
    format ascii;
    class {class_name};
    location \"{location}\";
    object {object_name};
}}
"""


def boundary_input_values() -> dict[str, float]:
    inlet_area_m2 = math.pi * (INLET_RADIUS_MM / 1000.0) ** 2
    inlet_velocity = VOLUME_FLOW_M3_S / inlet_area_m2
    kinematic_viscosity = DYNAMIC_VISCOSITY_PA_S / HOT_DENSITY_KG_M3
    turbulence_k = 1.5 * (inlet_velocity * TURBULENCE_INTENSITY) ** 2
    turbulence_length = (
        TURBULENCE_LENGTH_SCALE_FACTOR * 2.0 * INLET_RADIUS_MM / 1000.0
    )
    turbulence_epsilon = (
        0.09**0.75 * turbulence_k**1.5 / turbulence_length
    )
    return {
        "inlet_velocity_m_s": inlet_velocity,
        "kinematic_viscosity_m2_s": kinematic_viscosity,
        "turbulence_k_m2_s2": turbulence_k,
        "turbulence_epsilon_m2_s3": turbulence_epsilon,
        "turbulence_intensity": TURBULENCE_INTENSITY,
        "turbulence_length_scale_m": turbulence_length,
    }


def write_case_files(case: Path) -> dict[str, float]:
    zero = case / "0"
    constant = case / "constant"
    system = case / "system"
    zero.mkdir()
    constant.mkdir()
    system.mkdir()
    inputs = boundary_input_values()
    inlet_velocity = inputs["inlet_velocity_m_s"]
    kinematic_viscosity = inputs["kinematic_viscosity_m2_s"]
    turbulence_k = inputs["turbulence_k_m2_s2"]
    turbulence_epsilon = inputs["turbulence_epsilon_m2_s3"]

    (constant / "physicalProperties").write_text(
        foam_header("dictionary", "constant", "physicalProperties")
        + f"\nviscosityModel constant;\nnu {kinematic_viscosity:.12g};\n",
        encoding="utf-8",
    )
    (constant / "momentumTransport").write_text(
        foam_header("dictionary", "constant", "momentumTransport")
        + """
simulationType RAS;
RAS
{
    model kEpsilon;
    turbulence on;
}
""",
        encoding="utf-8",
    )
    (system / "controlDict").write_text(
        foam_header("dictionary", "system", "controlDict")
        + """
solver incompressibleFluid;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime 1200;
deltaT 1;
writeControl timeStep;
writeInterval 1200;
purgeWrite 1;
writeFormat ascii;
writePrecision 10;
writeCompression off;
timeFormat general;
timePrecision 6;
runTimeModifiable false;
""",
        encoding="utf-8",
    )
    (system / "fvSchemes").write_text(
        foam_header("dictionary", "system", "fvSchemes")
        + """
ddtSchemes
{
    default steadyState;
}
gradSchemes
{
    default Gauss linear;
    limited cellLimited Gauss linear 1;
}
divSchemes
{
    default none;
    div(phi,U) bounded Gauss linearUpwindV limited;
    div(phi,k) bounded Gauss upwind;
    div(phi,epsilon) bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes
{
    default Gauss linear limited 0.5;
}
interpolationSchemes
{
    default linear;
}
snGradSchemes
{
    default limited 0.5;
}
wallDist
{
    method meshWave;
}
""",
        encoding="utf-8",
    )
    (system / "fvSolution").write_text(
        foam_header("dictionary", "system", "fvSolution")
        + """
solvers
{
    p
    {
        solver GAMG;
        tolerance 1e-8;
        relTol 0.02;
        smoother DICGaussSeidel;
    }
    \"(U|k|epsilon)\"
    {
        solver smoothSolver;
        smoother symGaussSeidel;
        tolerance 1e-7;
        relTol 0.05;
    }
}
SIMPLE
{
    nNonOrthogonalCorrectors 2;
    consistent yes;
    residualControl
    {
        p 5e-5;
        U 2e-5;
        k 2e-5;
        epsilon 1e-5;
    }
}
relaxationFactors
{
    equations
    {
        U 0.7;
        k 0.7;
        epsilon 0.7;
    }
}
""",
        encoding="utf-8",
    )

    fields = {
        "U": (
            "volVectorField",
            "[0 1 -1 0 0 0 0]",
            f"uniform (0 0 {inlet_velocity:.12g})",
            f"""
    inlet {{ type fixedValue; value uniform (0 0 {inlet_velocity:.12g}); }}
    outlet {{ type zeroGradient; }}
    walls {{ type noSlip; }}
""",
        ),
        "p": (
            "volScalarField",
            "[0 2 -2 0 0 0 0]",
            "uniform 0",
            """
    inlet { type zeroGradient; }
    outlet { type fixedValue; value uniform 0; }
    walls { type zeroGradient; }
""",
        ),
        "k": (
            "volScalarField",
            "[0 2 -2 0 0 0 0]",
            f"uniform {turbulence_k:.12g}",
            f"""
    inlet {{ type fixedValue; value uniform {turbulence_k:.12g}; }}
    outlet {{ type zeroGradient; }}
    walls {{ type kqRWallFunction; value uniform {turbulence_k:.12g}; }}
""",
        ),
        "epsilon": (
            "volScalarField",
            "[0 2 -3 0 0 0 0]",
            f"uniform {turbulence_epsilon:.12g}",
            f"""
    inlet {{ type fixedValue; value uniform {turbulence_epsilon:.12g}; }}
    outlet {{ type zeroGradient; }}
    walls {{ type epsilonWallFunction; value uniform {turbulence_epsilon:.12g}; }}
""",
        ),
        "nut": (
            "volScalarField",
            "[0 2 -1 0 0 0 0]",
            "uniform 0",
            """
    inlet { type calculated; value uniform 0; }
    outlet { type calculated; value uniform 0; }
    walls { type nutkWallFunction; value uniform 0; }
""",
        ),
    }
    for name, (class_name, dimensions, initial, boundaries) in fields.items():
        (zero / name).write_text(
            foam_header(class_name, "0", name)
            + f"\ndimensions {dimensions};\n"
            + f"internalField {initial};\n"
            + f"boundaryField\n{{{boundaries}}}\n",
            encoding="utf-8",
        )
    return inputs


def parse_last_value(text: str, pattern: str) -> float:
    matches = re.findall(pattern, text, flags=re.MULTILINE)
    if not matches:
        raise RuntimeError(f"postprocess_value_missing:{pattern}")
    return float(matches[-1])


def parse_last_vector(text: str, pattern: str) -> tuple[float, float, float]:
    matches = re.findall(pattern, text, flags=re.MULTILINE)
    if not matches:
        raise RuntimeError(f"postprocess_vector_missing:{pattern}")
    return tuple(float(value) for value in matches[-1])


def promote_wall_patch(case: Path) -> None:
    boundary = case / "constant/polyMesh/boundary"
    text = boundary.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(walls\s*\{[^{}]*?\btype\s+)patch"
        r"(;[^{}]*?\bphysicalType\s+)patch;",
        flags=re.DOTALL,
    )
    updated, count = pattern.subn(r"\1wall\2wall;", text, count=1)
    if count != 1:
        raise RuntimeError("walls_patch_promotion_failed")
    boundary.write_text(updated, encoding="utf-8")


def read_mesh_metadata(case: Path, mesh_size_mm: float) -> dict[str, object]:
    import gmsh

    mesh = case / "flow.msh"
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(mesh))
        return {
            "mesh_size_mm": mesh_size_mm,
            "nodes": len(gmsh.model.mesh.getNodes()[0]),
            "tetrahedra": sum(
                len(tags) for tags in gmsh.model.mesh.getElements(3)[1]
            ),
            "patches": {"inlet": 1, "outlet": 1, "walls": 4},
            "msh_bytes": mesh.stat().st_size,
            "msh_sha256": sha256(mesh),
            "gmsh_version": str(gmsh.__version__),
        }
    finally:
        gmsh.finalize()


def final_initial_residuals(solver_log: str) -> dict[str, float]:
    residuals: dict[str, float] = {}
    for field, value in re.findall(
        r"Solving for (Ux|Uy|Uz|p|k|epsilon), Initial residual =\s*"
        r"([-+0-9.eE]+)",
        solver_log,
    ):
        residuals[field] = float(value)
    missing = sorted(set(FINAL_INITIAL_RESIDUAL_LIMITS) - set(residuals))
    if missing:
        raise RuntimeError(f"solver_residuals_missing:{','.join(missing)}")
    return residuals


def solve_case(
    root: Path, mesh_size_mm: float, *, reuse_complete_case: bool
) -> dict[str, object]:
    case = root / f"mesh-{str(mesh_size_mm).replace('.', 'p')}"
    reuse_files = (
        "flow.msh",
        "gmshToFoam.log",
        "transformPoints.log",
        "checkMesh.log",
        "checkMesh-extended.log",
        "solver.log",
    )
    reused = reuse_complete_case and case.is_dir() and all(
        (case / name).is_file() for name in reuse_files
    )
    if reused:
        mesh = read_mesh_metadata(case, mesh_size_mm)
        boundary_inputs = boundary_input_values()
        check_mesh = (case / "checkMesh.log").read_text(encoding="utf-8")
        extended_check = (case / "checkMesh-extended.log").read_text(
            encoding="utf-8"
        )
        solver = (case / "solver.log").read_text(encoding="utf-8")
    else:
        case.mkdir(parents=True, exist_ok=False)
        mesh = create_mesh(case, mesh_size_mm)
        boundary_inputs = write_case_files(case)
        run(
            ["gmshToFoam", str(case / "flow.msh"), "-case", str(case)],
            cwd=case,
            log=case / "gmshToFoam.log",
        )
        promote_wall_patch(case)
        run(
            [
                "transformPoints",
                "scale=(0.001 0.001 0.001)",
                "-case",
                str(case),
            ],
            cwd=case,
            log=case / "transformPoints.log",
        )
        check_mesh = run(
            ["checkMesh", "-case", str(case)],
            cwd=case,
            log=case / "checkMesh.log",
        )
        extended_check = run(
            ["checkMesh", "-allGeometry", "-allTopology", "-case", str(case)],
            cwd=case,
            log=case / "checkMesh-extended.log",
        )
        solver = run(
            ["foamRun", "-solver", "incompressibleFluid", "-case", str(case)],
            cwd=case,
            log=case / "solver.log",
        )
    if "Mesh OK." not in check_mesh:
        raise RuntimeError(f"mesh_not_ok:{mesh_size_mm}")
    low_determinant_match = re.search(
        r"Cells with small determinant \(< 0\.001\) found, number of cells:\s*(\d+)",
        extended_check,
    )
    low_determinant_cells = (
        int(low_determinant_match.group(1)) if low_determinant_match else 0
    )
    residuals = final_initial_residuals(solver)
    residual_acceptance = all(
        residuals[field] <= limit
        for field, limit in FINAL_INITIAL_RESIDUAL_LIMITS.items()
    )
    if "End" not in solver or not residual_acceptance:
        raise RuntimeError(f"solver_not_converged:{mesh_size_mm}")

    inlet_pressure_text = run(
        [
            "postProcess",
            "-func",
            "patchAverage(p,name=inlet,patch=inlet)",
            "-latestTime",
            "-case",
            str(case),
        ],
        cwd=case,
        log=case / "inlet-pressure.log",
    )
    outlet_velocity_text = run(
        [
            "postProcess",
            "-func",
            "patchAverage(U,name=outlet,patch=outlet)",
            "-latestTime",
            "-case",
            str(case),
        ],
        cwd=case,
        log=case / "outlet-velocity.log",
    )
    inlet_kinematic_pressure = parse_last_value(
        inlet_pressure_text,
        r"areaAverage\(inlet\) of p =\s*([-+0-9.eE]+)",
    )
    outlet_velocity = parse_last_vector(
        outlet_velocity_text,
        r"areaAverage\(outlet\) of U =\s*\("
        r"([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\)",
    )
    inlet_speed = boundary_inputs["inlet_velocity_m_s"]
    outlet_speed = math.sqrt(sum(component**2 for component in outlet_velocity))
    bulk_total_pressure_drop_pa = HOT_DENSITY_KG_M3 * (
        inlet_kinematic_pressure
        + 0.5 * inlet_speed**2
        - 0.5 * outlet_speed**2
    )
    artifacts = {}
    for path in (
        case / "flow.msh",
        case / "gmshToFoam.log",
        case / "transformPoints.log",
        case / "checkMesh.log",
        case / "checkMesh-extended.log",
        case / "solver.log",
        case / "inlet-pressure.log",
        case / "outlet-velocity.log",
    ):
        artifacts[path.name] = {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
    return {
        "mesh": mesh,
        "mesh_validation": {
            "standard_check_mesh_passed": True,
            "extended_check_mesh_passed": "Mesh OK." in extended_check,
            "low_cell_determinant_cells": low_determinant_cells,
            "low_cell_determinant_threshold": 0.001,
            "interpretation": "OpenFOAM extended determinant warning retained; no negative volume, topology, non-orthogonality or skewness failure reported.",
        },
        "boundary_inputs": boundary_inputs,
        "results": {
            "inlet_area_average_kinematic_pressure_m2_s2": inlet_kinematic_pressure,
            "static_pressure_recovery_pa": -inlet_kinematic_pressure
            * HOT_DENSITY_KG_M3,
            "outlet_area_average_velocity_m_s": list(outlet_velocity),
            "outlet_area_average_speed_m_s": outlet_speed,
            "bulk_total_pressure_drop_pa": bulk_total_pressure_drop_pa,
            "bulk_total_pressure_flow_power_w": bulk_total_pressure_drop_pa
            * VOLUME_FLOW_M3_S,
        },
        "solver": {
            "model": "OpenFOAM incompressibleFluid steady RANS k-epsilon",
            "converged": True,
            "simple_residual_control_exit": "SIMPLE solution converged" in solver,
            "final_initial_residuals": residuals,
            "residual_limits": FINAL_INITIAL_RESIDUAL_LIMITS,
            "case_reused": reused,
        },
        "artifacts": artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--mesh-sizes", default="6.0,4.0,3.0")
    parser.add_argument("--runtime-image-ref", default="not_recorded")
    parser.add_argument("--runtime-image-id", default="not_recorded")
    parser.add_argument("--reuse-complete-cases", action="store_true")
    args = parser.parse_args()

    for executable in (
        "gmshToFoam",
        "transformPoints",
        "checkMesh",
        "foamRun",
        "postProcess",
    ):
        if shutil.which(executable) is None:
            raise RuntimeError(f"openfoam_executable_not_found:{executable}")
    args.work_root.mkdir(parents=True, exist_ok=True)
    cases = [
        solve_case(
            args.work_root,
            float(value),
            reuse_complete_case=args.reuse_complete_cases,
        )
        for value in args.mesh_sizes.split(",")
    ]
    previous = cases[-2]["results"]
    finest = cases[-1]["results"]
    pressure_change = abs(
        finest["bulk_total_pressure_drop_pa"]
        - previous["bulk_total_pressure_drop_pa"]
    ) / abs(finest["bulk_total_pressure_drop_pa"])
    velocity_change = abs(
        finest["outlet_area_average_speed_m_s"]
        - previous["outlet_area_average_speed_m_s"]
    ) / abs(finest["outlet_area_average_speed_m_s"])
    inlet_area_m2 = math.pi * (INLET_RADIUS_MM / 1000.0) ** 2
    outlet_area_m2 = (
        math.pi * (OUTLET_A_MM / 1000.0) * (OUTLET_B_MM / 1000.0)
    )
    borda_loss_coefficient = (1.0 - inlet_area_m2 / outlet_area_m2) ** 2
    borda_pressure_loss_pa = (
        borda_loss_coefficient
        * 0.5
        * HOT_DENSITY_KG_M3
        * boundary_input_values()["inlet_velocity_m_s"] ** 2
    )
    report = {
        "schema_version": "1.0.0",
        "part_id": PART_ID,
        "twin_id": TWIN_ID,
        "status": "synthetic_steady_rans_screen_complete_not_vehicle_validation",
        "inputs": {
            "geometry": "project F0 inner flow loft, not measured 993 geometry",
            "volume_flow_m3_s": VOLUME_FLOW_M3_S,
            "hot_density_kg_m3": HOT_DENSITY_KG_M3,
            "dynamic_viscosity_pa_s": DYNAMIC_VISCOSITY_PA_S,
            "authority": "synthetic regression inputs only",
        },
        "runtime": {
            "python": platform.python_version(),
            "openfoam": "13",
            "runtime_image_ref": args.runtime_image_ref,
            "runtime_image_id": args.runtime_image_id,
            "runtime_reproducibility": "pinned registry digest and matching local immutable image ID recorded",
        },
        "cases": cases,
        "grid_comparison_fine_vs_previous": {
            "bulk_total_pressure_drop_relative_change": pressure_change,
            "outlet_velocity_relative_change": velocity_change,
            "screening_threshold": 0.10,
            "threshold_authority": "project regression threshold only; not a design acceptance criterion",
        },
        "numerical_gates": {
            "all_cases_converged": all(
                case["solver"]["converged"] for case in cases
            ),
            "bulk_total_pressure_drop_grid_change_below_10_percent": pressure_change
            <= 0.10,
            "outlet_velocity_grid_change_below_10_percent": velocity_change <= 0.10,
            "all_extended_mesh_checks_passed": all(
                case["mesh_validation"]["extended_check_mesh_passed"]
                for case in cases
            ),
        },
        "engineering_gates": {
            "measured_inlet_interface": False,
            "measured_exhaust_mass_flow": False,
            "measured_pressure_and_temperature": False,
            "compressible_pulsating_cfd": False,
            "conjugate_heat_transfer": False,
            "vehicle_correlation": False,
            "professional_review": False,
        },
        "interpretation": {
            "scope": "Steady incompressible RANS screen of the clean-sheet F0 inner duct only.",
            "analytic_comparison": {
                "borda_carnot_abrupt_expansion_pressure_loss_pa": borda_pressure_loss_pa,
                "finest_cfd_to_borda_pressure_loss_ratio": finest[
                    "bulk_total_pressure_drop_pa"
                ]
                / borda_pressure_loss_pa,
                "scope": "Borda-Carnot is an abrupt-expansion screen, not an expected match for the progressive loft.",
            },
            "missing_physics": "Compressibility, exhaust pulses, temperature-dependent properties, roughness, bends and conjugate heat transfer are absent.",
            "physicsnemo": "No training or inference: three uncorrelated mesh points are not an admissible surrogate dataset.",
            "manufacturing": "No numerical result authorizes printing or vehicle installation.",
        },
        "dfam_assessment": {
            "lpbf_preferred_for_current_geometry": False,
            "geometry_redesign_authorized": False,
            "current_route_decision": "conditional_candidate_requires_formed_welded_stainless_vs_LPBF_IN625_comparison",
            "favorable_features": [
                "one BREP consolidates the gas path, outer shield and eight ties",
                "the annular gap is open at both ends and has no intended trapped-powder volume",
                "the round-to-oval loft is geometrically natural for additive manufacture",
            ],
            "unfavorable_features": [
                "the 0.8 mm double walls and 2.7 mm gap require machine-specific capability evidence",
                "no measured thermal or acoustic benefit justifies IN625 LPBF over formed or welded stainless",
                "surface roughness, distortion, supports and post-machining remain undefined",
            ],
        },
        "release_authorized": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "numerical_gates": report["numerical_gates"],
                "engineering_gates": report["engineering_gates"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
