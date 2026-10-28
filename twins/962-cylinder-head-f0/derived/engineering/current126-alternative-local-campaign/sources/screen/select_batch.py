"""HELD current126 exact31 alternative-star screening; saved data only."""
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

ROOT=Path(__file__).resolve().parents[3]
OUTPUT='work/962-engineering/head-star-current126-alternative-batch-shells-001'
FACES=((0,2,1),(0,1,3),(1,2,3),(2,0,3))
CENSUS='work/962-engineering/head-star-current126-full-stars-001/readback-report.json'
PRIOR='work/962-engineering/head-star-current126-full-stars-001/frozen-contract.json'
PARTIAL='work/962-engineering/apex1613031-head-application-001/readback-report.json'
RECEIPT='work/962-engineering/apex1613031-head-application-001/execution-receipt.json'
CLOSED='work/962-engineering/apex1613031-head-application-root-execution-001/closed-result.json'
CENSUS_RECEIPT='work/962-engineering/head-star-current126-full-stars-001/execution-receipt.json'
CENSUS_CLOSED='work/962-engineering/head-star-current126-full-stars-root-execution-001/closed-result.json'
CENSUS_ROOT='work/962-engineering/head-star-current126-full-stars-root-execution-001/own-review.json'
PEER='work/962-engineering/head-star-current126-full-stars-result-peer-001/review.json'
PEER_BINDINGS='work/962-engineering/head-star-current126-full-stars-result-peer-001/bindings.json'
ACCEPTANCE='work/962-engineering/head-star-current126-full-stars-root-execution-001/result-peer-acceptance.json'
COHORT_HISTORY='work/962-engineering/current127-alternative-star-batch-plan-001/plan.json'
COHORT_COMPARISON='work/962-engineering/current126-alternative-star-batch-plan-001/plan.json'
PRIOR_MANIFEST='work/962-engineering/head-star-current204-local-stages-prep-001/case-manifest.json'
PROOF_SOURCE='work/962-engineering/head-star-current126-full-stars-prep-001/reader.py'
EXACT_SOURCE='work/962-engineering/fixed-shell-coupled-embedding-prep-001/check_embedding.py'
INCIDENCE_SOURCE='work/962-engineering/domain-equivalence-prep-001/certify_domain.py'
FACE_SOURCE='twins/962-cylinder-head-f0/source/certify_fixed_face.py'
PEER_DECISION='CLEAR_COMPLETED_READ_ONLY_CENSUS_SAVED_ASSOCIATIONS_ONLY'
CURRENT_MSH_SHA256='48b66aafbd9f1eb69e44305982186e966fe8f041d9b4a6a59be4b610b5d12e08'
ALTERNATIVE_APICES=[1393281, 1433071, 1436404, 1436405, 1436406, 1436407, 1459592, 1459657, 1460416, 1468585, 1476316, 1481549, 1488093, 1506140, 1508641, 1515013, 1528968, 1535650, 1538046, 1541053, 1558088, 1558090, 1570037, 1611558, 1611564, 1613030, 1613791, 1613794, 1613795, 1613801, 1613803]
REJECTED_APICES=[1393392, 1409441, 1421336, 1424314, 1432342, 1433502, 1441004, 1441011, 1441012, 1441013, 1442335, 1450443, 1458419, 1459063, 1459064, 1459940, 1459941, 1460612, 1470654, 1474771, 1481857, 1485102, 1487573, 1502469, 1504163, 1506129, 1512157, 1512642, 1514912, 1520064, 1527816, 1534323, 1534574, 1548247, 1549365, 1549366, 1549537, 1552068, 1555697, 1555743, 1555744, 1560546, 1573898, 1585373, 1585374, 1585378, 1596472, 1606005, 1608113, 1610627, 1610628, 1611139, 1611467, 1611657, 1611658, 1611659, 1611943, 1612414, 1612796, 1612957, 1613513, 1613514, 1613588, 1613756, 1613757, 1613783, 1613784, 1613798]
HELD_APEX=1393275
PINS = {'twins/962-cylinder-head-f0/source/certify_fixed_face.py': '9b13f4dc7f2eca7da04e1587eb1f59a379a0d0c2101026f9b1d999ae09aaebb8', 'work/962-engineering/apex1613031-head-application-001/execution-receipt.json': '496b0e01950b777acd1c1759177fe26fac5659e5ec6512bb19ff9cb56b5fd46d', 'work/962-engineering/apex1613031-head-application-001/readback-report.json': '64caf59811e229628ea1be138ebcc48cdf940c4ca2724be0b9080e255951c9f5', 'work/962-engineering/apex1613031-head-application-root-execution-001/closed-result.json': '9324c5ef88293efa33f9e14cfeff3e092795eec337fceeaffd7481ac2ee41471', 'work/962-engineering/apex1613031-head-application-root-execution-001/result-peer-acceptance.json': '19ef174a208868bf174909a1add690971fdf018b8cf438c5c26e3a2bca9bfada', 'work/962-engineering/current126-alternative-star-batch-plan-001/plan.json': 'd9b820a6cf25a06cfa33128e4a17555046d545735a0f8299300b613892f183f5', 'work/962-engineering/current127-alternative-star-batch-plan-001/plan.json': '5d4b3c06769ceac2777a2ae3f243c45f951979cc7ab8a79a8efe953acfbd72ac', 'work/962-engineering/domain-equivalence-prep-001/certify_domain.py': '0fe593d385e5a0ab4944528fa1b869ddf2c41c28d050576afe9be18213462296', 'work/962-engineering/fixed-shell-coupled-embedding-prep-001/check_embedding.py': '1b489cc8149f4b5db8f90c594e32fe4c09b5db00151df6b1cfc88362d1018134', 'work/962-engineering/head-star-current126-full-stars-001/execution-receipt.json': '883604b10d223d364010b845b5aff4e198561842b3c22dc9a67f92606f5bd444', 'work/962-engineering/head-star-current126-full-stars-001/frozen-contract.json': 'd579a794f18bc9f7c4e153cb2042f32cb32b2c6b2f2235cec2edbef8aba91317', 'work/962-engineering/head-star-current126-full-stars-001/readback-report.json': 'ac40521a4add15f1bb414d7d1a1c2cd231a0107278b6fe43ec38dad27c269e1a', 'work/962-engineering/head-star-current126-full-stars-prep-001/reader.py': '2348c032ecbbb694563978cb333aff1a7e4d37a5052c3ed841a7128bf797409c', 'work/962-engineering/head-star-current126-full-stars-result-peer-001/bindings.json': 'c2c33a39a1cb3f393288ee4a7f344f17d45bfa44c8c81347fe07cca6421b66d5', 'work/962-engineering/head-star-current126-full-stars-result-peer-001/review.json': 'f22ee8bfc026caec2b6182bddfdfa250795ea3ee698c73c41a823a6dd1f5a4c4', 'work/962-engineering/head-star-current126-full-stars-root-execution-001/closed-result.json': '4ec76692bd1fb7bb592bf24c82b199830eb6a4828cf9726fc879fa387022fb99', 'work/962-engineering/head-star-current126-full-stars-root-execution-001/own-review.json': '7d656e69d070e40d45de44c0bd61fedce03720201f44339ec7839c0dafc28931', 'work/962-engineering/head-star-current126-full-stars-root-execution-001/result-peer-acceptance.json': 'f66d5857a0fa75352c3880ab2cd7bbc0bcae73833254f39423fd48971ebd52d9', 'work/962-engineering/head-star-current129-full-stars-root-execution-001/launch-deviation-001.json': 'd60fff297c6c45dc92e117262e36ffde36e2169d53fcd32ce2b79fabde5eebc3', 'work/962-engineering/head-star-current204-batch-shells-prep-001/METHOD.md': '20df61af74b23631ee3fe22d0eeef00c5457951473402932f62f40d4d6f76bc5', 'work/962-engineering/head-star-current204-batch-shells-prep-001/select_batch.py': 'af388dd1a3ba5027c5c0b7a62295a2d8950b4789e0568e68f5451ab52a708350', 'work/962-engineering/head-star-current204-batch-shells-prep-001/selfcheck.py': 'd63f8783c6c5b813cfd3c1fb123ee938e0a68917cf3b5c1629b8c1c2d2106a28', 'work/962-engineering/head-star-current204-local-stages-prep-001/case-manifest.json': '3a558ede04cbc52c59e401befb36b8983ebd9b7f57d4266de0bea38fb1a963c5'}
FORBIDDEN=['native_execution_authorized','generation_authorized','optimization_authorized',
 'head_edit_authorized','head_execution_authorized','head_PDE_authorized','stitching_authorized',
 'engineering_accepted','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized']


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
 if (c.get('schema')!='962-current126-alternative-batch-shell-selection-actual/v1'
     or c.get('diagnostic_execution_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or any(c.get(k) is not False for k in FORBIDDEN) or c.get('automatic_retry') is not False
     or c.get('method')!='all_exact31_alternative_stars_after_full_current100_validation_then_vertex_disjoint_greedy'
     or c.get('output_directory')!=OUTPUT or c.get('alternative_apex_tags')!=ALTERNATIVE_APICES
     or c.get('excluded_prior_quality_rejected_apices')!=REJECTED_APICES or c.get('held_prior_apex')!=HELD_APEX):raise ValueError('One reviewed saved-data-only batch extraction authority required')


def current_proof(h,data):
 census,prior,partial,receipt,closed,cr,cz,root,peer,pb,accepted=[data[k] for k in
  [CENSUS,PRIOR,PARTIAL,RECEIPT,CLOSED,CENSUS_RECEIPT,CENSUS_CLOSED,CENSUS_ROOT,PEER,PEER_BINDINGS,ACCEPTANCE]]
 proof=h.partial_after_proof(partial,receipt,closed,prior);h.require_after_match(census,proof,126)
 if (prior.get('MSH_sha256')!=CURRENT_MSH_SHA256
     or census.get('status')!='direct_saved_file_readback_completed' or census.get('bound_inputs_unchanged') is not True
     or {k:census[k] for k in proof['array_sha256s']}!=proof['array_sha256s']
     or census['direct_fresh_classifications']!=proof['classifications']
     or census.get('declared_controller_command_conformant') is not False or census.get('SICN_point1_gate_passed') is not False
     or cr.get('returncode')!=0 or cr.get('stop_reason') is not None
     or cr.get('readback_report_sha256')!=PINS[CENSUS] or cr.get('contract_sha256')!=PINS[PRIOR]
     or cz.get('schema')!='962-current126-head-census-root-closed/v1' or cz.get('returncode')!=0
     or cz.get('error') is not None or cz.get('signals')!=[] or cz.get('outer_fallback_used') is not False
     or any(cz.get(k) is not True for k in ['controller_waited_reaped','controller_owned_group_observed_absent','all108_inputs_unchanged','runtime5_unchanged','static9_unchanged','valid_closed_controller_receipt','complete6_output_names'])
     or cz.get('whole_actual_mirror_sha256')!=PINS[PRIOR] or cz.get('upstream_d60_command_conformant') is not False
     or cz['output_files']['readback-report.json']['sha256']!=PINS[CENSUS]
     or cz['output_files']['execution-receipt.json']['sha256']!=PINS[CENSUS_RECEIPT]
     or root.get('schema')!='962-current126-census-root-saved-association-review/v1'
     or root.get('decision')!='ACCEPT_COMPLETE_SAVED_CENSUS_ASSOCIATIONS_ONLY_PENDING_SEPARATE_PEER'
     or peer.get('schema')!='962-current126-census-independent-stopped-saved-review/v1'
     or peer.get('decision')!=PEER_DECISION or peer.get('blockers')!=[]
     or peer['bindings']['sha256']!=PINS[PEER_BINDINGS]
     or pb.get('schema')!='962-current126-census-saved-result-bindings/v1'
     or pb['root_closed']['sha256']!=PINS[CENSUS_CLOSED]
     or any(pb['outputs'][name]['sha256']!=PINS[path] for name,path in [('readback-report.json',CENSUS),('frozen-contract.json',PRIOR),('execution-receipt.json',CENSUS_RECEIPT)])
     or pb['source_proof']['sha256']!=PINS[PARTIAL]
     or accepted.get('schema')!='962-current126-census-root-result-acceptance/v1'
     or accepted.get('decision')!='ACCEPT_COMPLETE_CURRENT126_READ_ONLY_CENSUS_ASSOCIATIONS_ONLY'
     or any(accepted[key]['sha256']!=PINS[path] for key,path in [('current_report',CENSUS),('current_contract',PRIOR),('current_receipt',CENSUS_RECEIPT),('root_closed',CENSUS_CLOSED),('root_own_review',CENSUS_ROOT),('peer_review',PEER),('peer_bindings',PEER_BINDINGS)])
     or accepted['current_mesh']['sha256']!=CURRENT_MSH_SHA256
     or accepted.get('whole_head_quality_accepted') is not False or accepted.get('prior_d60_command_conformant') is not False):
  raise ValueError('Exact accepted current126 census and current partial-after associations required')
 star=census['complete_seed_star_census']
 if (star.get('schema')!='962-complete-current-poor-seed-stars/v1'
     or (star['movable_count'],star['complete_incident_tetrahedron_count'],star['unique_incident_node_count'])!=(100,3123,1781)
     or census['positive_poor_SICN_cells']['total']!=126):raise ValueError('Exact fresh current126 census identity required')
 return census


def alternative_cohort(seeds,history,manifest):
 """The complete finite alternative cohort; historical rejections are not retried."""
 prior=[r['apex'] for r in manifest['cases_in_increasing_apex_order']]
 if (seeds!=sorted(set(seeds)) or len(seeds)!=100 or prior!=sorted(set(prior)) or len(prior)!=116
     or history['prospective_alternative_pool']['apex_tags']!=ALTERNATIVE_APICES
     or history['prior_history']['current_apices_with_prior_local_quality_rejection']!=REJECTED_APICES
     or history['prior_history']['held_apex1393275_no_retry'] is not True
     or sorted(set(seeds)-set(prior)-{1613031})!=ALTERNATIVE_APICES
     or sorted(set(ALTERNATIVE_APICES)|set(REJECTED_APICES)|{HELD_APEX})!=seeds
     or set(ALTERNATIVE_APICES)&(set(REJECTED_APICES)|{HELD_APEX,1613031})
     or set(prior)&set(seeds)!=set(REJECTED_APICES)|{HELD_APEX}):
  raise ValueError('Exact31 alternatives,68 preserved rejections and held1393275 required')
 return list(ALTERNATIVE_APICES)


def census_rows(census,boundary_count,tetrahedron_count):
 """Validate every serialized row/word/seed and six typed arrays before selecting stars."""
 star=census['complete_seed_star_census'];rows=star['complete_incident_tetrahedra'];node_rows=star['unique_incident_nodes']
 seeds=star['movable_node_tags'];poor=census['positive_poor_SICN_cells']['complete_tagged_cells']
 if (star['all_seed_stars_complete_including_initially_good_and_shared_cells'] is not True
     or star['all_positive_poor_rows_covered_by_movable_stars'] is not True
     or star['unseedable_positive_poor_tetrahedron_tags']!=[]
     or seeds!=sorted(set(seeds)) or any(type(t) is not int or t<=boundary_count for t in seeds)
     or len(seeds)!=star['movable_count'] or star['prospective_coordinate_variables']!=3*len(seeds)):
  raise ValueError('Complete fresh interior-seed star attestation required')
 tags=[r['tetrahedron_tag'] for r in rows];nt=[r['node_tag'] for r in node_rows]
 if (tags!=sorted(set(tags)) or any(type(t) is not int or t<=0 for t in tags)
     or nt!=sorted(set(nt)) or any(type(t) is not int or t<=0 for t in nt)
     or len(rows)!=star['complete_incident_tetrahedron_count'] or len(node_rows)!=star['unique_incident_node_count']
     or len({r['native_array_index'] for r in rows})!=len(rows)):
  raise ValueError('Complete increasing unique cell/node/index rows required')
 nodes={r['node_tag']:r for r in node_rows};seed_set=set(seeds);members=set();counts=Counter();poor_tags=[]
 for t,r in nodes.items():
  xyz=r['coordinates_mm'];boundary=t<=boundary_count
  if (len(xyz)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in xyz)
      or [float(v).hex() for v in xyz]!=r['binary64_hex'] or r['source_boundary_tag'] is not boundary
      or r['in_movable_seed_set'] is not (t in seed_set)
      or r['freshly_proved_classification_scope']!=('below_dim3' if boundary else 'dim3')):
   raise ValueError('Every current binary64 coordinate/classification/seed association required')
 for r in rows:
  row=r['node_tags'];q=r['initial_native_SICN'];touch=sorted(set(row)&seed_set)
  if (len(row)!=4 or len(set(row))!=4 or any(type(t) is not int or t not in nodes for t in row)
      or type(r['native_array_index']) is not int or not 0<=r['native_array_index']<tetrahedron_count
      or type(q) not in (int,float) or not math.isfinite(q) or q<=0
      or not touch or r['movable_node_tags']!=touch or r['initially_positive_poor'] is not (q<.1)):
   raise ValueError('Every native-ordered complete incident row/membership/quality required')
  counts.update(touch);members.update(row)
  if q<.1:poor_tags.append(r['tetrahedron_tag'])
 if (members!=set(nodes) or star['per_movable_node_complete_incident_counts']!=[[t,counts[t]] for t in seeds]
     or star['positive_poor_tetrahedron_tags']!=poor_tags or [r['tetrahedron_tag'] for r in poor]!=poor_tags
     or len(poor_tags)!=census['positive_poor_SICN_cells']['total']
     or len(poor_tags)!=star['initially_positive_poor_incident_tetrahedra']
     or len(rows)-len(poor_tags)!=star['initially_good_incident_tetrahedra']
     or sum(len(r['movable_node_tags'])>1 for r in rows)!=star['shared_by_multiple_movable_nodes_tetrahedra']
     or sum(r['source_boundary_tag'] for r in node_rows)!=star['unique_incident_boundary_node_count']
     or sum(not r['source_boundary_tag'] and not r['in_movable_seed_set'] for r in node_rows)!=star['unique_incident_other_interior_node_count']):
  raise ValueError('Complete poor/per-seed/shared/context counts and memberships required')
 bytag={r['tetrahedron_tag']:r for r in rows};bins={str(i):0 for i in range(5)};derived_seeds=set()
 for r in poor:
  source=bytag[r['tetrahedron_tag']];ordered=[nodes[t] for t in source['node_tags']]
  if (r['node_tags']!=source['node_tags'] or r['native_array_index']!=source['native_array_index'] or r['SICN']!=source['initial_native_SICN']
      or [struct.pack('<3d',*point) for point in r['coordinates_mm']]!=[struct.pack('<3d',*n['coordinates_mm']) for n in ordered]
      or r['binary64_hex']!=[n['binary64_hex'] for n in ordered]):
   raise ValueError('Every complete poor row must match original current native/corner/word rows')
  boundary=sum(t<=boundary_count for t in r['node_tags']);bins[str(boundary)]+=1
  if r['original_boundary_node_count']!=boundary or r['interior_node_count']!=4-boundary:raise ValueError('Fresh poor partition required')
  derived_seeds.update(t for t in r['node_tags'] if t>boundary_count)
 if sorted(derived_seeds)!=seeds or bins!=census['positive_poor_SICN_cells']['by_original_boundary_node_count']:
  raise ValueError('Seeds must be precisely all current poor interior members')
 arrays=[('movable_node_tags_u64','Q',seeds),('selected_tetrahedron_tags_u64','Q',tags),
  ('selected_tetrahedron_connectivity_u64','Q',[t for r in rows for t in r['node_tags']]),
  ('union_node_tags_u64','Q',nt),('union_coordinates_f64','d',[v for r in node_rows for v in r['coordinates_mm']]),
  ('selected_initial_SICN_f64','d',[r['initial_native_SICN'] for r in rows])]
 if set(star['ordered_tagged_array_sha256s'])!={name for name,_,_ in arrays}:raise ValueError('Exactly six typed census hashes required')
 for name,code,values in arrays:
  digest=hashlib.sha256(struct.pack('<'+code*len(values),*values)).hexdigest()
  if digest!=star['ordered_tagged_array_sha256s'][name]:raise ValueError('Complete typed census hash mismatch: '+name)
 return rows,nodes,seeds


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


