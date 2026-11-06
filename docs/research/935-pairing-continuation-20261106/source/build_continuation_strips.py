"""Construct bounded two-triangle frontier hypotheses after independent admission."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def directed_edges(faces):
    return faces[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2)


def incidence_changes(faces, vertices, parent_codes, parent_counts, parent_directions, boundary_codes, boundary_ids, boundary, curve_ids, curve):
    edges = directed_edges(faces); codes = edges.min(axis=1)*vertices+edges.max(axis=1)
    unique, counts = np.unique(codes, return_counts=True); changes = []; touched = []
    for code, count in zip(unique, counts):
        rows = edges[codes == code]
        if count > 2 or count == 2 and not np.array_equal(rows[0], rows[1, ::-1]):
            return None
        index = int(np.searchsorted(parent_codes, code))
        old_count = int(parent_counts[index]) if index < len(parent_codes) and parent_codes[index] == code else 0
        if old_count + count > 2:
            return None
        if old_count:
            if not np.array_equal(rows[0], parent_directions[index, ::-1]):
                return None
            pos = int(np.searchsorted(boundary_codes, code))
            assert pos < len(boundary_codes) and boundary_codes[pos] == code
            edge = int(boundary_ids[pos])
            if boundary['edge_origin_kind'][edge] != 1 or curve_ids[edge] != curve:
                return None
            touched.append(edge)
        changes.append((int(code), int(count), tuple(map(int, rows[0])), old_count))
    return changes, sorted(touched)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args(); job = json.loads(args.job.read_text()); started = time.monotonic()
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    proof = json.loads(Path(job['pair_verification']).read_text())
    assert proof['census_independently_verified'] and proof['census_sha256'] == sha(job['census'])
    assert proof['halo_sha256'] == sha(job['complete_halos'])
    registry_proof = json.loads(Path(job['registry_verification']).read_text())
    assert registry_proof['registry_independently_verified'] and registry_proof['registry_sha256'] == sha(job['registry'])
    assert registry_proof['source_sha256'] == sha(job['registry_inspector'])
    assert proof['source_sha256'] == sha(job['census_inspector'])
    assert registry_proof['census_sha256'] == sha(job['census'])
    first_global = job['first_global_pair_id']
    assert registry_proof['previous_registry_pairs'] == first_global
    assert job['assumption_accepted_for_exploratory_construction_only'] is True
    base, boundary, census, admission, registry = map(load, (job['mesh'], job['boundaries'], job['census'], job['complete_halos'], job['registry']))
    assert registry_proof['appended_selected_pairs'] == len(census['selected_pair_edge_ids'])
    assert np.array_equal(registry['global_pair_ids'][first_global:], np.arange(first_global, first_global+len(census['selected_pair_edge_ids'])))
    intersection = module(job['intersection_helper'], 'strip_intersection')
    fan_check = module(job['fan_helper'], 'strip_fans')
    points, faces = base['points'], base['triangles']; nv = len(points); edges = boundary['boundary_local_nodes']
    pedges = directed_edges(faces); pcodes = pedges.min(axis=1)*nv+pedges.max(axis=1)
    order = np.argsort(pcodes, kind='stable'); sorted_codes = pcodes[order]
    first = np.r_[0, np.flatnonzero(sorted_codes[1:] != sorted_codes[:-1])+1]
    parent_codes = sorted_codes[first]; parent_counts = np.diff(np.r_[first, len(order)])
    parent_directions = pedges[order[first]]
    assert np.all((parent_counts == 1) | (parent_counts == 2))
    bcodes = edges.min(axis=1)*nv+edges.max(axis=1); border = np.argsort(bcodes)
    bcodes = bcodes[border]
    # Complete parent incident masks have their own independent admission proof.
    trials, proposals = [], []
    pairs = census['selected_pair_edge_ids']; curves = census['selected_pair_curve_ids']
    for pair_id, ((left, right), curve) in enumerate(zip(pairs, curves)):
        a, b = edges[left]; c, d = edges[right]
        alternatives = (np.array([[b, a, d], [b, d, c]]), np.array([[b, a, c], [a, d, c]]))
        involved = np.unique([a, b, c, d])
        lo, hi = admission['halo_offsets'][pair_id:pair_id+2]
        halo = admission['halo_face_rows'][lo:hi]; valid = []
        flags = census['eligible_pair_diagonal_flags'][census['selected_eligible_pair_indices'][pair_id]]
        for diagonal, patch in enumerate(alternatives):
            row = dict(pair=pair_id, global_pair=first_global+pair_id, diagonal=diagonal, admitted=False)
            if not flags[diagonal]:
                row['reason'] = 'forward_material_side_wall_admission'; trials.append(row); continue
            change = incidence_changes(patch, nv, parent_codes, parent_counts, parent_directions,
                                       bcodes, border, boundary, census['edge_curve_ids'], curve)
            if change is None:
                row['reason'] = 'parent_edge_incidence_winding_or_origin'; trials.append(row); continue
            changes, touched = change
            assert int(left) in touched and int(right) in touched
            local = np.concatenate((faces[halo], patch)); ids, inverse = np.unique(local, return_inverse=True)
            local = inverse.reshape(-1, 3)
            conflicts, _, excluded = intersection.detect(points[ids], local)
            if len(conflicts) or len(excluded):
                row.update(reason='local_native_intersection_or_zero_area', intersection_pairs=len(conflicts), excluded=len(excluded))
                trials.append(row); continue
            fans, _ = fan_check.vertex_fans(local, len(ids))
            local_corners = np.searchsorted(ids, involved)
            if np.any(fans[local_corners] != 1):
                row['reason'] = 'complete_corner_fan'; trials.append(row); continue
            p = points[patch]; area = float(np.linalg.norm(np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]), axis=1).sum()/2)
            row.update(admitted=True, reason='local_checks_passed', area_nominal_mm2=area, touched_parent_boundary_edges=touched)
            trials.append(row); valid.append((area, diagonal, patch, changes, touched))
        if valid:
            best = min(valid, key=lambda value: (value[0], value[1]))
            proposals.append(dict(pair=pair_id, global_pair=first_global+pair_id, curve=int(curve), area=best[0], diagonal=best[1], faces=best[2], changes=best[3], touched=best[4]))
    # Complete edge budget, with a fixed order. No third edge use or conflicting winding.
    scores = census['eligible_pair_scores_squared'][census['selected_eligible_pair_indices']]
    proposals.sort(key=lambda row: (scores[row['pair']], row['area'], row['pair']))
    added, accepted, refused = {}, [], []
    for proposal in proposals:
        good = True
        for code, count, direction, old_count in proposal['changes']:
            previous, previous_direction = added.get(code, (0, None))
            good &= old_count + previous + count <= 2
            if previous and count == 1:
                good &= direction == previous_direction[::-1]
        if not good:
            refused.append(proposal['pair']); continue
        for code, count, direction, old_count in proposal['changes']:
            previous = added.get(code, (0, None))[0]; added[code] = (previous+count, direction)
        accepted.append(proposal)
    accepted.sort(key=lambda row: row['pair'])
    args.output.mkdir(mode=0o700, exist_ok=False)
    (args.output/'private-local-diagonal-trials.json').write_text(json.dumps(trials, indent=2)+'\n')
    (args.output/'private-accepted-proposals.json').write_text(json.dumps([{k:v for k,v in row.items() if k not in ('faces', 'changes')} for row in accepted], indent=2)+'\n')
    patch = np.concatenate([row['faces'] for row in accepted]) if accepted else np.empty((0, 3), dtype=np.int64)
    patch_ids = np.repeat([row['pair'] for row in accepted], 2).astype(np.int64)
    output = dict(base); output['triangles'] = np.concatenate((faces, patch))
    for key, values in base.items():
        if key in ('points', 'triangles', 'global_node_ids'):
            continue
        assert values.shape == (len(faces),), key
        new = np.full(len(patch), -1, dtype=values.dtype)
        if key == 'inferred_surface_kind':
            new[:] = 9
        elif key == 'source_patch_curve_ids':
            new[:] = 80000000+patch_ids+first_global
        output[key] = np.concatenate((values, new))
    previous_ids = base.get('source_continuation_pair_ids', np.full(len(faces), -1, dtype=np.int64))
    output['source_continuation_pair_ids'] = np.r_[previous_ids, patch_ids+first_global]
    previous_birth = base.get('continuation_birth_parent_face_rows', np.arange(len(faces)))
    output['continuation_birth_parent_face_rows'] = np.r_[previous_birth, np.full(len(patch), -1, dtype=np.int64)]
    np.savez_compressed(args.output/'candidate.npz', **output)
    with (args.output/'candidate.obj').open('w') as stream:
        for point in points:
            stream.write('v '+ ' '.join(format(float(x), '.17g') for x in point)+'\n')
        for face in output['triangles']:
            stream.write('f '+ ' '.join(str(int(x)+1) for x in face)+'\n')
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(args.output/'candidate.npz'),
                  obj_sha256=sha(args.output/'candidate.obj'), parent_mesh_sha256=sha(job['mesh']),
                  proposed_pairs=len(pairs), diagonal_trials=len(trials), local_passing_pairs=len(proposals),
                  edge_budget_refused_pair_ids=refused, accepted_pairs=len(accepted), added_triangles=len(patch),
                  local_rejection_counts=dict(Counter(row['reason'] for row in trials if not row['admitted'])),
                  source_faces_deleted=0, point_coordinates_changed=0, whole_candidate_checks_pending=True,
                  complete_halos_sha256=sha(job['complete_halos']), registry_sha256=sha(job['registry']),
                  current_global_pair_id_start=first_global, current_selected_pair_count=len(pairs),
                  assumption='unverified outward acquired windings; exploratory wall construction only',
                  physical_classifications_accepted=0, manufacturing_authorized=False, seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n'); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
