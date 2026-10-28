"""Prepare a private PicoGK assembly case with the original-export-bounded rotor."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh


ROTOR_SHA = "d2e86b89afe854ea4107cac170fdba7d5e73a40648c3a704dfd9ab6b5b1687e2"
CERTIFICATE_SHA = "1fbf62bf1e8c5cbeb5d84dda583c7e674ce0a2db86b8196e3ad6177df5cf9728"
PARENT_RECEIPT_SHA = "104c0155a246d6acb04ca83e66988ccc3dcc345821db69349ab465bd0ec47b23"
PARTS = ("engine_context", "drive_observed", "rotor_candidate", "provisional_shroud")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare(rotor_path, parent_dir, output):
    root = Path.cwd().resolve()
    rotor_path, parent_dir, output = map(lambda p: Path(p).resolve(),
                                         (rotor_path, parent_dir, output))
    if output.exists() or not output.is_relative_to(root / "work"):
        raise ValueError("Use a fresh private output under repository work/")
    if sha(rotor_path) != ROTOR_SHA:
        raise ValueError("Certified rotor OFF hash mismatch")
    proof_path = root / "docs/research/935-horizontal-cooling/analysis-mesh-20261022.json"
    if sha(proof_path) != CERTIFICATE_SHA:
        raise ValueError("Original PicoGK export certificate hash mismatch")
    proof = json.loads(proof_path.read_text())["surface"]
    if (proof["candidate"]["sha256"]["candidate-quantized.off"] != ROTOR_SHA
            or proof["certificate"]["complete_containment_pass"] is not True
            or proof["certificate"]["source_faces"] != 1322970):
        raise ValueError("Original PicoGK export certificate mismatch")
    parent_receipt = parent_dir / "receipt.json"
    if sha(parent_receipt) != PARENT_RECEIPT_SHA:
        raise ValueError("Parent assembly receipt hash mismatch")
    parent = json.loads(parent_receipt.read_text())
    parent_case_path = parent_dir / "case.json"
    if sha(parent_case_path) != parent["case_sha256"]:
        raise ValueError("Parent assembly case hash mismatch")
    parent_case = json.loads(parent_case_path.read_text())
    if (parent["target"] != "935" or parent["engine_cylinders"] != 6
            or parent["scale_verified"] is not False
            or parent["manufacturing_authorized"] is not False
            or {r["id"] for r in parent["components"]} != set(PARTS)):
        raise ValueError("Uncalibrated six-cylinder 935 parent required")
    by_id = {row["id"]: row for row in parent["components"]}
    for name in PARTS:
        row = by_id[name]
        if sha(parent_dir / row["file"]) != row["sha256"]:
            raise ValueError("Parent component changed: " + name)

    rotor = trimesh.load_mesh(rotor_path, process=False)
    if (len(rotor.vertices) != 435529 or len(rotor.faces) != 871078
            or not rotor.is_watertight or not rotor.is_winding_consistent
            or rotor.volume <= 0):
        raise ValueError("Certified rotor topology mismatch")
    output.mkdir(mode=0o700)
    rotor_stl = output / "rotor_candidate.stl"
    rotor.export(rotor_stl, file_type="stl")
    readback = trimesh.load_mesh(rotor_stl, process=False)
    expected = np.asarray(rotor.vertices, dtype="<f4")[rotor.faces]
    if (len(readback.faces) != len(rotor.faces)
            or not np.array_equal(readback.triangles, expected)):
        raise ValueError("Rotor STL triangle readback mismatch")
    rotor_hash = sha(rotor_stl)
    flags = dict(scale_verified=False, interfaces_verified=False,
                 mechanism_dynamics_validated=False,
                 historical_installation_verified=False,
                 manufacturing_authorized=False, physical_validation=False)
    rotor_receipt = dict(
        status="original_PicoGK_export_bounded_rotor_for_inspection_only",
        target="935", engine_cylinders=6,
        source_off_sha256=ROTOR_SHA, certificate_sha256=CERTIFICATE_SHA,
        components=[dict(id="rotor_candidate", file=rotor_stl.name,
                         classification="original_export_bounded_analysis_rotor",
                         triangles=len(rotor.faces), sha256=rotor_hash)],
        **flags,
    )
    receipt_path = output / "rotor-receipt.json"
    receipt_path.write_text(json.dumps(rotor_receipt, indent=2) + "\n")
    parts = []
    for name in PARTS:
        if name == "rotor_candidate":
            parts.append(dict(id=name, path=str(rotor_stl), sha256=rotor_hash,
                              receipt_path=str(receipt_path),
                              receipt_sha256=sha(receipt_path)))
        else:
            row = by_id[name]
            parts.append(dict(id=name, path=str(parent_dir / row["file"]),
                              sha256=row["sha256"], receipt_path=str(parent_receipt),
                              receipt_sha256=PARENT_RECEIPT_SHA))
    case = dict(
        classification="935_original_export_bounded_inspection_assembly",
        target="935", engine_cylinders=6, engine_actual_variant=None,
        assumptions=["One assumed millimetre per uncalibrated source unit.",
                     "Original PicoGK export envelope is not a raw-scan or engine-fit certificate.",
                     "Drive and six-cylinder engine context retain hypothetical poses and interfaces."],
        scale_verified=False, shroud={"origin_mm": [0, 0, 0]},
        imports=parent_case["imports"],
        composition={"parts": parts, "rotor_replaced": True,
                     "placements_changed": False, "revoxelization": False},
    )
    case_path = output / "case.json"
    case_path.write_text(json.dumps(case, indent=2) + "\n")
    result = dict(status="PicoGK_assembly_input_prepared_not_fitment",
                  case_sha256=sha(case_path), rotor_stl_sha256=rotor_hash,
                  parent_receipt_sha256=PARENT_RECEIPT_SHA,
                  rotor_triangles=len(rotor.faces), **flags)
    (output / "preparation-receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rotor_off", type=Path)
    parser.add_argument("parent_assembly", type=Path)
    parser.add_argument("new_output", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.rotor_off, args.parent_assembly, args.new_output)))
