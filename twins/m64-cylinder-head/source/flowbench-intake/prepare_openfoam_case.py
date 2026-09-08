#!/usr/bin/env python3
"""Prepare an explicitly unqualified OpenFOAM Foundation 14 intake pilot.

No geometry is generated here. Mesh conversion/qualification and execution
remain separate, observed steps. A synthetic runtime smoke is never a head run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil

IMAGE_ID = "sha256:a233511bef9b4fbf0653ca94258061d61b3fccbd6b4e3ef6d71c669d70de1c17"
UNIVERSAL_R = 8314.46261815324  # J/(kmol K), perfect-gas molecular-weight conversion
PATCHES = {"inlet": "patch", "receiver_outlet": "patch", "walls": "wall"}


def header(name: str, cls: str = "dictionary") -> str:
    return ("FoamFile\n{\n    version 2.0;\n    format ascii;\n"
            f"    class {cls};\n    object {name};\n}}\n\n")


def field(name: str, dimensions: str, internal: str, conditions: dict[str, str],
          vector: bool = False) -> str:
    body = header(name, "volVectorField" if vector else "volScalarField")
    body += f"dimensions {dimensions};\ninternalField uniform {internal};\nboundaryField\n{{\n"
    for patch in PATCHES:
        body += f"    {patch}\n    {{\n        {conditions[patch]}\n    }}\n"
    return body + "}\n"


def validate_policy(policy: dict) -> dict:
    if policy.get("schema") != "m64-intake-flowbench-pilot/v1":
        raise ValueError("unrecognized intake policy")
    inp = policy["inputs"]
    for key, value in inp.items():
        if isinstance(value, (int, float)) and (isinstance(value, bool) or not math.isfinite(value) or value <= 0):
            raise ValueError(f"invalid positive input: {key}")
    p0 = float(inp["inlet_total_pressure_Pa"])
    dp = float(inp["pressure_drop_inH2O_conventional"] * inp["Pa_per_inH2O_conventional"])
    gamma = float(inp["air_gamma_for_reference_normalization"])
    if not 0 < dp < p0 or gamma <= 1 or inp["intake_valve_count"] != 2:
        raise ValueError("invalid pressure, gamma or intake valve count")
    if inp["pilot_lift_mm"] != 6 or inp["receiver_bore_mm"] != 100:
        raise ValueError("this generator is scoped to the current 6 mm / 100 mm pilot")
    return {"p0": p0, "pout": p0 - dp, "T0": float(inp["inlet_total_temperature_K"]),
            "R": float(inp["air_gas_constant_J_kg_K"]), "gamma": gamma}


def check_mesh_format(text: str) -> None:
    if not re.search(r"\$MeshFormat\s+2\.2\s+0\s+8\s+\$EndMeshFormat", text):
        raise ValueError("expected Gmsh 2.2 ASCII double precision")
    section = re.search(r"\$PhysicalNames\s+(\d+)\s*\n(.*?)\$EndPhysicalNames", text, re.S)
    if section is None:
        raise ValueError("physical groups missing")
    groups = re.findall(r'^\s*([23])\s+(\d+)\s+"([A-Za-z_][A-Za-z_0-9]*)"\s*$', section[2], re.M)
    expected = {(2, "inlet"), (2, "receiver_outlet"), (2, "walls"), (3, "air")}
    if len(groups) != 4 or int(section[1]) != 4 or {(int(d), n) for d, _, n in groups} != expected:
        raise ValueError("expected exactly inlet, receiver_outlet, walls and air physical groups")
    if len({(d, tag) for d, tag, _ in groups}) != 4:
        raise ValueError("physical group tag collision")
    # This is intentionally only a format contract, not mesh topology validation.


def case_files(policy: dict, iterations: int) -> dict[str, str]:
    p = validate_policy(policy)
    if isinstance(iterations, bool) or not isinstance(iterations, int) or not 1 <= iterations <= 5000:
        raise ValueError("iterations must be an integer in [1, 5000]")
    g, T, p0, pout = p["gamma"], p["T0"], p["p0"], p["pout"]
    files = {}
    files["0/p"] = field("p", "[1 -1 -2 0 0 0 0]", f"{pout:.12g}", {
        "inlet": f"type totalPressure; psi psi; gamma {g:.12g}; p0 uniform {p0:.12g}; value uniform {p0:.12g};",
        "receiver_outlet": f"type fixedValue; value uniform {pout:.12g};",
        "walls": "type zeroGradient;"})
    files["0/U"] = field("U", "[0 1 -1 0 0 0 0]", "(0 0 0)", {
        "inlet": "type pressureInletOutletVelocity; value uniform (0 0 0);",
        "receiver_outlet": "type pressureInletOutletVelocity; value uniform (0 0 0);",
        "walls": "type noSlip;"}, vector=True)
    files["0/T"] = field("T", "[0 0 0 1 0 0 0]", f"{T:.12g}", {
        "inlet": f"type totalTemperature; gamma {g:.12g}; T0 uniform {T:.12g}; value uniform {T:.12g};",
        "receiver_outlet": f"type inletOutlet; inletValue uniform {T:.12g}; value uniform {T:.12g};",
        "walls": "type zeroGradient;"})
    files["0/k"] = field("k", "[0 2 -2 0 0 0 0]", "1", {
        "inlet": "type turbulentKineticEnergy; intensity 0.05; value uniform 1;",
        "receiver_outlet": "type inletOutlet; inletValue uniform 1; value uniform 1;",
        "walls": "type kqRWallFunction; value uniform 1;"})
    files["0/omega"] = field("omega", "[0 0 -1 0 0 0 0]", "200", {
        "inlet": "type turbulentOmega; mixingLength 0.003; value uniform 200;",
        "receiver_outlet": "type inletOutlet; inletValue uniform 200; value uniform 200;",
        "walls": "type omegaWallFunction; value uniform 200;"})
    for name, dims, wall in (("nut", "[0 2 -1 0 0 0 0]", "nutkWallFunction"),
                             ("alphat", "[1 -1 -1 0 0 0 0]", "compressible::alphatWallFunction")):
        files[f"0/{name}"] = field(name, dims, "0", {
            "inlet": "type calculated; value uniform 0;",
            "receiver_outlet": "type calculated; value uniform 0;",
            "walls": f"type {wall}; value uniform 0;"})
    files["constant/physicalProperties"] = header("physicalProperties") + f"""
