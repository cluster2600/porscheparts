"""Prepared stdlib fixed-family adapters/refusals; no pair query, native or scientific import."""
import ast,copy,hashlib,importlib.util,json,struct
from pathlib import Path
from unittest import TestCase,main,mock
SOURCE=Path(__file__).with_name('certify_domain.py')
SOURCE_SHA='7060580b7aa2743dec511bb9fc5e8cfb40ef86ea3332b068c5de9c845422efc8'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
spec=importlib.util.spec_from_file_location('held_finite_domain_adapters',SOURCE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module) # definitions only; never main/pair query
PREP=SOURCE.parent

class Guards(TestCase):
 def test_fixed47_complete_budgets_current_bindings_and_held_false(self):
  manifest=json.loads((PREP/'case-manifest.json').read_text())
  accepted=json.loads((module.ROOT/module.ACCEPT).read_text())
  self.assertEqual(manifest['accepted_apices'],accepted['local_quality_storage_pass_apices'])
  self.assertEqual(len(manifest['accepted_apices']),47)
  self.assertEqual(sum(r['total_pairs'] for r in manifest['cases_in_accepted_order']),147917)
  self.assertEqual(sum(r['plane_triples'] for r in manifest['cases_in_accepted_order']),8283352)
  for row in manifest['cases_in_accepted_order']:
   self.assertEqual(module.select_case(manifest,row['apex']),row)
   for r in row['records'].values():self.assertEqual(module.sha(module.ROOT/r['path']),r['sha256'])
   held=json.loads((PREP/'held-cases'/f"apex-{row['apex']}.json").read_text())
   self.assertFalse(held['diagnostic_execution_authorized'] or held['native_execution_authorized'] or held['root_and_peer_review_complete'])
   self.assertIsNone(held['actual_contract']);self.assertIsNone(held['domain_output'])
   self.assertFalse((module.ROOT/row['output_directory']).exists())
 def test_unselected_count_storage_and_complete_budget_refusals(self):
  original=json.loads((PREP/'case-manifest.json').read_text());apex=original['accepted_apices'][0]
  with self.assertRaises(ValueError):module.select_case(original,1393275)
  with self.assertRaises(ValueError):module.select_case(original,True)
  for key,value in [('NV',3),('N',0),('I',0),('M',1),('candidate_interior_node_tags',[1]),('total_pairs',0),('plane_triples',0),('original_internal_pairs',0)]:
   with self.subTest(field=key):
    m=copy.deepcopy(original);m['cases_in_accepted_order'][0][key]=value
    with self.assertRaises(ValueError):module.select_case(m,apex)
 def old_fixture(self):
  vertices=[[0.,0.,0.],[2.,0.,0.],[0.,2.,0.],[0.,0.,2.]];globals_=[101,102,103,104];apex=200;center=[.5,.5,.5]
  faces=[[1,3,2],[1,2,4],[2,3,4],[3,1,4]]
  cells=[[200,102,103,104],[101,200,103,104],[101,102,200,104],[101,102,103,200]]
  tags=[10,11,12,13];classes={'boundary_global_node_tags':[101,102],'other_interior_global_node_tags':[103,104]}
  observed=[dict(node_tag=t,coordinates_mm=p,binary64_hex=[x.hex() for x in p]) for t,p in zip(globals_+[apex],vertices+[center])]
  obs=dict(apex=apex,native_ordered_cell_rows=[dict(tetrahedron_tag=t,node_tags=c) for t,c in zip(tags,cells)],selected_node_rows=observed,original_source_classifications=classes)
  shell=dict(local_to_global_node_tags=globals_,global_to_local_node_tags={str(t):i+1 for i,t in enumerate(globals_)},
   vertex_rows=[dict(local_node_tag=i+1,source_global_node_tag=t,binary64_little_endian_bytes_hex=struct.pack('<3d',*p).hex()) for i,(t,p) in enumerate(zip(globals_,vertices))],
   oriented_triangle_rows=[dict(local_node_tags=f) for f in faces],original_source_classifications=dict(classes,boundary_local_node_tags=[1,2],other_interior_local_node_tags=[3,4]))
  case=dict(apex=apex,NV=4,NF=4,K=4,NB=2,old_tetrahedron_tags=tags,old_vertex_tags=globals_+[apex],source_record_sha256='a'*64)
  context=dict(selected_case_contexts=[dict(apex=apex,case_record_sha256='a'*64,old_cell_tags=tags,shell_node_tags=globals_,shell_nodes=4,shell_faces=4,old_tetrahedra=4,original_boundary_shell_nodes=2)],
   complete_old_selected_apex_incident_rows=copy.deepcopy(obs['native_ordered_cell_rows']),
   selected_original_native_node_rows=[dict(**r,dimension=2 if r['node_tag'] in [101,102] else 3) for r in observed],all_selected_shell_face_records=[])
  for f,owner in zip(faces,[13,12,10,11]):
   g=[globals_[t-1] for t in f];context['all_selected_shell_face_records'].append(dict(shell_face_key=sorted(g),oriented_shell_face=g,owners=[dict(tetrahedron_tag=owner,removed_star_owner=True)]))
  return case,obs,shell,context
 def test_original_current_context_raw_class_owner_and_incidence_refusals(self):
  case,obs,shell,context=self.old_fixture()
  # Real saved schema: observation has two global lists; shell also has two local lists.
  self.assertEqual(set(obs['original_source_classifications']),{'boundary_global_node_tags','other_interior_global_node_tags'})
  self.assertEqual(set(shell['original_source_classifications']),set(obs['original_source_classifications'])|{'boundary_local_node_tags','other_interior_local_node_tags'})
  self.assertNotEqual(obs['original_source_classifications'],shell['original_source_classifications'])
  with mock.patch.object(module,'CASE',case),mock.patch.object(module,'CONTEXT_DATA',context):
   module.context_join(obs,shell);points,cells,mapping=module.original(obs,shell)
   self.assertEqual(len(points),5);self.assertEqual(len(cells),4);self.assertEqual(mapping[200],5)
  for mode in ['missing_owner','missing_incident','changed_class','signed_zero','wrong_oldtag','changed_global_class','changed_local_class','changed_inverse','extra_class_field']:
   with self.subTest(mode=mode):
    c,o,s,ctx=self.old_fixture()
    if mode=='missing_owner':ctx['all_selected_shell_face_records'][0]['owners']=[]
    if mode=='missing_incident':ctx['complete_old_selected_apex_incident_rows'].pop()
    if mode=='changed_class':ctx['selected_original_native_node_rows'][0]['dimension']=3
    if mode=='signed_zero':ctx['selected_original_native_node_rows'][0]['coordinates_mm']=[-0.,0.,0.]
    if mode=='wrong_oldtag':c['old_tetrahedron_tags']=[9,10,11,12]
    if mode=='changed_global_class':s['original_source_classifications']['boundary_global_node_tags']=[101,103]
    if mode=='changed_local_class':s['original_source_classifications']['boundary_local_node_tags']=[1,3]
    if mode=='changed_inverse':s['global_to_local_node_tags']['101']=2
    if mode=='extra_class_field':s['original_source_classifications']['unexpected']=[1]
    with mock.patch.object(module,'CASE',c),mock.patch.object(module,'CONTEXT_DATA',ctx):
     with self.assertRaises(ValueError):module.context_join(o,s)
 def candidate_fixture(self):
  # Synthetic mapping/metadata fixture only, not a native-quality or geometric-domain proof.
  case,obs,shell,context=self.old_fixture();case.update(N=5,M=4,I=1,candidate_interior_node_tags=[17],records={'arrays':{'sha256':'b'*64},'worker':{'sha256':'c'*64}})
  a=dict(node_tags=[1,2,3,4,17],coordinates_mm=[[0.,0.,0.],[2.,0.,0.],[0.,2.,0.],[0.,0.,2.],[.5,.5,.5]],tetra_tags=[10,11,12,13],tetra_node_tags=[[17,2,3,4],[1,17,3,4],[1,2,17,4],[1,2,3,17]])
  state=dict(nodes=5,tetrahedra=4,referenced_interior_nodes=1,unreferenced_nodes=0,quality={'SICN':dict(count=4,minimum=.5,below_point1_count=0,nonpositive_count=0)},
   node_classifications=[[t,2 if t<=4 else 3] for t in a['node_tags']],node_entity_classifications=[[t,2 if t<=4 else 3,1] for t in a['node_tags']])
  w=dict(status='completed_finite_selected_cavity_Netgen_only',after=state,saved_reopen=state,full_tiny_arrays_sha256='b'*64,actual_SICN_threshold=.1)
  for k in ['fixture_procedural_checks_passed','actual_SICN_gate_passed','saved_mesh_identity_exact','bound_inputs_unchanged','geometry_flag_full_state_unchanged','exact_boundary_bits_faces_classifications']:w[k]=True
  for k in ['head_execution_authorized','stitching_authorized','native_head_application_authorized','engineering_accepted','physics_qualified','manufacturing_authorized']:w[k]=False
  return case,w,{'after':a,'saved_reopen':a},shell,dict(decision='CLEAR_COMPLETED_LOCAL_SAVED_EVIDENCE_47_PROVISIONAL_DOMAIN_ROUTES_68_REJECTS')
 def test_noncontiguous_actual_interior_tags_and_candidate_refusals(self):
  case,w,a,shell,peer=self.candidate_fixture()
  patch=dict(CASE=case,WORKER='fixture-worker',ARRAYS='fixture-arrays',INPUTS={'fixture-worker':'c'*64,'fixture-arrays':'b'*64})
  with mock.patch.multiple(module,**patch):
   points,cells=module.saved_candidate(w,a,shell,peer);self.assertIn(17,points);self.assertNotIn(5,points);self.assertEqual(len(cells),4)
  for mode in ['wrong_quality','wrong_class','signed_zero','duplicate_corner','orphan','wrong_interior_set']:
   with self.subTest(mode=mode):
    c,w,a,s,p=self.candidate_fixture()
    if mode=='wrong_quality':w['saved_reopen']['quality']['SICN']['minimum']=.099
    if mode=='wrong_class':w['saved_reopen']['node_classifications'][0][1]=3
    if mode=='signed_zero':a['saved_reopen']['coordinates_mm'][0][0]=-0.
    if mode=='duplicate_corner':a['saved_reopen']['tetra_node_tags'][0]=[17,1,1,3]
    if mode=='orphan':a['saved_reopen']['tetra_node_tags']=[[1,2,3,4]]*4
    if mode=='wrong_interior_set':c['candidate_interior_node_tags']=[19]
    with mock.patch.multiple(module,CASE=c,WORKER='fixture-worker',ARRAYS='fixture-arrays',INPUTS={'fixture-worker':'c'*64,'fixture-arrays':'b'*64}):
     with self.assertRaises(ValueError):module.saved_candidate(w,a,s,p)
 def test_donor_math_AST_identity_and_fixed_helper_namespace(self):
  donor=module.ROOT/'work/962-engineering/apex1474426-domain-equivalence-prep-001/certify_domain.py'
  functions=lambda s:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
  old=functions(donor.read_text());new=functions(SOURCE.read_text())
  self.assertEqual({k:new[k] for k in ['cycle','complex_rows']},{k:old[k] for k in ['cycle','complex_rows']})
  self.assertEqual(module.FIXED_INPUTS[module.HELPER],'1b489cc8149f4b5db8f90c594e32fe4c09b5db00151df6b1cfc88362d1018134')
  self.assertFalse(any(module.QUALIFICATION.values()))

if __name__=='__main__':main()
