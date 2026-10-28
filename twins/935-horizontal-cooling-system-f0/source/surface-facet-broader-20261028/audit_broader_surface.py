"""Independently count thin facets and vertex changes in the pinned 935 repair."""

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import cKDTree
import trimesh


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quality(mesh):
    triangles = mesh.triangles
    a = triangles[:, 1] - triangles[:, 0]
    b = triangles[:, 2] - triangles[:, 0]
    c = triangles[:, 2] - triangles[:, 1]
    denominator = np.sum(a * a, axis=1) + np.sum(b * b, axis=1) + np.sum(c * c, axis=1)
    q = 2 * np.sqrt(3) * np.linalg.norm(np.cross(a, b), axis=1) / denominator
    if not np.isfinite(q).all():
        raise ValueError("Non-finite facet quality")
    return q


if len(sys.argv) != 4:
    raise SystemExit("Usage: audit_broader_surface.py SOURCE_OFF CANDIDATE_OFF NEW_PRIVATE_JSON")
source, candidate, output = (Path(value).resolve() for value in sys.argv[1:])
if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
    raise SystemExit("Use a fresh private output under work/")
source_sha = "5d900f6da900b4bffac2fdacfd6e0a346f8c0259a19299725621d4fd1e48c12a"
candidate_sha = "7d273b6072449c1e9140a995847fc4704990944fbb888d74a6a10a5a3db79091"
if sha(source) != source_sha or sha(candidate) != candidate_sha:
    raise SystemExit("Pinned surface changed")
old, new = (trimesh.load_mesh(path, process=False) for path in (source, candidate))
if ((len(old.vertices), len(old.faces), len(new.vertices), len(new.faces)) != (439365, 878730, 439306, 878612)
        or not old.is_watertight or not new.is_watertight or not old.is_winding_consistent
        or not new.is_winding_consistent or old.volume <= 0 or new.volume <= 0):
    raise SystemExit("Surface shape or basic topology failed")
old_q, new_q = quality(old), quality(new)
old_distance, _ = cKDTree(new.vertices).query(old.vertices)
new_distance, _ = cKDTree(old.vertices).query(new.vertices)
removed = int(np.count_nonzero(old_distance > 1e-10))
if removed != 59 or np.any(new_distance > 1e-10):
    raise SystemExit("Unexpected vertex correspondence")
report = {
    "status": "facet_repair_quality_screen_not_CFD_or_manufacturing_admission",
    "source_sha256": source_sha, "candidate_sha256": candidate_sha,
    "source_faces": len(old.faces), "candidate_faces": len(new.faces),
    "source_quality_lt_0p01": int(np.count_nonzero(old_q < .01)),
    "candidate_quality_lt_0p01": int(np.count_nonzero(new_q < .01)),
    "source_quality_lt_0p05": int(np.count_nonzero(old_q < .05)),
    "candidate_quality_lt_0p05": int(np.count_nonzero(new_q < .05)),
    "source_min_quality": float(old_q.min()), "candidate_min_quality": float(new_q.min()),
    "candidate_vertices_are_source_subset_at_1e-10": True,
    "removed_source_vertices": removed,
    "source_volume_source_units_cubed": float(old.volume),
    "candidate_volume_source_units_cubed": float(new.volume),
    "self_intersection_and_full_surface_bound_checked_by_this_script": False,
    "scale_verified": False, "CFD_admitted": False, "manufacturing_authorized": False,
}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
