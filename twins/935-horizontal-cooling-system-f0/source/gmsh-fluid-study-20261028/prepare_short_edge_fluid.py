"""Build a private conditional PLC from one independently bounded rotor repair."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import trimesh


CASES = {
    "0.001": ("858b2cc7c5b6492b418a3293d5b30007b694da3182b8ec96905bbd97fbe83031", "ce4d6e59ad5cb5f47d7c49fd563a8dfa3203451f502d923efff39a04d5e8cc9e", 439358, 878716),
    "0.005": ("4cfffdfb8c4a98e603000fb1f3334a46f17a7a7fe772222ab37d6598f858f520", "b04b4670208a3004ce008357ecd1c163e391c321ad36fde9b3ad7500c40de474", 439349, 878698),
    "0.020": ("676a9f044a24ddbaeca0ed80431c803f62a1c0d5781fd96eee2563f4dab2e5a7", "8169ddfcddc4fc18a73529134fe4c6b36788c476868997b53af9ffcb0e6302c3", 439323, 878646),
}
PARENT_SHA = "67835eacd4d1c7f9736b5fc826979f8ad48366397b422e672043ef720c027f86"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_off", type=Path)
    parser.add_argument("envelope_stdout", type=Path)
    parser.add_argument("new_output", type=Path)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    candidate = args.candidate_off.resolve()
    envelope_file = args.envelope_stdout.resolve()
    out = args.new_output.resolve()
    if out.exists() or not out.is_relative_to(root / "work"):
        raise SystemExit("Use a fresh private output under repository work/")
    candidate_hash_actual = sha(candidate)
    matching = [
        (limit, expected)
        for limit, expected in CASES.items()
        if candidate_hash_actual == expected[0]
    ]
    if len(matching) != 1:
        raise SystemExit("Candidate hash is not an audited short-edge trial")
    limit, (candidate_hash, envelope_hash, vertex_count, face_count) = matching[0]
    if sha(envelope_file) != envelope_hash:
        raise SystemExit("Envelope receipt hash mismatch")
    proof = json.loads(envelope_file.read_text())
    if not (proof["complete_containment_pass"] and proof["topology_and_self_intersection_checks_pass"]
            and proof["source_faces"] == 878730 and proof["candidate_faces"] == face_count
            and proof["envelope_bound_native_units"] == 0.0225):
        raise SystemExit("Envelope gate did not pass")
    parent = root / "work/935-cfd-mesh-correction-20261022/prepared-concavity20-001/boundary.npz"
    if sha(parent) != PARENT_SHA:
        raise SystemExit("Exploratory outer-duct input changed")

    source = root / "twins/935-horizontal-cooling-system-f0/source/reference-fluid-wall-study-20261022/compose-reference-wall-001.py"
    sys.path.insert(0, str(source.parent.parent))
    spec = importlib.util.spec_from_file_location("reference_fluid_wall", source)
    wall = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wall)
    rotor = trimesh.load_mesh(candidate, process=False)
    rv, rf = np.asarray(rotor.vertices) * 0.001, np.asarray(rotor.faces)
    if not (len(rv) == vertex_count and len(rf) == face_count
            and rotor.is_watertight and rotor.is_winding_consistent and rotor.volume > 0):
        raise SystemExit("Candidate geometry/topology mismatch")
    with np.load(parent) as data:
        hole = data["hole"].copy()
        vertices, faces, markers, volume = wall.compose(
            data["vertices"], data["triangles"], data["markers"], rv, rf, hole
        )
    out.mkdir(mode=0o700)
    with (out / "rotor.obj").open("x") as stream:
        np.savetxt(stream, rv, fmt="v %.17g %.17g %.17g")
        np.savetxt(stream, rf + 1, fmt="f %d %d %d")
    readback = trimesh.load_mesh(out / "rotor.obj", process=False)
    if not (np.array_equal(readback.vertices, rv) and np.array_equal(readback.faces, rf)):
        raise SystemExit("Rotor OBJ readback mismatch")
    np.savez_compressed(out / "boundary.npz", vertices=vertices, triangles=faces,
                        markers=markers, hole=hole)
    with (out / "fluid.smesh").open("x") as stream:
        stream.write(f"{len(vertices)} 3 0 0\n")
        np.savetxt(stream, np.column_stack([np.arange(len(vertices)), vertices]),
                   fmt=["%d", "%.17g", "%.17g", "%.17g"])
        stream.write(f"{len(faces)} 1\n")
        np.savetxt(stream, np.column_stack([np.full(len(faces), 3), faces, markers]), fmt="%d")
        stream.write("1\n0 " + " ".join(f"{x:.17g}" for x in hole) + "\n0\n")
    receipt = {
        "status": "conditional_short_edge_fluid_PLC_pending_volume_quality",
        "limit_source_units": float(limit),
        "source_sha256": sha(Path(__file__)),
        "candidate_off_sha256": candidate_hash,
        "envelope_result_sha256": envelope_hash,
        "parent_boundary_sha256": PARENT_SHA,
        "vertices": len(vertices), "triangles": len(faces), "volume_m3": volume,
        "scale_verified": False, "CFD_accepted": False,
        "output_sha256": {name: sha(out / name) for name in ("rotor.obj", "boundary.npz", "fluid.smesh")},
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
