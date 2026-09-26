#!/usr/bin/env python3
"""Private G14 native CPU screen; one authorized candidate, no automatic refinement."""
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
PRIOR = REPO/'work/m64-g13/native-fea/candidate.py'
PRIOR_SHA = '1be80678849d76a5e34b82bb088599f9bef92f567ca624efa905976657cbf77b'
if hashlib.sha256(PRIOR.read_bytes()).hexdigest() != PRIOR_SHA:
    raise ValueError('approved native trust boundary changed')
spec = importlib.util.spec_from_file_location('g13_native_candidate', PRIOR)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
g13, g11, g8, g9 = native.g13, native.g11, native.g8, native.g9
CAD = HERE.parent/'cad-v1/receipt.json'
CAD_SHA = '3637a51b2d9fa03d97dd7316a7e6b281bb17db29d677ab204a3fade10420b905'
CAD_SOURCE_SHA = '612c412f2875d4302d2b88d533dd46abe1183ebffd74c30472ae011dc76c4f0f'
INTERFACE_SHA = '81bb801447f8e91f7a6b4756850f2a089200d703aaefcc72b7c5c49141a7abd2'
INTERFACE_SOURCE_SHA = '5cc251678788886fa1508572ed3310f5228bda6f6e00971f1aea1dc1e4a09316'
IDS = ('centre_spine68_t30', 'centre_spine70_shoulder_t30', 'outer_high_cheeks_p')
ALL_IDS = ('centre_spine70_t30', *IDS, 'outer_high_cheeks_m')
THREAD_ENV = {k: '1' for k in (*native.reference.THREAD_KEYS, 'OPENBLAS_NUM_THREADS',
                              'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')}


def accepted(row, interface, baseline_sha):
    central = row['id'].startswith('centre_')
    component = 'central_diaphragm' if central else 'carrier_base_'+row['id'][-1]
    if (row['cad_accepted'] is not True or row['rejections'] or row['component'] != component
            or row['BRep_valid'] is not True or row['solid_count'] != 1
            or row['motion_samples_checked'] != 144 or row['sampled_motion_interferences']
            or row['static_interferences'] or not native.bounded(row['volume_mm3'], math.inf)
            or row['volume_mm3'] <= 0 or row['closed_void_check']['no_enclosed_void_detected'] is not True):
        raise ValueError('CAD-rejected, incomplete, or invalid candidate')
    if (not g13.zero_difference(row['bottom_land_difference'])
            or set(row['journal_neighbourhood_difference']) != {'intake', 'exhaust'}
            or not all(g13.zero_difference(v) for v in row['journal_neighbourhood_difference'].values())
            or interface['id'] != row['id'] or interface['cad_accepted'] is not True
            or interface['step_sha256'] != row['step_sha256']
            or interface['baseline_step_sha256'] != baseline_sha
            or interface['journal_width_mm'] != (11. if central else 8.)
            or interface['journal_diameter_mm'] != 12.58
            or interface['first_1mm_unchanged'] is not True
            or not g13.zero_difference(interface['first_1mm_difference_mm3'])):
        raise ValueError('journal bands or unchanged bottom support proof failed')
    if (set(row['oil_paths']) != ({'intake', 'exhaust'} if central else {'intake', 'exhaust', 'return'})
            or any(p['tool_connected_solids'] != 1 or not native.bounded(p['residual_solid_mm3'], 1e-5)
                   for p in row['oil_paths'].values())):
        raise ValueError('oil passage audit failed')


