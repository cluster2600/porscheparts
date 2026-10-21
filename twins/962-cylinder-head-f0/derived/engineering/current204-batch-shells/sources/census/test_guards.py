"""UNRUN stdlib/AST guards; never import the reader, NumPy, Gmsh or geometry."""
import ast
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path(__file__).with_name('reader.py')
SOURCE_SHA='eb9b5cfeab50c9c74c87c3995b0ce97ebbc365581a2cc552f26fb73b96bd0a1f'
NAMES={'movable_from_poor_rows','incident_positions','partial_after_proof'}

def functions():
 raw=SOURCE.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise ValueError('Exact selected full-star reader required')
 selected=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in NAMES]
 if {n.name for n in selected}!=NAMES:raise ValueError('All three actual pure functions required')
 scope={}
 exec(compile(ast.Module(body=selected,type_ignores=[]),'<actual-full-star-selection>','exec'),scope)
 return scope

class Guards(unittest.TestCase):
 def test_complete_union_includes_initially_good_and_shared_rows(self):
  f=functions();poor=[[1,2,3,4],[1,2,4,5]]
  rows=poor+[[2,4,6,7],[1,4,5,7],[1,2,6,7]]
  movable=f['movable_from_poor_rows'](poor,[4,5,6,7],3)
  self.assertEqual(movable,[4,5])
  observed=f['incident_positions'](rows,movable)
  oracle=[i for i,row in enumerate(rows) if sum(int(a==b) for a in row for b in movable)>0]
  self.assertEqual(observed,oracle);self.assertEqual(observed,[0,1,2,3])
  self.assertEqual(len(set(observed)),4)
  self.assertEqual([i for i in observed if i>=len(poor)],[2,3])

 def test_input_row_order_does_not_change_movable_membership(self):
  f=functions();poor=[[5,2,4,1],[4,3,2,1]]
  self.assertEqual(f['movable_from_poor_rows'](poor,[4,5,6,7],3),[4,5])
  rows=[[1,2,6,7],[1,4,5,7],[2,4,6,7],*poor]
  self.assertEqual(f['incident_positions'](rows,[4,5]),[1,2,3,4])

 def test_empty_and_all_boundary_seed_cases(self):
  f=functions();self.assertEqual(f['movable_from_poor_rows']([],[],3),[])
  self.assertEqual(f['incident_positions']([],[]),[])
  self.assertEqual(f['movable_from_poor_rows']([[1,2,3,4]],[5],4),[])
  self.assertEqual(f['incident_positions']([[1,2,3,4]],[]),[])
  # The real main retains all current poor rows and explicitly reports any unseedable rows.

 def test_invalid_boundary_classification_and_connectivity_refuse(self):
  f=functions();m=f['movable_from_poor_rows'];s=f['incident_positions']
  for boundary in [0,-1,True,3.0]:
   with self.assertRaises(ValueError):m([[1,2,3,4]],[4],boundary)
  for interior in [[3,4],[5,4],[4,4],[True],[4.0]]:
   with self.assertRaises(ValueError):m([[1,2,3,4]],interior,3)
  with self.assertRaises(ValueError):m([[1,2,3,5]],[4],3)
  for row in [[1,2,3],[1,2,3,0],[1,2,3,True],[1,2,2,4],[1,2,3,4.0]]:
   with self.assertRaises(ValueError):m([row],[4],3)
   with self.assertRaises(ValueError):s([row],[4])
  for movable in [[4,4],[5,4],[True],[0],[4.0]]:
   with self.assertRaises(ValueError):s([[1,2,3,4]],movable)

 def test_exact_reuse_reverse_and_read_only_call_scope(self):
  raw=SOURCE.read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),SOURCE_SHA)
  delta=json.loads(SOURCE.with_name('source-delta.json').read_bytes());restored=raw.decode()
  for row in reversed(delta['exact_replacements']):
   self.assertEqual(restored.count(row['new']),row['count']);restored=restored.replace(row['new'],row['old'])
  original=(ROOT/delta['preserved_reader']).read_bytes();self.assertEqual(restored.encode(),original)
  tree=ast.parse(raw);new={n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
  old={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(original).body if isinstance(n,ast.FunctionDef)}
  for name in delta['unchanged_function_ASTs']:self.assertEqual(new[name],old[name])
  self.assertEqual(hashlib.sha256(SOURCE.with_name('run_readback.py').read_bytes()).hexdigest(),'4fb37080e1f3847b8b1d14d5df467799d8e9f7bf81b0a09170e5850857de3943')
  calls=[ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n,ast.Call)]
  for forbidden in ['gmsh.write','gmsh.model.mesh.generate','gmsh.model.mesh.optimize','gmsh.model.mesh.createGeometry','gmsh.model.mesh.rebuildElementCache']:self.assertNotIn(forbidden,calls)
  self.assertNotIn('expected_positive_poor_bins',raw.decode());self.assertNotIn('completed_saved_diagnosis',raw.decode())
  self.assertIn('complete_tagged_cells',raw.decode());self.assertIn('unseedable_positive_poor_tetrahedron_tags',raw.decode())

 def test_partial_saved_proof_join_and_refusals(self):
  from copy import deepcopy
  select=functions()['partial_after_proof']
  proof={'tetrahedra':4,'total_mesh_nodes':7,'source_boundary_identity':{'boundary':3},'array_sha256s':{k:'a'*64 for k in ['sorted_node_tags_sha256','sorted_coordinates_sha256','sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256']},'quality':{k:{'count':4,'nonpositive_count':0} for k in ['minimum_jacobian','native_volume_mm3','minimum_SICN','independent_signed_volume_mm3']}}
  proof['quality']['minimum_SICN'].update(minimum=.05,below_point1_count=2)
  contract={'MSH_sha256':'m','MSH_bytes':10,'local_candidate_report_sha256':'localreport','local_candidate_arrays_sha256':'localarrays','current_local_domain_report_sha256':'domainreport','current_local_domain_peer_sha256':'domainpeer','original_parent_MSH_sha256':'parent','partial_report_sha256':'report','partial_contract_sha256':'actual','partial_reader_sha256':'reader','partial_runner_sha256':'runner','partial_native_log_sha256':'log','partial_output_inventory':{'frozen':'identity'},'expected_saved_counts':{'tetrahedra':4,'total_mesh_nodes':7},'expected_positive_poor_total':2,'diagnostic_maximum_nonpositive_cells':0,'expected_source_boundary_identity':{'boundary':3}}
  worker={'schema':'962-apex1474426-head-application-result/v1','status':'completed_partial_head_replacement_whole_head_quality_gate_applied','stage':'completed_partial_repair_audits','procedural_checks_passed':True,'partial_replacement_completed':True,'saved_mesh_identity_exact':True,'bound_inputs_unchanged':True,'after':deepcopy(proof),'saved_reopen':deepcopy(proof),'mesh_sha256':'m','mesh_bytes':10,'local_candidate_report_sha256':'localreport','local_candidate_arrays_sha256':'localarrays','current_local_domain_report_sha256':'domainreport','current_local_domain_peer_sha256':'domainpeer','original_parent_MSH_sha256':'parent','actual_whole_head_positive_poor_count':2,'actual_whole_head_SICN_gate_passed':False}
  receipt={'returncode':2,'stop_reason':None,'readback_report_sha256':'report','contract_sha256':'actual','reader_sha256':'reader','runner_sha256':'runner','native_log_sha256':'log'}
  closed={'returncode':2,'stop_reason':None,'wait_reaped':True,'all56_inputs_unchanged':True,'all3_selected_native_runtime_unchanged':True,'selected_NumPy_unchanged':True,'actual_unchanged':True,'actual_sha256':'actual','outputs':{'frozen':'identity'}}
  self.assertEqual(select(worker,receipt,closed,contract),proof)
  def reject(w=worker,r=receipt,z=closed,c=contract):
   with self.assertRaises((ValueError,KeyError)):select(w,r,z,c)
  for field,value in [('schema','962-one-head-star-partial-replacement/v1'),('local_candidate_report_sha256','other'),('local_candidate_arrays_sha256','other'),('current_local_domain_report_sha256','other'),('current_local_domain_peer_sha256','other'),('mesh_sha256','other'),('procedural_checks_passed',False),('actual_whole_head_positive_poor_count',3),('actual_whole_head_SICN_gate_passed',True)]:
   w=deepcopy(worker);w[field]=value;reject(w=w)
  w=deepcopy(worker);w['saved_reopen']['quality']['minimum_SICN']['minimum']=.06;reject(w=w)
  w=deepcopy(worker)
  for field in ['after','saved_reopen']:w[field]['quality']['minimum_SICN']['count']=3
  reject(w=w)
  for field,value in [('reader_sha256','other'),('readback_report_sha256','other'),('stop_reason','deadline')]:
   r=deepcopy(receipt);r[field]=value;reject(r=r)
  for field,value in [('wait_reaped',False),('all56_inputs_unchanged',False),('selected_NumPy_unchanged',False),('actual_sha256','other'),('outputs',{})]:
   z=deepcopy(closed);z[field]=value;reject(z=z)


if __name__=='__main__':unittest.main()
