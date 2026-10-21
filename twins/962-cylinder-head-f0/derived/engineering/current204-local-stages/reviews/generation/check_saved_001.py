"""Independent stdlib saved-byte/row arithmetic review; never import a worker."""
from pathlib import Path
from fractions import Fraction
from collections import Counter, defaultdict
import ast,hashlib,json,math,struct,sys,time

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'work/962-engineering'
OUT=Path(__file__).resolve().parent
inputs={}

def digest(raw):return hashlib.sha256(raw).hexdigest()
def read(name,expected=None):
    p=ROOT/name
    assert not Path(name).is_absolute() and '..' not in Path(name).parts
    assert p.is_file() and not p.is_symlink()
    raw=p.read_bytes();h=digest(raw)
    if expected is not None:assert h==expected,name
    if name in inputs:assert inputs[name]==h
    inputs[name]=h
    return raw
def obj(name,expected=None):return json.loads(read(name,expected))
def u64(rows):
    flat=[v for row in rows for v in row] if rows and isinstance(rows[0],list) else rows
    assert all(type(v) is int and v>=0 for v in flat)
    return digest(struct.pack('<'+'Q'*len(flat),*flat))
def f64(rows):
    flat=[v for row in rows for v in row] if rows and isinstance(rows[0],list) else rows
    assert all(type(v) in (int,float) and math.isfinite(v) for v in flat)
    return digest(struct.pack('<'+'d'*len(flat),*flat))
def distribution(values):
    assert values and all(math.isfinite(v) for v in values)
    return dict(count=len(values),minimum=min(values),maximum=max(values),nonpositive_count=sum(v<=0 for v in values),
                below_point1_count=sum(v<.1 for v in values),array_sha256=f64(values))
def oriented(face):return min(tuple(face[i:]+face[:i]) for i in range(3))
def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum((x*y for x,y in zip(a,b)),Fraction(0))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def exact_cell(points):
    e1,e2,e3=[sub(p,points[0]) for p in points[1:]]
    det=dot(e1,cross(e2,e3))
    # Ideal regular-tetrahedron map columns e1, (2e2-e1)/sqrt(3),
    # (3e3-e1-e2)/sqrt(6), evaluated through exact rational squared norms.
    a=e1;b=[2*x-y for x,y in zip(e2,e1)];c=[3*x-y-z for x,y,z in zip(e3,e1,e2)]
    norm=dot(a,a)+dot(b,b)/3+dot(c,c)/6
    ab,ac,bc=cross(a,b),cross(a,c),cross(b,c)
    cof=dot(ab,ab)/3+dot(ac,ac)/6+dot(bc,bc)/18
    assert det>0 and norm>0 and cof>0
    return det,det/6,18*det*det/(norm*cof)

start=time.monotonic()
master_path='work/962-engineering/head-star-current204-generation-root-execution-002/closed-result.json'
master=obj(master_path,'36ee1b22928f0bc08d1d59936bef0256642c29da17d7e44d1260be922d08d334')
continuation=obj('work/962-engineering/head-star-current204-generation-root-execution-002/continuation.json')
index_path='work/962-engineering/head-star-current204-generation-actuals-prep-001/index.json'
index=obj(index_path,master['original_index_sha256'])
child_path='work/962-engineering/head-star-current204-generation-actuals-child-peer-001/review.json'
child=obj(child_path,master['child_peer_sha256']);assert child['decision']=='CLEAR_EXACT_ROOT_ACTUAL_BINDINGS_ONLY' and child['blockers']==[]
manifest_path='work/962-engineering/head-star-current204-local-stages-prep-001/case-manifest.json'
manifest=obj(manifest_path,'3a558ede04cbc52c59e401befb36b8983ebd9b7f57d4266de0bea38fb1a963c5')
batch=obj('work/962-engineering/head-star-current204-batch-shells-001/report.json','4f9fc0354918a907083006484d534c34c3b2621dfcc83b00cc4a4b731f009e86')
cases={r['apex']:r for r in manifest['cases_in_increasing_apex_order']};batch_cases={r['apex']:r for r in batch['all_candidate_star_records']}
source='work/962-engineering/head-star-current204-local-stages-prep-001/generate_case.py'
runner='work/962-engineering/head-star-current204-local-stages-prep-001/run_generation.py'
source_sha='fc1aba0a0ae93995f8fc4eea86d3fe693ce0360ac3f98d158ba5f01ae8983e3d';runner_sha='05b4f8996f1f642120b70be755e6609f7b641041cad1a867ea8da9e56ecb423b'
tree=ast.parse(read(source,source_sha).decode());read(runner,runner_sha)
literal={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
         and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['OPTIONS','RUNTIME','COUNTS']}
