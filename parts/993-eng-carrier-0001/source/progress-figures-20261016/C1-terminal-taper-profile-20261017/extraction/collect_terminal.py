"""Read only the actual owned new-profile terminal; no native operation."""
import copy,hashlib,importlib.util,json,math,os,resource,signal,subprocess,time
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];began=time.monotonic()
signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('90s stdlib terminal collection')));signal.alarm(90);resource.setrlimit(resource.RLIMIT_CPU,(60,70))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,x):
 with p.open('x')as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
plan=read(H/'plan.json');launch=read(H/'launch-plan.json');sup=read(H/'execution-001/execution-receipt.json');a=read(H/'output-001/assessment.json');started=read(H/'execution-001/started.json');command=read(H/'command.json')
assert sha(H/'root-review-GO-001.json')=='849920cd63e8183ff9241326355b7df812b3da8778cf956af3e2c4d4ed0fb741'
assert sup['actual_returncode']==0 and sup['direct_child_reaped']and sup['final_group_members']==[]and sup['no_non_zombie_group_members']and sup['cleanup_error']is None and sup['signals_to_owned_group_only']==[]and not sup['timeout']and not sup['interrupted']
assert sup['command']==launch['command']and sup['plan_sha256']==sha(H/'launch-plan.json')and sup['pid']==started['pid']==42237 and started['pgid']==42237
pins={**launch['inputs_sha256'],**launch['source_sha256']};assert sup['sources_before']==sup['sources_after']==pins and sup['sources_and_plan_unchanged']and {k:sha(R/k)for k in pins}==pins
assert a['sources_before']==a['sources_after']==plan['files_sha256']and a['sources_unchanged']and a['status']=='new_only_taper_profile_extracted_closed_profiles_reused_no_admission'
inv=copy.deepcopy(plan);gk=str((H/'root-review-GO-001.json').relative_to(R));inv.update(launch_ready=False,root_GO=None,root_GO_sha256=None);del inv['files_sha256'][gk];assert inv==read(H/'pending-plan.json')
inv=copy.deepcopy(launch);inv['launch_ready']=False;pk=str((H/'pending-plan.json').relative_to(R));ak=str((H/'plan.json').relative_to(R));del inv['inputs_sha256'][ak];del inv['inputs_sha256'][gk];inv['inputs_sha256'][pk]=sha(H/'pending-plan.json');inv['command'][-2:]=read(H/'pending-launch-plan.json')['command'][-2:];assert inv==read(H/'pending-launch-plan.json')
s=importlib.util.spec_from_file_location('_actual_profile_terminal_stdlib',H/'extract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);old=m.closed_old(plan);m.closed_volume(plan)
data=read(H/'output-001/section-data.json');m.check_new(data,old);vol=read(H/'output-001/native-volume-methods.json');assert data['native_volume_methods']==vol and sha(H/'output-001/native-volume-methods.json')==a['native_volume_methods_sha256']and sha(H/'output-001/section-data.json')==a['raw_profile_data_sha256']
assert vol['same_native_Solid_identity_before_after']and vol['same_Solid_passed_to_all_three_unchanged_calls']and vol['adaptive_exact_binary64_equal_to_closed_reference']and vol['Gmsh_getMass_mm3']is None and not vol['Gmsh_imported']and not vol['new_T10_mesh_executed']
assert [r['arguments']for r in vol['methods']]==[[False,False,False],[True,False,False],[1e-10,True,False]]
assert all(r['signed_mass_mm3']>0 and r['mass_binary64_hex']==r['signed_mass_mm3'].hex()for r in vol['methods'])and vol['methods'][2]['signed_mass_mm3']==m.ADAPTIVE_REFERENCE
assert data['source_sha256']==plan['files_sha256']and data['producer_sha256']==sha(H/'extract.py')and data['plan_sha256']==sha(H/'plan.json')
logs={n:sha(H/'execution-001'/n)for n in ['stdout.log','stderr.log']};assert logs==sup['logs_sha256']or all(sup['logs_sha256'].get(n)==v for n,v in logs.items())
r=subprocess.run(['/bin/ps','-g','42237','-o','pid=,ppid=,pgid=,stat='],capture_output=True,text=True,timeout=2);assert r.returncode==1 and not r.stdout.strip()and not r.stderr.strip()
assert not any(k=='OCP'or k.startswith('OCP.')or k=='gmsh'for k in __import__('sys').modules)
files={str(p.relative_to(H)):dict(bytes=p.stat().st_size,sha256=sha(p))for root in [H/'output-001',H/'execution-001']for p in sorted(root.iterdir())if p.is_file()}
section=data['taper_section'];report=dict(schema='new_only_taper_profile_actual_terminal_1',status='actual_RC0_new_profile_and_three_same_Solid_volumes_closed_no_admission',actual_tool_session=85052,actual_tool_launch_chunk='c27cac',actual_tool_terminal_chunk='f57205',actual_tool_returncode=0,actual_child_returncode=0,pid=42237,pgid=42237,parent_pid=42233,started_sha256=sha(H/'execution-001/started.json'),supervision_sha256=sha(H/'execution-001/execution-receipt.json'),assessment_sha256=sha(H/'output-001/assessment.json'),section_data_sha256=sha(H/'output-001/section-data.json'),native_volume_methods_sha256=sha(H/'output-001/native-volume-methods.json'),root_GO_sha256=sha(H/'root-review-GO-001.json'),plan_sha256=sha(H/'plan.json'),launch_sha256=sha(H/'launch-plan.json'),direct_child_reaped=True,final_group_members=[],fresh_owned_PGID_absent=True,cleanup_error=None,signals=[],timeout=False,unique_pins=len(pins),all_pins_actual_equal=True,whole_plan_and_launch_inverse_equal=True,whole_closed_profiles_context_equal=True,old_CAD_recomputed=False,new_native_section_edges=section['edge_count'],new_native_drawing_points=sum(len(e['points_xyz_mm'])for e in section['edges']),new_section_coordinates_sha256=section['sampled_positions_sha256'],maximum_plane_residual_mm=a['maximum_plane_residual_mm'],native_volume_methods=vol,supervision_seconds=sup['elapsed_seconds'],child_seconds=a['elapsed_seconds'],output_artifacts=files,collector_source_sha256=sha(__file__),collector_seconds=time.monotonic()-began,native_module_imported_by_collector=False,candidate_qualified=False,original_law_RC1_preserved=True,global_thickness_claimed=False,FEA_executed=False,render_executed=False)
write(H/'terminal-collection.json',report);signal.alarm(0)
print(json.dumps(dict(status=report['status'],terminal_sha256=sha(H/'terminal-collection.json'),section_sha256=report['section_data_sha256'],volume_methods=vol['methods'],edges=report['new_native_section_edges'],points=report['new_native_drawing_points'],files=len(files),pins=len(pins))))
