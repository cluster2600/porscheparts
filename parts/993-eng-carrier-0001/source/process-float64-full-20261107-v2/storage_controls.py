"""Rebound qualified storage/cap/continuation controls; original numerical bodies retained."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,io,json,shutil,sys,time
import common
P=Path(__file__).resolve().parent
R=common.LAYER
sha=common.sha
module=common.module
save=common.write
def run(args, output):
 global np, trimesh, layers
 _, replay, _, _, paths, profile, repo = common.bindings(args)
 sys.path.insert(0,str(paths['site_packages']));slicing=repo/'parts/993-eng-carrier-0001/source/process-slicing-20261016';sys.path.insert(0,str(slicing))
 import numpy as np
 import trimesh,layers
 replay.verify_profile(profile)
 start=time.monotonic();assert sys.flags.isolated and sys.flags.dont_write_bytecode and sys.flags.no_site
 assert sha(sys.executable)=='6c3cb7fae319bee761aeba0ebb1eeae07b4a4c28fa5b74e73f02b6a7e1ff10d8'
 budget_module=module('full_budget',P/'budget_storage.py');continuation=module('full_continuation',P/'continuation.py');store=module('qualified_storage',P/'batch_storage.py');oracle=module('qualified_oracle',R/'strict_plane_oracle.py');cache=module('native_cache',repo/'parts/993-eng-carrier-0001/source/process-cache-20261016/part_cache.py');core=module('native_core',repo/'parts/993-eng-carrier-0001/source/process-coverage-20261016/build_pyslm.py');audit=module('native_audit',slicing/'audit_scanpaths.py')
 pins={str(p):sha(p) for p in [Path(__file__),P/'budget_storage.py',P/'continuation.py',P/'batch_storage.py',R/'strict_plane_oracle.py',Path(cache.__file__),Path(core.__file__),Path(audit.__file__),Path(layers.__file__)]}
 base=Path(output)/'control-data';base.mkdir(exist_ok=False);indices=list(range(1034));heights=[(i+.5)*.06 for i in indices];assert continuation.validate_calendar(indices,heights,.06)
 root=base/'accepted';root.mkdir();budget=budget_module.OutputBudget(root,4*1024**3,indices);root.rmdir();writer,bound_store=budget_module.bind_storage(cache,store,budget)
 assert writer.write_layer.__code__ is cache.write_layer.__code__
 for name in ['create','publish','checkpoint','restore']:assert getattr(bound_store,name).__code__ is getattr(store,name).__code__
 geometry={'contract_sha256':hashlib.sha256(b'synthetic-fixture-only').hexdigest(),'scope':'synthetic storage fixture only, not a geometry arithmetic qualification'}
 geometry_bytes=(json.dumps(geometry,indent=2,allow_nan=False)+'\n').encode();context={'contract_sha256':geometry['contract_sha256'],'mesh_bounds_sha256':hashlib.sha256(geometry_bytes).hexdigest(),'scope':'synthetic full-index binding and bounded IO control','indices':indices,'heights':heights,'source':'ten millimetre synthetic cube'}
 bound_store.create(root,context);(root/'bounds').mkdir();budget.write_json(root/'mesh-bounds.json',geometry);rows=[];marker,marker_sha=bound_store.checkpoint(root,context,indices,heights,rows)
 mesh=trimesh.creation.box(extents=[10.,10.,10.]);part=SimpleNamespace(geometry=mesh);z_bounds=layers.face_z_bounds(mesh);parity=[]
 for i in [0,1]:
  native=layers.layer_geometry(part,heights[i],core.PARAMETERS,z_bounds);cut=oracle.slice_rings(mesh.vertices,mesh.faces,heights[i]);baseline=base/('baseline-%d'%i);(baseline/'layers').mkdir(parents=True);row=cache.write_layer(baseline,i,heights[i],native)
  item=bound_store.publish(root,context,i,heights[i],native,cut['rings'],cut['signed_area_mm2'],writer,core,audit)
  raw=root/'layers'/('layer-%05d.npz'%i);assert raw.read_bytes()==(baseline/'layers'/raw.name).read_bytes();assert json.loads((root/('layer-%05d.receipt.json'%i)).read_text())['row']==row
  edges=cut['ring_source_edges'];offsets=np.r_[0,np.cumsum([len(x) for x in edges])].astype('<i8');points=np.concatenate(edges).astype('<i8')
  ep=root/'oracle'/('source-edges-%05d.npz'%i);budget.save_npz(ep,source_edges=points,offsets=offsets);item['source_edge_cycles_sha256']=sha(ep)
  bp=root/'bounds'/('layer-%05d.json'%i);budget.write_json(bp,{'scope':'synthetic storage binding only','area_interval_mm2':[100.,100.]});item['arithmetic_bounds_sha256']=sha(bp);rows.append(item);marker,marker_sha=bound_store.checkpoint(root,context,indices,heights,rows);parity.append({'layer':i,'npz_bytes_identical':True,'numerical_row_identical':True})
 terminal=base/'prior-terminal.json';terminal_data={'contract_sha256':context['contract_sha256'],'prepared_sources_unchanged':True,'child_reaped':True,'owned_group_cleanup':{'group_absent':True,'only_exact_owned_group_signaled':True},'reason':'finite_resource_or_observer_guard','scope':'synthetic receipt fixture, not an actual scientific process'};save(terminal,terminal_data)
 restored=continuation.restore_prefix(root,context,indices,heights,marker,marker_sha,terminal,sha(terminal),bound_store,audit);assert restored==rows;budget.verify()
 resumed_budget=budget_module.OutputBudget(root,4*1024**3,indices);assert resumed_budget.used==budget.used and resumed_budget.verify()==budget.verify()
 budget=resumed_budget;writer,bound_store=budget_module.bind_storage(cache,store,budget)
 for i in [2]:
  native=layers.layer_geometry(part,heights[i],core.PARAMETERS,z_bounds);cut=oracle.slice_rings(mesh.vertices,mesh.faces,heights[i]);baseline=base/('baseline-%d'%i);(baseline/'layers').mkdir(parents=True);row=cache.write_layer(baseline,i,heights[i],native)
  item=bound_store.publish(root,context,i,heights[i],native,cut['rings'],cut['signed_area_mm2'],writer,core,audit)
  raw=root/'layers'/('layer-%05d.npz'%i);assert raw.read_bytes()==(baseline/'layers'/raw.name).read_bytes();assert json.loads((root/('layer-%05d.receipt.json'%i)).read_text())['row']==row
  edges=cut['ring_source_edges'];offsets=np.r_[0,np.cumsum([len(x) for x in edges])].astype('<i8');points=np.concatenate(edges).astype('<i8')
  ep=root/'oracle'/('source-edges-%05d.npz'%i);budget.save_npz(ep,source_edges=points,offsets=offsets);item['source_edge_cycles_sha256']=sha(ep)
  bp=root/'bounds'/('layer-%05d.json'%i);budget.write_json(bp,{'scope':'synthetic storage binding only','area_interval_mm2':[100.,100.]});item['arithmetic_bounds_sha256']=sha(bp);rows.append(item);marker,marker_sha=bound_store.checkpoint(root,context,indices,heights,rows);parity.append({'layer':i,'npz_bytes_identical':True,'numerical_row_identical':True})
 assert continuation.restore_prefix(root,context,indices,heights,marker,marker_sha,terminal,sha(terminal),bound_store,audit)==rows

 failures=[]
 def refuse(name,call):
  try:call()
  except (ValueError,AssertionError,FileNotFoundError) as exc:
   if name=='layer_outside_domain':assert str(exc)=='Layer outside declared domain'
   if name=='unaccounted_partial':assert str(exc)=='Unaccounted partial or missing scientific outputs refuse continuation'
   if name=='duplicate_output':assert str(exc)=='Existing scientific output must not be overwritten'
   if name in ['exact_npz_cap_before_publication','exact_json_cap_before_publication']:assert str(exc)=='Scientific output cap would be exceeded'
   failures.append({'name':name,'refused':True,'error':type(exc).__name__,'message':str(exc)})
  else:raise AssertionError('Invalid control admitted: '+name)
 refuse('missing_index',lambda:continuation.validate_calendar(indices[:-1],heights[:-1],.06));refuse('duplicate_index',lambda:continuation.validate_calendar([0,*indices[:-1]],heights,.06));refuse('changed_plane',lambda:continuation.validate_calendar(indices,[heights[0]+1e-6,*heights[1:]],.06));refuse('changed_layer_height',lambda:continuation.validate_calendar(indices,heights,.061))
 refuse('wrong_prior_terminal_hash',lambda:continuation.restore_prefix(root,context,indices,heights,marker,marker_sha,terminal,'0'*64,bound_store,audit));refuse('foreign_source_contract',lambda:continuation.restore_prefix(root,{**context,'contract_sha256':'0'*64},indices,heights,marker,marker_sha,terminal,sha(terminal),bound_store,audit))
 bad_terminal=base/'unreaped-terminal.json';save(bad_terminal,{**terminal_data,'child_reaped':False});refuse('unreaped_prior_process',lambda:continuation.restore_prefix(root,context,indices,heights,marker,marker_sha,bad_terminal,sha(bad_terminal),bound_store,audit))
 for label in ['changed_bound','missing_edge','unaccounted_partial','wrong_mesh_bound']:
  trial=base/label;shutil.copytree(root,trial)
  for old in sorted(trial.glob('checkpoint-*.json')):
   value=json.loads(old.read_text())
   for item in value['rows']:item['receipt_path']=str(trial/Path(item['receipt_path']).name)
   old.write_text(json.dumps(value,indent=2)+'\n')
  copied=trial/marker.name;pinned=sha(copied)
  if label=='changed_bound':(trial/'bounds/layer-00000.json').write_text('{}\n')
  elif label=='missing_edge':(trial/'oracle/source-edges-00000.npz').unlink()
  elif label=='unaccounted_partial':(trial/'layers/layer-00003.npz').write_bytes(b'partial fixture')
  else:(trial/'mesh-bounds.json').write_text('{}\n')
  refuse(label,lambda:continuation.restore_prefix(trial,context,indices,heights,copied,pinned,terminal,sha(terminal),bound_store,audit))
 caproot=base/'cap';(caproot/'layers').mkdir(parents=True);payload=np.arange(256,dtype=np.float64);buffer=io.BytesIO();np.savez_compressed(buffer,array=payload);exact=len(buffer.getvalue());cap=budget_module.OutputBudget(caproot,2*exact-1,indices);cap.save_npz(caproot/'layers/layer-00000.npz',array=payload);refuse('exact_npz_cap_before_publication',lambda:cap.save_npz(caproot/'layers/layer-00001.npz',array=payload));assert not (caproot/'layers/layer-00001.npz').exists();assert cap.verify()['scientific_bytes']==exact
 refuse('duplicate_output',lambda:budget.write_json(root/'context.json',{}));refuse('foreign_output_path',lambda:cap.write_json(base/'escaped.json',{}));refuse('unlisted_output_path',lambda:cap.write_json(caproot/'unlisted.json',{}));refuse('layer_outside_domain',lambda:cap.save_npz(caproot/'layers/layer-01034.npz',array=payload));refuse('exact_json_cap_before_publication',lambda:cap.write_json(caproot/'context.json',{'large':'x'*(exact+1)}));assert not (caproot/'context.json').exists()
 for path,h in pins.items():assert sha(path)==h
 result={'status':'full_index_storage_cap_and_source_bound_continuation_controls_passed','full_calendar_indices':1034,'synthetic_layers_written':3,'actual_next_layer_written_after_resume':True,'unchanged_numerical_bytecode':True,'native_serialization_parity':parity,'resumed_prefix_layers':len(restored),'refusals':failures,'all_refusals_passed':True,'scientific_output_budget':budget.verify(),'source_sha256':pins,'current_carrier_read_or_sliced':False,'elapsed_seconds':time.monotonic()-start}
 result['source_manifest_sha256']=args.source_manifest_sha256;replay.verify_profile(profile);common.bindings(args);save(Path(output)/'storage-controls.json',result);return result
