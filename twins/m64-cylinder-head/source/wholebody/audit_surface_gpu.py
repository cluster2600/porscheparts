#!/usr/bin/env python3
"""Compare an explicitly hash-bound surface with NumPy and PhysicsNeMo CPU/CUDA.

No geometry edits, surrogate training, thermal solve or manufacturing admission.
API: https://docs.nvidia.com/physicsnemo/latest/physicsnemo/api/mesh/core.html
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time

SOURCE = Path(__file__).resolve().parents[1] / 'physicsnemo-mesh'
sys.path.insert(0, str(SOURCE))
from cpu_reference import reference


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compare(actual, expected, atol):
    import numpy as np
    if actual.shape != expected.shape or actual.dtype != np.float64:
        raise ValueError('output_shape_or_precision_changed')
    finite = np.isfinite(actual) & np.isfinite(expected)
    passed = finite & np.isclose(actual, expected, rtol=1e-10, atol=atol)
    delta = np.abs(actual[finite] - expected[finite])
    return {'passed': bool(passed.all()), 'failed_values': int((~passed).sum()),
            'nonfinite_values': int((~finite).sum()),
            'max_absolute_error': float(delta.max()) if len(delta) else None,
            'rtol': 1e-10, 'atol': atol}


def run(args, report):
    import numpy as np
    import torch
    from physicsnemo.mesh import Mesh
    if not torch.cuda.is_available():
        raise ValueError('CUDA_required')
    torch.set_num_threads(4)
    with np.load(args.mesh, allow_pickle=False) as data:
        points, triangles = data['points'], data['triangles']
    if len(points) > 1_000_000 or len(triangles) > 2_000_000:
        raise ValueError('surface_budget_exceeded')
    expected = reference(points, triangles)
    report.update(points=len(points), triangles=len(triangles),
                  reference_sha256=sha(SOURCE / 'cpu_reference.py'),
                  versions={n: importlib.metadata.version(n) for n in ('torch', 'numpy', 'nvidia-physicsnemo')},
                  gpu=torch.cuda.get_device_name(0), cuda=torch.version.cuda,
                  devices={}, comparisons={})
    results = {}
    for device in ('cpu', 'cuda'):
        p = torch.from_numpy(points.copy()).to(device)
        c = torch.from_numpy(triangles.copy()).to(device)
        if device == 'cuda':
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
        start = time.perf_counter()
        with torch.inference_mode():
            mesh = Mesh(points=p, cells=c)
            values = {'areas': mesh.cell_areas, 'unit_normals': mesh.cell_normals}
            # Pure library geometry: no smoothing, remeshing or learned field.
            quality = mesh.quality_metrics
        if device == 'cuda':
            torch.cuda.synchronize()
        report['devices'][device] = {'compute_seconds': time.perf_counter() - start,
            'quality_keys': sorted(quality.keys()),
            'quality_nonfinite_values': {k: int((~torch.isfinite(v)).sum()) for k, v in quality.items()},
            'quality_minimum': {k: float(v[torch.isfinite(v)].min()) if torch.isfinite(v).any() else None for k, v in quality.items()}}
        if device == 'cuda':
            report['devices'][device]['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
        results[device] = {k: v.detach().cpu().numpy() for k, v in values.items()}
        report['comparisons'][device + '_vs_numpy'] = {
            k: compare(v, expected[k], 0 if k == 'areas' else 1e-12)
            for k, v in results[device].items()}
        if not (np.array_equal(p.cpu().numpy(), points) and np.array_equal(c.cpu().numpy(), triangles)):
            raise ValueError('input_tensor_modified')
    report['comparisons']['cuda_vs_cpu'] = {
        k: compare(v, results['cpu'][k], 0 if k == 'areas' else 1e-12)
        for k, v in results['cuda'].items()}
    report['numerical_comparison_passed'] = all(row['passed'] for group in report['comparisons'].values() for row in group.values())
    report['status'] = 'comparison_passed' if report['numerical_comparison_passed'] else 'comparison_rejected'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or sha(args.mesh) != args.sha256:
        raise ValueError('fresh_output_and_exact_input_required')
    report = {'schema': 'm64-wholebody-surface-gpu/v1', 'status': 'incomplete',
              'input_sha256': args.sha256, 'source_sha256': sha(__file__),
              'CFD_authorized': False, 'manufacturing_authorized': False,
              'absolute_scale_certified': False, 'external_timeout_required': True}
    try:
        run(args, report)
    except Exception as error:
        report.update(status='failed', error_type=type(error).__name__, error=str(error)[:200])
    report['input_unchanged'] = sha(args.mesh) == args.sha256
    if not report['input_unchanged']:
        report['status'] = 'failed_input_changed'
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps({k: report[k] for k in ('status', 'input_unchanged')}))
    return 0 if report['status'] == 'comparison_passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
