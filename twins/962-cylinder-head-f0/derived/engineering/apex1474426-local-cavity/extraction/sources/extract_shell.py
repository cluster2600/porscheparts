"""HELD saved-JSON extraction of original apex1474426 star; no native or meshing calls."""
import ast
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = 'work/962-engineering/direct-sicn-apex1474426-cavity-study-001'
APEX = 1474426
FACES = ((0,2,1),(0,1,3),(1,2,3),(2,0,3))
CENSUS = 'work/962-engineering/head-star-remaining-full-stars-001/readback-report.json'
PRIOR = 'work/962-engineering/head-star-remaining-full-stars-001/frozen-contract.json'
PARTIAL = 'work/962-engineering/head-star-replacement-001/readback-report.json'
RECEIPT = 'work/962-engineering/head-star-replacement-001/execution-receipt.json'
CLOSED = 'work/962-engineering/head-star-replacement-root-execution-001/closed-result.json'
PEER = 'work/962-engineering/head-star-remaining-full-stars-result-peer-001/review.json'
DIAGNOSIS = 'work/962-engineering/head-star-remaining-sicn-proposer-saved-diagnosis-001/report.json'
GRAPH = 'work/962-engineering/head-star-remaining-sicn-proposer-saved-diagnosis-root-review-001/review.json'
TRIAL = 'work/962-engineering/head-star-remaining-sicn-proposer-root-execution-001/closed-result.json'
TRIAL_REVIEW = 'work/962-engineering/head-star-remaining-sicn-proposer-root-execution-001/result-review.json'
PROOF_SOURCE = 'work/962-engineering/head-star-remaining-full-stars-prep-001/reader.py'
EXACT_SOURCE = 'work/962-engineering/fixed-shell-coupled-embedding-prep-001/check_embedding.py'
INCIDENCE_SOURCE = 'work/962-engineering/domain-equivalence-prep-001/certify_domain.py'
FACE_SOURCE = 'twins/962-cylinder-head-f0/source/certify_fixed_face.py'
PINS = {
 CENSUS:'e43e2de37512feef3c880a7e8ca5d2db39ecf147708de6e2e04bd8030fda5b68',
 PRIOR:'58bff7528882916674457ac1b3a631fa49f1512f7e464d69633f6ef205d0cb25',
 PARTIAL:'780937d788385cf2a227db6c2cec308474b9fcca32375f868d39bc74ae80429b',
 RECEIPT:'aeb4597e001ce6a68e20b90e961036719139c3225451a2dbfbabe151b7f5d67f',
 CLOSED:'f99279040e88822c910ff6d7d56249125d2dce98d32d088f856428862dde9ae4',
 PEER:'039e9cc8e970a0d7bd44869f3d0fab6d6168fffe086c12951d8efe753b987573',
 DIAGNOSIS:'bb4be97fa06520393df5c96a41da37478c13655ac93e632ce17bd22843c2da7f',
 GRAPH:'424e1161c67016f19b832114e21571e8d84d5e0a4cd08a986f239a1e351214c8',
 TRIAL:'97e28c126329aae326493157e1049984704eb4d0b52017672e588514673cae21',
 TRIAL_REVIEW:'622b22baea8328e35a7d87a3c07c140df9cc31fa7907e514ffb9a5c980769b1a',
 PROOF_SOURCE:'afcad55f5e716b90ff4bac39cee4268101a21c4bbd9078f950b9bf372948a05d',
 EXACT_SOURCE:'1b489cc8149f4b5db8f90c594e32fe4c09b5db00151df6b1cfc88362d1018134',
 INCIDENCE_SOURCE:'0fe593d385e5a0ab4944528fa1b869ddf2c41c28d050576afe9be18213462296',
 FACE_SOURCE:'9b13f4dc7f2eca7da04e1587eb1f59a379a0d0c2101026f9b1d999ae09aaebb8',
}
FORBIDDEN = ['native_execution_authorized','generation_authorized','optimization_authorized',
 'head_edit_authorized','stitching_authorized','engineering_accepted','physics_qualified','manufacturing_authorized']


