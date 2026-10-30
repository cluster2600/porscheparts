"""Recheck three existing rejected patches after conservative conflict removal."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import igl
import trimesh

ROOT = Path(sys.argv[1]).resolve()
OLD = ROOT / 'full-repair-20261029'
OUT = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from check_935_scan_intersections import detect

def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def edges(f):
    return np.concatenate([f[:,[0,1]], f[:,[1,2]], f[:,[2,0]]])

manifest = json.loads((OLD / 'manifest.json').read_text())
trial_path = OLD / 'cgal-surface-gaps/candidate.obj'
assert digest(trial_path) == manifest['cgal-surface-gaps/candidate.obj']
parent_path = ROOT / 'alternate-gap-456-20261029/candidate.npz'
parent_hash = digest(parent_path)
data = np.load(parent_path, allow_pickle=False)
v, current = data['vertices'], data['triangles']
original = np.load(ROOT / 'other-tools/exact-source-arrays.npz', allow_pickle=False)
trial = trimesh.load_mesh(trial_path, process=False, maintain_order=True, skip_materials=True)
assert np.array_equal(v, trial.vertices) and np.array_equal(v, original['vertices'])
assert np.array_equal(trial.faces[:len(original['triangles'])], original['triangles'])
added = np.asarray(trial.faces[len(original['triangles']):])
targets = json.loads((OLD / 'surface-gap-targets.json').read_text())
OUT.mkdir(mode=0o700)
rows = []
for cid in [807, 856, 916]:
    target = next(x for x in targets if x['contour_id'] == cid)
    patch = added[np.isin(added, target['target_vertices']).all(axis=1)]
    reasons = []
    if len(patch) != target['edges'] - 2:
        reasons.append('incomplete_patch')
    pe = edges(patch)
    keys, counts = np.unique(np.sort(pe, axis=1), axis=0, return_counts=True)
    perimeter = keys[counts == 1]
    if len(perimeter) != target['edges'] or counts.max(initial=0) > 2:
        reasons.append('patch_perimeter_mismatch')
    local = current[np.isin(current, target['target_vertices']).any(axis=1)]
    le = edges(local)
    for a, b in perimeter:
        pm = le[np.all(np.sort(le, axis=1) == [a,b], axis=1)]
        qm = pe[np.all(np.sort(pe, axis=1) == [a,b], axis=1)]
        if len(pm) != 1 or len(qm) != 1 or not np.array_equal(pm[0], qm[0][::-1]):
            reasons.append('cleaned_parent_has_different_boundary_or_orientation')
            break
    row = {'original_contour_id': cid, 'proposed_faces': len(patch),
           'whole_candidate_inspected': False, 'rejection_reasons': reasons}
    if not reasons:
        candidate = np.vstack([current, patch])
        pairs, _, zero = detect(v, candidate)
        np.save(OUT / f'contour-{cid}-intersection-pairs.npy', pairs)
        used = np.unique(candidate)
        bad = int(np.count_nonzero(~igl.is_vertex_manifold(candidate)[used]))
        mesh = trimesh.Trimesh(v, candidate, process=False)
        counts = np.bincount(mesh.edges_unique_inverse)
        row.update(whole_candidate_inspected=True, intersection_pairs=len(pairs),
                   zero_area_faces=len(zero), nonmanifold_used_vertices=bad,
                   winding_consistent=bool(mesh.is_winding_consistent))
        if len(pairs) or len(zero) or bad or counts.max() > 2 or not mesh.is_winding_consistent:
            reasons.append('whole_candidate_geometry_check_failed')
        else:
            current = candidate
    row['geometric_trial_accepted'] = not reasons
    rows.append(row)
    print(json.dumps(row), flush=True)
assert digest(parent_path) == parent_hash
assert digest(trial_path) == manifest['cgal-surface-gaps/candidate.obj']
accepted = [r['original_contour_id'] for r in rows if r['geometric_trial_accepted']]
report = {'parent_sha256': parent_hash, 'cgal_trial_sha256': manifest['cgal-surface-gaps/candidate.obj'],
          'trials': rows, 'accepted_original_contours': accepted,
          'original_coordinates_preserved': True, 'parent_faces_removed': 0,
          'physical_closure_accepted': False, 'manufacturing_accepted': False}
if accepted:
    np.savez_compressed(OUT / 'candidate.npz', vertices=v, triangles=current)
    with (OUT / 'candidate.obj').open('w') as f:
        f.write('# Conservative surface study; not a manufacturing part\n')
        np.savetxt(f, v, fmt='v %.17g %.17g %.17g')
        np.savetxt(f, current + 1, fmt='f %d %d %d')
(OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
