"""Read-only bounded cap-diagonal study; never author a replacement mesh."""
import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import signal
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def quad_graph(points, exact, quality):
    """Bound two graph triangulations of a strictly convex projected quad."""
    assert np.shape(points) == (4, 3) and np.isfinite(points).all()
    p = [tuple(Q.from_float(float(x)) for x in row) for row in points]
    triangles = [(0, 1, 2), (1, 0, 3), (2, 0, 3), (2, 3, 1)]
    normals = [exact.product(exact.difference(p[b], p[a]), exact.difference(p[c], p[a]))
               for a, b, c in triangles]
    axis = max(range(3), key=lambda k: abs(normals[0][k]))
    convex = all(n[axis]*normals[0][axis] > 0 for n in normals)
    if not convex:
        return {'strictly_convex_projection': False}
    determinant = exact.inner(normals[0], exact.difference(p[3], p[0]))
    # Subtract the first old face's affine graph. Both interpolants stay within
    # the four vertex residuals, so their vertical separation is at most this.
    deviation = abs(determinant/normals[0][axis])
    cosine = 1-Q(1, 1 << 40)
    same_normals = all(exact.inner(a, b) > 0 and
                       exact.inner(a, b)**2 >= cosine**2*exact.inner(a, a)*exact.inner(b, b)
                       for a in normals[:2] for b in normals[2:])
    values = [quality.quality_squared(np.asarray(points)[list(t)]) for t in triangles]
    return {'strictly_convex_projection': True, 'exactly_coplanar': determinant == 0,
            'deviation': deviation, 'signed_quad_volume': determinant/6,
            'normal_cosine_contract': same_normals,
            'old_min_q_squared': min(values[:2]), 'new_min_q_squared': min(values[2:])}


def controls(exact, quality):
    square = np.array([[0., 0., 0.], [1., 1., 0.], [1., 0., 0.], [0., 1., 0.]])
    planar = quad_graph(square, exact, quality)
    assert planar['strictly_convex_projection'] and planar['deviation'] == 0
    assert planar['old_min_q_squared'] == planar['new_min_q_squared'] == Q(3, 4)
    lifted = square.copy(); lifted[3, 2] = 2.**-48
    nonplanar = quad_graph(lifted, exact, quality)
    assert not nonplanar['exactly_coplanar'] and nonplanar['deviation'] == Q(1, 1 << 48)
    assert nonplanar['normal_cosine_contract']
    concave = square.copy(); concave[3] = [.75, .25, 0.]
    assert not quad_graph(concave, exact, quality)['strictly_convex_projection']
    steep = square.copy(); steep[3, 2] = 1.
    assert not quad_graph(steep, exact, quality)['normal_cosine_contract']
    return {'square_exact_quality_and_zero_bound': True, 'dyadic_lift_exact_bound': True,
            'concave_projection_refused': True, 'large_normal_change_refused': True}


