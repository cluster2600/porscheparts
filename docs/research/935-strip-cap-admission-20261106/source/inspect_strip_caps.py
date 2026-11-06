"""Independently inspect native cap masks against complete parent incident fans."""
import argparse
from collections import Counter, defaultdict
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
        return {key:data[key] for key in data.files}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'prepared', 'constructed', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text()); started = time.monotonic()
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    body, boundary = load(job['mesh']), load(job['boundaries'])
    preparation = json.loads((args.prepared/'report.json').read_text())
    raw = json.loads((args.constructed/'report.json').read_text())
    assert preparation['job_sha256'] == raw['job_sha256'] == sha(job['construction_job'])
    assert raw['all_owned_children_reaped'] and len(raw['trials']) == preparation['complete_target_denominator']
    checker = module(job['patch_checker'], 'frozen_cap_checker')
    detector = module(job['intersection_helper'], 'frozen_cap_intersections')
    fans = module(job['fan_helper'], 'frozen_cap_vertex_fans')
    metadata = {row['curve']:row for row in preparation['private_targets']}
    flag = np.zeros(len(body['points']), dtype=bool)
    for curve in metadata:
        a, b = boundary['offsets'][curve:curve+2]; ids = boundary['cycle_edges'][a:b]
        flag[boundary['boundary'][ids, 0]] = True
    incident = defaultdict(set)
    for face_row in np.flatnonzero(flag[body['triangles']].any(axis=1)):
        for node in body['triangles'][face_row]:
            if flag[node]:
                incident[int(node)].add(int(face_row))
    args.output.mkdir(mode=0o700, exist_ok=False); results = []
    for trial in raw['trials']:
        curve = trial['curve']; row = metadata[curve]; name = 'curve-'+str(curve).zfill(4); path = args.prepared/name
        assert sha(path/'input.obj') == row['input_OBJ_sha256'] and sha(path/'private-halo-map.npz') == row['halo_map_sha256']
        mapping = load(path/'private-halo-map.npz'); a, b = boundary['offsets'][curve:curve+2]; ids = boundary['cycle_edges'][a:b]
        nodes = boundary['boundary'][ids, 0]
        assert np.array_equal(mapping['parent_boundary_edge_ids'], ids)
        assert np.array_equal(mapping['parent_boundary_edge_origins'], boundary['edge_origin_kind'][ids])
        assert 6 in mapping['parent_boundary_edge_origins'] and set(map(int, mapping['parent_boundary_edge_origins'])) <= {1, 6}
        expected_halo = sorted({owner for node in nodes for owner in incident[int(node)]})
        assert np.array_equal(mapping['body_face_rows'], expected_halo)
        assert np.array_equal(mapping['points'], body['points'][mapping['source_body_vertex_ids']])
        assert np.array_equal(mapping['source_body_vertex_ids'][mapping['triangles']], body['triangles'][expected_halo])
        assert np.array_equal(mapping['source_body_vertex_ids'][mapping['expected_source_boundary_edges']], boundary['boundary'][ids])
        assert np.array_equal(mapping['original_global_hole_nodes'], body['global_node_ids'][nodes])
        source_points, source_faces = checker.read_obj(path/'input.obj')
        assert np.array_equal(source_points, mapping['points']) and np.array_equal(source_faces, mapping['triangles'])
        output = args.constructed/name/'candidate.obj'
        if trial['exit_code'] != 0 or not output.is_file():
            results.append(dict(curve=curve, accepted=False, reason='native_constructor_refusal')); continue
        assert sha(output) == trial['output_OBJ_sha256']
        try:
            points, faces = checker.read_obj(output)
            added, checks = checker.check_patch(source_points, source_faces, mapping['ordered_hole_nodes'], mapping['expected_source_boundary_edges'], points, faces)
            global_faces = mapping['source_body_vertex_ids'][faces]
            used, inverse = np.unique(global_faces, return_inverse=True); local_faces = inverse.reshape(-1, 3)
            pairs, _, excluded = detector.detect(body['points'][used], local_faces)
            assert not len(pairs) and not len(excluded), 'local_intersection_or_degeneracy'
            fan_counts, _ = fans.vertex_fans(local_faces, len(used))
            assert np.all(fan_counts[np.searchsorted(used, nodes)] == 1), 'local_vertex_fan'
        except (AssertionError, ValueError) as error:
            results.append(dict(curve=curve, accepted=False, reason=str(error))); continue
        patch = args.output/('private-patch-'+str(curve).zfill(4)+'.npz')
        np.savez_compressed(patch, triangles=mapping['source_body_vertex_ids'][added], parent_curve=np.array(curve))
        results.append(dict(curve=curve, accepted=True, reason='independent_exact_mask_native_predicate_and_fan_checks_passed',
                            added_triangles=len(added), private_patch_sha256=sha(patch), checks=checks, physical_role_accepted=False))
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), construction_job_sha256=sha(job['construction_job']),
                  complete_target_denominator=len(metadata), local_patches_accepted=sum(row['accepted'] for row in results),
                  local_patches_refused=sum(not row['accepted'] for row in results),
                  rejection_reason_counts=dict(Counter(row['reason'] for row in results if not row['accepted'])), private_patch_results=results,
                  original_parent_unchanged=True, complete_parent_incident_fans_verified=True,
                  full_candidate_checks_pending=True, physical_acceptance=False, manufacturing_authorized=False, seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'private_patch_results'}), flush=True)


if __name__ == '__main__':
    main()