remaining=[r['apex'] for r in index['all_original_manifest_cases_in_increasing_apex_order'][1:]]
assert len(remaining)==len(set(remaining))==115 and index['all_original_manifest_cases_in_increasing_apex_order'][0]['apex']==1393275
assert remaining==continuation['remaining_apices_in_original_order']==[r['apex'] for r in master['case_results']]
assert master['held_first_apex']==1393275 and master['remaining115_attempted_once'] is True and master['automatic_retry'] is False and master['backfill'] is False
assert master['no_Netgen_domain_context_or_head_operation_launched'] is True
first_peer_path='work/962-engineering/head-star-current204-generation-first-stop-peer-001/review.json'
first_peer=obj(first_peer_path,'da781c7144571897938835b01e33aa6acb4db6d59917de08a16852e65c844f40')
for row in first_peer['records'].values():read(row['path'],row['sha256'])
first_dir='work/962-engineering/head-star-current204-apex-1393275-generation-001'
assert set(p.name for p in (ROOT/first_dir).iterdir() if p.is_file())==set(first_peer['first_preserved_stop']['complete5_output_inventory'])
for name,row in first_peer['first_preserved_stop']['complete5_output_inventory'].items():assert len(read(first_dir+'/'+name,row['sha256']))==row['bytes']
assert first_peer['first_preserved_stop']['exact_native_identity_assert_cause_unproven'] is True
assert first_peer['first_preserved_stop']['first_case_must_remain_held_no_retry'] is True

