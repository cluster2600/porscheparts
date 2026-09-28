#!/usr/bin/env python3
"""G13 serial-runtime isolated-support screen; never an engine or print release."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

import g11_campaign as g11
import g13_reference as reference

g8, g9 = g11.g8, g11.g9
CENTRALS = tuple(f'centre_w11_spine60_t{w}' for w in (18, 24, 30))
OUTER = 'outer_d30_w30'
IDS, SIZES = CENTRALS+(OUTER,), (2., 1.5, 1.)
WORKSPACE = Path('/workspace/m64-g11')


def confined(root, name):
    path = (root/name).resolve()
    if Path(name).is_absolute() or not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError('artifact path escapes its receipt directory')
    return path


def zero_difference(row):
    return (set(row) == {'added_volume_mm3', 'removed_volume_mm3'}
            and all(math.isfinite(v) and abs(v) <= 1e-5 for v in row.values()))


def reference_gate(path, binary):
    summary = json.loads(path.read_text())
    rows = summary['rows']
    assessed = reference.assess(rows)
    if (summary.get('error') is not None or assessed['complete'] is not True
            or any(summary.get(k) != v for k, v in assessed.items())
            or not all(r['passed'] is True for r in rows if r['threads'] == 1)):
        raise ValueError('complete reference with every serial comparison passed required')
    identity_path = path.parent/'identity.json'
    identity = json.loads(identity_path.read_text())
    if (identity['recipe'] != reference.RECIPE or summary['recipe'] != reference.RECIPE
            or identity['source_sha256'] != g8.sha256(Path(reference.__file__))
            or identity['reused_sources_sha256'] != reference.SOURCES
            or identity['original_sha256'] != reference.INPUTS
            or identity['real_ccx_binary_sha256'] != g8.sha256(binary)):
        raise ValueError('reference source, original input, or native binary changed')
    reference.inputs(path.parent/'original-rejected')
    for row in rows:
        case = confined(path.parent, row['id'])
        if json.loads((case/'case.json').read_text()) != row:
            raise ValueError('reference row differs from retained case receipt')
        for name, digest in row['hashes'].items():
            if Path(name).name != name or g8.sha256(confined(case, name)) != digest:
                raise ValueError('reference artifact changed')
    return {'reference_summary_sha256': g8.sha256(path),
            'reference_identity_sha256': g8.sha256(identity_path),
            'reference_outcome': assessed['outcome'], 'serial_reference_passed': True,
            'real_ccx_binary_sha256': g8.sha256(binary)}


def inputs(path, outer_path):
    receipt = json.loads(path.read_text())
    baseline = json.loads(g8.BASELINE.read_text())
    evidence = g8.REPO/'twins/m64-cylinder-head/evidence'
    expected = [(Path(__file__).with_name('g13_cad.py'), receipt['source_sha256']),
                (Path(__file__).with_name('g11_cad.py'), receipt['g11_source_sha256']),
                (Path(__file__).with_name('g12_cad.py'), receipt['g12_source_sha256']),
                (g8.BASELINE, receipt['g7_baseline_sha256']),
                (evidence/'g11-support-stiffness-20260926/cad.json', receipt['g11_receipt_sha256']),
                (evidence/'g12-local-buttresses-20260926/cad.json', receipt['g12_receipt_sha256']),
                (outer_path, receipt['g11_receipt_sha256'])]
    expected += [(g8.REPO/name, digest) for name, digest in baseline['source_sha256'].items()]
    if any(g8.sha256(p) != digest for p, digest in expected):
        raise ValueError('CAD or frozen upstream source fingerprint mismatch')
    if (receipt['complete'] is not True or receipt['values'] != baseline['values']
            or tuple(v['id'] for v in receipt['variants']) != CENTRALS
            or receipt['head_axes_journals_oil_and_fasteners_unchanged'] is not True):
        raise ValueError('exact completed G13 CAD campaign required')
    outer_receipt = json.loads(outer_path.read_text())
    outer = next(v for v in outer_receipt['variants'] if v['id'] == OUTER)
    variants = {v['id']: dict(v, cad_receipt_sha256=g8.sha256(path),
                            step_path=confined(path.parent, v['step'])) for v in receipt['variants']}
    variants[OUTER] = dict(outer, cad_receipt_sha256=g8.sha256(outer_path),
                           step_path=confined(outer_path.parent, outer['step']))
    for ident, variant in variants.items():
        central = ident in CENTRALS
        if (variant['cad_accepted'] is not True or variant['rejections']
                or variant['component'] != ('central_diaphragm' if central else 'carrier_base_p')
                or variant['journal_width_mm'] != (11. if central else 8.)
                or variant['step_path'].suffix != '.step'
                or g8.sha256(variant['step_path']) != variant['step_sha256']
                or not math.isfinite(variant['volume_mm3']) or variant['volume_mm3'] <= 0):
            raise ValueError('CAD-rejected, changed, or invalid G13/outer candidate')
        if central and (variant['motion_samples_checked'] != 144
                        or variant['sampled_motion_interferences']
                        or not zero_difference(variant['bottom_land_difference'])
                        or set(variant['journal_neighbourhood_difference']) != {'intake', 'exhaust'}
                        or not all(zero_difference(v) for v in variant['journal_neighbourhood_difference'].values())):
            raise ValueError('unchanged support land and completed motion screen required')
    return receipt, baseline, variants


def runtime(args):
    if args.ccx_wrapper.name != 'ccx' or not os.access(args.ccx_wrapper, os.X_OK):
        raise ValueError('executable versioned serial bin/ccx wrapper required')
    proof = reference_gate(args.reference, args.ccx_binary)
    return dict(proof, ccx_wrapper_sha256=g8.sha256(args.ccx_wrapper),
                thread_policy='All CalculiX thread controls forced to one by versioned executable wrapper; pinned Python solvers unchanged')


def mirror_gate(receipt, root, outer):
    proof = receipt['outer_mirror_audit']
    if (proof['id'] != OUTER or proof['symmetry_accepted'] is not True
            or proof['transformation_matrix'] != [[1, 0, 0], [0, -1, 0], [0, 0, 1]]
            or proof['vector_cases'] != {'+x': [1, 0, 0], '-z': [0, 0, -1]}
            or proof['source_prior_step_sha256'] != outer['step_sha256']
            or proof['motion_samples_checked'] != 144 or proof['negative_static_interferences']
            or proof['sampled_motion_interferences']):
        raise ValueError('complete exact outer mirror proof required')
    if (set(proof['foot_mask_comparison_mm3']) != {'mirrored_fixed_land', 'positive_land_vs_G7', 'negative_land_vs_G7'}
            or set(proof['journal_mask_comparison_mm3']) != {'intake', 'exhaust'}):
        raise ValueError('complete outer mirror foot and journal masks required')
    diffs = [proof['native_difference_mm3'], *proof['foot_mask_comparison_mm3'].values(),
             *proof['journal_mask_comparison_mm3'].values()]
    if not all(zero_difference(row) for row in diffs):
        raise ValueError('outer mirrored geometry, foot or journal mask differs')
    if set(proof['files']) != {'p', 'm'}:
        raise ValueError('both mirrored STEP files required')
    for row in proof['files'].values():
        if row['BRep_valid'] is not True or row['solid_count'] != 1 or g8.sha256(confined(root, row['step'])) != row['step_sha256']:
            raise ValueError('outer mirror STEP fingerprint or topology changed')
    sidecar = root/'outer-original-step-equivalence.json'
    equivalence = json.loads(sidecar.read_text())
    hashes = {'g11_original': outer['step_sha256'], 'g13_rebuilt': proof['files']['p']['step_sha256'],
              'g13_mirror': proof['files']['m']['step_sha256']}
    if any(equivalence['files'][name]['sha256'] != digest for name, digest in hashes.items()):
        raise ValueError('original G11 STEP mirror equivalence fingerprint mismatch')
    for key in ('rebuilt_vs_original_mm3', 'negative_vs_original_mirrored_mm3'):
        if set(equivalence[key]) != {'added', 'removed'} or any(v != 0. for v in equivalence[key].values()):
            raise ValueError('G11 original STEP mirror equivalence failed')
    return {'accepted': True, 'negative_outer_method': 'exact_BRep_and_boundary_mirror_with_unchanged_vector_loads',
            'transformation_matrix': proof['transformation_matrix'],
            'original_step_equivalence_sha256': g8.sha256(sidecar),
            'mirrored_step_sha256': {side: row['step_sha256'] for side, row in proof['files'].items()}}


def serial_log(path):
    text = path.read_text()
    counts = sorted(set(map(int, re.findall(r'Using (?:up to )?(\d+) cpu\(s\)', text))))
    if counts != [1] or 'CalculiX Version 2.21' not in text or 'Job finished' not in text or '*ERROR' in text:
        raise ValueError('serial CalculiX 2.21 completion not verified: '+path.name)
    return {'observed_cpu_counts': counts, 'sha256': g8.sha256(path)}


def worker(args):
    if sys.platform != 'linux':
        raise ValueError('native Linux worker required')
    receipt, baseline, variants = inputs(args.cad, args.outer_cad)
    proof = runtime(args)
    os.environ['PATH'] = str(args.ccx_wrapper.resolve().parent)+os.pathsep+os.environ.get('PATH', '')
    variant = variants[args.worker]
    args.output.mkdir(parents=True, exist_ok=False)
    points, elements, support, weights, mesh = g11.mesh(variant['step_path'], args.mesh, receipt['values'], variant, args.output)
    loads = g11.forces(baseline, variant['component'])
    logs = {}
    for name, direction in g11.DIRECTIONS:
        g8.solve(args.output, points, elements, support, weights, loads, direction, name)
        logs[name] = serial_log(args.output/(name+'.log'))
    if any((args.output.name, name) in g9.HISTORICAL for name, _ in g11.DIRECTIONS):
        raise ValueError('G13 case aliases historical evidence')
    rows = g9.audit(args.output, tuple(n for n, _ in g11.DIRECTIONS), args.output, args.backend)
    logs['matrix'] = serial_log(args.output/'matrix.log')
    if runtime(args) != proof:
        raise ValueError('runtime changed during solve')
    result = dict(id=variant['id'], component=variant['component'], mesh=mesh, backend=args.backend,
        cad_receipt_sha256=variant['cad_receipt_sha256'], step_sha256=variant['step_sha256'],
        source_sha256=g11.source_hashes(), campaign_source_sha256=g8.sha256(Path(__file__)),
        runtime=proof, serial_logs=logs, volume_mm3=variant['volume_mm3'], journal_forces_N=loads,
        cases=rows, complete=len(rows) == 2, manufacturing_authorized=False, engine_start_authorized=False,
        assembled_stiffness_qualified=False,
        boundary_hypothesis='Inherited G11 whole bottom land fixed XYZ; not measured head contact, bolt preload, or hot assembly compliance.',
        hashes={p.name: g8.sha256(p) for p in sorted(args.output.iterdir()) if p.is_file()})
    g11.publish(args.output/'case.json', result)


def recover(root, record, variants, backend, proof):
    variant = variants[record['id']]
    path = confined(root, record['path'])
    result = g11.verify_result(path, record['sha256'], variant['cad_receipt_sha256'], variant, record['size_mm'], backend)
    if result['campaign_source_sha256'] != g8.sha256(Path(__file__)) or result['runtime'] != proof:
        raise ValueError('campaign or qualified runtime changed')
    if result['serial_logs'] != {name: serial_log(path.parent/(name+'.log')) for name in ('x', 'minus_z', 'matrix')}:
        raise ValueError('serial execution proof changed')
    return result


def choose(results, variants):
    eligible = [i for i in CENTRALS if (i, 2.) in results and g11.qualified_rows(results[i, 2.]) and g11.motion(results[i, 2.]) <= .04]
    margin = [i for i in eligible if g11.motion(results[i, 2.]) <= .035]
    central = (min(margin, key=lambda i: (variants[i]['volume_mm3'], i)) if margin else
               min(eligible, key=lambda i: (g11.motion(results[i, 2.]), variants[i]['volume_mm3'], i)) if eligible else None)
    outer = OUTER if (OUTER, 2.) in results and g11.qualified_rows(results[OUTER, 2.]) and g11.motion(results[OUTER, 2.]) <= .04 else None
    return {'central_diaphragm': central, 'carrier_base_p': outer}, (
        'smallest_volume_with_0.035mm_margin' if margin else
        'near_threshold_best_motion_without_0.035mm_margin' if eligible else 'no_central_below_0.040mm')


def run(args):
    receipt, _, variants = inputs(args.cad, args.outer_cad)
    proof = runtime(args)
    mirror = mirror_gate(receipt, args.cad.parent, variants[OUTER])
    args.output.mkdir(parents=True, exist_ok=True)
    identity = dict(cad_receipt_sha256=g8.sha256(args.cad), outer_cad_receipt_sha256=g8.sha256(args.outer_cad),
                    campaign_source_sha256=g8.sha256(Path(__file__)), source_sha256=g11.source_hashes(),
                    runtime=proof, backend=args.backend, outer_mirror=mirror)
    identity_path = args.output/'identity.json'
    if identity_path.exists():
        if json.loads(identity_path.read_text()) != identity:
            raise ValueError('resume identity differs')
    else:
        if any(args.output.iterdir()):
            raise ValueError('new output must be empty')
        g11.publish(identity_path, identity)
    checkpoints = sorted(args.output.glob('checkpoint-*.json'))
    records = json.loads(checkpoints[-1].read_text())['records'] if checkpoints else []
    keys = [(r['id'], r['size_mm']) for r in records]
    if len(set(keys)) != len(keys) or any(i not in IDS or s not in SIZES for i, s in keys):
        raise ValueError('duplicate or out-of-scope checkpoint')
    if any(r['status'] not in ('completed', 'failed', 'timeout') for r in records):
        raise ValueError('invalid checkpoint status')
    results = {(r['id'], r['size_mm']): recover(args.output, r, variants, args.backend, proof)
               for r in records if r['status'] == 'completed'}

    def snapshot(stem, value):
        if args.snapshots is not None:
            args.snapshots.mkdir(parents=True, exist_ok=True)
            number = max((int(p.stem.split('-')[1]) for p in args.snapshots.glob(stem+'-????.json')), default=0)+1
            g11.publish(args.snapshots/f'{stem}-{number:04d}.json', value)

    def execute(ident, size):
        if (ident, size) in keys:
            return
        if time.time()+args.case_timeout+args.reserve_seconds > args.deadline:
            return
        attempt = 1
        while (args.output/f'{ident}-{size:g}-attempt{attempt}').exists() or (args.output/f'{ident}-{size:g}-attempt{attempt}.log').exists():
            attempt += 1
        case = args.output/f'{ident}-{size:g}-attempt{attempt}'
        command = [sys.executable, str(Path(__file__).resolve()), '--output', str(case.resolve()),
                   '--backend', args.backend, '--worker', ident, '--mesh', str(size)]
        for name in ('cad', 'outer_cad', 'reference', 'ccx_wrapper', 'ccx_binary'):
            command += ['--'+name.replace('_', '-'), str(getattr(args, name).resolve())]
        start = time.monotonic()
        with (args.output/(case.name+'.log')).open('x') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=args.case_timeout)
                status = 'completed' if code == 0 and (case/'case.json').exists() else 'failed'
            except subprocess.TimeoutExpired:
                status, code = 'timeout', None
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
        record = dict(id=ident, size_mm=size, status=status, returncode=code, wall_seconds=time.monotonic()-start)
        if status == 'completed':
            path = case/'case.json'
            record.update(path=str(path.relative_to(args.output)), sha256=g8.sha256(path))
            result = recover(args.output, record, variants, args.backend, proof)
            results[ident, size] = result
            record.update(numerically_qualified=g11.qualified_rows(result), maximum_journal_motion_mm=g11.motion(result))
        records.append(record); keys.append((ident, size))
        g11.publish(args.output/f'checkpoint-{len(records):04d}.json', {'records': records})
        snapshot('checkpoint', {'records': records, 'campaign_identity': identity})
        print(json.dumps(record), flush=True)

    for ident in IDS:
        execute(ident, 2.)
    selected, selection_reason = choose(results, variants)
    for size, previous in ((1.5, 2.), (1., 1.5)):
        for ident in selected.values():
            prior = results.get((ident, previous))
            if prior and g11.qualified_rows(prior) and g11.motion(prior) <= .04:
                execute(ident, size)
    assessments = {i: g11.assessment(results[i, 1.5], results[i, 1.]) for i in selected.values()
                   if i is not None and (i, 1.5) in results and (i, 1.) in results}
    not_run = []
    for ident in IDS:
        for size in SIZES:
            if (ident, size) in keys:
                continue
            previous = results.get((ident, 2. if size == 1.5 else 1.5))
            reason = ('not_selected_by_coarse_screen' if size != 2. and ident not in selected.values() else
                      'previous_mesh_failed_or_above_0.040mm' if size != 2. and (previous is None or not g11.qualified_rows(previous) or g11.motion(previous) > .04) else
                      'deadline_reserve_insufficient')
            not_run.append(dict(id=ident, size_mm=size, status='not_run', reason=reason))
    complete = (all((i, 2.) in results and g11.qualified_rows(results[i, 2.]) for i in IDS)
                and all(i is not None and all((i, s) in results and g11.qualified_rows(results[i, s]) for s in (1.5, 1.)) for i in selected.values()))
    passed = {component: ident if assessments.get(ident, {}).get('accepted') is True else None
              for component, ident in selected.items()}
    report = dict(classification='G13_generic_cold_isolated_support_FEA_serial_runtime', **identity,
        records=records, not_run=not_run, refinement_candidates=selected, selection_reason=selection_reason,
        assessments=assessments, selected_pass=passed, complete=complete,
        central_and_positive_outer_qualified=all(passed.values()),
        all_supports_qualified=bool(complete and all(passed.values()) and mirror['accepted']),
        qualification_scope='Three isolated generic-cold supports, two journals, +x/−z envelope; negative outer by exact mirror, not a separately solved mesh or assembled engine.',
        generic_material={'E_MPa': g8.E, 'nu': g8.NU}, manufacturing_authorized=False,
        engine_start_authorized=False, assembled_stiffness_qualified=False, hot_material_qualified=False,
        boundary_hypothesis='G11 bottom land fixed XYZ, unchanged by G13 central spine; no head/contact/preload qualification.',
        baseline_support_land=receipt['baseline_support_land'])
    number = len(list(args.output.glob('summary-*.json')))+1
    g11.publish(args.output/f'summary-{number:04d}.json', report)
    snapshot('summary', report)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cad', 'outer-cad', 'reference', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--ccx-wrapper', type=Path, default=WORKSPACE/'serial-bin/ccx')
    parser.add_argument('--ccx-binary', type=Path, default=WORKSPACE/'ccx-runtime/usr/bin/ccx')
    parser.add_argument('--snapshots', type=Path, help='Optional existing root results directory for unchanged supervisor metadata collection')
    parser.add_argument('--backend', choices=('cpu', 'cuda'), default='cuda')
    parser.add_argument('--deadline', type=float)
    parser.add_argument('--case-timeout', type=int, default=1500)
    parser.add_argument('--reserve-seconds', type=int, default=180)
    parser.add_argument('--worker', choices=IDS, help=argparse.SUPPRESS)
    parser.add_argument('--mesh', type=float, choices=SIZES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if args.mesh is None:
            parser.error('worker mesh required')
        worker(args)
    else:
        if args.deadline is None or not math.isfinite(args.deadline) or not 0 < args.case_timeout <= 1800 or args.reserve_seconds < 1:
            parser.error('finite deadline, bounded case timeout and positive reserve required')
        signal.signal(signal.SIGTERM, lambda number, frame: sys.exit(128+number))
        raise SystemExit(run(args))
