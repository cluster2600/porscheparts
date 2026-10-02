#!/usr/bin/env python3
"""CGAL exact-predicate intersection audit of binary64 arrays; never a repair."""
import argparse
import hashlib
import json
from pathlib import Path
import signal
import struct
import subprocess
import tempfile
import time

import numpy as np


def intersection_pairs(points, triangles, executable):
    points, triangles = np.asarray(points), np.asarray(triangles)
    if (points.ndim != 2 or points.shape[1] != 3 or points.dtype != np.float64
            or triangles.ndim != 2 or triangles.shape[1] != 3 or triangles.dtype.kind not in 'iu'
            or not 0 < len(points) <= 2_000_000 or not 0 < len(triangles) <= 2_000_000
            or not np.isfinite(points).all() or triangles.min() < 0 or triangles.max() >= len(points)):
        raise ValueError('bounded_finite_double_surface_required')
    with tempfile.TemporaryDirectory(prefix='m64-intersections-') as directory:
        path = Path(directory)/'surface.bin'
        with path.open('xb') as stream:
            stream.write(b'M64TRI1\0'+struct.pack('<QQ', len(points), len(triangles)))
            stream.write(points.astype('<f8', copy=False).tobytes())
            stream.write(triangles.astype('<u8', copy=False).tobytes())
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result = subprocess.run([str(executable), str(path)], check=True, capture_output=True, text=True, timeout=240)
        report = json.loads(result.stdout)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest: raise ValueError('input_changed')
    pairs = np.asarray(report['pairs_private'], dtype=np.int64)
    if (report['vertices'] != len(points) or report['triangles'] != len(triangles)
            or not isinstance(report['complete'], bool) or len(pairs) > 100001
            or (len(pairs) and (pairs.shape != (len(pairs), 2) or pairs.min() < 0 or pairs.max() >= len(triangles)))):
        raise ValueError('bound_CGAL_result_required')
    return report


def run(args):
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    pins = {p: sha(p) for p in (args.arrays, args.receipt, args.executable, Path(__file__))}
    record = json.loads(args.receipt.read_text())
    if (args.output.exists() or args.output.is_symlink() or any(p.is_symlink() for p in pins)
            or record.get('schema') != 'm64-projected-surface-topology/v1'
            or record.get('status') != 'completed_diagnostic_only' or record.get('inputs_unchanged') is not True
            or record.get('array_export_sha256') != pins[args.arrays] or record.get('array_readback_exact') is not True
            or pins[args.executable] != args.executable_sha256):
        raise ValueError('fresh_output_and_bound_exact_array_export_required')
    started = time.monotonic()
    with np.load(args.arrays, allow_pickle=False) as data:
        points, triangles = data['points'], data['triangles']
    result = intersection_pairs(points, triangles, args.executable)
    report = dict(schema='m64-cgal-intersection-screen/v1', status='completed_diagnostic_only' if result['complete'] else 'incomplete_pair_cap',
        source_hashes={str(p): h for p, h in pins.items()}, CGAL=result,
        triangles=len(triangles), intersecting_pairs=len(result['pairs_private']),
        screen_passed=result['complete'] and not len(result['pairs_private']),
        predicates='CGAL_EPICK_on_stored_binary64_geometry', native_CAD_certified=False,
        CFD_authorized=False, manufacturing_authorized=False,
        inputs_unchanged=all(sha(p) == h for p, h in pins.items()), seconds=time.monotonic()-started)
    with args.output.open('x') as stream: json.dump(report, stream, indent=2, allow_nan=False)
    args.output.chmod(0o600)
    print(json.dumps({k: report[k] for k in ('status', 'triangles', 'intersecting_pairs', 'inputs_unchanged', 'seconds')}))
    return 0 if result['complete'] and report['inputs_unchanged'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('arrays', 'receipt', 'executable', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--executable-sha256', required=True)
    signal.alarm(300)
    raise SystemExit(run(parser.parse_args()))
