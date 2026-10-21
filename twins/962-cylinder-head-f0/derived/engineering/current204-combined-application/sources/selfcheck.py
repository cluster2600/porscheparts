"""UNRUN stdlib selected-AST negative mocks; no native, pair predicates or head bytes."""
from pathlib import Path
from types import SimpleNamespace
from fractions import Fraction
import ast,copy,hashlib,json,math,struct,unittest
SOURCE_SHA='c66da821a1d98794ed78f403067e02c349c11a59d6c22de72e587b05e5fc82f5'
path=Path(__file__).with_name('reader.py');text=path.read_text()
assert hashlib.sha256(path.read_bytes()).hexdigest()==SOURCE_SHA
tree=ast.parse(text);defs={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
ns={'struct':struct,'math':math,'CASE_COUNT':2,'Fraction':Fraction}
exec(compile(ast.Module(body=[defs[n] for n in ['allocate_case','validate_interfaces','edit_once','outside_reference','parameter_projection','require_snapshot','valid_positive_volume']],type_ignores=[]),'<fixed47-pure-mock-selected-AST>','exec'),ns)
# CASE_COUNT=2 only in this isolated fake namespace; production contract/manifest require exactly47.

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
 def test_real_manifest47_root_acceptance_and_vertex_disjoint_source_guard(self):
  root=path.resolve().parents[3];manifest=json.loads(path.with_name('admitted-manifest.json').read_text())
  accept=manifest['root_domain_acceptance'];raw=(root/accept['path']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),accept['sha256'])
  accepted=json.loads(raw);self.assertEqual(manifest['accepted_apices'],accepted['accepted_apices']);self.assertEqual(len(manifest['cases']),47)
  vertices=set()
  for item in manifest['cases']:
   row=item['local_case'];self.assertFalse(vertices&set(row['old_vertex_tags']));vertices.update(row['old_vertex_tags'])
  self.assertIn('present & vertices',ast.unparse(defs['make_case']))
  self.assertNotIn('1393275',str(manifest['accepted_apices']))
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
  changed=(Vector([[1.,2.,3.],[-0.,2.,3.],[7.,5.,6.]]),*state[1:]);self.assertNotEqual(ref,ns['outside_reference'](core,changed,case))
  with self.assertRaises(ValueError):ns['outside_reference'](core,state,{'apices':[999],'old':{40:[]}})
  # Metadata before/after comparison must retain the subset reference, not116 future_preservation_references.
  self.assertIn("case['outside_reference'][key]",ast.unparse(defs['metadata_snapshot']))
 def test_original_parameter_projection_and_preservation_refusals(self):
  inventory=[{'dimension':3,'entity_tag':1,'count':4,'parameter_width':0,'node_tags_u64_sha256':'tags','coordinate_words_f64_sha256':'old','available_parameter_words_f64_sha256':'params'}]
  other=copy.deepcopy(inventory);other[0]['coordinate_words_f64_sha256']='legitimately moved apex'
  self.assertEqual(ns['parameter_projection'](inventory),ns['parameter_projection'](other))
  other[0]['available_parameter_words_f64_sha256']='drift';self.assertNotEqual(ns['parameter_projection'](inventory),ns['parameter_projection'](other))
  body=ast.unparse(defs['metadata_snapshot']);self.assertIn('owned[keep]',body);self.assertIn('params[keep]',body);self.assertIn("case['original_entity_node_tags']",body)
  before={'preservation':{'outside':'old'},'metadata_sha256s':{'lower':'old'},'original_parameter_projection':inventory,'expected_new_nodes':2}
  after={**copy.deepcopy(before),'original_classification_projection_exact':True,'new_nodes_on_volume1':2};ns['require_snapshot'](before,after)
  for field in ['preservation','metadata_sha256s','original_parameter_projection','new_nodes_on_volume1']:
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
  self.assertIn("core.require_after_match(first, proof, 204)",ast.unparse(defs['require_original_records']))
  result=next(n.value for n in main.body if isinstance(n,ast.Return));expression=compile(ast.Expression(body=result),'<unchanged-final-status>','eval')
  self.assertEqual(eval(expression,{'report':{'procedural_checks_passed':True,'actual_whole_head_SICN_gate_passed':False,'bound_inputs_unchanged':True}}),2)
  self.assertIn("'setNode': 47",ast.unparse(tree));self.assertIn("'native_threads':2",text)

if __name__=='__main__':unittest.main()
