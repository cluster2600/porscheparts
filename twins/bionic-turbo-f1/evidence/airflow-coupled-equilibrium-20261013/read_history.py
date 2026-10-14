"""Separate complete steps and the interrupted step in budget-limited logs."""
import json,re,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'twins/bionic-turbo-f1/cfd')
from prepare_case import sha
w=Path(__file__).parent;c=Path('work/bionic-airflow-20261012/coupled-equilibrium-084');r=json.loads((c/'report.json').read_text());assert r['native_exit_code']==124 and not r['native_end'];assert all(sha(c/n)==h for n,h in r['output_sha256'].items())
log=(c/'log.rhoPimpleFoam').read_text();chunks=re.split(r'^Time = ([^\n]+)\n',log,flags=re.M);steps=[]
for time,body in zip(chunks[1::2],chunks[2::2]):
 pressure=re.findall(r'^GAMG:  Solving for p, Initial residual = ([^,]+), Final residual = ([^,]+), No Iterations (\d+)',body,re.M)
 steps.append(dict(time_s=float(time),pressure_solves=len(pressure),pressure_iterations=[int(t[2]) for t in pressure],complete_extrema=('max(region0) of UMagSqr' in body and 'min(region0) of UMagSqr' in body)))
assert len(steps)==112 and all(s['pressure_solves']==4 and s['complete_extrema'] for s in steps[:-1]);assert steps[-1]['pressure_solves']==2 and not steps[-1]['complete_extrema'];assert all(all(i==1000 for i in s['pressure_iterations']) for s in steps)
times=np.array([s['time_s'] for s in steps]);assert np.allclose(times,np.arange(1,113)*1e-7,rtol=0,atol=1e-18)
for name in ('minima','maxima'):
 data=np.loadtxt(c/f'postProcessing/{name}/0/volFieldValue.dat');assert len(data)==111 and np.array_equal(data[:,0],times[:-1])
control=(c/'system/controlDict').read_text();assert re.search(r'writeInterval\s+200\s*;',control) and re.search(r'writePrecision\s+16\s*;',control)
result=dict(reader_sha256=sha(Path(__file__)),all_payloads_verified=True,complete_steps=111,complete_interval_s=1.11e-5,interrupted_step=steps[-1],complete_step_pressure_solves=444,interrupted_step_pressure_solves=2,all_446_completed_pressure_solves_reach_1000_iterations=True,write_interval_steps=200,final_fields_absent=True,scope='No completed 20us rest qualification; interruption by fixed wall-clock budget, not evidence of physical instability.',steps=steps)
with (w/'history-readback.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='steps'}))
