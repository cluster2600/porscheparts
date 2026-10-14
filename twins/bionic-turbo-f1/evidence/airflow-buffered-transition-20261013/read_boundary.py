"""Prove planar cap subdivision by containment and oriented edge chains."""
import json,hashlib
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from scipy.spatial import cKDTree
w=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=json.loads((w/'construction.json').read_text());oldpath=Path('work/bionic-staged-transition-20261013/construction.json');assert sha(oldpath)=='930da4349e0e08f067a919dcc0fcf9810b48ffa50190b51edc56f34feee8985c';old=json.loads(oldpath.read_text());p=np.array(s['vertices']);q=np.array(old['vertices'])
def collapse(f):
 out=[]
 for x in f:
  if not out or out[-1]!=x:out.append(x)
 if out[-1]==out[0]:out.pop()
 return out
def canon(f):return min(tuple(f[i:]+f[:i]) for i in range(len(f)))
oldfaces=[collapse(f) for f in old['walls']];newfaces=[collapse(f) for f in s['walls']]
d,oldmap=cKDTree(p).query(q);assert d.max()==0 and len(set(oldmap))==len(q)
newold={int(v):i for i,v in enumerate(oldmap)};ends=[min(q[:,2]),max(q[:,2])]
is_cap=lambda f,a:all(a[i,2]==a[f[0],2] for i in f) and a[f[0],2] in ends
oldcaps=[f for f in oldfaces if is_cap(f,q)];newcaps=[f for f in newfaces if is_cap(f,p)]
nonold={canon([int(oldmap[i]) for i in f]) for f in oldfaces if not is_cap(f,q)};nonnew={canon(f) for f in newfaces if not is_cap(f,p)};assert nonold==nonnew
# Every new cap point is a midpoint of one old radial edge, proved from local neighbouring source vertices.
newids={i for f in newcaps for i in f if i not in newold};edges={tuple(sorted((a,b))) for f in oldcaps for a,b in zip(f,f[1:]+f[:1])};tree=cKDTree(q);midparent={};errors=[]
for i in newids:
 near=tree.query(p[i],k=12)[1];matches=[]
 for a in near:
  for b in near:
   if a<b and (int(a),int(b)) in edges:
    err=float(np.linalg.norm(p[i]-(q[a]+q[b])/2))
    if err<1e-16:matches.append((int(a),int(b),err))
 assert len(matches)==1;midparent[i]=matches[0][:2];errors.append(matches[0][2])
# Match descendants through exact source support labels; no assumed face numbering or centroid tolerance.
children=defaultdict(list)
for f in newcaps:
 support=set()
 for i in f:support.update([newold[i]] if i in newold else midparent[i])
 match=[j for j,g in enumerate(oldcaps) if support<=set(g)];assert len(match)==1;children[match[0]].append(f)
assert len(children)==len(oldcaps)
for j,g in enumerate(oldcaps):
 xy=q[g,:2];cross=lambda a,b:a[0]*b[1]-a[1]*b[0];turns=[cross(xy[(k+1)%len(g)]-xy[k],xy[(k+2)%len(g)]-xy[(k+1)%len(g)]) for k in range(len(g))];assert all(x>0 for x in turns) or all(x<0 for x in turns);sign=1 if turns[0]>0 else -1
 for f in children[j]:
  assert all(p[i,2]==q[g[0],2] for i in f)
  for i in f:
   assert all(sign*cross(xy[(k+1)%len(g)]-xy[k],p[i,:2]-xy[k])>=-1e-20 for k in range(len(g)))
 # Parent boundary with midpoint insertions; descendants' interior edges cancel exactly by labels.
 expected=[]
 for a,b in zip(g,g[1:]+g[:1]):
  expected.append(int(oldmap[a]));mids=[i for i,e in midparent.items() if set(e)=={a,b}];assert len(mids)<=1;expected+=mids
 edge=Counter((a,b) for f in children[j] for a,b in zip(f,f[1:]+f[:1]));boundary=Counter({(a,b):n-edge[b,a] for (a,b),n in edge.items() if n>edge[b,a]});assert boundary==Counter(zip(expected,expected[1:]+expected[:1]))
result={'source_sha256':sha(Path(__file__)),'construction_sha256':sha(w/'construction.json'),'old_points_exact':len(q),'noncap_faces_exact_oriented':len(nonnew),'old_cap_faces':len(oldcaps),'new_cap_faces':len(newcaps),'parent_child_counts':dict(Counter(len(c) for c in children.values())),'new_cap_midpoints':len(newids),'maximum_midpoint_error_m':max(errors),'convexity_containment_and_oriented_edge_coverage_verified':True,'volume_equality_not_used_as_coverage_proof':True,'native_executed':False}
(w/'boundary-readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
