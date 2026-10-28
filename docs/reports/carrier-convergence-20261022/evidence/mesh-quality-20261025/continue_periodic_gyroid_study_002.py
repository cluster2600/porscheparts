from pathlib import Path
import json,subprocess,sys,time
import numpy as np
W=Path(__file__).resolve().parent;P=W/'periodic-gyroid-study-002';contract=json.loads((P/'contract.json').read_text());rows=[]
try:
 for n in [16,24,32,48,64]:
  reports=[]
  for floor,label in [(.0001,'1e-4'),(.000001,'1e-6')]:
   name='n'+str(n)+'-floor'+label;out=(W/'periodic-gyroid-study-001' if n<=32 else P)/name;params=P/(name+'-parameters.json')
   if not out.exists():
    params.write_text(json.dumps(dict(resolution=n,void_relative_stiffness=floor,threshold=contract['threshold']),indent=2)+'\n')
    with(P/(name+'-driver.log')).open('w')as log:subprocess.run([sys.executable,str(W/'run_periodic_gyroid_case_002.py'),str(params),str(out)],stdout=log,stderr=subprocess.STDOUT,check=True)
   report=json.loads((out/'assessment.json').read_text());assert report['status']=='periodic_gyroid_six_strain_energy_checks_passed';reports.append(report)
  left,right=[np.array(x['effective_C_MPa'])for x in reports];contrast=float(np.linalg.norm(left-right)/np.linalg.norm(right));row=dict(resolution=n,solid_fraction=reports[1]['solid_fraction'],minimum_tensor_stiffness_ratio=reports[1]['minimum_tensor_stiffness_ratio'],relative_void_floor_tensor_change=contrast,void_floor_test_passed=contrast<=.01)
  if rows:
   previous_root=W/'periodic-gyroid-study-001' if rows[-1]['resolution']<=32 else P;old=np.array(json.loads((previous_root/('n'+str(rows[-1]['resolution'])+'-floor1e-6/assessment.json')).read_text())['effective_C_MPa']);row['relative_tensor_resolution_change']=float(np.linalg.norm(old-right)/np.linalg.norm(right));row['resolution_change_passed']=row['relative_tensor_resolution_change']<=.02
  rows.append(row);(P/'comparison-progress.json').write_text(json.dumps(rows,indent=2)+'\n');print(row,flush=True)
  if len(rows)>=3 and all(x.get('resolution_change_passed')and x['void_floor_test_passed']for x in rows[-2:]):break
 converged=len(rows)>=3 and all(x.get('resolution_change_passed')and x['void_floor_test_passed']for x in rows[-2:]);(P/'terminal.json').write_text(json.dumps(dict(status='periodic_gyroid_refinement_study_completed',unitcell_stiffness_converged=converged,comparisons=rows,carrier_convergence_demonstrated=False,cellular_part_generated=False),indent=2)+'\n')
except Exception as error:
 (P/'refusal.json').write_text(json.dumps(dict(error=type(error).__name__,detail=str(error),completed_comparisons=rows,unitcell_stiffness_converged=False,epoch=time.time()),indent=2)+'\n');raise
