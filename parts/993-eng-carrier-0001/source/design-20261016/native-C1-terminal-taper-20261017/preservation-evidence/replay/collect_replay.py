"""Collect this one closed analysis replay; hashes/JSON only, no numerical rerun."""
from pathlib import Path
import hashlib,json,os,subprocess
H=Path(__file__).resolve().parent;R=H.parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(p.read_text())
def enc(v):return(json.dumps(v,indent=2)+'\n').encode()
l=read(H/'replay-launch.json');s=read(H/'analysis-execution-001/execution-receipt.json');pins={**l['inputs_sha256'],**l['source_sha256']};assert s['actual_returncode']==0 and s['direct_child_reaped']and s['final_group_members']==[]and s['no_non_zombie_group_members']and not s['timeout']and not s['interrupted']and s['failure']is None and s['cleanup_error']is None and s['sources_and_plan_unchanged'];assert s['plan_sha256']==sha(H/'replay-launch.json')and pins==s['sources_before']==s['sources_after']=={n:sha(R/n)for n in pins};a=read(H/'analysis-replay-001/reanalysis-receipt.json');assert read(H/'analysis-execution-001/stdout.log')==a and(H/'analysis-execution-001/stderr.log').stat().st_size==0
assert a['status']=='two_preserved_taper_cases_reanalysed_entire_results_and_bytes_equal'and a['actual_returncode']==0 and a['capsule_manifest_sha256']==l['capsule_manifest_sha256']and a['runtime_unchanged']and a['runtime_files']==500 and a['restored_inputs_unchanged']and a['cwd']=='/'and a['actual_workers']==0 and not a['new_solver_run']and not a['new_mesh']and not a['stress_convergence_established'];assert len(a['cases'])==2 and all(x['energy_result_entirely_equal']and x['peak_result_entirely_equal']and x['tolerance']==1e-4 for x in a['cases'])
m=read(H/'capsule-001/manifest.json');restored=H/'analysis-replay-001/restored';members={n:row for slot in m['archives'].values()for n,row in slot['members'].items()};actual={str(p.relative_to(restored))for p in restored.rglob('*')if p.is_file()};assert actual==set(members)and len(actual)==495 and all((restored/n).stat().st_size==row['bytes']and sha(restored/n)==row['sha256']for n,row in members.items())
reports={}
for case in m['cases']:
 for label,name in [('energy','energy-audit.json'),('peak','global-peaks.json')]:
  new=H/'analysis-replay-001'/(case['key']+'-'+label+'.json');old=restored/case['root']/name;assert read(new)==read(old)and new.read_bytes()==old.read_bytes();reports[new.name]=dict(bytes=new.stat().st_size,sha256=sha(new),whole_JSON_equal=True,serialized_bytes_equal=True)
o=read(H/'pending-replay-launch.json');x=read(H/'replay-launch.json');x.update(status=o['status'],launch_ready=False,root_GO=None,root_GO_sha256=None)
for n in set(x['inputs_sha256'])-set(o['inputs_sha256']):x['inputs_sha256'].pop(n)
assert enc(x)==(H/'pending-replay-launch.json').read_bytes();o=read(H/'pending-replay-command.json');x=read(H/'replay-command.json');x.pop('argv');x.update(status=o['status'],launch_ready=False,actual_launch_sha256=None);assert enc(x)==(H/'pending-replay-command.json').read_bytes()
q=subprocess.run(['/bin/ps','-g',str(s['pid']),'-o','pid=,ppid=,pgid=,stat='],capture_output=True,text=True,timeout=2);assert q.returncode==1 and not q.stdout.strip()and not q.stderr.strip()
files=[p for directory in ['analysis-replay-001','analysis-execution-001']for p in sorted((H/directory).rglob('*'))if p.is_file()];whole={str(p.relative_to(H)):dict(bytes=p.stat().st_size,sha256=sha(p))for p in files};assert len(whole)==504
v=dict(status='closed_actual_RC0_one495_restore_four_entire_report_objects_and_bytes_equal',actual_tool_handle=64098,actual_initial_chunk='9454f0',actual_terminal_chunk='9bef42',actual_tool_returncode=0,actual_child_returncode=0,supervision_sha256=sha(H/'analysis-execution-001/execution-receipt.json'),reanalysis_receipt_sha256=sha(H/'analysis-replay-001/reanalysis-receipt.json'),manifest_sha256=l['capsule_manifest_sha256'],actual_pack_ROOT_sha256=l['actual_pack_ROOT_sha256'],actual_verify_ROOT_sha256=sha(H/'root-verify-terminal-review-001.json'),current_launch_map_entries=len(pins),all_current_pins_equal=True,two_whole_pending_inverses_original_bytes=True,restored_originals=495,all_restored_originals_postSHA_equal=True,four_entire_report_objects_and_serialized_bytes_equal=True,actual_reports=reports,actual_reanalysis=a,direct_child_reaped=True,final_group_empty=True,owned_pid=s['pid'],fresh_group_query=dict(returncode=q.returncode,stdout=q.stdout,stderr=q.stderr),outer_elapsed_seconds=s['elapsed_seconds'],runtime_files_verified_before_after=500,second_restoration_or_scientific_reanalysis_in_collector=False,new_native_CAD_Gmsh_CCX_runs=0,whole_output_files=whole,whole_output_count=len(whole),collector_source_sha256=sha(Path(__file__)))
with(H/'replay-terminal-collection-001.json').open('x')as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps({k:x for k,x in v.items()if k not in ['whole_output_files','fresh_group_query','actual_reanalysis']}));print('terminal_sha256='+sha(H/'replay-terminal-collection-001.json'))
