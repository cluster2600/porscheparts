"""Collect the one actual current07b two-case coarse render without loading fields or drawing."""
from pathlib import Path
import copy,hashlib,json,os,struct,subprocess
import xml.etree.ElementTree as ET
H=Path(__file__).resolve().parent;R=H.parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def read(p):p.stat();return json.loads(p.read_text())
def enc(v):return(json.dumps(v,indent=2,allow_nan=False)+'\n').encode()
p=read(H/'plan.json');l=read(H/'launch.json');s=read(H/'execution-001/execution-receipt.json');render=H/'render-001';a=read(render/'render-receipt.json')
pins={**l['inputs_sha256'],**l['source_sha256']}
assert s['actual_returncode']==0 and s['direct_child_reaped']and not s['timeout']and not s['interrupted']and s['failure']is None and s['cleanup_error']is None and s['final_group_members']==[]and s['no_non_zombie_group_members']and s['sources_and_plan_unchanged']
assert s['plan_sha256']==sha(H/'launch.json')and s['command']==l['command']and s['sources_before']==s['sources_after']==pins=={n:sha(R/n)for n in pins}
assert '-I'not in l['command']and l['command'][1]=='-B'and s['total_wall_budget_seconds']==180 and s['cleanup_grace_seconds']==[10,10]
go=str(Path(p['root_GO']).relative_to(R));armed_plan=str((H/'plan.json').relative_to(R))
p0=read(H/'pending-plan.json');l0=read(H/'pending-launch.json');c0=read(H/'pending-command.json')
inverse=copy.deepcopy(p);inverse['files_sha256'].pop(go);inverse['launch_ready']=p0['launch_ready'];inverse['root_GO_sha256']=p0['root_GO_sha256'];assert inverse==p0 and enc(inverse)==(H/'pending-plan.json').read_bytes()
inverse=copy.deepcopy(l);inverse['inputs_sha256'].pop(go);pending_plan=str((H/'pending-plan.json').relative_to(R));inverse['inputs_sha256']={pending_plan if k==armed_plan else k:l0['inputs_sha256'][pending_plan]if k==armed_plan else v for k,v in inverse['inputs_sha256'].items()};inverse['launch_ready']=l0['launch_ready'];inverse['root_GO_sha256']=l0['root_GO_sha256'];inverse['command'][4]=l0['command'][4];inverse['command'][5]=l0['command'][5];assert inverse==l0 and enc(inverse)==(H/'pending-launch.json').read_bytes()
inverse=read(H/'command.json');inverse['launch_ready']=c0['launch_ready'];inverse['argv'][4]=c0['argv'][4];inverse['argv'][6]=c0['argv'][6];assert inverse==c0 and enc(inverse)==(H/'pending-command.json').read_bytes()
assert a['status']=='actual_closed_current07b_coarse_fields_rendered_no_new_FEA'and a['plan_sha256']==sha(H/'plan.json')and a['source_sha256']==sha(H/'figure.py')and a['data_sources_sha256']==p['files_sha256']and a['runtime_sha256']==p['runtime_sha256']
assert a['all_faces_used']and a['common_color_scales']and a['all_global_IP_peaks_retained']and a['all_axes_common_mm']and not a['FEA_started']and not a['geometry_modified']and not a['stress_convergence_established']and a['strength_allowable']is None and p['new_complete_function_contract_passed']is True and a['cwd']=='/'
assert len(a['runtime_sha256'])==219 and set(a['runtime_imported_files'])<=set(a['runtime_sha256'])and all(sha(Path(n))==h for n,h in a['runtime_sha256'].items())
assert len(p['cases'])==len(a['global_maxima'])==2 and len(a['checks'])==4
case_records=[]
vm_max=max(read(R/r['record'])['integration_point_VM_max_MPa']for r in p['cases']);u_max=max(read(R/r['record'])['displacement_max_mm']for r in p['cases'])
for i,(row,summary)in enumerate(zip(p['cases'],a['global_maxima'])):
 record=read(R/row['record']);peak=read(R/row['peaks']);review=read(R/p['root_review']);root_case=review['cases'][row['role']]
 assert summary['global_IP_VM_MPa']==record['integration_point_VM_max_MPa']==peak['maximum_VM_MPa']and summary['all_nodes_Umax_mm']==record['displacement_max_mm']and summary['all_global_IP_ties']==peak['all_global_maximum_ties']==root_case['all_global_peak_ties']
 assert summary['all_IP_rows']==4*peak['C3D10_elements']and summary['all_global_U_nodes']and all(v['U_mm']==summary['all_nodes_Umax_mm']for v in summary['all_global_U_nodes'])
 assert peak['CAD_source']['sha256']==p['actual_BREP_sha256']and peak['CAD_source']['STEP_exchange_qualified']is False
 assert 0<=summary['displayed_boundary_element_VM_max_MPa']<=summary['global_IP_VM_MPa']
 for j,field in enumerate(['VM','U']):
  check=a['checks'][2*i+j]
  assert check['case']==row['case']and check['field']==field and check['all_boundary_faces_submitted']==check['displayed_face_values']==summary['reference_surface_faces']and check['color_scale']==[0,vm_max if field=='VM'else u_max]and check['orthographic']and check['deformation_amplification']==1 and check['decimation']is False
  assert check['xlim']==a['checks'][0]['xlim']and check['ylim']==a['checks'][0]['ylim']
 case_records.append(dict(role=row['role'],mesh_variant='current07b_coarse',case=row['case'],global_maxima=summary))
