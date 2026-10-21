"""UNRUN fixed-case source/metadata and mocked-operation refusals; no native or geometry."""
import ast,copy,hashlib,importlib.util,json
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase,main,mock
SOURCE=Path(__file__).with_name('reader.py');PREP=SOURCE.parent
SOURCE_SHA='eaa5f5d7fc14dc9653443d70a4801420bb5ecb42f4375f986ce187f33ba723f0'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
spec=importlib.util.spec_from_file_location('held1485102_default_source',SOURCE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module) # definitions only, never main

class Guards(TestCase):
 def case_record(self):
  manifest=json.loads((module.ROOT/module.MANIFEST).read_text());batch=json.loads((module.ROOT/module.BATCH).read_text())
  return next(x for x in manifest['cases_in_increasing_apex_order'] if x['apex']==1485102),next(x for x in batch['all_candidate_star_records'] if x['apex']==1485102)
 def contract_fixture(self):
  return copy.deepcopy(json.loads((PREP/'held-contract.json').read_text())['source_contract_values'])
 def authorized_fixture(self):
  c=self.contract_fixture()
  for key in ['native_execution_authorized','root_and_peer_review_complete','selected_runtime_review_complete','cavity_default_optimizer_authorized']:c[key]=True
  return c
 def test_finite_pins_held_false_baseline_shape_and_current_translation(self):
  held=json.loads((PREP/'held-contract.json').read_text());c=self.contract_fixture()
  self.assertEqual(c['optimization'],{'method':'','force':True});self.assertEqual(c['options']['Mesh.OptimizeThreshold'],.3)
  self.assertEqual(c['declared_operation_counts'],dict(generate=0,createGeometry_dim3=0,optimize_default=1,rebuildElementCache=1,write_mesh=1,solve=0))
  self.assertEqual(c['saved_Netgen_baseline'],module.BASELINE);self.assertEqual(module.BASELINE_INTERIOR_TAGS,[39,40,41])
  self.assertEqual(len(c['current_star_binding']['native_index_translation']),52);self.assertEqual(c['current_star_binding']['native_index_changes'],52)
  for key in ['native_execution_authorized','root_and_peer_review_complete','selected_runtime_review_complete','cavity_default_optimizer_authorized','automatic_retry']:
   self.assertIs(c[key],False)
  self.assertFalse(any(held['qualification'].values()));self.assertIsNone(held['actual_contract']);self.assertIsNone(held['trial_result'])
  self.assertFalse((module.ROOT/module.OUTPUT).exists())
  self.assertEqual(held['deferred_mesh_identity_only'],module.BASELINE['mesh'])
  for path,digest in held['input_hashes'].items():
   if path==module.BASELINE['mesh']['path']:continue
   self.assertEqual(module.sha(module.ROOT/path),digest)
 def test_only_distinct_default_authority_and_no_other_operation(self):
  c=self.authorized_fixture()
  with mock.patch.object(module,'OUT',module.ROOT/module.OUTPUT):module.require_authority(c)
  for key in ['generation_authorized','cavity_Netgen_optimizer_authorized','geometry_creation_authorized','head_execution_authorized','head_edit_authorized','domain_execution_authorized','outside_owner_query_authorized','PDE_solve_authorized','head_PDE_authorized','material_qualified','process_calibrated','manufacturing_authorized']:
   bad=copy.deepcopy(c);bad[key]=True
   with self.subTest(field=key),mock.patch.object(module,'OUT',module.ROOT/module.OUTPUT):
    with self.assertRaises(ValueError):module.require_authority(bad)
  for key,value in [('optimization',{'method':'Netgen','force':True}),('geometry_creation_dim_tags',[[3,1]]),('automatic_retry',True),('declared_controller_command_conformant',True),('output_directory','work/962-engineering/old-output')]:
   bad=copy.deepcopy(c);bad[key]=value
   with self.subTest(field=key),mock.patch.object(module,'OUT',module.ROOT/module.OUTPUT):
    with self.assertRaises(ValueError):module.require_authority(bad)
 def test_fixed_stopped_baseline_descriptors_no_old_authority_or_other_apex(self):
  c=self.contract_fixture();module.configure_baseline(c)
  self.assertEqual((module.INPUT,module.WORKER,module.ARRAYS),tuple(module.BASELINE[k]['path'] for k in ['mesh','worker','arrays']))
  for mode in ['other_apex','missing_root_acceptance','wrong_mesh_path','wrong_peer_digest']:
   bad=copy.deepcopy(c)
   if mode=='other_apex':bad['case_apex']=1613791
   if mode=='missing_root_acceptance':bad['saved_Netgen_baseline'].pop('root_acceptance')
   if mode=='wrong_mesh_path':bad['saved_Netgen_baseline']['mesh']['path']='work/962-engineering/unrelated.msh'
   if mode=='wrong_peer_digest':bad['saved_Netgen_baseline']['result_peer']['sha256']='0'*64
   with self.subTest(mode=mode):
    with self.assertRaises(ValueError):module.configure_baseline(bad)
 def test_exact_case_binding_is_historical_source_not_historical_output(self):
  c=self.contract_fixture();cavity=module.load_cavity_module();case,record=module.configure_case(c,cavity)
  self.assertEqual((cavity.NV,cavity.NF,cavity.NB,cavity.APEX),(28,52,18,1485102))
  self.assertEqual(case['old_tetrahedra'],52);self.assertEqual(len(record['all_vertex_tags']),29)
  self.assertNotEqual(c['output_directory'],case['stage_paths']['netgen'])
  self.assertTrue(cavity.candidate_storage_admission({'referenced_interior_nodes':1,'tetrahedra':52},case))
  self.assertFalse(cavity.candidate_storage_admission({'referenced_interior_nodes':0,'tetrahedra':64},case))
  self.assertFalse(cavity.candidate_storage_admission({'referenced_interior_nodes':3,'tetrahedra':51},case))
  for key,value in [('case_apex',1393275),('case_record_sha256','0'*64),('output_directory',case['stage_paths']['netgen'])]:
   bad=copy.deepcopy(c);bad[key]=value
   with self.subTest(field=key):
    with self.assertRaises(ValueError):module.configure_case(bad,cavity)
 def test_natural_rejected_Netgen_and_real_schema_refusals(self):
  c=self.contract_fixture();module.configure_baseline(c);case,record=self.case_record();w=json.loads((module.ROOT/module.WORKER).read_text())
  module.require_saved_baseline(w,c,case,record['shell'])
  for mode in ['generation_status','quality_pass','wrong_count','false_route','wrong_interior_tags','wrong_global_classes','wrong_shell_map']:
   bad=copy.deepcopy(w)
   if mode=='generation_status':bad['status']='completed_finite_selected_cavity_generation_only'
   if mode=='quality_pass':bad['actual_SICN_gate_passed']=True
   if mode=='wrong_count':bad['saved_reopen']['tetrahedra']=63
   if mode=='false_route':bad['next_stage']='domain'
   if mode=='wrong_interior_tags':bad['saved_reopen']['node_classifications'][-1][0]=31
   if mode=='wrong_global_classes':bad['original_source_classifications']['boundary_global_node_tags'].pop()
   if mode=='wrong_shell_map':bad['local_to_global_shell_node_tags'].reverse()
   with self.subTest(mode=mode):
    with self.assertRaises(ValueError):module.require_saved_baseline(bad,c,case,record['shell'])
  paths=[module.BASELINE[k]['path'] for k in ['receipt','root_closed','result_peer','root_acceptance']]+[module.ROOT_SAVED_REVIEW]
  originals=[json.loads((module.ROOT/path).read_text()) for path in paths]
  for mode in ['resource_stop','root_error','missing_wait','wrong_inventory','false_old_acceptance']:
   d=copy.deepcopy(originals)
   if mode=='resource_stop':d[0]['stop_reason']='deadline'
   if mode=='root_error':d[1]['root_error']='unclosed'
   if mode=='missing_wait':d[1]['controller_wait_reaped']=False
   if mode=='wrong_inventory':d[1]['output_files']['arrays.json']['sha256']='0'*64
   if mode=='false_old_acceptance':d[3]['local_quality_storage_pass_apices'].append(1485102)
   with self.subTest(mode=mode),mock.patch.object(module.json,'loads',side_effect=d):
    with self.assertRaises(ValueError):module.require_saved_baseline(w,c,case,record['shell'])
 def test_current52_semantics_raw_words_and_index_translation_refusals(self):
  c=self.contract_fixture();case,record=self.case_record();self.assertEqual(module.require_current_star(c,case,record),c['current_star_binding'])
  for mode in ['reuse_old_index','wrong_semantic_hash','wrong_node_hash','wrong_parent']:
   bad=copy.deepcopy(c)
   if mode=='reuse_old_index':bad['current_star_binding']['native_index_translation'][0]['current_native_array_index']=bad['current_star_binding']['native_index_translation'][0]['historical_native_array_index']
   if mode=='wrong_semantic_hash':bad['current_star_binding']['semantic_rows_sha256']='0'*64
   if mode=='wrong_node_hash':bad['current_star_binding']['node_rows_sha256']='0'*64
   if mode=='wrong_parent':bad['current_star_binding']['current_parent_MSH_sha256']='0'*64
   with self.subTest(mode=mode):
    with self.assertRaises(ValueError):module.require_current_star(bad,case,record)
  paths=[module.CURRENT_CENSUS,module.CURRENT_ACCEPT,module.CURRENT_CONTRACT,module.PARTIAL,module.PARTIAL_ACCEPT]
  original=[json.loads((module.ROOT/path).read_text()) for path in paths]
  for mode in ['corner_order','quality_word','class_flag','coordinate_word','claim_head']:
   d=copy.deepcopy(original);cz=d[0]['complete_seed_star_census']
   if mode=='corner_order':next(r for r in cz['complete_incident_tetrahedra'] if 1485102 in r['node_tags'])['node_tags'].reverse()
   if mode=='quality_word':next(r for r in cz['complete_incident_tetrahedra'] if 1485102 in r['node_tags'])['initial_native_SICN']=.9
   if mode=='class_flag':next(r for r in cz['unique_incident_nodes'] if r['node_tag']==355231)['source_boundary_tag']=False
   if mode=='coordinate_word':next(r for r in cz['unique_incident_nodes'] if r['node_tag']==355231)['coordinates_mm'][0]+=.001
   if mode=='claim_head':d[1]['whole_head_quality_accepted']=True
   with self.subTest(mode=mode),mock.patch.object(module.json,'loads',side_effect=d):
    with self.assertRaises(ValueError):module.require_current_star(c,case,record)
 def test_one_default_cache_and_truthful_failed_attempt_counters(self):
  for failure in [None,'optimize','cache']:
   calls=[]
   def optimize(**kwargs):
    calls.append(('optimize',kwargs))
    if failure=='optimize':raise RuntimeError('mock optimizer failure')
   def rebuild(flag):
    calls.append(('cache',flag))
    if failure=='cache':raise RuntimeError('mock cache failure')
   fake=SimpleNamespace(model=SimpleNamespace(mesh=SimpleNamespace(optimize=optimize,rebuildElementCache=rebuild)))
   report={'native_operation_counts':{k:0 for k in module.COUNTS}}
   if failure:
    with self.assertRaises(RuntimeError):module.default_once(fake,report)
   else:module.default_once(fake,report)
   self.assertEqual(calls[0],('optimize',{'method':'','force':True}));self.assertEqual(report['native_operation_counts']['optimize_default'],1)
   self.assertEqual(report['native_operation_counts']['rebuildElementCache'],0 if failure=='optimize' else 1)
   self.assertEqual(report['native_operation_counts']['generate'],0);self.assertEqual(report['native_operation_counts']['createGeometry_dim3'],0)
   if failure!='optimize':self.assertEqual(calls[1],('cache',False))
 def test_exact_kernels_default_helper_and_literal_only_controller_reversal(self):
  defs=lambda text:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
  donor=(module.ROOT/'work/962-engineering/head-star-current204-local-stages-prep-001/netgen_case.py').read_text();old=defs(donor);new=defs(SOURCE.read_text())
  for name in ['load_cavity_module','expected_live','require_before']:self.assertEqual(new[name],old[name])
  operation=(module.ROOT/module.DEFAULT).read_text();self.assertEqual(new['optimize_and_refresh'],defs(operation)['optimize_and_refresh'])
  original=(module.ROOT/'work/962-engineering/head-star-current204-local-stages-prep-001/run_netgen.py').read_text();selected=(PREP/'run_readback.py').read_text()
  selected=selected.replace('specific saved-cavity default-optimizer operation','specific saved-cavity Netgen operation').replace('one_saved_apex1485102_default_optimizer_witness','one_selected_current204_cavity_netgen_witness').replace("'createGeometry_dim3':0,'optimize_default':1","'createGeometry_dim3':1,'optimize_Netgen':1")
  self.assertEqual(selected,original)
  source=SOURCE.read_text();self.assertNotIn('gmsh.model.mesh.generate(',source);self.assertNotIn('gmsh.model.mesh.createGeometry(',source)
  self.assertNotIn("method='Netgen'",source);self.assertEqual(module.COUNTS['createGeometry_dim3'],0)

if __name__=='__main__':main()
