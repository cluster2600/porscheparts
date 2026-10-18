"""Prepared synthetic stdlib/AST union-context guards; no native/scientific import."""
from pathlib import Path
import ast,copy,hashlib,json,math,struct,unittest

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];SOURCE=HERE/'reader.py'
SOURCE_SHA='c852a8a536a0ef2c58a37132fb51e42e525403d1f519375cc04a9860bfe53b29'
if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Frozen reader changed')
TREE=ast.parse(SOURCE.read_text());FACES=((0,2,1),(0,1,3),(1,2,3),(2,0,3))
encoded=lambda x:(json.dumps(x,indent=2,allow_nan=False)+'\n').encode()
digest=lambda x:hashlib.sha256(encoded(x)).hexdigest()

def select(names,ns):
 rows=[n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name in names]
 if {r.name for r in rows}!=set(names):raise ValueError('All selected stdlib definitions required')
 exec(compile(ast.Module(body=rows,type_ignores=[]),'<synthetic-only>','exec'),ns);return ns

def fixture(offset):
 apex=1000000+offset;mapping=[10+offset,20+offset,900010+offset,900020+offset]
 xyz=[[-0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]];xyz=[[v+(3*offset if j==0 else 0) for j,v in enumerate(p)] for p in xyz]
 if offset==0:xyz[0][0]=-0.
 faces=[[1,3,2],[1,2,4],[1,4,3],[2,3,4]];cells=[]
 for i,face in enumerate(faces):cells.append(dict(tetrahedron_tag=100+offset+i,native_array_index=offset+i,node_tags=[apex,*[mapping[t-1] for t in face]],initially_positive_poor=i==0))
 points=[dict(node_tag=t,coordinates_mm=p,binary64_hex=[float(v).hex() for v in p]) for t,p in zip(mapping,xyz)]
 points.append(dict(node_tag=apex,coordinates_mm=[3*offset+.25,.25,.25],binary64_hex=[float(v).hex() for v in [3*offset+.25,.25,.25]]));points.sort(key=lambda r:r['node_tag'])
 for row in points:row.update(in_movable_seed_set=row['node_tag']==apex,source_boundary_tag=row['node_tag']<=871731,freshly_proved_classification_scope='below_dim3' if row['node_tag']<=871731 else 'dim3')
 observed_points=[dict(row,binary64_little_endian_bytes_hex=struct.pack('<3d',*row['coordinates_mm']).hex()) for row in points]
 shell=dict(excluded_source_apex_tag=apex,apex_not_in_shell_input=True,necessary_face_quality_passed=True,generation_input_rejected_by_necessary_face_quality=False,
  local_to_global_node_tags=mapping,global_to_local_node_tags={str(t):i+1 for i,t in enumerate(mapping)},
  original_source_classifications=dict(boundary_global_node_tags=mapping[:2],other_interior_global_node_tags=mapping[2:]),
  vertex_rows=[dict(local_node_tag=i+1,source_global_node_tag=t,coordinates_mm=p,binary64_hex=[float(v).hex() for v in p],binary64_little_endian_bytes_hex=struct.pack('<3d',*p).hex(),original_source_boundary_node=i<2) for i,(t,p) in enumerate(zip(mapping,xyz))],
  oriented_triangle_rows=[dict(local_node_tags=f,source_owner_tetrahedron_tag=cells[i]['tetrahedron_tag'],native_corner_indices=[1,2,3],source_global_node_tags=[mapping[t-1] for t in f],source_native_array_index=cells[i]['native_array_index']) for i,f in enumerate(faces)])
 obs=dict(apex=apex,native_ordered_cell_rows=cells,selected_node_rows=observed_points)
 record=dict(apex=apex,eligible=True,all_vertex_tags=sorted(mapping+[apex]),observation=obs,shell=shell,necessary_face_screen={'all':True})
 case=dict(apex=apex,case_key='apex-'+str(apex),shell_nodes=4,shell_faces=4,old_tetrahedra=4,original_boundary_shell_nodes=2,
  source_record_sha256=digest(record),shell_serialized_sha256=digest(shell),observation_serialized_sha256=digest(obs),screen_serialized_sha256=digest(record['necessary_face_screen']),old_tetrahedron_tags=[r['tetrahedron_tag'] for r in cells],old_vertex_tags=record['all_vertex_tags'])
 return case,record,cells,{r['node_tag']:r for r in points}

def refresh(case,record):
 case['source_record_sha256']=digest(record);case['shell_serialized_sha256']=digest(record['shell']);case['observation_serialized_sha256']=digest(record['observation'])

