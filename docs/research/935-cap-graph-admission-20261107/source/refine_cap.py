"""One Gmsh 2D cap proposal with a fixed contour and added interior nodes."""
import argparse
from collections import Counter
from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import signal
import time

import gmsh
import numpy as np


def mesh_polygon(points, triangles):
    owners = Counter(tuple(sorted(map(int, (t[k], t[(k+1) % 3])))) for t in triangles for k in range(3))
    boundary = [(int(t[k]), int(t[(k+1) % 3])) for t in triangles for k in range(3)
                if owners[tuple(sorted(map(int, (t[k], t[(k+1) % 3]))))] == 1]
    successor = dict(boundary); assert len(successor) == len(boundary) == len(points)
    loop = [min(successor)]
    while successor[loop[-1]] != loop[0]:
        loop.append(successor[loop[-1]]); assert len(loop) <= len(points)
    assert len(loop) == len(points)
    sizes = np.full(len(points), np.inf)
    for a, b in boundary:
        distance = float(np.linalg.norm(points[b]-points[a])); assert distance > 0
        sizes[a] = min(sizes[a], distance); sizes[b] = min(sizes[b], distance)
    gmsh.clear(); gmsh.model.add('fixed-contour-cap')
    for i, (x, y) in enumerate(points):
        gmsh.model.geo.addPoint(float(x), float(y), 0., float(sizes[i]), i+1)
    curves = [gmsh.model.geo.addLine(a+1, b+1) for a, b in zip(loop, loop[1:]+loop[:1])]
    wire = gmsh.model.geo.addCurveLoop(curves); surface = gmsh.model.geo.addPlaneSurface([wire])
    gmsh.model.geo.synchronize()
    for tag in curves:
        gmsh.model.mesh.setTransfiniteCurve(tag, 2)
    gmsh.model.mesh.generate(2)
    labels, coordinates, _ = gmsh.model.mesh.getNodes()
    coordinates = coordinates.reshape(-1, 3); assert np.all(coordinates[:, 2] == 0)
    lookup = {int(label): i for i, label in enumerate(labels)}
    old_node_rows = []
    for tag in range(1, len(points)+1):
        ids, _, _ = gmsh.model.mesh.getNodes(0, tag); assert len(ids) == 1
        old_node_rows.append(lookup[int(ids[0])])
    old_node_rows = np.asarray(old_node_rows)
    assert np.array_equal(coordinates[old_node_rows, :2].view(np.uint64), points.view(np.uint64))
    kinds, _, element_nodes = gmsh.model.mesh.getElements(2, surface)
    assert list(kinds) == [2]
    cells = np.asarray([[lookup[int(x)] for x in row] for row in element_nodes[0].reshape(-1, 3)], dtype=np.int64)
    return coordinates[:, :2].copy(), cells, old_node_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text())
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    spec = importlib.util.spec_from_file_location('refined_cap_io', job['diagnostic'])
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    for item in job['inputs']:
        assert helper.sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.NumThreads', 1)
        gmsh.option.setNumber('Mesh.Algorithm', 6)
        gmsh.option.setNumber('Mesh.Smoothing', 0)
        square = np.array([[0., 0.], [1., 0.], [1., 1.], [0., 1.]])
        xy, tri, original = mesh_polygon(square, np.array([[0, 1, 2], [0, 2, 3]]))
        assert len(xy) > 4 and len(tri) > 2
        u, v = xy[tri[:, 1]]-xy[tri[:, 0]], xy[tri[:, 2]]-xy[tri[:, 0]]
        area = (u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0])/2
        assert np.all(area > 0) and abs(float(area.sum())-1) < 1e-12
        controls = {'literal_square_refined_with_fixed_corner_bits': True,
                    'literal_square_area_and_positive_triangles': True}
        with np.load(job['cap'], allow_pickle=False) as data:
            old_points, old_triangles = data['vertices'], data['old_triangles']
            axes, base_row = data['projection_axes'].tolist(), int(data['graph_base_row'])
        points2 = np.ascontiguousarray(old_points[:, axes])
        xy, triangles, original = mesh_polygon(points2, old_triangles)
        gmsh.option.setNumber('Mesh.Binary', 1)
        msh = args.output/'private-native-cap.msh'; gmsh.write(str(msh))
        missing, = set(range(3))-set(axes)
        base = [[Q.from_float(float(x)) for x in p] for p in old_points[old_triangles[base_row]]]
        u = [base[1][k]-base[0][k] for k in range(3)]; v = [base[2][k]-base[0][k] for k in range(3)]
        normal = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        assert normal[missing] != 0
        offset = sum(normal[k]*base[0][k] for k in range(3))
        points = np.empty((len(xy), 3)); points[:, axes] = xy
        for i, point in enumerate(xy):
            height = (offset-sum(normal[k]*Q.from_float(float(point[j])) for j, k in enumerate(axes)))/normal[missing]
            points[i, missing] = float(height)
        points[original] = old_points
        assert np.array_equal(points[original].view(np.uint64), old_points.view(np.uint64))
        path = args.output/'private-refined-cap.npz'
        np.savez_compressed(path, vertices=points, triangles=triangles, original_node_rows=original,
                            projection_axes=np.asarray(axes), graph_base_row=np.asarray(base_row))
        report = dict(schema='935-refined-cap-proposal-1', source_sha256=helper.sha(__file__),
            job_sha256=helper.sha(args.job), gmsh_version=gmsh.__version__, controls=controls,
            old_vertices=len(old_points), old_triangles=len(old_triangles),
            new_vertices=len(points), new_triangles=len(triangles), added_vertices=len(points)-len(old_points),
            contour_point_bits_preserved=True, native_msh_sha256=helper.sha(msh),
            private_refined_cap_sha256=helper.sha(path), complete_head_modified=False,
            independent_check_pending=True, physics_admitted=False, manufacturing_qualified=False,
            new_paid_compute_usd=0, seconds=time.monotonic()-started)
    finally:
        gmsh.finalize()
    for item in job['inputs']:
        assert helper.sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
