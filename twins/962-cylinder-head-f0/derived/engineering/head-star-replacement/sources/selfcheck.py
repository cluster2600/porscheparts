"""UNRUN stdlib AST/mocked tag and preservation guards; no native or geometry query."""
from pathlib import Path
from types import SimpleNamespace
import ast,copy,hashlib,json,struct,unittest
SOURCE_SHA='05ed505cf1009b7554dc0134945ef1e9f3ec9e8d729d079ede60c87cfb550ce1'
source=Path(__file__).with_name('reader.py')
assert hashlib.sha256(source.read_bytes()).hexdigest()==SOURCE_SHA
tree=ast.parse(source.read_text());functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
constants={'APEX','NMAX','EMAX','FREE','COUNTS','OPTIONS','CONTROLS','FORBIDDEN','OUTPUT'}
assignments=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets)]
ns={'struct':struct,'ROOT':source.resolve().parents[3],'OUT':source.parent}
selected=assignments+[functions[n] for n in ['make_case','edit_once','require_snapshot','valid_positive_volume','require_contract']]
exec(compile(ast.fix_missing_locations(ast.Module(body=selected,type_ignores=[])),'<selected-head-index-and-mock-guards>','exec'),ns)
coords=[[float(i),0.,0.] for i in range(1,17)]+[[.2,.3,.4],[.3,.4,.5],[.4,.5,.6]]
ns['candidate_rows']=lambda candidate,arrays:(copy.deepcopy(coords),[28,29])
mapping=list(range(101,110))+list(range(900101,900108))
old=[{'tetrahedron_tag':10000001+i,'node_tags':[1435493,mapping[i%16],mapping[(i+1)%16],mapping[(i+2)%16]]} for i in range(28)]
points=[{'node_tag':t,'coordinates_mm':coords[i]} for i,t in enumerate(mapping)]
points.append({'node_tag':1435493,'coordinates_mm':[.5,.5,.5]})
observation={'apex':1435493,'native_ordered_cell_rows':old,'selected_node_rows':points}
shell={'local_to_global_node_tags':mapping,'vertex_rows':[{'local_node_tag':i+1,'source_global_node_tag':t,'binary64_little_endian_bytes_hex':struct.pack('<3d',*coords[i]).hex()} for i,t in enumerate(mapping)]}
context={'status':'complete_original_head_star_context_census','complete_context_census':True,
 'complete_old_apex_incident_rows':old,'independently_derived_global_maxima':{'node':1613803,'element_all_dimensions':32158115},
 'selected17_native_node_rows':[{'node_tag':t,'dimension':2 if i<9 else 3,'entity_tag':1} for i,t in enumerate(mapping)]+[{'node_tag':1435493,'dimension':3,'entity_tag':1}]}
arrays={'saved_reopen':{'tetra_node_tags':[[27,1,2,3] for _ in range(39)]}}

def make():return ns['make_case'](copy.deepcopy(observation),copy.deepcopy(shell),{},copy.deepcopy(arrays),copy.deepcopy(context))

def fake(case,calls):
 mesh=SimpleNamespace(getMaxNodeTag=lambda:case['nmax'],getMaxElementTag=lambda:case['emax'],
  getElement=lambda t:(4,case['old'][t],3,1),getNode=lambda t:([],[],3,1),
  removeElements=lambda *a:calls.append(('removeElements',a)),setNode=lambda *a:calls.append(('setNode',a)),
  addNodes=lambda *a:calls.append(('addNodes',a)),addElementsByType=lambda *a:calls.append(('addElementsByType',a)),
  rebuildNodeCache=lambda *a:calls.append(('rebuildNodeCache',a)),rebuildElementCache=lambda *a:calls.append(('rebuildElementCache',a)))
 return SimpleNamespace(model=SimpleNamespace(mesh=mesh))

