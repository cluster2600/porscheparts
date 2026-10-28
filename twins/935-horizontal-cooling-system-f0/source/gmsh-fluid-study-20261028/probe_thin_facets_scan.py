"""Private point-sampled proximity of thin analysis facets to the aligned scan."""

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


if len(sys.argv) != 4:
    raise SystemExit("Usage: probe_thin_facets_scan.py CANDIDATE_OFF ALIGNED_SCAN_NPZ NEW_PRIVATE_JSON")
candidate, scan, output = (Path(value).resolve() for value in sys.argv[1:])
if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
    raise SystemExit("Use a fresh private path under work/")
if sha(candidate) != "5d900f6da900b4bffac2fdacfd6e0a346f8c0259a19299725621d4fd1e48c12a":
    raise SystemExit("Unexpected candidate")
if sha(scan) != "452f76162d6148017299edd1563e4e06b933dd9fe105bee30c185f96d98cc247":
    raise SystemExit("Unexpected aligned scan")
mesh = trimesh.load_mesh(candidate, process=False)
v, f = np.asarray(mesh.vertices), np.asarray(mesh.faces)
with np.load(scan) as data:
    scan_mesh = trimesh.Trimesh(vertices=data["vertices"], faces=data["faces"], process=False)
if (v.shape, f.shape, scan_mesh.vertices.shape, scan_mesh.faces.shape) != (
        (439365, 3), (878730, 3), (624492, 3), (1240439, 3)):
    raise SystemExit("Unexpected geometry dimensions")
triangles = v[f]
ab, ac, bc = triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0], triangles[:, 2] - triangles[:, 1]
cross = np.cross(ab, ac)
quality = 2 * np.sqrt(3) * np.linalg.norm(cross, axis=1) / (np.sum(ab * ab, axis=1) + np.sum(ac * ac, axis=1) + np.sum(bc * bc, axis=1))
ids = np.flatnonzero(quality < 0.05)
if len(ids) != 113 or np.count_nonzero(quality < 0.01) != 24:
    raise SystemExit("Unexpected thin-facet population")
t = triangles[ids]
samples = np.stack((t[:, 0], t[:, 1], t[:, 2], (t[:, 0] + t[:, 1]) / 2,
                    (t[:, 1] + t[:, 2]) / 2, (t[:, 2] + t[:, 0]) / 2,
                    t.mean(axis=1)), axis=1)
closest, distance, scan_face = trimesh.proximity.closest_point(scan_mesh, samples.reshape(-1, 3))
distances = distance.reshape(len(ids), 7)
if not np.isfinite(distances).all():
    raise SystemExit("Non-finite scan distance")
worst = quality[ids] < 0.01
report = {
    "status": "point_sampled_scan_proximity_not_surface_containment_or_provenance",
    "candidate_sha256": sha(candidate), "aligned_scan_sha256": sha(scan),
    "scan_vertices": len(scan_mesh.vertices), "scan_faces": len(scan_mesh.faces),
    "facet_count": len(ids), "worst_facet_count": int(worst.sum()),
    "samples_per_face": 7, "unit": "uncalibrated_source_unit",
    "per_facet": [{"face_id": int(face_id), "quality": float(quality[face_id]),
                   "radial_centroid": float(np.linalg.norm(t[index].mean(axis=0)[:2])),
                   "sample_distances": distances[index].tolist(),
                   "nearest_scan_face_ids": scan_face.reshape(len(ids), 7)[index].tolist()}
                  for index, face_id in enumerate(ids)],
    "summary": {},
    "scan_identity_and_alignment_independently_verified": False,
    "calibrated": False, "measured_surface_classification": False,
}
for name, selected in (("all_below_0p05", distances), ("worst_below_0p01", distances[worst])):
    face_max = selected.max(axis=1)
    report["summary"][name] = {"faces": len(selected), "sample_distance_median": float(np.median(selected)),
                               "sample_distance_max": float(selected.max()),
                               "face_max_distance_median": float(np.median(face_max)),
                               "face_max_distance_max": float(face_max.max()),
                               "faces_all_samples_within_0p5": int(np.count_nonzero(face_max <= 0.5)),
                               "faces_all_samples_within_1p0": int(np.count_nonzero(face_max <= 1.0))}
good_ids = np.flatnonzero(quality >= 0.2)
good_centres = triangles[good_ids].mean(axis=1)
worst_centres = t[worst].mean(axis=1)
tree = cKDTree(good_centres)
_, neighbours = tree.query(worst_centres, k=64)
used = set()
controls = []
for candidates in neighbours:
    for index in candidates:
        face = int(good_ids[index])
        if face not in used:
            controls.append(face)
            used.add(face)
            break
    else:
        raise SystemExit("Could not select distinct nearby control faces")
control_triangles = triangles[controls]
control_samples = np.stack((control_triangles[:, 0], control_triangles[:, 1], control_triangles[:, 2],
                            (control_triangles[:, 0] + control_triangles[:, 1]) / 2,
                            (control_triangles[:, 1] + control_triangles[:, 2]) / 2,
                            (control_triangles[:, 2] + control_triangles[:, 0]) / 2,
                            control_triangles.mean(axis=1)), axis=1)
_, control_distance, _ = trimesh.proximity.closest_point(scan_mesh, control_samples.reshape(-1, 3))
control_distance = control_distance.reshape(len(controls), 7)
pair_distance = np.linalg.norm(control_triangles.mean(axis=1) - worst_centres, axis=1)
report["nearby_good_face_controls"] = {
    "selection": "nearest distinct analysis face with normalized quality >= 0.2 to each worst face centroid",
    "faces": len(controls), "face_ids": controls,
    "pair_centroid_distance_median": float(np.median(pair_distance)),
    "pair_centroid_distance_max": float(pair_distance.max()),
    "sample_distance_median": float(np.median(control_distance)),
    "face_max_distance_median": float(np.median(control_distance.max(axis=1))),
    "face_max_distance_max": float(control_distance.max()),
    "faces_all_samples_within_0p5": int(np.count_nonzero(control_distance.max(axis=1) <= 0.5)),
    "faces_all_samples_within_1p0": int(np.count_nonzero(control_distance.max(axis=1) <= 1.0)),
}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"thin": report["summary"], "nearby_controls": report["nearby_good_face_controls"]}))
