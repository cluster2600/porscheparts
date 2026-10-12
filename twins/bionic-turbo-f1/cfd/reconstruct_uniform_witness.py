#!/usr/bin/env python3
"""Reconstruct all logical witness nodes, retaining the original faceted wall surfaces."""
import math
import numpy as np
from audit_frame_interface import face_geometry


def reconstruct(points,nodes_mm,width_mm,sectors):
    p=np.asarray(points,dtype=float);nodes=np.asarray(nodes_mm,dtype=float)/1000;width=width_mm/1000
    if p.ndim!=2 or p.shape[1]!=3 or not np.isfinite(p).all() or nodes.ndim!=2 or nodes.shape[1]!=2 or len(nodes)<2 or not np.isfinite(nodes).all() or np.any(np.diff(nodes[:,0])<=0) or not 0<width<nodes[:,1].min() or type(sectors)is not int or sectors<3:raise ValueError('Finite positive uniform annular grid required')
    stations=np.sort(np.r_[nodes[:,0],(nodes[:-1,0]+nodes[1:,0])/2]);angles=np.arctan2(p[:,1],p[:,0]);angular=np.rint(angles*sectors/np.pi).astype(int)%(2*sectors)
    if np.max(np.abs(np.angle(np.exp(1j*(angles-angular*np.pi/sectors)))))>1e-12:raise ValueError('Native rays do not match the uniform grid')
    distance=np.abs(p[:,2,None]-stations);axial=distance.argmin(axis=1)
    if np.any(np.diff(np.sort(distance,axis=1)[:,:2],axis=1)<=1e-14):raise ValueError('Ambiguous axial addressing')
    chord=np.where(angular%2,math.cos(math.pi/sectors),1.)
    offset=np.linalg.norm(p[:,:2],axis=1)/chord-np.interp(p[:,2],nodes[:,0],nodes[:,1]);offsets=np.linspace(-width,width,5)
    distance=np.abs(offset[:,None]-offsets);radial=distance.argmin(axis=1)
    if np.any(np.diff(np.sort(distance,axis=1)[:,:2],axis=1)<=1e-14):raise ValueError('Ambiguous radial addressing')
    addresses=np.column_stack((axial,radial,angular))
    if len(p)!=len(stations)*5*2*sectors or len(np.unique(addresses,axis=0))!=len(p):raise ValueError('Uniform tensor grid is incomplete or duplicated')
    z=stations[axial];r=np.interp(z,nodes[:,0],nodes[:,1])+offsets[radial]
    r*=np.where(radial==2,1.,chord)
    theta=angular*np.pi/sectors;q=np.column_stack((r*np.cos(theta),r*np.sin(theta),z))
    anchors=(axial%2==0)&(angular%2==0)&(radial%2==0);q[anchors]=p[anchors]
    caps=(axial==0)|(axial==len(stations)-1);q[caps,2]=p[caps,2]
    # Each lateral point stays within its original planar macro face; cap perimeter is unchanged.
    maximum=0.
    for i in np.flatnonzero((radial==0)|(radial==4)):
        band=min(max(int(np.searchsorted(nodes[:,0],q[i,2],side='right'))-1,0),len(nodes)-2);sector=angular[i]//2
        theta0=sector*2*np.pi/sectors;theta1=(sector+1)*2*np.pi/sectors;shift=offsets[radial[i]]
        quad=np.array([[r*math.cos(t),r*math.sin(t),z] for z,r0 in nodes[[band,band+1]] for t in (theta0,theta1) for r in [r0+shift]])[[0,1,3,2]]
        centre,area=face_geometry(quad);unit=area/np.linalg.norm(area);error=abs(float(np.dot(q[i]-centre,unit)));maximum=max(maximum,error)
        edges=np.roll(quad,-1,axis=0)-quad
        if error>1e-12 or np.any(np.einsum('ij,j->i',np.cross(edges,q[i]-quad),unit)<-1e-12*np.linalg.norm(edges,axis=1)):raise ValueError('Wall point escaped its original macro face')
    return q,dict(source_macro_vertices_unchanged=bool(np.array_equal(q[anchors],p[anchors])),max_lateral_surface_distance_m=maximum,logical_grid_complete=True,max_displacement_m=float(np.linalg.norm(q-p,axis=1).max()),physical_turbo_geometry_present=False,solver_admission_granted=False)
