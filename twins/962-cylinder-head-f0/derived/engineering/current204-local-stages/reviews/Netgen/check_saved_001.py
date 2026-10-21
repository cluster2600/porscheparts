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

def check_state(state,r,shell,case):
    nv=case["shell_nodes"];nf=case["shell_faces"]
    nt=state['node_tags'];xyz=state['coordinates_mm'];et=state['tetra_tags'];en=state['tetra_node_tags'];n=len(nt);m=len(et)
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
    assert within
    assert exact_poor==r['quality']['SICN']['below_point1_count']
    return dict(nodes=n,tetrahedra=m,interiors=r['referenced_interior_nodes'],native_SICN=r['quality']['SICN'],
        exact_squared_quality_poor=exact_poor,exact_positive_volume_equals_source=True,internal_faces=len(internal),shell_faces=nf,
        max_native_vs_exact_errors=dict(per_case_error),all_existing_metric_tolerances_met=within)

start=time.monotonic()
master_path='work/962-engineering/head-star-current204-Netgen-root-execution-001/closed-result.json'
master=obj(master_path,'f53e8b905c1bab7872cc0b0ffcdbc58333c19575e6c8c71f8491886b89c00e87')
index_path='work/962-engineering/head-star-current204-Netgen-actuals-prep-002/index.json'
index=obj(index_path,master['selected_index_sha256'])
child_path='work/962-engineering/head-star-current204-Netgen-actuals-child-peer-002/review.json'
child=obj(child_path,master['exact_child_peer_sha256'])
assert child['decision']=='CLEAR_EXACT_SELECTED115_ROOT_ACTUAL_BINDINGS_ONLY' and child['blockers']==[]
root_review_path='work/962-engineering/head-star-current204-Netgen-root-execution-001/result-review.json'
obj(root_review_path,'5d8943639eea7b7e246e51714c09a2ab39e43c0cb19a5374218e65d7095dd9fc')
manifest_path='work/962-engineering/head-star-current204-local-stages-prep-001/case-manifest.json'
manifest=obj(manifest_path,'3a558ede04cbc52c59e401befb36b8983ebd9b7f57d4266de0bea38fb1a963c5')
batch=obj('work/962-engineering/head-star-current204-batch-shells-001/report.json','4f9fc0354918a907083006484d534c34c3b2621dfcc83b00cc4a4b731f009e86')
cases={r['apex']:r for r in manifest['cases_in_increasing_apex_order']};batch_cases={r['apex']:r for r in batch['all_candidate_star_records']}
source='work/962-engineering/head-star-current204-local-stages-prep-001/netgen_case.py'
runner='work/962-engineering/head-star-current204-local-stages-prep-001/run_netgen.py'
source_sha='38af98145aa8c4aa1798b5e5901a9837b962e8841d5b5d504674d6cefa922924';runner_sha='1e6ffec8141da0682b94f00eb4f8c49e31b493f32fd10ea35be04a9829e1ca06'
tree=ast.parse(read(source,source_sha).decode());read(runner,runner_sha)
literal={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['OPTIONS','COUNTS']}
rows=index['all_original115_in_increasing_apex_order'];remaining=[r['apex'] for r in rows]
assert len(remaining)==len(set(remaining))==115 and remaining==sorted(remaining) and set(remaining)==set(cases)-{1393275}
assert master['attempted_count']==master['selected_count']==115 and [r['case_apex'] for r in master['cases']]==remaining
assert master['held_first_apex_no_retry']==index['excluded_held_apex_no_retry']==1393275
assert master['original_order_no_backfill'] is True and master['one_launch_per_attempted_case'] is True and master['root_error'] is None
assert index['automatic_retry'] is False and index['backfill'] is False
first_peer=obj('work/962-engineering/head-star-current204-generation-first-stop-peer-001/review.json','da781c7144571897938835b01e33aa6acb4db6d59917de08a16852e65c844f40')
first_dir='work/962-engineering/head-star-current204-apex-1393275-generation-001'
assert set(p.name for p in (ROOT/first_dir).iterdir())==set(first_peer['first_preserved_stop']['complete5_output_inventory'])
for name,row in first_peer['first_preserved_stop']['complete5_output_inventory'].items():assert len(read(first_dir+'/'+name,row['sha256']))==row['bytes']
assert not (BASE/'head-star-current204-apex-1393275-netgen-001').exists()
ledger=[];totals=Counter();max_errors=defaultdict(float);index_cases={r['apex']:r for r in rows};all_maps={};rss_max=0;minimum=None
expected_files={'arrays.json','cavity.msh','execution-receipt.json','fixture-report.json','frozen-contract.json','native.log','reader.py','run_readback.py'}
runtime_expected={'python':'3.10.11','numpy':'2.0.2','gmsh':'4.15.2','machine':'arm64'}
runtime_hashes={'python':'72956ad35cff7691dfed9e04c9593de825ffd5b2fa7e8bc9ae96ce9a1af65621','gmsh_module':'f4b0935cebde899750293d87a643090e5ea33c9b18d249267f507db68a0e01c3','gmsh_library':'def0f5c10988a986e5e879b3db9669d8fe016a81e2d994bbaf2b8497c6b8a58a'}
for ordinal,result in enumerate(master['cases'],1):
    apex=result['case_apex'];case=cases[apex];shell=batch_cases[apex]['shell'];ix=index_cases[apex]
    assert result['ordinal']==ordinal
    rc=obj(result['closed_path'],result['sha256']);assert len(read(result['closed_path']))==result['bytes'];root_dir=str(Path(result['closed_path']).parent)
    launch=obj(root_dir+'/launch.json',rc['root_launch_sha256']);read(root_dir+'/stdout.log',rc['stdout_sha256']);read(root_dir+'/stderr.log',rc['stderr_sha256'])
    raw=read(ix['path'],ix['sha256']);assert len(raw)==ix['bytes'];actual=json.loads(raw);directory=actual['output_directory']
    assert directory==case['stage_paths']['netgen']==ix['output_directory'] and actual['case_apex']==rc['case_apex']==apex
    assert actual['case_key']==case['case_key'] and actual['case_record_sha256']==case['source_record_sha256']
    assert len(actual['input_hashes'])==actual['input_count']==ix['input_count']==60
    for name,h in actual['input_hashes'].items():read(name,h)
    all_maps[str(apex)]=actual['input_hashes']
    assert actual['reader_sha256']==source_sha and actual['runner_sha256']==runner_sha
    assert actual['options']==literal['OPTIONS'] and actual['declared_operation_counts']==literal['COUNTS']
    assert actual['optimization']=={'method':'Netgen','force':True} and actual['geometry_creation_dim_tags']==[[3,1]]
    assert actual['expected_runtime']==runtime_expected and actual['runtime_sha256s']==runtime_hashes and actual['numpy_init_sha256']=='c09e25b58f6b2f8e2cb3c158168f902d447f8171e5ea6513c0aca41ecbda7c2b'
    assert actual['native_execution_authorized'] is True and actual['cavity_Netgen_optimizer_authorized'] is True
    for k in ['generation_authorized','cavity_generation_authorized','head_execution_authorized','native_head_application_authorized','stitching_authorized','engineering_accepted','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized','automatic_retry','backfill']:assert actual[k] is False
    assert actual['controls']==dict(wall_seconds=30,sampled_RSS_stop_bytes=1024**3,sampled_output_stop_bytes=16*1024**2,threads=2,environment={'PATH':'/usr/bin:/bin','LANG':'C','PYTHONUTF8':'1','OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','VECLIB_MAXIMUM_THREADS':'2','PYTHONDONTWRITEBYTECODE':'1'},hard_OS_quota=False) and actual['root_outer_wall_seconds']==40
    assert set(p.name for p in (ROOT/directory).iterdir())==expected_files and set(rc['output_files'])==expected_files
    assert all(p.is_file() and not p.is_symlink() for p in (ROOT/directory).iterdir())
    for name,row in rc['output_files'].items():assert len(read(directory+'/'+name,row['sha256']))==row['bytes']
    assert read(directory+'/frozen-contract.json')==raw and rc['actual_sha256']==result['actual_sha256']==ix['sha256']==launch['actual_sha256']
    assert rc['child_peer_sha256']==master['exact_child_peer_sha256']==launch['child_peer_sha256'] and launch['selected_index_sha256']==master['selected_index_sha256']
    assert rc['output_files']['reader.py']['sha256']==source_sha and rc['output_files']['run_readback.py']['sha256']==runner_sha
    w=obj(directory+'/fixture-report.json');arrays=obj(directory+'/arrays.json');receipt=obj(directory+'/execution-receipt.json');log=read(directory+'/native.log').decode()
    assert read(directory+'/cavity.msh').startswith(b'$MeshFormat\n4.1 1 8\n')
    assert w['status']=='completed_finite_selected_cavity_Netgen_only' and w['schema']=='962-finite-selected-current204-Netgen/v1' and w['stage']=='completed_all_local_checks' and 'error' not in w
    for k in ['fixture_procedural_checks_passed','saved_mesh_identity_exact','exact_boundary_bits_faces_classifications','bound_inputs_unchanged','geometry_flag_full_state_unchanged','single_saved_before_state_exact','Netgen_returned_and_cache_refresh_completed','all_shell_nodes_fixed_only_for_this_cavity_operation']:assert w[k] is True
    assert w['call_counts_are_attempts'] is True and w['native_operation_counts']==literal['COUNTS'] and w['options']==literal['OPTIONS']
    assert w['frozen_contract_sha256']==ix['sha256'] and w['runtime']==runtime_expected and w['runtime_sha256s']==runtime_hashes
    assert w['case_apex']==apex and w['case_key']==case['case_key'] and w['case_record_sha256']==case['source_record_sha256'] and w['case_manifest_sha256']==actual['case_manifest_sha256'] and w['source_batch_sha256']==manifest['source_batch_report_sha256']
    assert w['full_tiny_arrays_sha256']==rc['output_files']['arrays.json']['sha256'] and w['mesh_sha256']==rc['output_files']['cavity.msh']['sha256'] and w['mesh_bytes']==rc['output_files']['cavity.msh']['bytes']
    assert w['original_source_classifications']==shell['original_source_classifications'] and w['local_to_global_shell_node_tags']==shell['local_to_global_node_tags'] and w['shell']['vertices']==case['shell_nodes'] and w['shell']['faces']==case['shell_faces']
    baseline=actual['generation_baseline'];gd=case['stage_paths']['generation']
    for role,name in {'mesh':'cavity.msh','worker':'fixture-report.json','arrays':'arrays.json','receipt':'execution-receipt.json','actual':'frozen-contract.json'}.items():assert baseline[role]['path']==gd+'/'+name and actual['input_hashes'][baseline[role]['path']]==baseline[role]['sha256']
    for row in baseline.values():assert actual['input_hashes'][row['path']]==row['sha256'] and len(read(row['path'],row['sha256']))==row['bytes']
    for k in ['generation_result_peer','generation_root_acceptance']:
        r=actual[k];assert actual['input_hashes'][r['path']]==r['sha256'];read(r['path'],r['sha256'])
    gen=obj(baseline['worker']['path']);genarrays=obj(baseline['arrays']['path']);gr=obj(baseline['receipt']['path'])
    assert w['input_mesh_sha256']==baseline['mesh']['sha256'] and w['input_worker_sha256']==baseline['worker']['sha256'] and w['input_arrays_sha256']==baseline['arrays']['sha256']
    assert gen['case_apex']==apex and gen['case_record_sha256']==case['source_record_sha256'] and gen['fixture_procedural_checks_passed'] is True and gen['actual_SICN_gate_passed'] is False and gen['next_stage']=='one_Netgen'
    assert gr['returncode']==2 and gr['stop_reason'] is None and gr['fixture_report_sha256']==baseline['worker']['sha256'] and gr['contract_sha256']==baseline['actual']['sha256']
    assert set(arrays)=={'before','after_geometry_flag','after','saved_reopen'}
    same=lambda a,b:json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)
    assert same(w['before'],gen['saved_reopen']) and same(arrays['before'],genarrays['saved_reopen'])
    assert same(w['before'],w['after_geometry_flag']) and same(arrays['before'],arrays['after_geometry_flag'])
    assert same(w['after'],w['saved_reopen']) and same(arrays['after'],arrays['saved_reopen'])
    before=check_state(arrays['before'],w['before'],shell,case);after=check_state(arrays['after'],w['after'],shell,case)
    q=w['saved_reopen']['quality']['SICN'];m=after['tetrahedra'];n=after['nodes'];storage=after['interiors']>=1 and m>=case['old_tetrahedra']
    quality=q['minimum']>=.1 and q['below_point1_count']==0;assert (after['exact_squared_quality_poor']==0) is quality
    assert w['actual_SICN_threshold']==actual['actual_SICN_threshold']==.1 and w['actual_SICN_gate_passed'] is quality and w['later_head_storage_compatible'] is storage
    route='domain' if quality and storage else 'hold_case';assert w['next_stage']==route and storage
    outcome=result['outcome'];assert outcome['status']==w['status'] and outcome['fixture_procedural_checks_passed'] is True and outcome['actual_SICN_gate_passed'] is quality and outcome['later_head_storage_compatible'] is storage and outcome['next_stage']==route and outcome['SICN']==q
    assert outcome['saved_counts']=={'nodes':n,'tetrahedra':m,'referenced_interior_nodes':after['interiors'],'old_tetrahedra':None}
    code=0 if quality else 2
    assert receipt['scope']=='one_selected_current204_cavity_netgen_witness' and receipt['returncode']==code and receipt['stop_reason'] is None
    assert receipt['reader_sha256']==source_sha and receipt['runner_sha256']==runner_sha and receipt['contract_sha256']==ix['sha256']
    assert receipt['native_log_sha256']==rc['output_files']['native.log']['sha256'] and receipt['fixture_report_sha256']==rc['output_files']['fixture-report.json']['sha256']
    assert receipt['declared_operation_counts']==literal['COUNTS'] and receipt['operation_counts_are_declarations_not_observed'] is True
    assert receipt['hard_wall_seconds']==30 and receipt['sampled_RSS_stop_bytes']==1024**3 and receipt['sampled_output_stop_bytes']==16*1024**2 and receipt['threads']==2
    samples=receipt['RSS_samples'];assert receipt['max_observed_RSS_bytes']==max((s['RSS_bytes'] for s in samples),default=0)<1024**3 and receipt['wall_seconds']<30
    assert receipt['final_output_bytes_before_receipt']==sum(v['bytes'] for k,v in rc['output_files'].items() if k!='execution-receipt.json')<16*1024**2
    assert rc['returncode']==result['returncode']==code and rc['root_stop_reason'] is None and rc['root_error'] is None and rc['wall_seconds']<40
    assert rc['controller_pid']==launch['controller_pid']==launch['controller_pgid'] and launch['output_directory']==directory
    for k in ['controller_wait_reaped','observed_controller_absent','native_wait_reap_attributed_to_unchanged_controller_and_valid_receipt','all60_inputs_native3_NumPy_actual_before_after_unchanged']:assert rc[k] is True
    for k in ['native_PID_observed','controller_fallback_SIGKILL','universal_descendant_absence_claimed']:assert rc[k] is False
    for k in ['full_head_geometry_read','generation_authorized','head_execution_authorized','stitching_authorized','native_head_application_authorized','global_self_intersection_checked','geometric_tetrahedron_overlap_checked','new_interior_node_point_in_cavity_containment_checked','interior_ancestry_inferred','engineering_accepted','physics_qualified','manufacturing_authorized']:assert w[k] is False
    totals.update(cases=1,after_nodes=n,after_tetrahedra=m,after_interiors=after['interiors'],after_exact_poor=after['exact_squared_quality_poor'],after_native_nonpositive=q['nonpositive_count'],quality_storage_passes=int(quality and storage),quality_rejects=int(not quality),storage_compatible=int(storage),abstract_internal_faces=after['internal_faces'],shell_faces=after['shell_faces'],RSS_samples=len(samples),output_files=8,output_bytes=sum(v['bytes'] for v in rc['output_files'].values()),exact_unique_saved_cell_arithmetic=before['tetrahedra']+after['tetrahedra'])
    rss_max=max(rss_max,receipt['max_observed_RSS_bytes']);minimum=q['minimum'] if minimum is None else min(minimum,q['minimum'])
    ledger.append(dict(apex=apex,case_record_sha256=case['source_record_sha256'],actual={'path':ix['path'],'sha256':ix['sha256']},root_closed={'path':result['closed_path'],'sha256':result['sha256']},complete8_output_inventory=rc['output_files'],generation_baseline=baseline,before=before,after=after,geometry_flag_full_noop_and_after_saved_all_words=True,fixed_shell_binary64_true_classes_and_oriented_boundary=True,native_operations_are_worker_attempt_counts=True,controller_operations_are_declared_counts=True,native_operation_counts=w['native_operation_counts'],strict_SICN_gate_pass=quality,later_head_storage_compatible=storage,next_stage=route,controller_returncode=code,root_wall_seconds=rc['wall_seconds'],controller_wall_seconds=receipt['wall_seconds'],maximum_sampled_RSS_bytes=receipt['max_observed_RSS_bytes'],RSS_samples=len(samples),root_owned_controller_wait_absence_attributed=True,native_PID_observed=False,native_cleanup_attributed_to_frozen_controller_and_receipt=True,gmsh_warning_error_rows=w['gmsh_warnings_errors'],native_log_lines=len(log.splitlines()),MSH_fullhash_binary41_header_only_no_decode=True))
