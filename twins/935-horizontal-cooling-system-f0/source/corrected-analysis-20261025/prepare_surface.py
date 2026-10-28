"""Write an indexed OFF surface from the independently audited corrected rotor."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


EXPECTED_NPZ = "9128da15ba5ac3ea55373c792006478deb5dd77713d52d38a9eac7c4b70d0c8e"
EXPECTED_STL = "ee8f91167f6147edd125b2b4db9da65a5704aac95879a82f2aab6bada779f9ed"


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_off(vertices, faces, path):
    if vertices.shape != (660003, 3) or faces.shape != (1320006, 3):
        raise ValueError("Corrected rotor counts differ from the audited indexed mesh")
    if not np.isfinite(vertices).all() or faces.min() < 0 or faces.max() >= len(vertices):
        raise ValueError("Invalid coordinate or triangle index")
    if np.any((faces[:, 0] == faces[:, 1]) | (faces[:, 1] == faces[:, 2]) | (faces[:, 2] == faces[:, 0])):
        raise ValueError("A triangle repeats a vertex")
    with path.open("x") as stream:
        stream.write(f"OFF\n{len(vertices)} {len(faces)} 0\n")
        np.savetxt(stream, vertices, fmt="%.17g")
        np.savetxt(stream, np.column_stack((np.full(len(faces), 3), faces)), fmt="%d")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("indexed_npz", type=Path)
    parser.add_argument("corrected_stl", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    if sha256(args.indexed_npz) != EXPECTED_NPZ or sha256(args.corrected_stl) != EXPECTED_STL:
        raise ValueError("Corrected rotor inputs do not match the independent audit")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    with np.load(args.indexed_npz, allow_pickle=False) as mesh:
        vertices, faces = mesh["vertices"], mesh["faces"]
    output = args.output_dir / "corrected-rotor.off"
    write_off(vertices, faces, output)
    with output.open() as stream:
        if stream.readline() != "OFF\n" or stream.readline() != "660003 1320006 0\n":
            raise ValueError("OFF header readback failed")
        checked_vertices = np.loadtxt(stream, max_rows=len(vertices))
        checked_faces = np.loadtxt(stream, dtype=np.int64)
    if not np.array_equal(checked_vertices, vertices) or not np.array_equal(checked_faces[:, 1:], faces) or not np.all(checked_faces[:, 0] == 3):
        raise ValueError("Complete OFF coordinate or triangle readback failed")
    receipt = {
        "schema": "935-corrected-analysis-source-v1",
        "source_sha256": sha256(Path(__file__)),
        "corrected_stl_sha256": EXPECTED_STL,
        "indexed_npz_sha256": EXPECTED_NPZ,
        "output_off_sha256": sha256(output),
        "vertices": len(vertices),
        "triangles": len(faces),
        "complete_off_readback": True,
        "source_unit": "uncalibrated_scan_unit",
        "CFD_accepted": False,
        "manufacturing_authorized": False,
    }
    (args.output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
