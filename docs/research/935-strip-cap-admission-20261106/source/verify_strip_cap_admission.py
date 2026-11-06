"""Independently recover every admitted source-owner chain and bounded loop verdict."""
import argparse
from collections import Counter
from fractions import Fraction
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


def independent_screen(points, normals, job, simple):
    limits = job['limits']; centre = np.mean(points, axis=0)
    _, singular, axes = np.linalg.svd(points-centre, full_matrices=False)
    rank = np.count_nonzero(singular > singular.max()*max(points.shape)*np.finfo(float).eps)
    normal = axes[-1]; planar = np.max(np.abs(np.dot(points-centre, normal)))
    span = np.linalg.norm(np.max(points, axis=0)-np.min(points, axis=0)); reasons = []
    if len(points) < limits['min_edges'] or len(points) > limits['max_edges']:
        reasons.append('edge_count')
    if rank < 2:
        reasons.append('rank_below_two')
    if span > limits['max_diagonal_nominal_mm']:
        reasons.append('diagonal')
    if planar > limits['max_plane_residual_nominal_mm']:
        reasons.append('planarity')
    absolute = np.quantile(np.abs(np.dot(normals, normal)), .1)
    if absolute < limits['minimum_adjacent_normal_absolute_p10']:
        reasons.append('adjacent_normal_alignment')
    if len({tuple(point) for point in points}) != len(points):
        reasons.append('repeated_source_coordinate')
    if not reasons:
        exact = [tuple(Fraction.from_float(float(value)) for value in point) for point in points]
        area = [sum(a[(axis+1)%3]*b[(axis+2)%3]-a[(axis+2)%3]*b[(axis+1)%3] for a,b in zip(exact, exact[1:]+exact[:1])) for axis in range(3)]
        drop = max(range(3), key=lambda axis:abs(area[axis])); keep = [axis for axis in range(3) if axis != drop]
        if not area[drop] or not simple([tuple(point[axis] for axis in keep) for point in exact]):
            reasons.append('non_simple_or_zero_exact_projection')
    # Centred Newell sum avoids dependence on the scan's absolute translation.
    local = points-centre; newell = np.cross(local, np.roll(local, -1, axis=0)).sum(axis=0)
    if np.dot(normal, newell) > 0:
        normal *= -1
    signed = normals@normal; minimum, p10 = float(signed.min()), float(np.quantile(signed, .1))
    if minimum <= job['minimum_acquired_signed_normal_dot']:
        reasons.append('opposed_or_tangent_acquired_owner')
    if p10 < job['minimum_acquired_signed_normal_p10']:
        reasons.append('acquired_signed_normal_cone')
    return reasons, minimum, p10


