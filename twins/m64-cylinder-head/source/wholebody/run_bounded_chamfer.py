#!/usr/bin/env python3
"""Bounded DelOptim intermediate-stage experiment; never a CAD/CAE release.

The executable must be the separately patched, SHA-bound research build.
Private meshes and receipts only. Reuse existing orientation/topology auditors.
"""
import argparse
import importlib.metadata as metadata
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import numpy as np

from trial_meshers_2026 import read_gmsh, read_inner_tets, boundary, normalize_convention, audit_output, native

INPUTS = {
    '285d0271e6e9cc4db1f80f8e7bdb54c88578c63c55ffe1ef3e442baa1cac3424': 1341461,
    '965de13aefda6f5a314c9edee295578b4f638d58c173dfe2098d77ae21e4e7af': 241299,
}


def interval_ok(lower, upper, tolerance):
    return bool(all(math.isfinite(x) for x in (lower, upper, tolerance))
                and tolerance > 0 and 0 <= lower <= upper and upper-lower <= tolerance)


def surface_arrays(points, faces):
    points, faces = np.asarray(points), np.asarray(faces)
    if (points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all()
            or faces.ndim != 2 or faces.shape[1] != 3 or not len(faces)
            or not np.issubdtype(faces.dtype, np.integer) or faces.min() < 0 or faces.max() >= len(points)):
        raise ValueError('finite_indexed_triangle_surface_required')
    used, inverse = np.unique(faces, return_inverse=True)
    points, faces = points[used].astype(np.float64), inverse.reshape(-1, 3).astype(np.int32)
    xyz = points[faces]
    if not (np.linalg.norm(np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0]), axis=1) > 0).all():
        raise ValueError('nondegenerate_surface_required')
    return points, faces


def distance_bounds(p, f, q, g, tolerance=1e-4):
    from cascading_upper_bounds import pompeiu_hausdorff
    p, f = surface_arrays(p, f); q, g = surface_arrays(q, g)
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('positive_absolute_tolerance_required')
    rows = []
    for a, fa, b, fb in ((p, f, q, g), (q, g, p, f)):
        # A relative cap of four starved tiny analytic witnesses. Bound the
        # actual subdivision allocation instead; exhaustion still fails closed.
        factor = max(1., min(1e6, 2000000/max(len(a), len(fa))))
        lo, hi, diagonal, bvh_ms, bounds_ms = map(float,
            pompeiu_hausdorff(a, fa, b, fb, tolerance, factor, False))
        rows.append(dict(lower=lo, upper=hi, diagonal=diagonal,
            interval_closed=interval_ok(lo, hi, tolerance), allocation_factor=factor,
            bvh_ms=bvh_ms, bounds_ms=bounds_ms))
    return dict(directions=rows, absolute_gap_tolerance=tolerance,
        upper=max(r['upper'] for r in rows), completed=all(r['interval_closed'] for r in rows),
        native_CAD_deviation_certified=False, rounding_error_certificate=False)


def command(executable, off, epsilon, safe, cap):
    if epsilon not in (.005, .010, .020) or not isinstance(safe, bool) or not 1 <= cap <= 200000:
        raise ValueError('bounded_experiment_options_required')
    flags = [str(executable), '-a', '-d', '-x', '-v', '-E', str(epsilon), '-m', str(cap)]
    if safe: flags.append('-S')
    return flags + [str(off)]


