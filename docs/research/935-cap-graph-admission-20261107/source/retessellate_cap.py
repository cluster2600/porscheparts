"""One constrained Lawson pass on the witness cap; private surface proposal only."""
import argparse
from collections import defaultdict, deque
from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import signal
import time

import numpy as np


def orient(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def incircle(a, b, c, d):
    x, y, z = [tuple(p[k]-d[k] for k in range(2)) for p in (a, b, c)]
    return ((x[0]**2+x[1]**2)*(y[0]*z[1]-y[1]*z[0])
            -(y[0]**2+y[1]**2)*(x[0]*z[1]-x[1]*z[0])
            +(z[0]**2+z[1]**2)*(x[0]*y[1]-x[1]*y[0]))


def edge(a, b):
    return tuple(sorted((int(a), int(b))))


def lawson(points, triangles, protected):
    """Strict exact incircle flips; fixed vertices, constrained edges and domain."""
    points = [tuple(Q.from_float(float(x)) for x in p) for p in points]
    rows = [list(map(int, t)) for t in triangles]
    assert all(orient(*(points[v] for v in t)) > 0 for t in rows)
    owners = defaultdict(set)

    def edges(t):
        return [edge(t[k], t[(k+1) % 3]) for k in range(3)]

    for r, t in enumerate(rows):
        for key in edges(t):
            owners[key].add(r)
    assert all(len(v) in (1, 2) for v in owners.values())
    queue = deque(sorted(owners)); flips = 0
    while queue:
        key = queue.popleft()
        if key in protected or len(owners[key]) != 2:
            continue
        r, s = sorted(owners[key]); a, b = key
        p, = set(rows[r])-set(key); q, = set(rows[s])-set(key)
        if orient(points[a], points[b], points[p]) < 0:
            a, b = b, a
        assert orient(points[b], points[a], points[q]) > 0
        new = [[p, a, q], [p, q, b]]
        if any(orient(*(points[v] for v in t)) <= 0 for t in new):
            continue
        if incircle(points[a], points[b], points[p], points[q]) <= 0:
            continue
        assert not owners[edge(p, q)]
        for row in (r, s):
            for old in edges(rows[row]):
                owners[old].remove(row)
        for row, t in zip((r, s), new):
            rows[row] = t
            for new_edge in edges(t):
                owners[new_edge].add(row); queue.append(new_edge)
        flips += 1
        assert flips <= 100000, 'Declared flip limit exceeded'
    return np.asarray(rows, dtype=np.int64), flips


def controls():
    points = np.array([[0., 0.], [2., 0.], [2., 1.], [0., 2.]])
    bad = np.array([[0, 1, 3], [1, 2, 3]])
    assert orient(*points[[0, 1, 2]]) == 2
    assert incircle(*[tuple(map(Q, p)) for p in points[[0, 1, 3, 2]]]) > 0
    good, count = lawson(points, bad, set())
    assert count == 1 and {tuple(sorted(t)) for t in good} == {(0, 1, 2), (0, 2, 3)}
    kept, count = lawson(points, bad, {(1, 3)})
    assert count == 0 and np.array_equal(kept, bad)
    again, count = lawson(points, good, set())
    assert count == 0 and np.array_equal(again, good)
    return {'literal_illegal_diagonal_replaced': True, 'protected_diagonal_preserved': True,
            'fixed_point_control': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); job = json.loads(args.job.read_text())
    signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(600); started = time.monotonic()
    spec = importlib.util.spec_from_file_location('cap_diagnostic', job['diagnostic'])
    diagnostic = importlib.util.module_from_spec(spec); spec.loader.exec_module(diagnostic)
    sha = diagnostic.sha
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    args.output.mkdir(mode=0o700, exist_ok=False)
    tested = controls()
    spec = importlib.util.spec_from_file_location('cap_quality', job['quality'])
    quality = importlib.util.module_from_spec(spec); spec.loader.exec_module(quality)
    with np.load(job['surface'], allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['triangles']
    tags = np.load(job['tags'], allow_pickle=False)
    witness = json.loads(Path(job['incidence']).read_text()); row = witness['source_face_row']
    assert faces[row].tolist() == witness['source_face_node_ids']
    cap = np.flatnonzero(tags == tags[row]); assert tags[row] > 0
    edge_rows = defaultdict(list)
    for r in cap:
        for k in range(3):
            edge_rows[edge(faces[r, k], faces[r, (k+1) % 3])].append(int(r))
    reached = {row}; queue = [row]
    while queue:
        r = queue.pop()
        for k in range(3):
            for neighbor in edge_rows[edge(faces[r, k], faces[r, (k+1) % 3])]:
                if neighbor not in reached:
                    reached.add(neighbor); queue.append(neighbor)
    source_rows = np.asarray(sorted(reached)); old = faces[source_rows]
    used, inverse = np.unique(old, return_inverse=True); points = vertices[used]
    old = inverse.reshape(-1, 3)
    with np.load(job['mapping'], allow_pickle=False) as data:
        mapping, retained = data['mapping'], data['used_source_vertices']
    inverse = np.full(len(mapping), -1, dtype=np.int64); inverse[retained] = np.arange(len(retained))
    original = np.load(job['features'], allow_pickle=False)
    marked = inverse[mapping[np.column_stack((original//len(mapping), original % len(mapping)))]]
    protected = {edge(a, b) for a, b in marked if a != b}
    local = {int(v): i for i, v in enumerate(used)}
    protected_local = {edge(local[a], local[b]) for a, b in protected if a in local and b in local}
    # The largest projected old face defines a stable diagnostic graph plane.
    xyz = points[old]; normals = np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0])
    base_row, axis = np.unravel_index(np.abs(normals).argmax(), normals.shape)
    axes = [(axis+1) % 3, (axis+2) % 3]
    if normals[base_row, axis] < 0:
        axes.reverse()
    projected = points[:, axes]
    new, flips = lawson(projected, old, protected_local)
    payload = args.output/'private-cap-proposal.npz'
    np.savez_compressed(payload, vertices=points, old_triangles=old, new_triangles=new,
                        source_node_ids=used, source_face_rows=source_rows, protected_edges=np.asarray(sorted(protected_local), dtype=np.int64).reshape(-1, 2),
                        projection_axes=np.asarray(axes), graph_base_row=np.asarray(base_row))
    old_q = [quality.quality_squared(points[t]) for t in old]
    new_q = [quality.quality_squared(points[t]) for t in new]
    necessary, warning = Q.from_float(.01)**3, Q.from_float(.01)**2
    report = dict(schema='935-cap-lawson-proposal-1', source_sha256=sha(__file__), job_sha256=sha(args.job),
        controls=tested, cap_tag=int(tags[row]), cap_component_triangles=len(old), cap_component_vertices=len(used),
        constrained_edges=len(protected_local), exact_strict_flips=flips,
        old_forcing_face_count=sum(q < necessary for q in old_q),
        new_forcing_face_count=sum(q < necessary for q in new_q),
        old_warning_face_count=sum(q < warning for q in old_q), new_warning_face_count=sum(q < warning for q in new_q),
        old_min_q_squared=float(min(old_q)), new_min_q_squared=float(min(new_q)),
        private_cap_proposal_sha256=sha(payload), source_surface_sha256=sha(job['surface']),
        complete_head_mesh_modified=False, independent_surface_check_pending=True,
        volume_remesh_admitted=False, physics_admitted=False, manufacturing_qualified=False,
        new_paid_compute_usd=0, seconds=time.monotonic()-started)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    signal.alarm(0); print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
