"""Check every imported ASCII OpenFOAM point against pinned MSH 2.2 nodes."""

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


if len(sys.argv) != 4:
    raise SystemExit("Usage: audit_openfoam_points.py PINNED_MSH22 OPENFOAM_POINTS NEW_JSON")
msh, points, output = (Path(value).resolve() for value in sys.argv[1:])
if output.exists() or sha(msh) != "9414355339ee15ae8a65a608b6545f0720af3017bc2a203dfab0a70d3af6302a":
    raise SystemExit("Input hash or output guard failed")
with msh.open(encoding="ascii") as stream:
    for line in stream:
        if line.strip() == "$Nodes":
            break
    else:
        raise SystemExit("Missing MSH node section")
    count = int(next(stream))
    if count != 1009234:
        raise SystemExit("Unexpected MSH node count")
    original = np.empty((count, 3), dtype=np.float64)
    for index in range(count):
        fields = next(stream).split()
        if len(fields) != 4 or int(fields[0]) != index + 1:
            raise SystemExit("MSH node labels are not sequential")
        original[index] = [float(value) for value in fields[1:]]
    if next(stream).strip() != "$EndNodes":
        raise SystemExit("Malformed MSH node section")
with points.open(encoding="ascii") as stream:
    for line in stream:
        if line.strip() == str(count):
            break
    else:
        raise SystemExit("Missing OpenFOAM point count")
    if next(stream).strip() != "(":
        raise SystemExit("Malformed OpenFOAM point list")
    imported = np.empty((count, 3), dtype=np.float64)
    for index in range(count):
        line = next(stream).strip()
        if not (line.startswith("(") and line.endswith(")")):
            raise SystemExit("Malformed OpenFOAM coordinate")
        values = np.fromstring(line[1:-1], sep=" ")
        if values.shape != (3,):
            raise SystemExit("Malformed OpenFOAM coordinate")
        imported[index] = values
if not np.isfinite(original).all() or not np.isfinite(imported).all():
    raise SystemExit("Non-finite coordinate")
changed = np.any(original != imported, axis=1)
displacement = np.linalg.norm(original - imported, axis=1)
report = {"status": "point_transport_exact" if not changed.any() else "point_transport_changed",
          "msh22_sha256": sha(msh), "openfoam_points_sha256": sha(points),
          "points_checked": count, "changed_points": int(changed.sum()),
          "max_coordinate_displacement_m_conditional": float(displacement.max()),
          "scale_verified": False, "CFD_admitted": False}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
if changed.any():
    raise SystemExit(1)
