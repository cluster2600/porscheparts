"""UNRUN synthetic stdlib guards; never read the actual census or run a batch."""
from copy import deepcopy
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest

SOURCE=Path(__file__).with_name('select_batch.py')
SOURCE_SHA='af388dd1a3ba5027c5c0b7a62295a2d8950b4789e0568e68f5451ab52a708350'


def module():
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
 spec=importlib.util.spec_from_file_location('held_current204_batch',SOURCE)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)  # stdlib top level only
 return m


def fixture(m,height=1.,apex=2000000):
 xyz={10:[0.,-0.,0.],20:[1.,0.,0.],30:[0.,height,0.],1000000:[0.,0.,1.],apex:[.25,height/4,.25]}
 faces=[[10,30,20],[10,20,1000000],[20,30,1000000],[30,10,1000000]]
 cells=[dict(tetrahedron_tag=100+i,native_array_index=i,node_tags=[apex]+face,initial_native_SICN=.2,
  initially_positive_poor=False,movable_node_tags=[apex]) for i,face in enumerate(faces)]
 nodes={t:dict(node_tag=t,coordinates_mm=p,binary64_hex=[v.hex() for v in p],source_boundary_tag=t<=871731,
  freshly_proved_classification_scope='below_dim3' if t<=871731 else 'dim3',in_movable_seed_set=t==apex) for t,p in xyz.items()}
 return cells,nodes


def tiny_census():
 seeds=[4,5];connectivity=[[1,2,3,4],[1,2,4,5],[2,4,6,7]];qualities=[.05,.07,.3]
 rows=[dict(tetrahedron_tag=101+i,native_array_index=i,node_tags=row,initial_native_SICN=q,
  initially_positive_poor=q<.1,movable_node_tags=sorted(set(row)&set(seeds))) for i,(row,q) in enumerate(zip(connectivity,qualities))]
 nodes=[dict(node_tag=t,coordinates_mm=[float(t),-0.,float(t+1)],binary64_hex=[float(t).hex(),(-0.).hex(),float(t+1).hex()],
  source_boundary_tag=t<=3,in_movable_seed_set=t in seeds,freshly_proved_classification_scope='below_dim3' if t<=3 else 'dim3') for t in range(1,8)]
 bynode={r['node_tag']:r for r in nodes}
 poor=[dict(tetrahedron_tag=r['tetrahedron_tag'],native_array_index=r['native_array_index'],node_tags=r['node_tags'],SICN=r['initial_native_SICN'],
  coordinates_mm=[bynode[t]['coordinates_mm'] for t in r['node_tags']],binary64_hex=[bynode[t]['binary64_hex'] for t in r['node_tags']],
  original_boundary_node_count=sum(t<=3 for t in r['node_tags']),interior_node_count=sum(t>3 for t in r['node_tags'])) for r in rows[:2]]
 arrays=[('movable_node_tags_u64','Q',seeds),('selected_tetrahedron_tags_u64','Q',[101,102,103]),
  ('selected_tetrahedron_connectivity_u64','Q',[t for row in connectivity for t in row]),('union_node_tags_u64','Q',list(range(1,8))),
  ('union_coordinates_f64','d',[v for r in nodes for v in r['coordinates_mm']]),('selected_initial_SICN_f64','d',qualities)]
 hashes={name:hashlib.sha256(struct.pack('<'+code*len(values),*values)).hexdigest() for name,code,values in arrays}
 star=dict(movable_node_tags=seeds,movable_count=2,prospective_coordinate_variables=6,complete_incident_tetrahedra=rows,
  complete_incident_tetrahedron_count=3,unique_incident_nodes=nodes,unique_incident_node_count=7,
  all_seed_stars_complete_including_initially_good_and_shared_cells=True,all_positive_poor_rows_covered_by_movable_stars=True,
  unseedable_positive_poor_tetrahedron_tags=[],positive_poor_tetrahedron_tags=[101,102],per_movable_node_complete_incident_counts=[[4,3],[5,1]],
  initially_positive_poor_incident_tetrahedra=2,initially_good_incident_tetrahedra=1,shared_by_multiple_movable_nodes_tetrahedra=1,
  unique_incident_boundary_node_count=3,unique_incident_other_interior_node_count=2,ordered_tagged_array_sha256s=hashes)
 return dict(complete_seed_star_census=star,positive_poor_SICN_cells=dict(total=2,complete_tagged_cells=poor,
  by_original_boundary_node_count={'0':0,'1':0,'2':1,'3':1,'4':0}))


