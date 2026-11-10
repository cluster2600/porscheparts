#!/usr/bin/env python3
"""Read-only exact neighborhood admission around the current forcing cap face."""
import argparse
from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


def patch_geometry(points, exact, quality):
    p = [tuple(Q.from_float(float(x)) for x in row) for row in points]
    normal = exact.product(exact.difference(p[1], p[0]), exact.difference(p[2], p[0]))
    determinant = exact.inner(normal, exact.difference(p[3], p[0]))
    if determinant:
        return {'exactly_coplanar': False, 'strictly_convex_common_quad': False}
    triangles = [(0, 1, 2), (1, 0, 3), (2, 0, 3), (2, 3, 1)]
    normals = [exact.product(exact.difference(p[b], p[a]), exact.difference(p[c], p[a]))
               for a, b, c in triangles]
    axis = max(range(3), key=lambda k: abs(normal[k]))
    convex = all(n[axis]*normal[axis] > 0 for n in normals)
    result = {'exactly_coplanar': True, 'strictly_convex_common_quad': convex}
    if convex:
        values = [quality.quality_squared(np.asarray(points)[list(t)]) for t in triangles]
        result.update(old_min_q_squared=values[0] if values[0] < values[1] else values[1],
                      new_min_q_squared=min(values[2:]))
    return result


