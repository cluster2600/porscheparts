"""Bounded synthetic native witness for a five-corner unequal-sampling strip."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text())
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    native = module(job['intersection_helper'], 'unequal_fixture_native')
    fans = module(job['fan_helper'], 'unequal_fixture_fans')
    topology = module(job['boundary_helper'], 'unequal_fixture_edges')
    primitive = module(job['incidence_primitive'], 'unequal_fixture_incidence')
    checker = module(job['component_checker'], 'unequal_fixture_primal')
    opposed = module(job['opposed_scalar'], 'unequal_fixture_atomic_class')
    masks = module(job['mask_helper'], 'unequal_fixture_complete_masks')
    points = np.array([[0., 0., .1], [1.2, 0., .1], [1.2, 0., -.1],
        [.6, 0., -.1], [0., 0., -.1], [0., .2, .1], [1.2, .2, .1],
        [0., .2, -.1], [1.2, .2, -.1]])
    parent = np.array([[0, 1, 6], [0, 6, 5], [2, 3, 8], [3, 4, 7], [3, 7, 8],
                       [5, 6, 8], [5, 8, 7]])
    boundary = checker.fixture_boundary(parent)
    edges = boundary['boundary']
    targets = [int(np.flatnonzero(np.all(edges == edge, axis=1))[0]) for edge in ([0, 1], [2, 3], [3, 4])]
    labels, before = checker.vertex_components(parent, len(points), boundary)
    assert np.all(labels == 0) and before.tolist() == [[9, 15, 7, 1, 1, 0]]
    q = points[parent[boundary['owners']]]
    normals = np.cross(q[:, 1]-q[:, 0], q[:, 2]-q[:, 0])
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    limits = dict(maximum_cross_endpoint_distance_nominal_mm=.5, maximum_tangent_dot=-.8,
        maximum_opposed_skin_normal_dot=-.8, maximum_material_side_gap_dot=-.8,
        minimum_outward_binormal_dot=.8, minimum_forward_wall_normal_dot=.8)
    atomic = [opposed.inspect_pair(points, edges, normals, targets[0], edge, limits)[0] for edge in targets[1:]]
    assert atomic == ['cross_endpoint_support_distance']*2
    # Literal new correspondence, not a relaxed atomic distance bound.
    assert np.linalg.norm(points[0]-points[4]) <= .5 and np.linalg.norm(points[1]-points[2]) <= .5
    projected_middle = np.array([.6, 0., .1])
    assert np.linalg.norm(points[3]-projected_middle) <= .5
    corners = [0, 1, 2, 3, 4]
    halo = np.flatnonzero(np.isin(parent, corners).any(axis=1))
    assert masks.mask_matches(parent, corners, halo)
    assert not masks.mask_matches(parent, corners, halo[:-1])
    all_edges, order, first, codes, uses = topology.table(parent, len(points))
    bc = edges.min(axis=1)*len(points)+edges.max(axis=1); border = np.argsort(bc)
    boundary['edge_origin_kind'] = np.ones(len(edges), dtype=np.int8)
    curves = np.zeros(len(edges), dtype=np.int64)
    polygon = np.array([1, 0, 4, 3, 2])
    patterns = [((0,1,2),(0,2,3),(0,3,4)), ((0,1,3),(1,2,3),(0,3,4)),
        ((0,1,4),(1,2,3),(1,3,4)), ((0,1,4),(1,2,4),(2,3,4)),
        ((0,1,2),(0,2,4),(2,3,4))]
    def incidence(patch):
        return primitive.incidence_changes(patch, len(points), codes, uses, all_edges[order[first]],
            bc[border], border, boundary, curves, 0)
    results = []
    for i, pattern in enumerate(patterns):
        patch = polygon[np.asarray(pattern)]
        xyz = points[patch]
        crosses = np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0])
        lengths = np.linalg.norm(crosses, axis=1)
        signed = bool(np.all(lengths > 0) and np.all((crosses/lengths[:, None])@np.array([0., -1., 0.]) >= .8))
        if not signed:
            results.append(dict(pattern=i, accepted=False, reason='zero_or_nonforward_triangle'))
            continue
        changed = incidence(patch)
        assert changed is not None and changed[1] == sorted(targets)
        assert incidence(patch[:, ::-1]) is None
        full = np.r_[parent, patch]
        conflicts, _, excluded = native.detect(points, full)
        assert len(conflicts) == len(excluded) == 0
        count, _ = fans.vertex_fans(full, len(points)); assert np.all(count == 1)
        _, after = checker.vertex_components(full, len(points), checker.fixture_boundary(full))
        assert after.tolist() == [[9, 19, 10, 2, 0, 0]]
        assert np.array_equal(full[:len(parent)], parent)
        results.append(dict(pattern=i, accepted=True, area_nominal_mm2=float(lengths.sum()/2),
                            component_certificate=after.tolist()))
    assert sum(row['accepted'] for row in results) == 3
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job),
        fixture='synthetic 1.2 by 0.2 by 0.2 unequal-sampling material strip',
        atomic_pairs_refused_without_threshold_change=atomic, pentagon_patterns=results,
        five_corners=True, three_old_acquired_edges_preserved=True,
        original_points_and_faces_preserved=True, complete_mask_controls_passed=True,
        new_chain_census_independently_admitted=False, annular_control_still_required=True,
        real_scan_used=False, head_geometry_changed=False, manufacturing_authorized=False)
    args.output.mkdir(mode=0o700, exist_ok=False)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
