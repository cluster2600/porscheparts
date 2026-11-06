"""One deterministic source-corner disk proposal, before independent acceptance."""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def first_disk(size, legal):
    allowed = frozenset(map(tuple, legal))
    @lru_cache(None)
    def solve(i, j):
        if j == i+1:
            return ()
        for k in range(i+1, j):
            if (i, k, j) not in allowed:
                continue
            left, right = solve(i, k), solve(k, j)
            if left is not None and right is not None:
                return ((i, j, k),)+left+right
        return None
    result = solve(0, size-1)
    assert result is not None and len(result) == size-2
    return np.asarray(result, dtype=np.int64)


def compose(parent, patch, walk):
    n = len(parent['triangles'])
    assert not np.any(parent['inferred_surface_kind'] == 10)
    assert 'source_nonplanar_cap_curve_ids' not in parent
    result = dict(parent)
    result['triangles'] = np.concatenate((parent['triangles'], patch))
    for key, values in parent.items():
        if key in ('points', 'triangles', 'global_node_ids'):
            continue
        assert values.shape == (n,)
        new = np.full(len(patch), -1, dtype=values.dtype)
        if key == 'inferred_surface_kind':
            new[:] = 10
        if key == 'source_patch_curve_ids':
            assert not np.any(values == 70000000+walk)
            new[:] = 70000000+walk
        result[key] = np.concatenate((values, new))
    result['source_nonplanar_cap_curve_ids'] = np.r_[np.full(n, -1, dtype=np.int64), np.full(len(patch), walk, dtype=np.int64)]
    result['nonplanar_cap_immediate_parent_face_rows'] = np.r_[np.arange(n), np.full(len(patch), -1, dtype=np.int64)]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('job', 'output'):
        parser.add_argument('--'+key, required=True, type=Path)
    args = parser.parse_args()
    began = time.monotonic()
    job = json.loads(args.job.read_text())
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    assert job['construction_policy'] == 'first_lexicographic_feasible_source_corner_disk_once_v1'
    proof = json.loads(Path(job['necessary_proof']).read_text())
    assert proof['nonplanar_boundary_necessary_conditions_independently_verified']
    assert proof['mesh_sha256'] == sha(job['mesh'])
    controls = json.loads(Path(job['native_control_proof']).read_text())
    assert controls['native_nonplanar_controls_passed']
    rows = json.loads((Path(job['audit'])/'private-walk-results.json').read_text())
    selected = [r for r in rows if r['necessary_conditions_passed']]
    assert len(selected) == 1, 'This bounded construction job admits exactly one source disk.'
    row = selected[0]
    data = Path(job['audit'])/row['private_file']
    assert sha(data) == row['private_sha256']
    with np.load(data, allow_pickle=False) as z:
        nodes, legal = z['nodes'], z['allowed_triangles']
    local = first_disk(len(nodes), legal)
    parent = dict(np.load(job['mesh'], allow_pickle=False))
    patch = nodes[local]
    candidate = compose(parent, patch, row['walk'])
    args.output.mkdir(mode=0o700, exist_ok=False)
    np.savez_compressed(args.output/'candidate.npz', **candidate)
    np.savez_compressed(args.output/'private-patch.npz', triangles=patch, local_triangles=local,
                        parent_boundary_walk=np.array(row['walk']), parent_boundary_nodes=nodes)
    with (args.output/'candidate.obj').open('x') as stream:
        for point in candidate['points']:
            stream.write('v '+' '.join(format(float(x), '.17g') for x in point)+'\n')
        for face in candidate['triangles']:
            stream.write('f '+' '.join(str(int(x)+1) for x in face)+'\n')
    result = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(job['mesh']),
                  candidate_sha256=sha(args.output/'candidate.npz'), obj_sha256=sha(args.output/'candidate.obj'),
                  patch_sha256=sha(args.output/'private-patch.npz'), selected_walks=1,
                  added_triangles=len(patch), new_vertices=0, independent_whole_surface_checks_pending=True,
                  geometry_proposal_only=True, candidate_accepted=False, manufacturing_authorized=False,
                  seconds=time.monotonic()-began)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
