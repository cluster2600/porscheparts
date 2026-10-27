from pathlib import Path
import hashlib,json,os,subprocess,sys,time
import numpy as np
P=Path(__file__).resolve().parent;S=P.parents[2]/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022';sys.path.insert(0,str(S));from run_local_ccx_serial import stop_and_reap
python=P/'venv/bin/python';driver=P/'run_fft_cell_002.py';D=P/'study-002';assert not D.exists();D.mkdir();sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();contract=dict(grids=[17,25,33,49,65,97,129],void_floors=[.0001,.000001],maximum_relative_tensor_change=.02,maximum_relative_void_floor_change=.01,required_successive_comparisons=2,per_case_wall_seconds=600,per_case_sampled_RSS_GiB=16,controls=['solid_n5','laminate_n5'],source_sha256={str(x):sha(x)for x in [driver,Path(__file__),S/'run_local_ccx_serial.py',P/'source-compatibility-fix-001.json']},carrier_geometry_changed=False);(D/'contract.json').write_text(json.dumps(contract,indent=2));env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1');rows=[]
def run(name,N,kind,floor):
 cfg=D/(name+'-parameters.json');cfg.write_text(json.dumps(dict(resolution=N,kind=kind,void_relative_stiffness=floor)));out=D/name;started=time.monotonic();reason=None;peak=0
 with(D/(name+'.log')).open('w')as log:
  child=subprocess.Popen([str(python),str(driver),str(cfg),str(out)],stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  try:
   while child.poll()is None:
    r=subprocess.run(['ps','-o','rss=','-p',str(child.pid)],capture_output=True,text=True);rss=int(r.stdout.strip()or'0')*1024;peak=max(peak,rss)
    if rss>16*1024**3:reason='sampled_RSS_limit';break
    if time.monotonic()-started>600:reason='wall_limit';break
    time.sleep(.5)
  finally:stop_and_reap(child)
 code=child.returncode if reason is None else 124;receipt=dict(actual_returncode=code,termination_reason=reason,process_reaped=child.returncode is not None,maximum_sampled_RSS_bytes=peak,elapsed_seconds=time.monotonic()-started,script_sha256=sha(driver),parameters_sha256=sha(cfg));(D/(name+'-terminal.json')).write_text(json.dumps(receipt,indent=2));assert code==0,receipt;r=json.loads((out/'assessment.json').read_text());assert r['status']=='six_strain_FFT_cell_controls_and_energy_passed';return r
try:
 assert json.loads((P/'install-terminal-004.json').read_text())['status']=='installed_unqualified'
 for kind in ['solid','laminate']:
  r=run(kind+'-n5',5,kind,.01);assert r['relative_control_tensor_error']<=1e-5
 (D/'analytic-controls-passed.json').write_text(json.dumps(dict(status='FFT_solid_and_laminate_analytic_controls_passed',source_sha256={str(D/(k+'-n5/assessment.json')):sha(D/(k+'-n5/assessment.json'))for k in ['solid','laminate']}),indent=2));last=None
 for N in contract['grids']:
  reports=[run('gyroid-n'+str(N)+'-floor'+str(f),N,'gyroid',f)for f in contract['void_floors']];C=np.array(reports[1]['effective_C_MPa']);contrast=float(np.linalg.norm(np.array(reports[0]['effective_C_MPa'])-C)/np.linalg.norm(C));row=dict(resolution=N,solid_fraction=reports[1]['solid_fraction'],minimum_tensor_stiffness_ratio=reports[1]['minimum_tensor_stiffness_ratio'],relative_void_floor_change=contrast,void_floor_passed=contrast<=.01)
  if last is not None:row.update(relative_tensor_change=float(np.linalg.norm(C-last)/np.linalg.norm(C)));row['spatial_change_passed']=row['relative_tensor_change']<=.02
  rows.append(row);last=C;(D/'comparison-progress.json').write_text(json.dumps(rows,indent=2));print(row,flush=True)
  if len(rows)>=3 and all(x.get('spatial_change_passed')and x['void_floor_passed']for x in rows[-2:]):break
 converged=len(rows)>=3 and all(x.get('spatial_change_passed')and x['void_floor_passed']for x in rows[-2:]);(D/'terminal.json').write_text(json.dumps(dict(status='FFT_periodic_cell_refinement_completed',unitcell_stiffness_converged=converged,comparisons=rows,carrier_convergence_demonstrated=False,cellular_part_generated=False),indent=2))
except BaseException as e:(D/'refusal.json').write_text(json.dumps(dict(error=type(e).__name__,detail=str(e),comparisons=rows,unitcell_stiffness_converged=False),indent=2));raise
