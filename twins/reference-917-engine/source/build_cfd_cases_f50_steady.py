#!/usr/bin/env python3
"""Construit une seconde formulation CFD F50 stationnaire depuis F48.

La géométrie, les patches et les conditions physiques finales restent ceux du
contrat F49. Seule la formulation numérique devient stationnaire compressible,
conformément au tutoriel officiel OpenFOAM 14
``fluid/aerofoilNACA0012Steady``. Aucun solide, CHT ou mouvement moteur n'est
inventé.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("f49_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module_introuvable:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def foam_header(object_name: str, location: str) -> str:
    return f"""FoamFile
{{
    format      ascii;
    class       dictionary;
    location    \"{location}\";
    object      {object_name};
}}

"""


def control_dict(source: str, sink: str, walls: list[str], variant: str, iterations: int) -> str:
    wall_list = " ".join(walls)
    return foam_header("controlDict", "system") + f"""solver fluid;
startFrom latestTime;
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
    velocityMagnitudeSquared
    {{
        type magSqr;
        libs (\"libfieldFunctionObjects.so\");
        field U;
        result UMagSqr;
        executeControl timeStep;
        executeInterval 1;
        writeControl timeStep;
        writeInterval 250;
    }}
    residuals
    {{
        type residuals;
        libs (\"libutilityFunctionObjects.so\");
        writeControl timeStep;
        writeInterval 250;
        fields (p U T k omega h);
    }}
    sourceMassFlow
    {{
        type surfaceFieldValue;
        libs (\"libfieldFunctionObjects.so\");
        writeControl timeStep;
        writeInterval 20;
        writeFields false;
        patch {source};
        operation sum;
        fields (phi);
    }}
    sinkMassFlow
    {{
        type surfaceFieldValue;
        libs (\"libfieldFunctionObjects.so\");
        writeControl timeStep;
        writeInterval 20;
        writeFields false;
        patch {sink};
        operation sum;
        fields (phi);
    }}
    sourcePressure
    {{
        type surfaceFieldValue;
        libs (\"libfieldFunctionObjects.so\");
        writeControl timeStep;
        writeInterval 20;
        writeFields false;
        patch {source};
        operation areaAverage;
        fields (p);
    }}
    sinkPressure
    {{
        type surfaceFieldValue;
        libs (\"libfieldFunctionObjects.so\");
        writeControl timeStep;
        writeInterval 20;
        writeFields false;
        patch {sink};
        operation areaAverage;
        fields (p);
    }}
    sinkTemperature
    {{
        type surfaceFieldValue;
        libs (\"libfieldFunctionObjects.so\");
        writeControl timeStep;
        writeInterval 20;
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
        writeControl timeStep;
        writeInterval 20;
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
        writeControl timeStep;
        writeInterval 20;
        writeFields false;
        patch {sink};
        operation average;
        weightField phi;
        fields (T UMagSqr);
    }}
    headHeatFlux
    {{
        type wallHeatFlux;
        libs (\"libfieldFunctionObjects.so\");
        writeControl timeStep;
        writeInterval 20;
        patches ({wall_list});
    }}
}}
"""


def fv_schemes() -> str:
    return foam_header("fvSchemes", "system") + """ddtSchemes { default steadyState; }
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
    div(phi,U) bounded Gauss upwind;
    energy bounded Gauss upwind;
    div(phi,h) $energy;
    div(phi,K) $energy;
    turbulence bounded Gauss upwind;
    div(phi,k) $turbulence;
    div(phi,omega) $turbulence;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear limited corrected 0.5; }
interpolationSchemes { default linear; }
snGradSchemes { default limited 0.5; }
wallDist { method meshWave; }
"""


def fv_solution() -> str:
    # Aucun residualControl: le runner juge le plateau et tous les bilans après
    # un nombre fixe d'itérations et ne permet pas un arrêt positif anticipé.
    return foam_header("fvSolution", "system") + """solvers
{
    p { solver GAMG; smoother DIC; tolerance 1e-9; relTol 0.02; }
    "(rho|U|k|omega|h)"
    {
        solver PBiCGStab;
        preconditioner DILU;
        tolerance 1e-10;
        relTol 0.1;
    }
}
PIMPLE
{
    nNonOrthogonalCorrectors 1;
}
relaxationFactors
{
    fields { p 0.05; rho 0.001; }
    equations { U 0.10; h 0.10; k 0.10; omega 0.08; }
}
"""


def build(project_root: Path, domain_root: Path, output: Path, iterations: int) -> dict:
    f49_builder_path = project_root / "twins/reference-917-engine/source/build_cfd_cases_f49.py"
    f49_contract_path = project_root / "twins/reference-917-engine/f49-cfd-cht-contract.json"
    correction_path = project_root / "twins/reference-917-engine/f49-cfd-cht-corrective-coarse.json"
    f50_contract_path = project_root / "twins/reference-917-engine/f50-steady-cfd-contract.json"
    f49 = load_module(f49_builder_path)
    manifest = f49.build(project_root, domain_root, output, f49_contract_path, correction_path)
    f49_contract = json.loads(f49_contract_path.read_text(encoding="utf-8"))
    for record in manifest["cases"]:
        case = output / "cases" / record["case_id"]
        screen = f49_contract["openfoam"]["screens"][record["screen"]]
        walls = record["wall_patches"]
        (case / "system" / "controlDict").write_text(
            control_dict(screen["source_patch"], screen["sink_patch"], walls, record["variant"], iterations),
            encoding="utf-8",
        )
        (case / "system" / "fvSchemes").write_text(fv_schemes(), encoding="utf-8")
        (case / "system" / "fvSolution").write_text(fv_solution(), encoding="utf-8")
        metadata_path = case / "case.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata.update(
            {
                "phase": "F50",
                "formulation": "steady compressible RANS kOmegaSST",
                "final_boundary_conditions_identical_to_F49": True,
                "outer_or_inner_geometry_modified": False,
                "ellipse_or_oval_proxy_used": False,
                "fixed_iterations": iterations,
                "F50_contract_sha256": sha256(f50_contract_path),
            }
        )
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest.update(
        {
            "schema_version": "porsche-917-f50-steady-case-manifest/v1",
            "F50_contract_sha256": sha256(f50_contract_path),
            "F49_contract_sha256": sha256(f49_contract_path),
            "formulation": "steady compressible RANS kOmegaSST",
            "outer_or_inner_geometry_modified": False,
            "ellipse_or_oval_proxy_used": False,
            "fixed_iterations": iterations,
        }
    )
    manifest_path = output / "case-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--domain-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=6000)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    output = args.output if args.output.is_absolute() else project_root / args.output
    domain_root = args.domain_root.resolve()
    if args.iterations < 100:
        raise RuntimeError("iterations_insuffisantes")
    manifest = build(project_root, domain_root, output, args.iterations)
    print(json.dumps({"cases": len(manifest["cases"]), "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
