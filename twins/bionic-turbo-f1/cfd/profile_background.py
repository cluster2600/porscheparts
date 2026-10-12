#!/usr/bin/env python3
"""Build a structured background around the frozen profile; no physical-wall meshing."""
import json
import math
from pathlib import Path
import numpy as np
from prepare_case import header, sha, IMAGE


def simplify(nodes):
    a=np.asarray(nodes,dtype=float)
    if a.ndim!=2 or a.shape[1]!=2 or len(a)<2 or not np.isfinite(a).all() or np.any(np.diff(a[:,0])<=0) or np.any(a[:,1]<=0):
        raise ValueError('Finite increasing axial stations with positive radii required')
    selected=[0];start=0
    while start<len(a)-1:
        end=start+1
        while end+1<len(a):
            candidate=end+1
            r=np.interp(a[start:candidate+1,0],a[[start,candidate],0],a[[start,candidate],1])
            if np.max(np.abs(r-a[start:candidate+1,1]))>1e-12:break
            end=candidate
        selected.append(end);start=end
    return a[selected]


def validate_profile(nodes,reports,clearance):
    a=np.asarray(nodes,dtype=float);separations=[];cosine=math.cos(math.pi/128)
    if not np.isfinite(clearance) or clearance<=0:raise ValueError('Positive clearance required')
    for report in reports:
        for i in range(3,359):
            band=report['bands'][i];lo,hi=band['z_low_mm'],band['z_high_mm']
            if lo<a[0,0] or hi>a[-1,0]:raise ValueError('Profile does not cover source band')
            samples=np.r_[lo,a[(a[:,0]>lo)&(a[:,0]<hi),0],hi]
            r=np.interp(samples,a[:,0],a[:,1])
            separations.append(min(r.min()*cosine-band['rotor_upper_mm'],band['stator_lower_mm']-r.max()))
    if not separations or min(separations)<clearance:raise ValueError('Simplified profile violates a frozen full-band bound')
    return float(min(separations))


def mesh_text(nodes,outer_radius_mm,z_bounds_mm,width_mm):
    a=np.asarray(nodes,dtype=float);simplify(a)
    if not z_bounds_mm[0]<-4<33<z_bounds_mm[1] or a[0,0]!=-4 or a[-1,0]!=33 or not 0<width_mm<a[:,1].min()/2 or outer_radius_mm<=a[:,1].max()+width_mm:
        raise ValueError('Background must enclose the complete declared zone')
    # shortcut: fixed 128-sector topology; finer sectors require a new native geometry audit.
    sectors=128;angular=sectors//4;core_half=a[:,1].min()/4
    stations=sorted(set([*a[:,0],-4.,-3.75,-3.5,33.,*z_bounds_mm]))
    radii=np.interp(stations,a[:,0],a[:,1]);vertices=[];arcs=[]
    for k,(z,r) in enumerate(zip(stations,radii)):
        for ring in range(5):
            for q in range(4):
                theta=math.pi/4+q*math.pi/2
                radius=core_half*math.sqrt(2) if ring==0 else (r-width_mm,r,r+width_mm,outer_radius_mm)[ring-1]
                vertices.append((radius*math.cos(theta)/1000,radius*math.sin(theta)/1000,z/1000))
                if ring:
                    middle=theta+math.pi/4
                    arcs.append((k*20+ring*4+q,k*20+ring*4+(q+1)%4,(radius*math.cos(middle)/1000,radius*math.sin(middle)/1000,z/1000)))
    blocks=[];boundary=[];expected=rotating=0
    radial_counts=(32,1,1,math.ceil((outer_radius_mm-float(radii.min())-width_mm)/1.2))
    for k in range(len(stations)-1):
        axial=max(1,math.ceil((stations[k+1]-stations[k])/.8))
        active=stations[k]>=-4 and stations[k+1]<=33
        core=[k*20+j for j in range(4)]+[(k+1)*20+j for j in range(4)]
        entries=[(core,(angular,angular,axial),active)]
        for ring,radial in enumerate(radial_counts):
            for q in range(4):
                j=(q+1)%4;bottom=[k*20+ring*4+q,k*20+(ring+1)*4+q,k*20+(ring+1)*4+j,k*20+ring*4+j]
                v=bottom+[i+20 for i in bottom];entries.append((v,(radial,angular,axial),active and ring<2))
                if ring==3:boundary.append([v[i] for i in (1,2,6,5)])
        for v,counts,zone in entries:
            n=math.prod(counts);expected+=n;rotating+=n if zone else 0
            blocks.append('hex ('+' '.join(map(str,v))+')'+(' rotorZone' if zone else '')+' ('+' '.join(map(str,counts))+') simpleGrading (1 1 1)')
            if k==0:boundary.append([v[i] for i in (0,3,2,1)])
            if k==len(stations)-2:boundary.append([v[i] for i in (4,5,6,7)])
    vector=lambda v:'('+' '.join(format(x,'.17g') for x in v)+')'
    text=header('blockMeshDict')+'vertices ('+' '.join(map(vector,vertices))+');\nblocks ('+'\n'.join(blocks)+');\nedges ('+'\n'.join(f'arc {i} {j} {vector(p)}' for i,j,p in arcs)+');\nboundary (background {type patch; faces ('+' '.join(map(vector,boundary))+');});\n'
    return text,dict(stations_z_mm=stations,interface_radii_mm=radii.tolist(),sectors=sectors,core_half_width_mm=core_half,radial_cell_counts=radial_counts,expected_cells=expected,expected_rotating_cells=rotating,blocks=len(blocks),outer_radius_mm=outer_radius_mm)


