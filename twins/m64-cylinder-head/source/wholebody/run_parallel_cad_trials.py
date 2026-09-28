#!/usr/bin/env python3
"""Finite, process-isolated CAD/meshing matrix; no automatic master replacement.

Reuses the fixed-boundary builder, native import and all existing mesh gates.
Mesh recipes vary meshing parameters, not geometry. Sources and inputs stay hash-bound.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import itertools
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import mesh_native_ported_head as native

BODY_SHA = 'b2b48fe40edd1a20c8e6c0d20d77e6045931189f18330b441b09bcbf4618fc0a'
DIAGNOSTIC_SHA = '14e6d154a84c1170b11b72fb63e2b1c3454fe706455391c5cee8fc726b9a41cf'


def recipes():
    result = [dict(minimum=lo, maximum=hi, surface=surface, volume=volume, optimizer='netgen')
              for (lo, hi), surface, volume in itertools.product(((1., 6.), (.5, 3.)), (6, 1), (1, 10))]
    result.append(dict(minimum=1., maximum=6., surface=6, volume=1, optimizer='none'))
    return result


def mesh_accepted(report):
    required = {'positive_jacobians', 'native_CAD_model_unchanged_after_meshing',
        'positive_signed_tetra_volumes', 'one_connected_tetra_region', 'complete_tetra_boundary',
        'all_CAD_faces_meshed', 'minSICN_project_limit', 'reread_positive_jacobians',
        'reread_minSICN_project_limit', 'coarse_volume_error_limit', 'mesh_export_roundtrip'}
    algorithm = report.get('volume_algorithm')
    if type(algorithm) is not int or algorithm not in (1, 10):
        return False
    if algorithm == 10:
        required.add('surface_triangulations_unchanged_during_3D')
    gates = report.get('gates')
    return (report.get('status') == 'coarse_mesh_checks_passed_NOT_CAE_VALIDATED'
            and isinstance(gates, dict) and required <= gates.keys()
            and all(v is True for v in gates.values())
            and all(report.get(k) is True for k in ('native_input_unchanged', 'baseline_unchanged', 'source_unchanged')))


def execute(argv, log, seconds):
    start = time.monotonic()
    env = {**os.environ, 'OMP_NUM_THREADS':'2', 'OPENBLAS_NUM_THREADS':'1', 'MKL_NUM_THREADS':'1'}
    with log.open('x') as stream:
        process = subprocess.Popen(argv, stdout=stream, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, start_new_session=True, env=env)
        timeout = False
        try:
            code = process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            timeout, code = True, None
        finally:
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait(timeout=5)
    return dict(exit_code=code, timed_out=timeout, seconds=time.monotonic()-start)


def audit_volume(body, candidate, receipt, output):
    from audit_fixed_boundary_volume import rectangular_flux
    from trial_fixed_boundary_seam import read_native, indexed
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    if (receipt.get('status') != 'local_candidate_passed_pending_full_mesh_and_physics'
            or receipt.get('candidate_sha256') != native.sha256(candidate)
            or receipt.get('input_sha256') != BODY_SHA
            or any(receipt.get(k) is not True for k in ('inputs_unchanged', 'native_valid',
                'all_entity_tolerances_identical', 'protected_face_serializations_unchanged',
                'reference_in_memory_unchanged', 'readback_valid', 'readback_tolerances_identical'))
            or any(receipt.get(k) is not False for k in ('BOP_has_faulty', 'BOP_has_errors'))):
        raise ValueError('completed_guarded_native_candidate_required')
    shapes = [read_native(p) for p in (body, candidate)]
    faces = [TopoDS.Face_s(indexed(s, TopAbs_FACE)[1153]) for s in shapes]
    deltas = [rectangular_flux(faces[1], n)-rectangular_flux(faces[0], n) for n in (8, 16, 32)]
    volumes = []
    for shape in shapes:
        props = GProp_GProps()
        estimate = BRepGProp.VolumeProperties_s(shape, props, 1e-12, True, False)
        volumes.append(dict(volume=props.Mass(), returned_error_estimate=estimate))
    delta = volumes[1]['volume']-volumes[0]['volume']
    passed = (all(math.isfinite(v) and v < 0 for v in [*deltas, delta])
              and max(deltas)-min(deltas) < 1e-9 and abs(delta-deltas[-1]) < 1e-8)
    native.save(output, dict(passed=passed, candidate_sha256=native.sha256(candidate),
        Gauss_deltas=deltas, adaptive_whole_volumes=volumes, adaptive_delta=delta,
        rigorous_interval_bound=False, manufacturing_authorized=False))
    if not passed: raise ValueError('independent_volume_crosscheck_failed')


def worker(args):
    import OCP
    import gmsh
    import resource
    if OCP.__version__ != '7.9.3.1' or gmsh.__version__ != '4.15.2':
        raise ValueError('qualified_native_versions_required')
    if sys.platform == 'linux':
        resource.setrlimit(resource.RLIMIT_AS, (16*1024**3, 16*1024**3))
    signal.alarm(600)
    if native.sha256(args.body) != BODY_SHA or native.sha256(args.diagnostic) != DIAGNOSTIC_SHA:
        raise ValueError('input_binding_failed')
    if args.mode == 'candidate':
        from trial_fixed_boundary_seam import run
        ns = argparse.Namespace(body=args.body, diagnostic=args.diagnostic, output=args.output, amplitude=args.amplitude)
        code = run(ns)
        if code: return code
        receipt = json.loads((args.output/'report.json').read_text())
        audit_volume(args.body, args.output/'diagnostic-candidate.brep', receipt, args.output/'volume-audit.json')
        return 0
    args.output.mkdir(mode=0o700)
    recipe = recipes()[args.recipe]
    sha = native.sha256(args.shape)
    baseline = json.loads(args.baseline.read_text())
    if baseline['native_BRep_sha256'] != sha: raise ValueError('shape_baseline_mismatch')
    receipt = dict(schema='m64-parallel-mesh-recipe/v1', recipe=recipe,
        shape_sha256=sha, source_sha256=native.sha256(__file__), helper_sha256=native.sha256(native.__file__),
        geometry_modified=False, previous_quality_gates_unchanged=True, calls=[])
    target = args.output/'recipe.json'
    native.save(target, receipt)
    generate = gmsh.model.mesh.generate
    def selected_generate(dimension=3):
        receipt['calls'].append(dimension)
        if dimension == 1: gmsh.option.setNumber('Mesh.Algorithm', recipe['surface'])
        native.save(target, receipt)
        return generate(dimension)
    gmsh.model.mesh.generate = selected_generate
    mesh_dir = args.output/'mesh'
    mesh_dir.mkdir(mode=0o700)
    ns = argparse.Namespace(input=args.shape, sha256=sha, baseline=args.baseline, output=mesh_dir,
        minimum=recipe['minimum'], maximum=recipe['maximum'], volume_algorithm=recipe['volume'],
        optimizer=recipe['optimizer'], maximum_tetrahedra=1500000, preserved_skin_meshadapt_evidence=None)
    try:
        return native.mesh(ns)
    finally:
        gmsh.model.mesh.generate = generate
        receipt.update(input_unchanged=native.sha256(args.shape)==sha, hook_completed=receipt['calls']==[1,2,3])
        native.save(target, receipt)


def run(args):
    if args.output.exists() or args.workers not in range(1, 9): raise ValueError('fresh_output_and_at_most_eight_workers')
    if any(p.is_symlink() for p in (args.body, args.diagnostic, args.pins)): raise ValueError('symlinks_rejected')
    pins = json.loads(args.pins.read_text())
    def unchanged():
        return all(not (HERE.parent/name).is_symlink() and native.sha256(HERE.parent/name)==sha for name, sha in pins.items())
    if not pins or any(Path(n).is_absolute() or '..' in Path(n).parts for n in pins) or not unchanged():
        raise ValueError('source_manifest_required')
    if native.sha256(args.body) != BODY_SHA or native.sha256(args.diagnostic) != DIAGNOSTIC_SHA:
        raise ValueError('private_inputs_mismatch')
    args.output.mkdir(mode=0o700)
    start = time.monotonic()
    summary = dict(schema='m64-parallel-cad-matrix/v1', source_pins=pins, body_sha256=BODY_SHA,
        diagnostic_sha256=DIAGNOSTIC_SHA, concurrent_workers=args.workers, candidate_runs=[], mesh_runs=[],
        status='incomplete', master_replaced=False, manufacturing_authorized=False, CAD_complete=False)
    def save(): native.save(args.output/'campaign.json', summary)
    save()
    prefix = [sys.executable, str(Path(__file__).resolve()), '--body', str(args.body), '--diagnostic', str(args.diagnostic)]
    def make_candidate(amplitude):
        out = args.output/('candidate-'+str(amplitude))
        row = execute(prefix+['--mode','candidate','--amplitude',str(amplitude),'--output',str(out)],
                      args.output/(out.name+'.log'), 610)
        row.update(name=out.name, amplitude=amplitude)
        return row
    with ThreadPoolExecutor(max_workers=min(2, args.workers)) as pool:
        summary['candidate_runs'] = list(pool.map(make_candidate, (.02, .035)))
    save()
    shapes = [('original', args.body)]
    for row in summary['candidate_runs']:
        if row['exit_code']==0 and not row['timed_out']:
            shapes.append((row['name'], args.output/row['name']/'diagnostic-candidate.brep'))
    ready = []
    for name, shape in shapes:
        out = args.output/(name+'-baseline')
        result = execute([sys.executable, str(HERE.parent/'mesh_native_ported_head.py'), '--mode','baseline',
            '--input',str(shape),'--sha256',native.sha256(shape),'--output',str(out)], args.output/(name+'-baseline.log'), 300)
        if result['exit_code']==0 and not result['timed_out']: ready.append((name, shape, out/'native-baseline.json'))
    def mesh_trial(job):
        (name, shape, baseline), index = job
        out = args.output/(name+'-mesh-'+str(index))
        row = execute(prefix+['--mode','mesh','--shape',str(shape),'--baseline',str(baseline),
            '--recipe',str(index),'--output',str(out)], args.output/(out.name+'.log'), 610)
        row.update(name=out.name, recipe=recipes()[index], coarse_mesh_passed=False)
        report = out/'mesh/mesh-report.json'
        if report.exists():
            data = json.loads(report.read_text())
            row.update(report_sha256=native.sha256(report), status=data.get('status'),
                coarse_mesh_passed=mesh_accepted(data) and row['exit_code']==0,
                quality={k:data.get('mesh',{}).get(k) for k in ('tetrahedra','minimum_minSICN','minSICN_below_0p1','nonpositive_Jacobians')})
        return row
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(mesh_trial, itertools.product(ready, range(len(recipes())))):
            summary['mesh_runs'].append(row)
            save()
            print(json.dumps({k:row[k] for k in ('name','exit_code','coarse_mesh_passed')}), flush=True)
    summary.update(status='completed_matrix_not_CAD_release', seconds=time.monotonic()-start,
        source_unchanged=unchanged(), input_unchanged=native.sha256(args.body)==BODY_SHA and native.sha256(args.diagnostic)==DIAGNOSTIC_SHA)
    if not summary['source_unchanged'] or not summary['input_unchanged']: summary['status']='rejected_input_changed'
    save()
    return 0 if summary['status']=='completed_matrix_not_CAD_release' else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('batch','candidate','mesh'), default='batch')
    for key in ('body','diagnostic','output'): parser.add_argument('--'+key, type=Path, required=True)
    for key in ('shape','baseline','pins'): parser.add_argument('--'+key, type=Path)
    parser.add_argument('--amplitude', type=float, choices=(.02,.035))
    parser.add_argument('--recipe', type=int, choices=range(9))
    parser.add_argument('--workers', type=int, default=8)
    os.umask(0o077)
    args = parser.parse_args()
    raise SystemExit(run(args) if args.mode=='batch' else worker(args))
