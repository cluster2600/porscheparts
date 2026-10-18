"""UNRUN stdlib selected-AST negative mocks; no native, pair predicates or head bytes."""
from pathlib import Path
from types import SimpleNamespace
from fractions import Fraction
import ast,copy,hashlib,json,math,struct,unittest
SOURCE_SHA='566b3245fb85a7a84efc1e016aa59b626bde0faf5844825ae84d62cc2e4a957e'
path=Path(__file__).with_name('reader.py');text=path.read_text()
assert hashlib.sha256(path.read_bytes()).hexdigest()==SOURCE_SHA
tree=ast.parse(text);defs={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
ns={'struct':struct,'math':math,'CASE_COUNT':2,'Fraction':Fraction,
 'CONTEXT':'work/962-engineering/head-star-current126-alternative-union-context-001/readback-report.json',
 'CONTEXT_CONTRACT':'work/962-engineering/head-star-current126-alternative-union-context-001/frozen-contract.json'}
exec(compile(ast.Module(body=[defs[n] for n in ['allocate_case','validate_interfaces','edit_once','outside_reference','parameter_projection','require_snapshot','valid_positive_volume','retained_positions','parameter_record','context_admission_records']],type_ignores=[]),'<fixed15-pure-mock-selected-AST>','exec'),ns)
# CASE_COUNT=2 only in this isolated fake namespace; production contract/manifest require exactly15.

def fixture(apex=10,offset=0):
 row={'apex':apex,'NV':3,'N':5,'M':2,'K':1,'I':2,'candidate_interior_node_tags':[7,11],'old_tetrahedron_tags':[40+offset]}
 shell={'local_to_global_node_tags':[1+offset,2+offset,3+offset]}
 a={'node_tags':[1,2,3,7,11],'coordinates_mm':[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.],[-0.,.2,.3],[.4,.5,.6]],'tetra_tags':[101,109],'tetra_node_tags':[[7,1,2,3],[11,7,2,3]]}
 return row,shell,a

def fake_case():
 first=ns['allocate_case'](*fixture(),100,200);second=ns['allocate_case'](*fixture(20,10),101,201)
 return {'cases':[first,second],'apices':[10,20],'old':{40:[10,1,2,3],50:[20,11,12,13]},'nmax':100,'emax':200,
  'proposed':{**first['proposed'],**second['proposed']},'fresh_nodes':first['fresh_nodes']+second['fresh_nodes'],
  'replacement':{**first['replacement'],**second['replacement']},'apex_parameters':{10:[],20:[]}}

COUNTS={n:0 for n in ['removeElements','setNode','addNodes','addElementsByType','rebuildNodeCache','rebuildElementCache','write_mesh','generate','optimize','createGeometry','reclassifyNodes','solve']}

def fake_native(case,calls):
 mesh=SimpleNamespace(getMaxNodeTag=lambda:case['nmax'],getMaxElementTag=lambda:case['emax'],
  getElement=lambda t:(4,case['old'][t],3,1),getNode=lambda t:([0.,0.,0.],case['apex_parameters'][t],3,1))
 for name in COUNTS:
  setattr(mesh,name,lambda *args,n=name:calls.append((n,args)))
 return SimpleNamespace(model=SimpleNamespace(mesh=mesh))

class Vector:
 def __init__(self,items):self.items=list(items)
 def __iter__(self):return iter(self.items)
 def all(self):return all(self.items)
 def __invert__(self):return Vector(not x for x in self.items)
 def __getitem__(self,key):return Vector(x for x,keep in zip(self.items,key.items) if keep)
class TinyNP:
 @staticmethod
 def asarray(items,**kw):return Vector(items)
 @staticmethod
 def isin(items,tags):return Vector(t in set(tags) for t in items)
 @staticmethod
 def count_nonzero(items):return sum(items)
def array_hash(array):
 rows=list(array)
 payload=b''.join((struct.pack('<3d',*r) if len(r)==3 else struct.pack('<4Q',*r)) if isinstance(r,list) else struct.pack('<Q',r) for r in rows)
 return hashlib.sha256(payload).hexdigest()

