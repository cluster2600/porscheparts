#!/usr/bin/env python3
"""Sample yPlus at saved iterations, keeping the equation settings of runtime 005."""
import json
from pathlib import Path
import sys

import prepare_runtime_005
from prepare_case import sha
from run_cartesian_pilot import verify


def prepare(parent, output):
    prepare_runtime_005.prepare(parent, output)
    path = output / "system/controlDict"
    content = path.read_text()
    old = 'yPlus {type yPlus; libs ("libfieldFunctionObjects.so"); writeControl writeTime;}'
    if content.count(old) != 1:
        raise ValueError("Expected the original write-time yPlus observer")
    path.write_text(content.replace(old, old.replace("writeControl", "executeControl writeTime; writeControl")))
    manifest = json.loads((output / "case-manifest.json").read_text())
    manifest["file_sha256"]["system/controlDict"] = sha(path)
    manifest["observer_schedule_correction"] = {
        "source_sha256": sha(Path(__file__)),
        "change": "Execute yPlus on saved iterations, matching its writeControl, instead of before each iteration.",
        "reason": "Native yPlus auxiliary observer hit a floating-point exception after the first SIMPLE step; turbulence bounding remains logged and is not validation.",
        "equations_changed": False, "wall_resolution_qualified": False,
    }
    (output / "case-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    proof = json.loads((output / "cartesian-proof.json").read_text())
    proof["case_manifest_sha256"] = sha(output / "case-manifest.json")
    proof["derivation"]["observer_schedule_source_sha256"] = sha(Path(__file__))
    (output / "cartesian-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    verify(output)


if __name__ == "__main__":
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps({"status": "fresh_runtime_006_prepared", "mesh_changed": False}))