def inputs(path, ident):
    if ident not in IDS:
        raise ValueError('only the three accepted positive-side candidates may be solved')
    interface_path = path.parent/'interface-proof.json'
    if g8.sha256(path) != CAD_SHA or g8.sha256(interface_path) != INTERFACE_SHA:
        raise ValueError('approved G14 CAD receipt or interface proof changed')
    receipt = json.loads(path.read_text()); interfaces = json.loads(interface_path.read_text())
    previous, baseline, prior_variants = g13.inputs(native.CAD, native.OUTER_CAD)
    old_mirror = g13.mirror_gate(previous, native.CAD.parent, prior_variants[g13.OUTER])
    if (receipt['complete'] is not True or receipt['error'] is not None
            or receipt['FEA_executed'] is not False or receipt['manufacturing_authorized'] is not False
            or receipt['engine_start_authorized'] is not False
            or receipt['G7_receipt_sha256'] != g8.sha256(g8.BASELINE)
            or receipt['G7_receipt_sha256'] != previous['g7_baseline_sha256']
            or receipt['source_sha256'] != CAD_SOURCE_SHA
            or tuple(v['id'] for v in receipt['variants']) != ALL_IDS
            or receipt['crank_samples_deg'] != list(range(0, 720, 5))):
        raise ValueError('complete exact G14 CAD and accepted G7 baseline required')
    source_map = dict(baseline['source_sha256'], **{
        'twins/m64-cylinder-head/source/fourvalve/g11_cad.py': previous['g11_source_sha256'],
        'twins/m64-cylinder-head/source/fourvalve/g13_cad.py': previous['source_sha256']})
    if receipt['frozen_sources_sha256'] != source_map:
        raise ValueError('frozen CAD dependency map differs')
    expected = [(REPO/n, sha) for n, sha in source_map.items()]
    expected += [(HERE.parent/'g14_cad_private.py', CAD_SOURCE_SHA),
                 (path.parent/'g14_cad_private.py', CAD_SOURCE_SHA),
                 (HERE.parent/'interface_proof.py', INTERFACE_SOURCE_SHA), (PRIOR, PRIOR_SHA)]
    if any(g8.sha256(p) != sha for p, sha in expected):
        raise ValueError('executed CAD or native source changed')
    if (interfaces['complete'] is not True or interfaces['source_sha256'] != INTERFACE_SOURCE_SHA
            or interfaces['cad_receipt_sha256'] != CAD_SHA or interfaces['values'] != baseline['values']
            or interfaces['G11_receipt_sha256'] != g8.sha256(native.OUTER_CAD)
            or interfaces['G13_receipt_sha256'] != g8.sha256(native.CAD)
            or tuple(v['id'] for v in interfaces['variants']) != ALL_IDS):
        raise ValueError('interface replay is not bound to the accepted CAD chain')
    old11 = json.loads(native.OUTER_CAD.read_text())
    old_centre = next(v for v in old11['variants'] if v['id'] == 'centre_w11')
    if g8.sha256(g13.confined(native.OUTER_CAD.parent, old_centre['step'])) != old_centre['step_sha256']:
        raise ValueError('central reference STEP changed')
    variants = {}
    for row, face in zip(receipt['variants'][1:], interfaces['variants'][1:]):
        central = row['component'] == 'central_diaphragm'
        base_sha = old_centre['step_sha256'] if central else old_mirror['mirrored_step_sha256'][row['id'][-1]]
        accepted(row, face, base_sha)
        step = g13.confined(path.parent, row['step'])
        if step.suffix != '.step' or g8.sha256(step) != row['step_sha256']:
            raise ValueError('native STEP changed')
        variants[row['id']] = dict(row, step_path=step, journal_width_mm=face['journal_width_mm'],
                                  cad_receipt_sha256=CAD_SHA)
    if not g13.zero_difference(receipt['outer_independent_mirror_difference_mm3']):
        raise ValueError('independently generated outer mirror differs')
    # Whole BRep mirror + unchanged journal neighbourhoods/first millimetre +
    # previously proved baseline masks imply the same mirrored FE selections.
    mirror = dict(accepted=True, transformation_matrix=[[1,0,0],[0,-1,0],[0,0,1]],
        vector_cases={'+x':[1,0,0], '-z':[0,0,-1]}, original_mirror=old_mirror,
        g14_step_sha256={s:variants['outer_high_cheeks_'+s]['step_sha256'] for s in ('p','m')},
        proof='Native whole-BRep mirror, unchanged journal neighbourhoods and first 1mm, chained to proved baseline masks; negative FE not executed')
    proof = dict(cad_receipt_sha256=CAD_SHA, interface_proof_sha256=INTERFACE_SHA,
        cad_source_sha256=CAD_SOURCE_SHA, interface_source_sha256=INTERFACE_SOURCE_SHA,
        G7_receipt_sha256=g8.sha256(g8.BASELINE), frozen_cad_sources_sha256=source_map,
        journal_width_mm=variants[ident]['journal_width_mm'], outer_mirror=mirror)
    return baseline, variants[ident], proof


def trust(args):
    runtime = native.native_gate(args.reference)
    baseline, variant, cad = inputs(args.cad, args.id)
    return baseline, variant, dict(runtime=runtime, cad=cad, candidate_source_sha256=g8.sha256(Path(__file__)),
        reused_native_source_sha256=PRIOR_SHA, numerical_sources_sha256=g11.source_hashes())


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
    for source, name in ((Path(__file__), 'candidate.py'), (PRIOR, 'g13-native-candidate.py'),
            (native.WRAPPER, 'ccx-wrapper'), (args.cad, 'cad.json'), (variant['step_path'], 'candidate.step'),
            (args.cad.parent/'interface-proof.json','interface-proof.json'),
            (HERE.parent/'g14_cad_private.py','g14_cad_private.py'), (HERE.parent/'interface_proof.py','interface_proof.py')):
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
