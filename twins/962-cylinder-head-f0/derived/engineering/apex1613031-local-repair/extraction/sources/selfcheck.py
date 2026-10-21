"""Five UNRUN stdlib glue guards; synthetic rows are not native evidence."""
import hashlib
import importlib.util
from pathlib import Path
import struct

SOURCE=Path(__file__).with_name('extract_shell.py')
SOURCE_SHA='a223996f23975912bdfb03590af5550fe2f92fbaf6a1b1b58fb488f2508cffbe'


def main():
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
 spec=importlib.util.spec_from_file_location('held_current127_14_extractor',SOURCE)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m) # stdlib-only top level
 for path in [m.EXACT_SOURCE,m.INCIDENCE_SOURCE,m.FACE_SOURCE,m.PROOF_SOURCE]:
  assert m.sha(m.ROOT/path)==m.PINS[path]
 h=m.load_helpers()
 def fixture(height=1.):
  xyz={10:[0.,-0.,0.],20:[1.,0.,0.],30:[0.,height,0.],1000000:[0.,0.,1.],m.APEX:[.25,height/4,.25]}
  faces=[[10,30,20],[10,20,1000000],[20,30,1000000],[30,10,1000000]]
  cells=[dict(tetrahedron_tag=100+i,native_array_index=i,node_tags=[m.APEX]+f,initial_native_SICN=.2,
   initially_positive_poor=False,movable_node_tags=[m.APEX]) for i,f in enumerate(faces)]
  nodes={t:dict(node_tag=t,coordinates_mm=p,binary64_hex=[x.hex() for x in p],source_boundary_tag=t<=871731,
   freshly_proved_classification_scope='below_dim3' if t<=871731 else 'dim3',in_movable_seed_set=t==m.APEX) for t,p in xyz.items()}
  return cells,nodes
 def refused(call):
  try:call()
  except ValueError:return
  raise AssertionError('Expected precise malformed/topology refusal')

 # Measured sizes, inverse sparse map, exact unit volume and original/temporary classes.
 cells,nodes=fixture();observation,shell,screen=m.build_records(h,cells,nodes)
 assert shell['vertices']==4 and shell['oriented_triangles']==4
 assert observation['outer_surface']['Euler']==2 and observation['outer_surface']['all_vertex_links_single_cycles']
 assert observation['exact_volume_mm3']==h.rational(m.Fraction(1,6))
 assert shell['local_to_global_node_tags']==[10,20,30,1000000]
 assert shell['global_to_local_node_tags']=={'10':1,'20':2,'30':3,'1000000':4}
 assert shell['original_source_classifications']['other_interior_local_node_tags']==[4]
 assert all(r['prospective_cavity_fixed'] for r in shell['vertex_rows'])
 assert shell['vertex_rows'][0]['binary64_little_endian_bytes_hex']==struct.pack('<3d',0.,-0.,0.).hex()

 # An omitted incident cell, duplicate TET or reversed owner cannot become a valid shell.
 refused(lambda:m.build_records(h,cells[:-1],nodes))
 refused(lambda:m.build_records(h,cells+[dict(cells[0],tetrahedron_tag=999)],nodes))
 reversed_cells=[dict(r) for r in cells];reversed_cells[0]['node_tags']=list(reversed(cells[0]['node_tags'][:2]))+cells[0]['node_tags'][2:]
 refused(lambda:m.build_records(h,reversed_cells,nodes))

 # Loose non-certificate is not tight compatibility: exact dyadic triangle between thresholds.
 cert=h.certificate([[0.,0.,0.],[1.,0.,0.],[0.,5./128.,0.]])
 q=cert['exact_triangle_SICN_squared'];q2=m.Fraction(int(q['numerator']),int(q['denominator']))
 assert cert['no_positive_linear_tetrahedron_with_this_fixed_face_can_reach_SICN_point1'] is False
 assert m.Fraction(4,900)<q2<m.Fraction(4,841)

 # Complete negative screens retain every source/shell/face row; held cannot authorize execution.
 cells,nodes=fixture(5./128.);observation,shell,screen=m.build_records(h,cells,nodes)
 assert len(observation['native_ordered_cell_rows'])==4 and len(observation['selected_node_rows'])==5
 assert len(shell['oriented_triangle_rows'])==len(screen['all_rows'])==4
 assert screen['counts']['below']>0 and not screen['all_necessary_point1_face_bounds_passed']
 assert shell['status']=='DATA_ONLY_REJECTED_FIXED_SHELL_FACE_QUALITY'
 assert shell['generation_input_rejected_by_necessary_face_quality'] and shell['execution_authorized'] is False
 refused(lambda:m.require_authority({'diagnostic_execution_authorized':False}))
 # Current127 binding guard uses the real ten-record schema, with mocked prior proof only.
 # The four earlier geometry guards above remain exact; this checks caller refusal/selection.
 from copy import deepcopy
 from types import SimpleNamespace
 cells,nodes=fixture()
 for i,tag in enumerate([40,50,1000001,1000002,1000003],1):
  point=[i/8.,i/16.,.5]
  nodes[tag]=dict(node_tag=tag,coordinates_mm=point,binary64_hex=[x.hex() for x in point],source_boundary_tag=tag<=871731,
   freshly_proved_classification_scope='below_dim3' if tag<=871731 else 'dim3',in_movable_seed_set=tag==1000000)
 corners=[10,20,30,1000000,40,50,1000001,1000002,1000003]
 selected=[]
 for i in range(14):
  row=[m.APEX]+[corners[(i+j)%9] for j in range(3)]
  selected.append(dict(tetrahedron_tag=100+i,native_array_index=i,node_tags=row,initial_native_SICN=.05 if i==0 else .2,
   initially_positive_poor=i==0,movable_node_tags=[m.APEX]+([1000000] if 1000000 in row else [])))
 filler=[dict(tetrahedron_tag=1000+i,native_array_index=100+i,node_tags=[40,50,60,70],
  initial_native_SICN=.2,initially_positive_poor=False,movable_node_tags=[2000000]) for i in range(3137-14)]
 arrays={k:k+'-value' for k in ['sorted_node_tags_sha256','sorted_coordinates_sha256','sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256']}
 proof=dict(array_sha256s=arrays,classifications={'current':True},tetrahedra=3621771)
 fake=SimpleNamespace(partial_after_proof=lambda *args:proof,require_after_match=lambda *args:None)
 data={k:{} for k in [m.CENSUS,m.PRIOR,m.PARTIAL,m.RECEIPT,m.CLOSED,m.PEER,m.PEER_BINDINGS,m.CENSUS_ROOT,m.CENSUS_ACCEPT,m.LAUNCH_DEVIATION]}
 data[m.CENSUS]=dict(arrays,status='direct_saved_file_readback_completed',bound_inputs_unchanged=True,
  direct_fresh_classifications=proof['classifications'],declared_controller_command_conformant=False,upstream_census_launch_deviation_sha256=m.PINS[m.LAUNCH_DEVIATION],
  complete_seed_star_census=dict(complete_incident_tetrahedra=selected+filler,
   movable_count=101,movable_node_tags=sorted([m.APEX,1000000]+list(range(2000000,2000099))),all_seed_stars_complete_including_initially_good_and_shared_cells=True,
   per_movable_node_complete_incident_counts=[[m.APEX,14]],unique_incident_nodes=list(nodes.values())))
 data[m.PEER]=dict(decision='CLEAR_COMPLETED_READ_ONLY_CENSUS_SAVED_ASSOCIATIONS_ONLY',bindings={'sha256':m.PINS[m.PEER_BINDINGS]},checked={'d60_false_conformance_preserved':True})
 data[m.PEER_BINDINGS]=dict(outputs={'readback-report.json':{'sha256':m.PINS[m.CENSUS]}},selected_control_records={'actual':{'sha256':m.PINS[m.CENSUS_ACTUAL]}})
 data[m.CENSUS_ROOT]=dict(schema='962-current127-head-census-root-closed/v1',returncode=0,stop_reason=None,waited_and_reaped=True,
  owned_controller_group_observed_absent=True,all79inputs_runtime4_and_rootPython_before_after_exact=True,
  actual={'sha256':m.PINS[m.PRIOR]},output_files={'readback-report.json':{'sha256':m.PINS[m.CENSUS]}})
 data[m.CENSUS_ACCEPT]=dict(decision='ACCEPT_COMPLETED_READ_ONLY_CENSUS_SAVED_ASSOCIATIONS_ONLY',peer={'sha256':m.PINS[m.PEER]},
  bindings={'sha256':m.PINS[m.PEER_BINDINGS]},root_closed={'sha256':m.PINS[m.CENSUS_ROOT]},report={'sha256':m.PINS[m.CENSUS]},upstream_d60_command_conformance=False)
 data[m.LAUNCH_DEVIATION]=dict(actual_sha256='ec888011591b8eda74ae83a4a3e796d1ab6d2cf555d99fba1fbbc2c003fb215f',declared_controller_command_conformant=False)
 got,gotnodes=m.select_original(fake,data)
 assert got==selected and len(gotnodes)==10 and len(got)==14 and sum(r['initially_positive_poor'] for r in got)==1
 assert sum(r['source_boundary_tag'] for t,r in gotnodes.items() if t!=m.APEX)==5
 assert any(len(r['movable_node_tags'])>1 for r in got)
 bad=deepcopy(data);bad[m.CENSUS_ACCEPT]['upstream_d60_command_conformance']=True
 refused(lambda:m.select_original(fake,bad))
 bad=deepcopy(data);bad[m.PEER_BINDINGS]['selected_control_records']['actual']['sha256']='refused001-or-old-census-actual'
 refused(lambda:m.select_original(fake,bad))
 bad=deepcopy(data);bad[m.CENSUS]['complete_seed_star_census']['complete_incident_tetrahedra'][0]['node_tags']=[40,50,60,70]
 refused(lambda:m.select_original(fake,bad))
 bad=deepcopy(data);bad[m.CENSUS]['complete_seed_star_census']['complete_incident_tetrahedra'][2]['initially_positive_poor']=True
 refused(lambda:m.select_original(fake,bad))
 bad=deepcopy(data);bad[m.CENSUS]['complete_seed_star_census']['unique_incident_nodes'][0]['binary64_hex'][1]='0x0.0p+0'
 refused(lambda:m.select_original(fake,bad))
 bad=deepcopy(data);bad[m.CENSUS]['complete_seed_star_census']['unique_incident_nodes'].pop()
 refused(lambda:m.select_original(fake,bad))
 bad=deepcopy(data);bad[m.CENSUS]['complete_seed_star_census']['complete_incident_tetrahedra'][0]['native_array_index']=3621771
 refused(lambda:m.select_original(fake,bad))
 print('5 stdlib glue guards PASS; no real census/extraction/native/meshing input exercised')


if __name__=='__main__':main()
