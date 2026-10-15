#!/usr/bin/env python3
"""Damp the steady iteration after rejecting negative-temperature startup histories."""
import json
from pathlib import Path
import sys

import prepare_runtime_006
from prepare_case import sha
from run_cartesian_pilot import verify


def prepare(parent, output):
    prepare_runtime_006.prepare(parent, output)
    path = output / "system/fvSolution"
    content = path.read_text()
    old = 'fields {p .2; rho .1;} equations {U .5; h .5; "(k|omega)" .5;}'
    new = 'fields {p .1; rho .1;} equations {U .2; h .02; "(k|omega)" .2;}'
    if content.count(old) != 1:
        raise ValueError("Expected the original relaxation factors")
    path.write_text(content.replace(old, new))
    manifest = json.loads((output / "case-manifest.json").read_text())
    manifest["file_sha256"]["system/fvSolution"] = sha(path)
    manifest["steady_relaxation_countertrial"] = {
        "source_sha256": sha(Path(__file__)),
        "change": "Pressure 0.1, velocity 0.2, enthalpy 0.02, turbulence 0.2; density remains 0.1.",
        "reason": "Reject runtime 006 negative temperatures; damp the steady iteration without temperature clipping.",
        "operating_conditions_changed": False, "acceptance_tolerances_changed": False,
    }
    (output / "case-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    proof = json.loads((output / "cartesian-proof.json").read_text())
    proof["case_manifest_sha256"] = sha(output / "case-manifest.json")
    proof["derivation"]["steady_relaxation_source_sha256"] = sha(Path(__file__))
    (output / "cartesian-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    verify(output)


if __name__ == "__main__":
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps({"status": "fresh_runtime_007_prepared", "mesh_changed": False}))
