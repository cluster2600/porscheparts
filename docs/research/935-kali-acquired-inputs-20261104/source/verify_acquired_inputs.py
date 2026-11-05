#!/usr/bin/env python3
"""Check a private acquired-input bundle and stream original OBJ against exact arrays."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def compare_obj(lines, vertices, triangles):
    vi, fi = 0, 0
    for line in lines:
        fields = line.split()
        if not fields or fields[0].startswith("#"):
            continue
        if fields[0] == "v":
            if len(fields) < 4 or vi >= len(vertices):
                raise ValueError("Invalid original vertex record")
            values = tuple(map(float, fields[1:4]))
            if not all(values[k] == vertices[vi, k] for k in range(3)):
                raise ValueError("Original OBJ vertex differs from exact arrays")
            vi += 1
        elif fields[0] == "f":
            if len(fields) != 4 or fi >= len(triangles):
                raise ValueError("Nontriangular or unexpected original face")
            values = [int(field.split("/", 1)[0]) for field in fields[1:]]
            if any(value == 0 for value in values):
                raise ValueError("Zero OBJ vertex index")
            decoded = [value-1 if value > 0 else vi+value for value in values]
            if not all(decoded[k] == triangles[fi, k] for k in range(3)):
                raise ValueError("Original OBJ face differs from exact arrays")
            fi += 1
    if vi != len(vertices) or fi != len(triangles):
        raise ValueError("Original OBJ record coverage differs from arrays")
    return {"vertices_compared": vi, "triangles_compared": fi,
            "all_original_coordinates_exact": True, "all_original_face_indices_and_order_exact": True}


def controls():
    v = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
    f = np.array([[0, 1, 2]])
    prefix = ["v 0 0 0\n", "v 1 0 0\n", "v 0 1 0\n"]
    compare_obj(prefix+["f 1/8/4 2/9/4 3/10/4\n"], v, f)
    compare_obj(prefix+["f -3 -2 -1\n"], v, f)
    for lines, expected in [(prefix+["f 1 3 2\n"], "face differs"),
                            (["v .01 0 0\n"]+prefix[1:]+["f 1 2 3\n"], "vertex differs"),
                            (prefix+["f 1 2 3 1\n"], "Nontriangular")]:
        try:
            compare_obj(lines, v, f)
        except ValueError as error:
            if expected not in str(error): raise
        else:
            raise AssertionError("Malformed source control accepted")
    return {"positive_with_texture_normal_indices": True, "negative_indices": True,
            "changed_face_refused": True, "changed_coordinate_refused": True, "nontriangle_refused": True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--contract-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists(): raise ValueError("Existing acquired-input verification refused")
    contract_path = a.root/"input-contract.json"
    if sha(contract_path) != a.contract_sha256:
        raise ValueError("Registered input contract changed")
    contract = json.loads(contract_path.read_text())
    checks = []
    for entry in contract["files"]:
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Input escapes private bundle")
        path = a.root/relative
        if path.is_symlink() or path.stat().st_size != entry["bytes"] or sha(path) != entry["sha256"]:
            raise ValueError("Acquired bundle checksum failed: "+entry["path"])
        checks.append(entry["path"])
    if (contract["mm_per_original_unit"] != 1. or contract["physical_metrology_accepted"] or
            contract["manufacturing_authorized"]):
        raise ValueError("Owner units or physical release boundary changed")
    original = a.root/"original/935-xtreme-cylinder-head.obj"
    arrays = a.root/"arrays/exact-source-arrays.npz"
    if (sha(original) != "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486" or
            sha(arrays) != "dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a"):
        raise ValueError("Wrong original specimen bytes or exact decoded arrays")
    with np.load(arrays, allow_pickle=False) as s:
        vertices, triangles = s["vertices"], s["triangles"]
    with original.open(encoding="utf-8", errors="strict") as stream:
        result = compare_obj(stream, vertices, triangles)
    result.update(input_contract_sha256=a.contract_sha256, files_hash_verified=checks,
                  controls=controls(), python_version=sys.version.split()[0], numpy_version=np.__version__,
                  verifier_source_sha256=sha(__file__), mm_per_original_unit=1.,
                  physical_metrology_accepted=False, manufacturing_authorized=False,
                  complete_engineering_chain_prepared=False)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x") as stream:stream.write(json.dumps(result, indent=2)+"\n")
    print("All private acquired inputs match; original OBJ matches every exact-array vertex and triangle.")


if __name__ == "__main__":
    main()
