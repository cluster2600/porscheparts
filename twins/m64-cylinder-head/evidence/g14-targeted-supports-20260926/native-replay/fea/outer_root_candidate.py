#!/usr/bin/env python3
"""Private G14 outer-root coarse CPU screen; no refinement or new solver."""
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
PRIOR = HERE/'next_candidates.py'
PRIOR_SHA = '2feb0779cbec984f75d50418d535a2e067792fe0261d3c18254f5d11a01d93bb'
if hashlib.sha256(PRIOR.read_bytes()).hexdigest() != PRIOR_SHA:
    raise ValueError('approved previous CPU recipe changed')
spec = importlib.util.spec_from_file_location('g14_next_candidates', PRIOR)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
native, g13, g11, g8, g9 = prior.native, prior.g13, prior.g11, prior.g8, prior.g9
core, np, audit = prior.core, prior.np, prior.audit
THREAD_ENV, RECIPE = prior.THREAD_ENV, prior.RECIPE
CAPS_SHA = 'ef77599f3347d581fae179ff0d7563082fd5decf0f078e2b4a5be1973b92d623'
caps = prior.load_entry('caps_candidate.py',CAPS_SHA)
IDENT = 'outer_high_cheeks_extended_root2_p'
IDS = (IDENT,)
ALL_IDS = (IDENT,IDENT[:-1]+'m')
CAD = HERE.parent/'cad-outer-root-v1/receipt.json'
CAD_SHA = '81048f826f7d98621d4395f64483afc32c0d18ae042947333e60216f01389da2'
SOURCE_NAME = 'g14_outer_root_private.py'
SOURCE_SHA = '0f8821f7e3b25506d39caa01d9ba977abed439d1512505ba9d8abaaaccd5f4a9'
PROBE = HERE.parent/'outer-root-fields.json'
PROBE_SHA = 'b8975869616beff230730efc19ddf4e69f2313bbb9e9a3e4ba0118b36ca14c00'
COMBINED = HERE.parent/'combined-caps-outer-root-clearance-v1.json'
COMBINED_SHA = 'b18bac78d510a6f99118381de1e0b872220879d0b251f582c01261876ff105f2'
COMBINED_SOURCE = HERE.parent/'check_caps_outer_root_candidates.py'
COMBINED_SOURCE_SHA = '2fd7cadfed7f354f7be0f72cdb013f7fa4183307f87c1b189beaae306a06f5c2'


def combined_gate(receipt, path=COMBINED):
    if g8.sha256(path) != COMBINED_SHA or g8.sha256(COMBINED_SOURCE) != COMBINED_SOURCE_SHA:
        raise ValueError('approved caps/outer-root coexistence proof changed')
    proof = json.loads(path.read_text())
    names = (caps.IDENT,*ALL_IDS)
    pairs = {(names[0],names[1]),(names[0],names[2]),(names[1],names[2])}
    if (proof['source_sha256'] != COMBINED_SOURCE_SHA or proof['pairwise_no_intersection'] is not True
            or proof['all_fingerprints_unchanged'] is not True or proof['hashes_before'] != proof['hashes_after']
            or tuple(r['id'] for r in proof['components']) != names
            or {(r['first'],r['second']) for r in proof['pairs']} != pairs or len(proof['pairs']) != 3
            or any(not native.bounded(r['intersection_volume_mm3'],1e-5) for r in proof['pairs'])
            or proof['G7_receipt_sha256'] != g8.sha256(g8.BASELINE)
            or any(g8.sha256(g13.confined(REPO,n)) != sha for n,sha in proof['hashes_before'].items())
            or any(proof['hashes_before'].get(n) != sha for n,sha in receipt['frozen_sources_sha256'].items())):
        raise ValueError('caps/outer-root coexistence identities or intersections failed')
    caps.inputs(caps.IDENT)  # Actual accepted central chain, not only the sidecar.
    central_cad = json.loads(caps.CAD.read_text())
    for row in proof['components']:
        central = row['id']==caps.IDENT
        expected = next(v for v in (central_cad if central else receipt)['variants'] if v['id']==row['id'])
        if (row['CAD_receipt_sha256'] != (caps.CAD_SHA if central else CAD_SHA)
                or row['source_sha256'] != (caps.SOURCE_SHA if central else SOURCE_SHA)
                or row['individual_sampled_poses'] != 144 or row['step_sha256'] != expected['step_sha256']
                or g8.sha256(g13.confined(REPO,row['step'])) != row['step_sha256']):
            raise ValueError('caps/outer-root coexistence STEP or CAD binding failed')
    return dict(receipt_sha256=COMBINED_SHA,pairwise_no_intersection=True,
                continuous_or_deformed_clearance_qualified=False,assembled_stiffness_qualified=False)


