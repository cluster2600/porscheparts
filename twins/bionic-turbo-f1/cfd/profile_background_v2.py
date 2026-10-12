#!/usr/bin/env python3
"""Use half-millimetre profile knots under the unchanged frozen clearance constraints."""
import json,math
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
import profile_background as previous
from prepare_case import sha


def constrained_profile(reports,spec):
    z=np.r_[np.arange(-3.5,32.1,.5),32.1];n=len(z);matrix=[];rhs=[]
    clearance=spec['retained_radial_clearance_mm'];cosine=math.cos(math.pi/128)
    for i in range(3,359):
        bands=[r['bands'][i] for r in reports]
        low=(max(r['rotor_upper_mm'] for r in bands)+clearance+1e-8)/cosine
        high=min(r['stator_lower_mm'] for r in bands)-clearance-1e-8
        for x in (bands[0]['z_low_mm'],bands[0]['z_high_mm']):
            j=min(n-2,max(0,np.searchsorted(z,x,side='right')-1));w=(x-z[j])/(z[j+1]-z[j]);row=np.zeros(n+1);row[j]=1-w;row[j+1]=w
            matrix.extend((row,-row));rhs.extend((high,-low))
    for j,dz in enumerate(np.diff(z)):
        for sign in (-1,1):
            row=np.zeros(n+1);row[j]=-sign;row[j+1]=sign;row[-1]=-dz;matrix.append(row);rhs.append(0)
    objective=np.zeros(n+1);objective[-1]=1
    bounds=[(0,None)]*(n+1);bounds[0]=(32,32);bounds[-2]=(spec['nodes_z_radius_mm'][-1][1],)*2
    result=linprog(objective,A_ub=matrix,b_ub=rhs,bounds=bounds,method='highs')
    if not result.success or not np.isfinite(result.x).all():raise ValueError('No feasible coarse profile: '+result.message)
    nodes=np.vstack(([-4,32],[-3.75,32],np.column_stack((z,result.x[:-1])),[33,result.x[-2]]))
    nodes=previous.simplify(nodes)
    verified=previous.validate_profile(nodes,reports,clearance)
    return nodes,verified


def prepare(parent,geometry_path,profile_paths,output):
    manifest=previous.prepare(parent,geometry_path,profile_paths,output)
    g=json.loads(geometry_path.read_text());reports=[json.loads(p.read_text()) for p in profile_paths]
    nodes,clearance=constrained_profile(reports,g['profile']);old=manifest['mesh']
    text,mesh=previous.mesh_text(nodes,old['outer_radius_mm'],(old['stations_z_mm'][0],old['stations_z_mm'][-1]),g['profile']['retained_radial_clearance_mm']/2)
    (output/'system/blockMeshDict').write_text(text)
    manifest.update(source_sha256=sha(Path(__file__)),previous_source_sha256=sha(Path(previous.__file__)),simplified_profile_nodes_mm=nodes.tolist(),verified_radial_clearance_mm=clearance,mesh=mesh,
                    profile_construction='New LP with 0.5 mm knots and unchanged rear/front radii; independently rechecked against every frozen 0.1 mm band for both variants. Physical surfaces and quality criteria unchanged.')
    manifest['file_sha256']['system/blockMeshDict']=sha(output/'system/blockMeshDict')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n');return manifest
