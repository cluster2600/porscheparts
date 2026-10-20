"""UNRUN stdlib/AST binding guards; never import the worker or scientific modules."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path(__file__).with_name('propose_component.py')
SOURCE_SHA='ad4dc24d21d803853006753b0b3cd28061d5b3fec9eb18576a6b4e0549faf977'
def selected_functions():
 raw=SOURCE.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise ValueError('Exact held component source required')
 names={'component_choice','bound_contract'}
 nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names]
 if {n.name for n in nodes}!=names:raise ValueError('Both actual metadata selectors required')
 scope={'json':json}
 exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual-component-selectors>','exec'),scope)
 return scope

class Guards(unittest.TestCase):
 def test_all73_manifest_cases_cover_exact_saved_partitions(self):
  m=json.loads(SOURCE.with_name('component-manifest.json').read_bytes());choose=selected_functions()['component_choice']
  self.assertEqual(len(m['cases']),73)
  for i,c in enumerate(m['cases'],1):self.assertEqual(choose(m,i),c)
  self.assertEqual(sum(c['counts']['movable_nodes'] for c in m['cases']),82)
  self.assertEqual(sum(c['counts']['TET4'] for c in m['cases']),2482)
  self.assertEqual(sum(c['counts']['poor'] for c in m['cases']),110)
  self.assertEqual(sum(c['counts']['good'] for c in m['cases']),2372)
  self.assertEqual(sum(c['counts']['shared'] for c in m['cases']),58)
  for key,n in [('movable_node_tags',82),('tetrahedron_tags',2482),('initially_positive_poor_tetrahedron_tags',110)]:
   rows=[v for c in m['cases'] for v in c[key]];self.assertEqual(len(rows),n);self.assertEqual(len(set(rows)),n)
 def test_invalid_or_stale_case_selection_refuses(self):
  m=json.loads(SOURCE.with_name('component-manifest.json').read_bytes());choose=selected_functions()['component_choice']
  for value in (None,True,False,0,74,1.0,'1'):
   with self.assertRaises(ValueError):choose(m,value)
  for key,value in [('schema','old'),('cases',[])]:
   changed=deepcopy(m);changed[key]=value
   with self.assertRaises(ValueError):choose(changed,1)
  for key,value in [('movable_nodes',3),('coordinate_variables',99),('TET4',0),('TET4',78)]:
   changed=deepcopy(m);changed['cases'][0]['counts'][key]=value
   with self.assertRaises(ValueError):choose(changed,1)
 def test_held_authority_refuses_before_runtime_or_input_reads(self):
  held=json.loads(SOURCE.with_name('held-contract.json').read_bytes());bound=selected_functions()['bound_contract']
  class TextOnly:
   def __init__(self,obj):self.obj=obj
   def read_text(self):return json.dumps(self.obj)
  with self.assertRaises(ValueError):bound(TextOnly(held))
  base={'schema':'962-current110-one-component-exact-sicn/v1','scope':'one_frozen_current110_component_analytic_SLSQP_only','proposal_execution_authorized':True,'root_and_peer_review_complete':True,'selected_runtime_review_complete':True}
  for k in ('proposal_execution_authorized','root_and_peer_review_complete','selected_runtime_review_complete'):
   changed=dict(base);changed[k]=False
   with self.assertRaises(ValueError):bound(TextOnly(changed))
 def test_complete_source_reversal17_helpers_and_controller_exact(self):
  raw=SOURCE.read_bytes();delta=json.loads(SOURCE.with_name('source-delta.json').read_bytes());text=raw.decode()
  for row in reversed(delta['exact_replacements']):
   self.assertEqual(text.count(row['new']),row['count']);text=text.replace(row['new'],row['old'])
  original=(ROOT/delta['donor_source']['path']).read_bytes();self.assertEqual(text.encode(),original)
  new={n.name:n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
  old={n.name:n for n in ast.parse(original).body if isinstance(n,ast.FunctionDef)}
  self.assertEqual(len(delta['unchanged_function_source_and_AST_names']),17)
  for name in delta['unchanged_function_source_and_AST_names']:
   self.assertEqual(ast.dump(new[name],include_attributes=False),ast.dump(old[name],include_attributes=False))
  self.assertEqual(hashlib.sha256(SOURCE.with_name('run_readback.py').read_bytes()).hexdigest(),'8fc4918b6a0a6c07439eb57c77ea922e778207b59ed0e9f367a8f02c34946206')
 def test_one_call_no_mesh_and_finite_retention_precedes_final_refusal(self):
  raw=SOURCE.read_text();tree=ast.parse(raw)
  calls=[ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n,ast.Call)]
  self.assertEqual(calls.count('optimize.minimize'),1)
  for name in ('gmsh.write','gmsh.model.mesh.generate','gmsh.model.mesh.optimize','subprocess.Popen','np.linalg.solve'):self.assertNotIn(name,calls)
  self.assertIn("bounds=[(None,None)]*(3*len(FREE))+[(initial_min,1.)]",raw)
  self.assertIn('volume==before_volume',raw);self.assertIn("all(row['exact_point1_gate_passed'] for row in rows)",raw)
  self.assertLess(raw.index("save(out/'diagnostic.json',diagnostic)"),raw.index("if not report['bound_inputs_unchanged']"))
  self.assertIn('donor39_cell_shell_volume_reused=False',raw)
if __name__=='__main__':unittest.main()
