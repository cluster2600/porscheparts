#!/usr/bin/env python3
"""Verify the independent uniform-strain analytical solution in actual native fields."""
import argparse,hashlib,json,re
from pathlib import Path
import numpy as np
from prepare_engineering_sensitivities import parse_mesh
from summarize_engineering_sensitivities import displacement_blocks,stress_blocks


def verify(case,output):
 log=(case/'log.native-benchmark').read_text()
 if 'Job finished' not in log or '*ERROR' in log:raise ValueError('Benchmark solver did not complete')
 nodes,elements=parse_mesh((case/'unit-eigenstrain.inp').read_text());u=displacement_blocks(case/'unit-eigenstrain.frd');s=stress_blocks(case/'unit-eigenstrain.dat')
 if len(elements)!=1 or len(nodes)!=10 or len(u)!=2 or len(s)!=2 or set(u[-1])!=set(nodes) or len(s[-1])!=4:raise ValueError('Analytical benchmark topology/field count mismatch')
 error=max(float(np.linalg.norm(u[-1][n]+.001*x)) for n,x in nodes.items());stress=max(float(np.abs(v).max()) for v in s[-1].values())
 if error>1e-8 or stress>1e-7:raise ValueError('Analytical benchmark failed')
 result={'status':'passed','solver':'CalculiX','solver_version':re.search(r'Version ([0-9.]+)',log)[1],'analytical_solution':'Released uniform strain -0.001: U=-0.001*x and stress=0','maximum_displacement_error_mm':error,'maximum_released_stress_component_MPa':stress,'displacement_limit_mm':1e-8,'stress_limit_MPa':1e-7,'native_field_coverage_complete':True,'file_sha256':{n:hashlib.sha256((case/n).read_bytes()).hexdigest() for n in ['unit-eigenstrain.inp','unit-eigenstrain.frd','unit-eigenstrain.dat','log.native-benchmark']},'process_calibration_established':False}
 if output.exists():raise FileExistsError('Preserve benchmark evidence')
 output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('case',type=Path);p.add_argument('output',type=Path);a=p.parse_args();verify(a.case,a.output)
