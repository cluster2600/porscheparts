"""Bounded-memory polygon geometry with the pinned native face-centre formula."""
import numpy as np


def geometry(vertices):
    p=np.asarray(vertices,float)
    if p.ndim!=3 or p.shape[2]!=3 or p.shape[1]<3 or not np.isfinite(p).all():raise ValueError('Finite equal-length polygons required')
    if p.shape[1]==3:c=p.mean(axis=1);s=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])*.5
    else:
        seed=p.mean(axis=1)[:,None,:];end=np.roll(p,-1,axis=1);normals=np.cross(end-p,seed-p);weights=np.linalg.norm(normals,axis=2)
        if np.any(weights.sum(axis=1)<=0):raise ValueError('Zero area polygon')
        c=((p+end+seed)*weights[:,:,None]).sum(axis=1)/(3*weights.sum(axis=1)[:,None]);s=normals.sum(axis=1)*.5
    area=np.linalg.norm(s,axis=1)
    if np.any(area<=0):raise ValueError('Zero oriented area')
    warp=np.abs(np.einsum('nkj,nj->nk',p-p[:,:1],s/area[:,None])).max(axis=1)
    return c,s,warp
