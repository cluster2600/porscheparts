#!/usr/bin/env python3
"""Private native-Mac single-candidate screen; requires a passed native reference."""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO/'twins/m64-cylinder-head/source/fourvalve'))
import g13_campaign as g13
import scipy

g11, g8, g9, reference = g13.g11, g13.g8, g13.g9, g13.reference
NATIVE_SCRIPT_SHA = '85d175ed6c0b7d7736b75ac29550e31ab272c11f47199a2f03aefc908656e667'
CAMPAIGN_SHA = '76a293a81ea49b82138dd3dd3fbf5466615a893103f683f75ced77ca9994b789'
BUILD_SHA = '44011ff1e9197d6110df6d4a375c5f2daa0c2b0030ae25a3664d37455f2aaca3'
INVENTORY_SHA = '82a729772dc14b1c5e80e31fc4038a95448a68ad1a19941f4684e7d75412923c'
BINARY_SHA = '9cd22c961a0ead334739802e369345745746aafd51a01cff5d2309274cf1548a'
PLAN = (('serial-z-r1', 'minus_z'), ('serial-z-r2', 'minus_z'), ('serial-x-control', 'x'))
WRAPPER = HERE/'serial-bin/ccx'
WRAPPER_SHA = 'ddf3144d246863c1e9d70ff1d1d628d88763c79ecc05a8db212d78c694ef83fa'
CAD = REPO/'work/m64-g13/cad/receipt.json'
OUTER_CAD = REPO/'work/m64-g11/cad-v2/receipt.json'


def bounded(value, limit):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= limit


def require_passed_summary(summary):
    if (summary.get('classification') != 'native_arm64_macOS_CPU_reference_pilot_not_G13_Linux_GPU_qualification'
            or summary.get('error') is not None or summary.get('complete') is not True
            or summary.get('all_native_CPU_comparisons_passed') is not True
            or summary.get('dynamic_libraries_verified_before') is not True
            or summary.get('dynamic_libraries_verified_after') is not True
            or summary.get('CUDA_executed') is not False or summary.get('G13_Linux_reference_promoted') is not False
            or tuple((r['id'], r['direction']) for r in summary['rows']) != PLAN
            or set(summary['references']) != {'x', 'minus_z'}):
        raise ValueError('completed, successful native CPU reference required; Linux recipe is not transferable')
    for row in summary['rows']:
        m, a, direct = row['mechanics'], row['agreement'], row['direct']
        if (row['passed'] is not True or row['compared'] is not True or row['threads'] != 1
                or direct['threads'] != 1 or direct['observed_cpu_counts'] != [1] or direct['exit_code'] != 0
                or direct['thread_environment'] != {k: '1' for k in reference.THREAD_KEYS}
                or m['equilibrium_passed'] is not True
                or not bounded(m['force_balance_relative_error'], 1e-4)
                or not bounded(m['moment_balance_F_times_100mm_error'], 1e-4)
                or not bounded(a['max_nodal_difference_over_max_reference_U'], 1e-4)
                or not bounded(a['printed_dat_rounding_residual_bound'], math.inf)
                or not bounded(a['printed_dat_relative_residual'], a['printed_dat_rounding_residual_bound'])):
            raise ValueError('native reference numerical or serial guard failed')
    for proof in summary['references'].values():
        if (proof['passed'] is not True or proof['solver']['backend'] != 'cpu'
                or proof['solver']['info'] != 0 or proof['solver']['dtype'] != 'float64'
                or not bounded(proof['relative_residual'], 1e-8)):
            raise ValueError('native fresh CPU matrix comparison failed')


def artifacts(root, hashes):
    if not hashes:
        raise ValueError('missing retained artifact hashes')
    for name, digest in hashes.items():
        if Path(name).name != name or g8.sha256(g13.confined(root, name)) != digest:
            raise ValueError('retained artifact fingerprint changed: '+name)


