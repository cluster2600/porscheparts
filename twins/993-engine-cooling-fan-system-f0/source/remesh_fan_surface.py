"""Isotropic remeshing with an independent audit against the PicoGK surface."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pymeshlab as ml
import trimesh

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
original = trimesh.load_mesh(args.source)
assert original.is_watertight and original.is_winding_consistent and original.body_count == 1
assert 240 < original.extents[0] < 246, "Expected the 245 mm pilot in millimetres"
args.output.mkdir(parents=True, exist_ok=False)
meshset = ml.MeshSet()
meshset.load_new_mesh(str(args.source))
meshset.meshing_isotropic_explicit_remeshing(
    iterations=6, targetlen=ml.PureValue(.8), maxsurfdist=ml.PureValue(.04),
    featuredeg=180, checksurfdist=True)
target = args.output / "rotor-mm.stl"
meshset.save_current_mesh(str(target))
meshset.compute_selection_by_self_intersections_per_face()
self_intersections = meshset.current_mesh().selected_face_number()
remeshed = trimesh.load_mesh(target)
distances = []
for direction, (source, destination) in enumerate(((original, remeshed), (remeshed, original))):
    points, _ = trimesh.sample.sample_surface(source, 10000, seed=993 + direction)
    _, distance, _ = trimesh.proximity.closest_point(destination, points)
    distances.append({"max_mm": float(distance.max()), "p99_mm": float(np.quantile(distance, .99))})
triangles = remeshed.triangles
quality = 4 * np.sqrt(3) * remeshed.area_faces / np.sum(
    (triangles - np.roll(triangles, 1, axis=1))**2, axis=(1, 2))
gap = float(124 - np.linalg.norm(remeshed.vertices[:, :2], axis=1).max())
volume_error = float(remeshed.volume / original.volume - 1)
passed = bool(remeshed.is_watertight and remeshed.is_winding_consistent
              and self_intersections == 0
              and remeshed.body_count == 1 and abs(volume_error) < .002
              and max(d["max_mm"] for d in distances) < .15
              and np.isfinite(quality).all() and quality.min() > .05 and gap > 1.35)
report = {"status": "passed_surface_screen" if passed else "rejected",
          "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
          "output_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
          "pymeshlab_version": importlib.metadata.version("pymeshlab"),
          "sample_count_each_direction": 10000, "sample_seeds": [993, 994],
          "faces": len(remeshed.faces), "volume_error_fraction": volume_error,
          "self_intersecting_faces": self_intersections,
          "minimum_triangle_quality": float(quality.min()), "minimum_vertex_gap_mm": gap,
          "distances_sampled_not_bound": distances, "manufacturing_authorized": False}
(args.output / "surface-audit.json").write_text(json.dumps(report, indent=2) + "\n")
if not passed:
    raise ValueError("Surface remeshing rejected; retain the attempted output")
