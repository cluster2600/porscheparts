#!/usr/bin/env python3
"""Construit le contrôle CFD F50 stationnaire incompressible sur F48.

Ce contrôle de conductance conserve le différentiel de pression physique F49.
La densité constante propre à chaque écran est calculée à l'état source idéal.
Il ne résout pas l'énergie et ne peut donc pas ouvrir une porte thermique.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


PATCHES = ("intake", "exhaust", "valve", "chamber", "deck", "bore", "walls")
R_AIR_J_KG_K = 287.05


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("f49_builder_inc", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module_introuvable:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def header(name: str, cls: str, location: str) -> str:
    return f"FoamFile\n{{\n    format ascii;\n    class {cls};\n    location \"{location}\";\n    object {name};\n}}\n\n"


def boundary(entries: dict[str, str]) -> str:
    lines = ["boundaryField", "{"]
    for patch in PATCHES:
        lines += [f"    {patch}", "    {", *[f"        {line}" for line in entries[patch].splitlines()], "    }"]
    return "\n".join(lines) + "\n}\n"


def field(name: str, cls: str, dimensions: str, initial: str, entries: dict[str, str]) -> str:
    return header(name, cls, "0") + f"dimensions {dimensions};\ninternalField uniform {initial};\n\n" + boundary(entries)


def overwrite_case(case: Path, record: dict, f49_contract: dict, iterations: int) -> None:
    screen = f49_contract["openfoam"]["screens"][record["screen"]]
    source = screen["source_patch"]
    sink = screen["sink_patch"]
    walls = set(record["wall_patches"])
    rho = screen["source_total_pressure_pa_abs"] / (R_AIR_J_KG_K * screen["source_temperature_k"])
    nu = f49_contract["openfoam"]["common_boundary_conditions"].get("dynamic_viscosity_pa_s", 1.82e-5) / rho
    # p est une pression cinématique dans incompressibleFluid.
    p0 = screen["imposed_pressure_difference_pa"] / rho
    kval = f49_contract["openfoam"]["common_boundary_conditions"]["turbulent_kinetic_energy_m2_s2"]
    omega = f49_contract["openfoam"]["common_boundary_conditions"]["specific_dissipation_rate_s-1"]
    entries = {name: {} for name in ("U", "p", "k", "omega", "nut")}
    for patch in PATCHES:
        if patch == source:
            entries["U"][patch] = "type pressureInletOutletVelocity;\nvalue uniform (0 0 0);"
            entries["p"][patch] = f"type totalPressure;\np0 uniform {p0:.12g};\nvalue uniform {p0:.12g};"
            entries["k"][patch] = f"type fixedValue;\nvalue uniform {kval};"
            entries["omega"][patch] = f"type fixedValue;\nvalue uniform {omega};"
            entries["nut"][patch] = "type calculated;\nvalue uniform 0;"
        elif patch == sink:
            entries["U"][patch] = "type pressureInletOutletVelocity;\nvalue uniform (0 0 0);"
            entries["p"][patch] = "type fixedValue;\nvalue uniform 0;"
            entries["k"][patch] = f"type inletOutlet;\ninletValue uniform {kval};\nvalue uniform {kval};"
            entries["omega"][patch] = f"type inletOutlet;\ninletValue uniform {omega};\nvalue uniform {omega};"
            entries["nut"][patch] = "type calculated;\nvalue uniform 0;"
        else:
            if patch not in walls:
                raise RuntimeError(f"patch_non_classee:{record['case_id']}:{patch}")
            entries["U"][patch] = "type noSlip;"
            entries["p"][patch] = "type zeroGradient;"
            entries["k"][patch] = f"type kqRWallFunction;\nvalue uniform {kval};"
            entries["omega"][patch] = f"type omegaWallFunction;\nvalue uniform {omega};"
            entries["nut"][patch] = "type nutkWallFunction;\nvalue uniform 0;"
    zero = case / "0"
    (zero / "U").write_text(field("U", "volVectorField", "[0 1 -1 0 0 0 0]", "(0 0 0)", entries["U"]), encoding="utf-8")
    (zero / "p").write_text(field("p", "volScalarField", "[0 2 -2 0 0 0 0]", "0", entries["p"]), encoding="utf-8")
    (zero / "k").write_text(field("k", "volScalarField", "[0 2 -2 0 0 0 0]", str(kval), entries["k"]), encoding="utf-8")
    (zero / "omega").write_text(field("omega", "volScalarField", "[0 0 -1 0 0 0 0]", str(omega), entries["omega"]), encoding="utf-8")
    (zero / "nut").write_text(field("nut", "volScalarField", "[0 2 -1 0 0 0 0]", "0", entries["nut"]), encoding="utf-8")
    for obsolete in ("T", "alphat"):
        path = zero / obsolete
        if path.exists():
            path.unlink()
    (case / "constant" / "physicalProperties").write_text(
        header("physicalProperties", "dictionary", "constant") + f"viscosityModel constant;\nnu {nu:.12g};\n",
        encoding="utf-8",
    )
    (case / "constant" / "momentumTransport").write_text(
        header("momentumTransport", "dictionary", "constant")
        + "simulationType RAS;\nRAS { model kOmegaSST; turbulence on; viscosityModel Newtonian; }\n",
        encoding="utf-8",
    )
    constraints = case / "system" / "fvConstraints"
    if constraints.exists():
        constraints.unlink()
    wall_list = " ".join(record["wall_patches"])
    (case / "system" / "controlDict").write_text(
        header("controlDict", "dictionary", "system")
        + f"""solver incompressibleFluid;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime {iterations};