def controls(job, simple):
    points = np.array([[0., 0., 0.], [0., 1., 0.], [1., 1., 0.], [1., 0., 0.]])
    normals = np.tile([0., 0., 1.], (4, 1))
    assert not independent_screen(points, normals, job, simple)[0]
    assert 'opposed_or_tangent_acquired_owner' in independent_screen(points, -normals, job, simple)[0]
    assert 'opposed_or_tangent_acquired_owner' in independent_screen(points[::-1], normals, job, simple)[0]
    mixed = normals.copy(); mixed[0] *= -1
    assert 'opposed_or_tangent_acquired_owner' in independent_screen(points, mixed, job, simple)[0]
    tangent = normals.copy(); tangent[0] = [1., 0., 0.]
    assert 'opposed_or_tangent_acquired_owner' in independent_screen(points, tangent, job, simple)[0]
    assert 'diagonal' in independent_screen(points*4, normals, job, simple)[0]
    return 6


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'admission', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text()); started = time.monotonic()
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    paths = (job['mesh'], job['boundaries'], job['source_arrays'], job['previous_mesh'], job['previous_boundaries'], job['pair_census'])
    mesh, boundary, raw, old_mesh, old_boundary, census = map(load, paths)
    producer = json.loads((args.admission/'report.json').read_text()); assert producer['mesh_sha256'] == sha(job['mesh'])
    expected = load(args.admission/'private-acquired-owner-references.npz')
    rows = json.loads((args.admission/'private-all-walk-decisions.json').read_text())
    assert len(rows) == len(boundary['offsets'])-1 == 1489
    spec = importlib.util.spec_from_file_location('frozen_exact_simple_polygon', job['patch_checker'])
    checker = importlib.util.module_from_spec(spec); spec.loader.exec_module(checker)
    control_count = controls(job, checker.simple_projection)
    acquired_normals = {}; refs = []; starts = [0]
    for edge_id in range(len(boundary['boundary'])):
        owner = int(boundary['owners'][edge_id]); origin = int(boundary['edge_origin_kind'][edge_id])
        if origin == 1:
            assert mesh['inferred_surface_kind'][owner] == 0
            source_ids = [int(mesh['original_face_ids'][owner])]
        elif origin == 6:
            assert mesh['inferred_surface_kind'][owner] == 4
            pair_id = int(mesh['source_frontier_pair_ids'][owner])
            source_ids = []
            for old_edge in census['selected_pair_edge_ids'][pair_id]:
                old_owner = old_boundary['boundary_face_rows'][old_edge]
                assert old_mesh['inferred_surface_kind'][old_owner] == 0
                source_ids.append(int(old_mesh['original_face_ids'][old_owner]))
        else:
            source_ids = []
        for source_id in source_ids:
            assert 0 <= source_id < len(raw['triangles'])
            if source_id not in acquired_normals:
                a, b, c = raw['vertices'][raw['triangles'][source_id]]
                normal = np.cross(b-a, c-a); assert np.linalg.norm(normal) > 0
                acquired_normals[source_id] = normal/np.linalg.norm(normal)
        refs.extend(source_ids); starts.append(len(refs))
    assert np.array_equal(starts, expected['offsets']) and np.array_equal(refs, expected['original_face_ids'])
    selected = []; scope = 0; reasons_total = Counter()
    for curve, row in enumerate(rows):
        assert row['curve'] == curve
        a, b = boundary['offsets'][curve:curve+2]; edge_ids = boundary['cycle_edges'][a:b]
        origins = set(map(int, boundary['edge_origin_kind'][edge_ids]))
        scoped = origins <= {1, 6} and 6 in origins
        assert row['eligible_scope'] == scoped and row['edges'] == len(edge_ids)
        if not scoped:
            assert not row['admitted']; continue
        scope += 1; nodes = boundary['boundary'][edge_ids, 0]
        assert np.array_equal(boundary['boundary'][edge_ids, 1], np.roll(nodes, -1))
        assert len(set(map(int, nodes))) == len(nodes)
        points = mesh['points'][nodes]; source_nodes = mesh['global_node_ids'][nodes]
        assert np.all(source_nodes < len(raw['vertices'])) and np.array_equal(points, raw['vertices'][source_nodes])
        source_ids = [source_id for edge in edge_ids for source_id in refs[starts[edge]:starts[edge+1]]]
        normals = np.array([acquired_normals[source_id] for source_id in source_ids])
        reasons, minimum, p10 = independent_screen(points, normals, job, checker.simple_projection)
        assert reasons == row['reasons'] and row['admitted'] == (not reasons)
        assert abs(minimum-row['descriptors']['minimum_acquired_signed_normal_alignment']) < 1e-9
        assert abs(p10-row['descriptors']['acquired_signed_normal_alignment_p10']) < 1e-9
        reasons_total.update(reasons)
        if not reasons:
            selected.append(curve)
    assert np.array_equal(np.load(args.admission/'private-admitted-walk-ids.npy', allow_pickle=False), selected)
    assert scope == 993 and len(selected) == producer['admitted_trials']
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)
    result = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(job['mesh']),
                  admission_sha256=sha(args.admission/'report.json'), control_cases_passed=control_count,
                  complete_boundary_owner_references_independently_recovered=len(starts)-1,
                  complete_walk_denominator=len(rows), changed_strip_border_walks_checked=scope,
                  admitted_trials=len(selected), source_owner_faces=len(acquired_normals),
                  scoped_rejection_reason_counts=dict(reasons_total), producer_imported=False,
                  admission_independently_verified=True, source_geometry_changed=False,
                  physical_acceptance=False, manufacturing_authorized=False, seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n'); print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
