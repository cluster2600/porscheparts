#!/usr/bin/env python3
"""Pinned PhysicsNeMo 2.2.2 mesh benchmark, not CFD or manufacturing validation."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import numpy as np

PINS = {'mesh': 'ab6f41b8802e96c5be1c159b47116e4a9818d91fe57b38139e277f3275e49d66',
        'reference': 'c99fcfc54d519fa4eb2d75e1d8dd7f6377eed2710e07df8bfc870fa1444e289b',
        'reference_report': '1624f39a009d190adb0c9e99fb11b08c8985e4f4ec177e268e04bd1ffe29d7b4'}
WHEEL_SHA = 'c447771384d92f5c31547e293f65b70e0947f8829981f34c7e8300daf1b8d2eb'
SOURCE_PINS = {
    'mesh/mesh.py': '90d5cd8a6182066ee4f90aca38432090a861bc81e476be8db86963f067f1fbba',
    'mesh/geometry/_cell_areas.py': '4f164c2db7b566fb8a3473f3293903b91876d977c5f974d5a698476cd44c2d53',
    'mesh/geometry/_cell_normals.py': '8204b60f801e924a2c50fb18f9510a6f7b089699d1db60a5c89fe0ec9ce462c5',
    'mesh/geometry/_angles.py': 'ec4eefb2c7b7d1b02f4167024c6a2024cb1c72babc20ac371094a2684189bdb1',
    'mesh/validation/quality.py': 'e2403ba1e7f282b63d92034bdc9cbc5569a2a4ee8893b7826012c1c6fc10f781'}
QUALITY_KEYS = ('aspect_ratio', 'edge_length_ratio', 'min_angle', 'max_angle',
                'min_edge_length', 'max_edge_length', 'quality_score')
REPEATS, RTOL, ATOL = 5, 1e-10, 1e-12  # numerical comparisons, not physical gates


class Refusal(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise Refusal(reason)


def sha(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def array_sha(array):
    return hashlib.sha256(str((array.dtype.str, array.shape)).encode() + array.tobytes(order='C')).hexdigest()


def validate(points, cells):
    require(points.dtype == np.float64 and points.ndim == 2 and points.shape[1] == 3, 'points_dtype_shape')
    require(cells.dtype == np.int64 and cells.ndim == 2 and cells.shape[1] == 3, 'cells_dtype_shape')
    require(0 < len(points) <= 1_000_000 and 0 < len(cells) <= 2_000_000, 'input_count_bound')
    require(np.isfinite(points).all() and cells.min() >= 0 and cells.max() < len(points), 'input_values')
    require(np.all(cells[:, 0] != cells[:, 1]) and np.all(cells[:, 1] != cells[:, 2])
            and np.all(cells[:, 0] != cells[:, 2]), 'repeated_triangle_node')


def compare(actual, reference, atol=ATOL):
    require(actual.shape == reference.shape and actual.dtype == np.float64, 'comparison_shape_dtype')
    finite = np.isfinite(actual) & np.isfinite(reference)
    delta = np.abs(actual[finite] - reference[finite])
    passed = finite & np.isclose(actual, reference, rtol=RTOL, atol=atol, equal_nan=False)
    report = {'passed': bool(passed.all()), 'failed_values': int((~passed).sum()),
              'failed_cells': int((~passed.reshape(len(actual), -1).all(axis=1)).sum()),
              'nonfinite_values': int((~finite).sum()), 'max_abs_error': float(delta.max()) if delta.size else None,
              'rtol': RTOL, 'atol': atol}
    if atol == 0:  # area comparisons have no absolute floor
        positive = finite & (reference > 0)
        relative = np.abs(actual[positive] - reference[positive]) / reference[positive]
        report.update(positive_reference_but_zero_area=int(((reference > 0) & (actual == 0)).sum()),
                      max_relative_area_error=float(relative.max()) if relative.size else None,
                      relative_error_over_finite_positive_reference_pairs=True)
    return report


def summarize(array):
    finite = array[np.isfinite(array)]
    return {'nonfinite': int(array.size - finite.size),
            'min': float(finite.min()) if finite.size else None,
            'max': float(finite.max()) if finite.size else None,
            'mean': float(finite.mean()) if finite.size else None}


def timed(call, sync):
    sync()
    start = time.perf_counter()
    result = call()
    sync()
    return result, time.perf_counter() - start


def repeated(call, sync):
    warm, warm_seconds = timed(call, sync)
    del warm
    samples, result = [], None
    for _ in range(REPEATS):
        result = None  # no cache or output retained from the preceding repetition
        result, elapsed = timed(call, sync)
        samples.append(elapsed)
    return result, {'warmup_seconds': warm_seconds, 'repetitions_seconds': samples,
                    'median_seconds': float(np.median(samples)), 'fresh_mesh_each_call': True}


def compute(Mesh, points, cells):
    mesh = Mesh(points=points, cells=cells)
    areas, normals = mesh.cell_areas, mesh.cell_normals
    quality = mesh.quality_metrics
    require(set(quality.keys()) == set(QUALITY_KEYS), 'quality_api_keys_changed')
    return {'areas': areas, 'unit_normals': normals, **{k: quality[k] for k in QUALITY_KEYS}}


def witness(torch, Mesh, device):
    s = 2.0 ** -30
    points = torch.tensor([[0., 0., 0.], [1., 0., 0.], [1., s, 0.],
                           [0., 0., 0.], [s, 0., 0.], [0., s, 0.]], dtype=torch.float64, device=device)
    cells = torch.tensor([[0, 1, 2], [3, 4, 5]], dtype=torch.int64, device=device)
    out = compute(Mesh, points, cells)
    areas = out['areas'].detach().cpu().numpy()
    norms = np.linalg.norm(out['unit_normals'].detach().cpu().numpy(), axis=1)
    return {'analytic_positive_areas': [s / 2, s * s / 2], 'observed_areas': areas.tolist(),
            'observed_normal_lengths': norms.tolist(), 'gram_positive_area_lost': bool(areas[0] == 0),
            'small_nonzero_normal_not_unit': bool(abs(norms[1] - 1) > ATOL),
            'geometrically_degenerate': False, 'expected_library_limitations_not_acceptance_tests': True}


def benchmark(args, report):
    import torch
    import physicsnemo
    from physicsnemo.mesh import Mesh
    require(metadata.version('nvidia-physicsnemo') == '2.2.2', 'physicsnemo_version')
    require(torch.__version__ == '2.10.0+cu128', 'torch_version')
    for relative, pin in SOURCE_PINS.items():
        require(sha(Path(physicsnemo.__file__).parent / relative) == pin, 'installed_source_hash')
    report['installed_sources_verified'] = True
    require(torch.cuda.is_available(), 'cuda_required_for_this_pilot')
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    report['versions'] = {k: metadata.version(k) for k in ('nvidia-physicsnemo', 'torch', 'numpy', 'tensordict', 'warp-lang')}
    report['runtime'] = {'python': sys.version.split()[0], 'cuda': torch.version.cuda,
                         'gpu': torch.cuda.get_device_name(0), 'cpu_threads': torch.get_num_threads(),
                         'gpu_total_memory_bytes': torch.cuda.get_device_properties(0).total_memory}
    for key, pin in PINS.items():
        require(sha(getattr(args, key)) == pin, 'input_sha_' + key)
    with np.load(args.mesh, allow_pickle=False) as data:
        require(set(data.files) == {'points', 'triangles'}, 'npz_keys')
        points, cells = data['points'], data['triangles']
    validate(points, cells)
    input_arrays = {'points': array_sha(points), 'ordered_triangles': array_sha(cells)}
    with np.load(args.reference, allow_pickle=False) as data:
        reference = {k: data[k] for k in ('areas', 'unit_normals')}
    receipt = json.loads(args.reference_report.read_text())
    require(receipt['input_sha256'] == PINS['mesh'] and receipt['output_sha256'] == PINS['reference']
            and receipt['input_unchanged'] is True, 'independent_reference_binding')
    report.update(points=len(points), triangles=len(cells), array_sha256=input_arrays)
    (cpu_p, cpu_c), cpu_copy = timed(lambda: (torch.from_numpy(points.copy()), torch.from_numpy(cells.copy())), lambda: None)
    (gpu_p, gpu_c), h2d = timed(lambda: (cpu_p.to('cuda'), cpu_c.to('cuda')), torch.cuda.synchronize)
    report['transfers_seconds'] = {'numpy_to_cpu_copy': cpu_copy, 'host_to_device': h2d}
    results, comparisons = {}, {}
    with torch.inference_mode():
        for device, p, c in [('cpu', cpu_p, cpu_c), ('cuda', gpu_p, gpu_c)]:
            sync = torch.cuda.synchronize if device == 'cuda' else lambda: None
            if device == 'cuda':
                torch.cuda.reset_peak_memory_stats()
            outputs, timing = repeated(lambda: compute(Mesh, p, c), sync)
            arrays, transfer = timed(lambda: {k: v.detach().cpu().numpy() for k, v in outputs.items()}, sync)
            require(all(a.dtype == np.float64 for a in arrays.values()), 'output_float64')
            results[device] = arrays
            report[device] = {'timing': timing, 'output_transfer_seconds': transfer,
                              'metrics': {k: summarize(v) for k, v in arrays.items()}}
            if device == 'cuda':
                report[device]['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
                report[device]['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
            report[device]['library_witnesses'] = witness(torch, Mesh, device)
            require(array_sha(p.cpu().numpy()) == input_arrays['points']
                    and array_sha(c.cpu().numpy()) == input_arrays['ordered_triangles'], 'tensor_input_mutation')
            comparisons[device + '_vs_numpy'] = {k: compare(arrays[k], reference[k], 0 if k == 'areas' else ATOL) for k in reference}
    comparisons['cpu_vs_cuda'] = {k: compare(results['cuda'][k], results['cpu'][k], 0 if k == 'areas' else ATOL) for k in results['cpu']}
    report['comparisons'] = comparisons
    report['normal_lengths'] = {k: summarize(np.linalg.norm(v['unit_normals'], axis=1)) for k, v in results.items()}
    report['numerical_comparison_passed'] = all(v['passed'] for group in comparisons.values() for v in group.values())
    require(array_sha(points) == input_arrays['points'] and array_sha(cells) == input_arrays['ordered_triangles'], 'numpy_input_mutation')
    require(all(sha(getattr(args, k)) == v for k, v in PINS.items()), 'input_file_mutation')
    report.update(inputs_unchanged=True, ordered_triangle_equivalence_verified=True, process_completed=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('mesh', 'reference', 'reference-report', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.child:
        args.output.mkdir(mode=0o700, exist_ok=True)
        require(not any(args.output.iterdir()), 'output_not_empty')
        with (args.output / 'benchmark.log').open('xb') as log:
            proc = subprocess.Popen([sys.executable, '-B', __file__, *sys.argv[1:], '--child'],
                                    stdout=log, stderr=log, start_new_session=True, shell=False)
            try:
                code = proc.wait(timeout=290)
            except subprocess.TimeoutExpired:
                code = 124
            except KeyboardInterrupt:
                code = 130
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=5)
        summary = {'process_exit_code': code, 'report_present': (args.output / 'report.json').is_file(),
                   'child_wall_limit_seconds': 290, 'cleanup_limit_seconds': 5,
                   'process_group_kill_and_wait_completed': True}
        (args.output / 'supervisor-report.json').write_text(json.dumps(summary) + '\n')
        print(json.dumps(summary))
        return code
    started = time.perf_counter()
    report = {'schema': 'm64-private-physicsnemo-mesh-benchmark/v1', 'process_completed': False,
              'pins': PINS, 'wheel_sha256': WHEEL_SHA, 'source_pins': SOURCE_PINS,
              'official_version_url': 'https://pypi.org/project/nvidia-physicsnemo/2.2.2/',
              'benchmark_source_sha256': sha(__file__), 'CFD_authorized': False, 'manufacturing_authorized': False,
              'absolute_scale_certified': False, 'length_unit': 'scan_unit', 'adjacency_computed': False,
              'quality_metrics_are_not_OpenFOAM_quality': True, 'quality_numpy_reference_available': False,
              'timing_includes_fresh_Mesh_construction_and_areas_normals_quality': True}
    try:
        benchmark(args, report)
    except Exception as exc:
        report['error_type'] = type(exc).__name__
        report['error_code'] = str(exc) if isinstance(exc, Refusal) else 'runtime_failure_see_private_log'
        import traceback
        traceback.print_exc()
    finally:
        report['elapsed_seconds'] = time.perf_counter() - started
        (args.output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return 0 if report.get('numerical_comparison_passed') and report['process_completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
