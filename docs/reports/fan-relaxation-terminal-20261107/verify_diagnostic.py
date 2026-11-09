"""Audit the terminated attempt without shortening its required windows."""
from pathlib import Path
import runpy,json,statistics,math,hashlib
r=Path(__file__).parent
receipt=json.loads((r/'collection.json').read_text())
for row in receipt['files']:
 path=r/row['path']
 if path.is_file():
  data=path.read_bytes()
  assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
source=r.parents[2]/'twins/993-engine-cooling-fan-system-f0/source/summarize_fan_cfd.py'
h=runpy.run_path(str(source));hist=[]
for name in ['inletFlow','outletFlow']:
 hist.append(h['table']((r/f'postProcessing/{name}/2000/surfaceFieldValue.dat').read_text(),['Time','sum(phi)']))
assert all(rows[0][0]==2000 for rows in hist)
initial_state_rows=[rows[0] for rows in hist]
a,b=[rows[1:] for rows in hist];assert [x[0] for x in a]==[x[0] for x in b]==list(range(2001,2164))
try:h['diagnostics'](a,b)
except ValueError as error:
 assert str(error)=='Two matching complete convergence windows required';rejection=str(error)
else:raise AssertionError('incomplete history was accepted')
forces=[list(map(float,line.replace('(',' ').replace(')',' ').split())) for line in (r/'postProcessing/rotorForces/2000/forces.dat').read_text().splitlines() if line.strip() and not line.startswith('#')]
assert all(len(x)==13 and all(math.isfinite(v) for v in x) for x in forces)
assert forces[0][0]==2000
forces=forces[1:]
assert [x[0] for x in forces]==[x[0] for x in a]
recent=[x[1] for x in b[-100:]];moments=[x[9]+x[12] for x in forces[-100:]];mean=statistics.fmean(recent);torque=statistics.fmean(moments)
result={'initial_state_2000_excluded':True,'status':'terminated_unconverged','exit_code':124,'complete_iterations':[2001,2163],'complete_samples':len(a),'required_samples':200,'strict_two_window_rejection':rejection,'last_100_iteration_range':[2064,2163],'mean_outlet_m3_s':mean,'relative_flow_peak_to_peak':(max(recent)-min(recent))/mean,'maximum_relative_mass_imbalance':max(abs(x[1]+y[1])/max(abs(x[1]),abs(y[1])) for x,y in zip(a[-100:],b[-100:])),'mean_fluid_torque_Nm':torque,'relative_torque_peak_to_peak':(max(moments)-min(moments))/abs(torque),'between_window_drift':None,'two_window_acceptance_available':False,'convergence_accepted':False,'diagnostic_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
result.update(h['residual_diagnostics']((r/'log.foamRun').read_text(),2163))
assert not result['nonlinear_residual_checks_passed']
assert result==json.loads((r/'diagnostic.json').read_text())
print(json.dumps(result))
