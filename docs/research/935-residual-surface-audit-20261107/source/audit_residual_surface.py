#!/usr/bin/env python3
"""Read-only exact face-quality census of the frozen 935 peel fixed point."""
import argparse
from collections import Counter
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'), 'sha256').hexdigest()


def quality_squared(points):
    """Exact mean-ratio squared, cross-checked by Gram and Heron identities."""
    p = [[Q.from_float(float(x)) for x in row] for row in points]
    assert len(p) == 3 and all(len(row) == 3 for row in p)
    u = [p[1][k]-p[0][k] for k in range(3)]
    v = [p[2][k]-p[0][k] for k in range(3)]
    a, b, uv = sum(x*x for x in u), sum(x*x for x in v), sum(x*y for x, y in zip(u, v))
    c = sum((x-y)**2 for x, y in zip(u, v))
    assert a+b+c > 0
    gram = 12*(a*b-uv*uv)/(a+b+c)**2
    heron = 3*(2*(a*b+b*c+c*a)-a*a-b*b-c*c)/(a+b+c)**2
    assert gram == heron and 0 <= gram <= 1
    return gram


def controls():
    triangle = np.array([[0., 0, 0], [3., 0, 0], [0., 4, 0]])
    assert quality_squared(triangle) == Q(432, 625)
    assert quality_squared(triangle[[2, 0, 1]]) == Q(432, 625)
    assert quality_squared(8*triangle+16) == Q(432, 625)
    assert quality_squared([[0., 0, 0], [1., 0, 0], [0., 1, 0]]) == Q(3, 4)
    assert quality_squared([[0., 0, 0], [1., 0, 0], [2., 0, 0]]) == 0
    try:
        quality_squared(np.zeros((3, 3)))
    except AssertionError:
        pass
    else:
        raise AssertionError('Coincident triangle accepted')
    return {'literal_345_area_identity': True, 'orientation_and_similarity': True,
            'collinear_zero_and_coincident_refusal': True, 'gram_equals_heron': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(600)
    started = time.monotonic()
    args.output.mkdir(mode=0o700, exist_ok=False)

    def module(name):
        spec = importlib.util.spec_from_file_location(name, job[name])
        result = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(result)
        return result

    op, attribution, record = (module(name) for name in ('operator', 'attribution', 'record'))
    tested = {'quality': controls(), 'operator': op.controls(),
              'surface_join': attribution.controls(record.records)}
    (args.output/'controls.json').write_text(json.dumps(tested, indent=2)+'\n')
    mesh_hash = sha(job['mesh'])
    assert mesh_hash == 'fdce160bc7ec2456ab339de09733d00cd2f3cd4c6a1327e03b44c838000e0db6'
    previous = json.loads(Path(job['availability_report']).read_text())
    native = json.loads(Path(job['native_report']).read_text())
    condition = json.loads(Path(job['condition_report']).read_text())
    assert previous['input_mesh_sha256'] == native['input_sha256'] == condition['input_mesh_sha256'] == mesh_hash
    assert previous['vertex_disjoint_peels_admitted'] == 0 and not condition['physics_admitted']
    assert not native['native_positive_metric_witness_passed']
    assert native['native_metrics']['minSICN']['private_indices_sha256'] == sha(job['native_ids'])
    assert condition['private_ids_sha256'] == sha(job['severe_ids'])
    with np.load(job['mesh'], allow_pickle=False) as data:
        nodes, cells, boundary = data['nodes'], data['tets'], data['boundary']
    with np.load(job['surface'], allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['triangles']
    assert np.array_equal(boundary, faces)
    assert np.array_equal(nodes[:len(vertices)].view(np.uint64), vertices.view(np.uint64))
    del boundary
    tags = np.load(job['tags'], allow_pickle=False)
    with np.load(job['severe_ids'], allow_pickle=False) as data:
        ids = data['cell_ids']
    assert len(ids) == condition['counts_kappa_F_at_least']['1e12'] == 12811
    assert ids.ndim == 1 and ids.dtype.kind in 'iu'
    assert len(np.unique(ids)) == len(ids) and np.all((ids >= 0) & (ids < len(cells)))
    with np.load(job['native_ids'], allow_pickle=False) as data:
        native_ids = data['cell_ids']
    assert len(native_ids) == native['native_metrics']['minSICN']['nonpositive_or_nonfinite_cells'] == 868
    assert native_ids.ndim == 1 and native_ids.dtype.kind in 'iu'
    assert len(np.unique(native_ids)) == len(native_ids) and np.all((native_ids >= 0) & (native_ids < len(cells)))
    native_set = set(map(int, native_ids))
    rows, labels, _, _, caps = attribution.surface_join(cells[ids], faces, tags, len(nodes), record.records)
    with np.load(job['prior_attribution'], allow_pickle=False) as data:
        assert np.array_equal(data['cell_ids'], ids)
        assert np.array_equal(data['source_boundary_face_ids'], rows)
        assert np.array_equal(data['construction_tags'], labels)
        assert np.array_equal(data['vertex_cap_memberships'], caps)
    with np.load(job['mapping'], allow_pickle=False) as data:
        mapping, used = data['mapping'], data['used_source_vertices']
    inverse = np.full(len(mapping), -1, dtype=np.int64)
    inverse[used] = np.arange(len(used))
    marked_source = np.load(job['features'], allow_pickle=False)
    marked = inverse[mapping[np.column_stack((marked_source//len(mapping), marked_source % len(mapping)))]]
    assert np.all(marked >= 0)
    protected = {op.edge_key(edge) for edge in marked if edge[0] != edge[1]}
    bound = Q(512, 1 << 52)*max(Q.from_float(float(x)) for x in np.ptp(vertices, axis=0))
    floor, warning = Q.from_float(.01)**3, Q.from_float(.01)**2
    reasons, cross_native, quality_classes, cap_classes = Counter(), Counter(), Counter(), Counter()
    details, profile = [], []
    for position, cell_id in enumerate(ids):
        slots = np.flatnonzero(rows[position] >= 0).tolist()
        reason = 'not_two_boundary_faces'
        if len(slots) == 2:
            tet = cells[cell_id]
            if caps[position].any() or np.any(labels[position, slots] != 0):
                reason = 'construction_cap_constraint'
                cap_classes['boundary_cap' if np.any(labels[position, slots] != 0) else 'cap_vertex_only'] += 1
            else:
                diagonal = sorted(set(map(int, tet[op.FACES[slots[0]]])) & set(map(int, tet[op.FACES[slots[1]]])))
                if op.edge_key(diagonal) in protected:
                    reason = 'protected_marked_curve'
                else:
                    reason, proof = op.geometry(nodes[tet], slots, bound)
                    assert proof is None, 'Frozen zero-successor census contradicted'
                    if reason == 'triangle_quality_worsens':
                        old = [quality_squared(nodes[tet[op.FACES[k]]]) for k in slots]
                        new = [quality_squared(nodes[tet[op.FACES[k]]]) for k in range(4) if k not in slots]
                        assert 0 < min(new) < min(old)
                        old_bad, new_bad = sum(x < warning for x in old), sum(x < warning for x in new)
                        classification = ('at_or_above_floor' if min(new) >= floor else 'below_floor',
                                          'warning_count_nonincreasing' if new_bad <= old_bad else 'warning_count_increases')
                        quality_classes['/'.join(classification)] += 1
                        details.append((int(cell_id), float(min(old)), float(min(new)),
                                        float(min(new)/min(old)), old_bad, new_bad))
                        if min(new) >= floor and new_bad <= old_bad:
                            profile.append((int(cell_id), slots, diagonal,
                                            sorted(set(map(int, tet))-set(diagonal))))
        reasons[reason] += 1
        if int(cell_id) in native_set:
            cross_native[reason] += 1
    assert dict(reasons) == previous['reasons'] and sum(reasons.values()) == len(ids)
    incidence = op.incidences(cells, [edge for row in profile for edge in row[2:4]])
    skin_incidence = op.incidences(faces, [row[3] for row in profile])
    topology = Counter()
    topology_native = Counter()
    for cell_id, slots, diagonal, other in profile:
        if incidence[op.edge_key(diagonal)] != [cell_id]:
            reason = 'old_diagonal_tet_valence_not_one'
        elif skin_incidence[op.edge_key(other)]:
            reason = 'new_diagonal_already_on_surface'
        elif not op.links(cells[incidence[op.edge_key(other)]], other):
            reason = 'new_diagonal_source_link_not_simple_cycle'
        else:
            reason = 'passes_counterfactual_local_topology_only'
        topology[reason] += 1
        if cell_id in native_set:
            topology_native[reason] += 1
    metrics = np.asarray(details, dtype=np.float64).reshape(-1, 6)
    diagnostic = args.output/'private-quality-diagnostics.npz'
    np.savez_compressed(diagnostic, diagnostics=metrics, columns=np.array(
        ['cell_id', 'old_min_q_squared', 'new_min_q_squared', 'new_over_old', 'old_warning_faces', 'new_warning_faces']))
    report = dict(schema='935-residual-surface-audit-1', source_sha256=sha(__file__), job_sha256=sha(args.job),
        input_mesh_sha256=mesh_hash, controls=tested, severe_cells_examined=len(ids),
        source_surface_faces_scanned=len(faces), current_attribution_recomputed_and_equal=True,
        unchanged_operator_reasons=dict(reasons), native_nonpositive_shape_cells=len(native_ids),
        native_bad_cells_outside_severe_census=len(native_set-set(map(int, ids))),
        native_bad_by_original_refusal=dict(cross_native), cap_refusal_subclasses=dict(cap_classes),
        exact_quality_cases_examined=len(details), quality_classes=dict(quality_classes),
        counterfactual_floor_and_warning_profile_cells=len(profile),
        counterfactual_topology_only=dict(topology), counterfactual_native_topology_only=dict(topology_native),
        counterfactual_is_not_an_admitted_operator=True, global_face_quality_monotonicity_not_proved=True,
        exact_floor_fraction=[str(floor.numerator), str(floor.denominator)],
        exact_warning_fraction=[str(warning.numerator), str(warning.denominator)],
        diagnostic_quantiles_new_over_old=np.quantile(metrics[:, 3], [0, .25, .5, .75, 1]).tolist(),
        diagnostic_minimum_new_q_squared=float(metrics[:, 2].min()),
        diagnostic_maximum_new_q_squared=float(metrics[:, 2].max()),
        private_diagnostics_sha256=sha(diagnostic), geometry_modified=False, candidate_exported=False,
        printing_master_changed=False, physics_admitted=False, manufacturing_qualified=False,
        new_paid_compute_usd=0, seconds=time.monotonic()-started)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
