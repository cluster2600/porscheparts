from pathlib import Path
import json,hashlib,math
import numpy as np
import manifold3d as mf
root=Path(__file__).resolve().parent;contract=json.loads((root/'contract.json').read_text());records=[]
def parallel_cube(s,t):return s**3+6*s*s*t+3*math.pi*s*t*t+4*math.pi*t**3/3
for label in ['h0100','h0050','h0025']:
 meta=json.loads((root/label/'runtime.json').read_text());h=float(np.float32(meta['voxel_mm']));r=float(np.float32(meta['radius_mm']));retreat=float(np.float32(meta['retreat_mm']));epsilon=contract['maximum_complete_directed_analytic_sdf_bound_in_voxels']*h
 for name in ['cube','sphere']:
  path=root/label/(name+'.stl');raw=path.read_bytes();n=int(np.frombuffer(raw[80:84],dtype='<u4')[0]);dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')]);assert len(raw)==84+n*50;t=np.frombuffer(raw[84:],dtype=dtype)['vertices'].astype(np.float64);assert np.isfinite(t).all();v,indices=np.unique(t.reshape(-1,3),axis=0,return_inverse=True);f=indices.reshape(-1,3);body=mf.Manifold(mf.Mesh64(v,f.astype(np.uint64)));assert body.status()==mf.Error.NoError and len(body.decompose())==1 and body.volume()>0
  c=t.mean(1);cover=np.linalg.norm(t-c[:,None,:],axis=2).max(1)
  if name=='sphere':
   rad=2-retreat;distance=np.linalg.norm(c,axis=1)-rad;expected=4*math.pi*rad**3/3;lower=4*math.pi*(rad-epsilon)**3/3;upper=4*math.pi*(rad+epsilon)**3/3
  else:
   s=4-2*(r+retreat);q=np.abs(c)-s/2;distance=np.linalg.norm(np.maximum(q,0),axis=1)+np.minimum(q.max(1),0)-r;expected=parallel_cube(s,r);lower=parallel_cube(s,r-epsilon);upper=parallel_cube(s,r+epsilon)
  bound=float((np.abs(distance)+cover).max());volume=body.volume();passed=bound<=epsilon and lower<=volume<=upper
  records.append(dict(case=name,voxel_mm=h,triangles=n,volume_mm3=volume,analytic_volume_mm3=expected,relative_volume_error=abs(volume-expected)/expected,complete_directed_analytic_sdf_bound_mm=bound,fixed_distance_limit_mm=epsilon,analytic_volume_interval_mm3=[lower,upper],passed=passed,input_sha256=hashlib.sha256(raw).hexdigest()))
for name in ['cube','sphere']:
 values=[r['complete_directed_analytic_sdf_bound_mm']for r in records if r['case']==name];assert all(a>b for a,b in zip(values,values[1:]))
passed=all(r['passed']for r in records);out=dict(status='analytical_opening_controls_passed'if passed else'analytical_controls_refused',cases=records,strict_bound_decrease=True,proof='For every triangle x: abs(d(x)) <= abs(d(centroid)) + max_vertex_distance_to_centroid, using the analytic signed-distance 1-Lipschitz property',scope='Complete mesh-to-analytic directed envelope, topology and volume controls; no symmetric carrier fidelity or manufacturing claim',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),manufacturing_authorized=False);path=root/'assessment.json';assert not path.exists();path.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));raise SystemExit(0 if passed else 2)
