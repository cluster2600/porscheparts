"""Exact integer distance witnesses and complete raw-AABB refusal certificates.

Passing probes need one exact source-triangle witness. Each refused triangle
needs one stored grid probe farther than the bound from every acquired triangle.
"""
import argparse
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def within(point, triangle, radius=.25):
    """Compare exact point-to-closed-triangle distance with a binary64 radius."""
    values = [[float(x).as_integer_ratio() for x in p] for p in [point, *triangle]]
    numerator, denominator = float(radius).as_integer_ratio()
    scale = max(denominator, *(q for p in values for _, q in p))
    q, a, b, c = [tuple(n*(scale//d) for n, d in p) for p in values]
    limit = (numerator*(scale//denominator))**2
    def subtract(x, y):
        return tuple(p-r for p, r in zip(x, y))
    def dot(x, y):
        return sum(p*r for p, r in zip(x, y))
    for x, y in ((a, b), (b, c), (c, a)):
        edge, offset = subtract(y, x), subtract(q, x)
        length, position, distance = dot(edge, edge), dot(offset, edge), dot(offset, offset)
        if distance <= limit:
            return True
        if length and 0 <= position <= length and distance*length-position**2 <= limit*length:
            return True
    u, v, w = subtract(b, a), subtract(c, a), subtract(q, a)
    uu, uv, vv, wu, wv, ww = dot(u, u), dot(u, v), dot(v, v), dot(w, u), dot(w, v), dot(w, w)
    determinant = uu*vv-uv**2
    assert determinant >= 0
    if determinant:
        x, y = wu*vv-wv*uv, wv*uu-wu*uv
        if x >= 0 and y >= 0 and x+y <= determinant:
            return ww*determinant-wu*x-wv*y <= limit*determinant
    return False


def count_disks(size, allowed):
    legal = set(map(tuple, allowed))
    @lru_cache(None)
    def count(i, j):
        if j-i == 1:
            return 1
        return sum(count(i, k)*count(k, j) for k in range(i+1, j) if (i, k, j) in legal)
    return count(0, size-1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('job', 'screen', 'output'):
        parser.add_argument('--'+key, required=True, type=Path)
    args = parser.parse_args()
    began = time.monotonic()
    job = json.loads(args.job.read_text())
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    report = json.loads((args.screen/'report.json').read_text())
    payload = args.screen/'private-all-triangle-support.npz'
    assert report['source_sha256'] == sha(job['producer_source'])
    assert report['job_sha256'] == sha(args.job) and report['support_payload_sha256'] == sha(payload)
    data = dict(np.load(payload, allow_pickle=False))
    mesh = dict(np.load(job['mesh'], allow_pickle=False))
    raw = dict(np.load(job['source_arrays'], allow_pickle=False))
    assert report['mesh_sha256'] == sha(job['mesh'])
    decisions = json.loads((Path(job['audit'])/'private-walk-results.json').read_text())
    selected = [r for r in decisions if r['necessary_conditions_passed']]
    assert len(selected) == 1
    source = dict(np.load(Path(job['audit'])/selected[0]['private_file'], allow_pickle=False))
    assert np.array_equal(data['nodes'], source['nodes'])
    assert np.array_equal(data['edge_ids'], source['edge_ids'])
    assert np.array_equal(data['allowed_triangles'], source['allowed_triangles'])
    weights = np.asarray([(i/16, j/16, k/16) for i in range(17) for j in range(17) for k in range(17)
                          if i+j+k == 16])
    assert np.array_equal(weights, data['weights']) and len(weights) == 153
    triangles = mesh['points'][data['nodes'][data['allowed_triangles']]]
    query = np.einsum('ij,fjk->fik', weights, triangles).reshape(-1, 3)
    assert np.array_equal(query, data['query_points'])
    assert len(query) == report['complete_support_probes']
    distances = data['distances'].reshape(-1, 153)
    passed = distances.max(axis=1) <= .25
    assert np.array_equal(passed, data['sampled_support_pass'])
    assert np.array_equal(distances.argmax(axis=1), data['worst_query_indices'])
    assert int(passed.sum()) == report['sampled_support_passing_triangles']
    # Every query lies in this source-corner convex hull. Outward-rounded boxes
    # retain every acquired triangle that could be within the fixed radius.
    low = np.nextafter(query.min(axis=0)-.25, -np.inf)
    high = np.nextafter(query.max(axis=0)+.25, np.inf)
    corners = raw['vertices'][raw['triangles']]
    minimum, maximum = corners.min(axis=1), corners.max(axis=1)
    retained = np.flatnonzero(np.all(maximum >= low, axis=1) & np.all(minimum <= high, axis=1))
    local_min, local_max = minimum[retained], maximum[retained]
    del corners, minimum, maximum
    pass_witnesses = 0
    refused_ids, offsets, candidate_faces = [], [0], []
    for index in range(len(triangles)):
        if passed[index]:
            for local in range(153):
                row = index*153+local
                face = int(data['nearest_original_faces'][row])
                assert 0 <= face < len(raw['triangles'])
                assert within(query[row], raw['vertices'][raw['triangles'][face]]), 'native_pass_has_no_exact_source_triangle_witness'
                pass_witnesses += 1
        else:
            local = int(data['worst_query_indices'][index])
            row = index*153+local
            q = query[row]
            qlow, qhigh = np.nextafter(q-.25, -np.inf), np.nextafter(q+.25, np.inf)
            possible = retained[np.all(local_max >= qlow, axis=1) & np.all(local_min <= qhigh, axis=1)]
            assert not any(within(q, raw['vertices'][raw['triangles'][int(face)]]) for face in possible), 'native_refusal_contradicted_by_exact_distance'
            refused_ids.append(row)
            candidate_faces.extend(map(int, possible))
            offsets.append(len(candidate_faces))
    assert pass_witnesses == int(passed.sum())*153
    assert len(refused_ids) == int((~passed).sum())
    filtered = data['allowed_triangles'][passed]
    ways = count_disks(len(data['nodes']), filtered)
    args.output.mkdir(mode=0o700, exist_ok=False)
    np.savez_compressed(args.output/'private-exact-support-certificates.npz',
                        passed_triangle_ids=np.flatnonzero(passed), refused_probe_rows=np.asarray(refused_ids, dtype=np.int64),
                        retained_global_AABB_face_ids=retained, refusal_face_offsets=np.asarray(offsets, dtype=np.int64),
                        refusal_candidate_original_faces=np.asarray(candidate_faces, dtype=np.int64))
    np.savez_compressed(args.output/'private-source-supported-disk.npz', nodes=data['nodes'], edge_ids=data['edge_ids'],
                        allowed_triangles=filtered, parent_walk=np.array(selected[0]['walk']))
    result = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(job['mesh']),
                  exact_probe_existence_witnesses=pass_witnesses, refused_triangle_global_distance_certificates=len(refused_ids),
                  complete_source_faces=len(raw['triangles']), global_AABB_retained_faces=len(retained),
                  refused_probe_exact_candidate_face_checks=len(candidate_faces), sampled_support_passing_triangles=int(passed.sum()),
                  sampled_support_refused_triangles=int((~passed).sum()), complete_source_corner_triples_screened=len(triangles),
                  complete_degree16_support_probes=len(query), source_supported_combinatorial_disk_count=str(ways),
                  exact_scalar_distance_implementation_uses_no_native_nearest_query=True,
                  supported_disk_sha256=sha(args.output/'private-source-supported-disk.npz'),
                  support_and_disk_independently_verified=True, construction_admitted=False,
                  sampled_probes_are_not_a_complete_surface_distance_bound=True, geometry_modified=False,
                  physical_acceptance=False, manufacturing_authorized=False, seconds=time.monotonic()-began)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
