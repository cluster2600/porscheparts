"""Fixed four-pass local fairing, clipped against the original vertex positions."""
import numpy as np
AUTHOR_CAP_MM=.0049

def fair(vertices, faces, seeds):
    v=np.asarray(vertices,dtype=np.float64);f=np.asarray(faces)
    if not np.isfinite(v).all() or f.dtype.kind not in 'iu':raise ValueError('Finite vertices and integer triangles required')
    ring=np.full(len(v),99,np.int8);ring[np.asarray(seeds,int)]=0
    for depth in range(1,5):
        incident=np.any(ring[f]<depth,axis=1);ids=np.unique(f[incident]);ring[ids]=np.minimum(ring[ids],depth)
    moving=ring<4;incident=np.any(moving[f],axis=1);patch_faces=f[incident];ids=np.unique(patch_faces);reverse=np.full(len(v),-1,np.int64);reverse[ids]=np.arange(len(ids));local_faces=reverse[patch_faces]
    edges=np.unique(np.sort(local_faces[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0)
    a=np.r_[edges[:,0],edges[:,1]];b=np.r_[edges[:,1],edges[:,0]];degree=np.bincount(a,minlength=len(ids));original=v[ids].copy();p=original.copy();weight=np.choose(np.minimum(ring[ids],4),[.5,.5,.375,.125,0.])
    for _ in range(4):
        average=np.zeros_like(p)
        for axis in range(3):average[:,axis]=np.bincount(a,weights=p[b,axis],minlength=len(ids))/degree
        delta=(p+weight[:,None]*(average-p))-original;size=np.abs(delta).sum(1);scale=np.minimum(1.,AUTHOR_CAP_MM/np.maximum(size,np.finfo(float).tiny));p=original+delta*scale[:,None]
    result=v.copy();result[ids]=p
    return result,dict(passes=4,author_cap_mm=AUTHOR_CAP_MM,verification_limit_mm=.005,patch_vertices=len(ids),changed_vertices=int(np.any(result!=v,axis=1).sum()),original_reference_retained=True)
