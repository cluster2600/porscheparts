"""Independently bound an actual two-face flip using exact projected overlay."""
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import numpy as np

r=Path(__file__).resolve().parent
before=r.parent/"carrier-001/decoded-001/candidate.npz"
after=r/"decoded-001/candidate.npz"
old,new=np.load(before),np.load(after)
v,w=old["vertices"],new["vertices"]
f,g=old["triangles"],new["triangles"]
assert np.array_equal(v,w) and np.isfinite(v).all()
changed=np.flatnonzero(np.any(f!=g,axis=1))
assert changed.tolist()==[13146,13147]
a,b=f[changed[0]].tolist(),f[changed[1]].tolist()
shared=set(a)&set(b);assert len(shared)==2
c=next(x for x in a if x not in shared);d=next(x for x in b if x not in shared)
u,t=next((a[j],a[(j+1)%3])for j in range(3)if {a[j],a[(j+1)%3]}==shared)
assert np.array_equal(g[changed],[[c,d,t],[d,c,u]])
assert not np.any(np.isin(f,[c,d]).sum(axis=1)==2)
p={i:[Q(float(x))for x in v[i]]for i in [u,t,c,d]}
axis=1;xy=[0,2]
aa=[p[t][k]-p[u][k]for k in xy];bb=[p[d][k]-p[c][k]for k in xy];rhs=[p[c][k]-p[u][k]for k in xy]
cross=lambda x,y:x[0]*y[1]-x[1]*y[0]
den=cross(aa,bb);assert den!=0
s=cross(rhs,bb)/den;q=cross(rhs,aa)/den
assert 0<s<1 and 0<q<1
pa=[p[u][k]+s*(p[t][k]-p[u][k])for k in range(3)]
pb=[p[c][k]+q*(p[d][k]-p[c][k])for k in range(3)]
assert all(pa[k]==pb[k]for k in xy)
def signed_area(face):
    x,y,z=[p[i]for i in face]
    return cross([y[k]-x[k]for k in xy],[z[k]-x[k]for k in xy])
areas=[signed_area(row.tolist())for row in np.vstack([f[changed],g[changed]])]
assert all(x*areas[0]>0 for x in areas)
def normal(face):
    x,y,z=[p[i]for i in face];a=[b-a for a,b in zip(x,y)];b=[b-a for a,b in zip(x,z)]
    return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
dot=lambda a,b:sum(x*y for x,y in zip(a,b))
on=[normal(row.tolist())for row in f[changed]];nn=[normal(row.tolist())for row in g[changed]]
od,nd=dot(*on),dot(*nn);assert od>0 and nd>0
assert nd*nd*dot(on[0],on[0])*dot(on[1],on[1]) > od*od*dot(nn[0],nn[0])*dot(nn[1],nn[1])
gap=abs(pa[axis]-pb[axis]);limit=Q(1,200);assert gap<=limit
upper=math.nextafter(float(gap),math.inf)
result=dict(status="complete_exact_edge_flip_bound_passed",changed_face_ids=changed.tolist(),vertices_compared=len(v),faces_compared=len(f),all_vertices_identical=True,all_other_faces_identical=True,projected_drop_axis=axis,exact_diagonal_parameters=[str(s),str(q)],exact_gap_mm=str(gap),whole_surface_bidirectional_distance_upper_mm=upper,maximum_mm=.005,patch_normal_turn_improves_exactly=True,proof="Both convex projected quadrilateral triangulations have the same planar domain. Their exact common refinement has zero lift difference at boundary vertices and one interior lift gap at the diagonal intersection; affine interpolation bounds both complete surfaces by that gap",before_sha256=hashlib.sha256(before.read_bytes()).hexdigest(),after_sha256=hashlib.sha256(after.read_bytes()).hexdigest(),checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),embedding_or_mechanical_admission_established=False)
(r/"fidelity.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result))