def prepare(parent,geometry_path,profile_paths,output):
    g=json.loads(geometry_path.read_text());prior=json.loads((parent/'case-manifest.json').read_text())
    if g['source_sha256']!=sha(Path(__file__).with_name('audit_rear_interface.py')) or not g['geometric_interface_candidate_verified'] or g['variants']['baseline']['surface_sha256']!=prior['surface']['sha256']:
        raise ValueError('Frozen geometry and baseline source required')
    if [sha(p) for p in profile_paths]!=g['profile_input_sha256']:raise ValueError('Frozen band reports required')
    reports=[json.loads(p.read_text()) for p in profile_paths];spec=g['profile'];nodes=simplify(spec['nodes_z_radius_mm'])
    clearance=validate_profile(nodes,reports,spec['retained_radial_clearance_mm'])
    lo,hi=np.array(prior['surface']['bounds_m'])*1000
    radius=math.hypot(max(abs(lo[0]),abs(hi[0])),max(abs(lo[1]),abs(hi[1])))+3
    text,mesh=mesh_text(nodes,radius,(float(lo[2]-3),float(hi[2]+3)),spec['retained_radial_clearance_mm']/2)
    output.mkdir(parents=True,exist_ok=False);(output/'system').mkdir()
    files={'system/blockMeshDict':text,'system/controlDict':header('controlDict')+'application blockMesh; startFrom startTime; startTime 0; stopAt endTime; endTime 0; deltaT 1; writeControl timeStep; writeInterval 1; writeFormat ascii; writePrecision 16; writeCompression off; runTimeModifiable false;\n',
           'system/fvSchemes':header('fvSchemes')+'ddtSchemes {default steadyState;} gradSchemes {default Gauss linear;} divSchemes {default none;} laplacianSchemes {default Gauss linear corrected;} interpolationSchemes {default linear;} snGradSchemes {default corrected;}\n',
           'system/fvSolution':header('fvSolution')+'solvers {}\n'}
    for name,content in files.items():(output/name).write_text(content)
    manifest=dict(schema='bionic-turbo-profile-background/v1',source_sha256=sha(Path(__file__)),image=IMAGE,parent_manifest_sha256=sha(parent/'case-manifest.json'),surface=prior['surface'],geometry_report_sha256=sha(geometry_path),profile_input_sha256=[sha(p) for p in profile_paths],
                  original_profile_stations=len(spec['nodes_z_radius_mm']),simplified_profile_nodes_mm=nodes.tolist(),verified_radial_clearance_mm=clearance,mesh=mesh,
                  file_sha256={name:sha(output/name) for name in files},native_write_precision=16,physical_walls_meshed=False,solver_admission_granted=False,performance_ranking_authorized=False)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n');return manifest
