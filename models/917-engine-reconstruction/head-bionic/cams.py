"""Roller-follower cam surfaces and an explicit hypothetical 12-cylinder cycle."""
import math
from optimize import VT, law_parameters


def cycles():
    phases=[0,120,240,60,180,300]
    result=[]
    for k,tdc in enumerate(range(0,360,60)):
        matches=[(bank,i,p) for bank in (-1,1) for i,p in enumerate(phases) if ((0 if bank==1 else 180)-p)%360==tdc]
        desired=1 if k%2==0 else -1
        matches.sort(key=lambda q:q[0]!=desired)
        for j,(bank,i,p) in enumerate(matches):
            fire=tdc+360*j
            result.append({"bank":bank,"pair_index":i,"crank_phase_deg":p,
                           "fire_tdc_deg":fire,"overlap_tdc_deg":(fire+360)%720})
    if sorted(r["fire_tdc_deg"] for r in result)!=list(range(0,720,60)):
        raise ValueError("Hypothetical firing-cycle assignment failed")
    return result


def cam_law(role,selected):
    return VT.CamLaw.from_params(law_parameters(role,selected["max_lift_mm"],selected["main_duration_deg"],selected["centreline_deg"]))


def section(role,selected,bank,overlap):
    import numpy as np
    law=cam_law(role,selected)
    sign=1 if role=="intake" else -1
    psi=math.atan2(-sign*math.sin(math.radians(8)),-bank*math.cos(math.radians(8)))
    theta=np.arange(720)*math.tau/720
    phi=-2*(theta-psi)-math.radians(overlap)
    r=28+law.cam_derivatives(phi)*1000
    dr=-2*law.cam_derivatives(phi,1)*1000
    ddr=4*law.cam_derivatives(phi,2)*1000
    px=r*np.cos(theta);py=r*np.sin(theta)
    dx=dr*np.cos(theta)-r*np.sin(theta);dy=dr*np.sin(theta)+r*np.cos(theta)
    norm=np.hypot(dx,dy)
    polygon=np.column_stack((px-8*dy/norm,py+8*dx/norm))
    curvature=(r*r+2*dr*dr-r*ddr)/((r*r+dr*dr)**1.5)
    positive=curvature>0
    radius=float(np.min(1/curvature[positive]))
    pressure=float(np.degrees(np.arctan(np.abs(dr/r))).max())
    if radius<=8 or pressure>35:
        raise ValueError("Cam undercut or pressure-angle design screen failed")
    return polygon,{"max_ideal_pressure_angle_deg":pressure,"minimum_positive_pitch_curvature_radius_mm":radius,
                    "roller_radius_mm":8,"base_radius_mm":20,"geometry":"inward_normal_offset_of_roller_pitch_curve"}


def extrude(polygon,x0,x1):
    import numpy as np
    import trimesh
    n=len(polygon)
    vertices=np.vstack((np.column_stack((np.full(n,x0),polygon)),np.column_stack((np.full(n,x1),polygon)),[[x0,0,0],[x1,0,0]]))
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces.extend([[2*n,j,i],[2*n+1,n+i,n+j],[i,j,n+j],[i,n+j,n+i]])
    mesh=trimesh.Trimesh(vertices,faces,process=False)
    if not mesh.is_volume:
        raise ValueError("Cam extrusion is not a positive closed surface")
    return mesh
