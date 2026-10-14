#!/usr/bin/env python3
"""Fail-closed projection of uniform quad interfaces on a piecewise affine profile."""
import json,re
from pathlib import Path
import numpy as np
from audit_diagnostic import ascii_list
from audit_frame_interface import face_geometry
from audit_frame_interface_v2 import cell_flags
from run_case import ascii_faces
from prepare_case import sha


def read_mesh(case):
    receipt=json.loads((case/'report.json').read_text());mesh=case/'constant/polyMesh'
    for name in ('points','faces','owner','neighbour','cellZones','boundary'):
        if sha(mesh/name)!=receipt['output_sha256']['constant/polyMesh/'+name]:raise ValueError('Native mesh changed')
    points=ascii_list((mesh/'points').read_text(),True);faces=[np.asarray(f,dtype=int) for f in ascii_faces((mesh/'faces').read_text())]
    owner=ascii_list((mesh/'owner').read_text()).astype(int);neighbour=ascii_list((mesh/'neighbour').read_text()).astype(int)
    match=re.search(r'rotorZone\s*\{.*?cellLabels\s+List<label>\s*(\d+)\s*\((.*?)\)',(mesh/'cellZones').read_text(),re.S)
    if not match:raise ValueError('Missing rotor zone')
    zone=np.fromstring(match[2],sep=' ',dtype=int)
    if len(zone)!=int(match[1]):raise ValueError('Invalid rotor zone count')
    active=cell_flags(owner,neighbour,zone);selected=np.flatnonzero(active[owner[:len(neighbour)]]^active[neighbour])
    return points,faces,selected,len(neighbour)


def metrics(points,faces,omega):
    normal=[];planarity=[]
    for face in faces:
        p=points[list(face)];c,a=face_geometry(p);unit=a/np.linalg.norm(a)
        normal.append(abs(np.dot(np.array([-c[1],c[0],0])*omega,unit)))
        planarity.append(float(np.max(np.abs((p-p[0])@unit))))
    if not normal:raise ValueError('Nonempty interface required')
    return dict(faces=len(faces),max_normal_frame_speed_m_s=max(normal),max_plane_distance_m=max(planarity))


def project(points,faces,nodes_mm,omega):
    p=np.asarray(points,dtype=float);nodes=np.asarray(nodes_mm,dtype=float)/1000
    if p.ndim!=2 or p.shape[1]!=3 or not np.isfinite(p).all() or nodes.ndim!=2 or nodes.shape[1]!=2 or len(nodes)<2 or not np.isfinite(nodes).all() or np.any(np.diff(nodes[:,0])<=0) or np.any(nodes[:,1]<=0) or not np.isfinite(omega):raise ValueError('Finite points and increasing positive profile required')
    if not faces or any(len(f)!=4 or len(set(f))!=4 for f in faces):raise ValueError('Uniform quadrilateral interface required')
    ids=np.unique(np.concatenate(faces));q=p.copy();z=p[ids,2];radius=np.linalg.norm(p[ids,:2],axis=1)
    if z.min()<nodes[0,0]-1e-14 or z.max()>nodes[-1,0]+1e-14 or radius.min()<=0:raise ValueError('Interface outside supported profile')
    for face in faces:
        v=p[list(face)];levels=np.sort(v[:,2]);angles=np.arctan2(v[:,1],v[:,0]);centre=np.angle(np.exp(1j*angles).mean());angles=np.sort(np.angle(np.exp(1j*(angles-centre))))
        if abs(levels[0]-levels[1])>1e-14 or abs(levels[2]-levels[3])>1e-14 or levels[2]-levels[1]<=1e-14 or abs(angles[0]-angles[1])>1e-12 or abs(angles[2]-angles[3])>1e-12 or angles[2]-angles[1]<=1e-12:raise ValueError('Quad is not a pair of axial levels and angular rays')
        if np.any((nodes[:,0]>levels[0]+1e-14)&(nodes[:,0]<levels[-1]-1e-14)):raise ValueError('Face crosses an affine profile segment')
    q[ids,:2]*=(np.interp(z,nodes[:,0],nodes[:,1])/radius)[:,None]
    after=metrics(q,faces,omega)
    if after['max_plane_distance_m']>1e-12 or after['max_normal_frame_speed_m_s']>=1e-8:raise ValueError('Projected interface is not planar and tangent')
    return q,dict(before=metrics(p,faces,omega),after=after,moved_points=int(np.count_nonzero(np.linalg.norm(q-p,axis=1)>0)),max_displacement_m=float(np.linalg.norm(q-p,axis=1).max()),solver_admission_granted=False)
