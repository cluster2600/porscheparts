"""UNRUN stdlib/selected-AST metadata and interface guards; no NumPy/Gmsh/runtime load."""
from pathlib import Path
import ast, copy, hashlib, json, math, struct
from itertools import combinations
SOURCE_SHA='7b38ef1fd0928544126e3b4f9720049037ad47e82a48162863b3a103057c81dd'
source=Path(__file__).with_name('reader.py')
assert hashlib.sha256(source.read_bytes()).hexdigest()==SOURCE_SHA
tree=ast.parse(source.read_text());functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
ns={'math':math,'struct':struct,'APEX':1613031,'BOUNDARY':871731,'FACES':((0,2,1),(0,1,3),(1,2,3),(2,0,3))};ns.update(MSH_SHA='m'*64,FIRST='census.json',DEVIATION='deviation.json',FIXED_INPUTS={'census.json':'c'*64,'deviation.json':'d'*64});names=['parameter_projection','canonical','validate_interface','face_hits','selection_records','current_after_proof']
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
 mapping=list(range(1,6))+list(range(900000,900004));apex=1613031
 def point(tag,local):
  xyz=[float(local),0.,-0.]
  return dict(node_tag=tag,coordinates_mm=xyz,binary64_hex=[x.hex() for x in xyz])
 points=[point(t,i) for i,t in enumerate(mapping+[apex],1)];lookup={r['node_tag']:r for r in points}
 triples=list(combinations(mapping,3))[:14]
 cells=[dict(tetrahedron_tag=1000+i,native_array_index=i,node_tags=[apex,*face]) for i,face in enumerate(triples)]
 vertices=[dict(local_node_tag=i,source_global_node_tag=t,coordinates_mm=lookup[t]['coordinates_mm'],binary64_hex=lookup[t]['binary64_hex'],binary64_little_endian_bytes_hex=struct.pack('<3d',*lookup[t]['coordinates_mm']).hex(),original_source_boundary_node=t<=871731) for i,t in enumerate(mapping,1)]
 faces=[dict(local_node_tags=[mapping.index(t)+1 for t in face],source_global_node_tags=list(face),source_owner_tetrahedron_tag=1000+i,source_native_array_index=i,native_corner_indices=[1,2,3]) for i,face in enumerate(triples)]
 observation=dict(apex=apex,source_census_sha256='c'*64,original_parent_MSH_sha256='m'*64,upstream_census_launch_deviation_sha256='d'*64,declared_controller_command_conformant=False,native_ordered_cell_rows=cells,selected_node_rows=points)
 shell=dict(upstream_census_launch_deviation_sha256='d'*64,declared_controller_command_conformant=False,excluded_source_apex_tag=apex,apex_not_in_shell_input=True,necessary_face_quality_passed=True,generation_input_rejected_by_necessary_face_quality=False,local_to_global_node_tags=mapping,global_to_local_node_tags={str(t):i for i,t in enumerate(mapping,1)},original_source_classifications=dict(boundary_global_node_tags=mapping[:5],other_interior_global_node_tags=mapping[5:]),vertex_rows=vertices,oriented_triangle_rows=faces)
 return observation,shell
obs,shell=synthetic_selection();answer=ns['selection_records'](obs,shell)
assert len(answer[0])==14 and len(answer[1])==10 and len(answer[2])==9 and len(answer[3])==14 and len(answer[4])==5
for category in ['apex','inverse','bytes','classification','owner','winding','missing_face','old32map','deviation','parent']:
 o,b=copy.deepcopy(obs),copy.deepcopy(shell)
 if category=='apex':o['apex']=1435493
 elif category=='inverse':b['global_to_local_node_tags'][str(b['local_to_global_node_tags'][0])]=2
 elif category=='bytes':b['vertex_rows'][0]['binary64_little_endian_bytes_hex']='00'*24
 elif category=='classification':b['original_source_classifications']['boundary_global_node_tags']=b['local_to_global_node_tags']
 elif category=='owner':b['oriented_triangle_rows'][0]['source_owner_tetrahedron_tag']=999
 elif category=='winding':b['oriented_triangle_rows'][0]['local_node_tags'].reverse()
 elif category=='missing_face':b['oriented_triangle_rows'].pop()
 elif category=='old32map':b['local_to_global_node_tags']=list(range(1,33))
 elif category=='deviation':o['declared_controller_command_conformant']=True
 elif category=='parent':o['original_parent_MSH_sha256']='old'
 try:ns['selection_records'](o,b)
 except ValueError:pass
 else:raise AssertionError('Expected specific current14/9 selection refusal: '+category)
