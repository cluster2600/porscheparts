#!/usr/bin/env python3
"""G13 thread-policy diagnostic on one frozen failed G12 deck, not a new design."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

import numpy as np
import g9_reference_campaign as g9

g8, bench = g9.g8, g9.bench
RECIPE = 'G13-B1.5-repeat-v1'
CCX_BINARY_SHA = '6adaabf5bf0382fc2bfd692b984320ed375dba777f7dc8297562f818043faa1b'
INPUTS = {'x.inp': 'd51f1343152d49bafef796cd257210c82dd6dc891df7d29e898528a0c9b94c84',
          'x.dat': 'b44e5f0916dec97181ba6d1e0f799757ec67b0a418693b1ee731a2afd823e520',
          'minus_z.inp': 'd5e2d625ec1f65f56e9a0f8896a43505ccec1a474f887dfd2400dc96bb09dc08',
          'minus_z.dat': '88cedaec685532ed97aa50e697f4f3987635251c5970f32b1edc6bf19fabe703'}
SOURCES = {'twins/m64-cylinder-head/source/fourvalve/'+n: h for n,h in {
    'g8_pilot.py': 'f6f3d1fe77c0a701bb1f75926cd4ac8cba3ee6cc9c3337967740d30ad85fee92',
    'g9_reference_campaign.py': 'ed6a2b21d89030ba39fc393f8a218bbbf328eceda49ce6bed361273bd2d8170b',
    'g8_matrix_benchmark.py': '4a98a110df2c4698b3ac0a74fb0dd1cb200c946fd9fa9a8748f6bd0e10c981cd',
    'g8_iterative_retry.py': '8600f234e60036668dc3a8f7f005c570638ea4cfc7a60c1327b86a534fa01963'}.items()}
SOURCES['twins/reference-917-engine/source/run_f37_carrier_calculix.py'] = '54e3478e219875872092cacb281dd12e640126cbed9273e8d82cd46d36fa2b13'
PLAN = (('t4-z-r1', 'minus_z', 4), ('t4-z-r2', 'minus_z', 4),
        ('t1-z-r1', 'minus_z', 1), ('t1-z-r2', 'minus_z', 1), ('t1-x-control', 'x', 1))
THREAD_KEYS = ('OMP_NUM_THREADS', 'CCX_NPROC_EQUATION_SOLVER', 'CCX_NPROC_STIFFNESS', 'CCX_NPROC_RESULTS', 'NUMBER_OF_CPUS')


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def publish(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def inputs(path):
    for name, expected in INPUTS.items():
        if (path/name).is_symlink() or sha(path/name) != expected:
            raise ValueError('original G12 input fingerprint mismatch: '+name)
    for name, expected in SOURCES.items():
        if sha(g8.REPO/name) != expected:
            raise ValueError('frozen source fingerprint mismatch: '+name)
    texts = {n: (path/(n+'.inp')).read_text() for n in ('x', 'minus_z')}
    if texts['x'].split('*STEP\n')[0] != texts['minus_z'].split('*STEP\n')[0]:
        raise ValueError('different stiffness geometry/material')
    return texts


def remaining(args, cap):
    seconds = min(cap, args.deadline-time.time()-30)
    if seconds < 5:
        raise TimeoutError('deadline reached; reserve kept for receipts/collection')
    return seconds


def ccx(case, name, threads, timeout):
    if threads not in (1, 4) or timeout <= 0:
        raise ValueError('bounded one/four-thread diagnostic only')
    env = dict(os.environ, **{k: str(threads) for k in THREAD_KEYS}, OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    start = time.monotonic()
    with (case/(name+'.log')).open('x') as log:
        process = subprocess.Popen(['ccx', name], cwd=case, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True, env=env)
        try:
            code = process.wait(timeout=timeout)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    text = (case/(name+'.log')).read_text()
    observed = set(map(int, re.findall(r'Using (?:up to )?(\d+) cpu\(s\)', text)))
    if (code or '*ERROR' in text or 'Job finished' not in text
            or 'CalculiX Version 2.21' not in text or observed != {threads}):
        raise ValueError('CalculiX failed: '+str(case/name))
    return {'seconds': time.monotonic()-start, 'threads': threads,
            'thread_environment': {k: env[k] for k in THREAD_KEYS}, 'observed_cpu_counts': sorted(observed), 'exit_code': code}


def assess(rows):
    complete = (tuple((r['id'], r['direction'], r['threads']) for r in rows) == PLAN
                and all(r.get('compared') for r in rows))
    parallel = [r for r in rows if r['threads'] == 4]
    serial = [r for r in rows if r['threads'] == 1]
    candidate = complete and all(r['passed'] for r in serial) and any(not r['passed'] for r in parallel)
    outcome = ('serial_runtime_candidate_v1_not_causal_proof' if candidate else
               'inconsistency_not_reproduced' if complete and all(r['passed'] for r in rows) else
               'unresolved_no_runtime_selected')
    return {'complete': complete, 'outcome': outcome, 'serial_runtime_candidate': bool(candidate),
            'original_failure_preserved': True, 'causal_SPOOLES_race_proven': False,
            'manufacturing_authorized': False, 'engine_start_authorized': False}


def compare(case, name, matrix, mapping, solution, rhs, points, support):
    _, loads, fixed = g9.deck((case/(name+'.inp')).read_text())
    if fixed != support or not np.array_equal(g9.rhs_for(mapping, loads), rhs):
        raise ValueError('reference load/support mismatch')
    reference, mechanics = g9.mechanics(case, name, points, loads, support)
    agreement = bench.comparison(matrix, rhs, mapping, solution['u'], reference)
    passed = (solution['passed'] and mechanics['equilibrium_passed']
              and agreement['max_nodal_difference_over_max_reference_U'] <= 1e-4
              and agreement['printed_dat_relative_residual'] <= agreement['printed_dat_rounding_residual_bound'])
    return dict(compared=True, passed=bool(passed), mechanics=mechanics, agreement=agreement)


def run(args):
    if sys.platform != 'linux' or not math.isfinite(args.deadline) or not 0 < args.case_timeout <= 900:
        raise ValueError('native Linux, finite deadline and case timeout <=900s required')
    texts = inputs(args.input)
    if sha(args.ccx_binary) != CCX_BINARY_SHA:
        raise ValueError('native CCX binary fingerprint differs from archived G12 runtime')
    remaining(args, args.case_timeout)
    args.output.mkdir(parents=True, exist_ok=False)
    provenance = args.output/'provenance'; provenance.mkdir()
    shutil.copyfile(__file__, provenance/'g13_reference.py')
    original = args.output/'original-rejected'; original.mkdir()
    for name in INPUTS:
        shutil.copyfile(args.input/name, original/name)
    inputs(original)
    binary = shutil.which('ccx')
    if not binary:
        raise ValueError('native ccx required')
    publish(args.output/'identity.json', dict(recipe=RECIPE, source_sha256=sha(Path(__file__)),
            reused_sources_sha256=SOURCES, original_sha256=INPUTS, ccx_entrypoint_sha256=sha(Path(binary)),
            real_ccx_binary_sha256=sha(args.ccx_binary),
            plan=PLAN, matrix_export_threads=1, CUDA_RHS_solves=2, deadline=args.deadline,
            case_timeout=args.case_timeout, original_failure_preserved=True,
            timeout_scope='CCX process groups have hard wait timeouts; CUDA uses a CG callback. Launcher deadline and independent rental guard must bound a stalled GPU kernel.',
            thread_policy_reference='https://www.dhondt.de/ccx_2.21.pdf#page=12'))
    rows, reference, error = [], {}, None
    try:
        for label, name, threads in PLAN:
            case = args.output/label; case.mkdir()
            shutil.copyfile(original/(name+'.inp'), case/(name+'.inp'))
            row = dict(id=label, direction=name, threads=threads, compared=False, passed=False)
            try:
                row['direct'] = ccx(case, name, threads, remaining(args, args.case_timeout))
            except (ValueError, subprocess.TimeoutExpired) as exc:
                row['error'] = type(exc).__name__+': '+str(exc)
            publish(case/'direct-receipt.json', row)
            if not reference:
                points, _, support = g9.deck(texts['x'])
                matrix_case = args.output/'matrix'; matrix_case.mkdir()
                prefix = texts['x'].split('*STEP\n')[0]
                with (matrix_case/'matrix.inp').open('x') as stream:
                    stream.write(prefix.replace('*SOLID SECTION', '*DENSITY\n2.7e-9\n*SOLID SECTION')
                                 + '*BOUNDARY\nSUPPORT,1,3\n*STEP\n*FREQUENCY,SOLVER=MATRIXSTORAGE\n*END STEP\n')
                export = ccx(matrix_case, 'matrix', 1, remaining(args, args.case_timeout))
                matrix, mapping = bench.read_matrix(matrix_case/'matrix.sti', matrix_case/'matrix.dof', points, support)
                matrix_proof = {p.name: sha(p) for p in matrix_case.iterdir() if p.is_file()}
                for direction in ('x', 'minus_z'):
                    rhs = g9.rhs_for(mapping, g9.deck(texts[direction])[1])
                    u, timing = bench.solve(matrix, rhs, 'cuda', max_seconds=remaining(args, 300))
                    residual = float(np.linalg.norm(matrix@u-rhs)/np.linalg.norm(rhs))
                    good = timing['info'] == 0 and np.isfinite(u).all() and residual <= 1e-8
                    reference[direction] = dict(u=u, rhs=rhs, passed=bool(good))
                    proof = dict(direction=direction, timing=timing, relative_residual=residual,
                                 reference_passed=bool(good), matrix_export=export, matrix_sha256=matrix_proof)
                    proof['original_rejected_comparison'] = compare(original, direction, matrix, mapping,
                                                                   reference[direction], rhs, points, support)
                    publish(matrix_case/(direction+'-reference.json'), proof)
                if not all(v['passed'] for v in reference.values()):
                    raise ValueError('fresh CUDA reference failed unchanged residual gate')
            if 'error' not in row:
                try:
                    row.update(compare(case, name, matrix, mapping, reference[name], reference[name]['rhs'], points, support))
                except ValueError as exc:
                    row['error'] = str(exc)
            row['hashes'] = {p.name: sha(p) for p in case.iterdir() if p.is_file()}
            publish(case/'case.json', row)
            rows.append(row)
            publish(args.output/('checkpoint-%02d.json' % len(rows)), dict(rows=rows, **assess(rows)))
            print(json.dumps({'id': label, 'passed': row['passed'], 'compared': row['compared']}), flush=True)
    except (Exception, KeyboardInterrupt) as exc:
        error = type(exc).__name__+': '+str(exc)
    finally:
        publish(args.output/'summary-0001.json', dict(recipe=RECIPE, rows=rows, error=error, **assess(rows)))
    return 0 if error is None and len(rows) == len(PLAN) else 2


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise InterruptedError('controller interrupted; no result promotion')
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--deadline', type=float, required=True)
    parser.add_argument('--case-timeout', type=int, default=900)
    parser.add_argument('--ccx-binary', type=Path, default=Path('/workspace/m64-g11/ccx-runtime/usr/bin/ccx'))
    raise SystemExit(run(parser.parse_args()))
