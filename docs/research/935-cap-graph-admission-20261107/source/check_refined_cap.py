"""Independent complete topology, projected embedding, graph-bound and face checks."""
import argparse
from collections import Counter
from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import signal
import time

import igl
import igl.predicates
import numpy as np


def controls():
    v = np.array([[0., 0., 0.], [1., 0., 0.], [1., 1., 0.], [0., 1., 0.]])
    f = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    found, pairs, _ = igl.predicates.find_self_intersections(v, f, False)
    assert not found and len(pairs) == 0
    crossed = np.array([[0., 0., 0.], [2., 0., 0.], [1., 2., 0.],
                        [0., 1., 0.], [2., 1., 0.], [1., -1., 0.]])
    found, pairs, _ = igl.predicates.find_self_intersections(crossed, np.array([[0, 1, 2], [3, 4, 5]]), False)
    assert found and len(pairs) == 1
    return {'shared_diagonal_square_not_intersection': True, 'coplanar_crossed_triangles_detected': True}


def directed_boundary(triangles):
    directed = Counter((int(t[k]), int(t[(k+1) % 3])) for t in triangles for k in range(3))
    undirected = Counter(tuple(sorted(edge)) for edge in directed.elements())
    assert all(n in (1, 2) for n in undirected.values())
    assert all(directed[a, b] == directed[b, a] == 1 for (a, b), n in undirected.items() if n == 2)
    return {edge for edge in directed if undirected[tuple(sorted(edge))] == 1}, len(undirected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text())
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()

    def load(name):
        spec = importlib.util.spec_from_file_location('refined_cap_check_'+name, job[name])
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    helper, exact, quality = (load(name) for name in ('diagnostic', 'exact', 'quality'))
    for item in job['inputs']:
        assert helper.sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False); tested = controls()
    with np.load(job['old_cap'], allow_pickle=False) as data:
        old_v, old_f, axes = data['vertices'], data['old_triangles'], data['projection_axes'].tolist()
        protected = data['protected_edges']; source_ids, source_rows = data['source_node_ids'], data['source_face_rows']
    with np.load(job['surface'], allow_pickle=False) as data:
        assert np.array_equal(data['vertices'][source_ids].view(np.uint64), old_v.view(np.uint64))
        assert np.array_equal(data['triangles'][source_rows], source_ids[old_f])
        extent = max(Q.from_float(float(x)) for x in np.ptp(data['vertices'], axis=0))
    parent = json.loads(Path(job['parent_report']).read_text())
    assert parent['candidate_surface_sha256'] == helper.sha(job['surface'])
    parent_bound = Q.from_float(parent['composed_complete_surface_correspondence_bound_nominal_mm'])
    with np.load(job['new_cap'], allow_pickle=False) as data:
        v, f, original = data['vertices'], data['triangles'], data['original_node_rows']
        assert data['projection_axes'].tolist() == axes
        base_row = int(data['graph_base_row'])
    assert np.isfinite(v).all() and f.ndim == 2 and f.shape[1] == 3
    assert f.min() == 0 and f.max() == len(v)-1 and len(np.unique(f)) == len(v)
    assert len(original) == len(old_v) and len(np.unique(original)) == len(old_v)
    assert np.array_equal(v[original].view(np.uint64), old_v.view(np.uint64))
    old_boundary, old_edges = directed_boundary(old_f)
    new_boundary, new_edges = directed_boundary(f)
    assert {(int(original[a]), int(original[b])) for a, b in old_boundary} == new_boundary
    # shortcut: this contract covers this 277-point cap; re-audit other caps.
    assert len(new_boundary) == len(old_v) == 277
    all_edges = {tuple(sorted((int(t[k]), int(t[(k+1) % 3])))) for t in f for k in range(3)}
    assert all(tuple(sorted((int(original[a]), int(original[b])))) in all_edges for a, b in protected)
    components, _ = igl.facet_components(f); assert components == 1
    assert np.all(igl.is_vertex_manifold(f)) and len(v)-new_edges+len(f) == 1
    # Every projected facet must be positive, with the same literal boundary.
    projected = np.zeros_like(v); projected[:, :2] = v[:, axes]
    p = [[Q.from_float(float(x)) for x in row] for row in v]
    for a, b, c in np.vstack((f, original[old_f])):
        assert ((p[b][axes[0]]-p[a][axes[0]])*(p[c][axes[1]]-p[a][axes[1]])
                -(p[b][axes[1]]-p[a][axes[1]])*(p[c][axes[0]]-p[a][axes[0]])) > 0
    found, pairs, coplanar = igl.predicates.find_self_intersections(projected, np.ascontiguousarray(f), False)
    assert not found and len(pairs) == 0
    old_found, old_pairs, _ = igl.predicates.find_self_intersections(
        np.ascontiguousarray(projected[original]), np.ascontiguousarray(old_f), False)
    assert not old_found and len(old_pairs) == 0
    # Both embedded disks cover the same projected polygon. Relative to any
    # common affine graph, both interpolants lie in the union vertex range.
    base = [[Q.from_float(float(x)) for x in row] for row in old_v[old_f[base_row]]]
    normal = exact.product(exact.difference(base[1], base[0]), exact.difference(base[2], base[0]))
    missing, = set(range(3))-set(axes); assert normal[missing] != 0
    offset = exact.inner(normal, base[0])
    residual = [point[missing]-(offset-sum(normal[k]*point[k] for k in axes))/normal[missing] for point in p]
    delta = max(residual)-min(residual)
    assert delta <= Q(512, 1 << 52)*extent and parent_bound+delta < Q.from_float(.01)
    old_q = [quality.quality_squared(old_v[t]) for t in old_f]
    new_q = [quality.quality_squared(v[t]) for t in f]
    threshold = Q.from_float(.01)**2
    warnings = sum(q < threshold for q in new_q)
    detail = args.output/'private-exact-certificate.json'
    detail.write_text(json.dumps({'graph_deviation': str(delta), 'composed_bound': str(parent_bound+delta),
        'minimum_face_q_squared': str(min(new_q)), 'source_face_rows': source_rows.tolist()}, indent=2)+'\n')
    report = dict(schema='935-refined-cap-independent-check-1', source_sha256=helper.sha(__file__),
        job_sha256=helper.sha(args.job), controls=tested, old_vertices=len(old_v), new_vertices=len(v),
        old_triangles=len(old_f), new_triangles=len(f), boundary_edges=len(new_boundary),
        all_original_point_bits_preserved=True, literal_oriented_contour_preserved=True,
        every_mapped_protected_cap_edge_preserved=True, connected_components=components,
        vertex_manifold=True, euler_characteristic=1, projected_intersection_pairs=len(pairs),
        all_projected_triangles_exactly_positive=True,
        complete_graph_deviation_nominal_mm_upper=helper.upper(delta),
        composed_hypothesis_correspondence_nominal_mm_upper=helper.upper(parent_bound+delta),
        old_min_face_q_squared=float(min(old_q)), new_min_face_q_squared=float(min(new_q)),
        old_forcing_face_count=sum(q < Q.from_float(.01)**3 for q in old_q),
        new_forcing_face_count=sum(q < Q.from_float(.01)**3 for q in new_q),
        old_warning_face_count=sum(q < threshold for q in old_q), new_warning_face_count=warnings,
        cap_surface_graph_checks_passed=True, all_cap_faces_clear_warning=warnings == 0,
        private_exact_certificate_sha256=helper.sha(detail), new_cap_sha256=helper.sha(job['new_cap']),
        full_head_modified=False, full_head_intersections_checked=False, volume_remesh_admitted=False,
        native_msh_readback_verified=False, physics_admitted=False, manufacturing_qualified=False,
        new_paid_compute_usd=0, seconds=time.monotonic()-started)
    for item in job['inputs']:
        assert helper.sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
