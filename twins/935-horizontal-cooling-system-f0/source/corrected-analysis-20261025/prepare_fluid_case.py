"""Stage the corrected rotor in the existing Foundation 13 pilot case."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_foundation13_rotor import write_si_obj


SOURCE_SHA = "5cdd1b993029a80921f995636a3a980027a66af7c87fc33ba935f7bf3a6458cf"
CANDIDATE_SHA = "c8aef379ac3a66188518ecc247fb1970ffe80fa33cea1b49b0b87db098959ac9"
QUALITY_SHA = "bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d"


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_off", type=Path)
    parser.add_argument("candidate_off", type=Path)
    parser.add_argument("bound_receipt", type=Path)
    parser.add_argument("template", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    bound = json.loads(args.bound_receipt.read_text())
    template = json.loads((args.template / "receipt.json").read_text())
    if (sha256(args.source_off) != SOURCE_SHA or sha256(args.candidate_off) != CANDIDATE_SHA
            or bound["source_off_sha256"] != SOURCE_SHA
            or bound["candidate_off_sha256"] != CANDIDATE_SHA
            or not bound["complete_containment_pass"]):
        raise ValueError("Corrected candidate lacks its complete bidirectional bound")
    if sha256(args.template / "system/meshQualityDict") != QUALITY_SHA:
        raise ValueError("The qualified mesh quality settings changed")
    if any(sha256(args.template / name) != expected for name, expected in template["files_sha256"].items()):
        raise ValueError("The retained case template changed")
    mesh = trimesh.load_mesh(args.candidate_off, process=False)
    if len(mesh.vertices) != 438652 or len(mesh.faces) != 877304 or not mesh.is_watertight:
        raise ValueError("Unexpected simplified rotor topology or counts")
    args.output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(args.template / "system", args.output / "system")
    (args.output / "constant/triSurface").mkdir(parents=True)
    obj = args.output / "constant/triSurface/rotor.obj"
    write_si_obj(obj, mesh.vertices, mesh.faces)
    receipt = {
        "schema": "935-corrected-rotor-fluid-case-v1",
        "source_sha256": sha256(__file__),
        "source_off_sha256": SOURCE_SHA,
        "candidate_off_sha256": CANDIDATE_SHA,
        "bound_receipt_sha256": sha256(args.bound_receipt),
        "template_receipt_sha256": sha256(args.template / "receipt.json"),
        "rotor_obj_sha256": sha256(obj),
        "mesh_quality_sha256": QUALITY_SHA,
        "rotor_vertices": len(mesh.vertices),
        "rotor_faces": len(mesh.faces),
        "assumed_m_per_uncalibrated_source_unit": 0.001,
        "scale_verified": False,
        "native_mesh_executed": False,
        "CFD_accepted": False,
        "manufacturing_authorized": False,
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
