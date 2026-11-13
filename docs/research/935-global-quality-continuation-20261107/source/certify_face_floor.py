#!/usr/bin/env python3
"""Certify a fixed boundary triangle's sharp upper bound on tet mean ratio."""
import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def tetra_face_bound(points, exact):
    """Return exact q_tet^3 <= q_face^2 and the factorized geometric gap."""
    assert np.shape(points) == (4, 3)
    p = [tuple(Q.from_float(float(x)) for x in row) for row in points]
    u, v, w = (exact.difference(p[k], p[0]) for k in (1, 2, 3))
    normal = exact.product(u, v)
    n2 = exact.inner(normal, normal)
    determinant = exact.inner(normal, w)
    assert n2 > 0 and determinant != 0
    length = sum(exact.inner(exact.difference(p[a], p[b]), exact.difference(p[a], p[b]))
                 for a, b in ((0, 1), (1, 2), (2, 0)))
    edge_sum = sum(exact.inner(exact.difference(p[a], p[b]), exact.difference(p[a], p[b]))
                   for a, b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)))
    offset = tuple(w[k]-(u[k]+v[k])/3 for k in range(3))
    radius2 = exact.inner(offset, offset)
    assert exact.inner(normal, offset) == determinant
    assert edge_sum == 4*length/3+3*radius2
    assert determinant**2 <= n2*radius2
    ratio = 9*radius2/(2*length)
    assert ratio >= 0
    polynomial_gap = (ratio+2)**3-27*ratio
    assert polynomial_gap == (ratio-1)**2*(ratio+8) >= 0
    assert edge_sum**3-36*radius2*length**2 == 8*length**3*polynomial_gap/27
    q_face_squared = 12*n2/length**2
    q_tet_cubed = 432*determinant**2/edge_sum**3
    assert 0 < q_tet_cubed <= q_face_squared <= 1
    return {'q_face_squared': q_face_squared, 'q_tet_cubed': q_tet_cubed,
            'polynomial_gap': polynomial_gap, 'determinant': determinant}


def controls(exact):
    regular = np.array([[0., 0, 0], [1., 0, 1], [1., 1, 0], [0., 1, 1]])
    sharp = tetra_face_bound(regular, exact)
    assert sharp['q_face_squared'] == sharp['q_tet_cubed'] == 1
    assert sharp['polynomial_gap'] == 0
    translated = tetra_face_bound(8*regular+16, exact)
    assert translated['q_face_squared'] == translated['q_tet_cubed'] == 1
    right = tetra_face_bound([[0., 0, 0], [1., 0, 0], [0., 1, 0], [0., 0, 1]], exact)
    assert right['q_face_squared'] == Q(3, 4) and right['q_tet_cubed'] == Q(16, 27)
    try:
        tetra_face_bound([[0., 0, 0], [1., 0, 0], [2., 0, 0], [0., 0, 1]], exact)
    except AssertionError:
        pass
    else:
        raise AssertionError('Collinear base accepted')
    return {'literal_regular_tet_sharp_bound': True, 'scale_translation_invariant': True,
            'literal_right_tet_fraction': True, 'collinear_base_refused': True}


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
    spec = importlib.util.spec_from_file_location('face_bound_fraction_primitives', job['exact'])
    exact = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exact)
    tested = controls(exact)
    (args.output/'controls.json').write_text(json.dumps(tested, indent=2)+'\n')
    volume = json.loads(Path(job['volume_report']).read_text())
    proof = json.loads(Path(job['proof_report']).read_text())
    witness = json.loads(Path(job['witness']).read_text())
    witness_report = json.loads(Path(job['witness_report']).read_text())
    assert sha(job['mesh']) == proof['candidate_volume_sha256'] == volume['mesh_sha256']
    assert volume['all_cells_positive_for_stored_binary_coordinates']
    assert volume['actual_complete_boundary_and_orientation_exact']
    assert sha(job['surface']) == proof['candidate_surface_sha256'] == witness_report['input_surface_sha256']
    assert sha(job['tags']) == witness_report['input_tags_sha256']
    assert sha(job['witness']) == witness_report['private_witness_sha256']
    with np.load(job['mesh'], allow_pickle=False) as data:
        nodes, cells, boundary = data['nodes'], data['tets'], data['boundary']
    with np.load(job['surface'], allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['triangles']
    assert np.array_equal(boundary, faces)
    assert np.array_equal(nodes[:len(vertices)].view(np.uint64), vertices.view(np.uint64))
    del boundary
    tags = np.load(job['tags'], allow_pickle=False)
    row = witness['row']
    assert isinstance(row, int) and 0 <= row < len(faces)
    assert np.array_equal(faces[row], witness['vertices']) and tags[row] > 0
    face = faces[row]
    incidents = []
    for start in range(0, len(cells), 100000):
        block = cells[start:start+100000]
        mask = np.ones(len(block), dtype=bool)
        for node in face:
            mask &= (block == node).any(axis=1)
        incidents.extend((start+np.flatnonzero(mask)).tolist())
    assert len(incidents) == 1
    cell = cells[incidents[0]]
    apex, = [int(node) for node in cell if node not in face]
    result = tetra_face_bound(nodes[[*map(int, face), apex]], exact)
    assert result['determinant'] < 0, 'Boundary orientation disagrees with inward apex'
    assert result['q_face_squared'] == Q(*map(int, witness_report['exact_witness_q_squared']))
    floor = Q.from_float(volume['diagnostic_mean_ratio_floor'])
    assert floor == Q.from_float(.01)
    assert result['q_tet_cubed'] <= result['q_face_squared'] < floor**3
    private = args.output/'private-incidence.json'
    private.write_text(json.dumps({'source_face_row':row, 'incident_cell_id':incidents[0],
                                   'source_face_node_ids':face.tolist()}, indent=2)+'\n')
    report = dict(schema='935-fixed-face-quality-bound-1', source_sha256=sha(__file__),
        job_sha256=sha(args.job), controls=tested, input_mesh_sha256=sha(job['mesh']),
        input_surface_sha256=sha(job['surface']), source_cap_tag=int(tags[row]),
        all_source_cells_scanned=len(cells), complete_boundary_incidence_count=1,
        exact_face_q_squared=[str(result['q_face_squared'].numerator), str(result['q_face_squared'].denominator)],
        exact_actual_incident_tet_q_cubed=[str(result['q_tet_cubed'].numerator), str(result['q_tet_cubed'].denominator)],
        approximate_sharp_upper_bound_q_tet=float(result['q_face_squared'])**(1/3),
        current_absolute_mean_ratio_floor=float(floor),
        fixed_triangle_incompatible_with_current_tet_floor=True,
        proof_scope='Any tetrahedral partition retaining this literal boundary triangle; no claim about retessellated surfaces or polyhedral cells',
        does_not_prove_cap_vertices_coplanar=True, physical_interface_identity_established=False,
        private_incidence_sha256=sha(private), geometry_modified=False, threshold_changed=False,
        field_solve_executed=False, manufacturing_qualified=False, new_paid_compute_usd=0,
        seconds=time.monotonic()-started)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
