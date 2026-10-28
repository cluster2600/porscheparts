"""Private diagnostic of vertices removed by a local facet repair."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import trimesh
from scipy.spatial import cKDTree


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


if len(sys.argv) != 6:
    raise SystemExit("Usage: audit_removed_vertices_scan.py SOURCE_OFF CANDIDATE_OFF SCAN_NPZ FRAME_JSON NEW_PRIVATE_JSON")
source, candidate, scan, frame, out = (Path(value).resolve() for value in sys.argv[1:])
expected = ["5d900f6da900b4bffac2fdacfd6e0a346f8c0259a19299725621d4fd1e48c12a",
            "7d273b6072449c1e9140a995847fc4704990944fbb888d74a6a10a5a3db79091",
            "452f76162d6148017299edd1563e4e06b933dd9fe105bee30c185f96d98cc247"]
if out.exists() or not out.is_relative_to((Path.cwd() / "work").resolve()) or [sha(p) for p in (source, candidate, scan)] != expected:
    raise SystemExit("Input hash or output guard failed")
if sha(frame) != "c9e86cbbc1fb0e1faa7add119bc69dfa87e8def68d67a5b7d1f7cf661c832e3f" or json.loads(frame.read_text())["aligned_npz_sha256"] != expected[2]:
    raise SystemExit("Scan frame audit mismatch")
a, b = (trimesh.load_mesh(p, process=False) for p in (source, candidate))
with np.load(scan) as z:
    scan_mesh = trimesh.Trimesh(vertices=z["vertices"], faces=z["faces"], process=False)
old = np.asarray(a.vertices); new = np.asarray(b.vertices)
old_distance, _ = cKDTree(new).query(old)
new_distance, _ = cKDTree(old).query(new)
ids = np.flatnonzero(old_distance > 1e-10)
if len(ids) != 59 or np.any(new_distance > 1e-10):
    raise SystemExit("Unexpected vertex identity")
_, distance, scan_face = trimesh.proximity.closest_point(scan_mesh, old[ids])
if not np.isfinite(distance).all():
    raise SystemExit("Non-finite distance")
report = {"status": "removed_vertex_proximity_screen_not_full_surface_or_measurement_classification",
          "source_sha256": expected[0], "candidate_sha256": expected[1], "aligned_scan_sha256": expected[2],
          "scan_frame_audit_sha256": sha(frame),
          "source_vertices": len(old), "candidate_vertices": len(new), "removed_vertex_count": len(ids),
          "candidate_vertices_are_source_subset_at_1e-10": True,
          "removed_vertex_to_candidate_vertex_max_source_units": float(old_distance[ids].max()),
          "removed_vertex_to_scan_median_source_units": float(np.median(distance)),
          "removed_vertex_to_scan_max_source_units": float(distance.max()),
          "removed_vertices_within_0p5_source_units": int(np.count_nonzero(distance <= .5)),
          "removed_vertices_over_1p0_source_units": int(np.count_nonzero(distance > 1)),
          "removed_vertex_ids": ids.tolist(), "scan_face_ids": scan_face.tolist(),
          "distances_source_units": distance.tolist(), "scale_verified": False,
          "scan_acquisitions_physically_registered": False}
out.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k not in ("removed_vertex_ids", "scan_face_ids", "distances_source_units")}))