thermoType
{{
    type hePsiThermo; mixture pureMixture; transport const;
    thermo hConst; equationOfState perfectGas; specie specie;
    energy sensibleEnthalpy;
}}
mixture
{{
    specie {{ molWeight {UNIVERSAL_R / p['R']:.15g}; }}
    thermodynamics {{ Cp {g * p['R'] / (g - 1):.15g}; hf 0; }}
    transport {{ mu 1.82e-5; Pr 0.71; }}
}}
"""
    files["constant/momentumTransport"] = header("momentumTransport") + "simulationType RAS;\nRAS { model kOmegaSST; turbulence on; }\n"
    files["constant/thermophysicalTransport"] = header("thermophysicalTransport") + "RAS { model eddyDiffusivity; Prt 0.85; }\n"
    files["system/fvSchemes"] = header("fvSchemes") + """
ddtSchemes { default steadyState; }
gradSchemes { default cellLimited Gauss linear 1; }
divSchemes
{
    default none;
    div(phi,U) bounded Gauss linearUpwind grad(U);
    div(phi,h) bounded Gauss linearUpwind grad(h);
    div(phi,K) bounded Gauss linearUpwind grad(K);
    div(phi,k) bounded Gauss upwind;
    div(phi,omega) bounded Gauss upwind;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear limited 0.5; }
interpolationSchemes { default linear; }
snGradSchemes { default limited 0.5; }
wallDist { method meshWave; }
"""
    files["system/fvSolution"] = header("fvSolution") + """
solvers
{
    p { solver GAMG; smoother DIC; tolerance 1e-8; relTol 0.01; }
    "(U|k|omega|h)" { solver PBiCGStab; preconditioner DILU; tolerance 1e-9; relTol 0.05; }
}
PIMPLE { nNonOrthogonalCorrectors 2; }
relaxationFactors
{
    fields { p 0.2; rho 0.1; }
    equations { U 0.5; h 0.5; "(k|omega)" 0.5; }
}
"""
    files["system/controlDict"] = header("controlDict") + f"""