assert totals['cases']==115 and totals['quality_storage_passes']==47 and totals['quality_rejects']==68 and totals['storage_compatible']==115
before_inputs=dict(sorted(inputs.items()))
for name,h in before_inputs.items():assert digest((ROOT/name).read_bytes())==h,name
report=dict(schema='962-current204-selected115-Netgen-independent-saved-check/v1',status='COMPLETE_LOCAL_SAVED_ASSOCIATIONS_47_PROVISIONAL_68_REJECTED',master_closed_sha256=inputs[master_path],selected_index_sha256=inputs[index_path],root_saved_review_sha256=inputs[root_review_path],source_sha256=source_sha,controller_sha256=runner_sha,input_sha256=before_inputs,input_sha256_after=before_inputs,all_selected_saved_inputs_unchanged=True,all_actual_input_maps60=all_maps,case_ledger=ledger,totals=dict(totals),minimum_after_native_SICN=minimum,maximum_sampled_controller_RSS_bytes=rss_max,maximum_native_vs_exact_saved_arithmetic_errors=dict(max_errors),comparison_policy={'relative':1e-11,'absolute':1e-14,'strict_SICN':.1},all_before_after_exact_positive_determinants_and_source_volume=True,all_exact_squared_quality_classifications_match_native_float_bins=True,all_four_stages_typedarrays_fullwords_classes_incidence_and_metricjoins=True,arithmetic_reuse='Exact pure Fraction/typedhash/oriented-face helper source and state check adapted from frozen generation reviewer9deda; no producer/helper module imported or called.',reviewer_role='Author of unchanged shared local-stage caller/controller adaptation and held templates; independent saved arithmetic/result associations here, not a new independent source review.',runtime3_NumPy_freshness_root_attribution_no_body_read=True,native_cleanup_scope='Root observed/waited/reaped individual controllers only. Native cleanup attributed to unchanged1e6 finally path and valid receipts; no native PID or universal descendant absence proof.',MSH_scope='Full saved tiny MSH SHA and binary4.1 header only; no section decode/native reopen.',proof_scope='Saved binary64 Fraction signed determinants/volumes/SICN² and abstract oriented incidence only; no geometric intersection/embedding/local-domain/global-head/PDE/physical proof.',all47_domain_routes_provisional_not_domain_or_head_admission=True,first1393275_preserved_held_unretried=True,engineering_accepted=False,physics_qualified=False,material_qualified=False,process_calibrated=False,manufacturing_authorized=False,reviewer_wall_seconds=time.monotonic()-start,prepared_producer_scientific_or_native_code_imported_or_called=False)
(OUT/'independent-saved-check.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps(dict(totals=dict(totals),min_SICN=minimum,max_errors=dict(max_errors),check_sha256=digest((OUT/'independent-saved-check.json').read_bytes()))))
