"""Admit only newly subdivided, acquired-owner-supported small strip-border loops."""
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
        return {key:data[key] for key in data.files}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def acquired_references(mesh, boundary, previous_mesh, previous_boundary, census):
    result = []; offsets = [0]
    for owner, origin in zip(boundary['owners'], boundary['edge_origin_kind']):
        kind = int(mesh['inferred_surface_kind'][owner])
        if origin == 1:
            assert kind == 0 and mesh['original_face_ids'][owner] >= 0
            rows = [int(mesh['original_face_ids'][owner])]
        elif origin == 6:
            assert kind == 4
            pair = int(mesh['source_frontier_pair_ids'][owner]); assert pair >= 0
            pair_edges = census['selected_pair_edge_ids'][pair]
            old_owners = previous_boundary['boundary_face_rows'][pair_edges]
            assert np.all(previous_mesh['inferred_surface_kind'][old_owners] == 0)
            rows = list(map(int, previous_mesh['original_face_ids'][old_owners])); assert min(rows) >= 0
        else:
            rows = []
        result.extend(rows); offsets.append(len(result))
    return np.array(offsets, dtype=np.int64), np.array(result, dtype=np.int64)


def signed_alignment(points, acquired_normals):
    centred = points-points.mean(axis=0); _, _, axes = np.linalg.svd(centred, full_matrices=False)
    normal = axes[-1]
    area = np.cross(points, np.roll(points, -1, axis=0)).sum(axis=0)
    if np.dot(normal, -area) < 0:
        normal = -normal
    dot = acquired_normals@normal
    return float(dot.min()), float(np.quantile(dot, .1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text()); started = time.monotonic()
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    proof = json.loads(Path(job['parent_proof']).read_text())
    assert proof['mesh_sha256'] == sha(job['mesh']) and proof['surface_study_checks_passed']
    assert proof['whole_mesh_intersection_pairs'] == proof['nonmanifold_used_vertices'] == 0
    data, boundary, raw, old_mesh, old_boundary, census = map(load, (job['mesh'], job['boundaries'], job['source_arrays'],
                                                                   job['previous_mesh'], job['previous_boundaries'], job['pair_census']))
    old_screen = module(job['screen_helper'], 'frozen_small_loop_screen')
    exact = module(job['patch_checker'], 'frozen_simple_polygon')
    offsets, references = acquired_references(data, boundary, old_mesh, old_boundary, census)
    p = raw['vertices'][raw['triangles']]; normals = np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0])
    length = np.linalg.norm(normals, axis=1); valid = length > 0; normals[valid] /= length[valid, None]
    decisions = []; counts = Counter(); scope = 0; total_edges = 0
    for curve in range(len(boundary['offsets'])-1):
        a, b = boundary['offsets'][curve:curve+2]; edges = boundary['cycle_edges'][a:b]
        origins = set(map(int, boundary['edge_origin_kind'][edges])); reasons = []; descriptors = {}
        eligible_scope = 6 in origins and origins <= {1, 6}
        if not eligible_scope:
            reasons.append('no_new_strip_boundary' if origins == {1} else 'other_origin_not_admitted')
        else:
            scope += 1; total_edges += len(edges)
            nodes = boundary['boundary'][edges, 0]
            assert np.array_equal(boundary['boundary'][edges, 1], np.roll(nodes, -1)) and len(np.unique(nodes)) == len(nodes)
            global_ids = data['global_node_ids'][nodes]
            assert np.all(global_ids < len(raw['vertices'])) and np.array_equal(data['points'][nodes], raw['vertices'][global_ids])
            ids = np.concatenate([references[offsets[edge]:offsets[edge+1]] for edge in edges])
            assert len(ids) >= len(edges) and np.all(valid[ids])
            reasons, descriptors = old_screen.screen(data['points'][nodes], normals[ids], exact.simple_projection, job['limits'])
            minimum, p10 = signed_alignment(data['points'][nodes], normals[ids])
            descriptors.update(minimum_acquired_signed_normal_alignment=minimum, acquired_signed_normal_alignment_p10=p10,
                               acquired_owner_references=len(ids), distinct_acquired_owner_faces=len(np.unique(ids)))
            if minimum <= job['minimum_acquired_signed_normal_dot']:
                reasons.append('opposed_or_tangent_acquired_owner')
            if p10 < job['minimum_acquired_signed_normal_p10']:
                reasons.append('acquired_signed_normal_cone')
        admitted = not reasons
        counts.update(reasons)
        decisions.append(dict(curve=curve, edges=len(edges), origins=sorted(origins), eligible_scope=eligible_scope,
                              admitted=admitted, reasons=reasons, descriptors=descriptors, physical_role_accepted=False))
    assert len(decisions) == 1489 and scope == 993 and total_edges == 79232
    args.output.mkdir(mode=0o700, exist_ok=False)
    np.savez_compressed(args.output/'private-acquired-owner-references.npz', offsets=offsets, original_face_ids=references)
    (args.output/'private-all-walk-decisions.json').write_text(json.dumps(decisions, indent=2)+'\n')
    selected = np.array([row['curve'] for row in decisions if row['admitted']], dtype=np.int64)
    np.save(args.output/'private-admitted-walk-ids.npy', selected)
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(job['mesh']),
                  complete_walk_denominator=len(decisions), complete_boundary_edge_denominator=len(boundary['boundary']),
                  new_strip_border_walks=scope, new_strip_border_edges=total_edges, admitted_trials=len(selected),
                  rejection_reason_counts=dict(counts), unchanged_acquired_walks_not_retried=462, other_origin_walks_not_retried=34,
                  acquired_owner_normals_recovered_without_using_inferred_normals=True, geometry_modified=False,
                  constructor_execution_authorized_only_after_independent_admission=True, physical_classifications_accepted=0,
                  manufacturing_authorized=False, seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n'); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
