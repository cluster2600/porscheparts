"""HELD exact old60/new101 pair embedding and common-shell local-domain query; no head action."""
from pathlib import Path
from fractions import Fraction
from itertools import combinations
import hashlib,importlib.util,json,math,re,struct,sys,time
ROOT=Path(__file__).resolve().parents[3]
OUTPUT='work/962-engineering/apex1474426-domain-equivalence-001'
QUALIFICATION=dict(native_application_authorized=False,head_execution_authorized=False,stitching_authorized=False,
 engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
HELPER='work/962-engineering/fixed-shell-coupled-embedding-prep-001/check_embedding.py'
CHAIN_SOURCE='work/962-engineering/domain-equivalence-prep-001/certify_domain.py'
OBSERVATION='work/962-engineering/direct-sicn-apex1474426-cavity-study-001/saved-star-observation.json'
SHELL='work/962-engineering/direct-sicn-apex1474426-cavity-study-001/local-shell-input-001.json'
WORKER='work/962-engineering/fixed-shell-netgen-apex1474426-001/fixture-report.json'
ARRAYS='work/962-engineering/fixed-shell-netgen-apex1474426-001/arrays.json'
PEER='work/962-engineering/fixed-shell-netgen-apex1474426-result-peer-001/review.json'
INPUTS={'work/962-engineering/fixed-shell-coupled-embedding-prep-001/check_embedding.py': '1b489cc8149f4b5db8f90c594e32fe4c09b5db00151df6b1cfc88362d1018134', 'work/962-engineering/domain-equivalence-prep-001/certify_domain.py': '0fe593d385e5a0ab4944528fa1b869ddf2c41c28d050576afe9be18213462296', 'work/962-engineering/direct-sicn-apex1474426-cavity-study-001/saved-star-observation.json': '3d80523e2ebd2a92584546f89dc71d35f401696338f99f45480d196a25f840f6', 'work/962-engineering/direct-sicn-apex1474426-cavity-study-001/local-shell-input-001.json': '6ad00be791b8b752106b5324b9f80df314f7458d8d0475b1ffc1a053bc04d12a', 'work/962-engineering/fixed-shell-netgen-apex1474426-001/fixture-report.json': '043c06613ce159acdc4432e0d155dcddc02fa909b02fe955c5f78e6d1b38f076', 'work/962-engineering/fixed-shell-netgen-apex1474426-001/arrays.json': 'ea3c5864a6b607afaf8428a806f65d8e3a81a6e4548e1588dd17b72ea44553b5', 'work/962-engineering/fixed-shell-netgen-apex1474426-result-peer-001/review.json': '12e4829d9a8a02e382c326ea5ef05f58c81f98c1b8b8b8df842846654ba60bd1'}
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
 if observation.get('apex')!=1474426 or len(observation['native_ordered_cell_rows'])!=60 or len(observation['selected_node_rows'])!=33:
  raise ValueError('Exact frozen60cell/33node source star required')
 mapping={t:i+1 for i,t in enumerate(shell['local_to_global_node_tags'])};mapping[1474426]=33
 if len(mapping)!=33 or shell['global_to_local_node_tags']!={str(t):i+1 for i,t in enumerate(shell['local_to_global_node_tags'])}:
  raise ValueError('Specific exact shell inverse mapping required')
 points={};words={}
 for row in observation['selected_node_rows']:
  tag=row['node_tag'];xyz=row['coordinates_mm']
  if tag not in mapping or len(xyz)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in xyz) or [float(x).hex() for x in xyz]!=row['binary64_hex']:
   raise ValueError('Exact source coordinate/hex association required')
  points[mapping[tag]]=tuple(Fraction.from_float(float(x)) for x in xyz);words[tag]=xyz
 if set(points)!=set(range(1,34)):raise ValueError('All33 original coordinate rows required')
 for row in shell['vertex_rows']:
  t=row['source_global_node_tag'];xyz=words[t]
  if mapping[t]!=row['local_node_tag'] or struct.pack('<3d',*xyz).hex()!=row['binary64_little_endian_bytes_hex']:
   raise ValueError('All32 fixed source coordinate words must match the common shell')
 cells={r['tetrahedron_tag']:[mapping[t] for t in r['node_tags']] for r in observation['native_ordered_cell_rows']}
 if len(cells)!=60 or any(33 not in row for row in cells.values()):raise ValueError('Complete original cone rows required')
 return points,cells,mapping


