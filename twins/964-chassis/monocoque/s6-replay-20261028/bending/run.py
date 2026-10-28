import hashlib,json,os,sys
from pathlib import Path
import numpy as np
root=Path.cwd(); source=root/'twins/964-chassis/monocoque/source'; out=root/'work/964-s6-bending-replay-001'
sys.path.insert(0,str(source))
import shell_s6 as s6
import torsion_monocoque as tm
import bending as bd
import build_shell as bs
os.environ['PATH']=str(out/'bin')+os.pathsep+os.environ['PATH'];os.environ['OMP_NUM_THREADS']='1'
rep=json.loads(tm.REPORT.read_text()); profiles=json.loads(bs.PROFILES.read_text())
with s6.installed():
 s,p,tri,points,triangles,kind,bands=bd.model(420,1.0,rep,profiles)
 case=bd.load_case(s,p,tri,rep,profiles)
fixed,at,force,mid,skin,line=case
assert len(at)==573 and len(fixed[0][0])==106 and abs(force.sum()+2000)<1e-9
prior=np.load(root/'work/964-s6-fine-replay-001/model.npz',allow_pickle=False)
assert np.array_equal(points,prior['points']) and np.array_equal(triangles,prior['triangles'])
secs,mass=tm.cases(kind,tm.areas(points,triangles))['monocoque, CFRP layup']
np.savez_compressed(out/'model.npz',points=points,triangles=triangles,kind=kind,load_nodes=at,forces_N=force,skin=skin,sill_line=line,mid=mid)
r={'scope':'Finest S6 assumed-carbon bending replay, original 2000 N load case','nodes':len(points),'triangles':len(triangles),'mass_kg_assumed':mass,'force_N':bd.FORCE_N,'load_nodes':len(at),'support_nodes':len(fixed[0][0]),'physical_validation':False,'manufacturing_authorized':False,'solver_threads':1,'memory_limit_gib':12,'runs':[],'sources_sha256':{str(q.relative_to(root)):hashlib.sha256(q.read_bytes()).hexdigest() for q in [source/'shell_s6.py',source/'torsion_monocoque.py',source/'bending.py',source/'build_shell.py',tm.REPORT,bs.PROFILES,out/'run.py',out/'bin/ccx']}}
(out/'prepared.json').write_text(json.dumps(r,indent=2)+'\n'); print(json.dumps({'nodes':len(points),'triangles':len(triangles),'load_nodes':len(at)}),flush=True)
for i in (1,2):
 target=out/f'run-{i}';u,vm=s6.run(points,triangles,secs,fixed,[(at,3,force)],output_dir=target)
 assert np.isfinite(u).all() and np.isfinite(vm).all()
 delta=-float((u[at,2]*force).sum()/force.sum())
 w0,wm,w1=bd.sag(skin,u,line,(bd.ms.CABIN_D[0],mid,bd.ms.CABIN_D[1]))
 chord=w0+(w1-w0)*(mid-bd.ms.CABIN_D[0])/(bd.ms.CABIN_D[1]-bd.ms.CABIN_D[0])
 k=bd.FORCE_N/delta; cabin=bd.FORCE_N/-(wm-chord)
 assert k>0 and cabin>0
 np.savez_compressed(target/'parsed.npz',u=u,vm_output_2d=vm)
 row={'repeat':i,'K_N_per_mm':float(k),'K_cabin_N_per_mm':float(cabin),'max_displacement_mm':float(np.linalg.norm(u,axis=1).max()),'fixed_displacement_max_mm':max(float(np.abs(u[ids,a-1:b]).max()) for ids,a,b in fixed),'files_sha256':{q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in target.iterdir() if q.is_file()}}
 r['runs'].append(row);(out/f'result-after-{i}.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(row),flush=True)
