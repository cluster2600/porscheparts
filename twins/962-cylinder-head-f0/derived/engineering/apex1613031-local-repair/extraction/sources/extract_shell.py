"""HELD saved-JSON extraction of current127 apex1613031 star; no native or meshing calls."""
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
OUTPUT = 'work/962-engineering/direct-sicn-apex1613031-cavity-study-001'
APEX = 1613031
FACES = ((0,2,1),(0,1,3),(1,2,3),(2,0,3))
CENSUS = 'work/962-engineering/head-star-current127-full-stars-002/readback-report.json'
PRIOR = 'work/962-engineering/head-star-current127-full-stars-002/frozen-contract.json'
PARTIAL = 'work/962-engineering/apex1613790-head-application-001/readback-report.json'
RECEIPT = 'work/962-engineering/apex1613790-head-application-001/execution-receipt.json'
CLOSED = 'work/962-engineering/apex1613790-head-application-root-execution-001/closed-result.json'
PEER = 'work/962-engineering/head-star-current127-full-stars-result-peer-001/review.json'
PEER_BINDINGS = 'work/962-engineering/head-star-current127-full-stars-result-peer-001/bindings.json'
CENSUS_ROOT = 'work/962-engineering/head-star-current127-full-stars-root-execution-001/closed-result.json'
CENSUS_ACCEPT = 'work/962-engineering/head-star-current127-full-stars-root-execution-001/result-peer-acceptance.json'
LAUNCH_DEVIATION = 'work/962-engineering/head-star-current129-full-stars-root-execution-001/launch-deviation-001.json'
CENSUS_ACTUAL = 'work/962-engineering/head-star-current127-full-stars-execution-prep-002/actual-contract.json'
PROOF_SOURCE = 'work/962-engineering/head-star-current127-full-stars-prep-001/reader.py'
EXACT_SOURCE = 'work/962-engineering/fixed-shell-coupled-embedding-prep-001/check_embedding.py'
INCIDENCE_SOURCE = 'work/962-engineering/domain-equivalence-prep-001/certify_domain.py'
FACE_SOURCE = 'twins/962-cylinder-head-f0/source/certify_fixed_face.py'
PINS = {
 CENSUS:'34e3e29a23cedeb155485156cb40b4e92b6d0017eefd852f30383927eaaa7ef7',
 PRIOR:'54ad12959a10bb153afec2f2541bec2d22ec3f6e22ee0302c581062265c8fc95',
 PARTIAL:'bb1266ede7b8fd41f282a04c2363ba0eb684a94b6272956895bb7a30a09ffad0',
 RECEIPT:'28bb0647a28de19e2413c0066468946ac5eee77e4b2e24a8b5f570ca184150fa',
 CLOSED:'e6951a0c920f88dda87efce797c111b1da83bb81f33cc2cd2c8acb900867504f',
 PEER:'e3f53c5b7280138296e4ffd8399149a61b9ecaf3bf796e4f780c74806a20b68b',
 PEER_BINDINGS:'968353193fa36fb96ec9dc85b4268ad3d37f011b19acff745c0a250dcf4fc2ac',
 CENSUS_ROOT:'34529d377e1e8aa9a858214aec6ed6e568cbee3c1bde39f504d06dfac604ee9c',
 CENSUS_ACCEPT:'bac2ff58db7e1f33556e8460e23d35cdd0cb7089c64afa6921ac7640b1bf0444',
 LAUNCH_DEVIATION:'d60fff297c6c45dc92e117262e36ffde36e2169d53fcd32ce2b79fabde5eebc3',
 CENSUS_ACTUAL:'54ad12959a10bb153afec2f2541bec2d22ec3f6e22ee0302c581062265c8fc95',
 PROOF_SOURCE:'11ad364b54b6b8f264f1727027659351ab38c9144b4c98c64e5265203fcb8a63',
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
 if (c.get('schema')!='962-apex1613031-cavity-extraction-actual/v1'
     or c.get('diagnostic_execution_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or any(c.get(k) is not False for k in FORBIDDEN) or c.get('automatic_retry') is not False
     or c.get('method')!='current127_apex1613031_complete14_star_exact_shell_and_necessary_face_screen'
     or c.get('output_directory')!=OUTPUT):raise ValueError('One reviewed data-only extraction authority required')


def select_original(h,data):
 census,prior,partial,receipt,closed,peer,peer_bindings,census_root,accepted,deviation=[data[k] for k in
  [CENSUS,PRIOR,PARTIAL,RECEIPT,CLOSED,PEER,PEER_BINDINGS,CENSUS_ROOT,CENSUS_ACCEPT,LAUNCH_DEVIATION]]
 proof=h.partial_after_proof(partial,receipt,closed,prior);h.require_after_match(census,proof,127)
 if (census.get('status')!='direct_saved_file_readback_completed' or census.get('bound_inputs_unchanged') is not True
     or {k:census[k] for k in proof['array_sha256s']}!=proof['array_sha256s']
     or census['direct_fresh_classifications']!=proof['classifications']
     or census.get('declared_controller_command_conformant') is not False
     or census.get('upstream_census_launch_deviation_sha256')!=PINS[LAUNCH_DEVIATION]
     or peer.get('decision')!='CLEAR_COMPLETED_READ_ONLY_CENSUS_SAVED_ASSOCIATIONS_ONLY'
     or peer.get('bindings',{}).get('sha256')!=PINS[PEER_BINDINGS]
     or peer.get('checked',{}).get('d60_false_conformance_preserved') is not True
     or peer_bindings.get('outputs',{}).get('readback-report.json',{}).get('sha256')!=PINS[CENSUS]
     or peer_bindings.get('selected_control_records',{}).get('actual',{}).get('sha256')!=PINS[CENSUS_ACTUAL]
     or PINS[PRIOR]!=PINS[CENSUS_ACTUAL]
     or census_root.get('schema')!='962-current127-head-census-root-closed/v1'
     or census_root.get('returncode')!=0 or census_root.get('stop_reason') is not None
     or census_root.get('waited_and_reaped') is not True or census_root.get('owned_controller_group_observed_absent') is not True
     or census_root.get('all79inputs_runtime4_and_rootPython_before_after_exact') is not True
     or census_root.get('actual',{}).get('sha256')!=PINS[PRIOR]
     or census_root['output_files']['readback-report.json']['sha256']!=PINS[CENSUS]
     or accepted.get('decision')!='ACCEPT_COMPLETED_READ_ONLY_CENSUS_SAVED_ASSOCIATIONS_ONLY'
     or accepted.get('peer',{}).get('sha256')!=PINS[PEER]
     or accepted.get('bindings',{}).get('sha256')!=PINS[PEER_BINDINGS]
     or accepted.get('root_closed',{}).get('sha256')!=PINS[CENSUS_ROOT]
     or accepted.get('report',{}).get('sha256')!=PINS[CENSUS]
     or accepted.get('upstream_d60_command_conformance') is not False
     or deviation.get('actual_sha256')!='ec888011591b8eda74ae83a4a3e796d1ab6d2cf555d99fba1fbbc2c003fb215f'
     or deviation.get('declared_controller_command_conformant') is not False):
  raise ValueError('Current127 stopped census/partial proof/corrected002 and historical d60 associations required')
 star=census['complete_seed_star_census'];all_rows=star['complete_incident_tetrahedra']
 if (len(all_rows)!=3137 or star['movable_count']!=101 or APEX not in star['movable_node_tags']
     or star['all_seed_stars_complete_including_initially_good_and_shared_cells'] is not True
     or dict(star['per_movable_node_complete_incident_counts']).get(APEX)!=14):
  raise ValueError('Complete current127 14-cell star attestation required')
 selected=[r for r in all_rows if APEX in r['node_tags']]
 if (len(selected)!=14 or [r['tetrahedron_tag'] for r in selected]!=sorted({r['tetrahedron_tag'] for r in selected})
     or len({r['native_array_index'] for r in selected})!=14 or sum(r['initially_positive_poor'] for r in selected)!=1
     or any(APEX not in r['movable_node_tags'] or type(r['native_array_index']) is not int or not 0<=r['native_array_index']<proof['tetrahedra']
            or len(r['node_tags'])!=4 or len(set(r['node_tags']))!=4 or not math.isfinite(r['initial_native_SICN']) or r['initial_native_SICN']<=0
            or r['initially_positive_poor']!=(r['initial_native_SICN']<.1) for r in selected)):
  raise ValueError('All14 unique current native-ordered cells and exact1 poor row required; shared movable labels retained')
 needed={t for r in selected for t in r['node_tags']};nodes={r['node_tag']:r for r in star['unique_incident_nodes'] if r['node_tag'] in needed}
 if len(needed)!=10 or set(nodes)!=needed or nodes[APEX]['source_boundary_tag'] is not False:raise ValueError('All10 current source nodes including dim3 apex required')
 for t,r in nodes.items():
  xyz=r['coordinates_mm'];boundary=t<=871731
  if (len(xyz)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in xyz)
      or [float(x).hex() for x in xyz]!=r['binary64_hex'] or r['source_boundary_tag'] is not boundary
      or r['freshly_proved_classification_scope']!=('below_dim3' if boundary else 'dim3')):
   raise ValueError('Current coordinate/hex/classification association changed')
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
 observation=dict(schema='962-current127-apex1613031-star-saved-observation/v1',apex=APEX,source_census_sha256=PINS[CENSUS],
  original_parent_MSH_sha256='8b16732d63cc69e48af113f6b618cc6378aaf121dbe1c63920dd6dd5eab8d07a',
  global_completeness_attribution='Accepted observed current127 census only; all14 retained rows selected here. Historical upstream d60 declared controller command conformant=False; no fresh full-MSH incidence query.',
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
 h=load_helpers();data={k:json.loads((ROOT/k).read_text()) for k in [CENSUS,PRIOR,PARTIAL,RECEIPT,CLOSED,PEER,PEER_BINDINGS,CENSUS_ROOT,CENSUS_ACCEPT,LAUNCH_DEVIATION]}
 selected,nodes=select_original(h,data)
 try:
  observation,shell,screen=build_records(h,selected,nodes)
  if (len(observation['native_ordered_cell_rows'])!=14 or len(observation['selected_node_rows'])!=10
      or shell['vertices']!=9 or shell['oriented_triangles']!=14
      or len(shell['original_source_classifications']['boundary_global_node_tags'])!=5
      or len(shell['original_source_classifications']['other_interior_global_node_tags'])!=4):
   raise ValueError('Anticipated current14/10 source and9/14 shell with5boundary+4dim3 classes required')
 except Exception as error:
  verify_pins(c['input_sha256'])
  if sha(path)!=digest:raise ValueError('Actual contract drift')
  out.mkdir();refusal=dict(status='input_or_shell_topology_refused',error=type(error).__name__+': '+str(error),
   native_ordered_cell_rows=selected,selected_node_rows=[nodes[t] for t in sorted(nodes)],face_quality_screen_complete=False,
   input_sha256=c['input_sha256'],native_or_meshing_calls=0,all_authorities_false=True,
   upstream_census_launch_deviation_sha256=PINS[LAUNCH_DEVIATION],declared_controller_command_conformant=False)
  (out/'refusal.json').write_text(json.dumps(refusal,indent=2,allow_nan=False)+'\n');return 2
 verify_pins(c['input_sha256'])
 if sha(path)!=digest:raise ValueError('Actual contract drift')
 out.mkdir()
 for name,value in [('saved-star-observation.json',observation),('local-shell-input-001.json',shell),('fixed-shell-tight-face-screen-001.json',screen)]:
  value['upstream_census_launch_deviation_sha256']=PINS[LAUNCH_DEVIATION];value['declared_controller_command_conformant']=False
  value['input_hashes']=c['input_sha256'];(out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
 passed=screen['all_necessary_point1_face_bounds_passed']
 receipt=dict(schema='962-apex1613031-current127-saved-star-shell-extraction-receipt/v1',
  status='complete_data_only_shell_and_necessary_screen' if passed else 'complete_data_only_shell_rejected_necessary_face_quality',
  returncode=0 if passed else 2,contract_sha256=digest,source_sha256=c['source_sha256'],input_sha256=c['input_sha256'],
  outputs={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir())},all_bound_inputs_unchanged=True,
  upstream_census_launch_deviation_sha256=PINS[LAUNCH_DEVIATION],declared_controller_command_conformant=False,
  native_or_meshing_calls=0,generation_authorized=False,head_edit_authorized=False,engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
 return receipt['returncode']


if __name__=='__main__':raise SystemExit(main(*sys.argv[1:]))
