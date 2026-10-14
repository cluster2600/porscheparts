#!/usr/bin/env python3
"""Reconstruct the logical half-station grid before projecting uniform quads."""
import numpy as np
from uniform_interface_projection import project as radial_project,metrics


def project(points,faces,nodes_mm,omega):
    p=np.asarray(points,dtype=float);nodes=np.asarray(nodes_mm,dtype=float)
    if nodes.ndim!=2 or nodes.shape[1]!=2 or len(nodes)<2 or not np.isfinite(nodes).all() or np.any(np.diff(nodes[:,0])<=0) or not np.isfinite(p).all():raise ValueError('Finite increasing source grid required')
    stations=np.sort(np.r_[nodes[:,0],(nodes[:-1,0]+nodes[1:,0])/2])/1000
    ids=np.unique(np.concatenate(faces));q=p.copy();distance=np.abs(p[ids,2,None]-stations)
    nearest=distance.argmin(axis=1)
    if np.any(np.diff(np.sort(distance,axis=1)[:,:2],axis=1)<=1e-14):raise ValueError('Ambiguous logical axial station')
    q[ids,2]=stations[nearest];labels=dict(zip(ids,nearest))
    for face in faces:
        levels=sorted(set(labels[i] for i in face))
        if len(levels)!=2 or levels[1]-levels[0]!=1:raise ValueError('Uniform adjacent half-stations required')
    q,audit=radial_project(q,faces,nodes_mm,omega)
    audit.update(before=metrics(p,faces,omega),moved_points=int(np.count_nonzero(np.linalg.norm(q-p,axis=1)>0)),max_displacement_m=float(np.linalg.norm(q-p,axis=1).max()),max_axial_displacement_m=float(np.abs(q[:,2]-p[:,2]).max()),logical_stations_m=stations.tolist())
    return q,audit
