#!/usr/bin/env python3
"""Private G14 central follow-up CPU screen; one authorized candidate, no automatic refinement."""
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

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PRIOR = HERE/'candidate.py'
PRIOR_SHA = '1f365763eb0544c4d2b8cadadbfc3bfe90b4edc61b41c39eb98d8bf187b2e57f'
if hashlib.sha256(PRIOR.read_bytes()).hexdigest() != PRIOR_SHA:
    raise ValueError('approved G14 native entry changed')
spec = importlib.util.spec_from_file_location('g14_native_candidate_v1', PRIOR)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
native, g13, g11, g8, g9 = prior.native, prior.g13, prior.g11, prior.g8, prior.g9
CAD = HERE.parent/'cad-central-v2/receipt.json'
CAD_SHA = '853240d3f5eec4425940da2868b237637df3cc50bed6a339db62276fe2103f81'
CAD_SOURCE_SHA = '44c8dc5033d29416bc533afa3d5bedb27bee08531eaccaa234cc351f6cc1c9eb'
IDS = ('centre_spine68_local_under_journals', 'centre_spine68_t40')
THREAD_ENV = prior.THREAD_ENV


def inputs(path, ident):
    if ident not in IDS or g8.sha256(path) != CAD_SHA:
        raise ValueError('only the two pinned, accepted central candidates may be solved')
    baseline, previous, original = prior.inputs(prior.CAD, 'centre_spine68_t30')
    receipt = json.loads(path.read_text())
    if (receipt['complete'] is not True or receipt['error'] is not None
            or receipt['FEA_executed'] is not False or receipt['manufacturing_authorized'] is not False
            or receipt['engine_start_authorized'] is not False
            or receipt['material_or_boundary_conditions_changed'] is not False
            or receipt['prior_CAD_receipt_sha256'] != prior.CAD_SHA
            or receipt['prior_private_source_sha256'] != prior.CAD_SOURCE_SHA
            or receipt['source_sha256'] != CAD_SOURCE_SHA
            or receipt['G7_receipt_sha256'] != original['G7_receipt_sha256']
            or receipt['frozen_sources_sha256'] != original['frozen_cad_sources_sha256']
            or receipt['values'] != baseline['values']
            or receipt['baseline_step_sha256'] != previous['step_sha256']
            or tuple(r['id'] for r in receipt['variants']) != IDS
            or receipt['crank_samples_deg'] != list(range(0,720,5))):
        raise ValueError('complete exact central CAD and unchanged upstream chain required')
    for source in (HERE.parent/'g14_central_followup_private.py', path.parent/'g14_central_followup_private.py'):
        if g8.sha256(source) != CAD_SOURCE_SHA:
            raise ValueError('executed central CAD source changed')
    variants = {}
    for row in receipt['variants']:
        # Schema adapter only: every value comes from this pinned CAD receipt.
        interface = dict(id=row['id'], cad_accepted=row['cad_accepted'],
            step_sha256=row['step_sha256'], baseline_step_sha256=row['baseline_step_sha256'],
            journal_width_mm=row['journal_width_mm'], journal_diameter_mm=row['journal_diameter_mm'],
            first_1mm_difference_mm3=row['first_1mm_difference_mm3'],
            first_1mm_unchanged=g13.zero_difference(row['first_1mm_difference_mm3']))
        prior.accepted(row, interface, previous['step_sha256'])
        tools = row['existing_functional_tool_checks']
        if (set(tools) != {'central_mount_pilot_-1','central_mount_pilot_1'}
                or any(set(t) != {'new_material_overlap_mm3','baseline_overlap_mm3','total_overlap_mm3'}
                       or not all(native.bounded(v,1e-5) for v in t.values()) for t in tools.values())):
            raise ValueError('central mounting pilot tool audit failed')
        step = g13.confined(path.parent,row['step'])
        if step.suffix != '.step' or g8.sha256(step) != row['step_sha256']:
            raise ValueError('native central STEP changed')
        variants[row['id']] = dict(row, step_path=step, cad_receipt_sha256=CAD_SHA)
    proof = dict(cad_receipt_sha256=CAD_SHA, cad_source_sha256=CAD_SOURCE_SHA, prior_cad=original,
        journal_width_mm=11., existing_functional_tool_checks=variants[ident]['existing_functional_tool_checks'],
        mounting_and_maintenance_qualified=False,
        tool_caveat='Existing pilot tools are clear; full assembly and maintenance approach are not qualified')
    return baseline, variants[ident], proof


def trust(args):
    runtime = native.native_gate(args.reference)
    baseline, variant, cad = inputs(args.cad, args.id)
    return baseline, variant, dict(runtime=runtime, cad=cad, candidate_source_sha256=g8.sha256(Path(__file__)),
        reused_G14_entry_sha256=PRIOR_SHA, numerical_sources_sha256=g11.source_hashes())


