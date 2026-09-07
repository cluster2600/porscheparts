#!/usr/bin/env python3
"""Audit an exact-boundary polynomial bubble, without modifying any CAD.

The displacement is delta * E(u,v)^2 * F(S0(u,v))^2, normalized at the
target. Here E=u(1-u)v(1-v), S0 is bilinear and F is a cylinder equation.
The degree is at most (8,8). Numerical sampling is not a global proof.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import sys


def multiply(a, b):
    result = {}
    for (i,j),x in a.items():
        for (k,l),y in b.items():
            key = (i+k,j+l)
            result[key] = result.get(key,0.)+x*y
    return result


def evaluate(a, u, v):
    return sum(c*u**i*v**j for (i,j),c in a.items())


def derivative(a, axis):
    return {(i-1,j) if axis==0 else (i,j-1):c*(i if axis==0 else j)
            for (i,j),c in a.items() if (i if axis==0 else j)>0}


def bernstein_coefficients(a, n=8, m=8):
    return [[sum(c*math.comb(i,k)/math.comb(n,k)*math.comb(j,l)/math.comb(m,l)
                  for (k,l),c in a.items() if k<=i and l<=j)
             for j in range(m+1)] for i in range(n+1)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def search_localized_exponents(u, v, f, ut, vt, ft, max_exponent=12):
    """Compare positive factored fields on supplied points; not a global bound."""
    import numpy as np
    pairs = [(p,q) for p in range(2,max_exponent+1) for q in range(2,max_exponent+1)]
    uf = np.array([(u/ut)**p*((1-u)/(1-ut))**q for p,q in pairs])
    vf = np.array([(v/vt)**r*((1-v)/(1-vt))**s for r,s in pairs])
    cylinder_factor_squared = (f/ft)**2
    best = None
    for index,(p,q) in enumerate(pairs):
        maxima = .85*np.max(vf*(uf[index]*cylinder_factor_squared)[None,:],axis=1)
        for j,(r,s) in enumerate(pairs):
            key = (float(maxima[j]),p+q+r+s,p,q,r,s)
            if best is None or key < best: best = key
    return {'exponents':list(best[2:]),'max_abs_D_scan_units':best[0],
            'searched_fields':len(pairs)**2}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source-step','trial-report','patches','helpers','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--localized-search',action='store_true')
    a = p.parse_args()
    if a.output.exists(): raise FileExistsError(a.output)
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    r = json.loads(a.trial_report.read_text()); patches = json.loads(a.patches.read_text())
    if digest(a.source_step)!=r['source_sha256']['step'] or patches['source_sha256']!=r['source_sha256']:
        raise ValueError('source provenance mismatch')
    import numpy as np
    sys.path.insert(0,str(a.helpers))
    from audit_brep_f42 import read_step
    from repair_topology_f42_1 import indexed
    from OCP.BRep import BRep_Tool
    from OCP.BRepTools import BRepTools,BRepTools_WireExplorer
    from OCP.BRepAdaptor import BRepAdaptor_Curve2d,BRepAdaptor_Surface
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
    from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_IN,TopAbs_ON
    from OCP.TopoDS import TopoDS
    from OCP.GeomAbs import GeomAbs_Cylinder
    from OCP.gp import gp_Pnt,gp_Pnt2d
    shape = read_step(a.source_step)[0]; faces = indexed(shape,TopAbs_FACE)
    face = TopoDS.Face_s(faces.FindKey(r['selected_face_private'])); surface = BRep_Tool.Surface_s(face)
    if (surface.UDegree(),surface.VDegree(),surface.NbUPoles(),surface.NbVPoles()) != (1,1,2,2):
        raise ValueError('source is not a single bilinear patch')
    if surface.IsURational() or surface.IsVRational(): raise ValueError('rational source unsupported')
    u0,u1,v0,v1 = surface.Bounds(); anchors = []; noniso = []
    w = BRepTools_WireExplorer(BRepTools.OuterWire_s(face),face)
    while w.More():
        edge = w.Current(); curve = BRepAdaptor_Curve2d(edge,face)
        uv = np.array([[q.X(),q.Y()] for q in [curve.Value(float(t)) for t in
                       np.linspace(curve.FirstParameter(),curve.LastParameter(),121)]])
        unit = (uv-np.array([u0,v0]))/np.array([u1-u0,v1-v0]); span = np.ptp(unit,axis=0)
        anchors.append((edge,unit))
        if min(span)>1e-9: noniso.append(len(anchors)-1)
        w.Next()
    if len(noniso)!=1: raise ValueError('exactly one nonisoparametric boundary required')
    target_edge = anchors[noniso[0]][0]; neighbors = []
    for i in range(1,faces.Extent()+1):
        if i==r['selected_face_private']: continue
        neighbor = TopoDS.Face_s(faces.FindKey(i))
        if indexed(neighbor,TopAbs_EDGE).Contains(target_edge): neighbors.append((i,neighbor))
    if len(neighbors)!=1: raise ValueError('boundary neighbor not unique')
    neighbor_id,neighbor = neighbors[0]; adaptor = BRepAdaptor_Surface(neighbor)
    report = {'schema':'m64-reference-implicit-bubble-feasibility/v1',
              'input_sha256':{'source':digest(a.source_step),'trial_report':digest(a.trial_report),'patches':digest(a.patches)},
              'neighbor_type':str(adaptor.GetType()),'neighbor_face_private':neighbor_id,
              'cad_modified':False,'manufacturing_authorized':False,'field_accepted':False}
    if adaptor.GetType()!=GeomAbs_Cylinder:
        report['status']='rejected_neighbor_not_analytic_cylinder'
    else:
        cylinder = adaptor.Cylinder(); loc = cylinder.Location(); axis = cylinder.Axis().Direction()
        center = np.array([loc.X(),loc.Y(),loc.Z()]); direction = np.array([axis.X(),axis.Y(),axis.Z()]); radius = cylinder.Radius()
        poles = np.array([[[surface.Pole(i,j).X(),surface.Pole(i,j).Y(),surface.Pole(i,j).Z()]
                           for j in (1,2)] for i in (1,2)])
        coeff = {(0,0):poles[0,0],(1,0):poles[1,0]-poles[0,0],(0,1):poles[0,1]-poles[0,0],
                 (1,1):poles[1,1]-poles[1,0]-poles[0,1]+poles[0,0]}
        q = {key:value.copy() for key,value in coeff.items()}; q[(0,0)]-=center
        q = {key:value-direction*np.dot(value,direction) for key,value in q.items()}
        f = {(0,0):-1.}
        for component in range(3):
            part = {key:float(value[component]/radius) for key,value in q.items()}
            for key,value in multiply(part,part).items(): f[key]=f.get(key,0.)+value
        edge_factor = multiply({(2,0):1.,(3,0):-2.,(4,0):1.},{(0,2):1.,(0,3):-2.,(0,4):1.})
        bubble = multiply(edge_factor,multiply(f,f))
        probe = next(p for patch in patches['patches_private'] for p in patch['probes_private'] if p['index']==r['probe_private'])
        entry = np.array(probe['entry_xyz_scan_units']); normal = -np.array(probe['direction'])
        projection = GeomAPI_ProjectPointOnSurf(gp_Pnt(*entry),surface); uu,vv = projection.LowerDistanceParameters()
        ut,vt = (uu-u0)/(u1-u0),(vv-v0)/(v1-v0)
        target_factor = float(evaluate(bubble,ut,vt)); target_f = float(evaluate(f,ut,vt))
        delta = .85
        report.update({'normalized_target_private':[ut,vt], 'F_target_dimensionless':target_f,
                       'bubble_target':target_factor,
                       'target_surface_projection_error':projection.LowerDistance(),
                       'displacement_limit_scan_units':1.,'target_displacement_scan_units':delta,
                       'F_definition':'squared_distance_to_cylinder_axis_divided_by_R_squared_minus_one'})
        if not math.isfinite(target_factor) or target_factor<=1e-20:
            report['status']='rejected_singular_target_normalization'
        else:
            report['normalization_C']=delta/target_factor
            amplitude = {key:delta*value/target_factor for key,value in bubble.items()}
            du,dv = derivative(amplitude,0),derivative(amplitude,1)
            boundary = []
            for index,(_,uv) in enumerate(anchors):
                u,v = uv.T
                boundary.append({'is_cylinder_trim':index==noniso[0],
                     'max_abs_F_dimensionless':float(np.max(np.abs(evaluate(f,u,v)))),
                     'max_abs_displacement_scan_units':float(np.max(np.abs(evaluate(amplitude,u,v)))),
                     'max_abs_dD_du':float(np.max(np.abs(evaluate(du,u,v)))),
                     'max_abs_dD_dv':float(np.max(np.abs(evaluate(dv,u,v))))})
            report['boundary_samples_121']=boundary
            grids=[]
            for count in (41,81):
                values=np.linspace(0,1,count); us,vs=np.meshgrid(values,values,indexing='ij'); mask=np.zeros_like(us,dtype=bool)
                for i in range(count):
                    for j in range(count):
                        state=BRepClass_FaceClassifier(face,gp_Pnt2d(u0+us[i,j]*(u1-u0),v0+vs[i,j]*(v1-v0)),1e-9).State()
                        mask[i,j]=state in (TopAbs_IN,TopAbs_ON)
                d=evaluate(amplitude,us,vs); ds=evaluate(du,us,vs); dt=evaluate(dv,us,vs)
                su=coeff[(1,0)]+vs[...,None]*coeff[(1,1)]; sv=coeff[(0,1)]+us[...,None]*coeff[(1,1)]
                before=np.cross(su,sv); after=np.cross(su+ds[...,None]*normal,sv+dt[...,None]*normal)
                orientation=np.sum(before*after,axis=-1)/np.sum(before*before,axis=-1)
                grids.append({'grid_size':count,'retained_points':int(mask.sum()),
                              'max_abs_D_scan_units':float(np.max(np.abs(d[mask]))),
                              'max_abs_dD_du':float(np.max(np.abs(ds[mask]))),'max_abs_dD_dv':float(np.max(np.abs(dt[mask]))),
                              'min_orientation_dot_ratio':float(np.min(orientation[mask])),
                              'nonpositive_orientation_count':int(np.sum(orientation[mask]<=0))})
            coefficients=np.array(bernstein_coefficients(amplitude))
            report.update({'grids_trimmed_domain':grids,
                 'whole_parameter_rectangle_Bernstein_abs_bound_float':float(np.max(np.abs(coefficients))),
                 'Bernstein_bound_not_interval_rounded':True,'polynomial_bidegree':[8,8],
                 'sampled_checks_only_not_global_geometry_proof':True,
                 'status':'rejected_naive_field_exceeds_displacement_or_orientation_limit'
                    if any(g['max_abs_D_scan_units']>1. or g['nonpositive_orientation_count'] for g in grids)
                    else 'sampled_field_candidate_requires_kernel_and_corridor_audit'})
            if a.localized_search:
                best=search_localized_exponents(us[mask],vs[mask],evaluate(f,us[mask],vs[mask]),ut,vt,target_f)
                p,q,r,s=best['exponents']
                factor_target=ut**p*(1-ut)**q*vt**r*(1-vt)**s*target_f**2
                dense=[]
                for count in (81,161):
                    uu,vv=np.meshgrid(np.linspace(0,1,count),np.linspace(0,1,count),indexing='ij')
                    inside=np.zeros_like(uu,dtype=bool)
                    for i in range(count):
                        for j in range(count):
                            state=BRepClass_FaceClassifier(face,gp_Pnt2d(u0+uu[i,j]*(u1-u0),v0+vv[i,j]*(v1-v0)),1e-9).State()
                            inside[i,j]=state in (TopAbs_IN,TopAbs_ON)
                    fu,fv=derivative(f,0),derivative(f,1)
                    fvalue=evaluate(f,uu,vv)
                    eu=uu**p*(1-uu)**q; ev=vv**r*(1-vv)**s
                    deu=p*uu**(p-1)*(1-uu)**q-q*uu**p*(1-uu)**(q-1)
                    dev=r*vv**(r-1)*(1-vv)**s-s*vv**r*(1-vv)**(s-1)
                    c=.85/factor_target
                    values=c*eu*ev*fvalue**2
                    ds=c*ev*(deu*fvalue**2+2*eu*fvalue*evaluate(fu,uu,vv))
                    dt=c*eu*(dev*fvalue**2+2*ev*fvalue*evaluate(fv,uu,vv))
                    su=coeff[(1,0)]+vv[...,None]*coeff[(1,1)]; sv=coeff[(0,1)]+uu[...,None]*coeff[(1,1)]
                    before=np.cross(su,sv); after=np.cross(su+ds[...,None]*normal,sv+dt[...,None]*normal)
                    orientation=np.sum(before*after,axis=-1)/np.sum(before*before,axis=-1)
                    dense.append({'grid_size':count,'retained_points':int(inside.sum()),
                                  'max_abs_D_scan_units':float(np.max(np.abs(values[inside]))),
                                  'max_abs_dD_du':float(np.max(np.abs(ds[inside]))),
                                  'max_abs_dD_dv':float(np.max(np.abs(dt[inside]))),
                                  'min_orientation_dot_ratio':float(np.min(orientation[inside])),
                                  'nonpositive_orientation_count':int(np.sum(orientation[inside]<=0))})
                best.update({'normalization_C':.85/factor_target,'factor_at_target':factor_target,
                             'polynomial_bidegree_bound':[p+q+4,r+s+4],
                             'target_gradient_log_D':[p/ut-q/(1-ut)+2*evaluate(derivative(f,0),ut,vt)/target_f,
                                                      r/vt-s/(1-vt)+2*evaluate(derivative(f,1),ut,vt)/target_f],
                             'refinement_grids_trimmed_domain':dense,
                             'sampled_amplitude_and_orientation_pass':all(g['max_abs_D_scan_units']<=1. and not g['nonpositive_orientation_count'] for g in dense),
                             'cad_construction_authorized':False,'continuous_corridor_not_checked':True})
                report['localized_search']=best
                report['status']='localized_field_sampled_candidate_requires_corridor_and_kernel_audit' if best['sampled_amplitude_and_orientation_pass'] else 'rejected_localized_fields_exceed_displacement_or_orientation_limit'
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'output_sha256':digest(a.output),'status':report['status'],
                      'grids_trimmed_domain':report.get('grids_trimmed_domain'),
                      'F_target_dimensionless':report.get('F_target_dimensionless'),
                      'bubble_target':report.get('bubble_target')}))


if __name__=='__main__': main()
