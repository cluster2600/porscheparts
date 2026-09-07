#!/usr/bin/env python3
"""Prépare les écrans CFD statiques F49 à partir des maillages F48.

Les cas produits sont des écrans de conductance port/chambre. Ils ne contiennent
ni piston mobile, ni loi de levée, ni solide de culasse. Le script vérifie les
hashes F48 avant de copier tout maillage local dans le répertoire de travail.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


PATCHES = ("intake", "exhaust", "valve", "chamber", "deck", "bore", "walls")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def foam_header(object_name: str, class_name: str, location: str) -> str:
    return f"""FoamFile
{{
    format      ascii;
    class       {class_name};
    location    \"{location}\";
    object      {object_name};
}}

"""


def boundary_block(entries: dict[str, str]) -> str:
    lines = ["boundaryField", "{"]
    for patch in PATCHES:
        lines.extend([f"    {patch}", "    {", *[f"        {line}" for line in entries[patch].splitlines()], "    }"])
    lines.append("}")
    return "\n".join(lines) + "\n"


def field_text(name: str, class_name: str, dimensions: str, initial: str, entries: dict[str, str]) -> str:
    return (
        foam_header(name, class_name, "0")
        + f"dimensions      {dimensions};\n\n"
        + f"internalField   uniform {initial};\n\n"
        + boundary_block(entries)
    )


def wall_patches(screen: dict) -> list[str]:
    flow = {screen["source_patch"], screen["sink_patch"]}
    return [patch for patch in PATCHES if patch not in flow]


def prepare_fields(case: Path, contract: dict, screen_name: str, correction: dict | None = None) -> None:
    screen = contract["openfoam"]["screens"][screen_name]
    common = contract["openfoam"]["common_boundary_conditions"]
    source = screen["source_patch"]
    sink = screen["sink_patch"]
    p0 = screen["source_total_pressure_pa_abs"]
    pout = screen["sink_static_pressure_pa_abs"]
    tin = screen["source_temperature_k"]
    twall = common["wall_temperature_k"]
    kval = common["turbulent_kinetic_energy_m2_s2"]
    omega = common["specific_dissipation_rate_s-1"]
    walls = set(wall_patches(screen))
    initial_pressure = 0.5 * (p0 + pout) if correction is not None else pout

    u_entries = {}
    p_entries = {}
    t_entries = {}
    k_entries = {}
    omega_entries = {}
    alphat_entries = {}
    nut_entries = {}
    for patch in PATCHES:
        if patch == source:
            u_entries[patch] = "type pressureInletOutletVelocity;\nvalue uniform (0 0 0);"
            p_entries[patch] = f"type totalPressure;\np0 uniform {p0};\ngamma 1.4;\nvalue uniform {p0};"
            t_entries[patch] = f"type fixedValue;\nvalue uniform {tin};"
            k_entries[patch] = f"type fixedValue;\nvalue uniform {kval};"
            omega_entries[patch] = f"type fixedValue;\nvalue uniform {omega};"
            alphat_entries[patch] = "type calculated;\nvalue uniform 0;"
            nut_entries[patch] = "type calculated;\nvalue uniform 0;"
        elif patch == sink:
            u_entries[patch] = "type pressureInletOutletVelocity;\nvalue uniform (0 0 0);"
            p_entries[patch] = f"type fixedValue;\nvalue uniform {pout};"
            t_entries[patch] = f"type inletOutlet;\ninletValue uniform {tin};\nvalue uniform {tin};"
            k_entries[patch] = f"type inletOutlet;\ninletValue uniform {kval};\nvalue uniform {kval};"
            omega_entries[patch] = f"type inletOutlet;\ninletValue uniform {omega};\nvalue uniform {omega};"
            alphat_entries[patch] = "type calculated;\nvalue uniform 0;"
            nut_entries[patch] = "type calculated;\nvalue uniform 0;"
        else:
            require(patch in walls, f"patch_non_classee:{patch}")
            u_entries[patch] = "type noSlip;"
            p_entries[patch] = "type zeroGradient;"
            t_entries[patch] = f"type fixedValue;\nvalue uniform {twall};"
            k_entries[patch] = f"type kqRWallFunction;\nvalue uniform {kval};"
            omega_entries[patch] = f"type omegaWallFunction;\nvalue uniform {omega};"
            alphat_entries[patch] = "type compressible::alphatWallFunction;\nvalue uniform 0;"
            nut_entries[patch] = "type nutkWallFunction;\nvalue uniform 0;"

    fields = {
        "U": field_text("U", "volVectorField", "[0 1 -1 0 0 0 0]", "(0 0 0)", u_entries),
        "p": field_text("p", "volScalarField", "[1 -1 -2 0 0 0 0]", str(initial_pressure), p_entries),
        "T": field_text("T", "volScalarField", "[0 0 0 1 0 0 0]", str(tin), t_entries),
        "k": field_text("k", "volScalarField", "[0 2 -2 0 0 0 0]", str(kval), k_entries),
        "omega": field_text("omega", "volScalarField", "[0 0 -1 0 0 0 0]", str(omega), omega_entries),
        "alphat": field_text("alphat", "volScalarField", "[1 -1 -1 0 0 0 0]", "0", alphat_entries),
        "nut": field_text("nut", "volScalarField", "[0 2 -1 0 0 0 0]", "0", nut_entries),
    }
    for name, text in fields.items():
        (case / "0" / name).write_text(text, encoding="utf-8")


def prepare_dictionaries(case: Path, contract: dict, screen_name: str, variant: str, correction: dict | None = None) -> None:
    screen = contract["openfoam"]["screens"][screen_name]
    source = screen["source_patch"]
    sink = screen["sink_patch"]
    walls = " ".join(wall_patches(screen))
    numerical = correction["numerical_controls"] if correction is not None else {}
    end_time = numerical.get("end_time_s", contract["openfoam"]["end_time_s"])
    delta_t = numerical.get("initial_time_step_s", contract["openfoam"]["initial_time_step_s"])
    max_co = numerical.get("maximum_Courant_number", contract["openfoam"]["maximum_Courant_number"])
    max_delta_t = numerical.get("maximum_time_step_s", 0.0001)
    n_outer = numerical.get("n_outer_correctors", 1)
    n_correctors = numerical.get("n_correctors", 2)
    n_non_orthogonal = numerical.get("n_non_orthogonal_correctors", 1)
    relaxation = numerical.get("equation_relaxation", {"U": 1, "h": 1, "k": 1, "omega": 1})
    gradient_limiter = numerical.get("gradient_limiter", 1)
    laplacian_limiter = numerical.get("laplacian_correction_limiter")
    velocity_advection = "bounded Gauss upwind" if correction is not None else "bounded Gauss linearUpwind limited"
    laplacian_scheme = (
        f"Gauss linear limited corrected {laplacian_limiter}"
        if laplacian_limiter is not None
        else "Gauss linear corrected"
    )
    sn_grad_scheme = f"limited {laplacian_limiter}" if laplacian_limiter is not None else "corrected"
    (case / "constant" / "physicalProperties").write_text(
        foam_header("physicalProperties", "dictionary", "constant")
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
    specie { molWeight 28.9; }
    thermodynamics { Cp 1005; hf 0; Tref 298.15; hsRef 0; }
    transport { mu 1.82e-05; Pr 0.71; }
}
""",
        encoding="utf-8",
    )
    (case / "constant" / "momentumTransport").write_text(
        foam_header("momentumTransport", "dictionary", "constant")
        + "simulationType RAS;\nRAS { model kOmegaSST; turbulence on; }\n",
        encoding="utf-8",
    )
    (case / "system" / "controlDict").write_text(
        foam_header("controlDict", "dictionary", "system")
        + f"""solver fluid;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime {end_time};
deltaT {delta_t};
adjustTimeStep yes;
maxCo {max_co};
maxDeltaT {max_delta_t};
writeControl adjustableRunTime;
writeInterval 0.002;
purgeWrite 2;
writeFormat ascii;
writePrecision 12;
runTimeModifiable false;
functions
{{
    velocityMagnitudeSquared
    {{
        type magSqr;
        libs (\"libfieldFunctionObjects.so\");
        field U;
        result UMagSqr;
        executeControl timeStep;
        executeInterval 1;
        writeControl adjustableRunTime;
        writeInterval 0.0002;
    }}
    residuals
    {{
        type residuals;
        libs (\"libutilityFunctionObjects.so\");
        writeControl adjustableRunTime;
        writeInterval 0.0002;
        fields (p U T k omega h);
    }}
    sourceMassFlow
    {{
        type surfaceFieldValue;
        libs (\"libfieldFunctionObjects.so\");
        writeControl adjustableRunTime;
        writeInterval 0.0002;
        writeFields false;
        patch {source};
        operation sum;
        fields (phi);
    }}
    sinkMassFlow
    {{
        type surfaceFieldValue;
        libs (\"libfieldFunctionObjects.so\");
        writeControl adjustableRunTime;
        writeInterval 0.0002;
        writeFields false;
        patch {sink};
        operation sum;
        fields (phi);
    }}
    sourcePressure
    {{
        type surfaceFieldValue;
        libs (\"libfieldFunctionObjects.so\");
        writeControl adjustableRunTime;
        writeInterval 0.0002;
        writeFields false;
        patch {source};
        operation areaAverage;
        fields (p);
    }}
    sinkPressure
    {{
        type surfaceFieldValue;
        libs (\"libfieldFunctionObjects.so\");
        writeControl adjustableRunTime;
        writeInterval 0.0002;
        writeFields false;
        patch {sink};
        operation areaAverage;
        fields (p);
    }}
    sinkTemperature
    {{
        type surfaceFieldValue;
        libs (\"libfieldFunctionObjects.so\");
        writeControl adjustableRunTime;
        writeInterval 0.0002;
        writeFields false;
        patch {sink};
        operation average;
        weightField phi;
        fields (T);
    }}
    sourceTotalEnergyTerms
    {{
        type surfaceFieldValue;
        libs (\"libfieldFunctionObjects.so\");
        writeControl adjustableRunTime;
        writeInterval 0.0002;
        writeFields false;
        patch {source};
        operation average;
        weightField phi;
        fields (T UMagSqr);
    }}
    sinkTotalEnergyTerms
    {{
        type surfaceFieldValue;
        libs (\"libfieldFunctionObjects.so\");
        writeControl adjustableRunTime;
        writeInterval 0.0002;
        writeFields false;
        patch {sink};
        operation average;
        weightField phi;
        fields (T UMagSqr);
    }}
    rhoTimesEnthalpy
    {{
        type multiply;
        libs ("libfieldFunctionObjects.so");
        fields (rho h);
        result rhoH;
        executeControl timeStep;
        executeInterval 1;
        writeControl timeStep;
        writeInterval 1000000000;
    }}
    rhoTimesVelocityMagnitudeSquared
    {{
        type multiply;
        libs ("libfieldFunctionObjects.so");
        fields (rho UMagSqr);
        result rhoUMagSqr;
        executeControl timeStep;
        executeInterval 1;
        writeControl timeStep;
        writeInterval 1000000000;
    }}
    fluidEnthalpyIntegral
    {{
        type volFieldValue;
        libs ("libfieldFunctionObjects.so");
        writeControl adjustableRunTime;
        writeInterval 0.0002;
        writeFields false;
        operation volIntegrate;
        cellZone fluid_gas_{variant};
        fields (rhoH);
    }}
    fluidKineticIntegral
    {{
        type volFieldValue;
        libs ("libfieldFunctionObjects.so");
        writeControl adjustableRunTime;
        writeInterval 0.0002;
        writeFields false;
        operation volIntegrate;
        cellZone fluid_gas_{variant};
        fields (rhoUMagSqr);
    }}
    headHeatFlux
    {{
        type wallHeatFlux;
        libs (\"libfieldFunctionObjects.so\");
        writeControl adjustableRunTime;
        writeInterval 0.0002;
        patches ({walls});
    }}
}}
""",
        encoding="utf-8",
    )
    (case / "system" / "fvSchemes").write_text(
        foam_header("fvSchemes", "dictionary", "system")
        + """ddtSchemes { default Euler; }
gradSchemes
{
    default Gauss linear;
    limited cellLimited Gauss linear __GRADIENT_LIMITER__;
    grad(U) $limited;
    grad(k) $limited;
    grad(omega) $limited;
}
divSchemes
{
    default none;
    div(phi,U) __VELOCITY_ADVECTION__;
    energy bounded Gauss upwind;
    div(phi,h) $energy;
    div(phi,K) $energy;
    turbulence bounded Gauss upwind;
    div(phi,k) $turbulence;
    div(phi,omega) $turbulence;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default __LAPLACIAN_SCHEME__; }
interpolationSchemes { default linear; }
snGradSchemes { default __SN_GRAD_SCHEME__; }
wallDist { method meshWave; }
"""
        .replace("__GRADIENT_LIMITER__", str(gradient_limiter))
        .replace("__VELOCITY_ADVECTION__", velocity_advection)
        .replace("__LAPLACIAN_SCHEME__", laplacian_scheme)
        .replace("__SN_GRAD_SCHEME__", sn_grad_scheme),
        encoding="utf-8",
    )
    (case / "system" / "fvSolution").write_text(
        foam_header("fvSolution", "dictionary", "system")
        + """solvers
{
    p { solver GAMG; smoother DIC; tolerance 1e-8; relTol 0.01; }
    pFinal { $p; relTol 0; }
    \"(rho|U|k|omega|h)\"
    {
        solver PBiCGStab;
        preconditioner DILU;
        tolerance 1e-10;
        relTol 0.1;
    }
    \"(rho|U|k|omega|h)Final\" { $U; relTol 0; }
}
PIMPLE
{
    nOuterCorrectors __N_OUTER__;
    nCorrectors __N_CORRECTORS__;
    nNonOrthogonalCorrectors __N_NON_ORTHOGONAL__;
}
relaxationFactors
{
    fields { rho 1; }
    equations { U __RELAX_U__; h __RELAX_H__; k __RELAX_K__; omega __RELAX_OMEGA__; }
}
"""
        .replace("__N_OUTER__", str(n_outer))
        .replace("__N_CORRECTORS__", str(n_correctors))
        .replace("__N_NON_ORTHOGONAL__", str(n_non_orthogonal))
        .replace("__RELAX_U__", str(relaxation["U"]))
        .replace("__RELAX_H__", str(relaxation["h"]))
        .replace("__RELAX_K__", str(relaxation["k"]))
        .replace("__RELAX_OMEGA__", str(relaxation["omega"])),
        encoding="utf-8",
    )
    temperature_min, temperature_max = contract["openfoam"]["common_boundary_conditions"]["temperature_constraint_k"]
    (case / "system" / "fvConstraints").write_text(
        foam_header("fvConstraints", "dictionary", "system")
        + f"limitT\n{{\n    type limitTemperature;\n    cellZone all;\n    min {temperature_min};\n    max {temperature_max};\n}}\n",
        encoding="utf-8",
    )


