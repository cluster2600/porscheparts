"""Analysis-only collapse of four sub-voxel PicoGK rotor edges."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import trimesh


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


if len(sys.argv) != 3:
    raise SystemExit("usage: collapse_short_edges_20261027.py NATIVE_ROTOR_NPZ NEW_OUTPUT_DIR")
source = Path(sys.argv[1])
assert sha(source) == "5f999a7596a5d491027eb4d9020a4e14bcad2620aa1e2a58748452df461b815b"
out = Path(sys.argv[2])
if out.exists():
    raise SystemExit("fresh output required")

with np.load(source, allow_pickle=False) as data:
    vertices = data["vertices"].copy()
    faces = data["faces"].copy()

old_mesh = trimesh.Trimesh(vertices=vertices.copy(), faces=faces.copy(), process=False)
assert old_mesh.is_watertight and old_mesh.is_winding_consistent
edges = ((152145, 152146), (563192, 563193), (656028, 656029), (653509, 653511))
assert len(set(sum((list(e) for e in edges), []))) == 8
checks = []
for keep, remove in edges:
    distance = float(np.linalg.norm(vertices[keep] - vertices[remove]))
    assert 0 < distance < 0.0005
    a = np.flatnonzero(np.any(faces == keep, axis=1))
    b = np.flatnonzero(np.any(faces == remove, axis=1))
    both = np.intersect1d(a, b)
    link = (set(faces[a].ravel()) - {keep, remove}) & (set(faces[b].ravel()) - {keep, remove})
    assert len(both) == 2 and len(link) == 2
    checks.append({"edge": [keep, remove], "length_source_units": distance, "link_condition": True})
    faces[faces == remove] = keep

keep_faces = (faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 2] != faces[:, 0])
assert int(np.count_nonzero(~keep_faces)) == 8
faces = faces[keep_faces]
used, inverse = np.unique(faces, return_inverse=True)
new_vertices = vertices[used]
new_faces = inverse.reshape(-1, 3)
new_mesh = trimesh.Trimesh(vertices=new_vertices, faces=new_faces, process=False)
assert new_mesh.is_watertight and new_mesh.is_winding_consistent
assert old_mesh.euler_number == new_mesh.euler_number
assert np.isfinite(new_mesh.volume) and new_mesh.volume > 0
assert abs((new_mesh.volume - old_mesh.volume) / old_mesh.volume) < 1e-7

out.mkdir(mode=0o700)
np.savez_compressed(out / "rotor-indexed.npz", vertices=new_vertices, faces=new_faces)
with (out / "rotor.off").open("x") as stream:
    stream.write(f"OFF\n{len(new_vertices)} {len(new_faces)} 0\n")
    np.savetxt(stream, new_vertices, fmt="%.17g")
    np.savetxt(stream, np.column_stack([np.full(len(new_faces), 3), new_faces]), fmt="%d")
report = {
    "schema": "935-analysis-only-native-edge-collapse-v1",
    "classification": "analysis_surface_candidate_not_historical_geometry",
    "source_npz_sha256": sha(source),
    "source_script_sha256": sha(Path(__file__)),
    "edge_checks": checks,
    "removed_vertices": len(vertices) - len(new_vertices),
    "removed_faces": len(keep_faces) - len(new_faces),
    "source_vertices": len(vertices),
    "candidate_vertices": len(new_vertices),
    "source_faces": len(keep_faces),
    "candidate_faces": len(new_faces),
    "watertight": new_mesh.is_watertight,
    "winding_consistent": new_mesh.is_winding_consistent,
    "euler_characteristic": new_mesh.euler_number,
    "source_volume_source_units_cubed": old_mesh.volume,
    "candidate_volume_source_units_cubed": new_mesh.volume,
    "relative_volume_change": (new_mesh.volume - old_mesh.volume) / old_mesh.volume,
    "candidate_npz_sha256": sha(out / "rotor-indexed.npz"),
    "candidate_off_sha256": sha(out / "rotor.off"),
    "CFD_admitted": False,
}
(out / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
