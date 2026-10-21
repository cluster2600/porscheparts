"""HELD old28 exact pair certificate and common-shell local domain equality; no head action."""
from pathlib import Path
from fractions import Fraction
from itertools import combinations
import hashlib,importlib.util,json,math,re,struct,sys,time
ROOT=Path(__file__).resolve().parents[3]
OUTPUT='work/962-engineering/domain-equivalence-001'
QUALIFICATION=dict(native_application_authorized=False,head_execution_authorized=False,stitching_authorized=False,
 engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
HELPER='work/962-engineering/fixed-shell-coupled-embedding-prep-001/check_embedding.py'
OBSERVATION='work/962-engineering/direct-sicn-apex1435493-cavity-study-001/saved-star-observation.json'
SHELL='work/962-engineering/direct-sicn-apex1435493-cavity-study-001/local-shell-input-001.json'
DIAGNOSTIC='work/962-engineering/fixed-shell-coupled-sicn-001/diagnostic.json'
ARRAYS='work/962-engineering/fixed-shell-netgen-apex1435493-001/arrays.json'
PRIOR='work/962-engineering/fixed-shell-coupled-embedding-001/report.json'
PEER='work/962-engineering/fixed-shell-coupled-embedding-result-peer-001/review.json'
INPUTS={'work/962-engineering/fixed-shell-coupled-embedding-prep-001/check_embedding.py': '1b489cc8149f4b5db8f90c594e32fe4c09b5db00151df6b1cfc88362d1018134', 'work/962-engineering/direct-sicn-apex1435493-cavity-study-001/saved-star-observation.json': '53a1fb5696d46c8773eea0ffd3a971706946b380a0b3a5f5ba41d1d6a121d15a', 'work/962-engineering/direct-sicn-apex1435493-cavity-study-001/local-shell-input-001.json': 'a6f15db60967807b057e357b8f159fa510c4a8cf6e3cb44c4327323c070398c8', 'work/962-engineering/fixed-shell-coupled-sicn-001/diagnostic.json': 'e9184514108a194e9f483c5bfb20ffef9d8334cddd01f60806d97b96f84f532a', 'work/962-engineering/fixed-shell-netgen-apex1435493-001/arrays.json': 'ace411a27a13332129f515ac456ab453cbede0920fe115bdb82057092e665e5f', 'work/962-engineering/fixed-shell-coupled-embedding-001/report.json': '478a6e42824772b181ed0d8f9d3523f6fe4e0c07043a9cdc0afe1916f7fe7240', 'work/962-engineering/fixed-shell-coupled-embedding-result-peer-001/review.json': '24ba3917b38c238b9d9e8faa4af0e254c2d6578125e25294fc8ab61678a2589c'}
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
 if observation.get('apex')!=1435493 or len(observation['native_ordered_cell_rows'])!=28 or len(observation['selected_node_rows'])!=17:
  raise ValueError('Exact frozen28cell/17node source star required')
 mapping={t:i+1 for i,t in enumerate(shell['local_to_global_node_tags'])};mapping[1435493]=17
 if len(mapping)!=17 or shell['global_to_local_node_tags']!={str(t):i+1 for i,t in enumerate(shell['local_to_global_node_tags'])}:
  raise ValueError('Specific exact shell inverse mapping required')
 points={};words={}
 for row in observation['selected_node_rows']:
  tag=row['node_tag'];xyz=row['coordinates_mm']
  if tag not in mapping or len(xyz)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in xyz) or [float(x).hex() for x in xyz]!=row['binary64_hex']:
   raise ValueError('Exact source coordinate/hex association required')
  points[mapping[tag]]=tuple(Fraction.from_float(float(x)) for x in xyz);words[tag]=xyz
 if set(points)!=set(range(1,18)):raise ValueError('All17 original coordinate rows required')
 for row in shell['vertex_rows']:
  t=row['source_global_node_tag'];xyz=words[t]
  if mapping[t]!=row['local_node_tag'] or struct.pack('<3d',*xyz).hex()!=row['binary64_little_endian_bytes_hex']:
   raise ValueError('All16 fixed source coordinate words must match the common shell')
 cells={r['tetrahedron_tag']:[mapping[t] for t in r['node_tags']] for r in observation['native_ordered_cell_rows']}
 if len(cells)!=28 or any(17 not in row for row in cells.values()):raise ValueError('Complete original cone rows required')
 return points,cells,mapping


def prior_candidate_proof(prior,peer,cells):
 expected=list(combinations(sorted(cells),2))
 if (prior.get('status')!='complete_exact_pair_intersection_pass' or prior.get('source_diagnostic_sha256')!=INPUTS[DIAGNOSTIC]
     or prior.get('source_sha256')!=INPUTS[HELPER] or prior.get('nodes')!=19 or prior.get('tetrahedra')!=39
     or prior.get('complete_unordered_pairs')!=741 or prior.get('pair_failures')!=0
     or prior.get('exact_pairwise_tagged_complex_embedding') is not True
     or prior.get('all39_exact_positive_quality_prerequisite') is not True or prior.get('bound_inputs_unchanged') is not True
     or peer.get('decision')!='CLEAR_COMPLETE_EXACT_SAVED_LOCAL_PAIRWISE_EMBEDDING'):
  raise ValueError('Exact completed candidate741 report and independent peer required')
 rows=prior['pair_results']
 if len(rows)!=741 or [tuple(r['tetrahedron_tags']) for r in rows]!=expected or any(r['intersection_equals_tagged_shared_simplex'] is not True or r['illegal_intersection_vertices']!=0 for r in rows):
  raise ValueError('Complete saved candidate741 verdict coverage required; never rerun or relabel it')