def sha(path):
 return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_helpers():
 ns = dict(Fraction=Fraction,math=math,FACES=FACES)
 groups = [(EXACT_SOURCE,['rational','subtract','dot','cross','exact_quality']),
           (INCIDENCE_SOURCE,['cycle','complex_rows']), (FACE_SOURCE,['certificate']),
           (PROOF_SOURCE,['partial_after_proof','require_after_match'])]
 for path,names in groups:
  tree=ast.parse((ROOT/path).read_text());selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
  if {n.name for n in selected}!=set(names):raise ValueError('Frozen helper definition missing')
  exec(compile(ast.Module(body=selected,type_ignores=[]),path,'exec'),ns)
 return SimpleNamespace(**ns)


def verify_pins(pins):
 if any(pins.get(k)!=v for k,v in PINS.items()):raise ValueError('Every consumed original/helper must be directly pinned')
 for name,digest in pins.items():
  p=ROOT/name
  if Path(name).is_absolute() or p.is_symlink() or not p.resolve().is_relative_to(ROOT) or sha(p)!=digest:
   raise ValueError('Input drift: '+name)


def require_authority(c):
 if (c.get('schema')!='962-apex1474426-cavity-extraction-actual/v1'
     or c.get('diagnostic_execution_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or any(c.get(k) is not False for k in FORBIDDEN) or c.get('automatic_retry') is not False
     or c.get('method')!='original60_star_exact_shell_and_necessary_face_screen'
     or c.get('output_directory')!=OUTPUT):raise ValueError('One reviewed data-only extraction authority required')


def select_original(h,data):
 census,prior,partial,receipt,closed,peer,diagnosis,graph,trial,trial_review=[data[k] for k in
  [CENSUS,PRIOR,PARTIAL,RECEIPT,CLOSED,PEER,DIAGNOSIS,GRAPH,TRIAL,TRIAL_REVIEW]]
 proof=h.partial_after_proof(partial,receipt,closed,prior);h.require_after_match(census,proof,208)
 if (census.get('status')!='direct_saved_file_readback_completed' or census.get('bound_inputs_unchanged') is not True
     or {k:census[k] for k in proof['array_sha256s']}!=proof['array_sha256s']
     or census['direct_fresh_classifications']!=proof['classifications']
     or peer.get('decision')!='CLEAR_COMPLETED_READ_ONLY_CURRENT208_CENSUS_MESH_REMAINS_REJECTED'
     or peer['bindings']['report']['sha256']!=PINS[CENSUS] or peer['bindings']['actual_sha256']!=PINS[PRIOR]
     or graph.get('status')!='PASS_SAVED_DATA_SCOPE_ONLY' or graph['report_sha256']!=PINS[DIAGNOSIS]
     or trial.get('returncode')!=2 or trial.get('stop_reason') is not None or trial.get('wait_reaped') is not True
     or trial_review.get('root_closed_sha256')!=PINS[TRIAL] or trial_review.get('current_head_MSH_unchanged') is not True
     or trial_review['current_head_MSH_sha256']!=prior['MSH_sha256']):raise ValueError('Current stopped proof/graph associations changed')
 star=census['complete_seed_star_census'];all_rows=star['complete_incident_tetrahedra']
 if (len(all_rows)!=5327 or star['movable_count']!=155 or star['all_seed_stars_complete_including_initially_good_and_shared_cells'] is not True
     or dict(star['per_movable_node_complete_incident_counts']).get(APEX)!=60):raise ValueError('Complete current60-star census attestation required')
 selected=[r for r in all_rows if APEX in r['node_tags']]
 if (len(selected)!=60 or [r['tetrahedron_tag'] for r in selected]!=sorted({r['tetrahedron_tag'] for r in selected})
     or len({r['native_array_index'] for r in selected})!=60
     or any(r['movable_node_tags']!=[APEX] or type(r['native_array_index']) is not int or not 0<=r['native_array_index']<3620820 or len(r['node_tags'])!=4
            or len(set(r['node_tags']))!=4 or not math.isfinite(r['initial_native_SICN']) or r['initial_native_SICN']<=0 for r in selected)):
  raise ValueError('All60 unique original native-ordered cells and singleton selected seed required')
 floor=diagnosis['floor_component']
 want=[dict(tetrahedron_tag=r['tetrahedron_tag'],native_array_index=r['native_array_index'],node_tags=r['node_tags'],initial_native_SICN=r['initial_native_SICN']) for r in selected]
 got=[dict(tetrahedron_tag=r['tetrahedron_tag'],native_array_index=r['source_native_array_index_zero_based'],node_tags=r['native_ordered_node_tags'],initial_native_SICN=r['initial_native_SICN']) for r in floor['all60_native_ordered_rows']]
 if floor['seed_tags']!=[APEX] or floor['singleton_in_selected_seed_graph'] is not True or want!=got:
  raise ValueError('Exact stopped saved graph/tag/native/corner links required')
 needed={t for r in selected for t in r['node_tags']};nodes={r['node_tag']:r for r in star['unique_incident_nodes'] if r['node_tag'] in needed}
 if set(nodes)!=needed or nodes[APEX]['source_boundary_tag'] is not False:raise ValueError('All original source nodes including interior apex required')
 for t,r in nodes.items():
  xyz=r['coordinates_mm'];boundary=t<=871731
  if (len(xyz)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in xyz)
      or [float(x).hex() for x in xyz]!=r['binary64_hex'] or r['source_boundary_tag'] is not boundary
      or r['freshly_proved_classification_scope']!=('below_dim3' if boundary else 'dim3')):
   raise ValueError('Original coordinate/hex/classification association changed')
 return selected,nodes


