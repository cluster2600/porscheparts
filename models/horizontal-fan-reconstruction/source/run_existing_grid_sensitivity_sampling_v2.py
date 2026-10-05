#!/usr/bin/env python3
"""Run an admitted existing mesh in four predeclared 150-iteration phases."""
import argparse,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
IMAGE='sha256:49979f46f421459dae4bf21aaa898e2253b07301c3e5b2cabaa6eaf06f54d696'


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source_case',type=Path);p.add_argument('label');p.add_argument('--protocol-template',type=Path);a=p.parse_args();root=Path.cwd();source=a.source_case.resolve();gate=json.load(open(source/'independent-mesh-gate.json'))
 if not gate['accepted_for_bounded_pilot']:raise ValueError('Both independent mesh checks must pass')
 if subprocess.check_output(['docker','ps','--filter','ancestor='+IMAGE,'--format','{{.ID}}'],text=True).strip():raise ValueError('An existing solver container is still active; no concurrent calculation')
 preparation=json.load(open(source/'preparation.json'))
 template_path=a.protocol_template or Path(__file__).resolve().parents[1]/'parameters/V2-common-h7-protocol.json'
 if not template_path.is_file():template_path=root/'cfd-V2-short-edge-resolution-run2/reference-protocol.json'
 template=json.loads(template_path.read_text());previous=None
 def bounded(label,command,threads=4,mem=5,seconds=600):
  subprocess.run([sys.executable,'run_bounded_task.py','--label',label,'--threads',str(threads),'--memory-gib',str(mem),'--timeout',str(seconds),'--',*map(str,command)],check=True)
 def docker(case,command=None):
  cmd=['docker','run','--pull=never','--rm','--network','none','--cpus','4','--cpuset-cpus','0,2,4,5','--memory','5g','--memory-swap','5g','--pids-limit','256','--cap-drop','ALL','--security-opt','no-new-privileges','--user',str(os.getuid())+':'+str(os.getgid()),'--env','OMP_NUM_THREADS=1','--env','OPENBLAS_NUM_THREADS=1','--mount',f'type=bind,source={case},target=/case','--mount',f'type=bind,source={root}/run_parallel_pilot.sh,target=/runner.sh,readonly',IMAGE,'bash']
  return cmd+['/runner.sh'] if command is None else cmd+['-c',command]
 for end in [150,300,450,600]:
  case=root/('cfd-'+a.label+'-phase'+str(end));case.mkdir(exist_ok=False)
  for name in ['0','constant','system']:shutil.copytree(source/name,case/name)
  for name in ['preparation.json','independent-mesh-gate.json']:shutil.copyfile(source/name,case/name)
  protocol=dict(template);protocol.update(protocol_id=a.label+'-phase'+str(end),reference_configuration=preparation['configuration_id'],iterations=end,planned_total_target=600,planned_phase_end_iterations=[150,300,450,600],wall_timeout_seconds=600,maximum_CPU=4,maximum_memory_GiB=5,cpu_set_verified_distinct_physical_cores='0,2,4,5',source_mesh_gate_sha256=hashlib.sha256((source/'independent-mesh-gate.json').read_bytes()).hexdigest(),flow_runner_sha256=hashlib.sha256((root/'run_parallel_pilot.sh').read_bytes()).hexdigest())
  protocol.pop('previous_attempt',None)
  if previous:
   initial=str(end-150);shutil.copytree(previous/initial,case/initial);protocol['initial_fields_sha256']={str(f.relative_to(previous)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (previous/initial).iterdir() if f.is_file()}
  control=case/'system/controlDict';s=control.read_text();s=re.sub(r'\bstartFrom\s+\w+','startFrom latestTime' if previous else 'startFrom startTime',s);s=re.sub(r'\bendTime\s+[0-9]+','endTime '+str(end),s);s=re.sub(r'\bwriteInterval\s+[0-9]+','writeInterval 150',s);control.write_text(s)
  (case/'reference-protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
  bounded(a.label+'-phase'+str(end),docker(case))
  bounded(a.label+'-summary'+str(end),[sys.executable,'summarize_reference_flow.py',case,root/(a.label+'-phase'+str(end)+'-summary.json')],threads=1,mem=3,seconds=90)
  previous=case
 bounded(a.label+'-gradient',docker(previous,'source /opt/openfoam13/etc/bashrc; cd /case; foamPostProcess -solver incompressibleFluid -func "grad(U)" -time 600'),threads=4,mem=5,seconds=90)
 bounded(a.label+'-balance',[sys.executable,'analyze_flow_balance.py',previous,root/(a.label+'-balance.json')],threads=1,mem=3,seconds=90)
 print('Four bounded phases completed; grid independence and physical validation remain unestablished',flush=True)

if __name__=='__main__':main()