class Guards(unittest.TestCase):
 def test_two_disjoint_complete_cases_and_good_context(self):
  a,r,ac,an=fixture(0);b,s,bc,bn=fixture(100);ns=select(['encoded','observation_node_matches','one_case_records','merge_case_records'],dict(json=json,hashlib=hashlib,math=math,struct=struct,FACES=FACES,BOUNDARY=871731))
  answer=ns['merge_case_records']([a,b],{a['apex']:r,b['apex']:s},ac+bc,{**an,**bn})
  self.assertEqual([len(answer[i]) for i in [0,1,2,3,5]],[8,10,8,8,2]);self.assertEqual(set(answer[5]),{a['apex'],b['apex']})
  self.assertEqual(sum(not row['initially_positive_poor'] for row in ac+bc),6)
  changed=copy.deepcopy(s);changed['observation']['native_ordered_cell_rows'].pop();altered=copy.deepcopy(b);altered['old_tetrahedra']=3;altered['old_tetrahedron_tags'].pop();refresh(altered,changed)
  with self.assertRaises(ValueError):ns['merge_case_records']([a,altered],{a['apex']:r,b['apex']:changed},ac+bc,{**an,**bn})

 def test_shared_vertex_or_face_refusal_and_raw_signed_zero(self):
  a,r,ac,an=fixture(0);b,s,bc,bn=fixture(100);ns=select(['encoded','observation_node_matches','one_case_records','merge_case_records'],dict(json=json,hashlib=hashlib,math=math,struct=struct,FACES=FACES,BOUNDARY=871731))
  changed=copy.deepcopy(s);changed['all_vertex_tags'][0]=r['all_vertex_tags'][0];altered=copy.deepcopy(b);refresh(altered,changed)
  with self.assertRaises(ValueError):ns['merge_case_records']([a,altered],{a['apex']:r,b['apex']:changed},ac+bc,{**an,**bn})
  changed=copy.deepcopy(r['shell']);changed['oriented_triangle_rows'][1]=copy.deepcopy(changed['oriented_triangle_rows'][0])
  with self.assertRaises(ValueError):ns['one_case_records'](r['observation'],changed,a)
  changed=copy.deepcopy(r['shell']);changed['vertex_rows'][0]['coordinates_mm'][0]=0.
  with self.assertRaises(ValueError):ns['one_case_records'](r['observation'],changed,a)
  changed=copy.deepcopy(r['shell']);changed['vertex_rows'][2]['original_source_boundary_node']=True
  with self.assertRaises(ValueError):ns['one_case_records'](r['observation'],changed,a)
  original=an[r['observation']['selected_node_rows'][0]['node_tag']];observed=r['observation']['selected_node_rows'][0]
  self.assertEqual(len(original),6);self.assertEqual(len(observed),7);check=ns['observation_node_matches'];self.assertTrue(check(original,observed))
  replacements={'node_tag':original['node_tag']+1,'coordinates_mm':[0.,0.,0.],
   'binary64_hex':[float(0.).hex(),float(0.).hex(),float(0.).hex()],
   'in_movable_seed_set':True,'source_boundary_tag':False,'freshly_proved_classification_scope':'dim3',
   'binary64_little_endian_bytes_hex':'00'*24,'unexpected_field':7}
  for key,value in replacements.items():
   changed=copy.deepcopy(observed);changed[key]=value
   self.assertFalse(check(original,changed),key)
  changed=copy.deepcopy(observed);changed.pop('binary64_little_endian_bytes_hex');self.assertFalse(check(original,changed))


 def test_complete_all_owners_and_exterior_TRI_or_internal_opposite(self):
  ns=select(['canonical','validate_interface'],{});f=ns['validate_interface'];key=(1,2,3);expected={key:[1,2,3]}
  old=dict(removed_star_owner=True,oriented_face=[1,2,3]);outside=dict(removed_star_owner=False,oriented_face=[3,2,1])
  self.assertEqual(f(expected,{key:[old,outside]},{key:[]})[0]['interface_kind'],'internal_with_outside_owner')
  self.assertEqual(f(expected,{key:[old]},{key:[{'node_tags':[1,2,3]}]})[0]['interface_kind'],'parent_exterior')
  for owners,triangles in [({key:[old]},{key:[]}),({key:[old,outside,outside]},{key:[]}),({key:[old,outside]},{key:[{'node_tags':[1,2,3]}]}),({}, {key:[]})]:
   with self.assertRaises(ValueError):f(expected,owners,triangles)

 def test_masks_exclude_only_apices_and_old_cell_union(self):
  f=select(['mask_exclusions'],{})['mask_exclusions'];tags=[1,2,3,4,100,101,999];elements=[10,11,12,20,21,22,9999]
  nodes,cells=f([100,101],{10:[],11:[],20:[]},tags,elements)
  self.assertEqual(nodes,[100,101]);self.assertEqual(cells,[10,11,20]);self.assertEqual([t for t in tags if t not in nodes],[1,2,3,4,999]);self.assertEqual([t for t in elements if t not in cells],[12,21,22,9999])
  with self.assertRaises(ValueError):f([100,100],{10:[]},tags,elements)
  with self.assertRaises(ValueError):f([102],{10:[]},tags,elements)

 def test_full_parameter_projection_and_all_dimensional_maxima(self):
  ns=select(['parameter_projection','validate_maxima'],{});row=dict(dimension=2,entity_tag=1,count=10,parameter_width=2,node_tags_u64_sha256='tags',coordinate_words_f64_sha256='coordinates',available_parameter_words_f64_sha256='signed-zero-parameter-bits')
  a=ns['parameter_projection']([row]);changed=dict(row,coordinate_words_f64_sha256='moved-apex-coordinate');self.assertEqual(a,ns['parameter_projection']([changed]))
  changed=dict(row,available_parameter_words_f64_sha256='parameter-drift');self.assertNotEqual(a,ns['parameter_projection']([changed]))
  self.assertEqual(ns['validate_maxima'](100,999,100,999),{'node':100,'element_all_dimensions':999})
  with self.assertRaises(ValueError):ns['validate_maxima'](100,999,100,200)

 def test_current204_proof_refuses_old208_or_wrong_census(self):
  ns=dict(MSH_SHA='mesh',WORKER='worker',FIRST='first',FIXED_INPUTS={'worker':'workerhash','first':'firsthash'})
  f=select(['current_after_proof'],ns)['current_after_proof'];proof={'array_sha256s':{'a':'aa'},'classifications':{'c':1}}
  helpers={'partial_after_proof':lambda *args:proof,'require_after_match':lambda report,proof,total:self.assertEqual(total,204)}
  prior=dict(MSH_sha256='mesh',MSH_bytes=235744782,partial_report_sha256='workerhash',expected_positive_poor_total=204)
  first=dict(status='direct_saved_file_readback_completed',bound_inputs_unchanged=True,single_partial_replacement_saved_proof=dict(report_sha256='workerhash',field='after',after_equals_saved_reopen=True,independent_prior_reader_alias_used=False,old210_bins_reused=False),a='aa',direct_fresh_classifications={'c':1})
  peer=dict(decision='CLEAR_COMPLETED_READ_ONLY_CENSUS_WHOLE_HEAD_QUALITY_REJECTED',records={'worker_report':{'sha256':'firsthash'}},blockers=[],engineering_accepted=False)
  self.assertEqual(f({}, {}, {},first,prior,peer,helpers),proof)
  changed=dict(prior,expected_positive_poor_total=208)
  with self.assertRaises(ValueError):f({}, {}, {},first,changed,peer,helpers)
  changed=copy.deepcopy(peer);changed['records']['worker_report']['sha256']='old'
  with self.assertRaises(ValueError):f({}, {}, {},first,prior,changed,helpers)

 def test_held_refusal_and_unchanged_face_kernels_controller(self):
  f=select(['require_inputs'],{})['require_inputs']
  with self.assertRaises(ValueError):f({'native_execution_authorized':False})
  donor=ast.parse((ROOT/'work/962-engineering/direct-sicn-apex1474426-head-context-prep-001/reader.py').read_text())
  for name in ['canonical','face_hits','validate_interface']:
   a=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name==name);b=next(n for n in donor.body if isinstance(n,ast.FunctionDef) and n.name==name);self.assertEqual(ast.dump(a),ast.dump(b))
  new=ast.parse((HERE/'run_readback.py').read_text());old=ast.parse((ROOT/'work/962-engineering/direct-sicn-apex1474426-head-context-prep-001/run_readback.py').read_text())
  for name in ['stop','request_sigterm']:
   a=next(n for n in ast.walk(new) if isinstance(n,ast.FunctionDef) and n.name==name);b=next(n for n in ast.walk(old) if isinstance(n,ast.FunctionDef) and n.name==name);self.assertEqual(ast.dump(a),ast.dump(b))
  self.assertEqual(ast.dump(next(n for n in ast.walk(new) if isinstance(n,ast.While))),ast.dump(next(n for n in ast.walk(old) if isinstance(n,ast.While))))

if __name__=='__main__':unittest.main()