ledger=[];common_pins=None;all_exact_q_bad=all_native_calibration=True
totals=Counter();max_errors=defaultdict(float);global_min=None;rss_max=0;index_cases={r['apex']:r for r in index['all_original_manifest_cases_in_increasing_apex_order']}
expected_files={'arrays.json','cavity.msh','execution-receipt.json','fixture-report.json','frozen-contract.json','native.log','reader.py','run_readback.py'}
for ordinal,result in enumerate(master['case_results'],1):
    apex=result['apex'];case=cases[apex];record=batch_cases[apex];shell=record['shell'];nv=case['shell_nodes'];nf=case['shell_faces']
    assert result['ordinal_in_remaining']==ordinal
    rc=obj(result['root_closed_path'],result['root_closed_sha256']);root_dir=str(Path(result['root_closed_path']).parent)
    launch=obj(root_dir+'/launch.json',rc['root_launch_sha256'])
    read(root_dir+'/stdout.log',rc['stdout_sha256']);read(root_dir+'/stderr.log',rc['stderr_sha256'])
    ix=index_cases[apex];actual_raw=read(ix['path'],ix['sha256']);assert len(actual_raw)==ix['bytes'];actual=json.loads(actual_raw)
    directory=actual['output_directory'];assert directory==ix['output_directory']==case['stage_paths']['generation']
    assert set(p.name for p in (ROOT/directory).iterdir() if p.is_file())==expected_files
    assert len(rc['output_files'])==8 and set(rc['output_files'])==expected_files
    for name,row in rc['output_files'].items():assert len(read(directory+'/'+name,row['sha256']))==row['bytes']
    assert read(directory+'/frozen-contract.json')==actual_raw
    assert rc['actual_sha256']==result['actual_sha256']==ix['sha256']==launch['actual_sha256']
    assert rc['child_peer_sha256']==master['child_peer_sha256']==launch['child_peer_sha256']
    assert rc['case_apex']==actual['case_apex']==apex and actual['case_key']==case['case_key'] and actual['case_record_sha256']==case['source_record_sha256']
    assert actual['case_manifest']==manifest_path and actual['case_manifest_sha256']=='3a558ede04cbc52c59e401befb36b8983ebd9b7f57d4266de0bea38fb1a963c5'
    assert actual['reader_sha256']==source_sha and actual['runner_sha256']==runner_sha
    assert rc['output_files']['reader.py']['sha256']==source_sha and rc['output_files']['run_readback.py']['sha256']==runner_sha
    assert actual['options']==literal['OPTIONS'] and actual['expected_runtime']==literal['RUNTIME'] and actual['declared_operation_counts']==literal['COUNTS']
    if common_pins is None:
        common_pins=actual['input_hashes'];assert len(common_pins)==38
        for name,h in common_pins.items():read(name,h)
    else:assert actual['input_hashes']==common_pins
    assert actual['native_execution_authorized'] is True and actual['cavity_generation_authorized'] is True
    for key in ['cavity_Netgen_optimizer_authorized','head_execution_authorized','stitching_authorized','native_head_application_authorized','engineering_accepted','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized','automatic_retry','backfill']:assert actual[key] is False
    assert actual['controls']==dict(wall_seconds=30,sampled_RSS_stop_bytes=1024**3,sampled_output_stop_bytes=16*1024**2,threads=2,
        environment={'PATH':'/usr/bin:/bin','LANG':'C','PYTHONUTF8':'1','OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','VECLIB_MAXIMUM_THREADS':'2','PYTHONDONTWRITEBYTECODE':'1'},hard_OS_quota=False)
    assert actual['root_outer_wall_seconds']==40 and actual['numpy_init_sha256']=='c09e25b58f6b2f8e2cb3c158168f902d447f8171e5ea6513c0aca41ecbda7c2b'
    assert actual['runtime_sha256s']=={'python':'72956ad35cff7691dfed9e04c9593de825ffd5b2fa7e8bc9ae96ce9a1af65621','gmsh_module':'f4b0935cebde899750293d87a643090e5ea33c9b18d249267f507db68a0e01c3','gmsh_library':'def0f5c10988a986e5e879b3db9669d8fe016a81e2d994bbaf2b8497c6b8a58a'}
    w=obj(directory+'/fixture-report.json');receipt=obj(directory+'/execution-receipt.json');arrays=obj(directory+'/arrays.json');log=read(directory+'/native.log').decode()
    assert w['schema']=='962-finite-selected-current204-generation/v1' and w['status']=='completed_finite_selected_cavity_generation_only' and w['stage']=='completed_all_local_checks' and 'error' not in w
    assert all(w[k] is True for k in ['fixture_procedural_checks_passed','saved_mesh_identity_exact','exact_boundary_bits_faces_classifications','bound_inputs_unchanged','all_shell_nodes_fixed_only_for_this_cavity_generation'])
    assert w['actual_SICN_gate_passed'] is False and w['actual_SICN_threshold']==.1 and w['next_stage']=='one_Netgen'
    assert w['native_operation_counts']==literal['COUNTS'] and w['call_counts_are_attempts'] is True and w['options']==literal['OPTIONS']
    assert w['case_apex']==apex and w['case_key']==case['case_key'] and w['case_record_sha256']==case['source_record_sha256'] and w['local_shell_serialized_sha256']==case['shell_serialized_sha256']
    assert w['case_manifest_sha256']==actual['case_manifest_sha256'] and w['source_batch_sha256']=='4f9fc0354918a907083006484d534c34c3b2621dfcc83b00cc4a4b731f009e86'
    assert w['frozen_contract_sha256']==ix['sha256'] and w['runtime']==actual['expected_runtime'] and w['runtime_sha256s']==actual['runtime_sha256s']
    assert w['full_tiny_arrays_sha256']==rc['output_files']['arrays.json']['sha256'] and w['mesh_sha256']==rc['output_files']['cavity.msh']['sha256'] and w['mesh_bytes']==rc['output_files']['cavity.msh']['bytes']
    msh=read(directory+'/cavity.msh');assert msh.startswith(b'$MeshFormat\n4.1 1 8\n')
    assert w['original_source_classifications']==shell['original_source_classifications'] and w['local_to_global_shell_node_tags']==shell['local_to_global_node_tags']
    assert w['shell']['vertices']==nv and w['shell']['faces']==nf
    assert Fraction(int(w['shell']['exact_volume_mm3']['numerator']),int(w['shell']['exact_volume_mm3']['denominator']))==Fraction(**case['exact_volume_mm3'])
    assert set(arrays)=={'after_generation','saved_reopen'}
    assert json.dumps(arrays['after_generation'],sort_keys=True,allow_nan=False)==json.dumps(arrays['saved_reopen'],sort_keys=True,allow_nan=False)
    assert json.dumps(w['after_generation'],sort_keys=True,allow_nan=False)==json.dumps(w['saved_reopen'],sort_keys=True,allow_nan=False)
    state=arrays['saved_reopen'];r=w['saved_reopen'];nt=state['node_tags'];xyz=state['coordinates_mm'];et=state['tetra_tags'];en=state['tetra_node_tags'];n=len(nt);m=len(et)
    assert nt==sorted(set(nt)) and all(t>0 for t in nt) and et==sorted(set(et)) and all(t>0 for t in et)
    assert len(xyz)==n and len(en)==m and all(len(p)==3 and all(math.isfinite(x) for x in p) for p in xyz)
    assert all(len(row)==4 and len(set(row))==4 for row in en) and set(t for row in en for t in row)==set(nt)
    assert len({struct.pack('<3d',*p) for p in xyz})==n and len({tuple(sorted(row)) for row in en})==m
    positions={tag:i for i,tag in enumerate(nt)}
    for v in shell['vertex_rows']:
        tag=v['local_node_tag'];p=xyz[positions[tag]];assert tag<=nv and struct.pack('<3d',*p).hex()==v['binary64_little_endian_bytes_hex'] and [float(x).hex() for x in p]==v['binary64_hex']
    assert r['nodes']==r['referenced_nodes']==n and r['tetrahedra']==m and r['referenced_interior_nodes']==sum(t>nv for t in nt) and r['unreferenced_nodes']==r['duplicate_tetrahedra']==0
    assert r['node_classifications']==[[t,2 if t<=nv else 3] for t in nt] and r['node_entity_classifications']==[[t,2 if t<=nv else 3,1] for t in nt]
    assert r['node_counts_by_classification_dimension']=={'0':0,'1':0,'2':nv,'3':sum(t>nv for t in nt)} and r['no_curve_or_surface_periodic_mapping'] is True
    assert r['sorted_node_tags_sha256']==u64(nt) and r['sorted_coordinates_sha256']==f64(xyz) and r['tetra_tags_sha256']==u64(et) and r['tagged_tetra_connectivity_sha256']==u64(en)
    assert r['canonical_cells_sha256']==u64(sorted(sorted(row) for row in en))
    for name,values in state['native_qualities'].items():assert distribution(values)==r['quality'][name] and len(values)==m
    signed=state['independent_signed_volume_mm3'];assert len(signed)==m and all(v>0 for v in signed)
    want=distribution(signed)
    for key,value in want.items():assert r['independent_signed_volume_mm3'][key]==value
    volume=Fraction(**case['exact_volume_mm3']);assert math.fsum(signed)==r['independent_signed_volume_mm3']['sum']
    assert abs(math.fsum(signed)/float(volume)-1)==r['independent_signed_volume_mm3']['relative_error']<=1e-6
    assert math.fsum(state['native_qualities']['native_volume_mm3'])==r['native_volume_sum_mm3'] and abs(r['native_volume_sum_mm3']/float(volume)-1)<=1e-6
    assert all(v>0 for key in ['Jacobian','native_volume_mm3'] for v in state['native_qualities'][key])
    faces=defaultdict(list)
    for row in en:
        for omitted in range(4):
            face=[v for i,v in enumerate(row) if i!=omitted]
            if omitted%2:face.reverse()
            faces[tuple(sorted(face))].append(face)
    exterior={key:rows[0] for key,rows in faces.items() if len(rows)==1};internal=[rows for rows in faces.values() if len(rows)==2]
    assert all(len(rows) in [1,2] for rows in faces.values())
    assert all(oriented(rows[0])==oriented(list(reversed(rows[1]))) for rows in internal)
    expected={tuple(sorted(row['local_node_tags'])):row['local_node_tags'] for row in shell['oriented_triangle_rows']}
    assert set(exterior)==set(expected) and all(oriented(exterior[key])==oriented(expected[key]) for key in expected)
    assert r['boundary_triangles']==len(exterior)==nf and r['internal_faces']==len(internal) and r['same_oriented_internal_faces']==r['nonmanifold_volume_faces']==0
    assert r['exact_oriented_tetra_boundary'] is True and r['exact_internal_orientation_balance'] is True and r['software_geometric_invariants_passed'] is True
    exact_points={tag:[Fraction.from_float(float(x)) for x in xyz[i]] for i,tag in enumerate(nt)}
    exact_volume=Fraction(0);exact_poor=0;per_case_error=defaultdict(float);within=True
    for i,row in enumerate(en):
        det,v,q2=exact_cell([exact_points[t] for t in row]);exact_volume+=v;exact_poor+=q2<Fraction(1,100)
        calculated={'SICN':math.sqrt(float(q2)),'Jacobian':float(det),'native_volume_mm3':float(v),'independent_signed_volume_mm3':float(v)}
        for name,value in calculated.items():
            observed=signed[i] if name=='independent_signed_volume_mm3' else state['native_qualities'][name][i]
            err=abs(observed-value);per_case_error[name]=max(per_case_error[name],err);max_errors[name]=max(max_errors[name],err)
            within=within and math.isclose(observed,value,rel_tol=1e-11,abs_tol=1e-14)
    assert exact_volume==volume
    all_native_calibration=all_native_calibration and within
    assert exact_poor>0;all_exact_q_bad=all_exact_q_bad and exact_poor>0
    q=r['quality']['SICN'];assert q['minimum']<.1 and q['below_point1_count']>0
    storage=r['referenced_interior_nodes']>=1 and m>=case['old_tetrahedra'];assert w['later_head_storage_compatible'] is storage
    assert result['procedural'] is True and result['strict_quality'] is False and result['next_stage']=='one_Netgen' and result['storage_compatible'] is storage and result['worker_error'] is None and result['output_files']==8
    assert receipt['returncode']==2 and receipt['stop_reason'] is None and receipt['scope']=='one_selected_current204_cavity_generation_witness'
    assert receipt['reader_sha256']==source_sha and receipt['runner_sha256']==runner_sha and receipt['contract_sha256']==ix['sha256']
    assert receipt['native_log_sha256']==rc['output_files']['native.log']['sha256'] and receipt['fixture_report_sha256']==rc['output_files']['fixture-report.json']['sha256']
    assert receipt['declared_operation_counts']==literal['COUNTS'] and receipt['operation_counts_are_declarations_not_observed'] is True
    assert receipt['hard_wall_seconds']==30 and receipt['sampled_RSS_stop_bytes']==1024**3 and receipt['sampled_output_stop_bytes']==16*1024**2 and receipt['threads']==2
    samples=receipt['RSS_samples'];assert receipt['max_observed_RSS_bytes']==max((x['RSS_bytes'] for x in samples),default=0)
    assert receipt['max_observed_RSS_bytes']<1024**3 and receipt['wall_seconds']<30
    assert receipt['final_output_bytes_before_receipt']==sum(x['bytes'] for name,x in rc['output_files'].items() if name!='execution-receipt.json')<16*1024**2
    assert rc['returncode']==result['controller_returncode']==2 and rc['root_stop_reason'] is None and rc['root_error'] is None and rc['wall_seconds']<40
    assert rc['controller_pid']==launch['controller_pid']==launch['controller_pgid'] and launch['output_directory']==directory
    for key in ['controller_wait_reaped','observed_controller_absent','native_wait_reap_attributed_to_unchanged_controller_and_valid_receipt','all38_inputs_native3_NumPy_actual_before_after_unchanged']:assert rc[key] is True
    for key in ['native_PID_observed','controller_fallback_SIGKILL','universal_descendant_absence_claimed']:assert rc[key] is False
    for key in ['input_MSH_read','full_head_geometry_read','head_execution_authorized','stitching_authorized','native_head_application_authorized','global_self_intersection_checked','geometric_tetrahedron_overlap_checked','new_interior_node_point_in_cavity_containment_checked','engineering_accepted','physics_qualified','manufacturing_authorized']:assert w[key] is False
    totals.update(cases=1,nodes=n,tetrahedra=m,referenced_interiors=r['referenced_interior_nodes'],positive_native_poor=q['below_point1_count']-q['nonpositive_count'],native_nonpositive=q['nonpositive_count'],exact_squared_poor=exact_poor,abstract_internal_faces=len(internal),shell_faces=nf,samples=len(samples),output_files=8,output_bytes=sum(x['bytes'] for x in rc['output_files'].values()))
    rss_max=max(rss_max,receipt['max_observed_RSS_bytes']);global_min=q['minimum'] if global_min is None else min(global_min,q['minimum'])
    ledger.append(dict(apex=apex,actual=dict(path=ix['path'],sha256=ix['sha256']),output_directory=directory,
        root_closed=dict(path=result['root_closed_path'],sha256=result['root_closed_sha256']),root_launch_sha256=rc['root_launch_sha256'],
        complete8_output_inventory=rc['output_files'],case_record_sha256=case['source_record_sha256'],shell_serialized_sha256=case['shell_serialized_sha256'],
        nodes=n,shell_nodes=nv,tetrahedra=m,old_tetrahedra=case['old_tetrahedra'],referenced_interior_nodes=r['referenced_interior_nodes'],
        native_SICN=q,exact_squared_quality_poor=exact_poor,exact_positive_signed_volume_equals_source=True,
        full_arrays_metric_hashes_classes_after_saved_word_identity=True,exact_oriented_exterior_and_opposite_abstract_internal_faces=True,
        native_vs_exact_saved_arithmetic_max_errors=dict(per_case_error),existing_combined_metric_comparison_tolerance_met=within,
        procedural_pass=True,strict_quality_pass=False,next_stage='one_Netgen',later_head_storage_compatible=storage,
        controller_returncode=2,no_resource_stop_or_root_fallback=True,root_controller_wait_and_individual_absence_attributed=True,native_PID_observed=False,
        native_cleanup_source_and_valid_receipt_attributed_only=True,root_wall_seconds=rc['wall_seconds'],controller_wall_seconds=receipt['wall_seconds'],
        sampled_RSS_count=len(samples),maximum_sampled_RSS_bytes=receipt['max_observed_RSS_bytes'],
        native_log_lines=len(log.splitlines()),worker_warning_error_rows=w['gmsh_warnings_errors'],MSH_hash_and_binary41_header_only_no_section_decode=True))

