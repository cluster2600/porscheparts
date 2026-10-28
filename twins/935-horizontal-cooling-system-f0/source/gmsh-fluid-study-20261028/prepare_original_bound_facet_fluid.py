"""Prepare fluid PLCs from three original-export-bounded facet repairs."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import trimesh


CANDIDATES = {
    "001": ("b7e07e8dc790dd411494f17480c2550ca370db6fc38342dd832db44c724e0086",
            "b86faa55f3ed911039dfe3894b4fab9948d0dc0d5a7b7e272860bb209c997aaf", 435520, 871060),
    "005": ("8360724ad4d6542329f156f813a41403070b57d8a92be3a7f830be44f13fe292",
            "eb7770d676e59ef22b8deee6b38cb575bece169c1be4873fca0531a2fd6db73a", 435499, 871018),
    "020": ("1cc284f5dbbd8ae574984c4e9a612605706b036831145e8f4528d7545783bd6e",
            "24c937d4c824edb9e4b29cdef3177d12f8bb262d1b2fd3a0771f9f107e27f238", 435451, 870922),
}
PARENT_SHA = "67835eacd4d1c7f9736b5fc826979f8ad48366397b422e672043ef720c027f86"
ORIGINAL_SHA = "e374fc2f850645efb6db4854a4355f541a9617833b827a6cff52d24929757587"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare(root, candidate_id, source_dir, output):
    candidate_sha, proof_sha, vertices_count, faces_count = CANDIDATES[candidate_id]
    candidate = source_dir / f"candidate-limit-{candidate_id}.off"
    proof = source_dir / f"envelope-limit-{candidate_id}.stdout"
    original = root / "work/935-analysis-volume-20261022/reference/original.off"
    parent = root / "work/935-cfd-mesh-correction-20261022/prepared-concavity20-001/boundary.npz"
    if output.exists() or not output.is_relative_to(root / "work"):
        raise ValueError("Use a fresh private output under repository work/")
    if (sha(candidate) != candidate_sha or sha(proof) != proof_sha
            or sha(original) != ORIGINAL_SHA or sha(parent) != PARENT_SHA):
        raise ValueError("Pinned geometry or certificate hash mismatch")
    certificate = json.loads(proof.read_text())
    if (certificate["source_faces"] != 1322970
            or certificate["candidate_faces"] != faces_count
            or certificate["envelope_bound_native_units"] != 0.0225
            or certificate["complete_containment_pass"] is not True
            or certificate["source_to_candidate_contained"] is not True
            or certificate["candidate_to_source_contained"] is not True):
        raise ValueError("Complete original-export envelope certificate required")

    source = root / "twins/935-horizontal-cooling-system-f0/source/reference-fluid-wall-study-20261022/compose-reference-wall-001.py"
    sys.path.insert(0, str(source.parent.parent))
    spec = importlib.util.spec_from_file_location("reference_fluid_wall", source)
    wall = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wall)
    rotor = trimesh.load_mesh(candidate, process=False)
    if (len(rotor.vertices) != vertices_count or len(rotor.faces) != faces_count
            or not rotor.is_watertight or not rotor.is_winding_consistent
            or rotor.volume <= 0):
        raise ValueError("Candidate topology mismatch")
    rv, rf = np.asarray(rotor.vertices) * 0.001, np.asarray(rotor.faces)
    with np.load(parent) as data:
        hole = data["hole"].copy()
        vertices, faces, markers, volume = wall.compose(
            data["vertices"], data["triangles"], data["markers"], rv, rf, hole)
    output.mkdir(mode=0o700)
    boundary = output / "boundary.npz"
    np.savez_compressed(boundary, vertices=vertices, triangles=faces,
                        markers=markers, hole=hole)
    with np.load(boundary) as readback:
        if not all(np.array_equal(readback[key], array) for key, array in (
                ("vertices", vertices), ("triangles", faces),
                ("markers", markers), ("hole", hole))):
            raise ValueError("Fluid PLC readback mismatch")
    receipt = dict(status="original_export_bounded_facet_fluid_trial_not_CFD_admitted",
                   candidate_id=candidate_id, rotor_sha256=candidate_sha,
                   envelope_certificate_sha256=proof_sha, parent_sha256=PARENT_SHA,
                   boundary_sha256=sha(boundary), vertices=len(vertices),
                   faces=len(faces), fluid_volume_m3_conditional=volume,
                   source_units_calibrated=False, CFD_accepted=False,
                   manufacturing_authorized=False)
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_id", choices=CANDIDATES)
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("new_output", type=Path)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    print(json.dumps(prepare(root, args.candidate_id, args.source_dir.resolve(),
                             args.new_output.resolve())))
