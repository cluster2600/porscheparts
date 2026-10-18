"""UNRUN stdlib selected-AST saved-metadata/fake-API guards; no native or pair query."""
from pathlib import Path
from fractions import Fraction
from itertools import combinations
from types import SimpleNamespace
import ast,copy,hashlib,json,math,struct,sys,unittest

SOURCE_SHA='15443fe1c0adebb02a4abe8a4db1c8dbb2f5148ad37f992ae8e74df8cd28d7d1'
source=Path(__file__).with_name('reader.py');ROOT=source.resolve().parents[3]
assert hashlib.sha256(source.read_bytes()).hexdigest()==SOURCE_SHA
tree=ast.parse(source.read_text());functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
constants={'OUTPUT','MESH','CONTEXT','CONTEXT_CONTRACT','OBSERVATION','SHELL','ARRAYS','WORKER','LOCAL_PEER','DOMAIN','DOMAIN_PEER','DOMAIN_SOURCE','DOMAIN_ACTUAL','ORIGINAL_WORKER','ORIGINAL_RECEIPT','PARTIAL_CLOSED','PARTIAL_METADATA','FIRST','PROOF_SOURCE','HEAD','CORE','AUDIT','FIXED_INPUTS','ARRAYS_SHA','WORKER_SHA','FREE','APEX','NMAX','EMAX','BOUNDARY','RUNTIME','OPTIONS','CONTROLS','COUNTS','FORBIDDEN','QUALIFICATION'}
assignments=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets)]
ns={'Path':Path,'Fraction':Fraction,'combinations':combinations,'struct':struct,'math':math,'json':json,'hashlib':hashlib,'sys':sys,'ROOT':ROOT,'OUT':source.parent}
selected=assignments+[functions[n] for n in ['sha','require_contract','require_domain','candidate_rows','make_case','edit_once','require_snapshot','require_original_records','valid_positive_volume']]
exec(compile(ast.fix_missing_locations(ast.Module(body=selected,type_ignores=[])),'<reviewed-case-and-mock-AST>','exec'),ns)
originals={name:ns[name] for name in ['sha','require_domain','candidate_rows']};CACHE={}

def record(name):
 path=ROOT/ns[name]
 if name not in CACHE:
  assert hashlib.sha256(path.read_bytes()).hexdigest()==ns['FIXED_INPUTS'][ns[name]]
  CACHE[name]=json.loads(path.read_text())
 return copy.deepcopy(CACHE[name])

def make():
 return ns['make_case'](*[record(n) for n in ['OBSERVATION','SHELL','WORKER','ARRAYS','CONTEXT','DOMAIN','DOMAIN_PEER']])

def fake(case,calls):
 mesh=SimpleNamespace(getMaxNodeTag=lambda:case['nmax'],getMaxElementTag=lambda:case['emax'],
  getElement=lambda tag:(4,case['old'][tag],3,1),getNode=lambda tag:([],[],3,1),
  removeElements=lambda *a:calls.append(('removeElements',a)),setNode=lambda *a:calls.append(('setNode',a)),
  addNodes=lambda *a:calls.append(('addNodes',a)),addElementsByType=lambda *a:calls.append(('addElementsByType',a)),
  rebuildNodeCache=lambda *a:calls.append(('rebuildNodeCache',a)),rebuildElementCache=lambda *a:calls.append(('rebuildElementCache',a)))
 return SimpleNamespace(model=SimpleNamespace(mesh=mesh))

