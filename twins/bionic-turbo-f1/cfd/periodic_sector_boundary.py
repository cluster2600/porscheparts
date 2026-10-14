"""Pair only the angular cuts of the pinned local sector, retaining face geometry."""
import numpy as np
from audit_frame_interface import face_geometry


def paired_cuts(points,faces,internal,angle,tolerance=1e-12):
    p=np.asarray(points,float)
    if not np.isfinite(p).all() or not 0<angle<np.pi or not 0<internal<len(faces):raise ValueError('Invalid sector')
    c,s=np.cos(angle),np.sin(angle);rotation=np.array([[c,-s,0],[s,c,0],[0,0,1]])
    lower=[];upper=[];walls=[]
    for i in range(internal,len(faces)):
        v=p[faces[i]];a=np.abs(v[:,1]).max()<tolerance;b=np.abs(v@np.array([-s,c,0])).max()<tolerance
        if a and b:raise ValueError('Ambiguous cut face')
        (lower if a else upper if b else walls).append(i)
    key=lambda i:(round(float(p[faces[i],2].mean()),12),round(float(np.linalg.norm(p[faces[i],:2],axis=1).mean()),12))
    lower.sort(key=key);upper.sort(key=key)
    if not lower or len(lower)!=len(upper) or len(set(map(key,lower)))!=len(lower):raise ValueError('Incomplete or ambiguous pairing')
    errors=[];areas=[]
    for i,j in zip(lower,upper):
        a=p[faces[i]]@rotation.T;b=p[faces[j]];d=np.linalg.norm(a[:,None]-b[None,:],axis=2)
        if len(a)!=len(b) or len(np.unique(d.argmin(axis=1)))!=len(a) or d.min(axis=1).max()>tolerance:raise ValueError('Unmatched rotated vertices')
        _,u=face_geometry(p[faces[i]]);_,v=face_geometry(b);error=np.linalg.norm(u@rotation.T+v)
        if error>1e-10*max(np.linalg.norm(u),np.linalg.norm(v)):raise ValueError('Cut normals do not oppose after rotation')
        errors.append(float(d.min(axis=1).max()));areas.append(float(error))
    order=np.array(list(range(internal))+walls+lower+upper,int)
    if len(np.unique(order))!=len(faces):raise ValueError('Incomplete face permutation')
    return order,dict(walls=len(walls),paired_faces=len(lower),rotation_matrix=rotation.tolist(),max_vertex_error_m=max(errors),max_area_error_m2=max(areas))
