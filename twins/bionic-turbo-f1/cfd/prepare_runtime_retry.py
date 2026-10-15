#!/usr/bin/env python3
"""Clone verified diagnostic inputs and fix the OpenCFD Hf keyword, preserving failures."""
import json
from pathlib import Path
import shutil
import sys

from prepare_case import sha
from run_cartesian_pilot import verify


def prepare(parent, output):
    hashes = verify(parent)
    manifest = json.loads((parent / "case-manifest.json").read_text())
    proof = json.loads((parent / "cartesian-proof.json").read_text())
    name = "constant/thermophysicalProperties"
    content = (parent / name).read_text()
    if content.count("hf 0;") != 1 or "Hf " in content:
        raise ValueError("Expected the original lowercase zero heat-of-formation entry")
    output.mkdir(parents=True, exist_ok=False)
    for name in manifest["file_sha256"] | proof["mesh"]["mesh_sha256"]:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(parent / name, target)
        if sha(target) != hashes[name]:
            raise ValueError("Copy changed: " + name)
    provenance = output / "provenance"
    provenance.mkdir()
    for name in ("case-manifest.json", "cartesian-proof.json"):
        shutil.copyfile(parent / name, provenance / name)
    name = "constant/thermophysicalProperties"
    (output / name).write_text(content.replace("hf 0;", "Hf 0;"))
    manifest["file_sha256"][name] = sha(output / name)
    manifest["runtime_correction"] = {
        "source_sha256": sha(Path(__file__)), "parent_case": parent.name,
        "parent_manifest_sha256": hashes["case-manifest.json"],
        "change": "Rename hf 0 to the OpenCFD hConst Hf 0 keyword; values unchanged.",
        "mesh_changed": False,
    }
    (output / "case-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    proof["case_manifest_sha256"] = sha(output / "case-manifest.json")
    proof["derivation"] = {
        "source_sha256": sha(Path(__file__)),
        "parent_proof_sha256": hashes["cartesian-proof.json"],
        "method": "Exact mesh copy, verified by every parent mesh hash. Geometry proof inherited unchanged; only Hf keyword corrected.",
    }
    if any(sha(parent / name) != digest for name, digest in hashes.items()):
        raise ValueError("Parent changed during copying")
    (output / "cartesian-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    verify(output)


if __name__ == "__main__":
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps({"status": "fresh_runtime_case_prepared", "mesh_changed": False}))
