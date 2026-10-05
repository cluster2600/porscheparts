#!/usr/bin/env python3
"""Sequential actual-field checks after all matched flow phases have finished."""
import os
from pathlib import Path
import subprocess
import sys
from run_existing_grid_sensitivity import IMAGE


def main():
    root=Path.cwd()
    if subprocess.check_output(['docker','ps','--filter','ancestor='+IMAGE,'--format','{{.ID}}'],text=True).strip():raise ValueError('Wait for the existing solver container; no concurrent calculation')
    def bounded(label,command,seconds=90):
        subprocess.run([sys.executable,'run_bounded_task.py','--label',label,'--threads','1','--memory-gib','3','--timeout',str(seconds),'--',*map(str,command)],check=True)
    case=root/'cfd-V2-short-edge-resolution-run2'
    if not (case/'600/grad(U)').is_file():
        bounded('V2-common-h7-gradient-v4',['docker','run','--pull=never','--rm','--network','none','--cpus','1','--memory','3g','--memory-swap','3g','--pids-limit','256','--cap-drop','ALL','--security-opt','no-new-privileges','--user',str(os.getuid())+':'+str(os.getgid()),'--env','OMP_NUM_THREADS=1','--env','OPENBLAS_NUM_THREADS=1','--mount',f'type=bind,source={case},target=/case',IMAGE,'bash','-c','source /opt/openfoam13/etc/bashrc; cd /case; foamPostProcess -solver incompressibleFluid -func "grad(U)" -time 600'])
    for variant in ['R0','V2']:
        for grid in ['h7','h5p6']:
            case=root/(('cfd-R0-common-h7' if variant=='R0' else 'cfd-V2-short-edge-resolution-run2') if grid=='h7' else 'cfd-'+variant+'-fine-150steps-phase600')
            output=root/(variant+'-common-'+grid+'-balance-v4.json')
            if output.exists():raise FileExistsError('Do not overwrite an independent actual-field analysis')
            bounded(variant+'-common-'+grid+'-balance-v4',[sys.executable,'analyze_flow_balance.py',case,output])
    bounded('verify-native-benchmark',[sys.executable,'verify_native_benchmark.py',root/'manufacturing-analytic-benchmark',root/'manufacturing-analytic-benchmark/native-verified.json'])
    print('Actual-field balance and native analytical verification complete')

if __name__=='__main__':main()
