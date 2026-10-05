#!/usr/bin/env python3
"""Run one explicitly bounded matched-grid case in the existing Foundation image."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil

IMAGE='sha256:49979f46f421459dae4bf21aaa898e2253b07301c3e5b2cabaa6eaf06f54d696'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('label');p.add_argument('cad',type=Path);p.add_argument('refinement',type=Path)
    p.add_argument('--size-mm',type=float,required=True);p.add_argument('--minimum-size-mm',type=float,required=True)
    p.add_argument('--cpu-set',default='0,2,4,5',help='Four logical CPUs on distinct physical cores; verify lscpu locally')
    p.add_argument('--protocol-template',type=Path)
    p.add_argument('--mesh-only',action='store_true',help='Prepare and independently check the mesh without a flow solve')
    p.add_argument('--split-300',action='store_true',help='Two explicitly bounded 300-iteration phases, preserving the first case')
    a=p.parse_args();root=Path.cwd()
    if subprocess.check_output(['docker','ps','--filter','ancestor='+IMAGE,'--format','{{.ID}}'],text=True).strip():raise ValueError('An existing solver container is active; no concurrent calculation')
    mesh=root/('mesh-'+a.label);case=root/('cfd-'+a.label)
    if len(a.cpu_set.split(','))!=4 or any(not c.isdigit() for c in a.cpu_set.split(',')):raise ValueError('Four explicit CPU IDs required')
    def bounded(label,cmd,threads=1,mem=5,seconds=300):
        subprocess.run([sys.executable,'run_bounded_task.py','--label',label,'--threads',str(threads),'--memory-gib',str(mem),'--timeout',str(seconds),'--',*map(str,cmd)],check=True)
    def docker(command,threads=1,mem=3,script=None):
        cmd=['docker','run','--pull=never','--rm','--network','none','--cpus',str(threads),'--memory',str(mem)+'g','--memory-swap',str(mem)+'g','--pids-limit','256','--cap-drop','ALL','--security-opt','no-new-privileges','--user',str(os.getuid())+':'+str(os.getgid()),'--env','OMP_NUM_THREADS=1','--env','OPENBLAS_NUM_THREADS=1','--mount',f'type=bind,source={case},target=/case']
        if threads==4:cmd+=['--cpuset-cpus',a.cpu_set]
        if script:cmd+=['--mount',f'type=bind,source={root/script},target=/runner.sh,readonly']
        return cmd+[IMAGE,'bash','/runner.sh'] if script else cmd+[IMAGE,'bash','-c',command]
    bounded(a.label+'-mesh',[sys.executable,'build_analytical_mesh.py',a.cad,mesh,'--mode','fluid','--size-mm',a.size_mm,'--minimum-size-mm',a.minimum_size_mm,'--netgen','--local-refinement',a.refinement])
    subprocess.run([sys.executable,'prepare_analytical_cfd.py',mesh,case,a.cad/'parameters.json','--iterations','300' if a.split_300 else '600'],check=True)
    bounded(a.label+'-gate',docker(None,script='gate-local.sh'),mem=3,seconds=120)
    if a.mesh_only:return
    template_path=a.protocol_template or Path(__file__).resolve().parents[1]/'parameters/V2-common-h7-protocol.json'
    if not template_path.is_file():template_path=root/'cfd-V2-short-edge-resolution-run2/reference-protocol.json'
    protocol=json.loads(template_path.read_text())
    protocol.update(protocol_id=a.label+'-6000rpm-600iterations',reference_configuration=json.loads((a.cad/'parameters.json').read_text())['configuration_id'],cpu_set_verified_distinct_physical_cores=a.cpu_set,grid_policy_sha256=hashlib.sha256(a.refinement.read_bytes()).hexdigest())
    protocol.pop('previous_attempt',None)
    if a.split_300:protocol.update(iterations=300,planned_continuation_target=600,planned_phases=2,wall_timeout_seconds_each_phase=600)
    (case/'reference-protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    bounded(a.label+'-flow',docker(None,threads=4,mem=5,script='run_parallel_pilot.sh'),threads=4,mem=5,seconds=600)
    if a.split_300:
        subprocess.run([sys.executable,'summarize_reference_flow.py',case,root/(a.label+'-phase300-summary.json')],check=True)
        previous=case;case=root/('cfd-'+a.label+'-continuation600');case.mkdir(exist_ok=False)
        for name in ['0','300','constant','system']:shutil.copytree(previous/name,case/name)
        for name in ['preparation.json','independent-mesh-gate.json']:shutil.copyfile(previous/name,case/name)
        control=case/'system/controlDict';text=control.read_text().replace('startFrom startTime','startFrom latestTime').replace('endTime 300','endTime 600');control.write_text(text)
        protocol.update(protocol_id=a.label+'-6000rpm-continuation600',iterations=600,initial_fields_sha256={str(p.relative_to(previous)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (previous/'300').iterdir() if p.is_file()})
        (case/'reference-protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
        bounded(a.label+'-continuation600',docker(None,threads=4,mem=5,script='run_parallel_pilot.sh'),threads=4,mem=5,seconds=600)
    subprocess.run([sys.executable,'summarize_reference_flow.py',case,root/(a.label+'-flow-summary.json')],check=True)
    bounded(a.label+'-gradient',docker('source /opt/openfoam13/etc/bashrc; cd /case; foamPostProcess -solver incompressibleFluid -func "grad(U)" -time 600'),mem=3,seconds=90)
    bounded(a.label+'-balance',[sys.executable,'analyze_flow_balance.py',case,root/(a.label+'-balance.json')],mem=3,seconds=90)

if __name__=='__main__':main()
