#!/usr/bin/env python3
"""Prepare a fresh Hf-corrected case using the actual thermo:psi registry name."""
import json
from pathlib import Path
import sys

import prepare_runtime_retry
from prepare_case import sha
from run_cartesian_pilot import verify


def prepare(parent, output):
    prepare_runtime_retry.prepare(parent, output)
    manifest = json.loads((output / "case-manifest.json").read_text())
    for name in ("0/p", "0/T"):
        path = output / name
        content = path.read_text()
        if content.count("psi psi;") != 1:
            raise ValueError("Expected one unqualified compressibility registry reference")
        path.write_text(content.replace("psi psi;", "psi thermo:psi;"))
        manifest["file_sha256"][name] = sha(path)
    manifest["boundary_registry_correction"] = {
        "source_sha256": sha(Path(__file__)),
        "change": "Use the hePsiThermo registered thermo:psi field in totalPressure and totalTemperature.",
        "mesh_changed": False,
    }
    (output / "case-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    proof = json.loads((output / "cartesian-proof.json").read_text())
    proof["case_manifest_sha256"] = sha(output / "case-manifest.json")
    proof["derivation"]["boundary_registry_source_sha256"] = sha(Path(__file__))
    (output / "cartesian-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    verify(output)


if __name__ == "__main__":
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps({"status": "fresh_runtime_003_prepared", "mesh_changed": False}))
