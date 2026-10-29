from optimize import optimize,prepare
import numpy as np,json
from fractions import Fraction as Q
from pathlib import Path
f=np.array([[0,1,2],[1,3,2]],np.uint64)
v=np.array([[-.006,0,.006],[0,-.006,0],[0,.006,0],[.006,0,.006]])
for sign in [1,-1]:
 v[:,2]=sign*np.array([.006,0,0,.006]);test=prepare(v,f,[0,1,2,3],closed=False);angles=np.asarray(test[-2](np.zeros(12))[0])
 if angles.min()<-np.pi/4:break
assert angles.min()<-np.pi/4
new,meta=optimize(v,f,[0,1,2,3],closed=False);assert meta['final_patch_maximum_degrees']<45
for i in range(4):assert sum((Q(float(new[i,k]))-Q(float(v[i,k])))**2 for k in range(3))<Q('0.005')**2
v[:,2]=0;new,flat=optimize(v,f,[0,1,2,3],closed=False);assert np.array_equal(new,v)
(Path(__file__).resolve().parent/'controls.json').write_text(json.dumps(dict(status='signed_dihedral_controls_passed',folded_hinge=meta,flat_plane_invariant=True,exact_euclidean_bound=True),indent=2)+'\n');print('PASS',meta['final_patch_maximum_degrees'])
