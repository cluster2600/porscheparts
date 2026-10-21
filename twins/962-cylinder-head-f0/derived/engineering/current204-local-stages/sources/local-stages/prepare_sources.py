"""Source/data preparation only; never import a worker, scientific package or controller."""
from pathlib import Path
import ast, difflib, hashlib, json

ROOT = Path(__file__).resolve().parents[3]
PREP = Path(__file__).resolve().parent
BASE = 'work/962-engineering/'
sha = lambda b: hashlib.sha256(b).hexdigest()
enc = lambda x: (json.dumps(x, indent=2, allow_nan=False) + '\n').encode()
BATCH = BASE + 'head-star-current204-batch-shells-001/report.json'
BATCH_SHA = '4f9fc0354918a907083006484d534c34c3b2621dfcc83b00cc4a4b731f009e86'
raw = (ROOT / BATCH).read_bytes(); assert sha(raw) == BATCH_SHA
batch = json.loads(raw); chosen = set(batch['selected_apex_tags'])
assert len(chosen) == batch['selected_star_count'] == 116
rows = {r['apex']: r for r in batch['all_candidate_star_records']}
cases = []; occupied = set()
for apex in sorted(chosen):
    r = rows[apex]; s = r['shell']; o = r['observation']
    assert r['eligible'] and not occupied.intersection(r['all_vertex_tags'])
    occupied.update(r['all_vertex_tags'])
    key = 'apex-' + str(apex)
    cases.append(dict(apex=apex,case_key=key,source_record_sha256=sha(enc(r)),
        shell_serialized_sha256=sha(enc(s)),observation_serialized_sha256=sha(enc(o)),screen_serialized_sha256=sha(enc(r['necessary_face_screen'])),
        old_tetrahedra=r['source_complete_incident_cell_count'],shell_nodes=s['vertices'],shell_faces=s['oriented_triangles'],
        original_boundary_shell_nodes=len(s['original_source_classifications']['boundary_global_node_tags']),
        other_interior_shell_nodes=len(s['original_source_classifications']['other_interior_global_node_tags']),
        old_vertex_tags=r['all_vertex_tags'],old_tetrahedron_tags=r['source_tetrahedron_tags'],old_poor_tags=r['poor_tetrahedron_tags'],
        exact_volume_mm3=s['exact_enclosed_volume_mm3'],
        stage_paths={stage:BASE+'head-star-current204-'+key+'-'+stage+'-001' for stage in ['generation','netgen','domain']},
        observed_generated_candidate=None,observed_Netgen_candidate=None))
