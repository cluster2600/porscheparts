"""Build a private fluid PLC from the original-PicoGK-export-bounded rotor."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import trimesh


ROTOR_SHA = "d2e86b89afe854ea4107cac170fdba7d5e73a40648c3a704dfd9ab6b5b1687e2"
PARENT_SHA = "67835eacd4d1c7f9736b5fc826979f8ad48366397b422e672043ef720c027f86"
PROOF_SHA = "1fbf62bf1e8c5cbeb5d84dda583c7e674ce0a2db86b8196e3ad6177df5cf9728"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rotor_off", type=Path)
    parser.add_argument("new_output", type=Path)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    rotor_path = args.rotor_off.resolve()
    output = args.new_output.resolve()
    if output.exists() or not output.is_relative_to(root / "work"):
        raise SystemExit("Use a fresh private output under repository work/")
    if sha(rotor_path) != ROTOR_SHA:
        raise SystemExit("Original-bounded rotor hash mismatch")
    proof_path = root / "docs/research/935-horizontal-cooling/analysis-mesh-20261022.json"
    if sha(proof_path) != PROOF_SHA:
        raise SystemExit("Original-PicoGK-export proof hash mismatch")
    proof = json.loads(proof_path.read_text())
    certificate = proof["surface"]["certificate"]
    if not (proof["surface"]["candidate"]["sha256"]["candidate-quantized.off"] == ROTOR_SHA
            and certificate["complete_containment_pass"]
            and certificate["source_faces"] == 1322970
            and certificate["candidate_faces"] == 871078
            and certificate["envelope_bound_native_units"] == 0.0225):
        raise SystemExit("Original-PicoGK-export certificate mismatch")
    parent = root / "work/935-cfd-mesh-correction-20261022/prepared-concavity20-001/boundary.npz"
    if sha(parent) != PARENT_SHA:
        raise SystemExit("Exploratory outer-duct hash mismatch")

    source = root / "twins/935-horizontal-cooling-system-f0/source/reference-fluid-wall-study-20261022/compose-reference-wall-001.py"
    sys.path.insert(0, str(source.parent.parent))
    spec = importlib.util.spec_from_file_location("reference_fluid_wall", source)
    wall = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wall)
    rotor = trimesh.load_mesh(rotor_path, process=False)
    rv, rf = np.asarray(rotor.vertices) * 0.001, np.asarray(rotor.faces)
    if not (len(rv) == 435529 and len(rf) == 871078
            and rotor.is_watertight and rotor.is_winding_consistent and rotor.volume > 0):
        raise SystemExit("Original-bounded rotor topology mismatch")
    with np.load(parent) as data:
        hole = data["hole"].copy()
        vertices, faces, markers, volume = wall.compose(
            data["vertices"], data["triangles"], data["markers"], rv, rf, hole
        )
    output.mkdir(mode=0o700)
    np.savez_compressed(output / "boundary.npz", vertices=vertices,
                        triangles=faces, markers=markers, hole=hole)
    with (output / "rotor.obj").open("x") as stream:
        np.savetxt(stream, rv, fmt="v %.17g %.17g %.17g")
        np.savetxt(stream, rf + 1, fmt="f %d %d %d")
    readback = trimesh.load_mesh(output / "rotor.obj", process=False)
    if not (np.array_equal(readback.vertices, rv)
            and np.array_equal(readback.faces, rf)):
        raise SystemExit("Rotor OBJ readback mismatch")
    receipt = {
        "status": "original_PicoGK_export_bounded_fluid_PLC_pending_volume_quality",
        "rotor_off_sha256": ROTOR_SHA,
        "proof_sha256": sha(proof_path),
        "parent_boundary_sha256": PARENT_SHA,
        "vertices": len(vertices), "triangles": len(faces),
        "fluid_volume_m3_conditional": volume,
        "scale_verified": False, "CFD_accepted": False,
        "output_sha256": {name: sha(output / name) for name in ("boundary.npz", "rotor.obj")},
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