expected={'carrier-complete-function-stress-displacement.'+e for e in ['png','svg','pdf']};assert {q.name for q in render.iterdir()}==expected|{'render-receipt.json'}and set(a['outputs_sha256'])==expected and all(sha(render/n)==h for n,h in a['outputs_sha256'].items())
png=render/'carrier-complete-function-stress-displacement.png'
with png.open('rb')as f:head=f.read(24)
assert head[:8]==b'\x89PNG\r\n\x1a\n';dimensions=list(struct.unpack('>II',head[16:24]));assert dimensions==[3060,2232]
assert ET.parse(render/'carrier-complete-function-stress-displacement.svg').getroot().tag.endswith('svg')
assert(H/'execution-001/stderr.log').stat().st_size==(H/'execution-001/stdout.log').stat().st_size==0
q=subprocess.run(['/bin/ps','-g',str(s['pid']),'-o','pid=,ppid=,pgid=,stat='],capture_output=True,text=True,timeout=2);assert q.returncode==1 and not q.stdout.strip()and not q.stderr.strip()
whole={str(q.relative_to(H)):dict(bytes=q.stat().st_size,sha256=sha(q))for folder in ['render-001','execution-001']for q in sorted((H/folder).iterdir())if q.is_file()};assert len(whole)==8
tool=read(H/'actual-tool-terminal-001.json');assert tool['actual_tool_returncode']==0 and tool['actual_tool_handle']==59482
v=dict(schema='actual-current07b-coarse-field-render-terminal-1',status='closed_actual_RC0_two_current07b_cases_four_panels_no_new_science',actual_tool_handle=tool['actual_tool_handle'],actual_initial_chunk=tool['actual_initial_chunk'],actual_terminal_chunk=tool['actual_terminal_chunk'],actual_tool_returncode=0,actual_child_returncode=0,actual_tool_terminal_sha256=sha(H/'actual-tool-terminal-001.json'),owned_pid=s['pid'],direct_child_reaped=True,owned_group_empty=True,fresh_owned_group_query=dict(returncode=q.returncode,stdout=q.stdout,stderr=q.stderr),supervision_sha256=sha(H/'execution-001/execution-receipt.json'),render_receipt_sha256=sha(render/'render-receipt.json'),all8_whole_outputs=whole,actual_launch_map_entries=len(pins),all_current_pins_and_before_after_maps_equal=True,whole_three_pending_inverses_original_bytes=True,original_child_SYSTEM_B_no_I=True,actual_runtime_files=len(a['runtime_sha256']),actual_postexport_imported_files=len(a['runtime_imported_files']),all_imported_plot_runtime_files_attested=True,PNG_dimensions=dimensions,SVG_XML_parsed=True,ROOT_visual_review=None,PDF_raster_visual_review=False,all4_field_checks=a['checks'],two_actual_case_global_maxima=case_records,elapsed_seconds=s['elapsed_seconds'],render_wall_seconds=a['wall_seconds'],render_CPU_seconds=a['CPU_seconds'],render_maxRSS_bytes=a['maxRSS_bytes'],candidate_qualified=False,complete_native_function_passed=True,all_original_stock_and_candidate_refusals_preserved=True,current_coarse_FEA_ROOT_sha256=p['root_review_sha256'],current_BREP_sha256=p['actual_BREP_sha256'],stress_convergence_or_strength_admission=False,new_solver_or_mesh_or_CAD_run=False,publication_stage_or_commit=False,collector_source_sha256=sha(Path(__file__)))
with(H/'terminal-collection-001.json').open('x')as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps({k:x for k,x in v.items()if k not in ['fresh_owned_group_query','all8_whole_outputs','all4_field_checks','two_actual_case_global_maxima']}));print('terminal_sha256='+sha(H/'terminal-collection-001.json'))
