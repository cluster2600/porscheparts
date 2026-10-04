#!/usr/bin/env python3
"""Sequential native CalculiX scenario jobs; no calibrated process prediction."""
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from prepare_engineering_sensitivities import parse_mesh
from summarize_engineering_sensitivities import displacement_blocks, stress_blocks

def run(label,command,directory=Path('.'),seconds=600):
    subprocess.run([sys.executable,'run_bounded_task.py','--directory',str(directory),'--label',label,'--threads','4','--memory-gib','5','--timeout',str(seconds),'--',*map(str,command)],check=True)

def benchmark(root):
    case=root/'manufacturing-analytic-benchmark';case.mkdir(exist_ok=False)
    (case/'unit-eigenstrain.inp').write_bytes((root/'unit-eigenstrain.inp').read_bytes())
    run('native-benchmark',['ccx','-i','unit-eigenstrain'],case,60)
    nodes,_=parse_mesh((case/'unit-eigenstrain.inp').read_text());u=displacement_blocks(case/'unit-eigenstrain.frd')[-1];s=stress_blocks(case/'unit-eigenstrain.dat')[-1]
    error=max(float(np.linalg.norm(u[n]+.001*x)) for n,x in nodes.items());stress=max(float(np.abs(v).max()) for v in s.values())
    log=(case/'log.native-benchmark').read_text()
    if error>1e-8 or stress>1e-7 or 'Job finished' not in log or '*ERROR' in log:raise ValueError('Analytical strain benchmark failed')
    report={'status':'passed','solver':'Native CalculiX 2.23','analytical_solution':'Released uniform contraction U=-0.001*x, zero stress','maximum_displacement_error_mm':error,'maximum_released_stress_component_MPa':stress,'limits':{'displacement_mm':1e-8,'stress_MPa':1e-7},'process_calibration_established':False}
    (case/'summary.json').write_text(json.dumps(report,indent=2)+'\n')

def main():
    root=Path.cwd()
    if (root/'manufacturing-analytic-benchmark/summary.json').is_file():
        if json.load(open(root/'manufacturing-analytic-benchmark/summary.json'))['status']!='passed':raise ValueError('Existing benchmark not admitted')
    else:benchmark(root)
    if not (root/'manufacturing-case-list.json').is_file():run('manufacturing-deck-preparation',[sys.executable,'build_manufacturing_scenarios.py'],seconds=180)
    for label in json.loads((root/'manufacturing-case-list.json').read_text()):
        case=root/label
        if not (case/'log.solve').is_file():run('solve',['ccx','-i','rotor'],case)
        receipt=json.load(open(case/'receipt.solve.json'));log=(case/'log.solve').read_text()
        if receipt['exit_status'] or 'Job finished' not in log or '*ERROR' in log:raise ValueError('Existing job cannot be resumed as success '+label)
        if not (case/'log.ccx').exists():(case/'log.ccx').write_bytes((case/'log.solve').read_bytes())
        if (case/'summary.json').is_file():
            from summarize_engineering_sensitivities import eigenstrain
            if eigenstrain(case)!=json.load(open(case/'summary.json')):raise ValueError('Existing summary no longer matches native fields')
            continue
        run(label+'-summarize',[sys.executable,root/'summarize_engineering_sensitivities.py','eigenstrain',case,case/'summary.json'],seconds=120)
        print(label+' completed',flush=True)

if __name__=='__main__':main()
