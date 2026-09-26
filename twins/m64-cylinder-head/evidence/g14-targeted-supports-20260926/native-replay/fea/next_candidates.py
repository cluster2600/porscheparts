#!/usr/bin/env python3
"""Private G14 two-candidate CPU recipe with explicit longer CG timebox; one authorized candidate, no automatic refinement."""
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
def load_entry(name, digest):
    path = HERE/name
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('approved native entry changed: '+name)
    spec = importlib.util.spec_from_file_location(name[:-3], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OUTER_SHA = '221d59b684acc00b6b4feea1d28fc77e1e529b24e6396f5b21523b11c5f3f234'
CENTRAL_SHA = 'dfd55462a13c5ec7678c2554380963d4bddae9c31b312529edbe4e07245f6018'
outer = load_entry('outer_candidate.py', OUTER_SHA)
central = load_entry('central_followup_candidate.py', CENTRAL_SHA)
native, g13, g11, g8, g9 = outer.native, outer.g13, outer.g11, outer.g8, outer.g9
core, reference, bench, np = outer.prior, outer.native.reference, outer.g9.bench, outer.g11.np
THREAD_ENV = outer.THREAD_ENV
RECIPE = 'G14-native-coarse-CPU-CG900-worker3600-v1'
CENTRE, EXTERIOR = 'centre_spine68_t40_root2', 'outer_high_cheeks_extended_haunch_p'
IDS = (CENTRE, EXTERIOR)
SPECS = {
    CENTRE: dict(folder='cad-central-root-v1', receipt='ec14ff714b2042b26941120d26d27e0288d7015f47265af250a30f8ba0324f01',
        source='g14_central_root_private.py', source_sha='fc634708cdf82a21232f60add7ffcf173b3f8c6d587c2a11c6fa87409fe21fbe',
        probe='fea/central-root-fields.json', probe_sha='9a5fe2259ef65544a148ebc99d5c613aa5a2a61c95fa2f4ac592b0dc35c89594'),
    EXTERIOR: dict(folder='cad-extended-v1', receipt='f495427952c68eefd8b31c1a0b43a32a83515fbb8acf334ad70674d093ea97e6',
        source='g14_extended_haunch_private.py', source_sha='f97eb345ec66a5d6de36db078dbfdf0df2ce8401f803dc272b5716037886dded',
        probe='outer-next-field-bands.json', probe_sha='1adf7df6d42f0c951261471bb4624136e9e5ea8b5bb42b6340e260211402cd19')}
COMBINED = HERE.parent/'combined-candidate-clearance-v1.json'
COMBINED_SHA = 'f81ea34eb31a01350435839ec44cd3f140976c00b1ace2d77d3091681ed106fd'
COMBINED_SOURCE_SHA = '0949dc724fb7f2110ba45a46746c7d196269e2a19c7c4e753f90b9445aa1d957'


def combined_gate():
    if (g8.sha256(COMBINED) != COMBINED_SHA
            or g8.sha256(HERE.parent/'check_combined_candidates.py') != COMBINED_SOURCE_SHA):
        raise ValueError('approved combined-candidate geometry proof changed')
    proof = json.loads(COMBINED.read_text())
    names = (CENTRE, EXTERIOR, EXTERIOR[:-1]+'m')
    pairs = {(names[0],names[1]),(names[0],names[2]),(names[1],names[2])}
    if (proof['source_sha256'] != COMBINED_SOURCE_SHA or proof['pairwise_no_intersection'] is not True
            or tuple(r['id'] for r in proof['components']) != names
            or {(r['first'],r['second']) for r in proof['pairs']} != pairs or len(proof['pairs']) != 3
            or any(not native.bounded(r['intersection_volume_mm3'],1e-5) for r in proof['pairs'])
            or proof['G7_receipt_sha256'] != g8.sha256(g8.BASELINE)
            or any(g8.sha256(REPO/n) != sha for n,sha in proof['frozen_sources_sha256'].items())):
        raise ValueError('combined candidate coexistence proof failed')
    for row in proof['components']:
        spec = SPECS[CENTRE if row['id']==CENTRE else EXTERIOR]
        path = HERE.parent/spec['folder']/'receipt.json'
        receipt = json.loads(path.read_text())
        expected = next(v for v in receipt['variants'] if v['id']==row['id'])
        if (g8.sha256(path) != spec['receipt'] or row['CAD_receipt_sha256'] != spec['receipt']
                or row['source_sha256'] != spec['source_sha'] or row['individual_sampled_poses'] != 144
                or row['step_sha256'] != expected['step_sha256']
                or g8.sha256(g13.confined(REPO,row['step'])) != row['step_sha256']):
            raise ValueError('combined proof STEP or CAD binding changed')
    return dict(receipt_sha256=COMBINED_SHA, pairwise_no_intersection=True,
                continuous_or_deformed_clearance_qualified=False, assembled_stiffness_qualified=False)


def inputs(ident, path=None):
    if ident not in IDS:
        raise ValueError('exactly the two approved CAD hypotheses are in scope')
    spec = SPECS[ident]; is_central = ident == CENTRE
    path = path or HERE.parent/spec['folder']/'receipt.json'
    if g8.sha256(path) != spec['receipt']:
        raise ValueError('approved new CAD receipt changed')
    # These are the two specific upstream CAD gates, not a configurable CAD loader.
    if is_central:
        baseline, previous, original = central.inputs(central.CAD,'centre_spine68_t40')
        helper_map = {'g14_central_followup_private.py':central.CAD_SOURCE_SHA,
                      'g14_cad_private.py':core.CAD_SOURCE_SHA}
        prior_sha, ids = central.CAD_SHA, (CENTRE,)
        step_hashes = {CENTRE:previous['step_sha256']}
    else:
        baseline, previous, original = outer.inputs(outer.CAD,outer.IDS[0])
        helper_map = {'g14_lower_cheeks_private.py':outer.CAD_SOURCE_SHA,
                      'g14_cad_private.py':core.CAD_SOURCE_SHA}
        prior_sha, ids = outer.CAD_SHA, (EXTERIOR,EXTERIOR[:-1]+'m')
        step_hashes = {name:original['outer_mirror']['g14_step_sha256'][name[-1]] for name in ids}
    upstream = original['prior_cad']
    receipt = json.loads(path.read_text())
    if (receipt['complete'] is not True or receipt['error'] is not None
            or receipt['FEA_executed'] is not False or receipt['manufacturing_authorized'] is not False
            or receipt['engine_start_authorized'] is not False
            or receipt['prior_CAD_receipt_sha256'] != prior_sha
            or receipt['source_sha256'] != spec['source_sha']
            or receipt['field_probe_sha256'] != spec['probe_sha']
            or receipt['private_helper_sha256'] != helper_map
            or receipt['G7_receipt_sha256'] != upstream['G7_receipt_sha256']
            or receipt['frozen_sources_sha256'] != upstream['frozen_cad_sources_sha256']
            or tuple(v['id'] for v in receipt['variants']) != ids
            or receipt['crank_samples_deg'] != list(range(0,720,5))):
        raise ValueError('completed exact CAD and immutable upstream chain required')
    if is_central and (receipt['values'] != baseline['values'] or receipt['material_or_boundary_conditions_changed'] is not False):
        raise ValueError('central baseline values or boundary policy changed')
    for source in (path.parent/spec['source'], HERE.parent/spec['source']):
        if g8.sha256(source) != spec['source_sha']:
            raise ValueError('new executed CAD source changed')
    if (g8.sha256(HERE.parent/spec['probe']) != spec['probe_sha']
            or any(g8.sha256(HERE.parent/name) != sha for name,sha in helper_map.items())):
        raise ValueError('private helper or motivating diagnostic changed')
    variants = {}
    for row in receipt['variants']:
        interface = dict(id=row['id'], cad_accepted=row['cad_accepted'], step_sha256=row['step_sha256'],
            baseline_step_sha256=row['baseline_step_sha256'], journal_width_mm=row['journal_width_mm'],
            journal_diameter_mm=row['journal_diameter_mm'], first_1mm_difference_mm3=row['first_1mm_difference_mm3'],
            first_1mm_unchanged=g13.zero_difference(row['first_1mm_difference_mm3']))
        core.accepted(row,interface,step_hashes[row['id']])
        tools = row['existing_functional_tool_checks']
        names = {'central_mount_pilot_-1','central_mount_pilot_1'} if is_central else {
            'stud_nut_access_-1','stud_nut_access_1','mount_tool_access_-1','mount_tool_access_1'}
        if (set(tools) != names or not native.bounded(row['baseline_removed_volume_mm3'],1e-5)
                or any(set(t) != {'new_material_overlap_mm3','baseline_overlap_mm3','total_overlap_mm3'}
                    or not native.bounded(t['new_material_overlap_mm3'],1e-5)
                    or not native.bounded(t['baseline_overlap_mm3'],math.inf)
                    or not native.bounded(t['total_overlap_mm3'],math.inf)
                    or abs(t['total_overlap_mm3']-t['baseline_overlap_mm3'])>1e-5 for t in tools.values())):
            raise ValueError('functional tool audit or baseline preservation failed')
        step = g13.confined(path.parent,row['step'])
        if step.suffix != '.step' or g8.sha256(step) != row['step_sha256']:
            raise ValueError('new native STEP changed')
        variants[row['id']] = dict(row, step_path=step, cad_path=path, source_path=HERE.parent/spec['source'],
                                  probe_path=HERE.parent/spec['probe'])
    mirror = None
    if not is_central:
        if not g13.zero_difference(receipt['outer_independent_mirror_difference_mm3']):
            raise ValueError('independent negative outer mirror failed')
        mirror = dict(accepted=True, transformation_matrix=[[1,0,0],[0,-1,0],[0,0,1]],
            vector_cases={'+x':[1,0,0],'-z':[0,0,-1]}, prior=original['outer_mirror'],
            step_sha256={name:variants[name]['step_sha256'] for name in ids},
            negative_FE_executed=False, unchanged_foot_and_journal_masks=True)
    proof = dict(cad_receipt_sha256=spec['receipt'], cad_source_sha256=spec['source_sha'],
        field_probe_sha256=spec['probe_sha'], prior_cad=original, journal_width_mm=11. if is_central else 8.,
        outer_mirror=mirror, combined_geometry=combined_gate(),
        functional_tool_checks=variants[ident]['existing_functional_tool_checks'], mounting_and_maintenance_qualified=False)
    return baseline, variants[ident], proof


def trust(args):
    runtime = native.native_gate(args.reference)
    if g8.sha256(HERE/'outer_candidate.py') != OUTER_SHA or g8.sha256(HERE/'central_followup_candidate.py') != CENTRAL_SHA:
        raise ValueError('frozen upstream native entry changed')
    baseline, variant, cad = inputs(args.id)
    return baseline, variant, dict(runtime=runtime,cad=cad,recipe=RECIPE,CG_RHS_limit_seconds=900,
        worker_limit_seconds=3600,candidate_source_sha256=g8.sha256(Path(__file__)),
        reused_entries_sha256={'outer_candidate.py':OUTER_SHA,'central_followup_candidate.py':CENTRAL_SHA},
        numerical_sources_sha256=g11.source_hashes())


def audit(case, deadline):
    text = (case/'x.inp').read_text(); points,_,support = g9.deck(text)
    prefix = text.split('*STEP\n')[0]
    with (case/'matrix.inp').open('x') as stream:
        stream.write(prefix.replace('*SOLID SECTION','*DENSITY\n2.7e-9\n*SOLID SECTION')
            + '*BOUNDARY\nSUPPORT,1,3\n*STEP\n*FREQUENCY,SOLVER=MATRIXSTORAGE\n*END STEP\n')
    export_seconds = g9.ccx(case,'matrix')  # Existing 900s export, serial wrapper unchanged.
    g13.serial_log(case/'matrix.log')
    matrix,mapping = bench.read_matrix(case/'matrix.sti',case/'matrix.dof',points,support)
    rows = []
    for name in ('x','minus_z'):
        current = (case/(name+'.inp')).read_text()
        if current.split('*STEP\n')[0] != prefix:
            raise ValueError('load cases do not share stiffness geometry and material')
        _,loads,fixed = g9.deck(current)
        if fixed != support: raise ValueError('support differs between directions')
        seconds = min(900.,deadline-time.monotonic()-30.)
        if seconds<=0: raise TimeoutError('CG deadline reserve exhausted')
        rhs = g9.rhs_for(mapping,loads)
        u,timing = bench.solve(matrix,rhs,'cpu',max_seconds=seconds)
        residual = float(np.linalg.norm(matrix@u-rhs)/np.linalg.norm(rhs))
        solution = dict(u=u,passed=bool(timing['info']==0 and np.isfinite(u).all() and residual<=1e-8))
        compared = reference.compare(case,name,matrix,mapping,solution,rhs,points,support)
        row = dict(case=case.name,direction=name,numerical_crosscheck_passed=compared['passed'],
            solver=timing,relative_residual=residual,mechanics=compared['mechanics'],fresh_direct=compared['agreement'],
            export_seconds=export_seconds,free_dofs=len(mapping),matrix_nnz=matrix.nnz,
            comparison_method='unchanged g13_reference.compare; same FE discretization, not independent physics',
            hashes={n:g8.sha256(case/n) for n in (name+'.inp',name+'.dat','matrix.inp','matrix.sti','matrix.dof')})
        rows.append(row); g11.publish(case/(name+'-crosscheck.json'),row)
        print(json.dumps(dict(direction=name,passed=compared['passed'])),flush=True)
        if not compared['passed']: break
    return rows


def worker(args):
    deadline = time.monotonic()+args.timeout
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
    rows = audit(case,deadline)
    logs = {n:g13.serial_log(case/(n+'.log')) for n in ('x','minus_z','matrix')}
    if trust(args)[2] != proof:
        raise ValueError('native runtime or CAD changed during solve')
    result = dict(classification='native_arm64_macOS_CPU_G14_isolated_support_screen', id=args.id,
        component=variant['component'], mesh=mesh, backend='cpu', proof=proof, step_sha256=variant['step_sha256'],
        cad_receipt_sha256=proof['cad']['cad_receipt_sha256'], recipe=RECIPE,
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
    for source,name in ((Path(__file__),'next_candidates.py'),(HERE/'outer_candidate.py','outer_candidate.py'),
            (HERE/'central_followup_candidate.py','central_followup_candidate.py'),(native.WRAPPER,'ccx-wrapper'),
            (variant['cad_path'],'cad.json'),(variant['source_path'],variant['source_path'].name),
            (variant['probe_path'],'diagnostic.json'),(variant['step_path'],'candidate.step'),(COMBINED,'combined-clearance.json')):
        shutil.copyfile(source,provenance/name)
    identity = dict(id=args.id, mesh_mm=args.mesh, proof=proof, step_sha256=variant['step_sha256'],
        timeout_seconds=args.timeout, numerical_thread_environment=THREAD_ENV, CUDA_executed=False)
    g11.publish(args.output/'identity.json', identity)
    command = [sys.executable, str(Path(__file__).resolve()), '--worker', '--reference', str(args.reference.resolve()),
        '--id', args.id, '--mesh', str(args.mesh),
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
    parser.add_argument('--id', choices=IDS, required=True)
    parser.add_argument('--mesh', type=float, choices=(2.,), default=2.)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=3600)
    parser.add_argument('--check', action='store_true', help='Trust gates only; never mesh or solve')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 0 < args.timeout <= 3600 or not args.output.resolve().is_relative_to(HERE) or args.output.resolve() == HERE:
        parser.error('new private output below fea and timeout <=3600s required')
    if args.worker:
        worker(args)
    else:
        signal.signal(signal.SIGTERM, interrupted)
        raise SystemExit(run(args))
