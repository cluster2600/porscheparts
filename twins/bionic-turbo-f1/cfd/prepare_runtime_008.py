#!/usr/bin/env python3
"""Test transonic pressure-density coupling without changing the operating point."""
import json
from pathlib import Path
import sys

import prepare_runtime_007
from prepare_case import sha
from run_cartesian_pilot import verify


def prepare(parent, output):
    prepare_runtime_007.prepare(parent, output)
    edits = {
        "system/fvSolution": [("consistent no;", "consistent no; transonic yes;"),
                              ("solver GAMG; smoother DIC;", "solver GAMG; smoother GaussSeidel; scaleCorrection false;")],
        "system/fvSchemes": [("divSchemes {default none;", "divSchemes {default none; div(phid,p) Gauss upwind;")],
    }
    manifest = json.loads((output / "case-manifest.json").read_text())
    for name, replacements in edits.items():
        path = output / name
        content = path.read_text()
        for old, new in replacements:
            if content.count(old) != 1:
                raise ValueError("Unexpected original pressure-density configuration")
            content = content.replace(old, new)
        path.write_text(content)
        manifest["file_sha256"][name] = sha(path)
    manifest["transonic_countertrial"] = {
        "source_sha256": sha(Path(__file__)),
        "change": "Enable implicit phid pressure convection, upwind pressure advection and asymmetric GAMG settings.",
        "source_url": "https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/applications/solvers/compressible/rhoSimpleFoam/pEqn.H",
        "reason": "Reject negative absolute pressures from the non-transonic runtime 007 history.",
        "operating_conditions_changed": False, "acceptance_tolerances_changed": False,
    }
    (output / "case-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    proof = json.loads((output / "cartesian-proof.json").read_text())
    proof["case_manifest_sha256"] = sha(output / "case-manifest.json")
    proof["derivation"]["transonic_source_sha256"] = sha(Path(__file__))
    (output / "cartesian-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    verify(output)


if __name__ == "__main__":
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps({"status": "fresh_runtime_008_prepared", "mesh_changed": False}))
