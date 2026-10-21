"""Four UNRUN stdlib glue guards; synthetic rows are not native evidence."""
import hashlib
import importlib.util
from pathlib import Path
import struct

SOURCE=Path(__file__).with_name('extract_shell.py')
SOURCE_SHA='49cf077be7ede9b145910597d032a58e5462c240fa8d378e40b86bf4e1a9dbcd'


def main():
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
 spec=importlib.util.spec_from_file_location('held_original60_extractor',SOURCE)
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
 print('4 stdlib glue guards PASS; no real census/extraction/native/meshing input exercised')


if __name__=='__main__':main()
