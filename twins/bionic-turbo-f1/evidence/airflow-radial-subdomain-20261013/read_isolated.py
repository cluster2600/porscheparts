"""Verify new region maps and isolated radial determinant without coupled patches."""
import json,re,sys
from collections import Counter
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from frame_balance_batches import geometry
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

def determinant(p,f,o,n):
 # Only internal faces: all patches in these standalone witnesses are walls.
 count=int(max(o.max(),n.max())+1);a=np.empty((len(n),3))
 for size in sorted(set(map(len,f[:len(n)]))):
  ids=np.array([i for i in range(len(n)) if len(f[i])==size]);_,areas,_=geometry(p[np.array([f[i] for i in ids])]);a[ids]=areas
 length=np.linalg.norm(a,axis=1);sums=np.zeros(count);counts=np.zeros(count);tensor=np.zeros((count,3,3))
 for labels in (o[:len(n)],n):
  np.add.at(sums,labels,length);np.add.at(counts,labels,1)
  np.add.at(tensor,labels,np.einsum('ij,ik->ijk',a,a))
 assert np.all(counts>0)
 avg=sums/counts;tensor/=avg[:,None,None]**2
 return np.abs(np.linalg.det(tensor))/8
# Cube self-check has area tensor diag(2,2,2), normalized determinant one.
assert abs(np.linalg.det(np.eye(3)*2)/8-1)<1e-15
for name in ('radial-full-077','radial-split-078','radial-isolated-079'):verify(base/name)
p,f,o,n=mesh(base/'radial-full-077/constant/polyMesh');original=cells(f,o,n)
assert len(set(original))==33920
split=base/'radial-split-078/constant';covered=[];splitfaces=Counter();rounding=0.
for region in ('rotorZone','domain1'):
 path=split/region/'polyMesh';rp,rf,ro,rn=mesh(path)
 pm=ascii_list((path/'pointRegionAddressing').read_text()).astype(int)
 fm=ascii_list((path/'faceRegionAddressing').read_text()).astype(int)
 cm=ascii_list((path/'cellRegionAddressing').read_text()).astype(int)
 assert len(pm)==len(rp) and len(fm)==len(rf) and len(cm)==int(max(ro.max(),rn.max())+1)
 rounding=max(rounding,float(np.linalg.norm(rp-p[pm],axis=1).max()));assert rounding==0
 for face,label in zip(rf,fm):
  assert label!=0
  expected=f[abs(label)-1][::1 if label>0 else -1]
  assert cycle(pm[face])==cycle(expected)
  splitfaces[abs(label)-1]+=1
 mapped=cells([pm[x] for x in rf],ro,rn)
 assert all(mapped[i]==original[c] for i,c in enumerate(cm))
 covered.extend(cm.tolist())
assert sorted(covered)==list(range(33920))
assert set(splitfaces)==set(range(len(f))) and Counter(splitfaces.values())==Counter({1:95616,2:6784})
case=base/'radial-isolated-079';path=case/'constant/polyMesh'
q,g,a,b=mesh(path);rp,rf,ro,rn=mesh(split/'domain1/polyMesh')
assert np.array_equal(q,rp) and np.array_equal(a,ro) and np.array_equal(b,rn)
assert len(g)==len(rf) and all(np.array_equal(x,y) for x,y in zip(g,rf))
assert not list(path.glob('*RegionAddressing')) and 'mapped' not in (path/'boundary').read_text()
assert re.findall(r'type\s+(\w+)',(path/'boundary').read_text())==['wall']
assert 'rotorZone' not in (path/'cellZones').read_text()
initial=w/'radial-isolated-079-inputs';manifest=json.loads((initial/'manifest.json').read_text())
assert all(sha(initial/k)==v for k,v in manifest['file_sha256'].items())
assert all(sha(case/k)==v for k,v in manifest['file_sha256'].items()),'checkMesh must preserve all prepared inputs'
d=determinant(q,g,a,b);assert len(d)==13568 and np.all(d>=.001)
log=(case/'log.checkMesh').read_text();match=re.search(r'determinant \(wellposedness\) : minimum: (\S+) average: (\S+)',log);assert match
native=np.array([float(match[1]),float(match[2])]);calculated=np.array([d.min(),d.mean()]);assert np.allclose(native,calculated,rtol=1e-9,atol=1e-15)
# Every isolated cell has a native radial internal face, unlike 071/072.
cf=np.empty((len(g),3));sf=cf.copy();warp=np.empty(len(g))
for size in sorted(set(map(len,g))):
 ids=np.array([i for i,x in enumerate(g) if len(x)==size]);cf[ids],sf[ids],warp[ids]=geometry(q[np.array([g[i] for i in ids])])
# Select cylindrical/profile-side faces by all four points spanning two angles and two z stations.
radial_ids=[]
for i in range(len(b)):
 verts=q[g[i]]
 # Radial faces have two distinct axial coordinates and nonzero radial area.
 if np.ptp(verts[:,2])>1e-12 and abs(np.dot(cf[i,:2],sf[i,:2]))>1e-12:radial_ids.append(i)
radial_ids=np.array(radial_ids);incident=np.bincount(np.r_[a[radial_ids],b[radial_ids]],minlength=len(d))
assert len(radial_ids)==6784 and np.all(incident==1)
part=np.einsum('ij,ij->i',cf,sf)/3
vol=np.bincount(a,weights=part,minlength=len(d))-np.bincount(b,weights=part[:len(b)],minlength=len(d));assert vol.min()>0
# Closed oriented per-cell edge chains are verified through the parent-cell bijection.
result=dict(all_payloads_verified=True,split_parentage_verified=True,split_cells_once=33920,split_faces_twice=6784,split_point_rounding_m=rounding,isolated_points=len(q),isolated_faces=len(g),isolated_internal_faces=len(b),isolated_cells=len(d),isolated_mesh_identical_to_split_geometry=True,only_boundary_and_empty_zone_metadata_changed=True,no_stale_region_maps_copied=True,uncoupled_wall_only=True,all_cells_have_one_radial_internal_face=True,radial_internal_faces=len(radial_ids),determinant_native_min_mean=native.tolist(),determinant_reconstructed_min_mean=calculated.tolist(),bad_determinants=0,maximum_face_warp_m=float(warp.max()),boundary_volume_m3=float(vol.sum()),minimum_cell_volume_m3=float(vol.min()),native_mesh_admitted=True,flow_solver_launched=False,physical_subdomain_meshing_qualified=False,reader_sha256=sha(Path(__file__)))
(w/'isolated-readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