def worker(args):
    baseline, variant, proof = trust(args)
    identity = json.loads((args.output/'identity.json').read_text())
    if (identity['proof'] != proof or identity['id'] != args.id or identity['mesh_mm'] != args.mesh
            or identity['step_sha256'] != variant['step_sha256']
            or any(os.environ.get(k) != '1' for k in THREAD_ENV)):
        raise ValueError('worker source, inputs, runtime or serial environment changed')
    os.environ['PATH'] = str(native.WRAPPER.parent)+os.pathsep+os.environ.get('PATH', '')
    case = args.output/('native-mac-g14-'+args.id+'-'+format(args.mesh, 'g')); case.mkdir()
    points, elements, support, weights, mesh = g11.mesh(variant['step_path'], args.mesh, baseline['values'], variant, case)
    loads = g11.forces(baseline, variant['component'])
    for name, direction in g11.DIRECTIONS:
        g8.solve(case, points, elements, support, weights, loads, direction, name)
        g13.serial_log(case/(name+'.log'))
    rows = g9.audit(case, tuple(n for n, _ in g11.DIRECTIONS), case, 'cpu')
    logs = {n:g13.serial_log(case/(n+'.log')) for n in ('x','minus_z','matrix')}
    if trust(args)[2] != proof:
        raise ValueError('native runtime or CAD changed during solve')
    result = dict(classification='native_arm64_macOS_CPU_G14_isolated_support_screen', id=args.id,
        component=variant['component'], mesh=mesh, backend='cpu', proof=proof, step_sha256=variant['step_sha256'],
        cad_receipt_sha256=CAD_SHA,
        journal_forces_N=loads, volume_mm3=variant['volume_mm3'], serial_logs=logs, cases=rows, complete=len(rows)==2,
        FEA_executed=True, CUDA_executed=False, G13_Linux_reference_promoted=False, manufacturing_authorized=False,
        engine_start_authorized=False, assembled_stiffness_qualified=False, hot_material_qualified=False,
        boundary_hypothesis='Unchanged whole bottom land fixed XYZ; generic E=70000 MPa, nu=0.33; not head contact, bolt preload or selected alloy',
        hashes={p.name:g8.sha256(p) for p in sorted(case.iterdir()) if p.is_file()})
    result['numerically_qualified'] = g11.qualified_rows(result)
    result['maximum_journal_motion_mm'] = g11.motion(result) if result['numerically_qualified'] else None
    result['mesh_convergence_qualified'] = False
    g11.publish(case/'case.json', result)


def run(args):
    _, variant, proof = trust(args)  # Fail before creating outputs or spawning.
    if args.check:
        print(json.dumps(dict(check_only=True, id=args.id, proof=proof)), flush=True)
        return 0
    args.output.mkdir(parents=True, exist_ok=False)
    provenance = args.output/'provenance'; provenance.mkdir()
    for source, name in ((Path(__file__), 'central_followup_candidate.py'), (PRIOR, 'g14-native-candidate.py'),
            (native.WRAPPER, 'ccx-wrapper'), (args.cad, 'cad.json'), (variant['step_path'], 'candidate.step'),
            (prior.CAD, 'prior-cad.json'), (prior.CAD.parent/'interface-proof.json','prior-interface-proof.json'),
            (HERE.parent/'g14_central_followup_private.py','g14_central_followup_private.py')):
        shutil.copyfile(source, provenance/name)
    identity = dict(id=args.id, mesh_mm=args.mesh, proof=proof, step_sha256=variant['step_sha256'],
        timeout_seconds=args.timeout, numerical_thread_environment=THREAD_ENV, CUDA_executed=False)
    g11.publish(args.output/'identity.json', identity)
    command = [sys.executable, str(Path(__file__).resolve()), '--worker', '--reference', str(args.reference.resolve()),
        '--cad', str(args.cad.resolve()), '--id', args.id, '--mesh', str(args.mesh),
        '--output', str(args.output.resolve()), '--timeout', str(args.timeout)]
    start, status, code, error = time.monotonic(), 'failed', None, None
    with (args.output/'worker.log').open('x') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                   env=dict(os.environ, **THREAD_ENV))
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
    result_path = args.output/('native-mac-g14-'+args.id+'-'+format(args.mesh, 'g'))/'case.json'
    if status == 'completed' and not result_path.is_file():
        status, error = 'failed', 'worker returned without case receipt'
    result = json.loads(result_path.read_text()) if result_path.is_file() else {}
    summary = dict(classification='native_Mac_G14_execution_not_physical_qualification', **identity,
        command=command, status=status, returncode=code, error=error, wall_seconds=time.monotonic()-start,
        FEA_executed=True if result else None, numerically_qualified=result.get('numerically_qualified',False),
        maximum_journal_motion_mm=result.get('maximum_journal_motion_mm'), mesh_convergence_qualified=False,
        result=str(result_path.relative_to(args.output)) if result else None,
        retained_artifacts_sha256={str(p.relative_to(args.output)):g8.sha256(p) for p in sorted(args.output.rglob('*')) if p.is_file()},
        manufacturing_authorized=False, engine_start_authorized=False)
    g11.publish(args.output/'summary.json', summary)
    print(json.dumps({k:summary[k] for k in ('status','numerically_qualified','maximum_journal_motion_mm')}), flush=True)
    return 0 if status == 'completed' else 2


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise InterruptedError('native G14 candidate controller interrupted')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--cad', type=Path, default=CAD)
    parser.add_argument('--id', choices=IDS, required=True)
    parser.add_argument('--mesh', type=float, choices=g13.SIZES, default=2.)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('--check', action='store_true', help='Trust gates only; never mesh or solve')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 0 < args.timeout <= 1800 or not args.output.resolve().is_relative_to(HERE) or args.output.resolve() == HERE:
        parser.error('new private output below fea and timeout <=1800s required')
    if args.worker:
        worker(args)
    else:
        signal.signal(signal.SIGTERM, interrupted)
        raise SystemExit(run(args))
