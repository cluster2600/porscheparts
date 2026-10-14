#!/usr/bin/env python3
"""Audit completed native MPI histories without weakening the frozen serial auditor."""
import json
from pathlib import Path
import re
import sys

from audit_diagnostic import history_metrics, wall_snapshot
from audit_case import table
from prepare_case import sha
from run_cartesian_pilot import verify


def require_completed(case):
    receipt=json.loads((case/'native-exit.json').read_text())
    log=(case/'log.transient-rhoPimpleFoam').read_text()
    reconstruction=(case/'log.reconstructPar').read_text()
    if (receipt.get('exit_code') != 0 or (case/'rejection-reason.txt').exists()
        or not re.search(r'\nEnd\s+Finalising parallel run\s*$',log)
        or 'FOAM FATAL' in log or 'Foam::sigFpe' in log
        or not reconstruction.rstrip().endswith('End') or 'FOAM FATAL' in reconstruction):
        raise ValueError('Successful native MPI solve and reconstruction required')


def audit(case):
    inputs=verify(case)
    require_completed(case)
    manifest=json.loads((case/'case-manifest.json').read_text())
    assert manifest['parallel_execution']['ranks']==4
    for name in ('native-exit.json','log.transient-rhoPimpleFoam','log.reconstructPar','launch-parallel.json'):
        inputs[name]=sha(case/name)
    series={}
    for key,name,width in [('inlet','mass_inlet/0/surfaceFieldValue.dat',2),('outlet','mass_outlet/0/surfaceFieldValue.dat',2),
                          ('energy_inlet','energy_inlet/0/surfaceFieldValue.dat',3),('energy_outlet','energy_outlet/0/surfaceFieldValue.dat',3),
                          ('moment','rotorForces/0/moment.dat',10),('minima','scalarMinima/0/volFieldValue.dat',3)]:
        path=case/'postProcessing'/name
        inputs[str(path.relative_to(case))]=sha(path)
        series[key]=table(path,width)
    physical=manifest.get('active_solve',{}).get('time_semantics') != 'local_pseudo_time_iterations_not_seconds'
    import math
    report=history_metrics(series,manifest['rpm']*manifest['rotation_sign']*math.pi/30,physical)
    checkpoint=max((p.name for p in case.iterdir() if p.is_dir() and re.fullmatch(r'[0-9.eE+-]+',p.name)),key=float)
    assert float(checkpoint)>0
    report['physical_wall_flux_at_last_saved_checkpoint']=wall_snapshot(case,checkpoint,inputs)
    if any(sha(case/name)!=digest for name,digest in inputs.items()):
        raise ValueError('Evidence changed during audit')
    report.update(source_sha256=sha(Path(__file__)),input_sha256=inputs,status='diagnostic_only_not_performance_qualification',
                  performance_ranking_authorized=False,canonical_mesh_gate_passed=False,engineering_validated=False)
    return report


if __name__=='__main__':
    report=audit(Path(sys.argv[1]))
    with Path(sys.argv[2]).open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k:report[k] for k in ('status','samples','checks')}))
