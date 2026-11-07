"""Bounded storage, arithmetic, interruption and actual current-source preparation."""
import argparse
import json
from pathlib import Path
import sys
import time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import common


def current_source(args, output):
    state=common.load_current(args)
    import numpy as np
    import parallel_layers
    mesh,pose,parameters=state['mesh'],state['pose'],state['parameters']
    expected=state['full_expected']
    interval=state['outward'].mesh_bounds(mesh.vertices,mesh.faces)
    if interval!=expected['geometry_preflight']['mesh_interval'] or pose!=expected['geometry_preflight']['pose']:
        raise ValueError('Current full-source outward geometry preflight differs')
    continuation=common.module('qualified_full_continuation',HERE/'continuation.py')
    indices=list(range(1034));heights=[(i+.5)*.06 for i in indices]
    continuation.validate_calendar(indices,heights,parameters['layer_height_mm'])
    if state['admission']['calendar']['n_layers']!=1034:
        raise ValueError('Current full calendar source binding differs')
    z=heights[517]
    from types import SimpleNamespace
    with parallel_layers.ParallelLayers(parameters,workers=1,heights=[z])as calculate:
        native=calculate(SimpleNamespace(geometry=mesh),z)
        processes=list(calculate.pool._processes.values())
    closure=calculate.receipt()
    if not(closure['completed_layers']==closure['declared_layers']==1 and closure['worker_group_closed'] and all(p.exitcode==0 and not p.is_alive()for p in processes)):
        raise ValueError('Current one-worker closure failed')
    oracle=state['oracle'].slice_rings(mesh.vertices,mesh.faces,z)
    bounds=state['outward'].section_area_bounds(mesh.vertices,oracle['ring_source_edges'],z,oracle['signed_area_mm2'])
    storage=common.module('qualified_control_storage',HERE/'batch_storage.py')
    budget_module=common.module('qualified_control_budget',HERE/'budget_storage.py')
    root=Path(output)/'current-golden';budget=budget_module.OutputBudget(root,256*1024**2,[517])
    writer,store=budget_module.bind_storage(state['cache'],storage,budget)
    context=dict(scope='actual current source and one golden worker control only',source_manifest_sha256=args.source_manifest_sha256,
                 source_sha256=common.sha(state['paths']['mesh']),pose=pose,parameters=parameters)
    store.create(root,context)
    row=store.publish(root,context,517,z,native,oracle['rings'],oracle['signed_area_mm2'],writer,state['core'],state['audit'])
    raw=root/'layers/layer-00517.npz';reference=state['paths']['golden_arrays']
    with np.load(raw,allow_pickle=False)as actual,np.load(reference,allow_pickle=False)as golden:
        if set(actual.files)!=set(golden.files):raise ValueError('Current reference array roster differs')
        for name in actual.files:
            if actual[name].dtype!=golden[name].dtype or actual[name].shape!=golden[name].shape or actual[name].tobytes()!=golden[name].tobytes():
                raise ValueError('Current reference array bytes differ: '+name)
    if common.sha(raw)!=common.sha(reference):raise ValueError('Current complete native NPZ differs')
    common.verify_runtime(state,args)
    result=dict(status='current_full_calendar_source_and_worker_controls_passed',source_manifest_sha256=args.source_manifest_sha256,
                geometry_preflight=interval,pose=pose,complete_indices=1034,current_layer_calls=1,
                golden_array_and_npz_byte_parity=True,raw_sha256=common.sha(raw),worker_closure=closure,
                original_and_independent_domain_audits_passed=True,independent_section_bounds=bounds,
                scientific_output=budget.verify(),full_calendar_executed=False)
    common.write(Path(output)/'current-controls.json',result)
    return result


def worker(args):
    start=time.monotonic();output=Path(args.output)
    common.bindings(args)
    lifecycle=common.module('full_lifecycle_controls',HERE/'lifecycle_controls.py').run(args,output)
    storage=common.module('full_storage_controls',HERE/'storage_controls.py').run(args,output)
    arithmetic=common.module('full_math_controls',HERE/'math_controls.py').run(args,output)
    current=current_source(args,output)
    common.bindings(args)
    report=dict(status='public_full_calendar_bounded_controls_passed',source_manifest_sha256=args.source_manifest_sha256,
                storage_refusals=len(storage['refusals']),arithmetic_refusals=len(arithmetic['negative_controls']),
                interrupted_stage_cleanup_passed=lifecycle['exact_owned_group_absent'],
                current_source_worker_control_passed=current['golden_array_and_npz_byte_parity'],
                full_calendar_executed=False,elapsed_seconds=time.monotonic()-start)
    common.write(output/'result.json',report)
    print(json.dumps(report),flush=True)


def main(args):
    if args.worker:
        worker(args);return
    common.bindings(args)
    output=Path(args.output).resolve();args.output=str(output);output.mkdir(mode=0o700,exist_ok=False)
    runroot=output/'supervision';runroot.mkdir()
    guard=common.module('bounded_full_preparation_guard',HERE/'guard.py');guard.WALL_SECONDS=300
    command=[sys.executable,'-I','-B','-S',str(Path(__file__).resolve()),'--worker']
    for name in ['repository_root','input_manifest','source_manifest_sha256','output']:
        command+=['--'+name.replace('_','-'),str(getattr(args,name))]
    report=guard.supervise(command,runroot,lambda:common.bindings(args),output.parent,args.source_manifest_sha256)
    if report['reason']!='complete' or report['actual_returncode']!=0:
        raise RuntimeError('Bounded full-calendar controls failed; retained output is not admitted')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['repository-root','input-manifest','source-manifest-sha256','output']:parser.add_argument('--'+name,required=True)
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    main(parser.parse_args())
