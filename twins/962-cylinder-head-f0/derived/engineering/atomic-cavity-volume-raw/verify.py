"""Verify sealed payload/scalar consistency only; never import scientific software."""
from pathlib import Path, PurePosixPath
import hashlib,json,math

BASE=Path(__file__).resolve().parent
load=lambda name:json.loads((BASE/name).read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=load('receipt.json'); expected=r['payloads']
for name,pin in expected.items():
 relative=PurePosixPath(name)
 assert not relative.is_absolute() and '..' not in relative.parts
 p=BASE/name
 assert p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(BASE)
 assert p.stat().st_size==pin['bytes'] and sha(p)==pin['sha256'],name
for p in BASE.rglob('*'):assert not p.is_symlink(),str(p.relative_to(BASE))
assert {str(p.relative_to(BASE)) for p in BASE.rglob('*') if p.is_file()}==set(expected)|{'receipt.json'}
assert len(expected)==r['payload_count'] and sum(v['bytes'] for v in expected.values())==r['payload_bytes']
o=load('original-records.json')
for name,pin in o['exact_copy_payloads'].items():
 assert expected[name]['sha256']==pin['original_sha256'] and expected[name]['bytes']==pin['bytes']
assert len(o['exact_copy_payloads'])==r['exact_copy_count']
assert len(o['native_artifact_inventory'])==11 and len(o['readback_artifact_inventory'])==6
for name,count in [('native_authorization',19),('surface_admission',129),('readback_contract',173),('readback_external_runtime',3)]:
 assert len(o['input_hash_maps'][name])==count
p=load('projections.json')['projections'];native=p['native_execution']['values'];worker=p['native_worker']['values']
read=load('reports/independent-readback.json');execution=load('reports/readback-execution.json')
assert native['returncode']==2 and native['stop_reason'] is None and native['geometric_volume_gate_passed'] is False
assert execution['returncode']==0 and execution['stop_reason'] is None
for data,window,rsskey,wallkey,count in [(native,'native_process_window_s','max_observed_RSS_bytes','wall_s',243),(execution,'wall_seconds','max_observed_RSS_bytes','wall_seconds',35)]:
 rows=data['RSS_samples'];assert len(rows)==count
 assert all(type(s['RSS_bytes']) is int and s['RSS_bytes']>=0 and math.isfinite(s[wallkey]) and 0<=s[wallkey]<=data[window] for s in rows)
 assert data[rsskey]==max(s['RSS_bytes'] for s in rows)
 assert all(rows[i][wallkey]<=rows[i+1][wallkey] for i in range(len(rows)-1))
assert native['mesh_sha256']==r['mesh_sha256'] and native['mesh_bytes']==211385374
assert read['actual_tetrahedra']==worker['tetrahedra']==3058267
assert read['actual_mesh_nodes']==worker['total_mesh_nodes']==979076
assert read['actual_referenced_interior_nodes']==worker['tetra_referenced_interior_nodes']==77349
assert read['actual_unreferenced_mesh_nodes']==0
for row in worker['quality'].values():assert row['count']==3058267 and row['nonpositive_count']==0 and math.isfinite(row['minimum']) and row['minimum']>0
for name,original in [('SICN','minimum_SICN'),('Jacobian','minimum_jacobian'),('native_volume_mm3','native_volume_mm3')]:
 row=read['direct_native_quality_extrema'][name];old=worker['quality'][original]
 assert row['count']==3058267 and row['nonpositive_count']==0
 assert row['minimum']==old['minimum'] and row['maximum']==old['maximum']
assert read['direct_native_quality_extrema']['SICN']['below_point1_count']==283853
assert read['direct_native_quality_extrema']['SICN']['minimum']==1.234770950435885e-10<.1
assert read['SICN_point1_gate_passed'] is False and read['nonpositive_SICN_tetrahedra']==[]
assert read['fixed_boundary_only_nonpositive_cells'] is True # all(empty): not a positive-poor-cell classification
assert read['independent_signed_volume_mm3']['count']==3058267
assert read['independent_signed_volume_mm3']['nonpositive_count']==0
assert read['independent_signed_volume_mm3']['sum']==915458.1131756522
assert read['independent_signed_volume_mm3']['relative_error_to_candidate']==0
for key in ['sorted_node_tags_sha256','sorted_coordinates_sha256','sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256']:assert read[key]==worker[key]
assert read['exact_source_boundary_coordinates'] and read['exact_sorted_explicit_surface_connectivity']
assert read['retained_only_not_repeated']['tetra_exterior_incidence']==worker['actual_tetra_boundary']
assert read['retained_only_not_repeated']['internal_face_orientation']==worker['internal_tetra_face_orientation']
assert load('reviews/readback-root.json')['independent_OS_PID_absence_check_performed'] is False
for name in ['reports/root-nine-tests.json','reports/root-eight-tests.json']:
 record=load(name);assert record['returncode']==0 and record['all_pins_unchanged'] is True
assert r['volume_mesh_accepted'] is False and r['head_physics_executed'] is False and r['manufacturing_authorized'] is False
print(json.dumps({'status':'sealed_payload_and_retained_scalar_checks_passed','payloads':len(expected),'native_resource_samples':243,'readback_resource_samples':35,'native_or_geometry_queries':0,'volume_mesh_accepted':False}))
