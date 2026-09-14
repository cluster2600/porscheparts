#!/usr/bin/env python3
"""Bounded C2 surface trial for isolated weak ray 1743, never the M64 master.

The support is the largest UV rectangle centered at the actual target and
contained in the source face parameter domain. No dimensions are inferred.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import sys


def beta3(t):return 64*t**3*(1-t)**3


def centered_support(t):
    if not math.isfinite(t) or not 0<t<1:raise ValueError('target not strictly inside source domain')
    half=min(t,1-t)
    return t-half,t+half


def coefficient_bound(value):return Fraction.from_float(float(value))*Fraction(25,256)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source-step','remaining-report','patches','helpers','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2]);resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    a.output.mkdir(parents=True)
    remaining=json.loads(a.remaining_report.read_text());patches=json.loads(a.patches.read_text())
    if sha(a.source_step)!=remaining['source_sha256'] or sha(a.source_step)!=patches['source_sha256']['step']:raise ValueError('source provenance mismatch')
    item=next(row for row in remaining['probes_private'] if row['probe_private']==1743)
    probe=next(row for patch in patches['patches_private'] for row in patch['probes_private'] if row['index']==1743)
    if item['degrees']!=[1,1] or item['pole_counts']!=[2,2] or item['rational'] or item['wire_count']!=1 or len(item['boundary_private'])!=4 or not all(b['iso_u'] or b['iso_v'] for b in item['boundary_private']):
        raise ValueError('four-isoparametric bilinear prerequisites not met')
    old_length=item['remaining_ray']['ray_scan_units'];target_length=1.60;delta=target_length-old_length
    if not 0<delta<=1.:raise ValueError('displacement outside bounded scope')
    report={'schema':'m64-reference-isolated-C2-surface-trial/v1','source_sha256':sha(a.source_step),
            'remaining_report_sha256':sha(a.remaining_report),'patches_sha256':sha(a.patches),
            'probe_private':1743,'selected_face_private':item['entry_face_private'],
            'original_ray_scan_units':old_length,'target_ray_scan_units':target_length,
            'requested_displacement_scan_units':delta,'master_modified':False,'combined_with_other_repair':False,
            'manufacturing_authorized':False,'face_or_solid_constructed':False,
            'exploratory_gradient_limit':1.0,'gradient_limit_is_geometric_screen_not_material_allowable':True}
    def save(status):
        report['status']=status;(a.output/'surface-report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'status':status}),flush=True)
    save('loading')
    import numpy as np
    sys.path.insert(0,str(a.helpers))
    from audit_brep_f42 import read_step
    from repair_topology_f42_1 import indexed
    from OCP.BRep import BRep_Tool
    from OCP.BRepTools import BRepTools,BRepTools_WireExplorer
    from OCP.BRepAdaptor import BRepAdaptor_Curve,BRepAdaptor_Curve2d
    from OCP.TopAbs import TopAbs_FACE,TopAbs_OUT
    from OCP.TopoDS import TopoDS
    from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
    from OCP.Geom import Geom_BSplineSurface
    from OCP.TColgp import TColgp_Array2OfPnt
    from OCP.TColStd import TColStd_Array1OfReal,TColStd_Array1OfInteger
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt,gp_Vec
    original=read_step(a.source_step)[0];face=TopoDS.Face_s(indexed(original,TopAbs_FACE).FindKey(item['entry_face_private']));s0=BRep_Tool.Surface_s(face)
    u0,u1,v0,v1=s0.Bounds();entry=np.array(probe['entry_xyz_scan_units']);normal=-np.array(probe['direction'])
    if abs(np.linalg.norm(normal)-1)>1e-10:raise ValueError('nonunit displacement direction')
    project=GeomAPI_ProjectPointOnSurf(gp_Pnt(*entry),s0);ut,vt=project.LowerDistanceParameters();un,vn=(ut-u0)/(u1-u0),(vt-v0)/(v1-v0)
    ul,uh=centered_support(un);vl,vh=centered_support(vn)
    target=entry+delta*normal;cl=BRepClass3d_SolidClassifier(original);cl.Perform(gp_Pnt(*target),1e-7)
    report['target_classification']=str(cl.State())
    if cl.State()!=TopAbs_OUT:save('rejected_target_not_outside_source');return
    # For this actual target both support upper ends coincide with the source
    # upper borders. Reject other placements instead of silently generalizing.
    if abs(uh-1)>1e-14 or abs(vh-1)>1e-14:raise ValueError('this bounded trial only supports upper-right target')
    source_poles=np.array([[[s0.Pole(i,j).X(),s0.Pole(i,j).Y(),s0.Pole(i,j).Z()] for j in (1,2)] for i in (1,2)])
    source_at=lambda u,v:((1-u)*(1-v)*source_poles[0,0]+u*(1-v)*source_poles[1,0]+(1-u)*v*source_poles[0,1]+u*v*source_poles[1,1])
    ucontrol=np.concatenate((np.linspace(0,ul,7),np.linspace(ul,1,7)[1:]));vcontrol=np.concatenate((np.linspace(0,vl,7),np.linspace(vl,1,7)[1:]))
    poles=np.array([[source_at(u,v) for v in vcontrol] for u in ucontrol]);coefficient=delta*256/25
    poles[9,9]+=coefficient*normal
    bound=coefficient_bound(coefficient)
    report.update({'support_uv_normalized_private':[ul,uh,vl,vh],'target_uv_normalized_private':[un,vn],
                   'displacement_bound_exact':str(bound),'displacement_bound_float':float(bound),
                   'bound_scope':'C2_scalar_Bernstein_field_before_native_knot_removal','native_roundoff_bound_included':False})
    if bound>1:save('rejected_global_displacement_bound');return
    pp=TColgp_Array2OfPnt(1,13,1,13)
    for i in range(13):
        for j in range(13):pp.SetValue(i+1,j+1,gp_Pnt(*poles[i,j]))
    uk,vk=TColStd_Array1OfReal(1,3),TColStd_Array1OfReal(1,3);um,vm=TColStd_Array1OfInteger(1,3),TColStd_Array1OfInteger(1,3)
    for i,(u,v,mult) in enumerate(zip([u0,u0+ul*(u1-u0),u1],[v0,v0+vl*(v1-v0),v1],[7,6,7]),1):uk.SetValue(i,u);vk.SetValue(i,v);um.SetValue(i,mult);vm.SetValue(i,mult)
    s1=Geom_BSplineSurface(pp,uk,vk,um,vm,6,6)
    save('removing_excess_internal_multiplicity')
    removed_u=s1.RemoveUKnot(2,4,1e-12);removed_v=s1.RemoveVKnot(2,4,1e-12)
    report['C2_knot_removal']={'u_success':removed_u,'v_success':removed_v,'tolerance':1e-12,
              'degrees':[s1.UDegree(),s1.VDegree()],'internal_multiplicities':[s1.UMultiplicity(2),s1.VMultiplicity(2)]}
    np.savez_compressed(a.output/'private-C2-surface.npz',pre_removal_poles=poles,source_poles=source_poles,normal=normal,
             support_normalized=[ul,uh,vl,vh],uv_bounds=[u0,u1,v0,v1],scalar_coefficient=coefficient,
             post_removal_poles=np.array([[[s1.Pole(i,j).X(),s1.Pole(i,j).Y(),s1.Pole(i,j).Z()] for j in range(1,s1.NbVPoles()+1)] for i in range(1,s1.NbUPoles()+1)]))
    report['coefficient_artifact_sha256']=sha(a.output/'private-C2-surface.npz')
    if not removed_u or not removed_v:save('rejected_C2_knot_reduction');return
    def geometry(surface,U,V):
        point=gp_Pnt();du,dv,duu,dvv,duv=gp_Vec(),gp_Vec(),gp_Vec(),gp_Vec(),gp_Vec();surface.D2(U,V,point,du,dv,duu,dvv,duv)
        vector=lambda x:np.array([x.X(),x.Y(),x.Z()])
        du,dv,duu,dvv,duv=map(vector,(du,dv,duu,dvv,duv));cross=np.cross(du,dv);norm=np.linalg.norm(cross)
        if norm<=1e-14:raise ValueError('singular surface Jacobian')
        n=cross/norm;E,F,G=np.dot(du,du),np.dot(du,dv),np.dot(dv,dv);det=E*G-F*F
        L,M,N=np.dot(n,duu),np.dot(n,duv),np.dot(n,dvv);H=(E*N-2*F*M+G*L)/(2*det);K=(L*N-M*M)/det
        kmax=abs(H)+math.sqrt(max(0.,H*H-K))
        return point,du,dv,cross,n,E,F,G,det,kmax
    save('checking_native_surface_quality')
    points=np.unique(np.concatenate((np.linspace(0,1,41),np.linspace(ul,uh,81),[un])))
    values=np.unique(np.concatenate((np.linspace(0,1,41),np.linspace(vl,vh,81),[vn])))
    max_gradient=0.;max_rotation=0.;min_orientation=float('inf');max_curvature=0.;max_source_curvature=0.;max_error=0.;max_displacement=0.
    for u in points:
        for v in values:
            U,V=u0+u*(u1-u0),v0+v*(v1-v0);old=geometry(s0,U,V);new=geometry(s1,U,V)
            displacement=delta*beta3((u-ul)/(uh-ul))*beta3((v-vl)/(vh-vl)) if ul<=u<=uh and vl<=v<=vh else 0.
            expected=source_at(u,v)+displacement*normal;max_error=max(max_error,new[0].Distance(gp_Pnt(*expected)));max_displacement=max(max_displacement,new[0].Distance(old[0]))
            Du,Dv=np.dot(normal,new[1]-old[1]),np.dot(normal,new[2]-old[2]);E,F,G,det=old[5:9]
            gradient=math.sqrt(max(0.,(G*Du*Du-2*F*Du*Dv+E*Dv*Dv)/det));max_gradient=max(max_gradient,gradient)
            max_rotation=max(max_rotation,math.degrees(math.acos(np.clip(np.dot(old[4],new[4]),-1,1))))
            min_orientation=min(min_orientation,np.dot(old[3],new[3])/np.dot(old[3],old[3]));max_curvature=max(max_curvature,new[9]);max_source_curvature=max(max_source_curvature,old[9])
    edges=[];w=BRepTools_WireExplorer(BRepTools.OuterWire_s(face),face)
    while w.More():
        edge=w.Current();curve=BRepAdaptor_Curve(edge);pc=BRepAdaptor_Curve2d(edge,face);dist=[]
        for t in np.linspace(curve.FirstParameter(),curve.LastParameter(),121):uv=pc.Value(float(t));dist.append(curve.Value(float(t)).Distance(s1.Value(uv.X(),uv.Y())))
        edges.append(max(dist));w.Next()
    report.update({'native_surface_exists':True,'boundary_samples_per_edge':121,'boundary_same_parameter_distances':edges,
                   'target_position_error':s1.Value(ut,vt).Distance(gp_Pnt(*target)),
                   'native_quality_samples':int(points.size*values.size),'max_factored_vs_native_error':max_error,'max_sampled_displacement':max_displacement,
                   'maximum_surface_gradient':max_gradient,'maximum_normal_rotation_degrees':max_rotation,
                   'minimum_orientation_ratio':min_orientation,'maximum_absolute_principal_curvature':max_curvature,
                   'minimum_principal_radius_scan_units':1/max_curvature if max_curvature else None,
                   'source_maximum_absolute_principal_curvature':max_source_curvature,
                   'master_hash_unchanged':sha(a.source_step)==remaining['source_sha256']})
    fail=[]
    if max_error>1e-7:fail.append('native_evaluation_disagrees_with_field')
    if max(edges)>1e-5 or report['target_position_error']>1e-5:fail.append('boundary_or_point_constraint')
    if max_displacement>1:fail.append('displacement_limit')
    if min_orientation<=0:fail.append('orientation_reversal')
    if max_gradient>report['exploratory_gradient_limit']:fail.append('exploratory_gradient_limit')
    report['failed_checks']=fail
    save('rejected_surface_quality' if fail else 'surface_quality_passed_requires_face_and_solid_checks')
    print(json.dumps({k:report[k] for k in ('status','failed_checks','maximum_surface_gradient','maximum_normal_rotation_degrees','minimum_orientation_ratio','minimum_principal_radius_scan_units','displacement_bound_float')},indent=2))


if __name__=='__main__':main()
