"""Read-only exact disk/boundary continuity, allowing internal quotient reductions."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT/'work/962-engineering'
SOURCE = ROOT/'twins/962-cylinder-head-f0/source'
ORIGINAL = WORK/'analysis-envelope-025-003/exact-input.bin'
CANDIDATE = WORK/'atomic-cavity-head-001/head-atomic002/candidate.bin'
ORIGINS = CANDIDATE.with_name('vertex-coordinate-origins.u64')
PATCH = WORK/'finest-endpoint-003-head-001/head-endpoint003/patch-reference-face-ids.u64'
RETAINED = WORK/'quality-patch-features-001/worker-report.json'
OUTPUT = Path(__file__).parent/'patch-analysis.json'
FIXED = {
    ORIGINAL: '894ece6e63d99684fd7c8710caf73132cd73731ac8bc667548c21c85962d4c95',
    CANDIDATE: '1f9dbd4cda61c7b58084479ebb165fb01280fa831752dc0da18517e548131b1a',
    ORIGINS: '22d9303503c98a7c4b0f08bfe20df3dddce51b7a86a96f4fcbc503f0cb163e47',
    PATCH: 'c93dcc98059fed493f2d50d64cbdd4a6ca4b3d79199af390442cea4506175763',
    RETAINED: 'bb99c186083869fa792228ad2095066abcca60c652112118999edb3c9265e72d',
    SOURCE/'audit_quality_features.py': '4e6eb1358c1687fabe78ca95958fb9e4c1724537abe2718414bfe46834f4ceb4',
    SOURCE/'audit_quality_head.py': 'a298270aa00b1536314a07629b935500c68883ca0d3bd1a179d71b49a8e73991',
    SOURCE/'audit_quality_patch.py': '3532a172b2bce3a8ead7c8b11b712a2b55891377726fa1b6d847e84f0eed3912',
    SOURCE/'mesh_head.py': '69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5',
    SOURCE/'prepare_head_analysis.py': 'cda8f7155a8c22ab66898f07d1ad452ba5384ad7f75a1f012606685cd8a12dc3',
}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def array_digest(rows):
    return hashlib.sha256(np.ascontiguousarray(rows).tobytes()).hexdigest()


def verify():
    if any(not p.is_file() or p.is_symlink() or digest(p) != sha for p, sha in FIXED.items()):
        raise ValueError('Exact bound source/candidate/origin/reference bytes required')


def unique_owner(original_ids, owners, face_id):
    choices = set(owners.get(int(original_ids[0]), ()))
    for vertex in original_ids[1:]:
        choices.intersection_update(owners.get(int(vertex), ()))
    if len(choices) != 1:
        raise ValueError('Candidate patch face %d has %d immutable group owners: %s' %
                         (face_id, len(choices), sorted(choices)))
    return next(iter(choices))


def analyze():
    verify(); source_hash = digest(Path(__file__)); started = time.monotonic()
    sys.path.insert(0, str(SOURCE))
    from audit_quality_features import patch_groups, patch_topology
    from audit_quality_head import read, canonical_faces
    p, f = read(ORIGINAL); q, g = read(CANDIDATE)
    input_arrays = [array_digest(x) for x in (p, f, q, g)]
    origins = np.fromfile(ORIGINS, dtype='<u8'); patch = np.fromfile(PATCH, dtype='<u8')
    if ((len(p), len(f), len(q), len(g)) != (902145, 1804706, 901727, 1803870)
            or len(origins) != len(q) or len(np.unique(origins)) != len(q)
            or origins.max() >= len(p) or q.tobytes() != p[origins].tobytes()
            or len(patch) != 4704 or not np.array_equal(patch, np.unique(patch)) or patch.max() >= len(f)):
        raise ValueError('Full ordered origin-byte association or original patch changed')
    mask = np.zeros(len(f), dtype=bool); mask[patch] = True
    fixed = np.zeros(len(p), dtype=bool); fixed[f[~mask].reshape(-1)] = True
    fixed |= (p[:, 0] == -76) | (p[:, 0] == 76)
    inverse = np.full(len(p), -1, dtype=np.int64); inverse[origins] = np.arange(len(q))
    if int(fixed.sum()) != 900845 or np.any(inverse[fixed] < 0):
        raise ValueError('Original fixed mask or retained fixed vertices changed')
    if q[inverse[fixed]].tobytes() != p[fixed].tobytes():
        raise ValueError('Original fixed-coordinate bytes changed')
    keys = lambda faces: np.ascontiguousarray(canonical_faces(faces), dtype='<u8').view('V24').reshape(-1)
    exterior = keys(f[~mask]); original_ids = origins[g]; candidate_keys = keys(original_ids)
    exterior_mask = np.isin(candidate_keys, exterior)
    if (len(exterior) != 1800002 or len(np.unique(exterior)) != len(exterior)
            or not np.array_equal(np.sort(candidate_keys[exterior_mask]), np.sort(exterior))):
        raise ValueError('Exact complete oriented exterior multiset changed')
    candidate_patch = np.flatnonzero(~exterior_mask)
    if len(candidate_patch) != 3868:
        raise ValueError('Full candidate patch-face complement changed')
    groups = patch_groups(f[patch]); retained = json.loads(RETAINED.read_text())
    if len(groups) != 228 or retained['patch_count'] != 228 or retained['disk_patch_count'] != 228:
        raise ValueError('Original 228-disk partition changed')
    owners = {}; before_rows = []
    for i, group in enumerate(groups):
        selected = patch[group].astype(np.int64); before, boundary = patch_topology(f[selected])
        old = retained['patches'][i]
        if (before['components'] != 1 or before['euler_characteristic'] != 1 or before['boundary_loops'] != 1
                or old['patch_id'] != i or old['first_source_face'] != int(selected[0])
                or old['source_face_indices_sha256'] != array_digest(selected)
                or old['topology'] != before or old['exact_oriented_boundary_indices_sha256'] != array_digest(boundary)
                or old['exact_boundary_coordinates_sha256'] != array_digest(p[np.unique(boundary)])):
            raise ValueError('Retained original disk/boundary identity changed: %d' % i)
        for vertex in np.unique(f[selected]):
            owners.setdefault(int(vertex), set()).add(i)
        before_rows.append((selected, before, boundary))
    assigned = [[] for _ in groups]
    labels = np.empty(len(candidate_patch), dtype=np.int64)
    for j, face_id in enumerate(candidate_patch):
        owner = unique_owner(original_ids[face_id], owners, int(face_id))
        assigned[owner].append(int(face_id)); labels[j] = owner
    rows = []
    for i, (selected, before, boundary) in enumerate(before_rows):
        ids = np.asarray(assigned[i], dtype=np.int64)
        if not len(ids):
            raise ValueError('Original disk has no uniquely assigned candidate faces: %d' % i)
        after, candidate_boundary = patch_topology(original_ids[ids])
        boundary_ids = np.unique(boundary)
        if (after['components'] != 1 or after['euler_characteristic'] != 1 or after['boundary_loops'] != 1
                or not after['vertex_link_manifold'] or not np.array_equal(boundary, candidate_boundary)
                or not fixed[boundary_ids].all() or np.any(inverse[boundary_ids] < 0)
                or q[inverse[boundary_ids]].tobytes() != p[boundary_ids].tobytes()):
            raise ValueError('Disk topology or exact oriented fixed boundary changed: %d' % i)
        rows.append(dict(patch_id=i, original_face_indices_sha256=array_digest(selected),
            candidate_face_indices_sha256=array_digest(ids), original=before, candidate=after,
            delta_VEF={key: after[key]-before[key] for key in ('vertices', 'edges', 'faces')},
            oriented_original_ID_boundary_sha256=array_digest(boundary),
            boundary_coordinate_bytes_sha256=array_digest(p[boundary_ids]),
            exact_fixed_boundary_unchanged=True, unique_original_group_association=True))
    verify()
    if source_hash != digest(Path(__file__)) or input_arrays != [array_digest(x) for x in (p, f, q, g)]:
        raise ValueError('Input/source/array drift during read-only patch analysis')
    return dict(status='all_original_disk_and_exact_fixed_boundary_subgates_passed',
        source_sha256=source_hash, input_sha256={str(p.relative_to(ROOT)): sha for p, sha in FIXED.items()},
        original_patch_faces=4704, candidate_patch_faces=3868, shared_oriented_exterior_faces=1800002,
        original_fixed_vertices=900845, original_patch_disks=228, candidate_patch_disks=len(rows),
        complete_candidate_face_partition=True, all_candidate_patch_faces_uniquely_assigned=True,
        candidate_patch_face_indices_sha256=array_digest(candidate_patch),
        assignment_patch_IDs_in_candidate_face_order_sha256=array_digest(labels), patches=rows,
        internal_VEF_reductions_permitted=True, equal_count_compare_patch_not_called=True,
        bound_inputs_and_arrays_unchanged=True, wall_seconds=time.monotonic()-started,
        opening_probes_executed=False, all_eight_retained_VTK_opening_probes_still_required=True,
        original_bionic_patch_continuity_only=True, complete_semantic_or_OEM_interface_map=False,
        candidate_wall_clearance_qualified=False, conformal_metal_fluid_interface_validated=False,
        independent_distance_or_global_intersections_credited_here=False,
        volume_mesh_or_solver_admitted=False, thermal_strength_LPBF_or_manufacturing_qualified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.output.resolve() != OUTPUT.resolve() or args.output.exists() or args.output.is_symlink():
        raise ValueError('Only the fixed fresh analysis report is permitted')
    try:
        report = analyze(); code = 0
    except Exception as exc:
        report = dict(status='failed_or_rejected_patch_continuity', error=type(exc).__name__+': '+str(exc),
            opening_probes_executed=False, complete_semantic_or_OEM_interface_map=False,
            volume_mesh_or_solver_admitted=False, thermal_strength_LPBF_or_manufacturing_qualified=False)
        code = 2
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False); stream.write('\n')
    raise SystemExit(code)
