#!/usr/bin/env python3
"""Inventory exact edge-connected rotor components without repairing geometry."""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def inventory(points,faces):
    points=np.asarray(points,dtype=float);faces=[np.asarray(f,dtype=np.int64) for f in faces]
    if points.ndim!=2 or points.shape[1]!=3 or not np.isfinite(points).all() or not faces:
        raise ValueError('Finite points and nonempty faces required')
    if any(f.ndim!=1 or len(f)<3 or len(np.unique(f))!=len(f) or f.min()<0 or f.max()>=len(points) for f in faces):
        raise ValueError('Invalid face addressing')
    sizes=np.array([len(f) for f in faces]);flat=np.concatenate(faces);ends=np.cumsum(sizes);starts=ends-sizes
    following=np.arange(len(flat))+1;following[ends-1]=starts
    edges=np.sort(np.column_stack((flat,flat[following])),axis=1)
    unique,first,inverse,counts=np.unique(edges,axis=0,return_index=True,return_inverse=True,return_counts=True)
    if np.any(counts>2):raise ValueError('Nonmanifold edge in rotor patch')
    owners=np.repeat(np.arange(len(faces)),sizes);order=np.argsort(inverse,kind='stable');last=np.cumsum(counts)[counts==2]
    a=owners[order[last-2]];b=owners[order[last-1]]
    graph=coo_matrix((np.ones(len(a)),(a,b)),shape=(len(faces),len(faces)))
    number,labels=connected_components(graph,directed=False)
    results=[]
    for label in range(number):
        face_ids=np.flatnonzero(labels==label);vertex_ids=np.unique(flat[labels[owners]==label]);edge_ids=np.flatnonzero(labels[owners[first]]==label)
        p=points[vertex_ids];boundary=int(np.count_nonzero(counts[edge_ids]==1))
        results.append(dict(component=label,faces=len(face_ids),vertices=len(vertex_ids),edges=len(edge_ids),boundary_edges=boundary,closed=boundary==0,euler_characteristic=len(vertex_ids)-len(edge_ids)+len(face_ids),bounds_mm=[p.min(axis=0).tolist(),p.max(axis=0).tolist()],vertex_radius_range_mm=[float(np.linalg.norm(p[:,:2],axis=1).min()),float(np.linalg.norm(p[:,:2],axis=1).max())],first_face=int(face_ids[0])))
    return results
