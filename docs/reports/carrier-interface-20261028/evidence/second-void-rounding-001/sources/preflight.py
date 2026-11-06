"""Freeze a local edge flip from the measured residual crease."""
from pathlib import Path
import hashlib,json
import numpy as np
r=Path(__file__).resolve().parent
source=r.parent/'carrier-r0-positive-001/decoded-001/candidate.npz'
digest=hashlib.sha256(source.read_bytes()).hexdigest()
assert digest=='0d9ccaf17aa0f7c298aed21794e510075df7133b054e8a59dcd4706280213c8d'
with np.load(source,allow_pickle=False)as z:
 v=z['vertices'];f=z['triangles']
 shared={315577,315175};ids=np.flatnonzero(np.isin(f,list(shared)).sum(1)==2);assert len(ids)==2
 a,b=f[ids].tolist();c=next(x for x in a if x not in shared);d=next(x for x in b if x not in shared)
 u,t=next((a[j],a[(j+1)%3])for j in range(3)if {a[j],a[(j+1)%3]}==shared)
 assert not np.any(np.isin(f,[c,d]).sum(1)==2)
 new=np.array([[c,d,t],[d,c,u]])
 def normals(faces):
  tri=v[faces];return np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
 def turn(faces):
  n=normals(faces);return float(np.degrees(np.arccos(np.clip(np.dot(n[0],n[1])/np.prod(np.linalg.norm(n,axis=1)),-1,1))))
 axis=int(np.argmax(abs(normals(f[ids]).sum(0))))
 plan=dict(parent_sha256=digest,changed_face_ids=ids.tolist(),old_faces=f[ids].tolist(),new_faces=new.tolist(),projected_drop_axis=axis,maximum_bidirectional_edit_mm=.005,observed_old_patch_turn_degrees=turn(f[ids]),observed_new_patch_turn_degrees=turn(new),projection_choice='Drop largest component of summed original patch normals',acceptance='Exact complete projected overlay bound, improved patch turn, full embedding and original-domain containment, full material-side audit')
 assert plan['observed_new_patch_turn_degrees']<plan['observed_old_patch_turn_degrees']
(r/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(plan))