class Guards(unittest.TestCase):
 def test_sparse_inverse_volume_words_and_classifications(self):
  m=module();delta=json.loads(SOURCE.with_name('source-delta.json').read_text())
  lines=SOURCE.read_text().splitlines(True)
  for row in reversed(delta['line_edits']):
   self.assertEqual(''.join(lines[row['new_start']:row['new_stop']]),row['new'])
   lines[row['new_start']:row['new_stop']]=row['old'].splitlines(True)
  donor=(m.ROOT/delta['preserved_source']).read_bytes()
  self.assertEqual(''.join(lines).encode(),donor)
  old={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(donor).body if isinstance(n,ast.FunctionDef)}
  new={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(SOURCE.read_bytes()).body if isinstance(n,ast.FunctionDef)}
  for name in delta['unchanged_copied_function_ASTs']:self.assertEqual(new[name],old[name])
  h=m.load_helpers();cells,nodes=fixture(m)
  observation,shell,screen=m.build_records(h,cells,nodes,2000000)
  self.assertEqual(shell['local_to_global_node_tags'],[10,20,30,1000000])
  self.assertEqual(shell['global_to_local_node_tags'],{'10':1,'20':2,'30':3,'1000000':4})
  self.assertEqual(observation['exact_volume_mm3'],h.rational(m.Fraction(1,6)))
  self.assertEqual(observation['outer_surface']['Euler'],2)
  self.assertEqual(shell['original_source_classifications']['other_interior_local_node_tags'],[4])
  self.assertEqual(shell['vertex_rows'][0]['binary64_little_endian_bytes_hex'],struct.pack('<3d',0.,-0.,0.).hex())
  self.assertEqual(observation['apex'],2000000)
  self.assertEqual(observation['original_parent_MSH_sha256'],m.CURRENT_MSH_SHA256)
  self.assertEqual(len(screen['all_rows']),4)

 def test_missing_duplicate_and_reversed_cell_refuse(self):
  m=module();h=m.load_helpers();cells,nodes=fixture(m)
  cases=[cells[:-1],cells+[dict(cells[0],tetrahedron_tag=999)]]
  reversed_rows=deepcopy(cells);r=reversed_rows[0]['node_tags'];r[0],r[1]=r[1],r[0];cases.append(reversed_rows)
  for rows in cases:
   with self.assertRaises(ValueError):m.build_records(h,rows,nodes,2000000)

 def test_tight_bound_and_complete_negative_screen(self):
  m=module();h=m.load_helpers();cert=h.certificate([[0.,0.,0.],[1.,0.,0.],[0.,5./128.,0.]])
  q=cert['exact_triangle_SICN_squared'];q2=m.Fraction(int(q['numerator']),int(q['denominator']))
  self.assertFalse(cert['no_positive_linear_tetrahedron_with_this_fixed_face_can_reach_SICN_point1'])
  self.assertTrue(m.Fraction(4,900)<q2<m.Fraction(4,841))
  cells,nodes=fixture(m,5./128.);observation,shell,screen=m.build_records(h,cells,nodes,2000000)
  self.assertEqual(len(observation['native_ordered_cell_rows']),4)
  self.assertEqual(len(screen['all_rows']),len(shell['oriented_triangle_rows']))
  self.assertGreater(screen['counts']['below'],0)
  self.assertFalse(screen['all_necessary_point1_face_bounds_passed'])
  self.assertFalse(shell['execution_authorized'])

 def test_greedy_poor_coverage_ties_and_full_vertex_conflicts(self):
  m=module()
  records=[dict(apex=30,poor_coverage=2,eligible=True,all_vertex_tags=[3,30]),
   dict(apex=20,poor_coverage=2,eligible=True,all_vertex_tags=[1,20]),
   dict(apex=10,poor_coverage=3,eligible=True,all_vertex_tags=[1,10]),
   dict(apex=50,poor_coverage=8,eligible=False,all_vertex_tags=[50,51]),
   dict(apex=40,poor_coverage=2,eligible=True,all_vertex_tags=[3,40])]
  selected,decisions=m.greedy_disjoint(records)
  self.assertEqual([r['apex'] for r in selected],[10,30])
  self.assertEqual([r['apex'] for r in decisions],[50,10,20,30,40])
  self.assertEqual(decisions[2]['conflicts_with_already_selected'],[{'selected_apex':10,'shared_vertex_tags':[1]}])
  self.assertEqual(decisions[-1]['conflicts_with_already_selected'],[{'selected_apex':30,'shared_vertex_tags':[3]}])
  self.assertEqual(decisions[0]['status'],'ineligible')
  self.assertEqual(m.greedy_disjoint([]),([],[]))
  with self.assertRaises(ValueError):m.greedy_disjoint(records+[records[0]])

 def test_complete_saved_rows_words_hashes_and_refusals(self):
  m=module();c=tiny_census();rows,nodes,seeds=m.census_rows(c,3,3)
  self.assertEqual(seeds,[4,5]);self.assertEqual(len(rows),3);self.assertEqual(len(nodes),7)
  mutations=[lambda x:x['complete_seed_star_census']['complete_incident_tetrahedra'][2].update(movable_node_tags=[]),
   lambda x:x['complete_seed_star_census']['unique_incident_nodes'][0]['coordinates_mm'].__setitem__(1,0.),
   lambda x:x['positive_poor_SICN_cells']['complete_tagged_cells'][0]['coordinates_mm'][0].__setitem__(1,0.),
   lambda x:x['complete_seed_star_census']['per_movable_node_complete_incident_counts'].__setitem__(0,[4,2]),
   lambda x:x['complete_seed_star_census']['ordered_tagged_array_sha256s'].update(selected_initial_SICN_f64='0'*64)]
  for mutate in mutations:
   bad=deepcopy(c);mutate(bad)
   with self.assertRaises(ValueError):m.census_rows(bad,3,3)

 def test_current_proof_schema_scope_and_root_peer_joins(self):
  m=module();proof=dict(array_sha256s={'a':'A'},classifications={'class':'identity'})
  census=dict(status='direct_saved_file_readback_completed',bound_inputs_unchanged=True,a='A',direct_fresh_classifications={'class':'identity'},
   complete_seed_star_census=dict(schema='962-complete-current-poor-seed-stars/v1',movable_count=154,complete_incident_tetrahedron_count=5267,unique_incident_node_count=2905),
   positive_poor_SICN_cells={'total':204})
  prior={'MSH_sha256':m.CURRENT_MSH_SHA256}
  receipt=dict(returncode=0,stop_reason=None,readback_report_sha256=m.PINS[m.CENSUS],contract_sha256=m.PINS[m.PRIOR])
  closed=dict(returncode=0,stop_reason=None,wait_reaped=True,all72_inputs_unchanged=True,all4_selected_runtime_unchanged=True,actual_unchanged=True,materialized_actual_copy_unchanged=True,
   actual_sha256=m.PINS[m.PRIOR],outputs={'readback-report.json':{'sha256':m.PINS[m.CENSUS]},'execution-receipt.json':{'sha256':m.PINS[m.CENSUS_RECEIPT]}})
  root=dict(decision='CLEAR_COMPLETED_READ_ONLY_CENSUS_KEEP_STRICT_HEAD_REJECTION',report_sha256=m.PINS[m.CENSUS],closed_sha256=m.PINS[m.CENSUS_CLOSED])
  peer=dict(decision=m.PEER_DECISION,records={'worker_report':{'sha256':m.PINS[m.CENSUS]},'actual':{'sha256':m.PINS[m.PRIOR]},'root_closed':{'sha256':m.PINS[m.CENSUS_CLOSED]}})
  data=dict(zip([m.CENSUS,m.PRIOR,m.PARTIAL,m.RECEIPT,m.CLOSED,m.CENSUS_RECEIPT,m.CENSUS_CLOSED,m.CENSUS_ROOT,m.PEER],[census,prior,{}, {}, {},receipt,closed,root,peer]))
  helper=SimpleNamespace(partial_after_proof=lambda *args:proof,require_after_match=lambda r,p,n:self.assertEqual(n,204))
  self.assertEqual(m.current_proof(helper,data),census)
  for path,field,value in [(m.PRIOR,'MSH_sha256','old'),(m.CENSUS_CLOSED,'all72_inputs_unchanged',False),(m.PEER,'decision','pending'),(m.CENSUS_RECEIPT,'stop_reason','deadline')]:
   bad=deepcopy(data);bad[path][field]=value
   with self.assertRaises(ValueError):m.current_proof(helper,bad)

 def test_held_cannot_authorize_native_or_saved_query(self):
  m=module()
  c=dict(schema='962-current204-batch-shell-selection-actual/v1',diagnostic_execution_authorized=True,root_and_peer_review_complete=True,
   automatic_retry=False,method='all_current_seed_stars_exact_shells_then_vertex_disjoint_greedy',output_directory=m.OUTPUT,**{k:False for k in m.FORBIDDEN})
  m.require_authority(c)
  for field,value in [('diagnostic_execution_authorized',False),('native_execution_authorized',True),('generation_authorized',True),('automatic_retry',True),('output_directory','old')]:
   bad=dict(c);bad[field]=value
   with self.assertRaises(ValueError):m.require_authority(bad)


if __name__=='__main__':unittest.main()
