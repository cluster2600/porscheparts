"""Prepared stdlib/AST guards only; no prepared/scientific/native module import."""
import ast,copy,hashlib,json,math,struct,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
PREP=Path(__file__).resolve().parent;ROOT=PREP.parents[2]
SOURCE=PREP/'mesh_apply_sicn_proposal.py';SOURCE_SHA='8cfb42772693ff3dcd64563692660b4702038af70727f6536c6cd3b058df3738'
if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Exact reviewed held current110 pass62 apply source required')
TEXT=SOURCE.read_text();TREE=ast.parse(TEXT)
FN={n.name:n for n in TREE.body if isinstance(n,ast.FunctionDef)}
def extracted(names,ns):
 exec(compile(ast.Module(body=[FN[n] for n in names],type_ignores=[]),str(SOURCE),'exec'),ns)
 return ns
class Mask(list):
 def __invert__(self):return Mask(not v for v in self)
class Rows:
 def __init__(self,rows):self.rows=[list(r) for r in rows]
 def __getitem__(self,mask):return Rows(r for r,keep in zip(self.rows,mask) if keep)
 def reshape(self,*args):return self
 def tobytes(self):return b''.join(struct.pack('<d',v) for row in self.rows for v in row)
class TinyNP:
 @staticmethod
 def isin(rows,values):
  return [[v in values for v in r] for r in rows] if rows and isinstance(rows[0],list) else Mask(v in values for v in rows)
 @staticmethod
 def any(rows,axis=None):return [any(r) for r in rows] if axis==1 else any(rows)
 @staticmethod
 def flatnonzero(mask):return [i for i,v in enumerate(mask) if v]
 array_equal=staticmethod(lambda a,b:a==b)
 count_nonzero=staticmethod(lambda mask:sum(mask))
 asarray=staticmethod(lambda rows,dtype=None:Rows(rows))
 ascontiguousarray=staticmethod(lambda rows:rows)
