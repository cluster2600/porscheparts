"""Construct exact tensor-product tangent root feet before window/union Booleans."""
import argparse
import hashlib
import json
from math import sqrt,acos,degrees,pi
from pathlib import Path
import sys

SOURCE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cubic(points,t):
    return [sum(w*p[k] for w,p in zip(((1-t)**3,3*t*(1-t)**2,3*t*t*(1-t),t**3),points)) for k in range(2)]


def roof_z(x):
    lo,hi=0.,1.
    for _ in range(60):
        t=(lo+hi)/2
        if cubic([[65,30],[80,30],[90,22],[105,22]],t)[0]<x:lo=t
        else:hi=t
    return cubic([[65,30],[80,30],[90,22],[105,22]],(lo+hi)/2)[1]


def smoothstep(t):
    t=max(0.,min(1.,t));return t**3*(10-15*t+6*t*t)


def vector(values):
    import numpy as np
    return np.array(values,dtype=float)


def make_foot(edge,plan):
    import numpy as np
    from build123d import Solid,Face,Edge,Wire
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.Geom import Geom_BSplineSurface,Geom_BSplineCurve
    from OCP.TColgp import TColgp_Array2OfPnt,TColgp_Array1OfPnt
    from OCP.TColStd import TColStd_Array1OfReal,TColStd_Array1OfInteger,TColStd_Array2OfReal
    from OCP.gp import gp_Pnt,gp_Vec
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace,BRepBuilderAPI_MakeEdge,BRepBuilderAPI_Sewing,BRepBuilderAPI_MakeSolid
    from OCP.BRepLib import BRepLib
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS

    # Mirrored intersections may use different native knot/pole layouts.
    # The tensor identity works in each curve's own rational basis.
    curve=BRepAdaptor_Curve(edge.wrapped).BSpline().Copy()
    assert not curve.IsPeriodic()
    if abs(curve.Value(curve.FirstParameter()).X())<abs(curve.Value(curve.LastParameter()).X()):
        curve.Reverse()
    lo,hi=curve.FirstParameter(),curve.LastParameter()
    poles=[vector(curve.Pole(i).Coord()) for i in range(1,curve.NbPoles()+1)]
    weights=[curve.Weight(i) for i in range(1,curve.NbPoles()+1)]
    assert max(abs(abs(p[0])-100) for p in poles[:1])<1e-7
    eps=plan['overlap_mm'];radius=plan['maximum_section_YZ_radius_mm']
    radii=[min(radius,radius*smoothstep((100-abs(p[0]))/3),max(0.,roof_z(abs(p[0]))-p[2]-eps)) for p in poles]
    radii[:2]=[0.,0.]
    assert max(radii)==1 and min(radii)==0
    def real(values):
        a=TColStd_Array1OfReal(1,len(values))
        for i,v in enumerate(values,1):a.SetValue(i,float(v))
        return a
    def integer(values):
        a=TColStd_Array1OfInteger(1,len(values))
        for i,v in enumerate(values,1):a.SetValue(i,int(v))
        return a
    knots=real([curve.Knot(i) for i in range(1,curve.NbKnots()+1)])
    mults=integer([curve.Multiplicity(i) for i in range(1,curve.NbKnots()+1)])
    r_poles=TColgp_Array1OfPnt(1,len(poles))
    for i,r in enumerate(radii,1):r_poles.SetValue(i,gp_Pnt(r,0,0))
    rcurve=Geom_BSplineCurve(r_poles,real(weights),knots,mults,curve.Degree(),False)
    # Profile vertices A=(-r,-e),B=(e,-e),C=(e,r),D=(0,r),E=(-r,0).
    # Each pair stores (radius coefficientYZ, overlap coefficientYZ, weight).
    profiles=[
      [('A',(-1,0),(0,-1),1.),('B',(0,0),(1,-1),1.)],
      [('B',(0,0),(1,-1),1.),('C',(0,1),(1,0),1.)],
      [('C',(0,1),(1,0),1.),('D',(0,1),(0,0),1.)],
      [('D',(0,1),(0,0),1.),('Q',(0,0),(0,0),sqrt(.5)),('E',(-1,0),(0,0),1.)],
      [('E',(-1,0),(0,0),1.),('A',(-1,0),(0,-1),1.)]]
    surfaces=[];faces=[];identity_error=0.;normal_angles=[]
    for profile in profiles:
        n=len(profile);degree=n-1;net=TColgp_Array2OfPnt(1,len(poles),1,n)
        ws=TColStd_Array2OfReal(1,len(poles),1,n)
        for i,(p,r,w) in enumerate(zip(poles,radii,weights),1):
            for j,(_,q,o,vw) in enumerate(profile,1):
                point=p+vector([0,r*q[0]+eps*o[0],r*q[1]+eps*o[1]])
                net.SetValue(i,j,gp_Pnt(*point));ws.SetValue(i,j,w*vw)
        surface=Geom_BSplineSurface(net,ws,knots,real([0,1]),mults,integer([n,n]),curve.Degree(),degree,False,False)
        maker=BRepBuilderAPI_MakeFace(surface,1e-8);assert maker.IsDone()
        faces.append(Face(maker.Face()));surfaces.append(surface)
        for u in np.linspace(lo+.001*(hi-lo),hi-.001*(hi-lo),13):
            c=vector(curve.Value(float(u)).Coord());r=rcurve.Value(float(u)).X()
            for v in np.linspace(0,1,9):
                if n==2:b=[1-v,v]
                else:b=[(1-v)**2,2*v*(1-v),v*v]
                denom=sum(a*item[3] for a,item in zip(b,profile))
                q=sum((a*item[3]*vector(item[1]) for a,item in zip(b,profile)),start=np.zeros(2))/denom
                o=sum((a*item[3]*vector(item[2]) for a,item in zip(b,profile)),start=np.zeros(2))/denom
                expected=c+vector([0,r*q[0]+eps*o[0],r*q[1]+eps*o[1]])
                actual=vector(surface.Value(float(u),float(v)).Coord())
                identity_error=max(identity_error,float(np.linalg.norm(actual-expected)))
    # Planar end caps. At r=0 the circular edge collapses and is omitted.
    for u in (lo,hi):
        c=vector(curve.Value(u).Coord());r=rcurve.Value(u).X();cap_edges=[]
        for profile in profiles:
            if len(profile)==3 and r<1e-14:continue
            p=TColgp_Array1OfPnt(1,len(profile));w=[]
            for j,(_,q,o,vw) in enumerate(profile,1):
                p.SetValue(j,gp_Pnt(*(c+vector([0,r*q[0]+eps*o[0],r*q[1]+eps*o[1]]))));w.append(vw)
            curve_edge=Geom_BSplineCurve(p,real(w),real([0,1]),integer([len(profile),len(profile)]),len(profile)-1,False)
            cap_edges.append(Edge(BRepBuilderAPI_MakeEdge(curve_edge).Edge()))
        cap=Face(Wire(cap_edges));assert cap.is_valid;faces.append(cap)
    sewing=BRepBuilderAPI_Sewing(1e-7)
    for face in faces:sewing.Add(face.wrapped)
    sewing.Perform()
    explorer=TopExp_Explorer(sewing.SewedShape(),TopAbs_SHELL);shells=[]
    while explorer.More():
        shells.append(TopoDS.Shell_s(explorer.Current()));explorer.Next()
    assert len(shells)==1,len(shells)
    maker=BRepBuilderAPI_MakeSolid(shells[0]);solid=maker.Solid()
    assert BRepLib.OrientClosedSolid_s(solid)
    body=Solid(solid);assert body.is_valid and body.volume>0
    arc=surfaces[3]
    # Exact endpoint tangent planes; independent finite point/derivative crosscheck.
    for u in np.linspace(lo+.02*(hi-lo),hi-.02*(hi-lo),81):
        p=gp_Pnt();dc=gp_Vec();curve.D1(float(u),p,dc)
        cprime=vector(dc.Coord())
        if rcurve.Value(float(u)).X()<1e-6:continue
        for v,support in ((1.,vector([-cprime[2],0,cprime[0]])),(0.,vector([-cprime[1],cprime[0],0]))):
            point=gp_Pnt();du=gp_Vec();dv=gp_Vec();arc.D1(float(u),v,point,du,dv)
            normal=np.cross(vector(du.Coord()),vector(dv.Coord()))
            normal/=np.linalg.norm(normal);support/=np.linalg.norm(support)
            normal_angles.append(degrees(acos(min(1.,abs(float(normal@support))))))
    assert identity_error<=plan['tensor_identity_error_mm_max'],identity_error
    assert max(normal_angles)<=plan['support_G1_normal_angle_degrees_max'],max(normal_angles)
    report={'curve_degree':curve.Degree(),'curve_poles':len(poles),'curve_parameter_domain':[lo,hi],
       'curve_ends_mm':[list(curve.Value(u).Coord()) for u in (lo,hi)],'radius_coefficients_mm':radii,
       'radius_first_two_coefficients_zero':radii[:2]==[0,0],
       'tensor_identity_error_mm':identity_error,'maximum_support_tangent_plane_angle_degrees':max(normal_angles),
       'closed_native_foot_valid':True,'native_foot_faces':len(body.faces()),'native_foot_volume_default_mm3':body.volume}
    return body,report