def expected_meshes(report: dict) -> dict[tuple[str, str], dict]:
    return {
        (variant, level): record
        for variant, levels in report["gas_domains"].items()
        for level, record in levels.items()
    }


def build(project_root: Path, domain_root: Path, output: Path, contract_path: Path, correction_path: Path | None = None) -> dict:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    correction = None
    if correction_path is not None:
        correction = json.loads(correction_path.read_text(encoding="utf-8"))
        require(correction["base_contract"]["path"] == str(contract_path.relative_to(project_root)), "correction_base_path_mismatch")
        require(correction["base_contract"]["sha256"] == sha256(contract_path), "correction_base_hash_mismatch")
    for record in contract["authority"].values():
        if not isinstance(record, dict):
            continue
        authority_path = project_root / record["path"]
        require(authority_path.is_file(), f"authority_absente:{record['path']}")
        require(sha256(authority_path) == record["sha256"], f"authority_hash_mismatch:{record['path']}")
    report = json.loads((project_root / contract["authority"]["F48_public_mesh_report"]["path"]).read_text(encoding="utf-8"))
    expected = expected_meshes(report)
    require(not output.exists(), f"output_existe:{output}")
    output.mkdir(parents=True)
    manifest = {
        "schema_version": "porsche-917-f49-case-manifest/v1",
        "contract_sha256": sha256(contract_path),
        "numerical_correction_sha256": sha256(correction_path) if correction_path is not None else None,
        "cases": [],
        "aate_icengines": contract["aate_icengines"],
    }
    for variant in ("2V", "4V"):
        for level in contract["mesh_matrix"]["levels"]:
            source_name = f"917-f48-gas-{variant.lower()}-{level}.msh"
            source_mesh = domain_root / source_name
            require(source_mesh.is_file(), f"maillage_absent:{source_mesh}")
            require(sha256(source_mesh) == expected[(variant, level)]["msh_sha256"], f"maillage_hash_mismatch:{source_name}")
            for screen_name in contract["openfoam"]["screens"]:
                case_id = f"{variant.lower()}-{level}-{screen_name}"
                case = output / "cases" / case_id
                for directory in (case / "0", case / "constant", case / "system", case / "source"):
                    directory.mkdir(parents=True, exist_ok=True)
                target_mesh = case / "source" / source_name
                shutil.copyfile(source_mesh, target_mesh)
                prepare_fields(case, contract, screen_name, correction)
                prepare_dictionaries(case, contract, screen_name, variant, correction)
                metadata = {
                    "case_id": case_id,
                    "variant": variant,
                    "level": level,
                    "screen": screen_name,
                    "source_mesh": str(target_mesh.relative_to(case)),
                    "source_mesh_sha256": sha256(target_mesh),
                    "F48_native_tetrahedron_count": expected[(variant, level)]["tetrahedron_count"],
                    "F48_native_volume_scan_units_cubed": expected[(variant, level)]["volume_scan_units_cubed"],
                    "source_patch": contract["openfoam"]["screens"][screen_name]["source_patch"],
                    "sink_patch": contract["openfoam"]["screens"][screen_name]["sink_patch"],
                    "wall_patches": wall_patches(contract["openfoam"]["screens"][screen_name]),
                    "execution_status": "prepared_not_run",
                    "numerical_correction_sha256": sha256(correction_path) if correction_path is not None else None,
                }
                (case / "case.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                manifest["cases"].append(metadata)
    manifest_path = output / "case-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--domain-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=Path("twins/reference-917-engine/f49-cfd-cht-contract.json"))
    parser.add_argument("--correction", type=Path)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    contract_path = args.contract if args.contract.is_absolute() else project_root / args.contract
    correction_path = args.correction if args.correction is None or args.correction.is_absolute() else project_root / args.correction
    manifest = build(project_root, args.domain_root.resolve(), args.output.resolve(), contract_path, correction_path)
    print(json.dumps({"case_count": len(manifest["cases"]), "output": str(args.output.resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
