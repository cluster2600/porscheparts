"""Compare unchanged private study meshes against the unchanged source observations."""
import hashlib
import json
from pathlib import Path
import time

import igl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

started = time.monotonic()
source_receipt = json.loads((ROOT / "source-array-verification.json").read_text())
source_path = ROOT / "exact-source-arrays.npz"
assert digest(source_path) == source_receipt["exact_arrays_sha256"]
source = np.load(source_path, allow_pickle=False)
sv, sf = source["vertices"], source["triangles"]
results = {}
probes = {}
for name in ["coarse", "fine"]:
    path = ROOT / f"935-head-reconstructed-study-{name}-mm.npz"
    parent = json.loads((ROOT / f"{name}-pitch2/report.json").read_text())
    assert digest(path) == parent["input_sha256"]
    arrays = np.load(path, allow_pickle=False)
    mesh = trimesh.Trimesh(arrays["vertices"], arrays["triangles"], process=False)
    assert mesh.is_volume
    topology = {"vertex_connected_bodies": int(mesh.body_count),
                "euler_characteristic": int(mesh.euler_number),
                "watertight": bool(mesh.is_watertight),
                "winding_consistent": bool(mesh.is_winding_consistent)}
    sample = np.load(ROOT / f"{name}-pitch2/private-thickness-probes.npz", allow_pickle=False)
    points, wall = sample["surface_points"], sample["local_thickness_mm"]
    d2, face_ids, nearest = igl.point_mesh_squared_distance(points, sv, sf)
    assert np.isfinite(d2).all() and (d2 >= 0).all()
    distance = np.sqrt(d2)
    thin = wall < .5
    results[name] = {
        "input_sha256": parent["input_sha256"], "topology": topology,
        "thin_sample_count_below_0_5_mm": int(thin.sum()),
        "thin_samples_source_distance_mm": {
            key: float(value) for key, value in zip(["min", "median", "max"],
                np.quantile(distance[thin], [0, .5, 1]))} if thin.any() else None,
        "thin_samples_farther_than_source_distance_mm": {
            str(limit): int((thin & (distance > limit)).sum()) for limit in [.05, .1, .25]},
        "interpretation": "Distances are to observed triangles, not to the unknown true surface; thresholds are diagnostic bins only",
    }
    np.savez_compressed(ROOT / f"{name}-source-probes.npz", surface_points=points,
                        local_thickness_mm=wall, source_distance_mm=distance,
                        nearest_source_face=face_ids, nearest_source_point=nearest)
    probes[name] = points, wall, distance
    assert digest(path) == parent["input_sha256"]
    del mesh, arrays
assert digest(source_path) == source_receipt["exact_arrays_sha256"]
results["source_obj_sha256"] = source_receipt["source_obj_sha256"]
results["source_arrays_sha256"] = source_receipt["exact_arrays_sha256"]
results["elapsed_seconds"] = time.monotonic() - started
results["manufacturing_accepted"] = False
(ROOT / "comparison.json").write_text(json.dumps(results, indent=2) + "\n")

fig, axes = plt.subplots(2, 2, figsize=(12, 10))
display = sv[::max(1, len(sv) // 50000)]
points, wall, distance = probes["fine"]
for ax, (a, b) in zip(axes.ravel()[:3], [(0, 1), (0, 2), (1, 2)]):
    ax.scatter(display[:, a], display[:, b], s=.15, color="#b6bdc6", rasterized=True)
    thin = wall < .5
    ax.scatter(points[thin, a], points[thin, b], s=22, color="#cb4b16", label="Fine study: thickness sample <0.5 mm")
    far = thin & (distance > .1)
    ax.scatter(points[far, a], points[far, b], s=40, facecolors="none", edgecolors="#6c2a96", label="Also >0.1 mm from observed triangles")
    ax.set(xlabel=f"{'XYZ'[a]} (mm)", ylabel=f"{'XYZ'[b]} (mm)", aspect="equal")
    ax.legend(fontsize=6)
ax = axes.ravel()[3]
for name, (_, values, _) in probes.items():
    ax.plot(np.sort(values), np.arange(1, len(values) + 1) / len(values), label=name)
ax.set(xlabel="Sampled local thickness (mm)", ylabel="Cumulative sample fraction", xlim=(0, 10))
ax.legend()
fig.suptitle("935 study geometry — diagnostic samples, no manufacturing acceptance")
fig.tight_layout()
fig.savefig(ROOT / "private-printability-overview.png", dpi=160)
print(json.dumps(results))