class ApplyGuards(unittest.TestCase):
 def rows(self,tags):
   return [dict(node_tag=t,coordinates_mm=[float(t),0.,-0.],binary64_hex=[float(t).hex(),0.0.hex(),(-0.0).hex()]) for t in tags]
 def test_exact_order_coordinate_hex_finite_and_bool_refusal(self):
   ns=extracted(['coordinate_rows'],dict(math=math));tags=[10,20];rows=self.rows(tags)
   self.assertEqual(ns['coordinate_rows'](rows,tags),[[10.,0.,-0.],[20.,0.,-0.]])
   bad=[rows[::-1],rows[:1],[None,*rows[1:]]]
   for key,value in [('node_tag',True),('node_tag',11),('coordinates_mm',[10.,float('nan'),0.]),('coordinates_mm',[10.,True,0.]),('binary64_hex',[10.0.hex(),0.0.hex(),0.0.hex()])]:
    changed=copy.deepcopy(rows);changed[0][key]=value;bad.append(changed)
   for changed in bad:
    with self.subTest(value=changed),self.assertRaises(ValueError):ns['coordinate_rows'](changed,tags)
   with self.assertRaises(ValueError):ns['coordinate_rows'](rows,[20,10])
 def test_all_unselected_coordinate_bits_including_signed_zero_and_exact_selected_bits(self):
   ns=extracted(['require_selected_coordinate_identity'],{})
   core=SimpleNamespace(np=TinyNP,array_sha=lambda a:hashlib.sha256(a.tobytes()).hexdigest())
   tags=list(range(1,69));movable=tags[2:];coords=[[float(t),0.,0.] for t in movable]
   before=(Rows([[0.,0.,0.],[1.,0.,0.],*coords]),tags,None,None)
   after=(Rows([[0.,0.,0.],[1.,0.,0.],*coords]),tags,None,None)
   self.assertEqual(ns['require_selected_coordinate_identity'](core,before,after,movable,coords)['unselected_nodes'],2)
   for i,value in [(0,[-0.,0.,0.]),(0,[2**-52,0.,0.]),(2,[99.,0.,0.])]:
    changed=Rows(after[0].rows);changed.rows[i]=value
    with self.assertRaises(ValueError):ns['require_selected_coordinate_identity'](core,before,(changed,tags,None,None),movable,coords)
 def test_actual_full_incidence_expression_includes_initially_good_and_shared_rows(self):
   node=next(n for n in ast.walk(FN['selected_census']) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ix' for t in n.targets))
   expression=ast.Expression(body=node.value);rows=[[1,2,3,4],[1,2,9,10],[2,5,6,7],[8,9,10,11]]
   result=eval(compile(expression,str(SOURCE),'eval'),dict(np=TinyNP,en=rows,movable=[1,2]))
   self.assertEqual(result,[0,1,2]);self.assertNotIn('SICN',ast.unparse(node.value));self.assertNotIn('poor',ast.unparse(node.value))
 def apply_context(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);binding=Path(temp.name)/'actual.json';binding.write_text('{}\n')
  tags=list(range(900000,900066));coords=[[float(t),0.,-0.] for t in tags];calls=[]
  gmsh=SimpleNamespace(model=SimpleNamespace(mesh=SimpleNamespace(setNode=lambda *args:calls.append(('setNode',args)),rebuildElementCache=lambda flag:calls.append(('cache',flag)))))
  ns=extracted(['apply_and_refresh'],dict(hashlib=hashlib,APPLICATION_BINDING=binding,SELECTED_TAGS=tags,SELECTION_SHA256='s'*64,CENSUS_SHA256='c'*64,bound_proposal=lambda:{},selected_census=lambda *args:([],{}),accepted_coordinate_rows=lambda *args:(coords,{})))
  return calls,gmsh,ns,tags,coords
 def test_one66_setter_pass_and_one_cache(self):
  calls,gmsh,ns,tags,coords=self.apply_context();report={}
  self.assertEqual(ns['apply_and_refresh'](None,gmsh,None,report,lambda:None),(tags,coords))
  self.assertEqual(report['setNode_call_count'],66);self.assertEqual(report['element_cache_refresh_count'],1)
  self.assertEqual([r[1][0] for r in calls[:-1]],tags);self.assertEqual(calls[-1],('cache',False))
  self.assertEqual(len(calls),67)
 def test_throwing_setter_retains_attempt_and_no_cache(self):
  calls,gmsh,ns,tags,coords=self.apply_context();report={}
  def throwing(*args):calls.append(('throw',args));raise RuntimeError('declared setter failure')
  gmsh.model.mesh.setNode=throwing
  with self.assertRaisesRegex(RuntimeError,'declared setter failure'):ns['apply_and_refresh'](None,gmsh,None,report,lambda:None)
  self.assertEqual(report['setNode_call_count'],1);self.assertEqual(len(calls),1)
  self.assertNotIn('element_cache_refresh_count',report);self.assertNotIn('proposal_applied',report)
 def test_exact_reverse_math_sections_owned_controller_and_no_optimizer(self):
  delta=json.loads((PREP/'source-delta.json').read_text());back=TEXT
  for row in reversed(delta['replacements']):
   self.assertEqual(back.count(row['new']),1);back=back.replace(row['new'],row['old'],1)
  self.assertEqual(hashlib.sha256(back.encode()).hexdigest(),delta['donor']['sha256'])
  old={n.name:n for n in ast.parse(back).body if isinstance(n,ast.FunctionDef)}
  for name in delta['unchanged_function_text_and_ASTs']:
   self.assertEqual(ast.dump(FN[name],include_attributes=False),ast.dump(old[name],include_attributes=False))
  self.assertIn('main',delta['unchanged_function_text_and_ASTs'])
  calls=[n for n in ast.walk(TREE) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
  self.assertFalse(any(n.func.attr in ['optimize','minimize','generate','addNodes','addElementsByType','removeElements','createGeometry'] for n in calls))
  self.assertEqual(sum(n.func.attr=='setNode' for n in calls),1)
  self.assertIn('quality["minimum_SICN"]["minimum"]<.1',TEXT);self.assertIn('["volume_relative_error"]>1e-6',TEXT)
 def test_authority_before_opaque_inputs_and_exact_classifier_numpy_binding(self):
  first=FN['require_inputs'].body[0]
  self.assertIsInstance(first,ast.Expr);self.assertEqual(ast.unparse(first.value),'bound_proposal()')
  self.assertIn('globals()["np"]=core.np',ast.get_source_segment(TEXT,FN['configure_core']))
  self.assertIn('saved_native_enumeration_index',TEXT);self.assertIn('fresh_sorted_tagged_array_index',TEXT)
 def test_fixed62_descriptors_exclude_rejected11_and_exact66(self):
  selection=json.loads((PREP/'selected-proposals.json').read_text())
  self.assertEqual(len(selection['diagnostics']),62);self.assertEqual(len(selection['selected_node_tags']),66)
  self.assertEqual(len(set(selection['selected_node_tags'])),66)
  ids=[r['component_ID'] for r in selection['diagnostics']]
  self.assertEqual(ids,selection['component_IDs'])
  self.assertFalse(set(ids)&set(selection['rejected_component_IDs']))
  self.assertEqual(len(selection['known_unmodified_rejected_positive_poor_tetrahedron_tags']),24)
  self.assertEqual(selection['original_worst_rejected_component_ID'],30)
 def test_missing_or_held_actual_refuses_before_runtime_or_helper_read(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);binding=Path(temp.name)/'actual.json'
  ns=extracted(['bound_proposal'],dict(json=json,APPLICATION_BINDING=binding))
  with self.assertRaises(FileNotFoundError):ns['bound_proposal']()
  for flags in [{},{'native_execution_authorized':False},{'native_execution_authorized':True,'root_and_peer_source_review_complete':False}]:
   binding.write_text(json.dumps({'schema':'962-current110-pass62-application-actual/v1',**flags}))
   with self.assertRaises(ValueError):ns['bound_proposal']()
if __name__=='__main__':unittest.main()
