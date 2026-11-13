"""Qualified full-calendar scientific loop with explicit public input bindings."""
from pathlib import Path
from types import SimpleNamespace
import argparse,hashlib,json,re,sys,time
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
import common
sha=common.sha
module=common.module

def json_bytes(value):return (json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
def dump(root,name,value):
 with (root/name).open('xb') as f:f.write(json_bytes(value))

def main(args):
 start=time.monotonic();contract_path=Path(args.output)/'contract.json';assert sha(contract_path)==args.contract_sha256;contract=json.loads(contract_path.read_text());PRIVATE=Path(contract['private_output_root']);runroot=Path(args.run_root)
 assert runroot.parent==Path(args.output)/'runs' and re.fullmatch(r'attempt-\d{3}',runroot.name) and runroot.is_dir() and not runroot.is_symlink()
 assert sys.version_info[:3]==(3,11,18) and sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode
 pins={Path(k):v for k,v in contract['source_sha256'].items()}
 for path,hsh in pins.items():assert sha(path)==hsh
 assert sha(__file__)==contract['driver_sha256']
 for row in contract['controls'].values():assert sha(row['path'])==row['sha256']
 indices=contract['indices'];heights=contract['heights_mm'];h=contract['layer_height_mm'];continuation=module('full_continuation',P/'continuation.py');assert continuation.validate_calendar(indices,heights,h)
 resume=args.resume_marker is not None;assert resume==all(x is not None for x in [args.resume_sha256,args.prior_terminal,args.prior_terminal_sha256])
 assert PRIVATE.is_dir() if resume else not PRIVATE.exists()
 state=common.load_current(args)
 import numpy as np
 import parallel_layers
 core,cache,audit=state['core'],state['cache'],state['audit'];pose,parameters,calendar=state['pose'],state['parameters'],state['admission']['calendar'];digest=state['digest'];mesh=state['mesh'];part=SimpleNamespace(geometry=mesh)
 source_record=contract['geometry_source_sha256'];assert parameters['layer_height_mm']==h and calendar['n_layers']==len(indices)
 oracle=state['oracle'];native_store=module('qualified_storage',P/'batch_storage.py');budget_module=module('qualified_budget',P/'budget_storage.py');outward=state['outward']
 geometry_preflight=state['full_expected']['geometry_preflight'];assert geometry_preflight['pose']==pose
 mesh_interval=outward.mesh_bounds(mesh.vertices,mesh.faces);assert mesh_interval['signed_volume_mm3'][0]>0 and mesh_interval==geometry_preflight['mesh_interval']
 mesh_record={'contract_sha256':args.contract_sha256,'source_sha256':source_record,'pose':pose,'bounds':mesh_interval};mesh_sha=hashlib.sha256(json_bytes(mesh_record)).hexdigest()
 context={'status':'fixed_current_full_calendar_context','contract_sha256':args.contract_sha256,'indices':indices,'heights_mm':heights,'pose':pose,'parameters':parameters,'calendar':calendar,'source_sha256':source_record,'mesh_bounds_sha256':mesh_sha}
 budget=budget_module.OutputBudget(PRIVATE,contract['scientific_output_cap_bytes'],indices);writer,store=budget_module.bind_storage(cache,native_store,budget)
 rows=continuation.restore_prefix(PRIVATE,context,indices,heights,Path(args.resume_marker),args.resume_sha256,Path(args.prior_terminal),args.prior_terminal_sha256,store,audit) if resume else []
 initial_prefix=len(rows);remaining=indices[initial_prefix:];remaining_heights=heights[initial_prefix:];golden=state['golden'];golden_path=state['paths']['golden_arrays'];golden_z=golden['layer']['z_mm']
 assert golden['status']=='one_current_float64_part_layer_native_slice_hatch_and_independent_audit_passed' and golden['layer']['layer']==517 and golden_z==heights[517]
 assert golden['pose']==pose and golden['calendar']==calendar and golden['parameters']==parameters and golden['admission_sha256']==sha(state['paths']['admission'])
 assert golden_path==Path(contract['golden_arrays_path']) and sha(golden_path)==contract['golden_arrays_sha256']==golden['raw_arrays_sha256']
 with parallel_layers.ParallelLayers(parameters,workers=1,heights=[golden_z,*remaining_heights]) as calculate:
  reference=calculate(part,golden_z);raw,contours,vectors,area=reference;rawpoints,rawoffsets=core.packed_paths(raw);contourpoints,contouroffsets=core.packed_paths(contours);actual={'z_mm':np.asarray(golden_z),'part_area_mm2':np.asarray(area),'part_boundary_points_mm':rawpoints,'part_boundary_offsets':rawoffsets,'part_scan_contour_points_mm':contourpoints,'part_scan_contour_offsets':contouroffsets,'part_hatch_segments_mm':np.asarray(vectors)}
  with np.load(golden_path,allow_pickle=False) as recorded:
   assert set(recorded.files)==set(actual)
   for key,value in actual.items():assert value.dtype==recorded[key].dtype and value.shape==recorded[key].shape and value.tobytes()==recorded[key].tobytes(),('Current one-worker golden parity failed',key)
  dump(runroot,'worker-parity.json',{'status':'current_517_matches_admitted_direct_layer_bitwise','reference_sha256':sha(golden_path),'all_arrays_bitwise_equal':True,'worker_calls':1});del reference,raw,contours,vectors,rawpoints,rawoffsets,contourpoints,contouroffsets,actual
  if not resume:
   store.create(PRIVATE,context);(PRIVATE/'bounds').mkdir();budget.write_json(PRIVATE/'mesh-bounds.json',mesh_record);marker,marker_sha=store.checkpoint(PRIVATE,context,indices,heights,rows)
  for index,z in zip(remaining,remaining_heights):
   native=calculate(part,z);independent=oracle.slice_rings(mesh.vertices,mesh.faces,z);interval=outward.section_area_bounds(mesh.vertices,independent['ring_source_edges'],z,independent['signed_area_mm2']);assert interval['area_mm2'][0]>=0
   row=store.publish(PRIVATE,context,index,z,native,independent['rings'],independent['signed_area_mm2'],writer,core,audit)
   keys=independent['ring_source_edges'];offsets=np.r_[0,np.cumsum([len(x) for x in keys])].astype('<i8');edges=np.concatenate(keys).astype('<i8') if keys else np.empty((0,2),dtype='<i8');edge_path=PRIVATE/'oracle'/('source-edges-%05d.npz'%index);budget.save_npz(edge_path,source_edges=edges,offsets=offsets);row['source_edge_cycles_sha256']=sha(edge_path)
   bounds_path=PRIVATE/'bounds'/('layer-%05d.json'%index);budget.write_json(bounds_path,{'layer':index,'z_mm':z,'native_area_mm2':float(native[3]),'reported_oracle_area_mm2':independent['signed_area_mm2'],'arithmetic':interval});row['arithmetic_bounds_sha256']=sha(bounds_path);rows.append(row);marker,marker_sha=store.checkpoint(PRIVATE,context,indices,heights,rows);storage=budget.verify()
   print(json.dumps({'stage':'full_calendar_layer_admitted','layer':index,'z_mm':z,'completed':len(rows),'declared':len(indices),'scientific_bytes':storage['scientific_bytes']}),flush=True)
  processes=list(calculate.pool._processes.values())
 closure=calculate.receipt();assert closure['completed_layers']==closure['declared_layers']==1+len(remaining) and closure['worker_group_closed'] and all(p.exitcode==0 and not p.is_alive() for p in processes)
 assert store.restore(PRIVATE,context,indices,heights,marker,marker_sha,audit)==rows
 bounds_rows=[]
 for row in rows:
  path=PRIVATE/'bounds'/('layer-%05d.json'%row['layer']);assert sha(path)==row['arithmetic_bounds_sha256'];bounds_rows.append(json.loads(path.read_text()))
 assessment=outward.calendar_bound(h,indices,heights,mesh_interval,[x['arithmetic']['area_mm2'] for x in bounds_rows],[x['native_area_mm2'] for x in bounds_rows],[x['reported_oracle_area_mm2'] for x in bounds_rows]);assert assessment['oracle_volume_bound_passed'] and assessment['native_volume_bound_passed'],'Full-calendar volume bound refused'
 assert digest(mesh.vertices)==pose['vertices_f64_sha256'] and digest(mesh.faces)==pose['faces_i64_sha256'] and common.verify_runtime(state,args)
 for path,hsh in pins.items():assert sha(path)==hsh
 for path,hsh in source_record.items():assert sha(path)==hsh
 assert budget.verify()['scientific_files']==len(continuation.prefix_paths(rows))
 manifest={str(path.relative_to(PRIVATE)):{'bytes':size,'sha256':sha(path)} for path,size in sorted(budget.files.items())};budget.write_json(PRIVATE/'scientific-manifest.json',{'scope':'all admitted scientific files before final manifest/result','files':manifest})
 report={'status':'all_1034_current_part_layers_and_outward_volume_bound_passed','contract_sha256':args.contract_sha256,'indices':indices,'layers_complete':len(rows),'initial_committed_prefix':initial_prefix,'indexed_layers_executed_this_attempt':len(remaining),'leading_517_control_calls_this_attempt':1,'worker_calls_this_attempt':len(remaining)+1,'worker_closure':closure,'all_numerical_workers_reaped':True,'final_checkpoint_sha256':marker_sha,'scientific_manifest_sha256':sha(PRIVATE/'scientific-manifest.json'),'full_calendar_volume':assessment,'source_runtime_and_pose_unchanged':True,'supports_generated':False,'machine_job_generated':False,'elapsed_seconds':time.monotonic()-start}
 budget.write_json(PRIVATE/'full-result.json',report);storage=budget.verify();dump(runroot,'result.json',{'status':report['status'],'full_result_sha256':sha(PRIVATE/'full-result.json'),'scientific_output':storage,'elapsed_seconds':report['elapsed_seconds']});print(json.dumps({'status':report['status'],'elapsed_seconds':report['elapsed_seconds']}),flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser()
 for name in ['repository-root','input-manifest','source-manifest-sha256','output','contract-sha256','run-root']:parser.add_argument('--'+name,required=True)
 for name in ['resume-marker','resume-sha256','prior-terminal','prior-terminal-sha256']:parser.add_argument('--'+name)
 args=parser.parse_args()
 try:main(args)
 except BaseException as exc:
  root=Path(args.run_root)
  if root.is_dir() and not (root/'refusal.json').exists():dump(root,'refusal.json',{'status':'full_calendar_not_admitted','error':repr(exc),'contract_sha256':args.contract_sha256})
  raise
