"""Bound star-kernel proposals; the analytic interior-star control must improve."""
import hashlib,json,os,resource,shutil,signal,subprocess,sys,time
from pathlib import Path
import numpy as np
b=Path(__file__).resolve().parent;root=b.parents[1];sys.path.insert(0,str(root/'twins/935-horizontal-cooling-system-f0/source'));from import_conforming_volume import exact_orientation
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
out=b/'kernel-001';out.mkdir();shutil.copyfile(root/'twins/935-horizontal-cooling-system-f0/source/optimize_interior_stars.py',out/'worker.py')
v=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1],[1e-7,.1,.1]]);f=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]]);c=np.column_stack([np.full(4,4),f]);np.savez_compressed(out/'control-input.npz',vertices=v,tetrahedra=c,boundary=f)
assert exact_orientation(v,c)['signed_volume_exact']=='1/6'
env=os.environ.copy();env['PYTHONPATH']=str(root/'twins/935-horizontal-cooling-system-f0/source')
def minimum_quality(v,c):
 t=v[c];det=np.linalg.det(np.swapaxes(t[:,1:]-t[:,0,None],1,2));assert (det>0).all();edges=sum(((t[:,i]-t[:,j])**2).sum(axis=1) for i,j in [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]);return float((12*(det/2)**(2/3)/edges).min())
for name in ['control','rotor']:
 folder=out/name;folder.mkdir();inp=out/'control-input.npz' if name=='control' else root/'work/935-analysis-patches-20261022/volume-151/volume.npz'
 if name=='rotor':assert sha(inp)=='68f5e6a4b1dcf188b8d536195821ce3c3475074d9ba95286f94022299442241a'
 shutil.copyfile(inp,folder/'input.npz');command=[sys.executable,str(out/'worker.py'),str(folder)];start=time.monotonic();peak=0;reason=None
 with (folder/'runtime.log').open('x') as log:
  p=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
  while p.poll() is None:
   s=subprocess.run(['/bin/ps','-o','rss=','-p',str(p.pid)],capture_output=True,text=True,timeout=5)
   if s.stdout.strip():peak=max(peak,int(s.stdout.strip())*1024)
   if peak>16*1024**3 or time.monotonic()-start>600:
    reason='rss_limit' if peak>16*1024**3 else 'wall_time_limit';os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    break
   time.sleep(.2)
 code=p.wait();r={'command':command,'exit':code,'elapsed_s':time.monotonic()-start,'peak_rss_bytes':peak,'rss_limit_bytes':16*1024**3,'timeout_s':600,'stop_reason':reason,'worker_sha256':sha(out/'worker.py'),'controller_sha256':sha(__file__),'input_sha256':sha(inp),'mechanical_mesh_admitted':False,'manufacturing_authorized':False};(folder/'execution.json').write_text(json.dumps(r,indent=2)+'\n');print(name,json.dumps(r),flush=True);assert code==0 and reason is None
 if name=='control':
  with np.load(folder/'volume.npz',allow_pickle=False) as d:actual=exact_orientation(d['vertices'],d['tetrahedra']);quality=minimum_quality(d['vertices'],d['tetrahedra'])
  before=minimum_quality(v,c);assert not actual['negative'] and not actual['zero'] and actual['signed_volume_exact']=='1/6' and quality>before*1.01
  (folder/'analytic-control.json').write_text(json.dumps({'exact_orientation':actual,'minimum_quality_before':before,'minimum_quality_after':quality,'quality_improved':True},indent=2)+'\n')