def native_gate(path):
    if sys.platform != 'darwin' or platform.machine() != 'arm64' or any(k.startswith('DYLD_') for k in os.environ):
        raise ValueError('native arm64 Mac with no injected dynamic-loader environment required')
    summary = json.loads(path.read_text())
    require_passed_summary(summary)
    build_root = HERE.parent/'native-ccx'
    build_path, inventory_path = build_root/'qualification-smoke.json', build_root/'build-inventory.json'
    if (g8.sha256(build_path) != BUILD_SHA or g8.sha256(inventory_path) != INVENTORY_SHA
            or g8.sha256(HERE/'reference.py') != NATIVE_SCRIPT_SHA
            or g8.sha256(Path(g13.__file__)) != CAMPAIGN_SHA):
        raise ValueError('accepted native build, reference script or campaign changed')
    inventory = json.loads(inventory_path.read_text())
    binary = Path(inventory['binary']['path'])
    if inventory['binary']['sha256'] != BINARY_SHA or g8.sha256(binary) != BINARY_SHA:
        raise ValueError('native CCX binary changed')
    for name, record in inventory['dynamic_libraries'].items():
        if str(Path(name).resolve()) != record['resolved_path'] or g8.sha256(Path(name)) != record['sha256']:
            raise ValueError('native linked library changed: '+name)
    expected = dict(native_binary_sha256=BINARY_SHA, build_receipt_sha256=BUILD_SHA,
        build_inventory_sha256=INVENTORY_SHA, script_sha256=NATIVE_SCRIPT_SHA,
        helper_sha256=g8.sha256(Path(reference.__file__)), source_sha256=reference.SOURCES,
        original_sha256=reference.INPUTS, dynamic_libraries=inventory['dynamic_libraries'])
    identity = json.loads((path.parent/'identity.json').read_text())
    if any(summary.get(k) != v or identity.get(k) != v for k, v in expected.items()):
        raise ValueError('native reference identity binding mismatch')
    if summary['software']['numpy'] != g13.g11.np.__version__ or summary['software']['scipy'] != scipy.__version__:
        raise ValueError('native CPU algebra package versions changed')
    reference.inputs(path.parent/'original-rejected')
    retained = {'provenance/reference.py': NATIVE_SCRIPT_SHA, 'provenance/accepted-build.json': BUILD_SHA,
        'provenance/accepted-build-inventory.json': INVENTORY_SHA, 'bin/ccx': BINARY_SHA}
    for name, digest in retained.items():
        if g8.sha256(g13.confined(path.parent, name)) != digest:
            raise ValueError('retained native reference provenance changed')
    for row in summary['rows']:
        case = g13.confined(path.parent, row['id'])
        if json.loads((case/'case.json').read_text()) != row:
            raise ValueError('native reference row differs from its case receipt')
        artifacts(case, row['hashes'])
        g13.serial_log(case/(row['direction']+'.log'))
    matrix = path.parent/'matrix'
    for name, proof in summary['references'].items():
        if json.loads((matrix/(name+'-reference.json')).read_text()) != proof:
            raise ValueError('native matrix reference differs from its retained proof')
        artifacts(matrix, proof['matrix_sha256'])
    g13.serial_log(matrix/'matrix.log')
    if not os.access(WRAPPER, os.X_OK) or g8.sha256(WRAPPER) != WRAPPER_SHA:
        raise ValueError('approved private serial wrapper changed or is not executable')
    return dict(native_reference_summary_sha256=g8.sha256(path), native_reference_identity_sha256=g8.sha256(path.parent/'identity.json'),
        **expected, wrapper_sha256=g8.sha256(WRAPPER), binary=str(binary), native_CPU_reference_qualified=True)


def worker(args):
    proof = native_gate(args.reference)
    identity = json.loads((args.output/'identity.json').read_text())
    if identity['candidate_source_sha256'] != g8.sha256(Path(__file__)) or identity['runtime'] != proof:
        raise ValueError('native worker differs from the controller-approved source or runtime')
    receipt, baseline, variants = g13.inputs(CAD, OUTER_CAD)
    mirror = g13.mirror_gate(receipt, CAD.parent, variants[g13.OUTER])
    variant = variants[args.id]
    os.environ['PATH'] = str(WRAPPER.parent)+os.pathsep+os.environ.get('PATH', '')
    case = args.output/('native-mac-'+args.id+'-'+format(args.mesh, 'g'))
    case.mkdir()
    points, elements, support, weights, mesh = g11.mesh(variant['step_path'], args.mesh, receipt['values'], variant, case)
    loads = g11.forces(baseline, variant['component'])
    for name, direction in g11.DIRECTIONS:
        g8.solve(case, points, elements, support, weights, loads, direction, name)
        g13.serial_log(case/(name+'.log'))
    rows = g9.audit(case, tuple(n for n, _ in g11.DIRECTIONS), case, 'cpu')
    logs = {name: g13.serial_log(case/(name+'.log')) for name in ('x', 'minus_z', 'matrix')}
    if native_gate(args.reference) != proof:
        raise ValueError('native runtime changed during candidate solve')
    result = dict(classification='native_arm64_macOS_CPU_isolated_candidate_not_Linux_CUDA', id=args.id,
        component=variant['component'], mesh=mesh, backend='cpu', runtime=proof, outer_mirror=mirror,
        candidate_source_sha256=g8.sha256(Path(__file__)), frozen_sources_sha256=g11.source_hashes(),
        cad_receipt_sha256=variant['cad_receipt_sha256'], step_sha256=variant['step_sha256'],
        journal_forces_N=loads, volume_mm3=variant['volume_mm3'], serial_logs=logs, cases=rows, complete=len(rows) == 2,
        FEA_executed=True, CUDA_executed=False, G13_Linux_reference_promoted=False, manufacturing_authorized=False,
        engine_start_authorized=False, assembled_stiffness_qualified=False, hot_material_qualified=False,
        boundary_hypothesis='Unchanged G11 whole bottom land fixed XYZ; generic E=70000 MPa, nu=0.33, not physical contact or selected alloy',
        hashes={p.name: g8.sha256(p) for p in sorted(case.iterdir()) if p.is_file()})
    result['numerically_qualified'] = g11.qualified_rows(result)
    result['maximum_journal_motion_mm'] = g11.motion(result) if result['numerically_qualified'] else None
    result['mesh_convergence_qualified'] = False
    g11.publish(case/'case.json', result)


