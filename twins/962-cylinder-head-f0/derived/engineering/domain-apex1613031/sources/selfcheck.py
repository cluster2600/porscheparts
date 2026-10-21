"""UNRUN stdlib caller guards; no pair query, native operation or scientific import."""
from pathlib import Path
from fractions import Fraction
from itertools import combinations
from copy import deepcopy
import ast,hashlib,json,math,struct,unittest
SOURCE=Path(__file__).with_name('certify_domain.py')
SOURCE_SHA='3cb92684b1d757617854d5ea1b0896e04db632648251810fc784289110330118'
ROOT=SOURCE.resolve().parents[3]
if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Exact reviewed source required')
tree=ast.parse(SOURCE.read_text());top={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
assignments={n.targets[0].id:n.value for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
inputs=ast.literal_eval(assignments['INPUTS'])
paths={n:ast.literal_eval(assignments[n]) for n in ['OBSERVATION','SHELL','WORKER','ARRAYS','PEER','PEER_BINDINGS','ACCEPTANCE','HELPER','CHAIN_SOURCE']}
ns={'Fraction':Fraction,'math':math,'struct':struct,'INPUTS':inputs,'QUALIFICATION':dict(native_application_authorized=False,head_execution_authorized=False,stitching_authorized=False,engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)}
ns.update({name:paths[name] for name in ['ARRAYS','WORKER','PEER','PEER_BINDINGS']})
exec(compile(ast.Module(body=[top['original'],top['saved_candidate']],type_ignores=[]),'<reviewed-case-adapter-AST>','exec'),ns)

def record(name):
 path=ROOT/paths[name]
 if hashlib.sha256(path.read_bytes()).hexdigest()!=inputs[paths[name]]:raise ValueError('Frozen guard input drift')
 return json.loads(path.read_text())

class CallerGuards(unittest.TestCase):
 def test_single_saved_candidate_and_refusals(self):
  worker,arrays,shell,peer,acceptance,peer_bindings=[record(n) for n in ['WORKER','ARRAYS','SHELL','PEER','ACCEPTANCE','PEER_BINDINGS']]
  points,cells=ns['saved_candidate'](worker,arrays,shell,peer,acceptance,peer_bindings)
  self.assertEqual(set(points),set(arrays['saved_reopen']['node_tags']));self.assertEqual(len(cells),14)
  bad=deepcopy(peer);bad['decision']='UNREVIEWED'
  with self.assertRaises(ValueError):ns['saved_candidate'](worker,arrays,shell,bad,acceptance,peer_bindings)
  bad=deepcopy(worker);bad['actual_SICN_gate_passed']=False
  with self.assertRaises(ValueError):ns['saved_candidate'](bad,arrays,shell,peer,acceptance,peer_bindings)
  bad=deepcopy(arrays);bad['saved_reopen']['coordinates_mm'][0][0]=float('nan');bad['after']=bad['saved_reopen']
  with self.assertRaises(ValueError):ns['saved_candidate'](worker,bad,shell,peer,acceptance,peer_bindings)
  bad=deepcopy(shell);bad['vertex_rows'][0]['binary64_little_endian_bytes_hex']='00'*24
  with self.assertRaises(ValueError):ns['saved_candidate'](worker,arrays,bad,peer,acceptance,peer_bindings)
  bad=deepcopy(arrays);bad['saved_reopen']['tetra_node_tags'].pop();bad['after']=bad['saved_reopen']
  with self.assertRaises(ValueError):ns['saved_candidate'](worker,bad,shell,peer,acceptance,peer_bindings)
  bad=deepcopy(acceptance);bad['peer']['sha256']='0'*64
  with self.assertRaises(ValueError):ns['saved_candidate'](worker,arrays,shell,peer,bad,peer_bindings)
  for name,key,value in [('fixture-report.json','sha256','0'*64),('arrays.json','path','wrong.json'),('arrays.json','bytes',13884)]:
   bad=deepcopy(peer_bindings);bad['full8_output_inventory'][name][key]=value
   with self.assertRaises(ValueError):ns['saved_candidate'](worker,arrays,shell,peer,acceptance,bad)
  bad=deepcopy(peer_bindings);bad['d60_historical_command_conformant']=True
  with self.assertRaises(ValueError):ns['saved_candidate'](worker,arrays,shell,peer,acceptance,bad)
  bad=deepcopy(worker);bad['declared_controller_command_conformant']=True
  with self.assertRaises(ValueError):ns['saved_candidate'](bad,arrays,shell,peer,acceptance,peer_bindings)
 def test_original_complete_map_and_refusals(self):
  observation,shell=[record(n) for n in ['OBSERVATION','SHELL']]
  points,cells,mapping=ns['original'](observation,shell)
  self.assertEqual(set(points),set(range(1,11)));self.assertEqual(len(cells),14)
  self.assertEqual(mapping[1613031],10);self.assertTrue(all(10 in row for row in cells.values()))
  bad=deepcopy(observation);bad['apex']=1474426
  with self.assertRaises(ValueError):ns['original'](bad,shell)
  bad=deepcopy(observation);bad['selected_node_rows'].pop()
  with self.assertRaises(ValueError):ns['original'](bad,shell)
  bad=deepcopy(shell);bad['global_to_local_node_tags']={}
  with self.assertRaises(ValueError):ns['original'](observation,bad)
  bad=deepcopy(shell);bad['declared_controller_command_conformant']=True
  with self.assertRaises(ValueError):ns['original'](observation,bad)
 def test_exact_donors_complete_pair_policy_and_authority_AST(self):
  for name in ['HELPER','CHAIN_SOURCE']:
   path=ROOT/paths[name];self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),inputs[paths[name]])
  donor=ast.parse((ROOT/paths['CHAIN_SOURCE']).read_text());df={n.name:n for n in donor.body if isinstance(n,ast.FunctionDef)}
  for name in ['cycle','complex_rows']:self.assertEqual(ast.dump(top[name],include_attributes=False),ast.dump(df[name],include_attributes=False))
  main=top['main'];loop=next(n for n in ast.walk(main) if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and [x.id for x in n.target.elts]==['name','points','cells','count'])
  self.assertEqual(ast.unparse(loop.iter),"[('old', old_points, old_cells, 91), ('candidate', new_points, new_cells, 91)]")
  calls=[n for n in ast.walk(loop) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='pair_check']
  self.assertEqual(len(calls),1);self.assertEqual(ast.unparse(calls[0]),'helper.pair_check(points, cells[first], cells[second])')
  self.assertIn("c.get('diagnostic_execution_authorized') is not True",ast.unparse(main))
  self.assertIn("c.get('native_execution_authorized') is not False",ast.unparse(main))
  self.assertIn("c.get('qualification') != QUALIFICATION",ast.unparse(main))
  self.assertFalse(any(isinstance(n,(ast.Import,ast.ImportFrom)) and any(a.name.split('.')[0] in ['numpy','scipy','gmsh'] for a in getattr(n,'names',[])) for n in ast.walk(tree)))

 def test_actual_tag_lookup_accepts_gapped_interiors_and_refuses_bad_membership(self):
  # Manufactured adapter-only metadata. Main's frozen hashes would reject these edits.
  worker,arrays,shell,peer,acceptance,peer_bindings=[record(n) for n in ['WORKER','ARRAYS','SHELL','PEER','ACCEPTANCE','PEER_BINDINGS']]
  a=arrays['saved_reopen'];changed={t:t+1000 for t in a['node_tags'] if t>9}
  a['node_tags']=[changed.get(t,t) for t in a['node_tags']]
  a['tetra_node_tags']=[[changed.get(t,t) for t in row] for row in a['tetra_node_tags']]
  arrays['after']=deepcopy(a)
  state=worker['saved_reopen']
  state['node_classifications']=[[changed.get(t,t),dim] for t,dim in state['node_classifications']]
  state['node_entity_classifications']=[[changed.get(t,t),dim,entity] for t,dim,entity in state['node_entity_classifications']]
  worker['after']=deepcopy(state)
  points,cells=ns['saved_candidate'](worker,arrays,shell,peer,acceptance,peer_bindings)
  self.assertEqual(set(points),set(a['node_tags']));self.assertEqual(len(cells),14)
  for tag in changed.values():
   self.assertEqual(points[tag],tuple(Fraction.from_float(v) for v in a['coordinates_mm'][a['node_tags'].index(tag)]))
  bad=deepcopy(arrays);bad['saved_reopen']['node_tags'][-1]=bad['saved_reopen']['node_tags'][-2];bad['after']=bad['saved_reopen']
  with self.assertRaises(ValueError):ns['saved_candidate'](worker,bad,shell,peer,acceptance,peer_bindings)
  bad=deepcopy(arrays);bad['saved_reopen']['tetra_node_tags'][0][0]=99999;bad['after']=bad['saved_reopen']
  with self.assertRaises(ValueError):ns['saved_candidate'](worker,bad,shell,peer,acceptance,peer_bindings)
  bad=deepcopy(worker);bad['saved_reopen']['node_classifications'][-1][1]=2;bad['after']=bad['saved_reopen']
  with self.assertRaises(ValueError):ns['saved_candidate'](bad,arrays,shell,peer,acceptance,peer_bindings)

if __name__=='__main__':unittest.main()