# Mock only the two unchanged donor proof calls; this tests the new current-census join.
ns.update(MSH_SHA='m'*64,WORKER='current.json',FIRST='census.json',FIRST_CONTRACT='prior.json',FIRST_ACTUAL='actual.json',CENSUS_PEER='peer.json',CENSUS_BINDINGS='bindings.json',DEVIATION='deviation.json',FIXED_INPUTS={'current.json':'w'*64,'census.json':'c'*64,'prior.json':'x'*64,'actual.json':'x'*64,'peer.json':'p'*64,'bindings.json':'b'*64,'deviation.json':'d'*64})
proof=dict(array_sha256s={'sorted_coordinates_sha256':'a'*64},classifications={});calls=[]
helpers=dict(partial_after_proof=lambda *args:proof,require_after_match=lambda first,observed,total:calls.append(total))
prior=dict(MSH_sha256='m'*64,MSH_bytes=235786462,partial_report_sha256='w'*64,expected_positive_poor_total=127)
first=dict(status='direct_saved_file_readback_completed',bound_inputs_unchanged=True,single_partial_replacement_saved_proof=dict(report_sha256='w'*64,field='after',after_equals_saved_reopen=True,independent_prior_reader_alias_used=False,old210_bins_reused=False),sorted_coordinates_sha256='a'*64,direct_fresh_classifications={})
flags=['engineering_accepted','head_edit_authorized','head_PDE_authorized','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized','automatic_retry']
peer=dict(schema='962-current127-census-independent-stopped-saved-review/v1',decision='CLEAR_COMPLETED_READ_ONLY_CENSUS_SAVED_ASSOCIATIONS_ONLY',bindings=dict(path='bindings.json',sha256='b'*64,bytes=1),checked=dict(d60_false_conformance_preserved=True),blockers=[],**{k:False for k in flags})
bindings=dict(schema='962-current127-census-saved-result-bindings/v1',outputs={'readback-report.json':dict(path='census.json',sha256='c'*64,bytes=1),'frozen-contract.json':dict(path='prior.json',sha256='x'*64,bytes=1)},selected_control_records={'actual':dict(path='actual.json',sha256='x'*64,bytes=1)},source_proof=dict(path='current.json',sha256='w'*64,bytes=1))
accept=dict(schema='962-current127-census-root-stopped-peer-acceptance/v1',decision='ACCEPT_COMPLETED_READ_ONLY_CENSUS_SAVED_ASSOCIATIONS_ONLY',peer=dict(path='peer.json',sha256='p'*64,bytes=1),bindings=copy.deepcopy(peer['bindings']),report=copy.deepcopy(bindings['outputs']['readback-report.json']),upstream_d60_command_conformance=False,positive_poor=127,nodes=1097222,TET4=3621771,**{k:False for k in ['whole_head_quality_accepted','stronger_Mesh2_criterion_passed','geometry_repair_feasibility_proved','head_PDE_authorized','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized','automatic_retry']})
assert ns['current_after_proof']({}, {},{},first,prior,peer,bindings,accept,helpers) is proof and calls==[127]
for category in ['old_count','mesh','optimizer_alias','arrays','classes','accepted_head','deviation','peer_body','report_body','actual_body','legacy_peer_schema','bindings_body']:
 f,p,e,b,a=copy.deepcopy(first),copy.deepcopy(prior),copy.deepcopy(peer),copy.deepcopy(bindings),copy.deepcopy(accept)
 if category=='old_count':p['expected_positive_poor_total']=129
 elif category=='mesh':p['MSH_sha256']='old'
 elif category=='optimizer_alias':f['single_partial_replacement_saved_proof']={'worker_report_sha256':'w'*64,'field':'after'}
 elif category=='arrays':f['sorted_coordinates_sha256']='old'
 elif category=='classes':f['direct_fresh_classifications']={'changed':True}
 elif category=='accepted_head':e['head_edit_authorized']=True
 elif category=='deviation':a['upstream_d60_command_conformance']=True
 elif category=='peer_body':a['peer']['sha256']='old'
 elif category=='report_body':b['outputs']['readback-report.json']['sha256']='old'
 elif category=='actual_body':b['selected_control_records']['actual']['sha256']='old'
 elif category=='legacy_peer_schema':e={'decision':'CLEAR_COMPLETED_SAVED_CENSUS_ASSOCIATIONS_WITH_DISCLOSED_CONTROLLER_COMMAND_DEVIATION','key_records':[]}
 elif category=='bindings_body':a['bindings']['sha256']='old'
 try:ns['current_after_proof']({}, {},{},f,p,e,b,a,helpers)
 except ValueError:pass
 else:raise AssertionError('Expected current partial proof refusal: '+category)
# Exact reused projection excludes coordinate words intentionally: those are separately retained.
row=dict(dimension=3,entity_tag=1,count=4,parameter_width=0,node_tags_u64_sha256='n'*64,available_parameter_words_f64_sha256='e'*64,coordinate_words_f64_sha256='x'*64)
keys=['dimension','entity_tag','count','parameter_width','node_tags_u64_sha256','available_parameter_words_f64_sha256']
assert ns['parameter_projection']([row])==[{k:row[k] for k in keys}]
bad=dict(row);del bad['parameter_width']
try:ns['parameter_projection']([bad])
except KeyError:pass
else:raise AssertionError('Missing original parameter field refused')
# Static boundaries retain exact controller and selected helper identities; no prepared native body runs.
root=Path(__file__).resolve().parents[3]
assert hashlib.sha256(source.with_name('run_readback.py').read_bytes()).hexdigest()=='4fb37080e1f3847b8b1d14d5df467799d8e9f7bf81b0a09170e5850857de3943'
new_defs={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
for donor,names in [('work/962-engineering/direct-sicn-apex1474426-head-context-prep-001/reader.py',['sha','canonical','json_sha','validate_interface','face_hits','selected_functions']),('work/962-engineering/head-star-current204-union-context-prep-002/reader.py',['parameter_projection'])]:
 donor_defs={n.name:n for n in ast.parse((root/donor).read_text()).body if isinstance(n,ast.FunctionDef)}
 for name in names:assert ast.dump(new_defs[name],include_attributes=False)==ast.dump(donor_defs[name],include_attributes=False)
print(json.dumps({'status':'pass','groups':4,'scope':'Interface/refusal, original14/10/9 map, current127 descriptor proof/d60, original-parameter and static source boundaries. Synthetic metadata only; no NumPy, Gmsh or head query.'}))