class Guards(unittest.TestCase):
 def test_actual_noncontiguous_tag_lookup_and_fresh_offsets(self):
  row,shell,a=fixture();part=ns['allocate_case'](row,shell,a,100,200)
  self.assertEqual(part['node_map'],{1:1,2:2,3:3,7:10,11:101})
  self.assertEqual(part['element_slots'],[40,201]);self.assertEqual(part['replacement'][201],[101,10,2,3])
  self.assertEqual(struct.pack('<d',part['proposed'][10][0]),struct.pack('<d',-0.))
  other=ns['allocate_case'](*fixture(20,10),101,201)
  self.assertEqual(other['fresh_nodes'],[102]);self.assertEqual(other['element_slots'],[50,202])
  for change in ['missing','duplicate','orphan','overflow']:
   rr,ss,aa=fixture()
   if change=='missing':aa['coordinates_mm'].pop()
   if change=='duplicate':aa['node_tags'][-1]=7
   if change=='orphan':aa['tetra_node_tags'][1]=[7,1,2,3]
   with self.assertRaises(ValueError):ns['allocate_case'](rr,ss,aa,2**64-1 if change=='overflow' else 100,200)
 def test_real_manifest15_root_acceptance_and_vertex_disjoint_source_guard(self):
  root=path.resolve().parents[3];manifest=json.loads(path.with_name('admitted-manifest.json').read_text())
  accept=manifest['root_domain_acceptance'];raw=(root/accept['path']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),accept['sha256'])
  accepted=json.loads(raw);self.assertEqual(manifest['accepted_apices'],accepted['accepted_domain_case_tags']);self.assertEqual(len(manifest['cases']),15)
  self.assertIsNone(manifest['context_result']);self.assertIsNone(manifest['context_peer']);self.assertIsNone(manifest['context_root_admission'])
  self.assertIsNone(manifest['native_application']);self.assertNotIn(1485102,manifest['accepted_apices'])
  vertices=set()
  for item in manifest['cases']:
   row=item['local_case'];self.assertFalse(vertices&set(row['old_vertex_tags']));vertices.update(row['old_vertex_tags'])
   self.assertEqual(item['completed_domain'],accepted['case_reports'][str(row['apex'])])
   self.assertEqual(row['total_pairs'],row['K']*(row['K']-1)//2+row['M']*(row['M']-1)//2)
  self.assertEqual(len(vertices),335);self.assertIn('present & vertices',ast.unparse(defs['make_case']))
  self.assertEqual(manifest['aggregate_counts_from_frozen_metadata'],{'removed_TET4':580,'replacement_TET4':834,'fresh_nodes':46,'fresh_elements':254,'initial_poor_removed':16})
  self.assertEqual(sum(row['local_case']['I']-1 for row in manifest['cases']),46)
 def test_subset_interface_ownership_not_superset_removed_flag(self):
  case={'old':{40:[10,1,2,3]},'cases':[{'apex':10,'old':{40:[10,1,2,3]}}]}
  inside={'tetrahedron_tag':40,'node_tags':[10,1,2,3],'oriented_face':[1,3,2],'dimension':3,'entity_tag':1,'removed_star_owner':False}
  outside={'tetrahedron_tag':50,'node_tags':[20,1,3,2],'oriented_face':[1,2,3],'dimension':3,'entity_tag':1,'removed_star_owner':True}
  context={'selected_case_contexts':[{'apex':10,'old_cell_tags':[40],'shell_face_keys':[[1,2,3]]}],
   'all_selected_shell_face_records':[{'shell_face_key':[1,2,3],'owners':[inside,outside],'parent_exterior_TRI_rows':[]}]}
  ns['validate_interfaces'](case,context) # Deliberately opposite historical116 flags: subset U controls the decision.
  for change in ['winding','missing','wrong_old','duplicate_case']:
   c=copy.deepcopy(case);d=copy.deepcopy(context)
   if change=='winding':d['all_selected_shell_face_records'][0]['owners'][1]['oriented_face']=[1,3,2]
   if change=='missing':d['all_selected_shell_face_records'][0]['owners'].pop()
   if change=='wrong_old':d['all_selected_shell_face_records'][0]['owners'][0]['node_tags']=[10,1,3,2]
   if change=='duplicate_case':c['cases'].append(copy.deepcopy(c['cases'][0]))
   with self.assertRaises(ValueError):ns['validate_interfaces'](c,d)
 def test_complete_union_api_order_conditional_add_and_attempt_failures(self):
  case=fake_case();calls=[];c=copy.deepcopy(COUNTS);ns['edit_once'](fake_native(case,calls),case,c)
  self.assertEqual([n for n,a in calls],['removeElements','setNode','setNode','addNodes','addElementsByType','rebuildNodeCache','rebuildElementCache'])
  self.assertEqual(c['setNode'],2);self.assertEqual(c['removeElements'],1);self.assertEqual(c['write_mesh'],0)
  zero=copy.deepcopy(case);zero['fresh_nodes']=[];calls=[];ns['edit_once'](fake_native(zero,calls),zero,copy.deepcopy(COUNTS));self.assertNotIn('addNodes',[n for n,a in calls])
  def throws(*args):raise RuntimeError('synthetic mutation failure')
  for name,prefix in [('removeElements',['removeElements']),('setNode',['removeElements','setNode']),('addNodes',['removeElements','setNode','addNodes'])]:
   gmsh=fake_native(case,[]);setattr(gmsh.model.mesh,name,throws);c=copy.deepcopy(COUNTS)
   with self.assertRaises(RuntimeError):ns['edit_once'](gmsh,case,c)
   self.assertEqual([n for n,v in c.items() if v],prefix)
   self.assertEqual(c[name],1);self.assertEqual(c['write_mesh'],0)
  bad=fake_native(case,[]);bad.model.mesh.getMaxElementTag=lambda:199
  with self.assertRaises(ValueError):ns['edit_once'](bad,case,copy.deepcopy(COUNTS))
 def test_subset_outside_retains_unadmitted_apex_and_signed_zero(self):
  core=SimpleNamespace(np=TinyNP,array_sha=array_hash);case={'apices':[10],'old':{40:[]}}
  state=(Vector([[1.,2.,3.],[-0.,2.,3.],[4.,5.,6.]]),Vector([1,10,20]),Vector([40,50]),Vector([[10,1,2,3],[20,4,5,6]]))
  ref=ns['outside_reference'](core,state,case);self.assertEqual(ref['outside_nodes'],2);self.assertEqual(ref['outside_TET4'],1)
  changed=(Vector([[1.,2.,3.],[0.,2.,3.],[4.,5.,6.]]),*state[1:]);self.assertEqual(ref,ns['outside_reference'](core,changed,case))
 def test_retained_actual_parameters_full_before_and_multiple_apex_exclusion(self):
  tags=[2,7,13,17,31,100];retained=[2,13,31]
  self.assertEqual(ns['retained_positions'](tags,retained),[0,2,4])
  for badtags,badretained in [(tags,[2,13,32]),(tags,[13,2]),([2,2,13],[2]),(tags,[True])]:
   with self.assertRaises(ValueError):ns['retained_positions'](badtags,badretained)
  inventory=[{'dimension':3,'entity_tag':1,'count':4,'parameter_width':2,'node_tags_u64_sha256':'tags','coordinate_words_f64_sha256':'old','available_parameter_words_f64_sha256':'params'}]
  other=copy.deepcopy(inventory);other[0]['available_parameter_words_f64_sha256']='drift'
  self.assertNotEqual(ns['parameter_projection'](inventory),ns['parameter_projection'](other))
  body=ast.unparse(defs['metadata_snapshot'])
  for expression in ['full != expected', "case['retained_entity_node_tags']", "np.isin(owned, np.asarray(case['apices']", "case['retained_parameter_inventory']", "observed != case['retained_parameter_inventory']"]:
   self.assertIn(expression,body)
  self.assertNotIn('owned != APEX',body);self.assertIn('owned[keep]',body);self.assertIn('params[keep]',body)
  rows=[[1.,-0.],[2.,3.]]
  core=SimpleNamespace(array_sha=lambda value:hashlib.sha256(repr(value).encode()).hexdigest())
  before_param=ns['parameter_record'](core,3,1,[2,13],[[1.,2.,3.],[4.,5.,6.]],rows,2)
  changed=ns['parameter_record'](core,3,1,[2,13],[[1.,2.,3.],[4.,5.,6.]],[[1.,0.],[2.,3.]],2)
  self.assertNotEqual(before_param,changed)
  before={'preservation':{'outside':'old'},'metadata_sha256s':{'lower':'old'},'retained_original_parameter_projection':inventory,'expected_new_nodes':2}
  after={**copy.deepcopy(before),'original_classification_projection_exact':True,'new_nodes_on_volume1':2};ns['require_snapshot'](before,after)
  for field in ['preservation','metadata_sha256s','retained_original_parameter_projection','new_nodes_on_volume1']:
   bad=copy.deepcopy(after);bad[field]='drift'
   with self.assertRaises(ValueError):ns['require_snapshot'](before,bad)
 def test_one_write_full_reopen_and_strict_refusal_control(self):
  forbidden={'generate','optimize','createGeometry','reclassifyNodes','renumberNodes','renumberElements','removeDuplicateNodes'}
  for node in ast.walk(tree):
   if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):self.assertNotIn(node.func.attr,forbidden)
  main=defs['main'];writes=[n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='write']
  self.assertEqual(len(writes),2) # One JSON stream.write plus exactly one gmsh.write.
  self.assertEqual(sum(isinstance(n.func.value,ast.Name) and n.func.value.id=='gmsh' for n in writes),1)
  self.assertIn('saved != after',ast.unparse(main));self.assertIn("np.any(local_metrics['SICN'] < 0.1)",ast.unparse(main))
  self.assertIn("helpers['require_after_match'](first, proof, 126)",ast.unparse(defs['current_after_proof']))
  result=next(n.value for n in main.body if isinstance(n,ast.Return));expression=compile(ast.Expression(body=result),'<unchanged-final-status>','eval')
  self.assertEqual(eval(expression,{'report':{'procedural_checks_passed':True,'actual_whole_head_SICN_gate_passed':False,'bound_inputs_unchanged':True}}),2)
  self.assertIn("'setNode': 15",ast.unparse(tree));self.assertIn("'native_threads':2",text)

 def test_pending_context_admission_is_fail_closed_before_native_imports(self):
  held=json.loads(path.with_name('held-contract.json').read_text())
  self.assertIsNone(held['context_admission']);self.assertFalse(held['fresh_context_result_and_peer_root_admitted'])
  with self.assertRaises(ValueError):ns['context_admission_records'](held)
  paths={'report':ns['CONTEXT'],'contract':ns['CONTEXT_CONTRACT'],
   'receipt':'work/962-engineering/head-star-current126-alternative-union-context-001/execution-receipt.json',
   'root_closed':'work/962-engineering/current126-alternative-union-context-root-execution-001/closed-result.json',
   'peer':'work/962-engineering/current126-alternative-union-context-result-peer-001/review.json',
   'bindings':'work/962-engineering/current126-alternative-union-context-result-peer-001/bindings.json',
   'root_acceptance':'work/962-engineering/current126-alternative-union-context-root-execution-001/result-peer-acceptance.json'}
  c={'fresh_context_result_and_peer_root_admitted':True,'context_admission':{k:{'path':v,'sha256':'a'*64,'bytes':1} for k,v in paths.items()},'input_hashes':{v:'a'*64 for v in paths.values()}}
  self.assertEqual(len(ns['context_admission_records'](c)),7)
  for change in ['missing_root','missing_pin','bad_bytes','wrong_report','false_admission']:
   bad=copy.deepcopy(c)
   if change=='missing_root':bad['context_admission'].pop('root_acceptance')
   if change=='missing_pin':bad['input_hashes'].pop(paths['report'])
   if change=='bad_bytes':bad['context_admission']['report']['bytes']=True
   if change=='wrong_report':bad['context_admission']['report']['path']='old116/report.json'
   if change=='false_admission':bad['fresh_context_result_and_peer_root_admitted']=False
   with self.assertRaises(ValueError):ns['context_admission_records'](bad)
  main=defs['main'];first_native=min(n.lineno for n in ast.walk(main) if isinstance(n,ast.Import) and any(x.name in ['numpy','gmsh'] for x in n.names))
  gate=next(n.lineno for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='require_contract')
  self.assertLess(gate,first_native);self.assertIn('context_admission_records(c)',ast.unparse(defs['require_contract']))
  body=ast.unparse(defs['make_case'])
  for name in ['case_record','census_join','accepted_native_records','saved_candidate']:
   self.assertIn(name,body)
  self.assertNotIn('context_join',body)

 def test_real_admitted_context_runtime_schema_and_separate_NumPy_drift_refusal(self):
  root=path.resolve().parents[3];held=json.loads(path.with_name('held-contract.json').read_text())
  original_path='work/962-engineering/head-star-current126-alternative-union-context-001/frozen-contract.json'
  original_bytes=(root/original_path).read_bytes()
  self.assertEqual(hashlib.sha256(original_bytes).hexdigest(),'0ae7184a29a62645e1c88cb905381cb759e90f1ed897305dc29a276c8029c5c3')
  original=json.loads(original_bytes);self.assertNotIn('numpy_init_sha256',original)
  binding_path='work/962-engineering/head-star-current126-alternative-union-context-execution-prep-001/runtime-parent-preflight.json'
  binding_bytes=(root/binding_path).read_bytes()
  self.assertEqual(hashlib.sha256(binding_bytes).hexdigest(),'b6d197768a0cd72cee0b84b2ce3654428a0194b48f9919bbafaedc3c2203b16f')
  numpy_sha='c09e25b58f6b2f8e2cb3c158168f902d447f8171e5ea6513c0aca41ecbda7c2b'
  fields=['external_runtime_hashes','runtime_sha256s','runtime','native_python','numpy_init']
  contract_body=defs['require_contract'].body
  start=next(i for i,n in enumerate(contract_body) if isinstance(n,ast.For) and isinstance(n.iter,ast.List) and all(isinstance(x,ast.Constant) for x in n.iter.elts) and [x.value for x in n.iter.elts]==fields)
  fragment=contract_body[start:start+4]
  self.assertEqual([type(x).__name__ for x in fragment],['For','Assign','If','If'])
  program=compile(ast.Module(body=fragment,type_ignores=[]),'<exact-admitted-context-runtime-fragment>','exec')
  # This fake seven-record admission permits the real metadata comparison only. No native/runtime body is accessed.
  paths={'report':ns['CONTEXT'],'contract':ns['CONTEXT_CONTRACT'],
   'receipt':'work/962-engineering/head-star-current126-alternative-union-context-001/execution-receipt.json',
   'root_closed':'work/962-engineering/current126-alternative-union-context-root-execution-001/closed-result.json',
   'peer':'work/962-engineering/current126-alternative-union-context-result-peer-001/review.json',
   'bindings':'work/962-engineering/current126-alternative-union-context-result-peer-001/bindings.json',
   'root_acceptance':'work/962-engineering/current126-alternative-union-context-root-execution-001/result-peer-acceptance.json'}
  c=copy.deepcopy(held);c['fresh_context_result_and_peer_root_admitted']=True
  c['context_admission']={k:{'path':v,'sha256':'a'*64,'bytes':1} for k,v in paths.items()}
  c['input_hashes'].update({v:'a'*64 for v in paths.values()})
  self.assertEqual(len(ns['context_admission_records'](c)),7)
  scope={'c':c,'original':original,'ROOT':root,'NUMPY_BINDING':binding_path,'NUMPY_SHA':numpy_sha,
   'FIXED_INPUTS':{binding_path:'b6d197768a0cd72cee0b84b2ce3654428a0194b48f9919bbafaedc3c2203b16f'},'Path':Path,'json':json,'sha':lambda unused:numpy_sha}
  exec(program,scope)
  bad=copy.deepcopy(c);bad['numpy_init_sha256']='0'*64
  with self.assertRaises(ValueError):exec(program,{**scope,'c':bad})
  bad_binding=json.loads(binding_bytes);bad_binding['native3_NumPy_selected_outer5'][c['numpy_init']]['sha256']='0'*64
  with self.assertRaises(ValueError):exec(program,{**scope,'json':SimpleNamespace(loads=lambda unused:bad_binding)})
  with self.assertRaises(ValueError):exec(program,{**scope,'sha':lambda unused:'0'*64})

if __name__=='__main__':unittest.main()
