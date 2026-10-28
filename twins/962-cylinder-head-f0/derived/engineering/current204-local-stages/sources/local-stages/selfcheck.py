"""Prepared stdlib/AST synthetic guards only; no real manifest/native worker import."""
from pathlib import Path
from fractions import Fraction
import ast,copy,hashlib,json,math,struct,tempfile,unittest
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
GEN=ast.parse((HERE/'generate_case.py').read_text())
NET=ast.parse((HERE/'netgen_case.py').read_text())
SOURCE_SHA={'generate_case.py':'fc1aba0a0ae93995f8fc4eea86d3fe693ce0360ac3f98d158ba5f01ae8983e3d',
 'netgen_case.py':'38af98145aa8c4aa1798b5e5901a9837b962e8841d5b5d504674d6cefa922924'}
for name,digest in SOURCE_SHA.items():
 if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=digest:raise ValueError('Frozen source changed')

def selected(tree,names,ns):
 nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 if {n.name for n in nodes}!=set(names):raise ValueError('Complete selected guard definitions required')
 exec(compile(ast.Module(body=nodes,type_ignores=[]),'<synthetic-stdlib-only>', 'exec'),ns)
 return ns

def selector_fixture():
 records=[];cases=[]
 encoded=lambda x:(json.dumps(x,indent=2,allow_nan=False)+'\n').encode()
 sha=lambda x:hashlib.sha256(encoded(x)).hexdigest()
 for i in range(116):
  apex=10000+i;shell=dict(vertices=4,oriented_triangles=4,exact_enclosed_volume_mm3={'numerator':1,'denominator':6},
   original_source_classifications={'boundary_global_node_tags':[i*10+1,i*10+2],'other_interior_global_node_tags':[i*10+3,i*10+4]})
  r=dict(apex=apex,eligible=True,all_vertex_tags=[i*10+1,i*10+2,i*10+3,i*10+4,apex],source_complete_incident_cell_count=4,
   source_tetrahedron_tags=[i*4+j+1 for j in range(4)],poor_tetrahedron_tags=[i*4+1],shell=shell,observation={'source':apex},necessary_face_screen={'all':True})
  cases.append(dict(apex=apex,source_record_sha256=sha(r),shell_serialized_sha256=sha(shell),observation_serialized_sha256=sha(r['observation']),screen_serialized_sha256=sha(r['necessary_face_screen']),
   old_tetrahedra=4,old_vertex_tags=r['all_vertex_tags'],old_tetrahedron_tags=r['source_tetrahedron_tags'],old_poor_tags=r['poor_tetrahedron_tags'],
   shell_nodes=4,shell_faces=4,exact_volume_mm3=shell['exact_enclosed_volume_mm3'],original_boundary_shell_nodes=2,other_interior_shell_nodes=2))
  records.append(r)
 return dict(schema='962-current204-finite-local-stage-manifest/v1',selected_count=116,cases_in_increasing_apex_order=cases,source_parent_MSH_sha256='parent'),dict(selected_apex_tags=[r['apex'] for r in records],all_candidate_star_records=records,source_current_positive_poor_cells=204,source_MSH_sha256='parent')

