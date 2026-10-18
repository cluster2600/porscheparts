"""UNRUN selected-AST interface guards and tiny selected-NumPy integer-key check; no Gmsh."""
from pathlib import Path
import ast, copy, hashlib, json, math, struct
from itertools import combinations
SOURCE_SHA='4640bc7c306f3016674a16a49734975bbaa96752075fc42deddb0a5fc2dabddb'
source=Path(__file__).with_name('reader.py')
assert hashlib.sha256(source.read_bytes()).hexdigest()==SOURCE_SHA
tree=ast.parse(source.read_text());functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
ns={'math':math,'struct':struct,'APEX':1474426,'BOUNDARY':871731,'FACES':((0,2,1),(0,1,3),(1,2,3),(2,0,3))};names=['canonical','validate_interface','face_hits','selection_records','current_after_proof']
exec(compile(ast.fix_missing_locations(ast.Module(body=[functions[n] for n in names],type_ignores=[])),'<selected-interface-only>','exec'),ns)
expected={(1,2,3):[1,2,3],(4,5,6):[4,5,6]}
owners={(1,2,3):[{'removed_star_owner':True,'oriented_face':[2,3,1]},
                    {'removed_star_owner':False,'oriented_face':[1,3,2]}],
        (4,5,6):[{'removed_star_owner':True,'oriented_face':[4,5,6]}]}
triangles={(1,2,3):[],(4,5,6):[{'node_tags':[5,6,4]}]}
answer=ns['validate_interface'](expected,owners,triangles)
assert [r['interface_kind'] for r in answer]==['internal_with_outside_owner','parent_exterior']
def refuses(o,t):
 try:ns['validate_interface'](expected,o,t)
 except ValueError:return
 raise AssertionError('Expected complete interface refusal')
bad=copy.deepcopy(owners);bad[(1,2,3)][1]['oriented_face']=[1,2,3];refuses(bad,triangles)
bad=copy.deepcopy(owners);bad[(1,2,3)].append(copy.deepcopy(bad[(1,2,3)][1]));refuses(bad,triangles)
bad=copy.deepcopy(triangles);bad[(1,2,3)]=[{'node_tags':[1,2,3]}];refuses(owners,bad)
bad=copy.deepcopy(triangles);bad[(4,5,6)]=[];refuses(owners,bad)
bad=copy.deepcopy(owners);bad[(4,5,6)]=[];refuses(bad,triangles)
assert ns['canonical']([1,2,3])==ns['canonical']([3,1,2])!=ns['canonical']([1,3,2])
for node in ast.walk(tree):
 if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
  assert node.func.attr not in ['getElementQualities','generate','optimize','setNode','addNodes','addElementsByType','removeElements','createGeometry','reclassifyNodes']
  assert ast.unparse(node.func)!='gmsh.write'
# Case-only mapping/owner guards use fabricated metadata, not a geometric mesh fixture.
def synthetic_selection():
 mapping=list(range(1,28))+list(range(900000,900005));apex=1474426
 def point(tag,local):
  xyz=[float(local),0.,-0.]
  return dict(node_tag=tag,coordinates_mm=xyz,binary64_hex=[x.hex() for x in xyz])
 points=[point(t,i) for i,t in enumerate(mapping+[apex],1)];lookup={r['node_tag']:r for r in points}
 triples=list(combinations(mapping,3))[:60]
 cells=[dict(tetrahedron_tag=1000+i,native_array_index=i,node_tags=[apex,*face]) for i,face in enumerate(triples)]
 vertices=[dict(local_node_tag=i,source_global_node_tag=t,coordinates_mm=lookup[t]['coordinates_mm'],binary64_hex=lookup[t]['binary64_hex'],binary64_little_endian_bytes_hex=struct.pack('<3d',*lookup[t]['coordinates_mm']).hex(),original_source_boundary_node=t<=871731) for i,t in enumerate(mapping,1)]
 faces=[dict(local_node_tags=[mapping.index(t)+1 for t in face],source_global_node_tags=list(face),source_owner_tetrahedron_tag=1000+i,source_native_array_index=i,native_corner_indices=[1,2,3]) for i,face in enumerate(triples)]
 observation=dict(apex=apex,native_ordered_cell_rows=cells,selected_node_rows=points)
 shell=dict(excluded_source_apex_tag=apex,apex_not_in_shell_input=True,necessary_face_quality_passed=True,generation_input_rejected_by_necessary_face_quality=False,local_to_global_node_tags=mapping,global_to_local_node_tags={str(t):i for i,t in enumerate(mapping,1)},original_source_classifications=dict(boundary_global_node_tags=mapping[:27],other_interior_global_node_tags=mapping[27:]),vertex_rows=vertices,oriented_triangle_rows=faces)
 return observation,shell