def run(args):
    # The trust boundary runs BEFORE creating outputs or spawning any process.
    proof = native_gate(args.reference)
    receipt, _, variants = g13.inputs(CAD, OUTER_CAD)
    mirror = g13.mirror_gate(receipt, CAD.parent, variants[g13.OUTER])
    if args.check:
        print(json.dumps({'check_only': True, 'runtime': proof, 'outer_mirror': mirror}), flush=True)
        return 0
    args.output.mkdir(parents=True, exist_ok=False)
    provenance = args.output/'provenance'; provenance.mkdir()
    shutil.copyfile(__file__, provenance/'candidate.py')
    shutil.copyfile(WRAPPER, provenance/'ccx-wrapper')
    identity = dict(id=args.id, mesh_mm=args.mesh, runtime=proof, outer_mirror=mirror,
        candidate_source_sha256=g8.sha256(Path(__file__)), frozen_sources_sha256=g11.source_hashes(),
        cad_receipt_sha256=g8.sha256(CAD), outer_receipt_sha256=g8.sha256(OUTER_CAD),
        timeout_seconds=args.timeout, CUDA_executed=False)
    g11.publish(args.output/'identity.json', identity)
    command = [sys.executable, str(Path(__file__).resolve()), '--worker', '--reference', str(args.reference.resolve()),
        '--id', args.id, '--mesh', str(args.mesh), '--output', str(args.output.resolve()), '--timeout', str(args.timeout)]
    start, status, code, error = time.monotonic(), 'failed', None, None
    with (args.output/'worker.log').open('x') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=args.timeout)
            status = 'completed' if code == 0 else 'failed'
        except subprocess.TimeoutExpired:
            status, error = 'timeout', 'whole candidate worker deadline reached'
        except (KeyboardInterrupt, InterruptedError) as exc:
            status, error = 'interrupted', str(exc)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    result_path = args.output/('native-mac-'+args.id+'-'+format(args.mesh, 'g'))/'case.json'
    if status == 'completed' and not result_path.is_file():
        status, error = 'failed', 'worker returned without a case receipt'
    summary = dict(classification='native_Mac_candidate_execution_not_physical_qualification', **identity,
        status=status, returncode=code, error=error, wall_seconds=time.monotonic()-start,
        FEA_executed=True if result_path.is_file() else None,
        result=str(result_path.relative_to(args.output)) if result_path.is_file() else None,
        retained_artifacts_sha256={str(p.relative_to(args.output)): g8.sha256(p) for p in sorted(args.output.rglob('*')) if p.is_file()},
        manufacturing_authorized=False, engine_start_authorized=False)
    g11.publish(args.output/'summary.json', summary)
    print(json.dumps({'status': status, 'summary': str(args.output/'summary.json')}), flush=True)
    return 0 if status == 'completed' else 2


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise InterruptedError('native candidate controller interrupted')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--id', choices=g13.IDS, required=True)
    parser.add_argument('--mesh', type=float, choices=g13.SIZES, default=2.)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('--check', action='store_true', help='Verify trust gates only; never launch a solve')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 0 < args.timeout <= 1800 or not args.output.resolve().is_relative_to(HERE) or args.output.resolve() == HERE:
        parser.error('private output below native-fea and timeout <=1800s required')
    if args.worker:
        worker(args)
    else:
        signal.signal(signal.SIGTERM, interrupted)
        raise SystemExit(run(args))
