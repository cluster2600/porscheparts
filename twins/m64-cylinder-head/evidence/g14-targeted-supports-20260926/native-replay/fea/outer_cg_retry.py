#!/usr/bin/env python3
"""One private G14 CPU-CG retry on retained matrices; never rerun CCX or mesh."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ENTRY = HERE/'outer_candidate.py'
ENTRY_SHA = '221d59b684acc00b6b4feea1d28fc77e1e529b24e6396f5b21523b11c5f3f234'
if hashlib.sha256(ENTRY.read_bytes()).hexdigest() != ENTRY_SHA:
    raise ValueError('approved outer entry changed')
spec = importlib.util.spec_from_file_location('g14_outer_native', ENTRY)
outer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(outer)
g8, g9, g11 = outer.g8, outer.g9, outer.g11
reference, bench, np = outer.native.reference, outer.g9.bench, outer.g11.np
ORIGINAL = HERE/'candidate-outer-lower-2'
SUMMARY_SHA = '96eed3e18e3529b8f30d674c3413b6d9101a85abaa942d800ebc039042a1e14e'
CASE_NAME = 'native-mac-g14-outer_high_cheeks_lower_haunch_p-2'
NATIVE_REFERENCE = outer.REPO/'work/m64-g13/native-fea/run-1/summary-0001.json'
PLAN = ('x', 'minus_z')
REQUIRED = ('x.inp', 'x.dat', 'x.log', 'minus_z.inp', 'minus_z.dat', 'minus_z.log',
            'matrix.inp', 'matrix.sti', 'matrix.dof', 'matrix.log')


def failed_case_gate(summary, identity, proof):
    if (summary['status'] != 'failed' or summary['returncode'] != 1 or summary['result'] is not None
            or summary['id'] != outer.IDS[0] or summary['mesh_mm'] != 2.
            or summary['numerically_qualified'] is not False or summary['mesh_convergence_qualified'] is not False
            or summary['proof'] != proof or identity['proof'] != proof
            or identity['id'] != summary['id'] or identity['mesh_mm'] != summary['mesh_mm']
            or identity['step_sha256'] != summary['step_sha256']):
        raise ValueError('only the exact failed outer2mm execution may be retried')


def trust():
    if g8.sha256(ORIGINAL/'summary.json') != SUMMARY_SHA:
        raise ValueError('original failed summary changed or missing')
    args = SimpleNamespace(reference=NATIVE_REFERENCE, cad=outer.CAD, id=outer.IDS[0])
    _, variant, proof = outer.trust(args)
    summary = json.loads((ORIGINAL/'summary.json').read_text())
    identity = json.loads((ORIGINAL/'identity.json').read_text())
    failed_case_gate(summary, identity, proof)
    if summary['step_sha256'] != variant['step_sha256']:
        raise ValueError('retained STEP identity changed')
    hashes = summary['retained_artifacts_sha256']
    if any(CASE_NAME+'/'+name not in hashes for name in REQUIRED):
        raise ValueError('required immutable numerical input omitted')
    for name, digest in hashes.items():
        if g8.sha256(outer.g13.confined(ORIGINAL, name)) != digest:
            raise ValueError('original retained artifact changed: '+name)
    case = ORIGINAL/CASE_NAME
    for name in ('x', 'minus_z', 'matrix'):
        outer.g13.serial_log(case/(name+'.log'))
    if 'TimeoutError: bounded CG runtime exceeded' not in (ORIGINAL/'worker.log').read_text():
        raise ValueError('original failure was not the bounded CG timeout')
    texts = {name:(case/(name+'.inp')).read_text() for name in PLAN}
    prefix = texts['x'].split('*STEP\n')[0]
    expected_matrix = (prefix.replace('*SOLID SECTION', '*DENSITY\n2.7e-9\n*SOLID SECTION')
        + '*BOUNDARY\nSUPPORT,1,3\n*STEP\n*FREQUENCY,SOLVER=MATRIXSTORAGE\n*END STEP\n')
    if texts['minus_z'].split('*STEP\n')[0] != prefix or (case/'matrix.inp').read_text() != expected_matrix:
        raise ValueError('retained matrix is not the unchanged static-deck stiffness export')
    return dict(original_summary_sha256=SUMMARY_SHA, original_identity_sha256=g8.sha256(ORIGINAL/'identity.json'),
        original_proof=proof, input_sha256={n:hashes[CASE_NAME+'/'+n] for n in REQUIRED},
        original_failed_execution_preserved=True, source_sha256=g8.sha256(Path(__file__)))


def worker(args):
    proof = trust()
    identity = json.loads((args.output/'identity.json').read_text())
    if identity['proof'] != proof or any(os.environ.get(k) != '1' for k in outer.THREAD_ENV):
        raise ValueError('worker provenance or one-thread environment changed')
    case = ORIGINAL/CASE_NAME
    report = dict(classification='native_CPU_G14_retained_matrix_CG_retry_not_new_direct_FEA',
        recipe='G14-outer2mm-CPU-CG-900-v1', proof=proof, cases=[], complete=False,
        numerically_qualified=False, maximum_journal_motion_mm=None, error=None,
        CCX_rerun=False, meshing_rerun=False, CUDA_executed=False, original_failure_preserved=True,
        mesh_convergence_qualified=False, manufacturing_authorized=False, engine_start_authorized=False,
        assembled_stiffness_qualified=False, hot_material_qualified=False,
        input_geometry_and_loads_unchanged=True, CG_RHS_limit_seconds=900, worker_limit_seconds=2400)
    try:
        points, _, support = g9.deck((case/'x.inp').read_text())
        matrix, mapping = bench.read_matrix(case/'matrix.sti', case/'matrix.dof', points, support)
        for name in PLAN:
            row = dict(direction=name, numerical_crosscheck_passed=False, error=None)
            try:
                seconds = min(900., args.deadline-time.time()-30.)
                if seconds < 1:
                    raise TimeoutError('worker deadline reserve reached')
                _, loads, fixed = g9.deck((case/(name+'.inp')).read_text())
                if fixed != support:
                    raise ValueError('retained support changed between directions')
                rhs = g9.rhs_for(mapping, loads)
                print(json.dumps(dict(stage='retained_CPU_CG', direction=name, allowed_seconds=seconds)), flush=True)
                u, timing = bench.solve(matrix, rhs, 'cpu', max_seconds=seconds)
                residual = float(np.linalg.norm(matrix@u-rhs)/np.linalg.norm(rhs))
                solution = dict(u=u, passed=bool(timing['info']==0 and np.isfinite(u).all() and residual<=1e-8))
                compared = reference.compare(case, name, matrix, mapping, solution, rhs, points, support)
                row.update(solver=timing, relative_residual=residual, numerical_crosscheck_passed=compared['passed'],
                    mechanics=compared['mechanics'], fresh_direct=compared['agreement'],
                    comparison_method='unchanged g13_reference.compare', free_dofs=len(mapping), matrix_nnz=matrix.nnz)
            except Exception as exc:
                row['error'] = type(exc).__name__+': '+str(exc)
            g11.publish(args.output/(name+'-retry.json'), row)
            report['cases'].append(row)
            g11.publish(args.output/('checkpoint-%d.json'%len(report['cases'])), report)
            print(json.dumps(dict(direction=name, passed=row['numerical_crosscheck_passed'], error=row['error'])), flush=True)
        if trust() != proof:
            raise ValueError('inputs or runtime changed during retry')
        report['complete'] = tuple(r['direction'] for r in report['cases']) == PLAN
        report['numerically_qualified'] = g11.qualified_rows(report)
        if report['numerically_qualified']:
            report['maximum_journal_motion_mm'] = g11.motion(report)
    except Exception as exc:
        report['error'] = type(exc).__name__+': '+str(exc)
    finally:
        g11.publish(args.output/'case.json', report)
    return 0 if report['numerically_qualified'] else 2


def run(args):
    proof = trust()  # No output directory or process before all immutable inputs pass.
    if args.check:
        print(json.dumps(dict(check_only=True, proof=proof)), flush=True)
        return 0
    args.output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, args.output/'outer_cg_retry.py')
    g11.publish(args.output/'identity.json', dict(recipe='G14-outer2mm-CPU-CG-900-v1', proof=proof,
        CG_RHS_limit_seconds=900, worker_limit_seconds=2400, plan=PLAN, CCX_rerun=False,
        numerical_thread_environment=outer.THREAD_ENV))
    command = [sys.executable, str(Path(__file__).resolve()), '--worker', '--output', str(args.output.resolve()),
               '--deadline', str(time.time()+2400)]
    status, code, error, start = 'failed', None, None, time.monotonic()
    with (args.output/'worker.log').open('x') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            env=dict(os.environ, **outer.THREAD_ENV))
        try:
            code = process.wait(timeout=2400)
            status = 'completed' if code == 0 else 'failed'
        except subprocess.TimeoutExpired:
            status, error = 'timeout', 'whole retry worker exceeded2400seconds'
        except (KeyboardInterrupt, InterruptedError) as exc:
            status, error = 'interrupted', str(exc)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    result = json.loads((args.output/'case.json').read_text()) if (args.output/'case.json').is_file() else {}
    if status == 'completed' and not result:
        status, error = 'failed', 'worker returned without retry receipt'
    qualified = status == 'completed' and result.get('numerically_qualified') is True
    summary = dict(status=status, returncode=code, error=error, wall_seconds=time.monotonic()-start,
        proof=proof, numerically_qualified=qualified, original_failure_preserved=True, CCX_rerun=False,
        maximum_journal_motion_mm=result.get('maximum_journal_motion_mm') if qualified else None,
        mesh_convergence_qualified=False, manufacturing_authorized=False, engine_start_authorized=False,
        artifacts_sha256={p.name:g8.sha256(p) for p in sorted(args.output.iterdir()) if p.is_file()})
    g11.publish(args.output/'summary.json', summary)
    print(json.dumps(dict(status=status, numerically_qualified=qualified)), flush=True)
    return 0 if qualified else 2


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise InterruptedError('native CG retry interrupted')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--deadline', type=float, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(HERE) or args.output.resolve() == HERE or args.output.resolve().is_relative_to(ORIGINAL):
        parser.error('new private output beneath fea, outside original execution required')
    if args.worker:
        if args.deadline is None or not math.isfinite(args.deadline) or not 0 < args.deadline-time.time() <= 2400:
            parser.error('bounded internal worker deadline required')
        raise SystemExit(worker(args))
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(run(args))
