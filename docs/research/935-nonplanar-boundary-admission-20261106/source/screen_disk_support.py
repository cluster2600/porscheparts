"""Screen all independently allowed corner triangles before another disk trial."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    began = time.monotonic()
    job = json.loads(args.job.read_text())
    for r in job['inputs']:
        assert sha(r['path']) == r['sha256']
    proof = json.loads(Path(job['necessary_proof']).read_text())
    assert proof['nonplanar_boundary_necessary_conditions_independently_verified']
    assert proof['mesh_sha256'] == sha(job['mesh'])
    rejected = json.loads(Path(job['rejected_candidate_proof']).read_text())
    assert rejected['rejection_reasons'] == ['complete_patch_sampled_support_exceeds_0.25_nominal_mm']
    rows = json.loads((Path(job['audit'])/'private-walk-results.json').read_text())
    selected = [r for r in rows if r['necessary_conditions_passed']]
    assert len(selected) == 1
    row = selected[0]
    file = Path(job['audit'])/row['private_file']
    assert sha(file) == row['private_sha256']
    source = dict(np.load(file, allow_pickle=False))
    mesh = dict(np.load(job['mesh'], allow_pickle=False))
    raw = dict(np.load(job['source_arrays'], allow_pickle=False))
    triangles = mesh['points'][source['nodes'][source['allowed_triangles']]]
    weights = np.array([(i/16, j/16, (16-i-j)/16) for i in range(17) for j in range(17-i)])
    queries = np.einsum('ij,fjk->fik', weights, triangles).reshape(-1, 3)
    spec = importlib.util.spec_from_file_location('frozen_support_query', job['distance_helper'])
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    distances, nearest, closest = helper.query(queries, raw['vertices'], raw['triangles'])
    per_triangle = distances.reshape(len(triangles), len(weights))
    passed = per_triangle.max(axis=1) <= .25
    args.output.mkdir(mode=0o700, exist_ok=False)
    payload = args.output/'private-all-triangle-support.npz'
    np.savez_compressed(payload, allowed_triangles=source['allowed_triangles'], nodes=source['nodes'],
                        edge_ids=source['edge_ids'], weights=weights, query_points=queries,
                        distances=distances, nearest_original_faces=nearest, closest_points=closest,
                        sampled_support_pass=passed, worst_query_indices=per_triangle.argmax(axis=1))
    result = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), mesh_sha256=sha(job['mesh']),
                  support_payload_sha256=sha(payload), allowed_triangles=len(triangles),
                  probes_per_triangle=len(weights), complete_support_probes=len(queries),
                  sampled_support_passing_triangles=int(passed.sum()), sampled_support_refused_triangles=int((~passed).sum()),
                  maximum_sampled_distance_nominal_mm=float(distances.max()),
                  independent_exact_support_and_disk_replay_pending=True, native_closest_query_is_not_independent_proof=True,
                  geometry_modified=False, construction_admitted=False, manufacturing_authorized=False,
                  seconds=time.monotonic()-began)
    for r in job['inputs']:
        assert sha(r['path']) == r['sha256']
    (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
