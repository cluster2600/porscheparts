from fair import fair
import numpy as np,json
from pathlib import Path
from fractions import Fraction as Q
n=15;v=np.array([[i/128,j/128,0]for i in range(n)for j in range(n)],float);f=[]
for i in range(n-1):
 for j in range(n-1):
  a=i*n+j;f.extend([[a,a+n,a+n+1],[a,a+n+1,a+1]])
f=np.array(f,np.uint64);seed=7*n+7;p,info=fair(v,f,[seed]);assert np.array_equal(p,v)
v[seed,2]=.02;p,info=fair(v,f,[seed]);changed=np.flatnonzero(np.any(p!=v,axis=1));assert len(changed)>1 and p[seed,2]<v[seed,2]
for i in changed:assert sum(abs(Q(float(p[i,k]))-Q(float(v[i,k])))for k in range(3))<Q(.005)
assert np.array_equal(p[:n],v[:n]);assert np.array_equal(p[-n:],v[-n:])
(Path(__file__).resolve().parent/'controls.json').write_text(json.dumps(dict(status='fixed_local_fairing_controls_passed',plane_preserved=True,bump_reduced=True,exact_changed_vertex_budget_passed=True,frozen_boundary_preserved=True),indent=2)+'\n');print('PASS')