def shell_faces(h,cells,apex):
 if not cells or len({tuple(sorted(r)) for r in cells.values()})!=len(cells):raise ValueError('Unique complete old TET4 rows required')
 owners=defaultdict(list)
 for tag,row in sorted(cells.items()):
  if len(row)!=4 or len(set(row))!=4 or apex not in row:raise ValueError('Every source cell must contain its one apex')
  for pattern in FACES:
   face=[row[i] for i in pattern];owners[tuple(sorted(face))].append(dict(source_owner_tetrahedron_tag=tag,global_node_tags=face,native_corner_indices=list(pattern)))
 outer=[]
 for key,rows in sorted(owners.items()):
  if len(rows)==1:
   if apex in key:raise ValueError('Incomplete star leaves an exposed apex face')
   outer.append(rows[0])
  elif len(rows)!=2 or h.cycle(rows[0]['global_node_tags'])!=h.cycle(list(reversed(rows[1]['global_node_tags']))):
   raise ValueError('Complete opposite internal-face pairing required')
 return outer


def shell_topology(faces):
 edges=defaultdict(list);links=defaultdict(list);adj=defaultdict(set)
 for face in faces:
  for i,a in enumerate(face):
   b=face[(i+1)%3];edges[tuple(sorted((a,b)))].append((a,b));adj[a].add(b);adj[b].add(a)
   links[a].append([face[(i+1)%3],face[(i+2)%3]])
 if not faces or any(len(v)!=2 or v[0]!=v[1][::-1] for v in edges.values()):raise ValueError('Closed oppositely oriented shell edges required')
 def connected(graph):
  seen=set();todo=[next(iter(graph))]
  while todo:
   x=todo.pop()
   if x not in seen:seen.add(x);todo.extend(graph[x]-seen)
  return len(seen)==len(graph)
 if not connected(adj) or len(adj)-len(edges)+len(faces)!=2:raise ValueError('One connected Euler2 shell required')
 for rows in links.values():
  graph=defaultdict(set);degrees=Counter()
  for a,b in rows:graph[a].add(b);graph[b].add(a);degrees.update([a,b])
  if any(v!=2 for v in degrees.values()) or not connected(graph):raise ValueError('Every shell vertex link must be one cycle')
 return dict(vertices=len(adj),edges=len(edges),oriented_triangles=len(faces),components=1,Euler=2,all_vertex_links_single_cycles=True)


