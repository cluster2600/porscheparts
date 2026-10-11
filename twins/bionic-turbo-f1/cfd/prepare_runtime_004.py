#!/usr/bin/env python3
"""Retry the same diagnostic with PCG pressure solution instead of GAMG."""
import json
from pathlib import Path
import sys

import prepare_runtime_003
from prepare_case import sha
from run_cartesian_pilot import verify


def prepare(parent, output):
    prepare_runtime_003.prepare(parent, output)
    path = output / "system/fvSolution"
    content = path.read_text()
    if content.count("solver GAMG; smoother DIC;") != 1:
        raise ValueError("Expected the original GAMG pressure solver")
    path.write_text(content.replace("solver GAMG; smoother DIC;", "solver PCG; preconditioner DIC;"))
    manifest = json.loads((output / "case-manifest.json").read_text())
    manifest["file_sha256"]["system/fvSolution"] = sha(path)
    manifest["pressure_solver_correction"] = {
        "source_sha256": sha(Path(__file__)),
        "change": "PCG/DIC instead of GAMG/DIC after a native GAMG scale floating-point exception; tolerances unchanged.",
        "mesh_changed": False,
    }
    (output / "case-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    proof = json.loads((output / "cartesian-proof.json").read_text())
    proof["case_manifest_sha256"] = sha(output / "case-manifest.json")
    proof["derivation"]["pressure_solver_source_sha256"] = sha(Path(__file__))
    (output / "cartesian-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    verify(output)


if __name__ == "__main__":
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps({"status": "fresh_runtime_004_prepared", "mesh_changed": False}))
