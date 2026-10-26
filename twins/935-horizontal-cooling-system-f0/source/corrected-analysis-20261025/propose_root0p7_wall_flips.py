"""Private exploratory flips; no candidate is admitted by this script."""
import hashlib, json, math
from pathlib import Path
import numpy as np
import trimesh

root=Path.cwd();out=root/'work/935-cfd-root0p7-20261026-flips'
source=root/'work/935-root-quality-local-20261025/analysis-candidate.off'
volume=root/'work/935-cfd-root0p7-20261026-audit/volume.npz'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='5d900f6da900b4bffac2fdacfd6e0a346f8c0259a19299725621d4fd1e48c12a'
assert hashlib.sha256(volume.read_bytes()).hexdigest()=='bcad2182f1e78e2cc6fe2ca90ddc5c277b0e93ca35dce4ddca9082b4a60e0420'
mesh=trimesh.load_mesh(source,process=False);vertices=np.asarray(mesh.vertices);faces=np.asarray(mesh.faces)
assert len(vertices)==439365 and len(faces)==878730 and mesh.is_watertight and mesh.is_winding_consistent

def quality(t):
    x=vertices[t]
    cross=np.cross(x[:,1]-x[:,0],x[:,2]-x[:,0]);area=np.linalg.norm(cross,axis=1)/2
    edges=sum(np.sum((x[:,i]-x[:,j])**2,axis=1) for i,j in ((0,1),(1,2),(2,0)))
    return 4*np.sqrt(3)*area/edges

q=quality(faces)
with np.load(volume) as z:
    fv=z['vertices'];cells=z['tetrahedra'];boundary=z['boundary'];tags=z['markers']
from importlib.util import spec_from_file_location,module_from_spec
spec=spec_from_file_location('audit',root/'twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/audit_root0p7_tet_quality.py')
audit=module_from_spec(spec);spec.loader.exec_module(audit)
ratio=np.concatenate([audit.mean_ratio(fv[cells[i:i+100000]]) for i in range(0,len(cells),100000)])
weak=cells[ratio<.01]
rotor=boundary[tags==4];assert len(rotor)==len(faces) and np.array_equal(fv[8503:8503+len(vertices)],vertices*.001)
row3=np.dtype((np.void,rotor.dtype.itemsize*3))
ref=np.ascontiguousarray(np.sort(faces[:,::-1]+8503,axis=1)).view(row3).ravel();order=np.argsort(ref);sorted_ref=ref[order]
tet_faces=np.stack([weak[:,[1,2,3]],weak[:,[0,3,2]],weak[:,[0,1,3]],weak[:,[0,2,1]]],axis=1).reshape(-1,3)
query=np.ascontiguousarray(np.sort(tet_faces,axis=1)).view(row3).ravel();loc=np.searchsorted(sorted_ref,query)
match=np.zeros(len(loc),bool);valid=loc<len(sorted_ref);match[valid]=sorted_ref[loc[valid]]==query[valid]
incident=np.unique(order[loc[match]]);target=incident[q[incident]<.1]
assert len(weak)==3461 and len(incident)==1989 and len(target)>0

all_edges=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]);all_edges.sort(axis=1)
row2=np.dtype((np.void,all_edges.dtype.itemsize*2))
ekeys=np.ascontiguousarray(all_edges).view(row2).ravel();eorder=np.argsort(ekeys);sorted_edges=ekeys[eorder]
owner=np.tile(np.arange(len(faces)),3)

def edge_key(u,v):
    return np.ascontiguousarray(np.array([[min(u,v),max(u,v)]],dtype=faces.dtype)).view(row2).ravel()[0]

def normal(tri):
    x=vertices[tri]
    n=np.cross(x[1]-x[0],x[2]-x[0]);return n/np.linalg.norm(n)

proposals={}
for fi in target:
    f=faces[fi]
    for k in range(3):
        u,v,p=map(int,(f[k],f[(k+1)%3],f[(k+2)%3]));key=edge_key(u,v)
        left=np.searchsorted(sorted_edges,key,'left');right=np.searchsorted(sorted_edges,key,'right')
        if right-left!=2:continue
        adjacent=owner[eorder[left:right]];other=int(adjacent[0] if adjacent[1]==fi else adjacent[1])
        g=faces[other]
        if not any(g[j]==v and g[(j+1)%3]==u for j in range(3)):continue
        h=[int(x) for x in g if x not in (u,v)]
        if len(h)!=1:continue
        r=h[0]
        if p==r:continue
        diag=edge_key(p,r)
        if np.searchsorted(sorted_edges,diag,'right')>np.searchsorted(sorted_edges,diag,'left'):continue
        n1,n2=normal(f),normal(g)
        if np.dot(n1,n2)<math.cos(math.radians(5)):continue
        pair=np.array([[p,r,v],[r,p,u]],dtype=faces.dtype)
        newq=quality(pair);oldmin=min(q[fi],q[other]);newmin=float(newq.min())
        if not (newmin>.15 and newmin>1.5*oldmin):continue
        if min(np.dot(normal(pair[0]),n1),np.dot(normal(pair[1]),n2))<math.cos(math.radians(20)):continue
        key_faces=tuple(sorted((int(fi),other)))
        gain=newmin-oldmin
        if key_faces not in proposals or proposals[key_faces][0]<gain:
            proposals[key_faces]=(gain,pair,(u,v,p,r),oldmin,newmin)

chosen=[];used_faces=set();used_vertices=set()
for (i,j),row in sorted(proposals.items(),key=lambda x:x[1][0],reverse=True):
    if i in used_faces or j in used_faces or any(v in used_vertices for v in row[2]):continue
    chosen.append((i,j,row));used_faces.update((i,j));used_vertices.update(row[2])
    if len(chosen)==32:break
candidate=faces.copy()
for i,j,row in chosen:candidate[i],candidate[j]=row[1]
newmesh=trimesh.Trimesh(vertices=vertices,faces=candidate,process=False)
assert newmesh.is_watertight and newmesh.is_winding_consistent and newmesh.volume>0
assert np.array_equal(newmesh.vertices,vertices)
off=out/'candidate.off'
with off.open('x') as stream:
    stream.write(f'OFF\n{len(vertices)} {len(candidate)} 0\n')
    np.savetxt(stream,vertices,fmt='%.17g')
    np.savetxt(stream,np.column_stack([np.full(len(candidate),3),candidate]),fmt='%d')
receipt={'status':'flip_proposal_pending_full_envelope_and_volume_audits','source_off_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'volume_npz_sha256':hashlib.sha256(volume.read_bytes()).hexdigest(),'incident_weak_rotor_faces':len(incident),'incident_faces_below_q0p1':len(target),'candidate_pairs':len(proposals),'selected_disjoint_flips':len(chosen),'selected': [{'face_ids':[i,j],'old_pair_min_quality':row[3],'new_pair_min_quality':row[4]} for i,j,row in chosen],'candidate_off_sha256':hashlib.sha256(off.read_bytes()).hexdigest(),'vertices_unchanged':True,'CFD_accepted':False}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='selected'}),flush=True)
