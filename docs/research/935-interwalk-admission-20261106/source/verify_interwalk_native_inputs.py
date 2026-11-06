"""Native annular-band, exact two-walk incidence and inherited mask controls."""
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
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def controls(job):
    inherited = module(job['native_control_helper'], 'inherited_native_mask_controls')
    count = inherited.controls(job)
    checker = module(job['census_inspector'], 'annular_topology_control')
    constructor = module(job['constructor_source'], 'two_walk_constructor_control')
    intersection = module(job['intersection_helper'], 'annular_native_intersections')
    fans = module(job['fan_helper'], 'annular_native_fans')
    topology = module(job['boundary_helper'], 'annular_incidence_table')
    n = 16
    theta = np.arange(n)*2*np.pi/n
    points = np.concatenate([np.c_[r*np.cos(theta), r*np.sin(theta), np.full(n, z)]
                             for r, z in ((1., 0.), (1., 1.), (.8, 0.), (.8, 1.))])
    faces = []
    for i in range(n):
        j = (i+1) % n
        faces.extend(((i, j, n+j), (i, n+j, n+i),
                      (2*n+i, 3*n+j, 2*n+j), (2*n+i, 3*n+i, 3*n+j),
                      (i, 2*n+j, j), (i, 2*n+i, 2*n+j)))
    faces = np.array(faces)
    boundary = checker.fixture_boundary(faces)
    edges = boundary['boundary']
    curves = np.empty(len(edges), dtype=np.int64)
    for curve, (a, b) in enumerate(zip(boundary['offsets'][:-1], boundary['offsets'][1:])):
        curves[boundary['cycle_edges'][a:b]] = curve
    left = next(i for i, edge in enumerate(edges) if set(edge) == {n, n+1})
    right = next(i for i, edge in enumerate(edges) if set(edge) == {3*n, 3*n+1})
    a, b = edges[left]; c, d = edges[right]
    patch = np.array([[b, a, d], [b, d, c]])
    all_edges, order, first, codes, uses = topology.table(faces, len(points))
    border_codes = edges.min(axis=1)*len(points)+edges.max(axis=1)
    border_order = np.argsort(border_codes)
    boundary['edge_origin_kind'] = np.ones(len(edges), dtype=np.int8)
    def admit(allowed):
        return constructor.incidence_changes(patch, len(points), codes, uses, all_edges[order[first]],
            border_codes[border_order], border_order, boundary, curves, allowed)
    result = admit([curves[left], curves[right]])
    assert result is not None and result[1] == sorted([left, right])
    assert admit(curves[left]) is None and admit(curves[right]) is None
    boundary['edge_origin_kind'][right] = 9
    assert admit([curves[left], curves[right]]) is None
    full = np.concatenate((faces, patch))
    conflicts, _, excluded = intersection.detect(points, full)
    assert len(conflicts) == len(excluded) == 0
    fan_counts, _ = fans.vertex_fans(full, len(points))
    assert np.all(fan_counts == 1)
    _, certificate = checker.vertex_components(full, len(points), checker.fixture_boundary(full))
    assert certificate.tolist() == [[64, 163, 98, 1, -1, 1]]
    return dict(inherited_native_mask_incidence_controls=count,
        different_walk_material_band_native_intersections_and_fans=True,
        exact_target_two_walk_incidence=True, either_single_walk_refused=True,
        inferred_boundary_edge_refused=True, actual_annular_boundary_Euler_genus_verified=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    for row in job['inputs']:
        assert sha(row['path']) == row['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job),
        controls=controls(job), native_inputs_admitted=True,
        full_scan_geometry_not_yet_accepted=True, physical_acceptance=False, manufacturing_authorized=False)
    args.output.mkdir(mode=0o700, exist_ok=False)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
