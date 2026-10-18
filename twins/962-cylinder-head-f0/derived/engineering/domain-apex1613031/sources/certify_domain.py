"""HELD exact old14/new14 pair embedding and common-shell local-domain query; no head action."""
from pathlib import Path
from fractions import Fraction
from itertools import combinations
import hashlib,importlib.util,json,math,re,struct,sys,time
ROOT=Path(__file__).resolve().parents[3]
OUTPUT='work/962-engineering/apex1613031-domain-equivalence-001'
QUALIFICATION=dict(native_application_authorized=False,head_execution_authorized=False,stitching_authorized=False,
 engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
HELPER='work/962-engineering/fixed-shell-coupled-embedding-prep-001/check_embedding.py'
CHAIN_SOURCE='work/962-engineering/domain-equivalence-prep-001/certify_domain.py'
OBSERVATION='work/962-engineering/direct-sicn-apex1613031-cavity-study-001/saved-star-observation.json'
SHELL='work/962-engineering/direct-sicn-apex1613031-cavity-study-001/local-shell-input-001.json'
WORKER='work/962-engineering/fixed-shell-netgen-apex1613031-001/fixture-report.json'
ARRAYS='work/962-engineering/fixed-shell-netgen-apex1613031-001/arrays.json'
PEER='work/962-engineering/fixed-shell-netgen-apex1613031-result-peer-001/review.json'
PEER_BINDINGS='work/962-engineering/fixed-shell-netgen-apex1613031-result-peer-001/bindings.json'
ACCEPTANCE='work/962-engineering/fixed-shell-netgen-apex1613031-root-execution-001/result-peer-acceptance.json'
INPUTS={'work/962-engineering/fixed-shell-coupled-embedding-prep-001/check_embedding.py': '1b489cc8149f4b5db8f90c594e32fe4c09b5db00151df6b1cfc88362d1018134', 'work/962-engineering/domain-equivalence-prep-001/certify_domain.py': '0fe593d385e5a0ab4944528fa1b869ddf2c41c28d050576afe9be18213462296', 'work/962-engineering/direct-sicn-apex1613031-cavity-study-001/saved-star-observation.json': '89689ac5ce5f12c8922be4cbe45e36565f60eed080633aaffa79539c8e12c8d3', 'work/962-engineering/direct-sicn-apex1613031-cavity-study-001/local-shell-input-001.json': '6529ffc5a5ca738c4bfe3041d858f2d40cc50efc6ee0e1dc5bcc626fd720d92d', 'work/962-engineering/fixed-shell-netgen-apex1613031-001/fixture-report.json': 'a7f4aa89c415be333b03301575898c4f2fc7ea56a9664c22422bb81ad2092a8b', 'work/962-engineering/fixed-shell-netgen-apex1613031-001/arrays.json': '84df4795b0e7499c45b56a0af800e2470a51b5333a881b8150ea735ed2d03954', 'work/962-engineering/fixed-shell-netgen-apex1613031-result-peer-001/review.json': 'b92bf933b272e39d5362c1adaf4bac155e98258668456d29abf5d6d4cb0b6fbe', 'work/962-engineering/fixed-shell-netgen-apex1613031-result-peer-001/bindings.json': 'dc23febe02576eaa17aab53c697bef3d67e4d774090780e0f313527d2dab1f51', 'work/962-engineering/fixed-shell-netgen-apex1613031-root-execution-001/result-peer-acceptance.json': '42ae8e27bc62f63c280c185c1d036223fbeea05f4452aec39cbfce4653c9813e'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
FACES=((0,2,1),(0,1,3),(1,2,3),(2,0,3))


def cycle(face):
 return min(tuple(face[i:]+face[:i]) for i in range(3))


def complex_rows(helper,points,cells,expected_shell):
 if not cells or any(len(row)!=4 or len(set(row))!=4 or not set(row)<=set(points) for row in cells.values()):
  raise ValueError('Complete nondegenerate tagged tetrahedron rows required')
 if len({tuple(sorted(row)) for row in cells.values()})!=len(cells):raise ValueError('Duplicate cell refused')
 incidence={};quality=[];volume=Fraction(0)
 for tag,row in sorted(cells.items()):
  det,q2=helper.exact_quality([[float(x) for x in points[t]] for t in row])
  if det<=0 or q2 is None:raise ValueError('Every old/new stored tetrahedron must be exact-positive; old quality may be poor')
  volume+=det/6
  quality.append(dict(tetrahedron_tag=tag,ordered_node_tags=row,exact_determinant_mm3=helper.rational(det),
   exact_SICN_squared=helper.rational(q2),exact_point1_gate_passed=q2>=Fraction(1,100)))
  for pattern in FACES:
   face=[row[i] for i in pattern];incidence.setdefault(tuple(sorted(face)),[]).append(face)
 boundary=[];internal=0
 for faces in incidence.values():
  if len(faces)==1:boundary.append(cycle(faces[0]))
  elif len(faces)==2 and cycle(faces[0])==cycle(list(reversed(faces[1]))):internal+=1
  else:raise ValueError('Complete opposite internal-face cancellation required')
 if sorted(boundary)!=sorted(cycle(list(f)) for f in expected_shell):
  raise ValueError('Exact geometric oriented boundary rows differ from the frozen shell')
 return dict(cell_count=len(cells),internal_face_pairs=internal,oriented_boundary=[list(x) for x in sorted(boundary)],
  all_exact_positive=True,quality_rows=quality,exact_signed_volume_mm3=helper.rational(volume)),volume


def original(observation,shell):
 if (observation.get('apex')!=1613031 or len(observation['native_ordered_cell_rows'])!=14 or len(observation['selected_node_rows'])!=10
     or any(data.get('upstream_census_launch_deviation_sha256')!='d60fff297c6c45dc92e117262e36ffde36e2169d53fcd32ce2b79fabde5eebc3'
            or data.get('declared_controller_command_conformant') is not False for data in [observation,shell])):
  raise ValueError('Exact frozen14cell/10node source star and upstream deviation required')
 mapping={t:i+1 for i,t in enumerate(shell['local_to_global_node_tags'])};mapping[1613031]=10
 if len(mapping)!=10 or shell['global_to_local_node_tags']!={str(t):i+1 for i,t in enumerate(shell['local_to_global_node_tags'])}:
  raise ValueError('Specific exact shell inverse mapping required')
 points={};words={}
 for row in observation['selected_node_rows']:
  tag=row['node_tag'];xyz=row['coordinates_mm']
  if tag not in mapping or len(xyz)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in xyz) or [float(x).hex() for x in xyz]!=row['binary64_hex']:
   raise ValueError('Exact source coordinate/hex association required')
  points[mapping[tag]]=tuple(Fraction.from_float(float(x)) for x in xyz);words[tag]=xyz
 if set(points)!=set(range(1,11)):raise ValueError('All10 original coordinate rows required')
 for row in shell['vertex_rows']:
  t=row['source_global_node_tag'];xyz=words[t]
  if mapping[t]!=row['local_node_tag'] or struct.pack('<3d',*xyz).hex()!=row['binary64_little_endian_bytes_hex']:
   raise ValueError('All9 fixed source coordinate words must match the common shell')
 cells={r['tetrahedron_tag']:[mapping[t] for t in r['node_tags']] for r in observation['native_ordered_cell_rows']}
 if len(cells)!=14 or any(10 not in row for row in cells.values()):raise ValueError('Complete original cone rows required')
 return points,cells,mapping


def saved_candidate(worker,arrays,shell,peer,acceptance,peer_bindings):
 a=arrays['saved_reopen'];state=worker['saved_reopen'];quality=state['quality']['SICN']
 if (worker.get('status')!='completed_specific_cavity_Netgen_only'
     or any(worker.get(k) is not True for k in ['fixture_procedural_checks_passed','actual_SICN_gate_passed','saved_mesh_identity_exact','bound_inputs_unchanged','geometry_flag_full_state_unchanged','exact_boundary_bits_faces_classifications'])
     or any(worker.get(k) is not False for k in ['head_execution_authorized','stitching_authorized','native_head_application_authorized','engineering_accepted','physics_qualified','manufacturing_authorized'])
     or worker.get('upstream_census_launch_deviation_sha256')!='d60fff297c6c45dc92e117262e36ffde36e2169d53fcd32ce2b79fabde5eebc3'
     or worker.get('declared_controller_command_conformant') is not False
     or worker.get('full_tiny_arrays_sha256')!=INPUTS[ARRAYS] or worker['after']!=state or arrays['after']!=a
     or (state.get('nodes'),state.get('tetrahedra'),state.get('referenced_interior_nodes'),state.get('unreferenced_nodes'))!=(10,14,1,0)
     or (quality.get('count'),quality.get('below_point1_count'),quality.get('nonpositive_count'))!=(14,0,0)
     or type(quality.get('minimum')) not in (int,float) or not math.isfinite(quality['minimum']) or quality['minimum']<.1
     or len(a['node_tags'])!=10 or any(type(t) is not int or t<=0 for t in a['node_tags']) or a['node_tags']!=sorted(set(a['node_tags'])) or len(a['coordinates_mm'])!=10
     or len(a['tetra_tags'])!=14 or a['tetra_tags']!=sorted(set(a['tetra_tags'])) or len(a['tetra_node_tags'])!=14
     or peer.get('schema')!='962-apex1613031-Netgen-result-peer/v1'
     or peer.get('decision')!='CLEAR_COMPLETED_LOCAL_SOFTWARE_QUALITY_PASS_ONLY_NO_DOMAIN_OR_HEAD_ADMISSION'
     or peer.get('bindings',{}).get('sha256')!=INPUTS[PEER_BINDINGS]
     or peer.get('checked',{}).get('negative_baseline_d60false_historical1435493_label_and_false_qualifications_retained') is not True
     or peer_bindings.get('schema')!='962-apex1613031-Netgen-result-peer-bindings/v1'
     or peer_bindings.get('full8_output_inventory',{}).get('fixture-report.json')!={'path':WORKER,'sha256':INPUTS[WORKER],'bytes':17220}
     or peer_bindings.get('full8_output_inventory',{}).get('arrays.json')!={'path':ARRAYS,'sha256':INPUTS[ARRAYS],'bytes':13885}
     or peer_bindings.get('d60_historical_command_conformant') is not False
     or acceptance.get('schema')!='962-apex1613031-root-Netgen-result-peer-acceptance/v1'
     or acceptance.get('decision')!='ACCEPT_COMPLETED_LOCAL_SOFTWARE_QUALITY_PASS_ONLY'
     or acceptance.get('peer',{}).get('sha256')!=INPUTS[PEER]
     or acceptance.get('peer_bindings',{}).get('sha256')!=INPUTS[PEER_BINDINGS]
     or acceptance.get('historical_d60_command_conformant') is not False
     or any(acceptance.get(k) is not False for k in ['next_domain_query_execution_authorized','outside_owner_context_query_authorized','head_execution_authorized','stitching_authorized','feasibility_accepted','engineering_accepted','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized'])):
  raise ValueError('Exact completed10-node14-cell local quality candidate and stopped peer/root acceptance required')
 points={};words={}
 for tag,xyz in zip(a['node_tags'],a['coordinates_mm']):
  if len(xyz)!=3 or any(type(x) is not float or not math.isfinite(x) for x in xyz):
   raise ValueError('Complete finite binary64 candidate coordinate rows required')
  points[tag]=tuple(Fraction.from_float(x) for x in xyz);words[tag]=xyz
 if len(shell['vertex_rows'])!=9 or [row['local_node_tag'] for row in shell['vertex_rows']]!=list(range(1,10)):
  raise ValueError('Exact9 ordered fixed shell rows required')
 for row in shell['vertex_rows']:
  tag=row['local_node_tag']
  if tag not in words or struct.pack('<3d',*words[tag]).hex()!=row['binary64_little_endian_bytes_hex']:
   raise ValueError('All9 source shell binary64 words must remain fixed')
 classes=state.get('node_classifications',[])
 if (len(classes)!=10 or any(len(row)!=2 or any(type(x) is not int for x in row) for row in classes)
     or len(dict(classes))!=10 or set(dict(classes))!=set(points)
     or any(dim!=(2 if tag in range(1,10) else 3) for tag,dim in classes)):
  raise ValueError('Actual tagged9-shell/one-interior classification lookup required')
 cells=dict(zip(a['tetra_tags'],a['tetra_node_tags']))
 if (any(type(t) is not int or t<=0 for t in cells)
     or any(len(row)!=4 or len(set(row))!=4 or any(type(t) is not int for t in row) or not set(row)<=set(points) for row in cells.values())
     or set().union(*(set(row) for row in cells.values()))!=set(points)):
  raise ValueError('Complete ordered TET4 membership and no orphan node required')
 return points,cells


def main(contract_path,digest):
 start=time.monotonic();path=Path(contract_path)
 if not re.fullmatch('[0-9a-f]{64}',digest) or path.is_symlink() or sha(path)!=digest:raise ValueError('Exact external actual contract required')
 c=json.loads(path.read_text())
 if (c.get('schema')!='962-apex1613031-old14-new14-domain-actual/v1' or c.get('diagnostic_execution_authorized') is not True
     or c.get('root_and_peer_review_complete') is not True or c.get('native_execution_authorized') is not False
     or c.get('qualification')!=QUALIFICATION or c.get('automatic_retry') is not False
     or c.get('upstream_census_launch_deviation_sha256')!='d60fff297c6c45dc92e117262e36ffde36e2169d53fcd32ce2b79fabde5eebc3'
     or c.get('declared_controller_command_conformant') is not False
     or c.get('method')!='all91_old_and91_new_exact_pairs_and_common_shell' or c.get('output_directory')!=OUTPUT
     or c.get('source_sha256')!=sha(__file__) or c.get('python_sha256')!=sha(Path(sys.executable).resolve())):
  raise ValueError('One reviewed stdlib-only local domain diagnostic required')
 pins=c['input_hashes']
 if any(pins.get(k)!=v for k,v in INPUTS.items()):raise ValueError('Every consumed record/helper must be direct-pinned')
 for k,v in pins.items():
  f=ROOT/k
  if Path(k).is_absolute() or f.is_symlink() or not f.resolve().is_relative_to(ROOT) or sha(f)!=v:raise ValueError('Before input drift')
 out=ROOT/OUTPUT
 if out.exists() or out.is_symlink() or out.resolve()!=out:raise ValueError('Fresh raw canonical output required')
 spec=importlib.util.spec_from_file_location('frozen_exact_local_pair_helper',ROOT/HELPER)
 helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper) # stdlib-only definitions; never main().
 observation=json.loads((ROOT/OBSERVATION).read_text());shell=json.loads((ROOT/SHELL).read_text())
 worker=json.loads((ROOT/WORKER).read_text());arrays=json.loads((ROOT/ARRAYS).read_text());peer=json.loads((ROOT/PEER).read_text())
 acceptance=json.loads((ROOT/ACCEPTANCE).read_text());peer_bindings=json.loads((ROOT/PEER_BINDINGS).read_text())
 new_points,new_cells=saved_candidate(worker,arrays,shell,peer,acceptance,peer_bindings);old_points,old_cells,mapping=original(observation,shell)
 expected=[row['local_node_tags'] for row in shell['oriented_triangle_rows']]
 if len(expected)!=14 or len({tuple(sorted(f)) for f in expected})!=14:raise ValueError('Exactly14 unique frozen shell faces required')
 old,old_volume=complex_rows(helper,old_points,old_cells,expected);new,new_volume=complex_rows(helper,new_points,new_cells,expected)
 if old['internal_face_pairs']!=21 or new['internal_face_pairs']!=21:raise ValueError('Exact21/21 complete opposite internal pair counts required')
 if any(row['exact_point1_gate_passed'] is not True for row in new['quality_rows']):raise ValueError('All14 exact SICN squared at least1/100 required')
 if any(old_points[t]!=new_points[t] for t in range(1,10)):raise ValueError('Common9 exact shell coordinates differ')
 if old_volume!=new_volume or helper.rational(old_volume)!={k:str(v) for k,v in shell['exact_enclosed_volume_mm3'].items()}:
  raise ValueError('Exact common-shell signed-volume bookkeeping differs')
 pair_results={};pair_failures={}
 for name,points,cells,count in [('old',old_points,old_cells,91),('candidate',new_points,new_cells,91)]:
  pairs=[]
  for first,second in combinations(sorted(cells),2):
   row=helper.pair_check(points,cells[first],cells[second]);row['tetrahedron_tags']=[first,second];pairs.append(row)
  if len(pairs)!=count:raise ValueError('Complete fixed-case unordered pair enumeration required')
  pair_results[name]=pairs;pair_failures[name]=sum(not row['intersection_equals_tagged_shared_simplex'] for row in pairs)
 failures=sum(pair_failures.values())
 if any(sha(ROOT/k)!=v for k,v in pins.items()) or sha(path)!=digest:raise ValueError('After input/contract drift')
 report=dict(schema='962-exact-apex1613031-old14-new14-domain-result/v1',
  status='same_compact_oriented_local_domain' if failures==0 else 'pair_embedding_failed_no_domain_certificate',
  upstream_census_launch_deviation_sha256='d60fff297c6c45dc92e117262e36ffde36e2169d53fcd32ce2b79fabde5eebc3',declared_controller_command_conformant=False,
  source_sha256=c['source_sha256'],contract_sha256=digest,input_hashes=pins,old=old,candidate=new,
  original_global_to_comparison_node_tags=mapping,old_complete_unordered_pairs=91,candidate_complete_unordered_pairs=91,
  complete_unordered_pairs=182,plane_triples_enumerated=182*56,pair_failures=pair_failures,pair_results=pair_results,
  exact_common9_coordinate_words=True,exact_identical_oriented14_boundary=True,exact_signed_volume_identity=True,
  exact_old_pair_embedding=pair_failures['old']==0,exact_candidate_pair_embedding=pair_failures['candidate']==0,
  local_domain_equivalence_proved=failures==0,
  argument='Finite exact positive embedded3-chains in R3 have the same geometric oriented boundary. Their compact difference has zero boundary; its integer multiplicity is constant and zero outside bounded support, hence zero. Multiplicity-one interiors imply identical closed tetrahedral unions.',
  assumptions_checked=['exact stored binary64 coordinates','positive nondegenerate old14 and candidate14 cells','complete21/21 opposite internal-face pairs','exact identical oriented14 shell and fixed9 coordinate words','complete91 old and91 candidate exact pair embeddings'],
  source_candidate_report_sha256=INPUTS[WORKER],source_candidate_arrays_sha256=INPUTS[ARRAYS],source_candidate_independent_peer_sha256=INPUTS[PEER],source_candidate_root_acceptance_sha256=INPUTS[ACCEPTANCE],
  scope='Relative local occupied-domain equality only; no new proof of original full-head embedding, outside non-overlap, connected-neighbor join, head edit or physical validity.',
  qualification=QUALIFICATION,native_optimizer_or_meshwrite_calls=0,coordinates_changed=False,bound_inputs_unchanged=True,wall_seconds=time.monotonic()-start)
 out.mkdir()
 with (out/'report.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
 return 0 if failures==0 else 2

if __name__=='__main__':raise SystemExit(main(*sys.argv[1:]))