deltaT 1;
writeControl timeStep;
writeInterval 250;
purgeWrite 2;
writeFormat ascii;
writePrecision 12;
runTimeModifiable false;
functions
{{
    residuals {{ type residuals; libs (\"libutilityFunctionObjects.so\"); writeControl timeStep; writeInterval 20; fields (p U k omega); }}
    sourceVolumeFlow {{ type surfaceFieldValue; libs (\"libfieldFunctionObjects.so\"); writeControl timeStep; writeInterval 20; writeFields false; patch {source}; operation sum; fields (phi); }}
    sinkVolumeFlow {{ type surfaceFieldValue; libs (\"libfieldFunctionObjects.so\"); writeControl timeStep; writeInterval 20; writeFields false; patch {sink}; operation sum; fields (phi); }}
    sourceKinematicPressure {{ type surfaceFieldValue; libs (\"libfieldFunctionObjects.so\"); writeControl timeStep; writeInterval 20; writeFields false; patch {source}; operation areaAverage; fields (p); }}
    sinkKinematicPressure {{ type surfaceFieldValue; libs (\"libfieldFunctionObjects.so\"); writeControl timeStep; writeInterval 20; writeFields false; patch {sink}; operation areaAverage; fields (p); }}
}}
""",
        encoding="utf-8",
    )
    (case / "system" / "fvSchemes").write_text(
        header("fvSchemes", "dictionary", "system")
        + """ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; limited cellLimited Gauss linear 1; grad(U) $limited; grad(k) $limited; grad(omega) $limited; }
divSchemes
{
    default none;
    div(phi,U) bounded Gauss upwind;
    div(phi,k) bounded Gauss upwind;
    div(phi,omega) bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear limited corrected 0.5; }
interpolationSchemes { default linear; }
snGradSchemes { default limited 0.5; }
wallDist { method meshWave; }
""",
        encoding="utf-8",
    )
    (case / "system" / "fvSolution").write_text(
        header("fvSolution", "dictionary", "system")
        + """solvers
{
    p { solver GAMG; tolerance 1e-8; relTol 0.05; smoother GaussSeidel; }
    pcorr { solver GAMG; tolerance 1e-8; relTol 0; smoother GaussSeidel; }
    "(U|k|omega)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-9; relTol 0.1; }
}
SIMPLE { nNonOrthogonalCorrectors 1; consistent yes; }
relaxationFactors { equations { U 0.5; k 0.4; omega 0.3; ".*" 0.3; } }
""",
        encoding="utf-8",
    )
    metadata_path = case / "case.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "phase": "F50",
            "formulation": "steady incompressible RANS kOmegaSST",
            "source_density_kg_m3": rho,
            "kinematic_viscosity_m2_s": nu,
            "imposed_kinematic_pressure_difference_m2_s2": p0,
            "imposed_physical_pressure_difference_pa": screen["imposed_pressure_difference_pa"],
            "energy_equation_solved": False,
            "outer_or_inner_geometry_modified": False,
            "ellipse_or_oval_proxy_used": False,
            "fixed_iterations": iterations,
        }
    )
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--domain-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=6000)
    args = parser.parse_args()
    root = args.project_root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    f49 = load_module(root / "twins/reference-917-engine/source/build_cfd_cases_f49.py")
    f49_contract_path = root / "twins/reference-917-engine/f49-cfd-cht-contract.json"
    correction_path = root / "twins/reference-917-engine/f49-cfd-cht-corrective-coarse.json"
    manifest = f49.build(root, args.domain_root.resolve(), output, f49_contract_path, correction_path)
    contract = json.loads(f49_contract_path.read_text(encoding="utf-8"))
    for record in manifest["cases"]:
        overwrite_case(output / "cases" / record["case_id"], record, contract, args.iterations)
    manifest.update(
        {
            "schema_version": "porsche-917-f50-incompressible-case-manifest/v1",
            "formulation": "steady incompressible RANS kOmegaSST",
            "case_count": len(manifest["cases"]),
            "energy_equation_solved": False,
            "outer_or_inner_geometry_modified": False,
            "ellipse_or_oval_proxy_used": False,
        }
    )
    (output / "case-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(manifest["cases"]), "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
