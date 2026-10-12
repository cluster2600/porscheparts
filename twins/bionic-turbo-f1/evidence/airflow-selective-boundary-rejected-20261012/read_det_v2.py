"""Reproduce native internal-face determinant and preserve all paired payloads."""
import hashlib,json,re,sys,tarfile
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from frame_balance_batches import geometry
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz')
assert sha(archive)=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
refs=[]
with tarfile.open(archive) as t:
 for tail in ('primitiveMeshCheck/primitiveMeshTools.C','polyMeshCheck/polyMeshCheck.C'):
  members=[m for m in t.getmembers() if m.name.endswith(tail)];assert len(members)==1
  m=members[0];data=t.extractfile(m).read();dest=w/Path(m.name).name
  assert dest.read_bytes()==data
  refs.append(dict(member=m.name,sha256=sha(dest)))
assert 'getInternalOrCoupledFaces' in (w/'polyMeshCheck.C').read_text()
assert 'mag(det(areaTensor))/8.0' in (w/'primitiveMeshTools.C').read_text()
def load(case,sub='constant/polyMesh'):
 r=json.loads((case/'report.json').read_text());assert all(sha(case/n)==h for n,h in r['output_sha256'].items())
 m=case/sub;p=ascii_list((m/'points').read_text(),True);f=[np.array(x,dtype=int) for x in ascii_faces((m/'faces').read_text())];o=ascii_list((m/'owner').read_text()).astype(int);n=ascii_list((m/'neighbour').read_text()).astype(int)
 return p,f,o,n

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
parent=root/'collar-split-065';pp,pf,po,pn=load(parent,'constant/domain1/polyMesh');results={}
for name in ('selective-initial-071','selective-unshifted-072'):
 case=root/name;p,f,o,n=load(case);initial=w/(name+'-inputs');manifest=json.loads((initial/'manifest.json').read_text())
 assert all(sha(initial/k)==h for k,h in manifest['file_sha256'].items())
 assert all(np.array_equal(x,y) for x,y in zip(f,pf)) and len(f)==len(pf)
 assert np.array_equal(o,po) and np.array_equal(n,pn)
 protected=np.array(manifest['frozen_point_labels']);moving=np.array(manifest['moving_point_labels'])
 assert np.array_equal(p[protected],pp[protected])
 if name.endswith('072'):assert np.array_equal(p,pp)
 d=determinant(p,f,o,n);bad=ascii_list((case/'constant/polyMesh/sets/underdeterminedCells').read_text()).astype(int)
 assert np.array_equal(np.sort(bad),np.flatnonzero(d<.001)) and len(bad)==6784
 log=(case/'log.checkMesh').read_text();match=re.search(r'determinant \(wellposedness\) : minimum: (\S+) average: (\S+)',log);assert match
 native=np.array([float(match[1]),float(match[2])]);calc=np.array([d.min(),d.mean()]);assert np.allclose(calc,native,rtol=1e-9,atol=1e-15)
 results[name]=dict(points=len(p),faces=len(f),cells=len(d),bad_cells=len(bad),native_min_mean=native.tolist(),reconstructed_min_mean=calc.tolist(),protected_point_max_displacement_m=float(np.linalg.norm(p[protected]-pp[protected],axis=1).max()),moving_point_max_displacement_m=float(np.linalg.norm(p[moving]-pp[moving],axis=1).max()),topology_identical_to_source=True,report_sha256=sha(case/'report.json'))
# Native parent cells retain a radial internal face before isolation.
bp,bf,bo,bn=load(root/'full-collar-063');bd=determinant(bp,bf,bo,bn);mapping=ascii_list((parent/'constant/domain1/polyMesh/cellRegionAddressing').read_text()).astype(int)
assert len(mapping)==6784 and len(np.unique(mapping))==6784
results['parent_outer_cells']=dict(minimum=float(bd[mapping].min()),maximum=float(bd[mapping].max()),all_above_criterion=bool(np.all(bd[mapping]>=.001)))
assert results['parent_outer_cells']['all_above_criterion']
res=dict(source_archive_sha256=sha(archive),official_url='https://dl.openfoam.com/source/v2406/OpenFOAM-v2406.tgz',members=refs,source_sha256=sha(Path(__file__)),results=results,scope='Native determinant depends on internal/coupled face connectivity. Standalone noncoupled wall closure loses radial internal-face contribution; no threshold changed. No snap and no flow solver executed.')
with (w/'readback.json').open('x') as f:json.dump(res,f,indent=2)
print(json.dumps(res,indent=2))