def build_records(h,selected,nodes,apex):
 cells={r['tetrahedron_tag']:r['node_tags'] for r in selected};index={r['tetrahedron_tag']:r['native_array_index'] for r in selected}
 outer=shell_faces(h,cells,apex);faces=[r['global_node_tags'] for r in outer];topology=shell_topology(faces)
 fixed=sorted({t for row in faces for t in row})
 if set(nodes)!=set(fixed+[apex]):raise ValueError('All non-apex star nodes must occur on the prospective shell')
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
 observation=dict(schema='962-current126-alternative-batch-star-saved-observation/v1',apex=apex,source_census_sha256=PINS[CENSUS],
  original_parent_MSH_sha256=CURRENT_MSH_SHA256,
  global_completeness_attribution='Frozen executed current census only; all complete source-star rows selected here, no fresh full-MSH incidence query.',
  native_ordered_cell_rows=selected,selected_node_rows=[dict(nodes[t],binary64_little_endian_bytes_hex=struct.pack('<3d',*nodes[t]['coordinates_mm']).hex()) for t in sorted(nodes)],
  tetrahedral_complex=complex_report,outer_surface=dict(topology,oriented_source_owner_rows=outer),exact_volume_mm3=h.rational(volume),
  original_source_classifications=dict(boundary_global_node_tags=boundary,other_interior_global_node_tags=interior),
  exact_old_cells_required_positive_but_not_quality_point1=True,embedding_domain_and_external_owner_checks_performed=False)
 shell=dict(schema='962-fixed-cavity-local-shell-input/v1',status='DATA_ONLY_HELD' if passed else 'DATA_ONLY_REJECTED_FIXED_SHELL_FACE_QUALITY',
  units='mm',frame='Unchanged original census frame; no OEM datum qualification',excluded_source_apex_tag=apex,apex_not_in_shell_input=True,
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



def greedy_disjoint(records):
 """Fixed ranking; complete vertex sets, including apex and every shell node, are disjoint."""
 if len({r['apex'] for r in records})!=len(records):raise ValueError('One eligibility record per unique apex required')
 for r in records:
  if (type(r['apex']) is not int or r['apex']<=0 or type(r['poor_coverage']) is not int or r['poor_coverage']<=0
      or type(r['eligible']) is not bool or r['all_vertex_tags']!=sorted(set(r['all_vertex_tags']))
      or r['apex'] not in r['all_vertex_tags'] or any(type(t) is not int or t<=0 for t in r['all_vertex_tags'])):
   raise ValueError('Exact eligibility/coverage/full-vertex records required')
 selected=[];decisions=[]
 for rank,r in enumerate(sorted(records,key=lambda r:(-r['poor_coverage'],r['apex'])),1):
  conflicts=[dict(selected_apex=old['apex'],shared_vertex_tags=sorted(set(r['all_vertex_tags'])&set(old['all_vertex_tags']))) for old in selected
   if set(r['all_vertex_tags'])&set(old['all_vertex_tags'])]
  take=r['eligible'] and not conflicts
  if take:selected.append(r)
  decisions.append(dict(rank=rank,apex=r['apex'],poor_coverage=r['poor_coverage'],eligible=r['eligible'],selected=take,
   status='selected' if take else ('ineligible' if not r['eligible'] else 'vertex_conflict'),conflicts_with_already_selected=conflicts))
 return selected,decisions


def main(contract_path,digest):
 path=Path(contract_path)
 if path.is_symlink() or sha(path)!=digest:raise ValueError('Exact external actual contract required')
 c=json.loads(path.read_text());require_authority(c)
 if c.get('source_sha256')!=sha(__file__) or c.get('python_sha256')!=sha(Path(sys.executable).resolve()):raise ValueError('Bound source/interpreter required')
 verify_pins(c['input_sha256']);out=ROOT/OUTPUT
 if out.exists() or out.is_symlink() or out.resolve()!=out:raise ValueError('Fresh raw canonical output required')
 h=load_helpers();data={k:json.loads((ROOT/k).read_text()) for k in [CENSUS,PRIOR,PARTIAL,RECEIPT,CLOSED,CENSUS_RECEIPT,CENSUS_CLOSED,CENSUS_ROOT,PEER,PEER_BINDINGS,ACCEPTANCE,COHORT_HISTORY,PRIOR_MANIFEST]}
 census=current_proof(h,data);prior=data[PRIOR];rows,nodes,seeds=census_rows(census,prior['candidate_vertices'],census['actual_tetrahedra'])
 cohort=alternative_cohort(seeds,data[COHORT_HISTORY],data[PRIOR_MANIFEST])
 records=[]
 for apex in cohort:
  selected=[r for r in rows if apex in r['node_tags']];vertex_tags=sorted({t for r in selected for t in r['node_tags']})
  poor=[r['tetrahedron_tag'] for r in selected if r['initially_positive_poor']]
  record=dict(apex=apex,source_complete_incident_cell_count=len(selected),source_tetrahedron_tags=[r['tetrahedron_tag'] for r in selected],
   source_native_array_indices=[r['native_array_index'] for r in selected],all_vertex_tags=vertex_tags,poor_tetrahedron_tags=poor,poor_coverage=len(poor))
  try:
   observation,shell,screen=build_records(h,selected,{t:nodes[t] for t in vertex_tags},apex)
   record.update(eligible=screen['all_necessary_point1_face_bounds_passed'],eligibility_status='all_exact_shell_and_necessary_face_gates_pass' if screen['all_necessary_point1_face_bounds_passed'] else 'necessary_face_quality_refused',
    observation=observation,shell=shell,necessary_face_screen=screen)
  except ValueError as error:
   record.update(eligible=False,eligibility_status='exact_star_or_shell_refused',error=type(error).__name__+': '+str(error),
    native_ordered_cell_rows=selected,selected_node_rows=[nodes[t] for t in vertex_tags],face_quality_screen_complete=False)
  records.append(record)
 selected,decisions=greedy_disjoint(records);selected_tags=[r['apex'] for r in selected]
 covered=sorted({t for r in selected for t in r['poor_tetrahedron_tags']});vertices=[t for r in selected for t in r['all_vertex_tags']]
 if len(vertices)!=len(set(vertices)):raise ValueError('Every selected entire vertex set must be disjoint')
 report=dict(schema='962-current126-alternative-star-vertex-disjoint-batch/v1',status='complete_saved_data_batch_selection',
  source_census_sha256=PINS[CENSUS],source_partial_head_report_sha256=PINS[PARTIAL],source_MSH_sha256=CURRENT_MSH_SHA256,
  source_current_positive_poor_cells=126,source_seed_count=len(seeds),candidate_star_count=len(records),
  alternative_apex_tags=cohort,excluded_prior_quality_rejected_apices=REJECTED_APICES,held_prior_apex=HELD_APEX,
  excluded_history_not_rescreened=[dict(apex=t,status='prior_local_quality_rejected_no_retry' if t!=HELD_APEX else 'held_no_retry') for t in sorted(set(REJECTED_APICES)|{HELD_APEX})],
  declared_controller_command_conformant=False,upstream_census_launch_deviation_sha256=census['upstream_census_launch_deviation_sha256'],
  eligibility_count=sum(r['eligible'] for r in records),ineligible_count=sum(not r['eligible'] for r in records),
  selection_policy='Eligible exact31 alternative stars after complete100 census validation, in descending current poor-cell coverage, increasing apex tag on ties; greedily select if the entire original star vertex set has no intersection with any previously selected star. No batch cap or optimal-coverage claim.',
  all_candidate_star_records=records,all_ranked_selection_decisions=decisions,selected_apex_tags=selected_tags,selected_star_count=len(selected),
  selected_unique_vertex_count=len(vertices),selected_complete_cell_count=sum(r['source_complete_incident_cell_count'] for r in selected),
  current_poor_tetrahedron_tags_covered=covered,current_poor_cell_coverage=len(covered),
  remaining_current_poor_tetrahedron_tags=sorted(set(census['complete_seed_star_census']['positive_poor_tetrahedron_tags'])-set(covered)),
  full_source_star_completeness_attributed_to_executed_census=True,tag_disjointness_is_not_a_geometric_nonoverlap_proof=True,
  embedding_domain_parent_owner_or_containment_checks_performed=False,next_candidate=None,native_or_meshing_calls=0,
  generation_authorized=False,optimization_authorized=False,head_edit_authorized=False,stitching_authorized=False,
  engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False,input_sha256=c['input_sha256'])
 verify_pins(c['input_sha256'])
 if sha(path)!=digest:raise ValueError('Actual contract drift')
 out.mkdir();(out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
 receipt=dict(schema='962-current126-alternative-batch-shell-selection-receipt/v1',status='complete_saved_data_only_batch',returncode=0,
  contract_sha256=digest,source_sha256=c['source_sha256'],input_sha256=c['input_sha256'],
  outputs={'report.json':dict(bytes=(out/'report.json').stat().st_size,sha256=sha(out/'report.json'))},all_bound_inputs_unchanged=True,
  native_or_meshing_calls=0,all_native_edit_physics_authorities_false=True)
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
 return 0


if __name__=='__main__':raise SystemExit(main(*sys.argv[1:]))
