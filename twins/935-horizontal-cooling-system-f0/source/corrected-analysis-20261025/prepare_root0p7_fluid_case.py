"""Stage the protected 0.7-root 935 rotor in the existing CFD pilot case."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np


SURFACE_SHA = "5d900f6da900b4bffac2fdacfd6e0a346f8c0259a19299725621d4fd1e48c12a"
TEMPLATE_RECEIPT_SHA = "a408de352864493ac265a77ab4ee5427d8433558a82a2e21403abe4d90697e0d"
SYSTEM_SHA = "8fcd9c378dad7948b8315fd201d07e9d3430d24496be04f83f9207f5277788ec"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("surface_off", type=Path)
    parser.add_argument("template", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4]
    output = args.output.resolve()
    if not output.is_relative_to(root / "work") or output.exists():
        parser.error("Use a new private output directory under ignored work/")
    if sha(args.surface_off) != SURFACE_SHA or sha(args.template / "receipt.json") != TEMPLATE_RECEIPT_SHA:
        raise ValueError("Pinned surface or template changed")
    system_files = sorted((args.template / "system").iterdir())
    digest = hashlib.sha256()
    for file in system_files:
        if not file.is_file() or file.is_symlink():
            raise ValueError("Only regular template dictionaries are accepted")
        digest.update(file.name.encode() + b"\0" + bytes.fromhex(sha(file)))
    if digest.hexdigest() != SYSTEM_SHA:
        raise ValueError("Pinned OpenFOAM dictionaries changed")

    with args.surface_off.open() as stream:
        if stream.readline().strip() != "OFF":
            raise ValueError("OFF surface required")
        vertex_count, face_count, _ = map(int, stream.readline().split())
        if (vertex_count, face_count) != (439365, 878730):
            raise ValueError("Unexpected protected rotor topology")
        if stream.readline().strip():
            raise ValueError("Unexpected OFF header separator")
        vertices = np.loadtxt(stream, max_rows=vertex_count)
        faces = np.loadtxt(stream, max_rows=face_count, usecols=(1, 2, 3), dtype=np.int64)
        if stream.read().strip() or vertices.shape != (vertex_count, 3) or faces.shape != (face_count, 3):
            raise ValueError("Unexpected OFF payload")
    if not np.isfinite(vertices).all() or faces.min() < 0 or faces.max() >= vertex_count:
        raise ValueError("Invalid surface coordinates or indices")

    output.mkdir(parents=True)
    shutil.copytree(args.template / "system", output / "system")
    target = output / "constant/triSurface/rotor.obj"
    target.parent.mkdir(parents=True)
    scaled = vertices * 0.001  # Assumed conversion; the scan unit remains uncalibrated.
    with target.open("x") as stream:
        np.savetxt(stream, scaled, fmt="v %.17g %.17g %.17g")
        stream.write("g rotor\n")
        np.savetxt(stream, faces + 1, fmt="f %d %d %d")
    with target.open() as stream:
        for expected in scaled:
            row = stream.readline().split()
            if row[0] != "v" or not np.array_equal(np.asarray(row[1:], dtype=float), expected):
                raise ValueError("OBJ coordinate readback differs")
        if stream.readline() != "g rotor\n":
            raise ValueError("Rotor group missing")
        for expected in faces:
            row = stream.readline().split()
            if row[0] != "f" or not np.array_equal(np.asarray(row[1:], dtype=int) - 1, expected):
                raise ValueError("OBJ face readback differs")
        if stream.read():
            raise ValueError("Unexpected OBJ suffix")
    receipt = {
        "schema": "935-root-0p7-fluid-input-v1",
        "source_sha256": sha(__file__),
        "surface_off_sha256": SURFACE_SHA,
        "template_receipt_sha256": TEMPLATE_RECEIPT_SHA,
        "system_digest_sha256": SYSTEM_SHA,
        "rotor_obj_sha256": sha(target),
        "rotor_vertices": vertex_count,
        "rotor_faces": face_count,
        "assumed_m_per_uncalibrated_source_unit": 0.001,
        "scale_verified": False,
        "historical_shroud_defined": False,
        "native_mesh_executed": False,
        "CFD_accepted": False,
        "manufacturing_authorized": False,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