obs,shell=synthetic_selection();answer=ns['selection_records'](obs,shell)
assert len(answer[0])==60 and len(answer[1])==33 and len(answer[2])==32 and len(answer[3])==60 and len(answer[4])==27
for category in ['apex','inverse','bytes','classification','owner','winding','missing_face','old16map']:
 o,b=copy.deepcopy(obs),copy.deepcopy(shell)
 if category=='apex':o['apex']=1435493
 elif category=='inverse':b['global_to_local_node_tags'][str(b['local_to_global_node_tags'][0])]=2
 elif category=='bytes':b['vertex_rows'][0]['binary64_little_endian_bytes_hex']='00'*24
 elif category=='classification':b['original_source_classifications']['boundary_global_node_tags']=b['local_to_global_node_tags']
 elif category=='owner':b['oriented_triangle_rows'][0]['source_owner_tetrahedron_tag']=999
 elif category=='winding':b['oriented_triangle_rows'][0]['local_node_tags'].reverse()
 elif category=='missing_face':b['oriented_triangle_rows'].pop()
 elif category=='old16map':b['local_to_global_node_tags']=b['local_to_global_node_tags'][:16]
 try:ns['selection_records'](o,b)
 except ValueError:pass
 else:raise AssertionError('Expected specific current60/32 selection refusal: '+category)
# Mock only the two unchanged donor proof calls; this tests the new current-census join.
ns.update(MSH_SHA='m'*64,WORKER='current.json',FIRST='census.json',FIXED_INPUTS={'current.json':'w'*64,'census.json':'c'*64})
proof=dict(array_sha256s={'sorted_coordinates_sha256':'a'*64},classifications={});calls=[]
helpers=dict(partial_after_proof=lambda *args:proof,require_after_match=lambda first,observed,total:calls.append(total))
prior=dict(MSH_sha256='m'*64,MSH_bytes=235742918,partial_report_sha256='w'*64,expected_positive_poor_total=208)
first=dict(status='direct_saved_file_readback_completed',bound_inputs_unchanged=True,single_partial_replacement_saved_proof=dict(report_sha256='w'*64,field='after',after_equals_saved_reopen=True,independent_prior_reader_alias_used=False,old210_bins_reused=False),sorted_coordinates_sha256='a'*64,direct_fresh_classifications={})
peer=dict(decision='CLEAR_COMPLETED_READ_ONLY_CURRENT208_CENSUS_MESH_REMAINS_REJECTED',bindings=dict(report=dict(sha256='c'*64)),blockers=[],head_volume_accepted=False)
assert ns['current_after_proof']({}, {},{},first,prior,peer,helpers) is proof and calls==[208]
for category in ['old_count','mesh','optimizer_alias','arrays','classes','accepted_head']:
 f,p,e=copy.deepcopy(first),copy.deepcopy(prior),copy.deepcopy(peer)
 if category=='old_count':p['expected_positive_poor_total']=210
 elif category=='mesh':p['MSH_sha256']='old'
 elif category=='optimizer_alias':f['single_partial_replacement_saved_proof']={'worker_report_sha256':'w'*64,'field':'after'}
 elif category=='arrays':f['sorted_coordinates_sha256']='old'
 elif category=='classes':f['direct_fresh_classifications']={'changed':True}
 elif category=='accepted_head':e['head_volume_accepted']=True
 try:ns['current_after_proof']({}, {},{},f,p,e,helpers)
 except ValueError:pass
 else:raise AssertionError('Expected current partial proof refusal: '+category)

# Root-only literal check of the actual NumPy integer face matcher, not a head query.
import numpy as np
assert np.__version__=='2.0.2'
assert Path(np.__file__).resolve()==Path('runtime-role://registered-native/numpy/__init__.py')
high=2**53+1;keys={(1,2,3),(7,8,9),(high,high+1,high+2)}
rows=np.asarray([[9,7,8],[1,2,3],[4,5,6],[3,2,1],[high+2,high,high+1]],dtype='<u8')
assert ns['face_hits'](np,rows,keys).tolist()==[0,1,3,4]
assert ns['face_hits'](np,np.empty((0,3),dtype='<u8'),keys).tolist()==[]
print(json.dumps({'status':'pass','scope':'Inherited interface/AST/literal uint64 guards plus case-only current proof and synthetic60/32 map refusals; no Gmsh/head query/native mutation.'}))