def saved_candidate(worker,arrays,shell,peer):
 a=arrays['saved_reopen'];state=worker['saved_reopen'];quality=state['quality']['SICN']
 if (worker.get('status')!='completed_specific_cavity_Netgen_only'
     or any(worker.get(k) is not True for k in ['fixture_procedural_checks_passed','actual_SICN_gate_passed','saved_mesh_identity_exact','bound_inputs_unchanged','geometry_flag_full_state_unchanged','exact_boundary_bits_faces_classifications'])
     or any(worker.get(k) is not False for k in ['head_execution_authorized','stitching_authorized','native_head_application_authorized','engineering_accepted','physics_qualified','manufacturing_authorized'])
     or worker.get('full_tiny_arrays_sha256')!=INPUTS[ARRAYS] or worker['after']!=state or arrays['after']!=a
     or (state.get('nodes'),state.get('tetrahedra'),state.get('referenced_interior_nodes'),state.get('unreferenced_nodes'))!=(40,101,8,0)
     or (quality.get('count'),quality.get('below_point1_count'),quality.get('nonpositive_count'))!=(101,0,0)
     or a['node_tags']!=list(range(1,41)) or len(a['coordinates_mm'])!=40
     or len(a['tetra_tags'])!=101 or a['tetra_tags']!=sorted(set(a['tetra_tags'])) or len(a['tetra_node_tags'])!=101
     or peer.get('decision')!='CLEAR_COMPLETED_LOCAL_SICN_GATE_PASS_ONLY'
     or peer.get('bindings',{}).get('report_sha256')!=INPUTS[WORKER] or peer['bindings'].get('arrays_sha256')!=INPUTS[ARRAYS]):
  raise ValueError('Exact completed40-node101-cell saved Netgen candidate and stopped peer required')
 points={};words={}
 for tag,xyz in zip(a['node_tags'],a['coordinates_mm']):
  if len(xyz)!=3 or any(type(x) is not float or not math.isfinite(x) for x in xyz):
   raise ValueError('Complete finite binary64 candidate coordinate rows required')
  points[tag]=tuple(Fraction.from_float(x) for x in xyz);words[tag]=xyz
 if len(shell['vertex_rows'])!=32 or [row['local_node_tag'] for row in shell['vertex_rows']]!=list(range(1,33)):
  raise ValueError('Exact32 ordered fixed shell rows required')
 for row in shell['vertex_rows']:
  xyz=words[row['local_node_tag']]
  if struct.pack('<3d',*xyz).hex()!=row['binary64_little_endian_bytes_hex']:
   raise ValueError('All32 source shell binary64 words must remain fixed')
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
 if (c.get('schema')!='962-apex1474426-old60-new101-domain-actual/v1' or c.get('diagnostic_execution_authorized') is not True
     or c.get('root_and_peer_review_complete') is not True or c.get('native_execution_authorized') is not False
     or c.get('qualification')!=QUALIFICATION or c.get('automatic_retry') is not False
     or c.get('method')!='all1770_old_and5050_new_exact_pairs_and_common_shell' or c.get('output_directory')!=OUTPUT
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
 new_points,new_cells=saved_candidate(worker,arrays,shell,peer);old_points,old_cells,mapping=original(observation,shell)
 expected=[row['local_node_tags'] for row in shell['oriented_triangle_rows']]
 if len(expected)!=60 or len({tuple(sorted(f)) for f in expected})!=60:raise ValueError('Exactly60 unique frozen shell faces required')
 old,old_volume=complex_rows(helper,old_points,old_cells,expected);new,new_volume=complex_rows(helper,new_points,new_cells,expected)
 if old['internal_face_pairs']!=90 or new['internal_face_pairs']!=172:raise ValueError('Exact90/172 complete opposite internal pair counts required')
 if any(row['exact_point1_gate_passed'] is not True for row in new['quality_rows']):raise ValueError('All101 exact SICN squared at least1/100 required')
 if any(old_points[t]!=new_points[t] for t in range(1,33)):raise ValueError('Common32 exact shell coordinates differ')
 if old_volume!=new_volume or helper.rational(old_volume)!={k:str(v) for k,v in shell['exact_enclosed_volume_mm3'].items()}:
  raise ValueError('Exact common-shell signed-volume bookkeeping differs')
 pair_results={};pair_failures={}
 for name,points,cells,count in [('old',old_points,old_cells,1770),('candidate',new_points,new_cells,5050)]:
  pairs=[]
  for first,second in combinations(sorted(cells),2):
   row=helper.pair_check(points,cells[first],cells[second]);row['tetrahedron_tags']=[first,second];pairs.append(row)
  if len(pairs)!=count:raise ValueError('Complete fixed-case unordered pair enumeration required')
  pair_results[name]=pairs;pair_failures[name]=sum(not row['intersection_equals_tagged_shared_simplex'] for row in pairs)
 failures=sum(pair_failures.values())
 if any(sha(ROOT/k)!=v for k,v in pins.items()) or sha(path)!=digest:raise ValueError('After input/contract drift')
 report=dict(schema='962-exact-apex1474426-old60-new101-domain-result/v1',
  status='same_compact_oriented_local_domain' if failures==0 else 'pair_embedding_failed_no_domain_certificate',
  source_sha256=c['source_sha256'],contract_sha256=digest,input_hashes=pins,old=old,candidate=new,
  original_global_to_comparison_node_tags=mapping,old_complete_unordered_pairs=1770,candidate_complete_unordered_pairs=5050,
  complete_unordered_pairs=6820,plane_triples_enumerated=6820*56,pair_failures=pair_failures,pair_results=pair_results,
  exact_common32_coordinate_words=True,exact_identical_oriented60_boundary=True,exact_signed_volume_identity=True,
  exact_old_pair_embedding=pair_failures['old']==0,exact_candidate_pair_embedding=pair_failures['candidate']==0,
  local_domain_equivalence_proved=failures==0,
  argument='Finite exact positive embedded3-chains in R3 have the same geometric oriented boundary. Their compact difference has zero boundary; its integer multiplicity is constant and zero outside bounded support, hence zero. Multiplicity-one interiors imply identical closed tetrahedral unions.',
  assumptions_checked=['exact stored binary64 coordinates','positive nondegenerate old60 and candidate101 cells','complete90/172 opposite internal-face pairs','exact identical oriented60 shell and fixed32 coordinate words','complete1770 old and5050 candidate exact pair embeddings'],
  source_candidate_report_sha256=INPUTS[WORKER],source_candidate_arrays_sha256=INPUTS[ARRAYS],source_candidate_independent_peer_sha256=INPUTS[PEER],
  scope='Relative local occupied-domain equality only; no new proof of original full-head embedding, outside non-overlap, connected-neighbor join, head edit or physical validity.',
  qualification=QUALIFICATION,native_optimizer_or_meshwrite_calls=0,coordinates_changed=False,bound_inputs_unchanged=True,wall_seconds=time.monotonic()-start)
 out.mkdir()
 with (out/'report.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
 return 0 if failures==0 else 2

if __name__=='__main__':raise SystemExit(main(*sys.argv[1:]))