def inputs(ident, path=CAD):
    if ident != IDENT or g8.sha256(path) != CAD_SHA:
        raise ValueError('only the approved positive outer-root CAD may be solved')
    baseline, previous, original = prior.inputs(prior.EXTERIOR)
    root_spec = prior.SPECS[prior.EXTERIOR]
    old = json.loads((HERE.parent/root_spec['folder']/'receipt.json').read_text())
    helpers = dict(old['private_helper_sha256'], **{root_spec['source']:root_spec['source_sha']})
    receipt = json.loads(path.read_text())
    if (receipt['complete'] is not True or receipt['error'] is not None
            or receipt['FEA_executed'] is not False or receipt['manufacturing_authorized'] is not False
            or receipt['engine_start_authorized'] is not False
            or receipt['material_or_boundary_conditions_changed'] is not False
            or receipt['prior_CAD_receipt_sha256'] != root_spec['receipt']
            or receipt['source_sha256'] != SOURCE_SHA or receipt['field_probe_sha256'] != PROBE_SHA
            or receipt['private_helper_sha256'] != helpers
            or receipt['G7_receipt_sha256'] != g8.sha256(g8.BASELINE)
            or receipt['frozen_sources_sha256'] != old['frozen_sources_sha256']
            or receipt['values'] != baseline['values']
            or tuple(v['id'] for v in receipt['variants']) != ALL_IDS
            or receipt['crank_samples_deg'] != list(range(0,720,5))):
        raise ValueError('complete outer-root CAD and unchanged baseline chain required')
    for file,sha in [(path.parent/SOURCE_NAME,SOURCE_SHA),(HERE.parent/SOURCE_NAME,SOURCE_SHA),(PROBE,PROBE_SHA),
                     *((HERE.parent/n,s) for n,s in helpers.items())]:
        if g8.sha256(file) != sha:
            raise ValueError('executed outer-root source, diagnostic or helper changed')
    variants = {}
    for row in receipt['variants']:
        oldrow = next(v for v in old['variants'] if v['id'][-1]==row['id'][-1])
        interface = {k:row[k] for k in ('id','cad_accepted','step_sha256','baseline_step_sha256',
                                      'journal_width_mm','journal_diameter_mm','first_1mm_difference_mm3')}
        interface['first_1mm_unchanged'] = g13.zero_difference(row['first_1mm_difference_mm3'])
        core.accepted(row,interface,oldrow['step_sha256'])
        tools = row['existing_functional_tool_checks']
        if (not native.bounded(row['baseline_removed_volume_mm3'],1e-5)
                or set(tools) != {'stud_nut_access_-1','stud_nut_access_1','mount_tool_access_-1','mount_tool_access_1'}
                or any(set(t) != {'new_material_overlap_mm3','baseline_overlap_mm3','total_overlap_mm3'}
                    or not native.bounded(t['new_material_overlap_mm3'],1e-5)
                    or not native.bounded(t['baseline_overlap_mm3'],math.inf)
                    or not native.bounded(t['total_overlap_mm3'],math.inf)
                    or abs(t['total_overlap_mm3']-t['baseline_overlap_mm3'])>1e-5
                    or abs(t['baseline_overlap_mm3']-oldrow['existing_functional_tool_checks'][n]['total_overlap_mm3'])>1e-5
                    for n,t in tools.items())):
            raise ValueError('outer-root baseline preservation or inherited tool audit failed')
        step = g13.confined(path.parent,row['step'])
        if step.suffix != '.step' or g8.sha256(step) != row['step_sha256']:
            raise ValueError('outer-root STEP changed')
        variants[row['id']] = dict(row,step_path=step,cad_path=path,source_path=HERE.parent/SOURCE_NAME,probe_path=PROBE)
    if not g13.zero_difference(receipt['outer_independent_mirror_difference_mm3']):
        raise ValueError('independent outer-root mirror differs')
    mirror = dict(accepted=True,transformation_matrix=[[1,0,0],[0,-1,0],[0,0,1]],
        vector_cases={'+x':[1,0,0],'-z':[0,0,-1]},prior=original['outer_mirror'],
        step_sha256={name:variants[name]['step_sha256'] for name in ALL_IDS},
        negative_FE_executed=False,unchanged_foot_and_journal_masks=True)
    proof = dict(cad_receipt_sha256=CAD_SHA,cad_source_sha256=SOURCE_SHA,field_probe_sha256=PROBE_SHA,
                 prior_cad=original,journal_width_mm=8,combined_geometry=combined_gate(receipt),
                 outer_mirror=mirror,functional_tool_checks=variants[IDENT]['existing_functional_tool_checks'],
                 mounting_and_maintenance_qualified=False)
    return baseline,variants[IDENT],proof


def trust(args):
    runtime = native.native_gate(args.reference)
    if g8.sha256(PRIOR) != PRIOR_SHA or g8.sha256(HERE/'caps_candidate.py') != CAPS_SHA:
        raise ValueError('frozen reused CPU recipe changed')
    baseline,variant,cad = inputs(args.id)
    return baseline,variant,dict(runtime=runtime,cad=cad,recipe=RECIPE,CG_RHS_limit_seconds=900,
        worker_limit_seconds=3600,candidate_source_sha256=g8.sha256(Path(__file__)),
        reused_entry_sha256=PRIOR_SHA,caps_entry_sha256=CAPS_SHA,numerical_sources_sha256=g11.source_hashes())


# Worker and bounded process-group controller retained from next_candidates.py.
# Only the private input/provenance mapping changes; audit is the pinned function above.
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
    for source,name in ((Path(__file__),'outer_root_candidate.py'),(PRIOR,'next_candidates.py'),
            (HERE/'caps_candidate.py','caps_candidate.py'),
            (HERE/'outer_candidate.py','outer_candidate.py'),
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