class Guards(unittest.TestCase):
 def test_exact116_membership_subrecord_hashes_and_whole_vertex_conflict(self):
  f=selected(GEN,['encoded','select_case'],dict(json=json,hashlib=hashlib))['select_case'];manifest,batch=selector_fixture()
  self.assertEqual(f(manifest,batch,10003)[0]['apex'],10003)
  with self.assertRaises(ValueError):f(manifest,batch,9999)
  changed=copy.deepcopy(batch);changed['all_candidate_star_records'][0]['all_vertex_tags'][0]=11
  changed_manifest=copy.deepcopy(manifest);encoded=lambda x:(json.dumps(x,indent=2,allow_nan=False)+'\n').encode()
  changed_manifest['cases_in_increasing_apex_order'][0]['source_record_sha256']=hashlib.sha256(encoded(changed['all_candidate_star_records'][0])).hexdigest()
  with self.assertRaises(ValueError):f(changed_manifest,changed,10003)
  changed=copy.deepcopy(manifest);changed['cases_in_increasing_apex_order'][3]['shell_serialized_sha256']='0'*64
  with self.assertRaises(ValueError):f(changed,batch,10003)
  changed=copy.deepcopy(manifest);changed['cases_in_increasing_apex_order'][3]['old_tetrahedra']=5
  with self.assertRaises(ValueError):f(changed,batch,10003)

 def test_dynamic_shell_raw_signed_zero_inverse_class_and_volume(self):
  ns=selected(GEN,['validate_shell','shell_rows'],dict(Fraction=Fraction,math=math,struct=struct,NV=4,NF=4,NB=2,APEX=999,VOLUME=Fraction(1,6)))
  points=[[-0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]];faces=[[1,3,2],[1,2,4],[1,4,3],[2,3,4]];mapping=[10,20,30,40]
  shell=dict(schema='962-fixed-cavity-local-shell-input/v1',vertices=4,oriented_triangles=4,excluded_source_apex_tag=999,apex_not_in_shell_input=True,status='DATA_ONLY_HELD',necessary_face_quality_passed=True,generation_input_rejected_by_necessary_face_quality=False,
   local_to_global_node_tags=mapping,global_to_local_node_tags={str(t):i+1 for i,t in enumerate(mapping)},
   vertex_rows=[dict(local_node_tag=i+1,source_global_node_tag=mapping[i],coordinates_mm=p,binary64_hex=[v.hex() for v in p],binary64_little_endian_bytes_hex=struct.pack('<3d',*p).hex(),prospective_cavity_fixed=True,original_source_boundary_node=i<2,original_source_classification='below_dim3' if i<2 else 'dim3') for i,p in enumerate(points)],
   oriented_triangle_rows=[dict(local_face_id=i+1,source_owner_tetrahedron_tag=i+100,local_node_tags=f) for i,f in enumerate(faces)],
   original_source_classifications=dict(boundary_global_node_tags=mapping[:2],other_interior_global_node_tags=mapping[2:],boundary_local_node_tags=[1,2],other_interior_local_node_tags=[3,4]),exact_enclosed_volume_mm3={'numerator':1,'denominator':6})
  answer=ns['shell_rows'](shell);self.assertEqual(struct.pack('<d',answer[0][0][0]),struct.pack('<d',-0.))
  for kind in ['bits','class','inverse','face','volume']:
   changed=copy.deepcopy(shell)
   if kind=='bits':changed['vertex_rows'][0]['coordinates_mm'][0]=0.
   elif kind=='class':changed['vertex_rows'][2]['original_source_boundary_node']=True
   elif kind=='inverse':changed['global_to_local_node_tags']['10']=2
   elif kind=='face':changed['oriented_triangle_rows'][0]['local_node_tags'].reverse()
   else:changed['exact_enclosed_volume_mm3']['numerator']=2
   with self.assertRaises(ValueError):ns['shell_rows'](changed)

 def test_predeclared_route_and_storage_no_backfill_or_retry(self):
  ns=selected(GEN,['candidate_storage_admission','case_route'],{});case={'old_tetrahedra':20};admit=ns['candidate_storage_admission']
  self.assertTrue(admit({'referenced_interior_nodes':1,'tetrahedra':20},case))
  self.assertFalse(admit({'referenced_interior_nodes':0,'tetrahedra':25},case));self.assertFalse(admit({'referenced_interior_nodes':2,'tetrahedra':19},case))
  route=ns['case_route'];self.assertEqual(route(False,False,False),'stop_case');self.assertEqual(route(True,False,False),'one_Netgen')
  self.assertEqual(route(True,True,True),'domain');self.assertEqual(route(True,True,False),'hold_mapping_incompatible_no_Netgen')
  with self.assertRaises(ValueError):route(True,1,True)

 def test_Netgen_requires_same_case_five_outputs_plus_stopped_peer_and_root(self):
  f=selected(NET,['configure_baseline'],{})['configure_baseline'];apex=10003;d='work/962-engineering/head-star-current204-apex-10003-generation-001'
  b={k:dict(path=d+'/'+v,sha256=k) for k,v in dict(mesh='cavity.msh',worker='fixture-report.json',arrays='arrays.json',receipt='execution-receipt.json',actual='frozen-contract.json',root_closed='root.json',result_peer='peer.json').items()}
  c=dict(case_apex=apex,generation_baseline=b,input_hashes={v['path']:v['sha256'] for v in b.values()});f(c)
  for kind in ['case','peer','hash']:
   changed=copy.deepcopy(c)
   if kind=='case':changed['case_apex']=10004
   elif kind=='peer':changed['generation_baseline'].pop('result_peer')
   else:changed['input_hashes'][b['worker']['path']]='changed'
   with self.assertRaises(ValueError):f(changed)

 def test_dynamic_generation_rejection_proof_and_receipt_refusals(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);receipt=root/'receipt.json'
   receipt.write_text(json.dumps(dict(returncode=2,stop_reason=None,fixture_report_sha256='worker',contract_sha256='actual',reader_sha256='reader',runner_sha256='runner')))
   f=selected(NET,['require_saved_baseline'],dict(ROOT=root,json=json,INPUT_SHA='mesh',ARRAYS_SHA='arrays',WORKER_SHA='worker',CAVITY_SHA='reader',GENERATION_RUNNER_SHA='runner',MANIFEST_SHA='manifest',BATCH_SHA='batch'))['require_saved_baseline']
   case=dict(apex=10003,case_key='apex-10003',source_record_sha256='record',shell_serialized_sha256='shell')
   r=dict(nodes=13,tetrahedra=17,referenced_interior_nodes=2,unreferenced_nodes=0,quality={'SICN':dict(count=17,minimum=.02,below_point1_count=3,nonpositive_count=0)})
   w=dict(status='completed_finite_selected_cavity_generation_only',fixture_procedural_checks_passed=True,actual_SICN_gate_passed=False,next_stage='one_Netgen',saved_mesh_identity_exact=True,bound_inputs_unchanged=True,
    case_apex=10003,case_key='apex-10003',case_record_sha256='record',case_manifest_sha256='manifest',local_shell_serialized_sha256='shell',source_batch_sha256='batch',mesh_sha256='mesh',mesh_bytes=111,full_tiny_arrays_sha256='arrays',after_generation=r,saved_reopen=r)
   c=dict(generation_runner_sha256='runner',generation_baseline={'mesh':{'bytes':111},'receipt':{'path':'receipt.json'},'actual':{'sha256':'actual'}});f(w,c,case)
   for key,value in [('case_apex',10004),('fixture_procedural_checks_passed',False),('actual_SICN_gate_passed',True),('next_stage','domain'),('mesh_bytes',112)]:
    changed=copy.deepcopy(w);changed[key]=value
    with self.assertRaises(ValueError):f(changed,c,case)
   value=json.loads(receipt.read_text());value['stop_reason']='deadline';receipt.write_text(json.dumps(value))
   with self.assertRaises(ValueError):f(w,c,case)

 def test_held_authority_refuses_before_files_or_runtime(self):
  for tree in [GEN,NET]:
   f=selected(tree,['require_authority'],{})['require_authority']
   with self.assertRaises(ValueError):f({'native_execution_authorized':False})

 def test_exact_native_policy_one_operation_and_full_saved_audits(self):
  g=(HERE/'generate_case.py').read_text();n=(HERE/'netgen_case.py').read_text()
  self.assertEqual(g.count('gmsh.model.mesh.generate(3)'),1)
  self.assertEqual(n.count('helper.optimize_once(gmsh,'),1);self.assertEqual(n.count('helper.geometry_flag_only(gmsh,'),1)
  self.assertNotIn('gmsh.model.mesh.generate',n)
  self.assertIn("helper.require_same(live['after_generation'],live['saved_reopen']",g)
  self.assertIn("helper.require_same(live['after'],live['saved_reopen']",n)
  self.assertIn("if live['after'][0]!=live['saved_reopen'][0]",n)
  for text in [g,n]:
   self.assertNotIn('setNode(',text);self.assertIn("actual_SICN_threshold=.1",text);self.assertNotIn('while ',text)

 def test_controller_cleanup_ASTs_and_limits_unchanged(self):
  root=HERE.parents[2]
  for name,donor in [('run_generation.py','fixed-shell-generation-apex1474426-prep-001'),('run_netgen.py','fixed-shell-netgen-apex1474426-prep-001')]:
   new=ast.parse((HERE/name).read_text());old=ast.parse((root/'work/962-engineering'/donor/'run_readback.py').read_text())
   for fn in ['stop','request_sigterm']:
    a=next(n for n in ast.walk(new) if isinstance(n,ast.FunctionDef) and n.name==fn);b=next(n for n in ast.walk(old) if isinstance(n,ast.FunctionDef) and n.name==fn)
    self.assertEqual(ast.dump(a,include_attributes=False),ast.dump(b,include_attributes=False))
   a=next(n for n in ast.walk(new) if isinstance(n,ast.While));b=next(n for n in ast.walk(old) if isinstance(n,ast.While));self.assertEqual(ast.dump(a),ast.dump(b))
   text=(HERE/name).read_text();self.assertIn('hard_wall_seconds=30',text);self.assertIn('sampled_RSS_stop_bytes=1024**3',text);self.assertIn('sampled_output_stop_bytes=16*1024**2',text)

if __name__=='__main__':unittest.main()
