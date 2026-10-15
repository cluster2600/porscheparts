"""Build an explicitly paired closed synthetic target from native086 boundary."""
import json,re,sys
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
from audit_diagnostic import ascii_list
from run_case import ascii_faces
from frame_balance_batches import geometry
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');parent=root/'outer-wall-bisect-086';m=parent/'constant/polyMesh'
r=json.loads((parent/'report.json').read_text());assert r['mesh_gate_passed'] and r['native_exit_code']==0 and not r['container_state']['OOMKilled'];assert all(sha(parent/n)==h for n,h in r['output_sha256'].items())
p=ascii_list((m/'points').read_text(),True);f=[np.array(x,int) for x in ascii_faces((m/'faces').read_text())];o=ascii_list((m/'owner').read_text()).astype(int);n=ascii_list((m/'neighbour').read_text()).astype(int)
bl=re.search(r'outerWall\s*\{(.*?)\}',(m/'boundary').read_text(),re.S)[1];start=int(re.search(r'startFace\s+(\d+)',bl)[1]);cnt=int(re.search(r'nFaces\s+(\d+)',bl)[1]);outer=set(range(start,start+cnt));regions=defaultdict(list)
for i in range(len(n),len(f)):
 v=f[i];name='outer' if i in outer else ('rear' if np.all(p[v,2]==p[:,2].min()) else 'front' if np.all(p[v,2]==p[:,2].max()) else 'join');regions[name].append(i)
assert {k:len(v) for k,v in regions.items()}=={'join':6784,'rear':384,'front':384,'outer':6784}
# The named join is independently matched to source078, with exact point coordinates.
s=root/'radial-split-078/constant/domain1/polyMesh';sp=ascii_list((s/'points').read_text(),True);sf=[np.array(x,int) for x in ascii_faces((s/'faces').read_text())];b=re.search(r'domain1_to_rotorZone\s*\{(.*?)\}',(s/'boundary').read_text(),re.S)[1];st=int(re.search(r'startFace\s+(\d+)',b)[1]);ct=int(re.search(r'nFaces\s+(\d+)',b)[1]);jp=np.unique(np.concatenate(sf[st:st+ct]));dist,ix=cKDTree(p).query(sp[jp]);assert np.all(dist==0);mp=dict(zip(jp,ix))
def cyc(v):
 v=tuple(map(int,v));return min(v[i:]+v[:i] for i in range(len(v)))
assert {cyc(f[i]) for i in regions['join']}=={cyc([mp[x] for x in v]) for v in sf[st:st+ct]}
case=root/'castellation-target-089';assert not case.exists();(case/'constant/triSurface').mkdir(parents=True)
triangles=[];edges=Counter();bounds=[];records=[]
with (case/'constant/triSurface/collar.stl').open('x') as out:
 for name,ids in regions.items():
  out.write('solid '+name+'\n')
  for i in ids:
   v=f[i];xyz=p[v];assert len(v)==4
   normal=np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0]);axis=int(np.argmax(abs(normal)));xy=np.delete(xyz,axis,axis=1);e=np.roll(xy,-1,axis=0)-xy;c=e[:,0]*np.roll(e[:,1],-1)-e[:,1]*np.roll(e[:,0],-1);assert np.all(c>0) or np.all(c<0)
   # Paired four-triangle fans: arithmetic centre versus midpoint of chosen diagonal.
   bounds.append(float(np.linalg.norm(xyz.mean(axis=0)-(xyz[0]+xyz[2])/2)))
   for labels in (v[[0,1,2]],v[[0,2,3]]):
    t=p[labels];nn=np.cross(t[1]-t[0],t[2]-t[0]);assert np.linalg.norm(nn)>0;nn/=np.linalg.norm(nn)
    out.write(' facet normal '+' '.join(format(x,'.17g') for x in nn)+'\n  outer loop\n')
    for point in t:out.write('   vertex '+' '.join(format(x,'.17g') for x in point)+'\n')
    out.write('  endloop\n endfacet\n');triangles.append(t)
    for a,b in zip(labels,np.roll(labels,-1)):edges[int(a),int(b)]+=1
  out.write('endsolid '+name+'\n')
assert all(v==1 and edges[b,a]==1 for (a,b),v in edges.items())
# Seed from an unchanged inner hex, strictly inside each oriented face plane and closed STL.
cf,sf,warp=geometry(p[np.array(f)]);candidates=np.unique(o[regions['join']]);seed=None
for cell in candidates:
 ids=np.flatnonzero(o==cell).tolist()+np.flatnonzero(n==cell).tolist();verts=np.unique(np.concatenate([f[i] for i in ids]));point=p[verts].mean(axis=0);normals=np.array([sf[i]*(1 if o[i]==cell else -1) for i in ids]);clear=-np.einsum('ij,ij->i',point-cf[ids],normals)/np.linalg.norm(normals,axis=1)
 if clear.min()>1e-6:
  seed=point;seedcell=int(cell);clearance=float(clear.min());break
assert seed is not None
t=np.array(triangles)-seed;norm=np.linalg.norm(t,axis=2);numer=np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2]));den=norm.prod(axis=1)+np.einsum('ij,ij->i',t[:,0],t[:,1])*norm[:,2]+np.einsum('ij,ij->i',t[:,1],t[:,2])*norm[:,0]+np.einsum('ij,ij->i',t[:,2],t[:,0])*norm[:,1];winding=float(np.arctan2(numer,den).sum()/(2*np.pi));assert abs(winding-1)<1e-10
report=dict(source_sha256=sha(Path(__file__)),parent_receipt_sha256=sha(parent/'report.json'),surface_sha256=sha(case/'constant/triSurface/collar.stl'),regions={k:len(v) for k,v in regions.items()},triangles=len(triangles),all_oriented_edges_paired=True,join_matches_source078=True,quad_projected_convexity_verified=True,paired_fan_hausdorff_upper_bound_m=max(bounds),bound_scope='Only explicit vertex-mean centre fans versus diagonal(v0,v2) triangulation, by common four-triangle barycentric pairing; not a measured distance or physical tolerance.',location_in_mesh=seed.tolist(),seed_parent_cell=seedcell,seed_min_face_plane_clearance_m=clearance,seed_target_winding=winding,synthetic_only=True)
(w/'target-preparation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