def run(args):
    import gmsh
    from audit_envelope_regions import audit as audit_regions
    os.umask(0o077)
    exe = args.executable.resolve()
    if (args.output.exists() or args.output.is_symlink() or args.executable.is_symlink()
            or native.sha256(exe) != args.executable_sha256 or gmsh.__version__ != '4.15.2'
            or np.__version__ != '2.2.6' or metadata.version('cascading-upper-bounds') != '1.0.0'):
        raise ValueError('fresh_output_pinned_executable_and_runtime_required')
    mesh_sha = native.sha256(args.mesh) if args.mesh else None
    if args.mesh and (args.mesh.is_symlink() or mesh_sha not in INPUTS):
        raise ValueError('retained_mesh_required')
    sources = {Path(__file__): native.sha256(__file__)}
    for name in ('trial_meshers_2026.py', 'audit_envelope_regions.py', 'run_local_surface_trial.py'):
        p = Path(__file__).with_name(name); sources[p] = native.sha256(p)
    sources[Path(native.__file__)] = native.sha256(native.__file__)
    args.output.mkdir(mode=0o700)
    start = time.monotonic()
    report = dict(schema='m64-bounded-intermediate/v1', status='incomplete',
        input_sha256=mesh_sha, witness=args.witness, executable_sha256=args.executable_sha256,
        sources={p.name: h for p, h in sources.items()},
        epsilon_scan_units=args.epsilon, safe_chamfer=args.safe, refinement_cap=args.cap,
        refinement_convergence_claimed=False, CAD_modified=False, master_replaced=False,
        CAE_authorized=False, manufacturing_authorized=False, mesh_gate_closed=False)
    target = args.output/'report.json'
    save = lambda: native.save(target, report)
    save()
    gmsh.initialize(['bounded-chamfer', '-nopopup'], readConfigFiles=False, run=False)
    gmsh.option.setNumber('General.Terminal', 0)
    try:
        if args.mesh:
            p, c, f, _ = read_gmsh(args.mesh)
            if len(c) != INPUTS[mesh_sha]: raise ValueError('retained_element_count_required')
            c, reverse = normalize_convention(p, c)
            if reverse: raise ValueError('reference_orientation_changed')
            bf = boundary(c)
            if not np.array_equal(np.unique(np.sort(f, axis=1), axis=0), np.unique(np.sort(bf, axis=1), axis=0)):
                raise ValueError('complete_input_boundary_required')
        else:
            p = np.array([[0., 0, 0], [1., 0, 0], [0, 1., 0], [0, 0, 1.]])
            if args.witness == 'acute': p[2] = [1., .024, 0]
            c = np.array([[0, 1, 2, 3]]); f = boundary(c)
        v = p[c]
        report['reference_polygon_volume'] = math.fsum(map(float, np.linalg.det(v[:, 1:]-v[:, [0]])/6))
        p, f = surface_arrays(p, f)
        off = (args.output/'input-private.off').resolve()
        with off.open('x') as stream:
            stream.write(f'OFF\n{len(p)} {len(f)} 0\n')
            np.savetxt(stream, p, fmt='%.17g')
            np.savetxt(stream, np.column_stack([np.full(len(f), 3), f]), fmt='%d')
        report.update(input_surface_vertices=len(p), input_surface_triangles=len(f),
            command=command(exe, off, args.epsilon, args.safe, args.cap))
        save()
        with (args.output/'mesher.log').open('x') as log:
            process = subprocess.Popen(report['command'], cwd=args.output, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True)
            try: report['mesher_returncode'] = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.wait()
                report['mesher_returncode'] = process.returncode
                raise TimeoutError('bounded_mesher_timeout')
        save()
        if report['mesher_returncode'] != 0: raise ValueError('mesher_process_failed')
        q, d, counts = read_inner_tets(args.output/'DR_mesh.tet')
        report['classification'] = counts; save()
        d, reverse = normalize_convention(q, d)
        report['uniform_orientation_permutation'] = reverse
        g = boundary(d)
        report['mesh'] = audit_output(q, d, g, args.output/'result-private.msh'); save()
        report['regions'], _ = audit_regions(q, d); save()
        report['distance'] = distance_bounds(p, f, q, g); save()
        report.update(status='completed_diagnostic_only',
            within_polygon_epsilon=bool(report['distance']['completed'] and report['distance']['upper'] <= args.epsilon),
            polygon_volume_relative_change=report['mesh']['tetra_volume']/report['reference_polygon_volume']-1)
        # DelOptim's polygon result carries no native functional-face mapping.
        # Positive tets and a small distance never close the native CAD gate.
    except Exception as exc:
        report.update(status='failed', error=type(exc).__name__+': '+str(exc))
    finally:
        gmsh.finalize()
        report.update(seconds=time.monotonic()-start, inputs_unchanged=(
            native.sha256(exe) == args.executable_sha256 and
            (not args.mesh or native.sha256(args.mesh) == mesh_sha) and
            all(native.sha256(p) == h for p, h in sources.items())))
        save()
    print(json.dumps({k: report.get(k) for k in ('status', 'error', 'classification',
        'within_polygon_epsilon', 'polygon_volume_relative_change', 'seconds')}), flush=True)
    return 0 if report['status'] == 'completed_diagnostic_only' and report['inputs_unchanged'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--mesh', type=Path)
    group.add_argument('--witness', choices=('tetrahedron', 'acute'))
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--executable-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--epsilon', type=float, choices=(.005, .010, .020), required=True)
    parser.add_argument('--safe', action='store_true')
    parser.add_argument('--cap', type=int, default=200000)
    parser.add_argument('--timeout', type=int, default=120)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 1200: parser.error('timeout_must_be_1_to_1200_seconds')
    raise SystemExit(run(args))