solver fluid;
startFrom startTime; startTime 0; stopAt endTime; endTime {iterations}; deltaT 1;
writeControl timeStep; writeInterval {min(iterations, 100)}; purgeWrite 2;
writeFormat ascii; writePrecision 12; writeCompression off;
timeFormat general; timePrecision 10; runTimeModifiable false;
functions
{{
"""
    for patch in PATCHES:
        files["system/controlDict"] += f"""
    massFlow_{patch}
    {{
        type surfaceFieldValue; libs ("libfieldFunctionObjects.so");
        log true; writeControl timeStep; writeInterval 1; writeFields false;
        writeArea true; patch {patch}; operation orientedSum; fields (phi);
    }}
"""
    files["system/controlDict"] += """
    yPlus { type yPlus; libs ("libfieldFunctionObjects.so"); writeControl writeTime; }
    scalarMinima
    {
        type volFieldValue; libs ("libfieldFunctionObjects.so");
        cellZone all; operation min; fields (p T k omega);
        log true; writeFields false; writeControl timeStep; writeInterval 10;
    }
    scalarMaxima
    {
        type volFieldValue; libs ("libfieldFunctionObjects.so");
        cellZone all; operation max; fields (p T k omega);
        log true; writeFields false; writeControl timeStep; writeInterval 10;
    }
    maximumSpeed
    {
        type volFieldValue; libs ("libfieldFunctionObjects.so");
        cellZone all; operation maxMag; fields (U);
        log true; writeFields false; writeControl timeStep; writeInterval 10;
    }
}
"""
    files["system/createPatchDict"] = header("createPatchDict") + "pointSync false;\npatches\n(\n" + "\n".join(
        f"{{ name {name}; patchInfo {{ type {kind}; }} constructFrom patches; patches ({name}); }}"
        for name, kind in PATCHES.items()) + "\n);\n"
    files["system/decomposeParDict"] = header("decomposeParDict") + "numberOfSubdomains 4;\nmethod scotch;\n"
    return files


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy", type=Path, required=True)
    ap.add_argument("--mesh", type=Path, required=True)
    ap.add_argument("--case-dir", type=Path, required=True)
    ap.add_argument("--purpose", choices=("head_pilot", "synthetic_runtime_smoke"), required=True)
    ap.add_argument("--iterations", type=int, default=600)
    args = ap.parse_args()
    policy_bytes = args.policy.read_bytes()
    mesh_bytes = args.mesh.read_bytes()
    check_mesh_format(mesh_bytes.decode("ascii"))
    files = case_files(json.loads(policy_bytes), args.iterations)
    args.case_dir.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        path = args.case_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="ascii")
    shutil.copyfile(args.mesh, args.case_dir / "input.msh")
    manifest = {
        "schema": "m64-openfoam-intake-case/v1", "status": "prepared_not_executed",
        "purpose": args.purpose, "manufacturing_authorized": False, "head_CFD_executed": False,
        "CFD_qualified": False, "convergence_demonstrated": False,
        "local_runtime_image_ID": IMAGE_ID, "registry_image_qualified_for_new_rental": False,
        "policy_sha256": hashlib.sha256(policy_bytes).hexdigest(),
        "mesh_sha256": hashlib.sha256(mesh_bytes).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "file_sha256": {n: hashlib.sha256(s.encode("ascii")).hexdigest() for n, s in files.items()},
        "mesh_input_length_units": "scan_unit", "meters_per_scan_unit_hypothesis": 0.001,
        "scale_command_before_solving": 'transformPoints "scale=(0.001 0.001 0.001)"',
        "scale_applied_by_generator": False,
        "steady_iterations": args.iterations, "iterations_are_physical_seconds": False,
        "statistical_window_iterations": 100, "spatial_levels_executed": 0,
        "turbulence": {"model": "kOmegaSST", "inlet_intensity": 0.05, "mixing_length_m": 0.003,
                       "authority": "unmeasured_pilot_assumptions_sensitivity_and_wall_resolution_required"},
        "wall_thermal_boundary": "adiabatic_cold_flow_not_head_heat_rejection",
        "entry_fixture_radius_validated": False,
        "results": {"mass_flow_kg_s": None, "CdA_m2": None, "Cd": None, "engine_power_PS": None},
        "required_before_execution": ["independent_geometry_boundary_review", "gmshToFoam",
                                      "one_time_explicit_scale", "createPatch", "checkMesh_Mesh_OK",
                                      "exact_three_nonempty_patches", "observed_runtime_exit_and_logs"],
    }
    (args.case_dir / "case-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"status": manifest["status"], "purpose": args.purpose, "case": str(args.case_dir)}))


if __name__ == "__main__":
    main()
