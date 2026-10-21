"""Compare the actual CCX control against its fixed analytic tolerances."""
import argparse
import ast
import hashlib
import json
from pathlib import Path


def main():
 p=argparse.ArgumentParser(__doc__);p.add_argument('--dat',type=Path,required=True);p.add_argument('--analytic',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Fresh output required')
 a.output.mkdir(parents=True)
 import numpy as np
 helper=Path(__file__).resolve().parents[5]/'parts/993-eng-carrier-0001/source/bionic-20261011/simulate.py';text=helper.read_text();node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name=='parse_dat');namespace={'np':np};exec(compile(ast.get_source_segment(text,node),str(helper),'exec'),namespace)
 values=namespace['parse_dat'](a.dat);control=json.loads(a.analytic.read_text())
 if values['displacements'].shape!=(8,4)or values['stresses'].shape!=(6,8):raise ValueError('Analytic full result roster differs')
 uerror=float(abs(values['displacements'][:,1:]-np.array(control['expected_displacements'])).max());serror=float(abs(values['stresses'][:,2:]-np.array(control['expected_stress_MPa'])).max())
 passed=uerror<=control['absolute_displacement_tolerance_mm']and serror<=control['absolute_stress_tolerance_MPa']
 report=dict(status='analytic_control_passed'if passed else'analytic_control_refused',maximum_displacement_error_mm=uerror,maximum_stress_error_MPa=serror,displacement_limit_mm=control['absolute_displacement_tolerance_mm'],stress_limit_MPa=control['absolute_stress_tolerance_MPa'],source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.dat,a.analytic,helper,Path(__file__)]})
 (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
