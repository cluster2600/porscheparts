#!/usr/bin/env python3
"""Preserve a completed flow attempt and freeze one additional bounded 150-step phase."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from measurement_window import configure_measurement_cadence
import re
import shutil
import subprocess
import sys
from run_existing_grid_sensitivity import IMAGE


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source_case',type=Path);p.add_argument('label');p.add_argument('--pressure-relaxation',type=float);a=p.parse_args();root=Path.cwd();source=a.source_case.resolve()
    if subprocess.check_output(['docker','ps','--filter','ancestor='+IMAGE,'--format','{{.ID}}'],text=True).strip():raise ValueError('An existing study flow container is active')
    protocol=json.loads((source/'reference-protocol.json').read_text());gate=json.loads((source/'independent-mesh-gate.json').read_text());initial=int(protocol['iterations']);end=initial+150
    if not gate['accepted_for_bounded_pilot'] or not (source/str(initial)).is_dir():raise ValueError('Independently admitted mesh and completed checkpoint required')
    case=root/('cfd-'+a.label);case.mkdir(exist_ok=False)
    for name in ['0',str(initial),'constant','system']:shutil.copytree(source/name,case/name)
    for name in ['preparation.json','independent-mesh-gate.json']:shutil.copyfile(source/name,case/name)
    previous_sha=hashlib.sha256((source/'reference-protocol.json').read_bytes()).hexdigest()
    protocol.update(protocol_id=a.label,iterations=end,previous_frozen_protocol_sha256=previous_sha,previous_target_iteration=initial,additional_phase_reason='Pressure residual did not satisfy the unchanged frozen criterion; preserve previous result and continue its fields',planned_total_target=end,wall_timeout_seconds=600,maximum_CPU=4,maximum_memory_GiB=5,initial_fields_sha256={str(f.relative_to(source)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (source/str(initial)).iterdir() if f.is_file()},flow_runner_sha256=hashlib.sha256((root/'run_parallel_pilot.sh').read_bytes()).hexdigest())
    protocol['planned_phase_end_iterations']=protocol.get('planned_phase_end_iterations',[])+[end]
    control=case/'system/controlDict';s=control.read_text();s=re.sub(r'\bstartFrom\s+\w+','startFrom latestTime',s);s=re.sub(r'\bendTime\s+[0-9]+','endTime '+str(end),s);s=configure_measurement_cadence(s,150)
    control.write_text(s)
    if a.pressure_relaxation is not None:
        if not 0<a.pressure_relaxation<=.25:raise ValueError('Pressure relaxation must be positive and no higher than the original 0.25')
        fv=case/'system/fvSolution';before=fv.read_bytes();text=before.decode()
        match=re.search(r'(relaxationFactors\s*\{\s*fields\s*\{\s*p\s+)([.0-9]+)(;)',text)
        if not match:raise ValueError('Original pressure relaxation entry not found')
        text=text[:match.start(2)]+format(a.pressure_relaxation,'.8g')+text[match.end(2):];fv.write_text(text)
        protocol.update(numerical_pressure_relaxation_before=float(match[2]),numerical_pressure_relaxation_after=a.pressure_relaxation,fvSolution_before_sha256=hashlib.sha256(before).hexdigest(),fvSolution_after_sha256=hashlib.sha256(fv.read_bytes()).hexdigest(),numerical_sensitivity_reason='Reduce pressure update oscillation; same discretization, solver tolerances, physical inputs and original acceptance thresholds; matched reference sensitivity required')
    protocol['frozen_system_file_sha256']={str(f.relative_to(case)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (case/'system').iterdir() if f.is_file()}
    (case/'reference-protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    def bounded(label,command,threads=4,mem=5,seconds=600):subprocess.run([sys.executable,'run_bounded_task.py','--label',label,'--threads',str(threads),'--memory-gib',str(mem),'--timeout',str(seconds),'--',*map(str,command)],check=True)
    def docker(command=None):
        args=['docker','run','--pull=never','--rm','--network','none','--cpus','4','--cpuset-cpus','0,2,4,5','--memory','5g','--memory-swap','5g','--pids-limit','256','--cap-drop','ALL','--security-opt','no-new-privileges','--user',str(os.getuid())+':'+str(os.getgid()),'--env','OMP_NUM_THREADS=1','--env','OPENBLAS_NUM_THREADS=1','--mount',f'type=bind,source={case},target=/case','--mount',f'type=bind,source={root}/run_parallel_pilot.sh,target=/runner.sh,readonly',IMAGE,'bash']
        return args+['/runner.sh'] if command is None else args+['-c',command]
    bounded(a.label+'-flow',docker())
    bounded(a.label+'-summary',[sys.executable,'summarize_reference_flow.py',case,root/(a.label+'-summary.json')],threads=1,mem=3,seconds=90)
    bounded(a.label+'-gradient',docker('source /opt/openfoam13/etc/bashrc; cd /case; foamPostProcess -solver incompressibleFluid -func "grad(U)" -time '+str(end)),seconds=90)
    bounded(a.label+'-balance',[sys.executable,'analyze_flow_balance.py',case,root/(a.label+'-balance-v4.json'),'--time',str(end)],threads=1,mem=3,seconds=90)
    print('Additional bounded phase completed with unchanged criteria; admission is determined by its actual summary')

if __name__=='__main__':main()