def main(contract_path,digest):
 start=time.monotonic();path=Path(contract_path)
 if not re.fullmatch('[0-9a-f]{64}',digest) or path.is_symlink() or sha(path)!=digest:raise ValueError('Exact external actual contract required')
 c=json.loads(path.read_text())
 if (c.get('schema')!='962-old28-domain-equivalence-actual/v1' or c.get('diagnostic_execution_authorized') is not True
     or c.get('root_and_peer_review_complete') is not True or c.get('native_execution_authorized') is not False
     or c.get('qualification')!=QUALIFICATION or c.get('automatic_retry') is not False
     or c.get('method')!='all378_old_pairs_and_exact_common_oriented_shell' or c.get('output_directory')!=OUTPUT
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
 helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper) # stdlib-only top level; never main()
 observation=json.loads((ROOT/OBSERVATION).read_text());shell=json.loads((ROOT/SHELL).read_text())
 diagnostic=json.loads((ROOT/DIAGNOSTIC).read_text());arrays=json.loads((ROOT/ARRAYS).read_text())
 new_points,new_cells=helper.candidate(diagnostic,arrays,shell)
 old_points,old_cells,mapping=original(observation,shell)
 expected=[r['local_node_tags'] for r in shell['oriented_triangle_rows']]
 if len(expected)!=28 or len({tuple(sorted(f)) for f in expected})!=28:raise ValueError('Exactly28 unique frozen shell faces required')
 old,old_volume=complex_rows(helper,old_points,old_cells,expected);new,new_volume=complex_rows(helper,new_points,new_cells,expected)
 if old['internal_face_pairs']!=42 or new['internal_face_pairs']!=64:raise ValueError('Exact42/64 complete internal pair counts required')
 if any(old_points[t]!=new_points[t] for t in range(1,17)):raise ValueError('Common16 exact coordinates differ')
 if old_volume!=new_volume or helper.rational(old_volume)!={k:str(v) for k,v in shell['exact_enclosed_volume_mm3'].items()}:
  raise ValueError('Exact common-shell signed-volume bookkeeping differs')
 prior=json.loads((ROOT/PRIOR).read_text());peer=json.loads((ROOT/PEER).read_text());prior_candidate_proof(prior,peer,new_cells)
 pairs=[]
 for first,second in combinations(sorted(old_cells),2):
  row=helper.pair_check(old_points,old_cells[first],old_cells[second]);row['tetrahedron_tags']=[first,second];pairs.append(row)
 if len(pairs)!=378:raise ValueError('Complete28choose2 result required')
 failures=sum(not r['intersection_equals_tagged_shared_simplex'] for r in pairs)
 if any(sha(ROOT/k)!=v for k,v in pins.items()) or sha(path)!=digest:raise ValueError('After input/contract drift')
 report=dict(schema='962-exact-old28-candidate39-domain-equivalence/v1',status='same_compact_oriented_local_domain' if failures==0 else 'old_pair_embedding_failed_no_domain_certificate',
  source_sha256=c['source_sha256'],contract_sha256=digest,input_hashes=pins,old=old,candidate=new,
  original_global_to_comparison_node_tags=mapping,old_complete_unordered_pairs=378,old_pair_failures=failures,old_pair_results=pairs,
  candidate741_proof_sha256=INPUTS[PRIOR],candidate_independent_peer_sha256=INPUTS[PEER],candidate_pair_predicates_reexecuted=False,
  exact_common16_coordinate_words=True,exact_identical_oriented28_boundary=True,exact_signed_volume_identity=True,
  exact_old_pair_embedding=failures==0,local_domain_equivalence_proved=failures==0,
  argument='Finite exact positive embedded3-chains in R3 have the same geometric oriented boundary. Their compact difference has zero boundary; its integer multiplicity is constant and zero outside bounded support, hence zero. Multiplicity-one interiors imply identical closed tetrahedral unions.',
  assumptions_checked=['exact stored binary64 coordinates','positive nondegenerate old28 and candidate39 cells','complete42/64 opposite internal-face pairs','exact identical oriented28 shell and fixed16 coordinates','old378 embedding plus immutable independently reviewed candidate741 embedding'],
  scope='Relative local occupied-domain equality only; no new proof of original full-head embedding, outside non-overlap, connected-neighbor join, head edit or physical validity.',
  qualification=QUALIFICATION,native_optimizer_or_meshwrite_calls=0,coordinates_changed=False,bound_inputs_unchanged=True,wall_seconds=time.monotonic()-start)
 out.mkdir()
 with (out/'report.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
 return 0 if failures==0 else 2

if __name__=='__main__':raise SystemExit(main(*sys.argv[1:]))
