#!/usr/bin/env python3
"""Separate cross-product adapter over Mesh; no upstream patch or CAE admission."""
import argparse
import hashlib
import importlib.util
import importlib.metadata as metadata
import json
from pathlib import Path
import signal
import time
LIBRARY_SHA = 'cdbd5ef49ace8bd45edd037cf87757d5480e2cdafcb2e285401626e936799782'


def load(path):
    if hashlib.sha256(path.read_bytes()).hexdigest() != LIBRARY_SHA:
        raise ValueError('library_pin_mismatch')
    spec = importlib.util.spec_from_file_location('pinned_mesh_benchmark', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compute(torch, Mesh, points, cells):
    mesh = Mesh(points=points, cells=cells)
    vertices = mesh.points[mesh.cells]
    cross = torch.linalg.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0], dim=-1)
    twice_area = torch.linalg.vector_norm(cross, dim=-1)
    return {'areas': twice_area / 2, 'unit_normals': cross / twice_area[:, None]}


def expired(signum, frame):
    raise TimeoutError('benchmark_300s_limit')


def run(args, b, report):
    import numpy as np
    import torch
    import physicsnemo
    from physicsnemo.mesh import Mesh
    b.require(metadata.version('nvidia-physicsnemo') == '2.2.2' and torch.__version__ == '2.10.0+cu128', 'version_pin')
    for relative, pin in b.SOURCE_PINS.items():
        b.require(b.sha(Path(physicsnemo.__file__).parent / relative) == pin, 'installed_source_pin')
    b.require(torch.cuda.is_available(), 'cuda_required')
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    report.update(upstream_source_pins=b.SOURCE_PINS, upstream_wheel_sha256=b.WHEEL_SHA, versions={k: metadata.version(k) for k in ('torch', 'numpy', 'nvidia-physicsnemo')},
                  gpu=torch.cuda.get_device_name(0), cuda=torch.version.cuda, input_pins=b.PINS)
    b.require(all(b.sha(getattr(args, k)) == pin for k, pin in b.PINS.items()), 'input_pin')
    with np.load(args.mesh, allow_pickle=False) as data:
        points, cells = data['points'], data['triangles']
    b.validate(points, cells)
    hashes = {'points': b.array_sha(points), 'ordered_triangles': b.array_sha(cells)}
    with np.load(args.reference, allow_pickle=False) as data:
        reference = {k: data[k] for k in ('areas', 'unit_normals')}
    receipt = json.loads(args.reference_report.read_text())
    b.require(receipt['input_sha256'] == b.PINS['mesh'] and receipt['output_sha256'] == b.PINS['reference']
              and receipt['input_unchanged'] is True, 'reference_binding')
    report.update(points=len(points), triangles=len(cells), array_sha256=hashes)
    (cp, cc), cpu_copy = b.timed(lambda: (torch.from_numpy(points.copy()), torch.from_numpy(cells.copy())), lambda: None)
    (gp, gc), transfer = b.timed(lambda: (cp.to('cuda'), cc.to('cuda')), torch.cuda.synchronize)
    report['input_transfers_seconds'] = {'numpy_to_cpu_copy': cpu_copy, 'host_to_device': transfer}
    results, comparisons, witness_passes = {}, {}, []
    with torch.inference_mode():
        for device, p, c in [('cpu', cp, cc), ('cuda', gp, gc)]:
            sync = torch.cuda.synchronize if device == 'cuda' else lambda: None
            if device == 'cuda':
                torch.cuda.reset_peak_memory_stats()
            outputs, timing = b.repeated(lambda: compute(torch, Mesh, p, c), sync)
            arrays, transfer = b.timed(lambda: {k: v.detach().cpu().numpy() for k, v in outputs.items()}, sync)
            results[device] = arrays
            report[device] = {'bundle_cross_area_normal': timing, 'output_transfer_seconds': transfer,
                              'metrics': {k: b.summarize(v) for k, v in arrays.items()}}
            if device == 'cuda':
                report[device].update(peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved())
            comparisons[device + '_vs_numpy'] = {k: b.compare(arrays[k], reference[k], 0 if k == 'areas' else b.ATOL) for k in reference}
            s = 2. ** -30
            wp = torch.tensor([[0., 0., 0.], [1., 0., 0.], [1., s, 0.], [0., 0., 0.], [s, 0., 0.], [0., s, 0.]], dtype=torch.float64, device=device)
            wc = torch.tensor([[0, 1, 2], [3, 4, 5]], dtype=torch.int64, device=device)
            witnesses = {k: v.detach().cpu().numpy() for k, v in compute(torch, Mesh, wp, wc).items()}
            checks = {'areas': b.compare(witnesses['areas'], np.array([s / 2, s * s / 2]), 0),
                      'unit_normals': b.compare(witnesses['unit_normals'], np.array([[0., 0., 1.], [0., 0., 1.]]))}
            report[device]['positive_skinny_and_small_witnesses'] = checks
            witness_passes.extend(v['passed'] for v in checks.values())
            b.require(b.array_sha(p.cpu().numpy()) == hashes['points'] and b.array_sha(c.cpu().numpy()) == hashes['ordered_triangles'], 'tensor_mutation')
    comparisons['cpu_vs_cuda'] = {k: b.compare(results['cuda'][k], results['cpu'][k], 0 if k == 'areas' else b.ATOL) for k in reference}
    b.require(b.array_sha(points) == hashes['points'] and b.array_sha(cells) == hashes['ordered_triangles'], 'numpy_mutation')
    b.require(all(b.sha(getattr(args, k)) == pin for k, pin in b.PINS.items()) and b.sha(args.library) == LIBRARY_SHA, 'file_mutation')
    report.update(comparisons=comparisons, witnesses_passed=all(witness_passes), process_completed=True,
                  numerical_comparison_passed=all(v['passed'] for group in comparisons.values() for v in group.values()),
                  inputs_unchanged=True, ordered_triangle_equivalence_verified=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('library', 'mesh', 'reference', 'reference-report', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=True)
    if any(args.output.iterdir()):
        raise ValueError('output_not_empty')
    report = {'schema': 'm64-private-physicsnemo-cross-adapter/v1', 'process_completed': False, 'CFD_authorized': False,
              'manufacturing_authorized': False, 'absolute_scale_certified': False, 'length_unit': 'scan_unit',
              'upstream_monkeypatched': False, 'quality_metrics_computed': False, 'library_sha256': LIBRARY_SHA, 'external_hard_timeout_required': True,
              'adapter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    started = time.perf_counter()
    old_handler = signal.signal(signal.SIGALRM, expired)
    signal.alarm(300)
    try:
        run(args, load(args.library), report)
    except Exception as exc:
        report['error_type'] = type(exc).__name__
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        report['elapsed_seconds'] = time.perf_counter() - started
        (args.output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: report.get(k, False) for k in ('process_completed', 'numerical_comparison_passed', 'witnesses_passed')}))
    return 0 if report.get('numerical_comparison_passed') and report.get('witnesses_passed') and report['process_completed'] else 2

if __name__ == '__main__':
    raise SystemExit(main())
