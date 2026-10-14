"""Partition star-shaped cells into face pyramids, retaining all boundary polygons."""
import numpy as np
from audit_frame_interface import face_geometry


def partition(points,faces,owner,neighbour,zone):
    p=np.asarray(points,float);owner=np.asarray(owner,int);neighbour=np.asarray(neighbour,int)
    if len(owner)!=len(faces) or len(neighbour)>len(faces) or not np.isfinite(p).all() or np.any(owner<0) or np.any(neighbour<0):raise ValueError('Invalid mesh arrays')
    count=int(max(owner.max(),neighbour.max(initial=-1)))+1;incidence=[[] for _ in range(count)]
    for i,o in enumerate(owner):incidence[o].append((i,False))
    for i,n in enumerate(neighbour):incidence[n].append((i,True))
    centres=[];base_owner=np.full(len(faces),-1,int);base_nei=np.full(len(neighbour),-1,int);extra=[];parent=[]
    for cell,inc in enumerate(incidence):
        if len(inc)<4:raise ValueError('Unclosed cell')
        vertices=np.unique(np.concatenate([faces[i] for i,_ in inc]));centre=p[vertices].mean(axis=0);centres.append(centre);apex=len(p)+cell;sides={}
        for i,reverse in inc:
            face=list(map(int,faces[i]));face=face[::-1] if reverse else face;c,s=face_geometry(p[face]);unit=s/np.linalg.norm(s)
            if np.abs((p[face]-p[face[0]])@unit).max()>1e-12 or np.dot(c-centre,unit)<=1e-14:raise ValueError('Nonplanar base or centre outside cell kernel')
            sub=len(parent);parent.append(cell)
            if reverse:base_nei[i]=sub
            else:base_owner[i]=sub
            for a,b in zip(face,face[1:]+face[:1]):
                key=tuple(sorted((a,b)));tri=[b,a,apex]
                if key in sides:
                    previous,prior=sides.pop(key)
                    if prior!=[a,b,apex]:raise ValueError('Inconsistent shared edge orientation')
                    extra.append((prior,previous,sub))
                else:sides[key]=(sub,tri)
        if sides:raise ValueError('Open cell edge chain')
    q=np.concatenate((p,np.asarray(centres)));parent=np.asarray(parent,int)
    records=[(list(faces[i]),int(base_owner[i]),int(base_nei[i])) for i in range(len(neighbour))]+extra
    normalized=[(f if o<n else f[::-1],min(o,n),max(o,n)) for f,o,n in records];normalized.sort(key=lambda r:(r[1],r[2]))
    new_faces=[x[0] for x in normalized]+[list(f) for f in faces[len(neighbour):]]
    new_owner=np.array([x[1] for x in normalized]+base_owner[len(neighbour):].tolist(),int);new_nei=np.array([x[2] for x in normalized],int)
    if len(set(zip(new_owner[:len(new_nei)],new_nei)))!=len(new_nei):raise ValueError('Multiple shared faces remain')
    new_zone=np.flatnonzero(np.isin(parent,zone))
    return q,new_faces,new_owner,new_nei,new_zone,parent
