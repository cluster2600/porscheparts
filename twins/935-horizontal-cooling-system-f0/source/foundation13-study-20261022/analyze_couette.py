"""Compare every Couette cell and native force history to the analytic solution."""
import hashlib,json,re,sys
from pathlib import Path
import numpy as np
from run_reconstruction import ROOT,fresh
import prepare_couette as physics
sys.path.insert(0,str(ROOT/'outils/benchmarks/openfoam-poiseuille-f25'))
from analyze_results import read_vector_field,latest_time_dir,read_check_mesh
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def force_history(path):
 text=Path(path).read_text()
 if not re.search(r'#\s*Time\s+forces\(pressure viscous\)\s+moments\(pressure viscous\)',text):raise ValueError('Foundation 13 non-porous force/moment header required')
 rows=[]
 for line in text.splitlines():
  if not line.strip() or line.lstrip().startswith('#'):continue
  values=list(map(float,line.replace('(',' ').replace(')',' ').split()))
  if len(values)!=13 or not np.isfinite(values).all():raise ValueError('Complete finite force and moment record required')
  rows.append(values)
 result=np.array(rows)
 if len(result)<6 or not np.all(np.diff(result[:,0])>0):raise ValueError('Unique increasing force history required')
 return result

def analyze(base,output):
 base=Path(base);contract=json.loads((base/'contract.json').read_text());report={'cases':{},'source_sha256':sha(__file__),'physics_source_sha256':sha(physics.__file__),'rotor_935_CFD_accepted':False,'manufacturing_authorized':False};rejected=[]
 for name in contract['mesh_levels']:
  p=base/name;proof=json.loads((p/'input-receipt.json').read_text());job=json.loads((p/'execution.json').read_text());assert job['exit']==0 and job['stop_reason'] is None and job['input_files_unchanged'];assert all(sha(p/f)==value for f,value in proof['prepared_input_sha256'].items())
  mesh=read_check_mesh(p,proof['cells']);assert proof['source_sha256']==sha(physics.__file__) and job['input_receipt_sha256']==sha(p/'input-receipt.json')
  latest=latest_time_dir(p);u=np.array(read_vector_field(latest/'U',proof['cells']));c=np.array(read_vector_field(latest/'C',proof['cells']));exact=np.array([physics.velocity(x,y) for x,y,_ in c]);assert u.shape==exact.shape==(proof['cells'],3) and np.isfinite(u).all() and np.isfinite(c).all() and np.isfinite(exact).all() and np.linalg.norm(exact)>0
  history=force_history(p/'postProcessing/rotorForces/0/forces.dat');reference=physics.torque();torque=history[-1,9]+history[-1,12];steady=float(np.ptp(history[-5:,9]+history[-5:,12])/abs(reference));difference=np.linalg.norm(u-exact,axis=1)
  row={'cells':proof['cells'],'latest_time':latest.name,'sampled_velocity_relative_L2':float(np.linalg.norm(u-exact)/np.linalg.norm(exact)),'velocity_relative_Linf_to_inner_wall_speed':float(difference.max()/(physics.OMEGA*physics.RI)),'maximum_axial_velocity_m_s':float(abs(u[:,2]).max()),'analytic_torque_Nm':reference,'reported_torque_Nm':float(torque),'torque_relative_error':float(abs(torque/reference-1)),'last_five_torque_relative_range':steady,'pressure_torque_Nm':float(history[-1,9]),'execution_sha256':sha(p/'execution.json'),'force_history_sha256':sha(p/'postProcessing/rotorForces/0/forces.dat'),'complete_cell_coverage':True}
  if torque*reference<=0 or steady>contract['torque_steady_relative_change_limit']:rejected.append(name+'_torque_sign_or_stationarity')
  report['cases'][name]=row
 fine=report['cases']['fine'];medium=report['cases']['medium'];change=abs(fine['reported_torque_Nm']/medium['reported_torque_Nm']-1);report['fine_to_medium_torque_relative_change']=change
 for key,limit in [('sampled_velocity_relative_L2','fine_velocity_relative_L2_limit'),('velocity_relative_Linf_to_inner_wall_speed','fine_velocity_relative_Linf_limit'),('torque_relative_error','fine_torque_relative_error_limit')]:
  if fine[key]>=contract[limit]:rejected.append(key)
 if change>=contract['fine_to_medium_torque_relative_difference_limit']:rejected.append('torque_grid_change')
 report.update(status='MRF_Couette_control_passed' if not rejected else 'qualification_refused',rejected=rejected,contract_sha256=sha(base/'contract.json'))
 out=fresh(output)/'qualification.json'
 with out.open('x') as s:s.write(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report),flush=True);return not rejected
if __name__=='__main__':raise SystemExit(0 if analyze(sys.argv[1],sys.argv[2]) else 2)
