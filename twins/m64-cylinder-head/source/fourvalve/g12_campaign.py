#!/usr/bin/env python3
"""Bounded FEA of the two CAD-accepted G12 central supports; no engine release."""
import argparse
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

import g11_campaign as g11

g8, g9 = g11.g8, g11.g9
CAD_SHA256 = '1038c9a40bd005f8390b7ce806c51ad65323d6706c35c12844d01489e1fd4d83'
ACCEPTED = ('centre_w11_local24_foot24_h40', 'centre_w11_local28_foot30_h50')
SIZES = (2., 1.5, 1.)


def inputs(path):
    published = g8.REPO/'twins/m64-cylinder-head/evidence/g12-local-buttresses-20260926/cad.json'
    if g8.sha256(path) != CAD_SHA256 or g8.sha256(published) != CAD_SHA256:
        raise ValueError('G12 CAD receipt differs from published fingerprint')
    receipt = json.loads(path.read_text())
    baseline = json.loads(g8.BASELINE.read_text())
    expected = [(Path(__file__).with_name('g12_cad.py'), receipt['source_sha256']),
                (Path(__file__).with_name('g11_cad.py'), receipt['g11_source_sha256']),
                (g8.REPO/'twins/m64-cylinder-head/evidence/g11-support-stiffness-20260926/cad.json', receipt['g11_receipt_sha256']),
                (g8.BASELINE, receipt['g7_baseline_sha256'])]
    expected += [(g8.REPO/name, sha) for name, sha in baseline['source_sha256'].items()]
    if any(g8.sha256(p) != sha for p, sha in expected):
        raise ValueError('frozen source or upstream evidence fingerprint mismatch')
    variants = [v for v in receipt['variants'] if v['cad_accepted'] is True]
    if (receipt['complete'] is not True or receipt['values'] != baseline['values']
            or len(variants) != 2 or tuple(v['id'] for v in variants) != ACCEPTED):
        raise ValueError('exact two accepted G12 candidates required')
    for variant in variants:
        step = (path.parent/variant['step']).resolve()
        if (not step.is_relative_to(path.parent.resolve()) or step.suffix != '.step'
                or g8.sha256(step) != variant['step_sha256'] or variant['rejections']
                or variant['component'] != 'central_diaphragm' or variant['journal_width_mm'] != 11.):
            raise ValueError('invalid G12 STEP or journal definition')
    return receipt, baseline, {v['id']: v for v in variants}


def worker(args):
    if sys.platform != 'linux':
        raise ValueError('native Linux worker required')
    receipt, baseline, variants = inputs(args.cad)
    variant = variants[args.worker]  # CAD-rejected controls cannot enter the solver.
    args.output.mkdir(parents=True, exist_ok=False)
    points, elements, support, weights, mesh = g11.mesh(args.cad.parent/variant['step'], args.mesh, receipt['values'], variant, args.output)
    loads = g11.forces(baseline, variant['component'])
    for name, direction in g11.DIRECTIONS:
        g8.solve(args.output, points, elements, support, weights, loads, direction, name)
    if any((args.output.name, name) in g9.HISTORICAL for name, _ in g11.DIRECTIONS):
        raise ValueError('G12 case aliases historical evidence')
    rows = g9.audit(args.output, tuple(n for n, _ in g11.DIRECTIONS), args.output, args.backend)
    result = {'id': variant['id'], 'component': variant['component'], 'mesh': mesh, 'backend': args.backend,
              'cad_receipt_sha256': CAD_SHA256, 'step_sha256': variant['step_sha256'],
              'source_sha256': g11.source_hashes(), 'campaign_source_sha256': g8.sha256(Path(__file__)),
              'volume_mm3': variant['volume_mm3'], 'journal_forces_N': loads, 'cases': rows,
              'projected_land': variant['projected_land'],
              'boundary_hypothesis': 'Entire widened bottom foot fixed in XYZ, including any unsupported projected area; not head contact or preload validation.',
              'artifact_bytes': sum(p.stat().st_size for p in args.output.iterdir() if p.is_file()),
              'worker_peak_RSS_MiB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
              'maximum_child_RSS_MiB_not_sum': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss/1024,
              'complete': len(rows) == 2, 'manufacturing_authorized': False, 'engine_start_authorized': False,
              'assembled_stiffness_qualified': False,
              'hashes': {p.name: g8.sha256(p) for p in sorted(args.output.iterdir()) if p.is_file()}}
    g11.publish(args.output/'result.json', result)


def recover(root, record, variants, backend):
    path = (root/record['path']).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('checkpoint path escapes campaign')
    result = g11.verify_result(path, record['sha256'], CAD_SHA256, variants[record['id']], record['size_mm'], backend)
    if result['campaign_source_sha256'] != g8.sha256(Path(__file__)):
        raise ValueError('G12 campaign source changed')
    return result


