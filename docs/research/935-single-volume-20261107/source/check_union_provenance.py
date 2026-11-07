"""Check every output triangle against its claimed input surface, without sampling."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    began = time.monotonic()
    job = json.loads(args.job.read_text())
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    tree = ast.parse(Path(job['containment_source']).read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'check_partial')
    namespace = {'np': np}
    exec(compile(ast.Module(body=[function], type_ignores=[]), job['containment_source'], 'exec'), namespace)
    check = namespace['check_partial']
    source = np.array([[[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]])
    assert check(source, source) == 0
    assert check(source+np.array([0., 0., 1.]), source) >= 1
    assert check(source+np.array([2., 0., 0.]), source) >= 1
    data = dict(np.load(job['candidate'], allow_pickle=False))
    head = dict(np.load(job['head'], allow_pickle=False))
    aux = dict(np.load(job['supports'], allow_pickle=False))
    v, f = data['vertices'], data['triangles']
    resources, ids = data['source_resource_ids'], data['source_triangle_ids']
    assert len(resources) == len(ids) == len(f) and np.all((resources >= 1) & (resources <= 1120))
    maximum = 0.
    unchanged = 0
    minimum_normal_cosine = 1.
    counts = np.zeros(1120, dtype=np.int64)
    for start in range(0, len(f), 50000):
        r, original_ids = resources[start:start+50000], ids[start:start+50000]
        q = v[f[start:start+50000]]
        original = np.empty_like(q)
        for resource in np.unique(r):
            selected = r == resource
            ii = original_ids[selected]
            if resource == 1:
                assert ii.min() >= 0 and ii.max() < len(head['triangles'])
                original[selected] = head['vertices'][head['triangles'][ii]]
            else:
                a, b = aux['vertex_offsets'][resource-2:resource]
                c, d = aux['face_offsets'][resource-2:resource]
                assert ii.min() >= 0 and ii.max() < d-c
                original[selected] = aux['vertices'][a:b][aux['triangles'][c+ii]]
            counts[resource-1] += int(selected.sum())
        exact = np.zeros(len(q), dtype=bool)
        for shift in range(3):
            exact |= np.all(q == np.roll(original, shift, axis=1), axis=(1, 2))
        unchanged += int(exact.sum())
        maximum = max(maximum, check(q[~exact], original[~exact]))
        normals = np.cross(q[:, 1]-q[:, 0], q[:, 2]-q[:, 0])
        reference = np.cross(original[:, 1]-original[:, 0], original[:, 2]-original[:, 0])
        cosine = np.einsum('ij,ij->i', normals, reference)/(np.linalg.norm(normals, axis=1)*np.linalg.norm(reference, axis=1))
        assert np.isfinite(cosine).all() and np.all(cosine > 0), 'Changed surface orientation'
        minimum_normal_cosine = min(minimum_normal_cosine, float(cosine.min()))
    args.output.mkdir(mode=0o700, exist_ok=False)
    passed = maximum < 1e-8
    report = dict(source_sha256=sha(__file__), job_sha256=sha(args.job), candidate_sha256=sha(job['candidate']),
                  all_output_triangles_checked=len(f), exact_unchanged_triangles=unchanged,
                  clipped_or_retriangulated_triangles=len(f)-unchanged,
                  numerical_whole_triangle_containment_bound_mm=maximum,
                  containment_limit_mm=1e-8, containment_passed=passed,
                  minimum_source_normal_cosine=minimum_normal_cosine,
                  resource_triangle_counts=counts.tolist(), claimed_source_indices_valid=True,
                  analytic_inside_off_plane_and_outside_controls_passed=True,
                  floating_point_containment_is_not_an_exact_rational_proof=True,
                  missing_boundary_or_union_completeness_not_checked_here=True,
                  manufacturing_qualified=False, engine_qualified=False, seconds=time.monotonic()-began)
    for item in job['inputs']:
        assert sha(item['path']) == item['sha256']
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: value for k, value in report.items() if k != 'resource_triangle_counts'}), flush=True)


if __name__ == '__main__':
    main()
