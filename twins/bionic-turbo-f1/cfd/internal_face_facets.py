"""Split warped internal quads without moving points or touching MRF/wall faces."""
import numpy as np
from audit_frame_interface import face_geometry


def facet_internal(points,faces,owner,neighbour,protected):
    p=np.asarray(points,float);owner=np.asarray(owner,int);neighbour=np.asarray(neighbour,int)
    if len(owner)!=len(faces) or len(neighbour)>len(faces) or not np.isfinite(p).all():raise ValueError('Invalid native mesh arrays')
    protected=set(map(int,protected));result=[];parents=[];split=[]
    if any(i<0 or i>=len(neighbour) for i in protected):raise ValueError('Invalid protected interface')
    for i,face in enumerate(faces):
        face=list(map(int,face));v=p[face];c,s=face_geometry(v);warp=float(np.abs((v-v[0])@(s/np.linalg.norm(s))).max())
        if i<len(neighbour) and i not in protected and warp>1e-14:
            if len(face)!=4 or len(set(face))!=4:raise ValueError('Only warped quads supported')
            triangles=[face[:3],[face[0],face[2],face[3]]]
            areas=[face_geometry(p[f])[1] for f in triangles]
            if any(np.dot(a,s)<=0 for a in areas) or not np.allclose(sum(areas),s,rtol=1e-12,atol=1e-24):raise ValueError('Invalid oriented subdivision')
            result.extend(triangles);parents.extend([i,i]);split.append(i)
        else:result.append(face);parents.append(i)
    parents=np.asarray(parents,int);internal=int(np.count_nonzero(parents<len(neighbour)))
    return result,owner[parents],neighbour[parents[:internal]],parents,dict(split_original_faces=split,points_moved=0,protected_faces_unchanged=True,boundary_faces_unchanged=True)


def balance(points,faces,owner,neighbour,omega,zone):
    count=int(max(np.max(owner),np.max(neighbour,initial=-1)))+1
    net=np.zeros(count);closure=np.zeros((count,3));volume=np.zeros(count);warp=[];flux=[]
    for i,f in enumerate(faces):
        p=points[list(f)];c,s=face_geometry(p);q=float(np.dot(np.cross([0,0,omega],c),s));v=float(np.dot(c,s))/3
        net[owner[i]]+=q;closure[owner[i]]+=s;volume[owner[i]]+=v
        if i<len(neighbour):net[neighbour[i]]-=q;closure[neighbour[i]]-=s;volume[neighbour[i]]-=v
        warp.append(float(np.abs((p-p[0])@(s/np.linalg.norm(s))).max()));flux.append(q)
    z=np.asarray(zone,int);order=z[np.argsort(np.abs(net[z]))[-20:][::-1]]
    return dict(cells=count,faces=len(faces),max_face_warp_m=max(warp),max_area_closure_m2=float(np.linalg.norm(closure,axis=1).max()),minimum_oriented_cell_volume_m3=float(volume.min()),max_rotating_cell_flux_m3_s=float(np.abs(net[z]).max()),worst_rotating_cells=[dict(cell=int(i),geometric_frame_flux_m3_s=float(net[i])) for i in order]),np.asarray(flux)