def run(args):
    _, _, variants = inputs(args.cad)
    args.output.mkdir(parents=True, exist_ok=True)
    identity = {'cad_receipt_sha256': CAD_SHA256, 'campaign_source_sha256': g8.sha256(Path(__file__)),
                'reused_source_sha256': g11.source_hashes(), 'backend': args.backend}
    path = args.output/'identity.json'
    if path.exists():
        if json.loads(path.read_text()) != identity:
            raise ValueError('resume identity differs')
    else:
        if any(args.output.iterdir()):
            raise ValueError('new output must be empty')
        g11.publish(path, identity)
    checkpoints = sorted(args.output.glob('checkpoint-*.json'))
    records = json.loads(checkpoints[-1].read_text())['records'] if checkpoints else []
    keys = [(r['id'], r['size_mm']) for r in records]
    if len(set(keys)) != len(keys) or any(i not in ACCEPTED or s not in SIZES for i, s in keys):
        raise ValueError('duplicate or out-of-scope checkpoint case')
    results = {(r['id'], r['size_mm']): recover(args.output, r, variants, args.backend)
               for r in records if r['status'] == 'completed'}
    for index, size in enumerate(SIZES):
        for ident in ACCEPTED:
            if (ident, size) in keys:
                continue
            previous = results.get((ident, SIZES[index-1])) if index else None
            if index and (previous is None or not g11.qualified_rows(previous)):
                continue
            if time.time()+args.case_timeout+args.reserve_seconds > args.deadline:
                break
            base, attempt = f'{ident}-{size:g}-attempt', 1
            while (args.output/f'{base}{attempt}').exists() or (args.output/f'{base}{attempt}.log').exists():
                attempt += 1
            case = args.output/f'{base}{attempt}'
            command = [sys.executable, str(Path(__file__).resolve()), '--cad', str(args.cad.resolve()),
                       '--output', str(case.resolve()), '--backend', args.backend, '--worker', ident, '--mesh', str(size)]
            start = time.monotonic()
            with (args.output/f'{case.name}.log').open('x') as log:
                process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    code = process.wait(timeout=args.case_timeout)
                    status = 'completed' if code == 0 and (case/'result.json').exists() else 'failed'
                except subprocess.TimeoutExpired:
                    status, code = 'timeout', None
                finally:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
            record = {'id': ident, 'size_mm': size, 'status': status, 'returncode': code, 'wall_seconds': time.monotonic()-start}
            if status == 'completed':
                result_path = case/'result.json'
                record.update(path=str(result_path.relative_to(args.output)), sha256=g8.sha256(result_path))
                results[ident, size] = recover(args.output, record, variants, args.backend)
            records.append(record); keys.append((ident, size))
            g11.publish(args.output/f'checkpoint-{len(records):04d}.json', {'records': records})
            print(json.dumps(record), flush=True)
    assessments = {i: g11.assessment(results[i, 1.5], results[i, 1.]) for i in ACCEPTED if (i, 1.5) in results and (i, 1.) in results}
    passing = [i for i in ACCEPTED if assessments.get(i, {}).get('accepted') is True]
    report = {'classification': 'G12_generic_cold_isolated_central_support_FEA', **identity,
              'manufacturing_authorized': False, 'engine_start_authorized': False, 'assembled_stiffness_qualified': False,
              'hot_material_qualified': False, 'outer_supports_recomputed': False,
              'generic_material': {'E_MPa': g8.E, 'nu': g8.NU}, 'records': records, 'assessments': assessments,
              'selected_variant': min(passing, key=lambda i: variants[i]['volume_mm3']) if passing else None,
              'complete': len(results) == 6 and all(g11.qualified_rows(r) for r in results.values()),
              'boundary_hypothesis': 'Entire widened foot fixed in XYZ; enlarged clamp area is not validated assembled head contact.',
              'projected_lands': {i: v['projected_land'] for i, v in variants.items()}}
    number = len(list(args.output.glob('summary-*.json')))+1
    g11.publish(args.output/f'summary-{number:04d}.json', report)
    print(json.dumps({'complete': report['complete'], 'selected_variant': report['selected_variant']}), flush=True)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cad', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backend', choices=('cpu', 'cuda'), default='cuda')
    parser.add_argument('--deadline', type=float)
    parser.add_argument('--case-timeout', type=int, default=900)
    parser.add_argument('--reserve-seconds', type=int, default=180)
    parser.add_argument('--worker', choices=ACCEPTED, help=argparse.SUPPRESS)
    parser.add_argument('--mesh', type=float, choices=SIZES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if args.mesh is None:
            parser.error('worker mesh size required')
        worker(args)
    else:
        if args.deadline is None or not math.isfinite(args.deadline) or min(args.case_timeout, args.reserve_seconds) < 1:
            parser.error('finite deadline and positive time limits required')
        signal.signal(signal.SIGTERM, lambda number, frame: sys.exit(128+number))
        raise SystemExit(run(args))
