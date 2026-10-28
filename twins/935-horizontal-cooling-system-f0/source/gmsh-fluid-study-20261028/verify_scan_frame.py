"""Verify full raw-to-axis vertex transport without claiming a physical datum."""

import hashlib
import json
from pathlib import Path
import sys

import numpy as np


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


if len(sys.argv) != 5:
    raise SystemExit("Usage: verify_scan_frame.py ORIGINAL_OBJ ALIGNED_NPZ AXIS_JSON NEW_PRIVATE_JSON")
original, aligned, axis, output = (Path(value).resolve() for value in sys.argv[1:])
if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
    raise SystemExit("Use a fresh private output under work/")
expected = {
    original: "244d4caeb2c4ac4a692b650ec9d766bee2a8124335a0236a55a1d30c1b2b98ba",
    aligned: "452f76162d6148017299edd1563e4e06b933dd9fe105bee30c185f96d98cc247",
    axis: "30a1564b47246c2bdb29bcca6b0d8678f73983982e30e9fbafcae0937788f9d2",
}
if any(sha(path) != digest for path, digest in expected.items()):
    raise SystemExit("Input hash mismatch")
vertices = []
with original.open(encoding="utf-8") as stream:
    for line in stream:
        if line.startswith("v "):
            fields = line.split()
            if len(fields) != 4:
                raise SystemExit("Unexpected OBJ vertex format")
            vertices.append([float(value) for value in fields[1:]])
raw = np.asarray(vertices, dtype=np.float64)
with np.load(aligned) as data:
    target = data["vertices"].copy()
    faces = data["faces"]
frame = json.loads(axis.read_text())
forward = np.asarray(frame["transform_source_to_candidate_axis"], dtype=np.float64)
inverse = np.asarray(frame["transform_candidate_axis_to_source"], dtype=np.float64)
if raw.shape != (624492, 3) or target.shape != raw.shape or faces.shape != (1240439, 3):
    raise SystemExit("Unexpected geometry dimensions")
if not np.isfinite(raw).all() or not np.isfinite(target).all() or forward.shape != (4, 4) or inverse.shape != (4, 4):
    raise SystemExit("Invalid geometry or transform")
if not np.allclose(forward @ inverse, np.eye(4), rtol=0, atol=1e-10):
    raise SystemExit("Transforms are not mutual inverses")
rotation = forward[:3, :3]
if not np.allclose(rotation.T @ rotation, np.eye(3), rtol=0, atol=1e-10) or not np.isclose(np.linalg.det(rotation), 1.0, rtol=0, atol=1e-10):
    raise SystemExit("Transform is not a proper rigid rotation")
errors = np.linalg.norm(raw @ rotation.T + forward[:3, 3] - target, axis=1)
maximum = float(errors.max())
if maximum > 1e-10:
    raise SystemExit("Raw-to-axis vertex transport failed")
report = {
    "status": "all_vertex_transport_verified_not_physical_datum_or_calibration",
    "original_obj_sha256": expected[original], "aligned_npz_sha256": expected[aligned],
    "axis_json_sha256": expected[axis], "vertices_checked": len(raw),
    "max_transport_error_source_units": maximum,
    "rms_transport_error_source_units": float(np.sqrt(np.mean(errors ** 2))),
    "functional_datum_verified": False, "scale_verified": False,
    "scan_acquisitions_physically_registered": False,
}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