def build_records(h,selected,nodes):
 cells={r['tetrahedron_tag']:r['node_tags'] for r in selected};index={r['tetrahedron_tag']:r['native_array_index'] for r in selected}
 outer=shell_faces(h,cells,APEX);faces=[r['global_node_tags'] for r in outer];topology=shell_topology(faces)
 fixed=sorted({t for row in faces for t in row})
 if set(nodes)!=set(fixed+[APEX]):raise ValueError('All non-apex star nodes must occur on the prospective shell')
 points={t:tuple(Fraction.from_float(float(x)) for x in r['coordinates_mm']) for t,r in nodes.items()}
 complex_report,volume=h.complex_rows(h,points,cells,faces)
 shell_volume=sum((h.dot(points[f[0]],h.cross(points[f[1]],points[f[2]]))/6 for f in faces),Fraction(0))
 if volume<=0 or shell_volume!=volume:raise ValueError('Exact positive old-cell and oriented-shell volumes must agree')
 inverse={t:i+1 for i,t in enumerate(fixed)};vertex_rows=[]
 for t in fixed:
  r=nodes[t];xyz=r['coordinates_mm']
  vertex_rows.append(dict(local_node_tag=inverse[t],source_global_node_tag=t,coordinates_mm=xyz,binary64_hex=r['binary64_hex'],
   binary64_little_endian_bytes_hex=struct.pack('<3d',*xyz).hex(),original_source_boundary_node=r['source_boundary_tag'],
   original_source_classification=r['freshly_proved_classification_scope'],prospective_cavity_fixed=True))
 triangle_rows=[];screen_rows=[]
 for i,row in enumerate(outer,1):
  face=row['global_node_tags'];xyz=[nodes[t]['coordinates_mm'] for t in face];cert=h.certificate(xyz)
  q=cert['exact_triangle_SICN_squared'];q2=Fraction(int(q['numerator']),int(q['denominator']));threshold=Fraction(4,841)
  triangle_rows.append(dict(local_face_id=i,local_node_tags=[inverse[t] for t in face],source_global_node_tags=face,
   source_owner_tetrahedron_tag=row['source_owner_tetrahedron_tag'],source_native_array_index=index[row['source_owner_tetrahedron_tag']],native_corner_indices=row['native_corner_indices']))
  screen_rows.append(dict(local_face_id=i,source_global_node_tags=face,coordinates_mm=xyz,binary64_hex=[nodes[t]['binary64_hex'] for t in face],
   exact_fixed_face_certificate=cert,exact_triangle_SICN_squared=q,exact_threshold_squared=h.rational(threshold),
   strictly_above=q2>threshold,equal=q2==threshold,below=q2<threshold,necessary_point1_face_bound_passed=q2>=threshold))
 counts={name:sum(r[name] for r in screen_rows) for name in ['strictly_above','equal','below']};passed=counts['below']==0
 boundary=[t for t in fixed if nodes[t]['source_boundary_tag']];interior=[t for t in fixed if not nodes[t]['source_boundary_tag']]
 observation=dict(schema='962-original60-star-saved-observation/v1',apex=APEX,source_census_sha256=PINS[CENSUS],
  original_parent_MSH_sha256='9d85bbd0f762aebe07d96fad9618f2d7b8992ae29d288c8ba1829dc0481cc895',
  global_completeness_attribution='Frozen executed current census only; all60 retained rows selected here, no fresh full-MSH incidence query.',
  native_ordered_cell_rows=selected,selected_node_rows=[dict(nodes[t],binary64_little_endian_bytes_hex=struct.pack('<3d',*nodes[t]['coordinates_mm']).hex()) for t in sorted(nodes)],
  tetrahedral_complex=complex_report,outer_surface=dict(topology,oriented_source_owner_rows=outer),exact_volume_mm3=h.rational(volume),
  original_source_classifications=dict(boundary_global_node_tags=boundary,other_interior_global_node_tags=interior),
  exact_old_cells_required_positive_but_not_quality_point1=True,embedding_domain_and_external_owner_checks_performed=False)
 shell=dict(schema='962-fixed-cavity-local-shell-input/v1',status='DATA_ONLY_HELD' if passed else 'DATA_ONLY_REJECTED_FIXED_SHELL_FACE_QUALITY',
  units='mm',frame='Unchanged original census frame; no OEM datum qualification',excluded_source_apex_tag=APEX,apex_not_in_shell_input=True,
  vertices=len(fixed),oriented_triangles=len(faces),local_to_global_node_tags=fixed,global_to_local_node_tags={str(t):inverse[t] for t in fixed},
  vertex_rows=vertex_rows,oriented_triangle_rows=triangle_rows,exact_enclosed_volume_mm3=dict(numerator=volume.numerator,denominator=volume.denominator),
  original_source_classifications=dict(boundary_global_node_tags=boundary,other_interior_global_node_tags=interior,
    boundary_local_node_tags=[inverse[t] for t in boundary],other_interior_local_node_tags=[inverse[t] for t in interior]),
  necessary_face_quality_passed=passed,generation_input_rejected_by_necessary_face_quality=not passed,
  prospective_fixed_shell_only=True,execution_authorized=False,native_application_authorized=False,
  next_candidate=None,native_output=None,engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
 screen=dict(schema='962-fixed-cavity-tight-face-screen/v1',complete_face_count=len(faces),counts=counts,all_necessary_point1_face_bounds_passed=passed,
  exact_threshold_triangle_SICN_squared=h.rational(Fraction(4,841)),all_rows=screen_rows,
  tight_decision_uses_q_squared_not_the_included_loose_certificate_flag=True,
  scope='Exact necessary condition for retaining every stored shell triangle as a fixed unsplit linear TET face. Failure obstructs this fixed-shell scope only; pass does not prove replacement feasibility.',
  engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
 return observation,shell,screen


def main(contract_path,digest):
 path=Path(contract_path)
 if path.is_symlink() or sha(path)!=digest:raise ValueError('Exact external actual contract required')
 c=json.loads(path.read_text());require_authority(c)
 if c.get('source_sha256')!=sha(__file__) or c.get('python_sha256')!=sha(Path(sys.executable).resolve()):raise ValueError('Bound source/interpreter required')
 verify_pins(c['input_sha256']);out=ROOT/OUTPUT
 if out.exists() or out.is_symlink() or out.resolve()!=out:raise ValueError('Fresh raw canonical output required')
 h=load_helpers();data={k:json.loads((ROOT/k).read_text()) for k in [CENSUS,PRIOR,PARTIAL,RECEIPT,CLOSED,PEER,DIAGNOSIS,GRAPH,TRIAL,TRIAL_REVIEW]}
 selected,nodes=select_original(h,data)
 try:observation,shell,screen=build_records(h,selected,nodes)
 except Exception as error:
  verify_pins(c['input_sha256'])
  if sha(path)!=digest:raise ValueError('Actual contract drift')
  out.mkdir();refusal=dict(status='input_or_shell_topology_refused',error=type(error).__name__+': '+str(error),
   native_ordered_cell_rows=selected,selected_node_rows=[nodes[t] for t in sorted(nodes)],face_quality_screen_complete=False,
   input_sha256=c['input_sha256'],native_or_meshing_calls=0,all_authorities_false=True)
  (out/'refusal.json').write_text(json.dumps(refusal,indent=2,allow_nan=False)+'\n');return 2
 verify_pins(c['input_sha256'])
 if sha(path)!=digest:raise ValueError('Actual contract drift')
 out.mkdir()
 for name,value in [('saved-star-observation.json',observation),('local-shell-input-001.json',shell),('fixed-shell-tight-face-screen-001.json',screen)]:
  value['input_hashes']=c['input_sha256'];(out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
 passed=screen['all_necessary_point1_face_bounds_passed']
 receipt=dict(schema='962-apex1474426-saved-star-shell-extraction-receipt/v1',
  status='complete_data_only_shell_and_necessary_screen' if passed else 'complete_data_only_shell_rejected_necessary_face_quality',
  returncode=0 if passed else 2,contract_sha256=digest,source_sha256=c['source_sha256'],input_sha256=c['input_sha256'],
  outputs={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir())},all_bound_inputs_unchanged=True,
  native_or_meshing_calls=0,generation_authorized=False,head_edit_authorized=False,engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
 return receipt['returncode']


if __name__=='__main__':raise SystemExit(main(*sys.argv[1:]))
