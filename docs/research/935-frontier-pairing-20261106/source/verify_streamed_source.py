"""Read-only Linux source-prefix and full edge audit from hash-checked stdin bytes."""
import hashlib
import io
import json
import os
import platform
import resource
import sys
import time


def main():
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['OMP_NUM_THREADS'] = '1'
    import numpy as np
    arrays = []
    for key in ('parent', 'candidate'):
        length = STREAM_HEADER[key+'_bytes']; assert 0 < length <= 256*1024**2
        payload = sys.stdin.buffer.read(length)
        assert len(payload) == length and hashlib.sha256(payload).hexdigest() == STREAM_HEADER[key+'_sha256']
        with np.load(io.BytesIO(payload), allow_pickle=False) as data:
            arrays.append({name:data[name] for name in data.files})
    assert not sys.stdin.buffer.read(1)
    parent, candidate = arrays; points, faces = candidate['points'], candidate['triangles']; n = len(parent['triangles'])
    assert np.array_equal(points, parent['points']) and np.array_equal(faces[:n], parent['triangles'])
    assert np.array_equal(candidate['global_node_ids'], parent['global_node_ids'])
    for key in parent:
        if key not in ('points', 'triangles', 'global_node_ids'):
            assert np.array_equal(candidate[key][:n], parent[key])
    assert faces.min() >= 0 and faces.max() < len(points)
    crosses = np.cross(points[faces[:, 1]]-points[faces[:, 0]], points[faces[:, 2]]-points[faces[:, 0]])
    assert np.all(np.any(crosses != 0, axis=1)); del crosses
    # Different edge layout from the constructor and Mac checker.
    edges = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    low, high = np.minimum(edges[:, 0], edges[:, 1]), np.maximum(edges[:, 0], edges[:, 1])
    codes = low*len(points)+high; order = np.argsort(codes, kind='stable')
    ordered = codes[order]; starts = np.r_[0, np.flatnonzero(np.diff(ordered))+1]
    counts = np.diff(np.r_[starts, len(order)])
    assert np.all((counts == 1) | (counts == 2))
    paired = starts[counts == 2]
    assert np.array_equal(edges[order[paired]], edges[order[paired+1]][:, ::-1])
    canonical = np.sort(faces, axis=1); assert len(points)**3 < 2**63
    fc = (canonical[:, 0]*len(points)+canonical[:, 1])*len(points)+canonical[:, 2]
    assert len(np.unique(fc)) == len(faces)
    report = dict(source_sha256=STREAM_HEADER['source_sha256'], parent_sha256=STREAM_HEADER['parent_sha256'],
                  candidate_sha256=STREAM_HEADER['candidate_sha256'], host=platform.node(), system=platform.system(),
                  python=platform.python_version(), numpy=np.__version__, vertices=len(points), triangles=len(faces),
                  parent_prefix_faces=n, added_triangles=len(faces)-n, source_prefix_and_provenance_exact=True,
                  whole_edge_incidence_and_winding_passed=True, no_duplicate_or_zero_area_faces=True,
                  open_boundary_edges=int(np.count_nonzero(counts == 1)), unused_vertices=len(points)-len(np.unique(faces)),
                  affinity_cpus=len(os.sched_getaffinity(0)), address_space_limit_bytes=resource.getrlimit(resource.RLIMIT_AS)[0],
                  transferred_bytes=STREAM_HEADER['parent_bytes']+STREAM_HEADER['candidate_bytes'], persistent_payload_files_written=0,
                  intersection_and_vertex_fan_replay_performed=False, physical_acceptance=False, manufacturing_authorized=False,
                  maximum_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, seconds=time.monotonic()-started)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
