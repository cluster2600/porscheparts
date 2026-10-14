"""Refine one synthetic annular sector azimuthally while retaining its wall planes."""
import math
import numpy as np
from audit_frame_interface import face_geometry
from prepare_case import header


def sector_grid(points,nodes_mm,width_mm,sectors,factor):
    p=np.asarray(points,float);nodes=np.asarray(nodes_mm,float)/1000;width=width_mm/1000
    if type(factor)is not int or factor<1 or type(sectors)is not int or sectors<3 or not np.isfinite(p).all():raise ValueError('Finite native points and positive integer refinement required')
    stations=np.sort(np.r_[nodes[:,0],(nodes[:-1,0]+nodes[1:,0])/2]);angle=np.arctan2(p[:,1],p[:,0]);angular=np.rint(angle*sectors/np.pi).astype(int)%(2*sectors)
    if np.max(np.abs(np.angle(np.exp(1j*(angle-angular*np.pi/sectors)))))>1e-12:raise ValueError('Source rays differ from pinned grid')
    axial=np.abs(p[:,2,None]-stations).argmin(axis=1);chord=np.where(angular%2,math.cos(math.pi/sectors),1.)
    offset=np.linalg.norm(p[:,:2],axis=1)/chord-np.interp(p[:,2],nodes[:,0],nodes[:,1]);radial=np.abs(offset[:,None]-np.linspace(-width,width,5)).argmin(axis=1)
    addresses=np.column_stack((axial,radial,angular))
    if len(p)!=len(stations)*5*2*sectors or len(np.unique(addresses,axis=0))!=len(p):raise ValueError('Source tensor grid is incomplete')
    lookup={tuple(a):v for a,v in zip(addresses,p)};coarse=np.array([[[lookup[k,r,a] for a in range(3)] for r in range(5)] for k in range(len(stations))])
    q=np.empty((len(stations),5,2*factor+1,3))
    for j in range(2*factor+1):
        left=min(j//factor,1);t=(j-left*factor)/factor;q[:,:,j]=(1-t)*coarse[:,:,left]+t*coarse[:,:,left+1]
        if j%factor:
            v=q[:,2,j];radius=np.interp(v[:,2],nodes[:,0],nodes[:,1]);v[:,:2]*=(radius/np.linalg.norm(v[:,:2],axis=1))[:,None]
    if not np.array_equal(q[:,:,::factor],coarse):raise ValueError('Source anchors moved')
    max_wall_error=0.
    for k in range(len(stations)-1):
        for r in (0,4):
            for a in range(2):
                quad=coarse[[k,k,k+1,k+1],[r]*4,[a,a+1,a+1,a]];c,s=face_geometry(quad);unit=s/np.linalg.norm(s)
                v=q[k:k+2,r,a*factor:(a+1)*factor+1].reshape(-1,3);error=float(np.abs((v-c)@unit).max());max_wall_error=max(max_wall_error,error)
                if error>1e-12:raise ValueError('Wall plane changed')
    return q,dict(angular_factor=factor,source_anchors_unchanged=True,max_wall_plane_error_m=max_wall_error,angular_extent_rad=2*np.pi/sectors,synthetic_angular_cut_walls=True)


def hex_topology(grid):
    nz,nr,na,_=grid.shape;pending={};internal=[];boundary=[];zone=[];cell=0
    index=lambda k,r,a:(k*nr+r)*na+a
    for k in range(nz-1):
        for r in range(nr-1):
            for a in range(na-1):
                v=[index(k,r,a),index(k,r+1,a),index(k,r+1,a+1),index(k,r,a+1),index(k+1,r,a),index(k+1,r+1,a),index(k+1,r+1,a+1),index(k+1,r,a+1)]
                for order in ((0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(0,1,5,4),(3,7,6,2)):
                    f=[v[i] for i in order];key=tuple(sorted(f))
                    if key in pending:
                        prior,o=pending.pop(key)
                        if {(prior[i],prior[(i+1)%4]) for i in range(4)}!={(f[(i+1)%4],f[i]) for i in range(4)}:raise ValueError('Inconsistent face orientation')
                        internal.append((prior,o,cell))
                    else:pending[key]=(f,cell)
                if r<2:zone.append(cell)
                cell+=1
    internal.sort(key=lambda x:(x[1],x[2]));boundary=list(pending.values())
    return [x[0] for x in internal]+[x[0] for x in boundary],np.array([x[1] for x in internal]+[x[1] for x in boundary]),np.array([x[2] for x in internal],int),np.array(zone,int)


def write_mesh(path,points,faces,owner,neighbour,zone):
    path.mkdir(parents=True,exist_ok=False)
    def write(name,kind,entries):(path/name).write_text(header(name,kind)+str(len(entries))+'\n(\n'+'\n'.join(entries)+'\n)\n')
    write('points','vectorField',['('+' '.join(format(x,'.17g') for x in v)+')' for v in points]);write('faces','faceList',[str(len(f))+'('+' '.join(map(str,f))+')' for f in faces]);write('owner','labelList',list(map(str,owner)));write('neighbour','labelList',list(map(str,neighbour)))
    (path/'boundary').write_text(header('boundary','polyBoundaryMesh')+f'1\n(\nwalls {{type wall; nFaces {len(faces)-len(neighbour)}; startFace {len(neighbour)};}}\n)\n')
    (path/'cellZones').write_text(header('cellZones','regIOobject')+'1\n(\nrotorZone {type cellZone; cellLabels List<label>\n'+str(len(zone))+'\n(\n'+'\n'.join(map(str,zone))+'\n);}\n)\n')
    for name in ('faceZones','pointZones'):(path/name).write_text(header(name,'regIOobject')+'0()\n')