manifest = dict(schema='962-current204-finite-local-stage-manifest/v1',status='HELD_SOURCE_ONLY',
    source_batch_report=BATCH,source_batch_report_sha256=BATCH_SHA,
    source_census_sha256=batch['source_census_sha256'],source_parent_MSH_sha256=batch['source_MSH_sha256'],
    root_saved_review_sha256='5a80128a5e4dd3ea685449c1124fd1fad4c07a3bb1c586f9f80a2e26caacf913',
    root_failed_inspection_sha256='032c990a0edd6ff61fa9d9a45cc727693628862e20917068ab435d524d2fdf8c',
    selected_count=116,cases_in_increasing_apex_order=cases,selected_vertex_sets_disjoint=True,
    frozen_selection_is_not_reranked_or_backfilled=True,source_subrecord_encoding='json.dumps(record,indent=2,allow_nan=False)+newline; explicit generated body identity, not master-report hash or original substring identity',
    stage_policy=dict(procedural_generation_failure='stop_case',generation_strict_pass_and_storage_compatible='domain',
        generation_strict_pass_storage_incompatible='hold_case_no_Netgen',procedural_generation_quality_rejection='one_Netgen',
        Netgen_terminal='domain_only_if_strict_pass_and_storage_compatible_else_hold_case',automatic_retry=False,backfill=False),
    later_head_storage_admission=dict(minimum_candidate_referenced_interior_nodes=1,minimum_candidate_tetrahedra='old_tetrahedra',
        incompatible_case_held_without_new_node_deletion_or_element_retirement_semantics=True),
    controls_per_native_stage=dict(wall_seconds=30,sampled_RSS_stop_bytes=1073741824,sampled_output_stop_bytes=16777216,threads=2,hard_OS_quota=False),
    native_execution_authorized=False,head_execution_authorized=False,stitching_authorized=False,engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
manifest_raw=enc(manifest);(PREP/'case-manifest.json').write_bytes(manifest_raw)
manifest_sha=sha(manifest_raw)

gen_source=BASE+'fixed-shell-generation-apex1474426-prep-001/reader.py'
old_gen=(ROOT/gen_source).read_text(); new=old_gen
new=new.replace('HELD single fixed-shell apex1474426 cavity generation; no head stitching.','HELD one selected current204 fixed-shell case generation; no head stitching.')
new=new.replace("SHELL='work/962-engineering/direct-sicn-apex1474426-cavity-study-001/local-shell-input-001.json'\nSHELL_SHA='6ad00be791b8b752106b5324b9f80df314f7458d8d0475b1ffc1a053bc04d12a'",f"MANIFEST='{BASE}head-star-current204-local-stages-prep-001/case-manifest.json'\nMANIFEST_SHA='{manifest_sha}'\nBATCH='{BATCH}'\nBATCH_SHA='{BATCH_SHA}'\nNV=NF=NB=APEX=None\nSHELL_SHA=VOLUME=None")
start=new.index('VOLUME=Fraction(');end=new.index('\nsha=lambda',start);new=new[:start]+new[end+1:]
insert='''def encoded(value):
 return (json.dumps(value,indent=2,allow_nan=False)+'\\n').encode()

def select_case(manifest,batch,apex):
 cases=manifest['cases_in_increasing_apex_order'];tags=[r['apex'] for r in cases]
 if (manifest.get('schema')!='962-current204-finite-local-stage-manifest/v1' or manifest.get('selected_count')!=116
     or tags!=sorted(set(tags)) or len(tags)!=116 or set(tags)!=set(batch['selected_apex_tags'])
     or type(apex) is not int or apex not in tags or batch.get('source_current_positive_poor_cells')!=204
     or batch.get('source_MSH_sha256')!=manifest['source_parent_MSH_sha256']):
  raise ValueError('Exactly the frozen selected116 cases required; no backfill or new case')
 original={r['apex']:r for r in batch['all_candidate_star_records']};used=set()
 for row in cases:
  record=original[row['apex']]
  if (record.get('eligible') is not True or set(record['all_vertex_tags'])&used
      or hashlib.sha256(encoded(record)).hexdigest()!=row['source_record_sha256']):
   raise ValueError('Complete selected record identity or whole-vertex disjointness changed')
  used.update(record['all_vertex_tags'])
 row=cases[tags.index(apex)];record=original[apex];shell=record['shell']
 if (hashlib.sha256(encoded(shell)).hexdigest()!=row['shell_serialized_sha256']
     or hashlib.sha256(encoded(record['observation'])).hexdigest()!=row['observation_serialized_sha256']
     or hashlib.sha256(encoded(record['necessary_face_screen'])).hexdigest()!=row['screen_serialized_sha256']
     or row['old_tetrahedra']!=record['source_complete_incident_cell_count']
     or row['old_vertex_tags']!=record['all_vertex_tags'] or row['old_tetrahedron_tags']!=record['source_tetrahedron_tags']
     or row['old_poor_tags']!=record['poor_tetrahedron_tags']
     or (row['shell_nodes'],row['shell_faces'])!=(shell['vertices'],shell['oriented_triangles'])
     or row['exact_volume_mm3']!=shell['exact_enclosed_volume_mm3']
     or row['original_boundary_shell_nodes']!=len(shell['original_source_classifications']['boundary_global_node_tags'])
     or row['other_interior_shell_nodes']!=len(shell['original_source_classifications']['other_interior_global_node_tags'])):
  raise ValueError('All explicit case shell/observation/screen/count/class/volume associations required')
 return row,record

def configure_case(c,stage='generation'):
 global NV,NF,NB,APEX,VOLUME,SHELL_SHA
 if (c.get('case_manifest')!=MANIFEST or c.get('case_manifest_sha256')!=MANIFEST_SHA
     or c['input_hashes'].get(MANIFEST)!=MANIFEST_SHA or c['input_hashes'].get(BATCH)!=BATCH_SHA
     or sha(ROOT/MANIFEST)!=MANIFEST_SHA or sha(ROOT/BATCH)!=BATCH_SHA):
  raise ValueError('Frozen finite manifest and complete batch report must be direct current pins')
 case,record=select_case(json.loads((ROOT/MANIFEST).read_text()),json.loads((ROOT/BATCH).read_text()),c.get('case_apex'))
 if (c.get('case_key')!=case['case_key'] or c.get('case_record_sha256')!=case['source_record_sha256']
     or c.get('output_directory')!=case['stage_paths'][stage]):raise ValueError('Exact selected case/stage/output binding required')
 NV,NF,NB,APEX=case['shell_nodes'],case['shell_faces'],case['original_boundary_shell_nodes'],case['apex']
 value=case['exact_volume_mm3'];VOLUME=Fraction(value['numerator'],value['denominator']);SHELL_SHA=case['shell_serialized_sha256']
 if type(NV) is not int or NV<4 or type(NF) is not int or NF<4 or type(NB) is not int or not 0<=NB<=NV or VOLUME<=0:
  raise ValueError('Positive frozen shell dimensions/volume required')
 return case,record['shell']

def candidate_storage_admission(report,case):
 return (type(report.get('referenced_interior_nodes')) is int and report['referenced_interior_nodes']>=1
  and type(report.get('tetrahedra')) is int and report['tetrahedra']>=case['old_tetrahedra'])

def case_route(procedural,quality,storage):
 if type(procedural) is not bool or type(quality) is not bool or type(storage) is not bool:raise ValueError('Explicit terminal booleans required')
 if not procedural:return 'stop_case'
 if quality:return 'domain' if storage else 'hold_mapping_incompatible_no_Netgen'
 return 'one_Netgen'

'''
pos=new.index('def validate_shell(');new=new[:pos]+insert+new[pos:]
for old,replacement in [('!=32','!=NV'),('!=60','!=NF'),('<=32','<=NV'),('>32','>NV'),('range(1,33)','range(1,NV+1)'),('range(1,61)','range(1,NF+1)'),('range(1,28)','range(1,NB+1)'),('range(28,33)','range(NB+1,NV+1)'),('i<27','i<NB'),('mapping[:27]','mapping[:NB]'),('mapping[27:]','mapping[NB:]'),('!=1474426','!=APEX'),('1474426 in mapping','APEX in mapping'),('dict(vertices=32,faces=60','dict(vertices=NV,faces=NF')]:new=new.replace(old,replacement)
new=new.replace("'fixed_shell_apex1474426_cavity'","'fixed_shell_current204_apex_'+str(APEX)")
new=new.replace("     or c.get('automatic_retry') is not False or c.get('local_shell_input')!=SHELL\n     or c.get('local_shell_input_sha256')!=SHELL_SHA)","     or c.get('automatic_retry') is not False or c.get('case_manifest')!=MANIFEST\n     or c.get('case_manifest_sha256')!=MANIFEST_SHA)")
new=new.replace(" for name,digest in [(SHELL,SHELL_SHA),(HELPER,HELPER_SHA),(ORIENTATION,ORIENTATION_SHA),(CUBE,CUBE_SHA)]:"," case,data=configure_case(c)\n for name,digest in [(MANIFEST,MANIFEST_SHA),(BATCH,BATCH_SHA),(HELPER,HELPER_SHA),(ORIENTATION,ORIENTATION_SHA),(CUBE,CUBE_SHA)]:")
old="  raise ValueError('Materialized source or selected Python changed')\n\ndef load_audit_helper"
new=new.replace(old,"  raise ValueError('Materialized source or selected Python changed')\n return case,data\n\ndef load_audit_helper")
new=new.replace(" c=json.loads((OUT/'frozen-contract.json').read_text());require_contract(c)"," c=json.loads((OUT/'frozen-contract.json').read_text());case,data=require_contract(c)")
new=new.replace("schema='962-fixed-shell-generation-apex1474426/v1'","schema='962-finite-selected-current204-generation/v1'")
new=new.replace("local_shell_sha256=SHELL_SHA,input_MSH_read=False","local_shell_serialized_sha256=SHELL_SHA,case_key=case['case_key'],case_apex=APEX,case_record_sha256=case['source_record_sha256'],case_manifest_sha256=MANIFEST_SHA,source_batch_sha256=BATCH_SHA,input_MSH_read=False")
new=new.replace("  data=json.loads((ROOT/SHELL).read_text());shell_rows(data)","  shell_rows(data)")
new=new.replace("report['all32_shell_nodes_fixed_only_for_this_cavity_generation']","report['all_shell_nodes_fixed_only_for_this_cavity_generation']")
new=new.replace("status='completed_specific_cavity_generation_only')","status='completed_finite_selected_cavity_generation_only')\n  storage=candidate_storage_admission(live['after_generation'][0],case)\n  report.update(later_head_storage_compatible=storage,next_stage=case_route(True,report['actual_SICN_gate_passed'],storage))")
new=new.replace("report=dict(schema=","report=dict(next_stage='stop_case',later_head_storage_compatible=False,schema=")
for old,replacement in [('Exact finite thirty-two-node/sixty-triangle cavity shell required','Exact finite selected-case shell required'),('Original twenty-seven-boundary/five-interior distinction changed','Original per-case boundary/interior shell distinction changed'),('Exactly sixty TRI3 elements required','Exactly the selected case TRI3 elements required')]:new=new.replace(old,replacement)
ast.parse(new);(PREP/'generate_case.py').write_text(new)

net_source=BASE+'fixed-shell-netgen-apex1474426-prep-001/reader.py';old_net=(ROOT/net_source).read_text();net=old_net
net=net.replace('HELD one saved-cavity Netgen operation; no generation, stitching or head apply.','HELD one selected current204 saved-case Netgen operation; no generation, stitching or head apply.')
start=net.index("CAVITY='");end=net.index("OPTIONS=",start)
net=net[:start]+f"CAVITY='{BASE}head-star-current204-local-stages-prep-001/generate_case.py'\nCAVITY_SHA='{sha(new.encode())}'\nCUBE='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/reader.py'\nCUBE_SHA='97b7e9fc7d17defa84594c50dac1d4e09cd39bb47ef2059e00b6ac07fe8c029b'\nMANIFEST='{BASE}head-star-current204-local-stages-prep-001/case-manifest.json'\nMANIFEST_SHA='{manifest_sha}'\nBATCH='{BATCH}'\nBATCH_SHA='{BATCH_SHA}'\nINPUT=INPUT_SHA=WORKER=WORKER_SHA=ARRAYS=ARRAYS_SHA=None\nAUDIT_INPUTS={{'twins/962-cylinder-head-f0/source/mesh_head.py':'69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5','work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py':'a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4',MANIFEST:MANIFEST_SHA,BATCH:BATCH_SHA}}\n"+net[end:]
net=net.replace("     or c.get('input_mesh')!=INPUT or c.get('input_mesh_sha256')!=INPUT_SHA\n",'')
net=net.replace(" for name,digest in [(CAVITY,CAVITY_SHA),(CUBE,CUBE_SHA),(INPUT,INPUT_SHA),(WORKER,WORKER_SHA),(ARRAYS,ARRAYS_SHA)]:"," configure_baseline(c)\n for name,digest in [(CAVITY,CAVITY_SHA),(CUBE,CUBE_SHA),(INPUT,INPUT_SHA),(WORKER,WORKER_SHA),(ARRAYS,ARRAYS_SHA)]:")
pos=net.index('def load_cavity_module(')
net=net[:pos]+'''def configure_baseline(c):
 global INPUT,INPUT_SHA,WORKER,WORKER_SHA,ARRAYS,ARRAYS_SHA
 b=c['generation_baseline'];directory='work/962-engineering/head-star-current204-apex-'+str(c['case_apex'])+'-generation-001'
 expected={'mesh':directory+'/cavity.msh','worker':directory+'/fixture-report.json','arrays':directory+'/arrays.json','receipt':directory+'/execution-receipt.json','actual':directory+'/frozen-contract.json'}
 if set(b)!=set(expected)|{'root_closed','result_peer'} or any(b[k]['path']!=v for k,v in expected.items()):raise ValueError('Same-case generation plus root closure and stopped peer direct pins required')
 for row in b.values():
  if not isinstance(row,dict) or c['input_hashes'].get(row['path'])!=row['sha256']:raise ValueError('All stopped generation/proof records must be direct pins')
 INPUT,INPUT_SHA=b['mesh']['path'],b['mesh']['sha256'];WORKER,WORKER_SHA=b['worker']['path'],b['worker']['sha256'];ARRAYS,ARRAYS_SHA=b['arrays']['path'],b['arrays']['sha256']

'''+net[pos:]
start=net.index('def require_saved_baseline(');end=net.index('\ndef expected_live(',start)
net=net[:start]+'''def require_saved_baseline(worker,c,case):
 r=worker.get('saved_reopen',{});q=r.get('quality',{}).get('SICN',{});b=c['generation_baseline']
 if (worker.get('status')!='completed_finite_selected_cavity_generation_only' or worker.get('fixture_procedural_checks_passed') is not True
     or worker.get('actual_SICN_gate_passed') is not False or worker.get('next_stage')!='one_Netgen'
     or worker.get('saved_mesh_identity_exact') is not True or worker.get('bound_inputs_unchanged') is not True
     or worker.get('case_apex')!=case['apex'] or worker.get('case_key')!=case['case_key']
     or worker.get('case_record_sha256')!=case['source_record_sha256'] or worker.get('case_manifest_sha256')!=MANIFEST_SHA
     or worker.get('local_shell_serialized_sha256')!=case['shell_serialized_sha256']
     or worker.get('source_batch_sha256')!=BATCH_SHA or worker.get('mesh_sha256')!=INPUT_SHA
     or worker.get('mesh_bytes')!=b['mesh']['bytes'] or worker.get('full_tiny_arrays_sha256')!=ARRAYS_SHA
     or worker.get('after_generation')!=r or r.get('unreferenced_nodes')!=0
     or type(r.get('tetrahedra')) is not int or r['tetrahedra']<=0 or q.get('count')!=r['tetrahedra']
     or type(q.get('nonpositive_count')) is not int or not 0<=q['nonpositive_count']<=r['tetrahedra'] or type(q.get('minimum')) not in (int,float)
     or q['minimum']>=.1 or q.get('below_point1_count',0)<=0):
  raise ValueError('Same-case stopped procedural generation with actual strict-quality rejection required')
 receipt=json.loads((ROOT/b['receipt']['path']).read_text())
 if (receipt.get('returncode')!=2 or receipt.get('stop_reason') is not None
     or receipt.get('fixture_report_sha256')!=WORKER_SHA or receipt.get('contract_sha256')!=b['actual']['sha256']
     or receipt.get('reader_sha256')!=CAVITY_SHA or receipt.get('runner_sha256')!=c['generation_runner_sha256']):
  raise ValueError('Natural procedural generation quality rejection receipt required; stopped/error runs are never retried')

'''+net[end:]
net=net.replace("  worker=json.loads((ROOT/WORKER).read_text());require_saved_baseline(worker)\n  arrays=json.loads((ROOT/ARRAYS).read_text());cavity=load_cavity_module()","  cavity=load_cavity_module();case,data=cavity.configure_case(c,stage='netgen')\n  worker=json.loads((ROOT/WORKER).read_text());require_saved_baseline(worker,c,case)\n  arrays=json.loads((ROOT/ARRAYS).read_text())")
net=net.replace("  data=json.loads((ROOT/cavity.SHELL).read_text());points,faces,shell=cavity.shell_rows(data)","  points,faces,shell=cavity.shell_rows(data)")
net=net.replace("schema='962-specific-saved-cavity-Netgen/v1'","schema='962-finite-selected-current204-Netgen/v1'")
net=net.replace('all32_shell_nodes_fixed_only_for_this_cavity_operation','all_shell_nodes_fixed_only_for_this_cavity_operation')
net=net.replace("status='completed_specific_cavity_Netgen_only')","status='completed_finite_selected_cavity_Netgen_only')\n  storage=cavity.candidate_storage_admission(live['after'][0],case)\n  report.update(case_key=case['case_key'],case_apex=case['apex'],case_record_sha256=case['source_record_sha256'],case_manifest_sha256=MANIFEST_SHA,source_batch_sha256=BATCH_SHA,later_head_storage_compatible=storage,next_stage='domain' if report['actual_SICN_gate_passed'] and storage else 'hold_case')")
net=net.replace('report=dict(schema=','report=dict(next_stage=\'hold_case\',later_head_storage_compatible=False,schema=')
ast.parse(net);(PREP/'netgen_case.py').write_text(net)

sources=[('generation',gen_source,old_gen,new),('Netgen',net_source,old_net,net)]
for name,source,old,changed in sources:
 donor=BASE+('fixed-shell-generation-apex1474426-prep-001' if name=='generation' else 'fixed-shell-netgen-apex1474426-prep-001')+'/run_readback.py'
 before=(ROOT/donor).read_text();after=before
 if name=='generation':
  after=after.replace('specific apex1435493 cavity generation','selected current204 cavity generation').replace('one_specific_apex1435493_cavity_generation_witness','one_selected_current204_cavity_generation_witness')
 else:after=after.replace('one_specific_saved_apex1435493_cavity_Netgen_witness','one_selected_current204_cavity_netgen_witness')
 filename='run_generation.py' if name=='generation' else 'run_netgen.py';(PREP/filename).write_text(after)
 (PREP/(name.lower()+'-controller.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=donor,tofile=str((PREP/filename).relative_to(ROOT)))))
 (PREP/(name.lower()+'-source.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),changed.splitlines(True),fromfile=source,tofile=str((PREP/('generate_case.py' if name=='generation' else 'netgen_case.py')).relative_to(ROOT)))))
evidence={
 BASE+'head-star-current204-batch-shells-001/receipt.json':'78e215c5c85f01ca614e44e4e443fd4181086f63e2edc5d5aee81fbef77dbedb',
 BASE+'head-star-current204-batch-shells-root-execution-001/closed-result.json':'67d9b2763fcd5ac887eddca79010d8a21dc6365b19f56224512acbaf7a3150e2',
 BASE+'head-star-current204-batch-shells-root-execution-001/result-review.json':'5a80128a5e4dd3ea685449c1124fd1fad4c07a3bb1c586f9f80a2e26caacf913',
 BASE+'head-star-current204-batch-shells-result-peer-001/review.json':'3fd325b3e4e18b942bda26d9292127d1dc1c2b8ecc5841d11257dc61884030da',
 BASE+'head-star-current204-batch-shells-root-execution-001/result-peer-acceptance.json':'47a98aad883748178b7b25a1a5957ca01c0780eb0274f778567e6c5fb22fe538'}
new=(PREP/'generate_case.py').read_text();net=(PREP/'netgen_case.py').read_text()
line='BATCH_EVIDENCE='+repr(evidence)+'\n'
new=new.replace('NV=NF=NB=APEX=None',line+'NV=NF=NB=APEX=None')
new=new.replace('[(MANIFEST,MANIFEST_SHA),(BATCH,BATCH_SHA),(HELPER,HELPER_SHA),(ORIENTATION,ORIENTATION_SHA),(CUBE,CUBE_SHA)]:','[(MANIFEST,MANIFEST_SHA),(BATCH,BATCH_SHA),(HELPER,HELPER_SHA),(ORIENTATION,ORIENTATION_SHA),(CUBE,CUBE_SHA)]+list(BATCH_EVIDENCE.items()):')
new=new.replace("or c.get('native_head_application_authorized') is not False or c.get('manufacturing_authorized') is not False):","or c.get('native_head_application_authorized') is not False or c.get('manufacturing_authorized') is not False\n     or any(c.get(k) is not False for k in ['engineering_accepted','physics_qualified'])):")
net=net.replace("CAVITY_SHA='"+sha((PREP/'generate_case.py').read_bytes())+"'","CAVITY_SHA='"+sha(new.encode())+"'")
runner_path=BASE+'head-star-current204-local-stages-prep-001/run_generation.py';runner_sha=sha((PREP/'run_generation.py').read_bytes())
net=net.replace('OPTIONS={',line+"GENERATION_RUNNER='"+runner_path+"'\nGENERATION_RUNNER_SHA='"+runner_sha+"'\nAUDIT_INPUTS.update(BATCH_EVIDENCE)\nAUDIT_INPUTS[GENERATION_RUNNER]=GENERATION_RUNNER_SHA\nOPTIONS={",1)
net=net.replace("or receipt.get('reader_sha256')!=CAVITY_SHA or receipt.get('runner_sha256')!=c['generation_runner_sha256']):","or receipt.get('reader_sha256')!=CAVITY_SHA or receipt.get('runner_sha256')!=GENERATION_RUNNER_SHA\n     or c.get('generation_runner_sha256')!=GENERATION_RUNNER_SHA):")
for filename,source,old,changed in [('generate_case.py',gen_source,old_gen,new),('netgen_case.py',net_source,old_net,net)]:
 ast.parse(changed);(PREP/filename).write_text(changed)
 name='generation' if filename=='generate_case.py' else 'netgen'
 (PREP/(name+'-source.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),changed.splitlines(True),fromfile=source,tofile=str((PREP/filename).relative_to(ROOT)))))
print(json.dumps({'manifest_sha256':manifest_sha,'cases':len(cases),'generation_source_sha256':sha(new.encode()),'Netgen_source_sha256':sha(net.encode()),'no_functions_or_tests_run':True},indent=2))