def build(base,output):
    import numpy as np
    from OCP.OSD import OSD_ThreadPool
    OSD_ThreadPool.DefaultPool_s().Init(1)
    from build123d import import_step,export_step,export_stl,export_brep,Pos,Box,Polygon,fillet,Face,extrude
    sys.path.insert(0,str(SOURCE.parent.parent/'bionic-20261011/correction-20261013'))
    from corrected_cad import precise_volume
    base,output=Path(base),Path(output);plan=json.loads((SOURCE/'plan.json').read_text())
    assert not output.exists();assert sha(base/'carrier.step')==plan['base_STEP_sha256']
    output.mkdir();(output/'construction-plan.json').write_bytes((SOURCE/'plan.json').read_bytes())
    (output/'source-snapshot.py').write_bytes(Path(__file__).read_bytes())
    settings=json.loads((base/'study.json').read_text());g=settings['geometry']
    body=import_step(base/'carrier.step');original=body;all_edges=list(body.edges());reports=[]
    try:
        for selected in plan['selected_edges']:
            edge=all_edges[selected['edge_index_zero_based']]
            assert abs(edge.length-selected['edge_length_mm'])<1e-7
            foot,report=make_foot(edge,plan)
            sx=selected['mirror_X'];report['mirror_X']=sx
            export_brep(foot,output/f'foot-native-X{sx}.brep')
            (output/f'foot-native-X{sx}.json').write_text(json.dumps(report,indent=2)+'\n')
            # Recreate the same rounded first-window cutter before joining.
            points=np.array([[78,-25],[146,-20],[80,24]],dtype=float)
            centre=points.mean(axis=0);points=centre+g['window_scale']*(points-centre);points[:,0]*=sx
            # Polygon treats coordinate lists as nested sequences; explicit
            # tuples retain the same 2D vertices as the original CAD builder.
            polygon=Polygon(*(tuple(map(float,p)) for p in points),align=None)
            assert polygon.is_valid and len(polygon.vertices())==3
            rounded=fillet(polygon.vertices(),6*g['window_scale']).faces()[0]
            window=Face(rounded.outer_wire().offset_2d(-g['window_edge_inset_mm']))
            cutter=Pos(0,0,-44)*extrude(window,amount=88,dir=(0,0,1))
            trimmed=foot-cutter
            assert trimmed is not None and trimmed.is_valid
            report['window_trimmed_foot_volume_mm3']=precise_volume(trimmed)[0]
            export_brep(trimmed,output/f'foot-window-trimmed-X{sx}.brep')
            # Initial end cap must be wholly removed by the frozen window.
            start_x=abs(report['curve_ends_mm'][1][0]);exposed=[]
            for face in trimmed.faces():
                box=face.bounding_box()
                if abs(abs(box.min.X)-start_x)<1e-6 and abs(abs(box.max.X)-start_x)<1e-6:
                    exposed.append(face.area)
            report['initial_longitudinal_cap_remaining_area_mm2']=sum(exposed)
            assert sum(exposed)<1e-8
            before,_=precise_volume(body);body=body+trimmed
            assert body.is_valid and len(body.solids())==1
            report['actual_added_volume_mm3']=precise_volume(body)[0]-before
            reports.append(report);print(json.dumps(report),flush=True)
        volume,error=precise_volume(body)
        removed=original-body;added=body-original
        removed_volume=abs(precise_volume(removed)[0]) if removed is not None else 0
        added_volume=abs(precise_volume(added)[0]) if added is not None else 0
        assert removed_volume<=plan['removed_reference_volume_mm3_max'],removed_volume
        assert added_volume>0
        pad=Pos(0,0,0)*Box(130,72,8);a,b=original&pad,body&pad
        differences=[a-b,b-a];pad_difference=sum(abs(precise_volume(s)[0]) if s is not None else 0 for s in differences)
        assert pad_difference<=plan['protected_pad_difference_mm3_max']
        mass=volume*settings['material']['density_tonne_mm3']*1000
        assert mass<=plan['mass_kg_max']
        box=body.bounding_box()
        for actual,expected in zip(list(box.min)+list(box.max),[-296,-36.5,-22,296,36.5,30]):assert abs(actual-expected)<1e-6
        export_brep(body,output/'native-body.brep');export_step(body,output/'carrier.step')
        export_stl(body,output/'carrier.stl',tolerance=.06,angular_tolerance=.10)
        reread=import_step(output/'carrier.step');read_volume,read_error=precise_volume(reread)
        assert reread.is_valid and len(reread.solids())==1
        assert abs(read_volume/volume-1)<=plan['native_and_STEP_relative_volume_difference_max']
        settings['design_id']=plan['design_id'];settings['tensor_root_foot']=plan
        (output/'study.json').write_text(json.dumps(settings,indent=2)+'\n')
        receipt={'design_id':plan['design_id'],'source_sha256':sha(__file__),'plan_sha256':sha(SOURCE/'plan.json'),
          'base_STEP_sha256':sha(base/'carrier.step'),'CAD_valid':True,'solid_count':1,'volume_mm3':volume,
          'readback_volume_mm3':read_volume,'dense_reference_mass_kg':mass,'added_volume_mm3':added_volume,
          'removed_volume_mm3':removed_volume,'central_pad_symmetric_difference_mm3':pad_difference,
          'STEP_readback_relative_volume_difference':read_volume/volume-1,'integration_errors':[error,read_error],
          'bounds_mm':[list(box.min),list(box.max)],'feet':reports,
          'geometry_sha256':{n:sha(output/n) for n in ('carrier.step','carrier.stl')},
          'mass_ceiling_pass':mass<=plan['mass_kg_max'],'junction_trim_audit_complete':False,'mechanics_evaluated':False}
        (output/'geometry.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
        return receipt
    except BaseException as error:
        failure={'status':'rejected','error_type':type(error).__name__,'reason':str(error),
          'source_sha256':sha(__file__),'plan_sha256':sha(SOURCE/'plan.json'),'completed_feet':reports}
        (output/'rejection.json').write_text(json.dumps(failure,indent=2)+'\n');print(json.dumps(failure),flush=True);raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('base',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();build(args.base,args.output)