before=dict(sorted(inputs.items()))
for name,h in before.items():assert digest((ROOT/name).read_bytes())==h
report=dict(schema='962-current204-remaining115-generation-independent-saved-check/v1',status='COMPLETE_SAVED_ASSOCIATIONS_ALL115_PROCEDURAL_QUALITY_REJECTED',
    master_root_closed_sha256=inputs[master_path],source_sha256=source_sha,controller_sha256=runner_sha,
    input_sha256=before,input_sha256_after=before,all_saved_inputs_unchanged=True,case_count=115,case_ledger=ledger,
    totals=dict(totals),minimum_native_SICN_across_candidates=global_min,maximum_sampled_controller_RSS_bytes=rss_max,
    all115_exact_positive_determinants_and_exact_total_volumes=True,all115_exact_squared_quality_rejected=all_exact_q_bad,
    all_saved_native_metric_comparisons_within_existing_rel1e11_abs1e14=all_native_calibration,
    maximum_saved_native_vs_exact_arithmetic_errors=dict(max_errors),comparison_policy=dict(relative=1e-11,absolute=1e-14,quality_gate_unchanged=.1),
    proof_scope='Independent stdlib saved binary64 Fraction determinant/volume/regular-reference SICN-squared arithmetic and abstract oriented face incidence. Not tetrahedron-intersection, embedding, containment, parent-domain or native replay.',
    native_metric_query_and_saved_file_reopen_are_worker_source_attestations=True,MSH_bodies_hash_header_only_no_section_decode=True,
    runtime3_NumPy_binary_freshness_root_metadata_attributed_no_reviewer_body_read=True,
    native_cleanup_scope='Only root-owned controllers were observed/waited/reaped/individually absent. Native cleanup is attributed to frozen05b4 finalizer and valid receipts; no native PID or universal descendant absence proof.',
    first1393275_five_file_stop_preserved_no_retry=True,first_identity_observation_cause_remains_unproven=True,
    no_Netgen_domain_context_or_head_operation_by_reviewer=True,automatic_retry=False,backfill=False,
    engineering_accepted=False,physics_qualified=False,material_qualified=False,process_calibrated=False,manufacturing_authorized=False,
    reviewer_wall_seconds=time.monotonic()-start,prepared_creator_checker_assessor_scientific_or_native_code_imported_or_called=False)
(OUT/'independent-saved-check.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps(dict(cases=115,totals=dict(totals),all_native_calibration=all_native_calibration,max_errors=dict(max_errors),output_sha256=digest((OUT/'independent-saved-check.json').read_bytes()))))