class Guards(unittest.TestCase):
 def setUp(self):
  ns.update(originals);ns['OUT']=source.parent
 def test_complete_valid_saved_case_and_domain_refusals(self):
  args=[record(n) for n in ['WORKER','ARRAYS','DOMAIN','DOMAIN_PEER','OBSERVATION','SHELL']]
  coordinates=ns['candidate_rows'](*args)
  self.assertEqual(len(coordinates),40)
  self.assertEqual([struct.pack('<3d',*row) for row in coordinates],[struct.pack('<3d',*row) for row in args[1]['saved_reopen']['coordinates_mm']])
  for key,value in [('status','UNREVIEWED'),('local_domain_equivalence_proved',False)]:
   bad=copy.deepcopy(args);bad[2][key]=value
   with self.assertRaises(ValueError):ns['candidate_rows'](*bad)
  bad=copy.deepcopy(args);bad[3]['decision']='UNREVIEWED'
  with self.assertRaises(ValueError):ns['candidate_rows'](*bad)
  bad=copy.deepcopy(args);bad[2]['pair_results']['candidate'].pop()
  with self.assertRaises(ValueError):ns['candidate_rows'](*bad)
  bad=copy.deepcopy(args);bad[2]['source_candidate_arrays_sha256']='0'*64
  with self.assertRaises(ValueError):ns['candidate_rows'](*bad)
 def test_sparse_global_mapping_and_actual_classes(self):
  case=make();self.assertEqual(case['node_map'][33],1474426)
  self.assertEqual([case['node_map'][t] for t in range(34,41)],list(range(1613806,1613813)))
  self.assertEqual(case['element_slots'][:60],sorted(case['old']))
  self.assertEqual(case['element_slots'][60:],list(range(32158127,32158168)))
  self.assertEqual(len(case['replacement']),101);self.assertEqual(len(case['fresh_nodes']),7)
  self.assertEqual(sum(v==[2,1] for v in case['classes'].values()),27)
  self.assertEqual(sum(v==[3,1] for v in case['classes'].values()),6)
  self.assertEqual(case['expected_counts'],{'nodes':1097057,'TET4':3620861,'interior':225326})
  arrays=record('ARRAYS')['saved_reopen']
  self.assertEqual(list(case['replacement'].values()),[[case['node_map'][t] for t in row] for row in arrays['tetra_node_tags']])
 def test_fixed_word_class_parameter_and_max_refusals(self):
  args=[record(n) for n in ['OBSERVATION','SHELL','WORKER','ARRAYS','CONTEXT','DOMAIN','DOMAIN_PEER']]
  bad=copy.deepcopy(args);bad[1]['vertex_rows'][0]['binary64_little_endian_bytes_hex']='00'*24
  with self.assertRaises(ValueError):ns['make_case'](*bad)
  bad=copy.deepcopy(args);bad[4]['independently_derived_global_maxima']['element_all_dimensions']=3620820
  with self.assertRaises(ValueError):ns['make_case'](*bad)
  bad=copy.deepcopy(args);bad[4]['selected33_native_node_rows'][0]['dimension']=3
  with self.assertRaises(ValueError):ns['make_case'](*bad)
  bad=copy.deepcopy(args);bad[4]['selected33_native_node_rows'][0]['available_parametric_coordinates']=[0.]
  with self.assertRaises(ValueError):ns['make_case'](*bad)
 def test_raw_copy_preserves_interior_signed_zero(self):
  # Isolate copying only; this synthetic mutation is not a domain/candidate certificate.
  args=[record(n) for n in ['WORKER','ARRAYS','DOMAIN','DOMAIN_PEER','OBSERVATION','SHELL']]
  for stage in ['after','saved_reopen']:args[1][stage]['coordinates_mm'][32][0]=-0.
  ns['require_domain']=lambda *a:None
  coordinates=ns['candidate_rows'](*args)
  self.assertEqual(struct.pack('<d',coordinates[32][0]),struct.pack('<d',-0.))
  self.assertNotEqual(struct.pack('<d',coordinates[32][0]),struct.pack('<d',0.))
 def test_exact_api_order_complete_removal_and_stale_max(self):
  case=make();calls=[];gmsh=fake(case,calls);counts={k:0 for k in ns['COUNTS']}
  ns['edit_once'](gmsh,case,counts)
  self.assertEqual([x[0] for x in calls],['removeElements','setNode','addNodes','addElementsByType','rebuildNodeCache','rebuildElementCache'])
  self.assertEqual(calls[0][1],(3,1,sorted(case['old'])))
  self.assertEqual(calls[1][1],(1474426,case['proposed'][1474426],[]))
  self.assertEqual(calls[2][1][:3],(3,1,list(range(1613806,1613813))))
  self.assertEqual(calls[3][1][:3],(1,4,case['element_slots']))
  self.assertEqual(calls[-2][1],(False,));self.assertEqual(calls[-1][1],(False,))
  for rows in [{},dict(list(case['old'].items())[:-1])]:
   with self.assertRaises(ValueError):ns['edit_once'](gmsh,dict(case,old=rows),{k:0 for k in ns['COUNTS']})
  gmsh.model.mesh.getMaxNodeTag=lambda:case['nmax']+1
  with self.assertRaises(ValueError):ns['edit_once'](gmsh,case,{k:0 for k in ns['COUNTS']})
 def test_throwing_mutations_count_attempts_before_call(self):
  case=make()
  def throws(*a):raise RuntimeError('synthetic native refusal')
  for method,expected in [('removeElements',['removeElements']),('setNode',['removeElements','setNode']),('addNodes',['removeElements','setNode','addNodes'])]:
   gmsh=fake(case,[]);setattr(gmsh.model.mesh,method,throws);counts={k:0 for k in ns['COUNTS']}
   with self.assertRaises(RuntimeError):ns['edit_once'](gmsh,case,counts)
   self.assertEqual([k for k,v in counts.items() if v],expected)
   self.assertEqual(counts['rebuildNodeCache'],0);self.assertEqual(counts['write_mesh'],0)
 def test_outside_and_original_class_preservation_refusals(self):
  before={'preservation':{'outside_coordinates':'original','outside_cells':'original'},'metadata_sha256s':{'all_lower':'original'}}
  after=dict(copy.deepcopy(before),original_classification_projection_exact=True,new_nodes_on_volume1=7)
  ns['require_snapshot'](before,after)
  for section in ['preservation','metadata_sha256s']:
   bad=copy.deepcopy(after);bad[section][next(iter(bad[section]))]='different'
   with self.assertRaises(ValueError):ns['require_snapshot'](before,bad)
  for key,value in [('original_classification_projection_exact',False),('new_nodes_on_volume1',8)]:
   with self.assertRaises(ValueError):ns['require_snapshot'](before,dict(after,**{key:value}))
  body=ast.unparse(functions['metadata_snapshot'])
  self.assertIn("removed = list(case['replacement'] if after else case['old'])",body)
  self.assertIn("[APEX, *case['fresh_nodes']]",body)
  self.assertIn("len(fresh) != (7 if after else 0)",body)
 def test_valid_runtime_contract_then_wrong_runtime_and_authority(self):
  reference=record('CONTEXT_CONTRACT');ns['OUT']=ROOT/ns['OUTPUT']
  c={k:copy.deepcopy(reference[k]) for k in ['external_runtime_hashes','runtime_sha256s','runtime','native_python','numpy_init','numpy_init_sha256','expected_runtime']}
  c.update(schema='962-apex1474426-head-application/v1',native_execution_authorized=True,partial_head_replacement_authorized=True,root_and_peer_review_complete=True,selected_runtime_review_complete=True,automatic_retry=False,head_execution_authorized=False,options=ns['OPTIONS'],declared_operation_counts=ns['COUNTS'],controls=ns['CONTROLS'],output_directory=ns['OUTPUT'],input_hashes=ns['FIXED_INPUTS'],reader_sha256=SOURCE_SHA,runner_sha256='5ab38b53e4019506772cc429b46699ac0e217141c87a0a043718d8123ecb159c')
  c.update({k:False for k in ns['FORBIDDEN']})
  hashes={str((ROOT/k).resolve()):v for k,v in ns['FIXED_INPUTS'].items()}
  hashes.update({str(Path(k).resolve()):v for k,v in reference['external_runtime_hashes'].items()})
  hashes[str(Path(c['numpy_init']).resolve())]=c['numpy_init_sha256']
  hashes[str((ns['OUT']/'reader.py').resolve())]=SOURCE_SHA;hashes[str((ns['OUT']/'run_readback.py').resolve())]=c['runner_sha256']
  hashes[str(Path(sys.executable).resolve())]=c['runtime']['python_executable_sha256']
  ns['sha']=lambda path:hashes[str(Path(path).resolve())]
  ns['require_contract'](c) # Valid branch hashes are fake; no runtime or MSH body read.
  bad=copy.deepcopy(c);bad['expected_runtime']['gmsh']='UNREVIEWED'
  with self.assertRaises(ValueError):ns['require_contract'](bad)
  bad=copy.deepcopy(c);bad['head_execution_authorized']=True
  with self.assertRaises(ValueError):ns['require_contract'](bad)
  bad=copy.deepcopy(c);bad['native_execution_authorized']=False
  with self.assertRaises(ValueError):ns['require_contract'](bad)
 def test_current_partial_proof_join_and_wrong_alias_refusal(self):
  path=ROOT/ns['PROOF_SOURCE'];assert hashlib.sha256(path.read_bytes()).hexdigest()==ns['FIXED_INPUTS'][ns['PROOF_SOURCE']]
  pure=[n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ['partial_after_proof','require_after_match']]
  self.assertEqual({n.name for n in pure},{'partial_after_proof','require_after_match'})
  pn={};exec(compile(ast.Module(body=pure,type_ignores=[]),'<exact-partial-proof-AST>','exec'),pn)
  core=SimpleNamespace(**{k:v for k,v in pn.items() if callable(v)})
  args=[record(n) for n in ['ORIGINAL_WORKER','ORIGINAL_RECEIPT','FIRST','PARTIAL_CLOSED','PARTIAL_METADATA','CONTEXT']]
  proof=ns['require_original_records'](core,*args);self.assertEqual(proof,args[0]['after'])
  bad=copy.deepcopy(args);bad[0]['status']='completed_Netgen_optimizer'
  with self.assertRaises(ValueError):ns['require_original_records'](core,*bad)
  bad=copy.deepcopy(args);bad[5]['full_array_sha256s']['sorted_coordinates_sha256']='0'*64
  with self.assertRaises(ValueError):ns['require_original_records'](core,*bad)
 def test_no_forbidden_API_and_poor_whole_head_is_not_success(self):
  with self.assertRaises(ValueError):ns['require_contract']({'schema':'962-apex1474426-head-application/v1','native_execution_authorized':False})
  for node in ast.walk(tree):
   if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):self.assertNotIn(node.func.attr,['generate','optimize','createGeometry','reclassifyNodes','renumberNodes','renumberElements','removeDuplicateNodes'])
  self.assertEqual(ns['CONTROLS'],{'hard_wall_seconds':1200,'sampled_RSS_stop_bytes':8589934592,'sampled_output_stop_bytes':1073741824,'native_threads':2,'automatic_retry':False})
  self.assertIn("len(v)!=101",source.read_text());self.assertIn("np.any(local_metrics['SICN']<.1)",source.read_text())
  report={'quality':{'minimum_SICN':{'nonpositive_count':0,'minimum':.039074},'minimum_jacobian':{'nonpositive_count':0}},'volume_relative_error':0.}
  self.assertTrue(ns['valid_positive_volume'](report))
  result=next(n.value for n in functions['main'].body if isinstance(n,ast.Return))
  expression=compile(ast.Expression(body=result),'<final-status-AST>','eval')
  self.assertEqual(eval(expression,{'report':{'procedural_checks_passed':True,'actual_whole_head_SICN_gate_passed':False,'bound_inputs_unchanged':True}}),2)
  self.assertEqual(eval(expression,{'report':{'procedural_checks_passed':True,'actual_whole_head_SICN_gate_passed':True,'bound_inputs_unchanged':True}}),0)

if __name__=='__main__':unittest.main()
