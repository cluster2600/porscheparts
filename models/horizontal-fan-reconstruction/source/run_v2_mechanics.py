#!/usr/bin/env python3
"""Sequential V2 rotation/modal study under the original R0/V5 assumptions."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from run_existing_grid_sensitivity import IMAGE


def main():
    root=Path.cwd()
    if subprocess.check_output(['docker','ps','--filter','ancestor='+IMAGE,'--format','{{.ID}}'],text=True).strip():raise ValueError('Existing flow job must finish first')
    def bounded(label,command,directory=None,threads=4,seconds=600):
        args=[sys.executable,'run_bounded_task.py','--label',label,'--threads',str(threads),'--memory-gib','5','--timeout',str(seconds)]
        if directory:args+=['--directory',str(directory)]
        subprocess.run(args+['--',*map(str,command)],check=True)
    for size,label in [(4.5,'h4p5'),(3.6,'h3p6')]:
        case=root/('mesh-V2-'+label)
        bounded('V2-'+label+'-mesh',[sys.executable,'build_analytical_mesh_original.py',root/'private-V2',case,'--mode','structural','--size-mm',size,'--rpm','6000'],threads=1,seconds=300)
        mesh=json.loads((case/'mesh-report.json').read_text())
        if mesh['minimum_Gauss4_jacobian']<=0 or mesh['relative_volume_error']>.02 or mesh['source_step_sha256']!=hashlib.sha256((root/'private-V2/rotor.step').read_bytes()).hexdigest():raise ValueError('Structural mesh positivity/volume/STEP identity failed')
        for job in ['rotation','modal']:
            bounded(job,['ccx','-i',job],directory=case)
        bounded('V2-'+label+'-summary',[sys.executable,'summarize_analytical_fem.py',case,case/'summary.json'],threads=1,seconds=90)
    print('V2 two-grid centrifugal and unprestressed modal calculations completed; no service qualification')

if __name__=='__main__':main()
