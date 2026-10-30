"""Test an existing alternate local triangulation against the frozen conservative parent."""
from pathlib import Path
import hashlib
import json
import sys
import time

import igl
import numpy as np
import trimesh

ROOT = Path(sys.argv[1]).resolve()
PARENT = ROOT / 'full-repair-20261029'
OUT = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from check_935_scan_intersections import detect

def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

paths = [PARENT / 'final-conservative-manifold/candidate.npz',
         PARENT / 'pymeshlab-surface-gaps-filtered/candidate.npz',
         PARENT / 'pymeshlab-surface-gaps-filtered/added-face-contour-ids.npy',
         PARENT / 'surface-gap-targets.json',
         ROOT / 'other-tools/exact-source-arrays.npz']
hashes = {str(p.relative_to(ROOT)): digest(p) for p in paths}
assert hashes['other-tools/exact-source-arrays.npz'] == 'dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a'
frozen = json.loads((PARENT / 'manifest.json').read_text())
assert all(frozen[str(p.relative_to(PARENT))] == hashes[str(p.relative_to(ROOT))]
           for p in paths if p.is_relative_to(PARENT))
OUT.mkdir(mode=0o700)
started = time.monotonic()
parent = np.load(paths[0], allow_pickle=False)
alternate = np.load(paths[1], allow_pickle=False)
original = np.load(paths[4], allow_pickle=False)
v, f = parent['vertices'], parent['triangles']
assert np.array_equal(v, alternate['vertices']) and np.array_equal(v, original['vertices'])
labels = np.load(paths[2], allow_pickle=False)
added = alternate['triangles'][len(original['triangles']):]
assert len(labels) == len(added)
patch = added[labels == 456]
target = next(x for x in json.loads(paths[3].read_text()) if x['contour_id'] == 456)
assert len(patch) == target['edges'] - 2 and len(patch) > 0
assert np.isin(patch, target['target_vertices']).all()
local = f[np.isin(f, target['target_vertices']).any(axis=1)]
def edges(faces):
    return np.concatenate([faces[:,[0,1]], faces[:,[1,2]], faces[:,[2,0]]])
pe = edges(patch)
keys, counts = np.unique(np.sort(pe, axis=1), axis=0, return_counts=True)
perimeter = keys[counts == 1]
assert len(perimeter) == target['edges'] and counts.max() == 2
le = edges(local)
for a, b in perimeter:
    parent_matches = le[np.all(np.sort(le, axis=1) == [a,b], axis=1)]
    patch_matches = pe[np.all(np.sort(pe, axis=1) == [a,b], axis=1)]
    assert len(parent_matches) == len(patch_matches) == 1
    assert np.array_equal(parent_matches[0], patch_matches[0][::-1])
candidate = np.vstack([f, patch])
assert np.array_equal(candidate[:len(f)], f)
print('Exact local perimeter and orientation matched; checking the whole candidate', flush=True)
pairs, _, degenerate = detect(v, candidate)
np.save(OUT / 'intersection-pairs.npy', pairs)
used = np.unique(candidate)
bad_vertices = int(np.count_nonzero(~igl.is_vertex_manifold(candidate)[used]))
mesh = trimesh.Trimesh(v, candidate, process=False)
edge_counts = np.bincount(mesh.edges_unique_inverse)
accepted = not len(pairs) and not len(degenerate) and not bad_vertices and edge_counts.max() <= 2 and mesh.is_winding_consistent
report = {'trial': 'existing_alternate_triangulation_for_original_contour_456',
          'inputs': hashes, 'added_faces': len(patch), 'original_coordinates_preserved': True,
          'all_parent_faces_preserved_in_order': True, 'local_perimeter_edges': len(perimeter),
          'intersection_pairs': len(pairs), 'degenerate_faces': len(degenerate),
          'nonmanifold_used_vertices': bad_vertices,
          'edges_above_two_incident_faces': int(np.count_nonzero(edge_counts > 2)),
          'boundary_edges_after': int(np.count_nonzero(edge_counts == 1)),
          'winding_consistent': bool(mesh.is_winding_consistent),
          'geometric_trial_accepted': bool(accepted), 'physical_closure_accepted': False,
          'manufacturing_accepted': False, 'elapsed_seconds': time.monotonic() - started}
assert all(digest(p) == hashes[str(p.relative_to(ROOT))] for p in paths)
if accepted:
    np.savez_compressed(OUT / 'candidate.npz', vertices=v, triangles=candidate)
    np.save(OUT / 'added-triangles.npy', patch)
    with (OUT / 'candidate.obj').open('w') as stream:
        stream.write('# Conservative surface study; unresolved boundaries; not a manufacturing part\n')
        np.savetxt(stream, v, fmt='v %.17g %.17g %.17g')
        np.savetxt(stream, candidate + 1, fmt='f %d %d %d')
(OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
