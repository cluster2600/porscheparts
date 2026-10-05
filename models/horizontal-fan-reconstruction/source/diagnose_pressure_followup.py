#!/usr/bin/env python3
"""Diagnose existing steady iteration histories; never infer physical frequency."""
import argparse,hashlib,json,re,sys
from pathlib import Path
import numpy as np


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('inputs',type=Path);ap.add_argument('output',type=Path);ap.add_argument('--source-directory',type=Path,required=True);a=ap.parse_args();sys.path.insert(0,str(a.source_directory))
 from diagnose_and_merge_fv_cells import read
 from analyze_flow_balance import field_values
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 declared=json.loads((a.inputs/'input-manifest.json').read_text())['members']
 for name,record in declared.items():
  p=a.inputs/name
  if p.stat().st_size!=record['bytes'] or sha(p)!=record['sha256']:raise ValueError('Native input identity changed '+name)
 histories={}
 for label in ['V2-fine-150steps-phase600','V2-fine-continuation750','V2-fine-pressure015-900','R0-fine-pressure015-750','V2-short-edge-resolution-run2']:
  case=a.inputs/('cfd-'+label);rows=[]
  for block in re.split(r'(?m)^Time = ',(case/'log.foamRun').read_text())[1:]:
   time=float(re.match(r'([\d.eE+-]+)',block)[1]);solves=re.findall(r'Solving for p, Initial residual = ([\d.eE+-]+), Final residual = ([\d.eE+-]+), No Iterations (\d+)',block)
   if len(solves)!=3:raise ValueError('Three pressure corrections required')
   continuity=re.search(r'time step continuity errors : sum local = ([\d.eE+-]+), global = ([\d.eE+-]+)',block)
   rows.append([time,max(float(v[0]) for v in solves),max(float(v[1]) for v in solves),max(int(v[2]) for v in solves),float(continuity[1]),float(continuity[2])])
  rows=np.array(rows)
  def table(name):
   candidates=[]
   for p in (case/'postProcessing'/name).iterdir():
    f=p/('forces.dat' if name=='rotorForces' else 'surfaceFieldValue.dat')
    values=np.array([list(map(float,re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?',l))) for l in f.read_text().splitlines() if l.strip() and not l.startswith('#')])
    if values.size:
     values=values[(values[:,0]>=rows[0,0])&(values[:,0]<=rows[-1,0])]
     if len(values):candidates.append(values)
   values=max(candidates,key=len)
   if not np.array_equal(values[-100:,0],rows[-100:,0]):return None
   return values
  qtable=table('outletFlow');ttable=table('rotorForces');n=100;r=rows[-n:];q=None if qtable is None else qtable[-n:,1];torque=None if ttable is None else ttable[-n:,9]+ttable[-n:,12];d=r[:,1]-r[:,1].mean();ft=np.abs(np.fft.rfft(d));ft[0]=0;index=int(ft.argmax());frequency=np.fft.rfftfreq(len(d))[index]
  corr=lambda x,y:None if x.std()==0 or y.std()==0 else float(np.corrcoef(x,y)[0,1])
  histories[label]={'iterations':len(rows),'first_iteration':rows[0,0],'last_iteration':rows[-1,0],'window_iterations':len(r),'p_initial_residual_max':float(r[:,1].max()),'p_initial_residual_mean':float(r[:,1].mean()),'p_initial_residual_relative_std':float(r[:,1].std()/r[:,1].mean()),'p_final_linear_residual_max':float(r[:,2].max()),'pressure_correctors_each_iteration':3,'linear_pressure_max_iterations':int(r[:,3].max()),'Q_relative_std_last100':None if q is None else float(q.std()/abs(q.mean())),'torque_relative_std_last100':None if torque is None else float(torque.std()/abs(torque.mean())),'native_last100_Q_torque_window_available':q is not None and torque is not None,'correlation_p_initial_with_Q':None if q is None else corr(r[:,1],q),'correlation_p_initial_with_global_continuity':corr(r[:,1],r[:,5]),'largest_iteration_spectral_component_cycles_per_iteration':float(frequency),'spectral_component_is_not_physical_frequency':True,'initial_pressure_residuals_last100':r[:,1].tolist(),'Q_last100':None if q is None else q.tolist(),'iteration_last100':r[:,0].tolist()}
 case=a.inputs/'cfd-V2-fine-pressure015-900';points,faces,owner,neighbor,patches=read(case);nc=int(max(owner.max(),neighbor.max()))+1;ni=len(neighbor);tri=points[faces];fc=tri.mean(axis=1);sf=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])*.5
 centers=np.zeros((nc,3));count=np.zeros(nc);volumes=np.zeros(nc);vf=np.einsum('ij,ij->i',fc,sf)/3
 np.add.at(centers,owner,fc);np.add.at(centers,neighbor,fc[:ni]);np.add.at(count,owner,1);np.add.at(count,neighbor,1);centers/=count[:,None]
 np.add.at(volumes,owner,vf);np.add.at(volumes,neighbor,-vf[:ni]);volumes=np.abs(volumes)
 if not np.all(count==4) or volumes.min()<=0:raise ValueError('Actual tetrahedral control-volume topology/volume')
 pfields={};ufields={}
 for label,end in [('V2-fine-150steps-phase600',600),('V2-fine-continuation750',750),('V2-fine-pressure015-900',900)]:
  root=a.inputs/('cfd-'+label)/str(end);pfields[end]=1.2*field_values((root/'p').read_text(),'internalField',nc,1);ufields[end]=field_values((root/'U').read_text(),'internalField',nc,3)
 deltas={}
 for old,new in [(600,750),(750,900)]:
  dp=pfields[new]-pfields[old];du=np.linalg.norm(ufields[new]-ufields[old],axis=1);indices=np.argsort(np.abs(dp))[-10:][::-1];rms=float(np.sqrt(np.dot(volumes,dp*dp)/volumes.sum()));rows=[]
  for index in indices:
   closest={p['name']:float(np.linalg.norm(fc[p['startFace']:p['startFace']+p['nFaces']]-centers[index],axis=1).min()*1000) for p in patches}
   rows.append({'cell':int(index),'center_mm':(centers[index]*1000).tolist(),'radius_mm':float(np.linalg.norm(centers[index,:2])*1000),'pressure_change_Pa':float(dp[index]),'cell_volume_mm3':float(volumes[index]*1e9),'nearest_boundary_face_centroid_distance_mm_proxy':closest})
  scale=float(pfields[new].max()-pfields[new].min())
  deltas[str(old)+'_to_'+str(new)]={'pressure_delta_volume_RMS_Pa':rms,'pressure_delta_RMS_over_pressure_range':rms/scale,'maximum_pressure_change_Pa':float(np.abs(dp).max()),'pressure_delta_absolute_cell_count_weighted_p99_Pa':float(np.quantile(np.abs(dp),.99)),'volume_fraction_abs_pressure_delta_above_1Pa':float(volumes[np.abs(dp)>1].sum()/volumes.sum()),'velocity_delta_volume_RMS_m_s':float(np.sqrt(np.dot(volumes,du*du)/volumes.sum())),'maximum_velocity_change_m_s':float(du.max()),'largest_pressure_change_cells':rows,'pressure_change_is_not_algebraic_cell_residual':True,'same_mesh_cells':nc}
 log=(a.inputs/'cfd-V2-common-h5p6-repair1/log.checkMesh').read_text();quality=[l.strip() for l in log.splitlines() if any(x in l for x in ['determinant','non-orthogonality','Max skewness','Mesh OK','interpolation weights'])]
 result={'status':'diagnostic_of_existing_native_steady_outputs_only','sources_match_verified_archive':True,'script_sha256':sha(Path(__file__)),'dependency_sha256':{name:sha(a.source_directory/name) for name in ['diagnose_and_merge_fv_cells.py','analyze_flow_balance.py']},'input_manifest_sha256':sha(a.inputs/'input-manifest.json'),'histories':histories,'matched_checkpoint_changes':deltas,'independent_mesh_quality_lines':quality,'physical_oscillation_demonstrated':False,'new_solver_run':False,'limits':['Iteration labels in a steady solver are not physical time; spectral components cannot be interpreted as rotor frequencies.','Original fine postProcessing tables contain only two snapshots because continuation helpers changed measurement writeInterval from 1 to 150. All original hashes are preserved. Historical Q/torque statistics are not 20-iteration means and fine admission is withdrawn.','Only three saved field checkpoints; cannot resolve intra-iteration pressure oscillation or identify actual algebraic residual cells without matrices/residual fields.','Changing pressure relaxation changes nonlinear update and normalization history; the original frozen admission criteria remain unchanged.'],'next_discriminating_test':'One matched-checkpoint short V2 pressure-linear-solve sensitivity at relTol=0, unchanged physical fields/discretization/acceptance criteria; log pressure residual field or matrix normalization if available. No blind continuation.'}
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k in ['status','matched_checkpoint_changes','independent_mesh_quality_lines']}))

if __name__=='__main__':main()
