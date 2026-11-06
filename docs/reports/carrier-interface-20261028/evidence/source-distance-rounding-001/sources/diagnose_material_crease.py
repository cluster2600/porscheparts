"""Local diagnostic of the one marked material-side crease; not a certificate."""
from pathlib import Path
import hashlib
import json

import igl
import numpy as np

r = Path(__file__).resolve().parent
out = r/"material-crease-diagnosis-001.json"
assert not out.exists()
source = r.parent/"precision-transfer-001/carrier-local-001/candidate.npz"
rounded = r/"carrier-001/decoded-001/candidate.npz"
sz, rz = np.load(source), np.load(rounded)
sv, sf = sz["vertices"], sz["triangles"]
v, f = rz["vertices"], rz["triangles"]
audit = json.loads((r/"carrier-001/material-feature-audit.json").read_text())
edge = audit["most_reentrant_edges"][0]["vertices"]
ids = np.flatnonzero(np.any(f == edge[0], axis=1) & np.any(f == edge[1], axis=1))
assert len(ids) == 2
tri = v[f[ids]]
normals = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
normals /= np.linalg.norm(normals, axis=1)[:, None]
points = np.vstack([tri.mean(axis=1), v[edge], v[edge].mean(axis=0)])
d2, nearest, closest = igl.point_mesh_squared_distance(points, sv, sf)
dist = np.sqrt(d2)
gradient = (points-closest)/dist[:, None]
angle = np.degrees(np.arccos(np.clip(gradient[0]@gradient[1], -1, 1)))
report = dict(scope="Local double-precision distance diagnostic; not complete embedding or an exact-offset certificate",
              source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), rounded_sha256=hashlib.sha256(rounded.read_bytes()).hexdigest(),
              material_edge=edge, incident_void_face_indices=ids.tolist(), incident_void_triangles_mm=tri.tolist(),
              incident_void_normals=normals.tolist(), query_points_mm=points.tolist(), nearest_source_faces=nearest.tolist(),
              nearest_source_points_mm=closest.tolist(), unsigned_source_distances_mm=dist.tolist(),
              distance_gradient_angle_between_face_centroids_degrees=float(angle),
              outward_void_facet_normal_difference_degrees=float(np.degrees(np.arccos(np.clip(normals[0]@normals[1], -1, 1)))),
              centre_normal_to_distance_gradient_angles_degrees=np.degrees(np.arccos(np.clip(np.einsum("ij,ij->i", normals, gradient[:2]), -1, 1))).tolist(),
              target_offset_mm=.1, maximum_local_offset_residual_mm=float(np.abs(dist-.1).max()))
out.write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps({k: v for k, v in report.items() if k not in ["incident_void_triangles_mm", "query_points_mm", "nearest_source_points_mm"]}))