def upper(value):
    return math.nextafter(float(value), math.inf) if value else 0.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600)
    started = time.monotonic(); job = json.loads(args.job.read_text())
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)

    def load(name):
        spec = importlib.util.spec_from_file_location('cap_graph_'+name, job[name])
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    exact, quality, bound = (load(name) for name in ('exact', 'quality', 'bound'))
    tested = controls(exact, quality)
    witness_report = json.loads(Path(job['witness_report']).read_text())
    assert witness_report['input_mesh_sha256'] == sha(job['mesh'])
    assert witness_report['input_surface_sha256'] == sha(job['surface'])
    assert witness_report['private_neighborhood_sha256'] == sha(job['neighborhood'])
    neighborhoods = json.loads(Path(job['neighborhood']).read_text())
    with np.load(job['mesh'], allow_pickle=False) as data:
        nodes, cells = data['nodes'], data['tets']
    with np.load(job['surface'], allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['triangles']
    assert np.array_equal(nodes[:len(vertices)].view(np.uint64), vertices.view(np.uint64))
    tags = np.load(job['tags'], allow_pickle=False)
    selected = sorted({x for item in neighborhoods for key in ('old_edge', 'alternate_edge') for x in item[key]})
    # Recover literal coordinate ancestry, rather than treating a cap tag as a
    # physical plane or silently projecting the stored points onto a fit.
    with np.load(job['source_aligned'], allow_pickle=False) as data:
        aligned = data['vertices']
    ancestors = {}
    for vertex in selected:
        hits = np.flatnonzero(np.all(aligned.view(np.uint64) == nodes[vertex].view(np.uint64), axis=1))
        assert len(hits) == 1, 'Unique unchanged aligned source coordinate required'
        ancestors[vertex] = int(hits[0])
    del aligned
    frame = json.loads(Path(job['frame']).read_text())
    assert frame['source_mesh_sha256'] == sha(job['source_unaligned'])
    construction = json.loads(Path(job['construction']).read_text())
    with np.load(job['source_unaligned'], allow_pickle=False) as data:
        source_points = data['vertices'][[ancestors[v] for v in selected]]
    rotation = np.asarray(frame['rotation_rows']); offset = np.asarray(frame['translation_after_rotation_mm'])
    # Recomputing a matrix product need not reproduce a different BLAS rounding
    # path; this is a measured residual, not a claim of bitwise inversion.
    transform_error = float(np.linalg.norm(source_points@rotation.T+offset-nodes[selected], axis=1).max())
    assert transform_error < 1e-9
    profiles = []; private = []
    geometry_limit = Q(512, 1 << 52)*max(Q.from_float(float(x)) for x in np.ptp(vertices, axis=0))
    parent_bound = Q.from_float(job['parent_correspondence_bound_nominal_mm'])
    for item in neighborhoods:
        number = item['edge_profile']; previous = witness_report['profiles'][number]
        a, b = item['old_edge']; p, q = item['alternate_edge']; ids = [a, b, p, q]
        old_rows = item['old_face_rows']; cap_tag = int(tags[old_rows[0]])
        assert cap_tag > 0 and all(tags[r] == cap_tag for r in old_rows)
        assert all(set(map(int, faces[r])) == set(t) for r, t in zip(old_rows, ([a, b, p], [b, a, q])))
        graph = quad_graph(nodes[ids], exact, quality)
        profile = {'edge_profile': number, 'source_cap_tag': cap_tag,
                   'source_fit': construction[cap_tag-1]['source_fit'],
                   'stock_nominal_mm': construction[cap_tag-1]['stock_mm'],
                   'physical_datum_accepted': construction[cap_tag-1]['physical_datum_accepted'],
                   'unique_bitwise_source_ancestors': True,
                   'old_edge_unmarked': previous['old_edge_unmarked'],
                   'alternate_edge_globally_absent': previous['alternate_edge_globally_absent'],
                   'strictly_convex_projection': graph['strictly_convex_projection']}
        plane = [Q.from_float(float(x)) for x in construction[cap_tag-1]['keep_negative_halfspace_coefficients']]
        residuals = []
        for v in ids:
            sp = [Q.from_float(float(x)) for x in source_points[selected.index(v)]]
            residuals.append(abs(sum(plane[k]*sp[k] for k in range(3))+plane[3]))
        normal_l1 = sum(abs(x) for x in plane[:3]); assert normal_l1 > 0
        # L1-normalised algebraic residual is diagnostic, not Euclidean distance.
        profile['max_source_plane_l1_residual_nominal_mm_upper'] = upper(max(residuals)/normal_l1)
        possible = False
        if graph['strictly_convex_projection']:
            profile.update(exactly_coplanar=graph['exactly_coplanar'],
                max_graph_deviation_nominal_mm_upper=upper(graph['deviation']),
                signed_quad_volume_nominal_mm3=float(graph['signed_quad_volume']),
                graph_bound_passed=graph['deviation'] <= geometry_limit,
                normal_cosine_contract=graph['normal_cosine_contract'],
                old_min_face_q_squared=float(graph['old_min_q_squared']),
                new_min_face_q_squared=float(graph['new_min_q_squared']),
                new_faces_clear_warning=graph['new_min_q_squared'] >= Q.from_float(.01)**2,
                composed_bound_below_limit=parent_bound+graph['deviation'] < Q.from_float(.01))
            possible = all(profile[k] for k in ('old_edge_unmarked', 'alternate_edge_globally_absent',
                'graph_bound_passed', 'normal_cosine_contract', 'new_faces_clear_warning', 'composed_bound_below_limit'))
        old_ids = item['old_cell_ids']; outer = set(map(int, cells[old_ids].ravel()))-set(ids)
        pyramid = len(old_ids) == 2 and len(outer) == 1
        profile['two_tet_pyramid'] = pyramid
        if pyramid and graph['strictly_convex_projection']:
            apex, = outer
            assert sorted(sorted(map(int, cells[c])) for c in old_ids) == sorted(
                sorted([*map(int, faces[r]), apex]) for r in old_rows)
            new_cells = [[p, q, a, apex], [p, b, q, apex]]
            new_values = [bound.tetra_face_bound(nodes[t], exact) for t in new_cells]
            old_values = [bound.tetra_face_bound(nodes[cells[c]], exact) for c in old_ids]
            positive = all(v['determinant'] > 0 for v in new_values)
            floor = min(v['q_tet_cubed'] for v in new_values) >= Q.from_float(.01)**3
            profile.update(new_cells_positive_orientation=positive, new_cells_clear_mean_ratio_floor=floor,
                old_min_tet_q_cubed=float(min(v['q_tet_cubed'] for v in old_values)),
                new_min_tet_q_cubed=float(min(v['q_tet_cubed'] for v in new_values)))
            possible = possible and positive and floor
            private.append({'edge_profile': number, 'new_cells': new_cells,
                'exact_graph_deviation': str(graph['deviation']),
                'exact_signed_quad_volume': str(graph['signed_quad_volume'])})
        else:
            possible = False
        profile['local_metric_candidate_only'] = bool(possible)
        profiles.append(profile)
    detail = args.output/'private-diagnostics.json'
    detail.write_text(json.dumps({'source_ancestors': ancestors, 'profiles': private}, indent=2)+'\n')
    report = dict(schema='935-bounded-cap-diagonal-diagnostic-1', source_sha256=sha(__file__),
        job_sha256=sha(args.job), controls=tested, input_mesh_sha256=sha(job['mesh']),
        input_surface_sha256=sha(job['surface']), profiles=profiles, profiles_examined=len(profiles),
        local_metric_candidates=sum(p['local_metric_candidate_only'] for p in profiles),
        measured_transform_recompute_max_nominal_mm=transform_error,
        graph_deviation_limit_nominal_mm_upper=upper(geometry_limit),
        private_diagnostics_sha256=sha(detail), geometry_modified=False, candidate_exported=False,
        independent_volume_partition_verified=False, complete_new_boundary_admitted=False,
        physics_admitted=False, manufacturing_qualified=False, new_paid_compute_usd=0,
        seconds=time.monotonic()-started)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
