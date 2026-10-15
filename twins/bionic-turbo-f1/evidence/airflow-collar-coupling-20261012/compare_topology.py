"""Independent native split ancestry and stitched cell/face correspondence."""
import json,re,sys
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
w=Path(__file__).parent;base=Path('work/bionic-airflow-20261012')
def verify(case):
 r=json.loads((case/'report.json').read_text())
 assert all(sha(case/n)==h for n,h in r['output_sha256'].items())
 return r
def mesh(path):
 p=ascii_list((path/'points').read_text(),True)
 f=[np.asarray(x,int) for x in ascii_faces((path/'faces').read_text())]
 o=ascii_list((path/'owner').read_text()).astype(int);n=ascii_list((path/'neighbour').read_text()).astype(int)
 return p,f,o,n
def cycle(f):
 f=tuple(map(int,f));return min(f[i:]+f[:i] for i in range(len(f)))
def cells(f,o,n):
 out=[[] for _ in range(int(max(o.max(),n.max())+1))]
 for i,c in enumerate(o):out[c].append(cycle(f[i]))
 for i,c in enumerate(n):out[c].append(cycle(f[i][::-1]))
 return [tuple(sorted(fs)) for fs in out]
# Orientation matters; rotation is harmless but reversal is not.
assert cycle([1,2,3])==cycle([2,3,1]) and cycle([1,2,3])!=cycle([3,2,1])
for name in ('full-collar-063','collar-split-065','collar-stitch-066','collar-clean-067'):verify(base/name)
p,f,o,n=mesh(base/'full-collar-063/constant/polyMesh');original=cells(f,o,n)
assert len(set(original))==27136
split=base/'collar-split-065/constant';covered=[];splitfaces=Counter();rounding=0.
for region in ('rotorZone','domain1'):
 path=split/region/'polyMesh';rp,rf,ro,rn=mesh(path)
 pm=ascii_list((path/'pointRegionAddressing').read_text()).astype(int)
 fm=ascii_list((path/'faceRegionAddressing').read_text()).astype(int)
 cm=ascii_list((path/'cellRegionAddressing').read_text()).astype(int)
 assert len(pm)==len(rp) and len(fm)==len(rf) and len(cm)==int(max(ro.max(),rn.max())+1)
 rounding=max(rounding,float(np.linalg.norm(rp-p[pm],axis=1).max()));assert rounding<1e-16
 for face,label in zip(rf,fm):
  assert label!=0
  expected=f[abs(label)-1][::1 if label>0 else -1]
  assert cycle(pm[face])==cycle(expected)
  splitfaces[abs(label)-1]+=1
 mapped=cells([pm[x] for x in rf],ro,rn)
 assert all(mapped[i]==original[c] for i,c in enumerate(cm))
 covered.extend(cm.tolist())
assert sorted(covered)==list(range(27136))
assert set(splitfaces)==set(range(len(f))) and Counter(splitfaces.values())==Counter({1:75136,2:6784})
q,g,a,b=mesh(base/'collar-clean-067/constant/polyMesh')
dist,pm=cKDTree(p).query(q);assert dist.max()<1e-16 and len(set(pm))==len(p)==len(q)
joined=cells([pm[x] for x in g],a,b);lookup={v:i for i,v in enumerate(original)}
assert len(joined)==27136 and set(joined)==set(original)
cm=np.array([lookup[x] for x in joined]);assert len(set(cm))==27136
# Every shared face carries precisely its original owner/neighbour pair.
def face_records(f,o,n,pointmap,cellmap):
 result=[]
 for i,face in enumerate(f):
  own=int(cellmap[o[i]]);nei=int(cellmap[n[i]]) if i<len(n) else -1
  face=pointmap[face]
  if nei>=0 and own>nei:own,nei=nei,own;face=face[::-1]
  result.append((cycle(face),own,nei))
 return Counter(result)
assert face_records(f,o,n,np.arange(len(p)),np.arange(27136))==face_records(g,a,b,pm,cm)
def zone(path):
 s=(path/'cellZones').read_text();m=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*\d+\s*\((.*?)\)',s,re.S)
 assert m;return np.fromstring(m[1],sep=' ',dtype=int)
assert set(cm[zone(base/'collar-clean-067/constant/polyMesh')])==set(zone(base/'full-collar-063/constant/polyMesh'))
# createPatch changes boundary metadata; native geometry and addressing stay exact.
u,v,c,d=mesh(base/'collar-stitch-066/constant/polyMesh')
assert np.array_equal(q,u) and np.array_equal(a,c) and np.array_equal(b,d)
assert len(g)==len(v) and all(np.array_equal(x,y) for x,y in zip(g,v))
assert np.array_equal(zone(base/'collar-stitch-066/constant/polyMesh'),zone(base/'collar-clean-067/constant/polyMesh'))
result=dict(all_payloads_verified=True,split_parentage_verified=True,split_cells_once=27136,split_faces_twice=6784,stitched_cells_bijective=True,oriented_faces_and_owner_neighbour_preserved=True,rotor_zone_preserved=True,cleanup_changes_no_geometry_or_zone=True,max_split_point_rounding_m=rounding,max_joined_point_rounding_m=float(dist.max()),native_mesh_admitted=True,flow_solver_launched=False,physical_subdomain_meshing_qualified=False,reader_sha256=sha(Path(__file__)))
with (w/'topology-readback.json').open('x') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result))
