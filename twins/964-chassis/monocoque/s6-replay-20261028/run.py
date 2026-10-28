import hashlib,json,os,sys
from pathlib import Path
import numpy as np
root=Path.cwd()
source=root/'twins/964-chassis/monocoque/source'
out=root/'work/964-s6-fine-replay-001'
sys.path.insert(0,str(source))
import shell_s6 as s6
import torsion_monocoque as tm
import torsion as tr
import build_shell as bs
os.environ['PATH']=str(out/'bin')+os.pathsep+os.environ['PATH']
os.environ['OMP_NUM_THREADS']='1'
report=json.loads(tm.REPORT.read_text());profiles=json.loads(bs.PROFILES.read_text())
s,p,tri=s6.load_shell()
rear,fl,fr=tr.supports(s,p)
p,tri,kind,used,folds,n=tm.build(s,p,tri,lambda q,st:tm.picogk_bands(q,st,report,profiles))
sections,mass=tm.cases(kind,tm.areas(p,tri))['monocoque, CFRP layup']
np.savez_compressed(out/'model.npz',points=p,triangles=tri,kind=kind,rear=rear,front_left=fl,front_right=fr)
arm=float(p[fl,1].mean()-p[fr,1].mean())
receipt={'scope':'finest S6 replay with historical assumed material and synthetic patches','nodes':len(p),'triangles':len(tri),'mass_kg_assumed':mass,'arm_mm':arm,'force_each_side_N':tr.FORCE_N,'physical_validation':False,'manufacturing_authorized':False,'runtime_memory_gib':12,'solver_threads':1,'runs':[],'sources_sha256':{str(q.relative_to(root)):hashlib.sha256(q.read_bytes()).hexdigest() for q in [source/'shell_s6.py',source/'torsion_monocoque.py',source/'torsion.py',source/'build_shell.py',tm.REPORT,bs.PROFILES,out/'run.py',out/'bin/ccx']}}
(out/'prepared.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'nodes':len(p),'triangles':len(tri),'mass_kg':mass,'arm_mm':arm}),flush=True)
for index in (1,2):
 run=out/f'run-{index}'
 u,vm=s6.run(p,tri,sections,[(rear,1,6)],[(fl,3,np.full(len(fl),tr.FORCE_N/len(fl))),(fr,3,np.full(len(fr),-tr.FORCE_N/len(fr)))],output_dir=run)
 theta=(u[fl,2].mean()-u[fr,2].mean())/arm
 k=tr.FORCE_N*arm/1000/np.degrees(theta)
 assert np.isfinite(u).all() and np.isfinite(vm).all() and k>0
 np.savez_compressed(run/'parsed.npz',u=u,vm_output_2d=vm)
 row={'repeat':index,'K_Nm_per_deg':float(k),'max_displacement_mm':float(np.linalg.norm(u,axis=1).max()),'fixed_translation_max_mm':float(np.abs(u[rear]).max()),'file_hashes':{q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in run.iterdir() if q.is_file()}}
 receipt['runs'].append(row)
 (out/f'result-after-{index}.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(row),flush=True)