class Guards(unittest.TestCase):
 def test_complete_sparse_mapping_and_actual_classes(self):
  case=make()
  self.assertEqual(case['node_map'][27],1435493)
  self.assertEqual([case['node_map'][t] for t in [28,29]],[1613804,1613805])
  self.assertEqual(case['element_slots'][:28],sorted(case['old']))
  self.assertEqual(case['element_slots'][28:],list(range(32158116,32158127)))
  self.assertEqual(len(case['replacement']),39)
  self.assertEqual(sum(c==[2,1] for c in case['classes'].values()),9)
  self.assertEqual(sum(c==[3,1] for c in case['classes'].values()),8)
  bad=copy.deepcopy(context);bad['selected17_native_node_rows'][9]['dimension']=2
  with self.assertRaises(ValueError):ns['make_case'](observation,shell,{},arrays,bad)
 def test_signed_zero_shell_word_and_wrong_max_refusal(self):
  bad=copy.deepcopy(shell);bad['vertex_rows'][0]['binary64_little_endian_bytes_hex']=struct.pack('<3d',coords[0][0],-0.,0.).hex()
  with self.assertRaises(ValueError):ns['make_case'](observation,bad,{},arrays,context)
  bad=copy.deepcopy(context);bad['independently_derived_global_maxima']['element_all_dimensions']=3620809
  with self.assertRaises(ValueError):ns['make_case'](observation,shell,{},arrays,bad)
 def test_exact_api_order_and_nonempty_removal(self):
  case=make();calls=[];gmsh=fake(case,calls);counts={k:0 for k in ns['COUNTS']}
  ns['edit_once'](gmsh,case,counts)
  self.assertEqual([x[0] for x in calls],['removeElements','setNode','addNodes','addElementsByType','rebuildNodeCache','rebuildElementCache'])
  self.assertEqual(calls[0][1][:2],(3,1));self.assertEqual(len(calls[0][1][2]),28)
  self.assertEqual(calls[2][1][:2],(3,1));self.assertEqual(calls[2][1][2],[1613804,1613805])
  self.assertEqual(calls[3][1][:2],(1,4));self.assertEqual(len(calls[3][1][2]),39)
  self.assertEqual(calls[-2][1],(False,));self.assertEqual(calls[-1][1],(False,))
  for oldrows in [{},dict(list(case['old'].items())[:-1])]:
   with self.assertRaises(ValueError):ns['edit_once'](gmsh,dict(case,old=oldrows),{k:0 for k in ns['COUNTS']})
 def test_throwing_api_attempts_are_counted_before_call(self):
  case=make();gmsh=fake(case,[]);counts={k:0 for k in ns['COUNTS']}
  def throws(*_):raise RuntimeError('synthetic native refusal')
  gmsh.model.mesh.removeElements=throws
  with self.assertRaises(RuntimeError):ns['edit_once'](gmsh,case,counts)
  self.assertEqual(counts['removeElements'],1);self.assertEqual(counts['setNode'],0)
  gmsh=fake(case,[]);counts={k:0 for k in ns['COUNTS']};gmsh.model.mesh.setNode=throws
  with self.assertRaises(RuntimeError):ns['edit_once'](gmsh,case,counts)
  self.assertEqual(counts['removeElements'],1);self.assertEqual(counts['setNode'],1);self.assertEqual(counts['addNodes'],0)
 def test_preservation_drift_and_all_old_classes_refuse(self):
  before={'preservation':{'outside_coordinates':'original','outside_cells':'original'},'metadata_sha256s':{'all_lower':'original'}}
  after=dict(copy.deepcopy(before),original_classification_projection_exact=True,new_nodes_on_volume1=2)
  ns['require_snapshot'](before,after)
  for section in ['preservation','metadata_sha256s']:
   bad=copy.deepcopy(after);bad[section][next(iter(bad[section]))]='different'
   with self.assertRaises(ValueError):ns['require_snapshot'](before,bad)
  for key,value in [('original_classification_projection_exact',False),('new_nodes_on_volume1',1)]:
   bad=dict(after);bad[key]=value
   with self.assertRaises(ValueError):ns['require_snapshot'](before,bad)
 def test_held_authority_and_no_mesher_or_threshold_change(self):
  with self.assertRaises(ValueError):ns['require_contract']({'schema':'962-held-head-star-replacement/v1','native_execution_authorized':False})
  report={'quality':{'minimum_SICN':{'nonpositive_count':0,'minimum':.039074},'minimum_jacobian':{'nonpositive_count':0}},'volume_relative_error':0.}
  self.assertTrue(ns['valid_positive_volume'](report)) # Baseline positivity is separate from the strict final0.1 gate.
  for node in ast.walk(tree):
   if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
    self.assertNotIn(node.func.attr,['generate','optimize','createGeometry','reclassifyNodes','renumberNodes','renumberElements','removeDuplicateNodes'])
  self.assertEqual(ns['CONTROLS'],{'hard_wall_seconds':1200,'sampled_RSS_stop_bytes':8589934592,'sampled_output_stop_bytes':1073741824,'native_threads':2,'automatic_retry':False})
  self.assertIn("np.any(local_metrics['SICN']<.1)",source.read_text())
  self.assertIn("after['quality']['minimum_SICN']['minimum']>=.1",source.read_text())

if __name__=='__main__':unittest.main()
