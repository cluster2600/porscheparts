"""Collect only the closed archive-cap refusal; no archive decompression or retry."""
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
s=read(H/'pack-execution-001/execution-receipt.json');p=read(H/'pack-plan.json');l=read(H/'pack-launch.json');pins={**l['inputs_sha256'],**l['source_sha256']};assert s['actual_returncode']==1 and s['direct_child_reaped']and s['final_group_members']==[]and s['no_non_zombie_group_members']and not s['timeout']and not s['interrupted']and not s['cleanup_error']and not s['failure']and s['sources_and_plan_unchanged'];assert s['plan_sha256']==sha(H/'pack-launch.json')and pins==s['sources_before']==s['sources_after']=={n:sha(R/n)for n in pins}
error=(H/'pack-execution-001/stderr.log').read_text();assert error.endswith('ValueError: Archive exceeds the strict 100 MB limit\n');actual={q.name:q for q in(H/'capsule-001').iterdir()};assert set(actual)=={'taper-common.zip'}and actual['taper-common.zip'].stat().st_size==110433657;assert not(H/'packaging.json').exists()and not(H/'capsule-001/manifest.json').exists()
op=read(H/'pending-pack-plan.json');x=read(H/'pack-plan.json');x.update(status=op['status'],launch_ready=False,root_GO=None,root_GO_sha256=None);x['files_sha256'].pop(p['root_GO']);assert enc(x)==(H/'pending-pack-plan.json').read_bytes()
ol=read(H/'pending-pack-launch.json');x=read(H/'pack-launch.json');x.update(status=ol['status'],launch_ready=False,root_GO=None,root_GO_sha256=None);x['command']=ol['command'];x['inputs_sha256']=ol['inputs_sha256'];assert enc(x)==(H/'pending-pack-launch.json').read_bytes()
oc=read(H/'pending-pack-command.json');x=read(H/'pack-command.json');x.pop('argv');x.update(status=oc['status'],launch_ready=False,actual_launch_sha256=None);assert enc(x)==(H/'pending-pack-command.json').read_bytes()
q=subprocess.run(['/bin/ps','-g',str(s['pid']),'-o','pid=,ppid=,pgid=,stat='],capture_output=True,text=True,timeout=2);assert q.returncode==1 and not q.stdout.strip()and not q.stderr.strip()
files=[H/'actual-pack-plan.json',*[x for x in(H/'pack-execution-001').iterdir()if x.is_file()],*actual.values()];whole={str(x.relative_to(H)):dict(bytes=x.stat().st_size,sha256=sha(x))for x in sorted(files)}
v=dict(status='closed_actual_RC1_strict_common_archive_size_refusal_no_retry',actual_tool_handle=43753,actual_initial_chunk='e44b83',actual_terminal_chunk='19beb6',actual_tool_returncode=1,actual_child_returncode=1,supervision_sha256=sha(H/'pack-execution-001/execution-receipt.json'),current_pin_map_entries=len(pins),all_current_small_pins_equal=True,three_whole_pending_inverses_original_bytes=True,owned_pid=s['pid'],direct_child_reaped=True,final_group_empty=True,fresh_group_query=dict(returncode=q.returncode,stdout=q.stdout,stderr=q.stderr),elapsed_seconds=s['elapsed_seconds'],actual_common_archive_bytes=110433657,strict_archive_limit_bytes=100000000,packaging_receipt_written=False,manifest_written=False,original495_final_postrehash_reached=False,actual_archives_complete=False,archive_decompression_executed=False,stored_evidence_verification_executed=False,analysis_replay_executed=False,new_scientific_runs=0,candidate_qualified=False,whole_files=whole,whole_files_count=len(whole),collector_source_sha256=sha(Path(__file__)))
with(H/'terminal-collection-001.json').open('x')as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps({k:x for k,x in v.items()if k not in ['whole_files','fresh_group_query']}));print('terminal_sha256='+sha(H/'terminal-collection-001.json'));print(json.dumps(whole['capsule-001/taper-common.zip']))
