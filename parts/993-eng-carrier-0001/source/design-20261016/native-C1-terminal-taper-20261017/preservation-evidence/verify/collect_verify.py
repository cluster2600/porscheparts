"""Collect this stored-byte verification without repeating decompression."""
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
l=read(H/'verify-launch.json');s=read(H/'verify-execution-001/execution-receipt.json');pins={**l['inputs_sha256'],**l['source_sha256']};assert s['actual_returncode']==0 and s['direct_child_reaped']and s['final_group_members']==[]and s['no_non_zombie_group_members']and not s['timeout']and not s['interrupted']and s['failure']is None and s['cleanup_error']is None and s['sources_and_plan_unchanged'];assert s['plan_sha256']==sha(H/'verify-launch.json')and s['sources_before']==s['sources_after']==pins=={n:sha(R/n)for n in pins};stdout=read(H/'verify-execution-001/stdout.log');assert stdout==dict(status='all_archived_original_bytes_verified',archives=3,files=495,new_solver_run=False);assert(H/'verify-execution-001/stderr.log').stat().st_size==0 and not(H/'verify-output-001').exists()
o=read(H/'pending-verify-launch.json');x=read(H/'verify-launch.json');x.update(status=o['status'],launch_ready=False,root_GO=None,root_GO_sha256=None);x['inputs_sha256'].pop(l['root_GO']);assert enc(x)==(H/'pending-verify-launch.json').read_bytes();o=read(H/'pending-verify-command.json');x=read(H/'verify-command.json');x.pop('argv');x.update(status=o['status'],launch_ready=False,actual_launch_sha256=None);assert enc(x)==(H/'pending-verify-command.json').read_bytes()
q=subprocess.run(['/bin/ps','-g',str(s['pid']),'-o','pid=,ppid=,pgid=,stat='],capture_output=True,text=True,timeout=2);assert q.returncode==1 and not q.stdout.strip()and not q.stderr.strip();whole={str(p.relative_to(H)):dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted((H/'verify-execution-001').iterdir())if p.is_file()}
v=dict(status='closed_actual_RC0_all495_preserved_original_member_bytes_verified',actual_tool_handle=87703,actual_initial_chunk='90fb84',actual_terminal_chunk='fce72a',actual_tool_returncode=0,actual_child_returncode=0,supervision_sha256=sha(H/'verify-execution-001/execution-receipt.json'),actual_stdout=stdout,manifest_sha256=l['capsule_manifest_sha256'],actual_pack_ROOT_sha256=l['actual_pack_ROOT_sha256'],current_launch_map_entries=len(pins),all_current_pins_equal=True,complete_capsule_posthashes_equal=True,two_whole_pending_inverses_original_bytes=True,direct_child_reaped=True,final_group_empty=True,owned_pid=s['pid'],fresh_group_query=dict(returncode=q.returncode,stdout=q.stdout,stderr=q.stderr),elapsed_seconds=s['elapsed_seconds'],reserved_output_absent_as_expected=True,second_decompression_in_collector=False,analysis_replay_executed=False,new_native_science_runs=0,whole_execution_files=whole,collector_source_sha256=sha(Path(__file__)))
with(H/'verify-terminal-collection-001.json').open('x')as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps({k:x for k,x in v.items()if k not in ['fresh_group_query','whole_execution_files']}));print('terminal_sha256='+sha(H/'verify-terminal-collection-001.json'))