def controls(exact, quality):
    square = [[0., 0, 0], [1., 1, 0], [0., 1, 0], [1., 0, 0]]
    result = patch_geometry(square, exact, quality)
    assert result['strictly_convex_common_quad']
    assert result['old_min_q_squared'] == result['new_min_q_squared'] == Q(3, 4)
    lifted = np.asarray(square); lifted[3, 2] = 2.**-44
    assert not patch_geometry(lifted, exact, quality)['exactly_coplanar']
    concave = [[0., 0, 0], [1., 0, 0], [0., 1, 0], [2., -.125, 0]]
    assert not patch_geometry(concave, exact, quality)['strictly_convex_common_quad']
    return {'literal_square_both_diagonals': True, 'noncoplanar_stored_point_refused': True,
            'concave_projected_quad_refused': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600)
    started = time.monotonic()

    def sha(path):
        import hashlib
        with Path(path).open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()

    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)

    def load(name):
        spec = importlib.util.spec_from_file_location('cap_neighborhood_'+name, job[name])
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    exact, quality, op, bound = (load(name) for name in ('exact', 'quality', 'operator', 'bound'))
    tested = controls(exact, quality)
    (args.output/'controls.json').write_text(json.dumps(tested, indent=2)+'\n')
    certificate = json.loads(Path(job['certificate']).read_text())
    witness = json.loads(Path(job['incidence']).read_text())
    assert certificate['source_sha256'] == sha(job['bound'])
    assert certificate['input_mesh_sha256'] == sha(job['mesh'])
    assert certificate['input_surface_sha256'] == sha(job['surface'])
    assert certificate['private_incidence_sha256'] == sha(job['incidence'])
    with np.load(job['surface'], allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['triangles']
    with np.load(job['mesh'], allow_pickle=False) as data:
        nodes, cells = data['nodes'], data['tets']
    assert np.array_equal(vertices.view(np.uint64), nodes[:len(vertices)].view(np.uint64))
    tags = np.load(job['tags'], allow_pickle=False)
    proof = json.loads(Path(job['proof_report']).read_text())
    assert proof['candidate_tags_sha256'] == sha(job['tags'])
    row = witness['source_face_row']; face = faces[row]
    assert face.tolist() == witness['source_face_node_ids'] and tags[row] == certificate['source_cap_tag']
    edges = [tuple(map(int, (face[i], face[(i+1) % 3]))) for i in range(3)]
    other_pairs, neighbors = [], []
    incidence = op.incidences(faces, edges)
    for edge in edges:
        rows = incidence[op.edge_key(edge)]
        assert len(rows) == 2 and row in rows
        neighbor, = [r for r in rows if r != row]
        p, = [int(x) for x in face if x not in edge]
        q, = [int(x) for x in faces[neighbor] if x not in edge]
        assert tuple(map(int, faces[neighbor])) in ((edge[1], edge[0], q), (edge[0], q, edge[1]), (q, edge[1], edge[0]))
        neighbors.append((neighbor, p, q)); other_pairs.append((p, q))
    with np.load(job['mapping'], allow_pickle=False) as data:
        mapping, used = data['mapping'], data['used_source_vertices']
    inverse = np.full(len(mapping), -1, dtype=np.int64); inverse[used] = np.arange(len(used))
    original = np.load(job['features'], allow_pickle=False)
    marked = inverse[mapping[np.column_stack((original//len(mapping), original % len(mapping)))]]
    assert np.all(marked >= 0)
    protected = {op.edge_key(edge) for edge in marked if edge[0] != edge[1]}
    tet_edges = op.incidences(cells, edges+other_pairs)
    surface_new = op.incidences(faces, other_pairs)
    profiles, private = [], []
    floor3 = Q.from_float(.01)**3
    for number, (edge, (neighbor, p, q)) in enumerate(zip(edges, neighbors)):
        quad = [*edge, p, q]
        result = patch_geometry(nodes[quad], exact, quality)
        old_cells = tet_edges[op.edge_key(edge)]
        outer = set(map(int, cells[old_cells].ravel()))-set(quad)
        pyramid = len(old_cells) == 2 and len(outer) == 1
        same_tag = bool(tags[neighbor] == tags[row])
        unmarked = op.edge_key(edge) not in protected
        absent = not tet_edges[op.edge_key((p, q))] and not surface_new[op.edge_key((p, q))]
        improved = result.get('new_min_q_squared', Q(0)) >= floor3
        surface_candidate = same_tag and unmarked and result['strictly_convex_common_quad'] and improved and absent
        new_tet_floor = None
        if surface_candidate and pyramid:
            apex, = outer
            assert all(set(map(int, faces[r])) | {apex} == set(map(int, cells[c]))
                       for r, c in zip((row, neighbor), old_cells)) or all(
                           set(map(int, faces[r])) | {apex} == set(map(int, cells[c]))
                           for r, c in zip((neighbor, row), old_cells))
            values = [bound.tetra_face_bound(nodes[t], exact)['q_tet_cubed']
                      for t in ([p, edge[0], q, apex], [p, q, edge[1], apex])]
            new_tet_floor = bool(min(values) >= floor3)
        profiles.append({'edge_profile':number, 'same_cap_tag':same_tag,
            'old_edge_unmarked':unmarked, 'exactly_coplanar':result['exactly_coplanar'],
            'strictly_convex_common_quad':result['strictly_convex_common_quad'],
            'new_faces_clear_necessary_floor':bool(improved), 'alternate_edge_globally_absent':bool(absent),
            'old_edge_tet_valence':len(old_cells), 'two_tet_pyramid':pyramid,
            'surface_candidate_only':bool(surface_candidate), 'new_tets_clear_mean_ratio_floor':new_tet_floor,
            'new_min_face_q_squared_diagnostic':float(result['new_min_q_squared']) if 'new_min_q_squared' in result else None})
        private.append({'edge_profile':number,'old_face_rows':[row,neighbor],'old_edge':list(edge),
                        'alternate_edge':[p,q],'old_cell_ids':old_cells})
    path = args.output/'private-neighborhood.json';path.write_text(json.dumps(private, indent=2)+'\n')
    report = dict(schema='935-cap-witness-neighborhood-1', source_sha256=sha(__file__), job_sha256=sha(args.job),
        controls=tested, input_mesh_sha256=sha(job['mesh']), input_surface_sha256=sha(job['surface']),
        source_cap_tag=int(tags[row]), witness_edges_examined=3, profiles=profiles,
        private_neighborhood_sha256=sha(path), geometry_modified=False, candidate_exported=False,
        current_literal_cap_face_contract_would_require_separate_change=True,
        volume_partition_independently_verified=False, physics_admitted=False, manufacturing_qualified=False,
        new_paid_compute_usd=0, seconds=time.monotonic()-started)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0);print(json.dumps(report),flush=True)


if __name__ == '__main__':
    main()
