"""Construct a local C2 cap-to-rib-roof shoulder from true support polynomials."""
import argparse,hashlib,importlib.util,json,math,sys
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def build(base,out):
    import numpy as np
    from numpy.polynomial import Polynomial as P,Chebyshev
    from build123d import (import_step,export_step,export_brep,export_stl,Face,Edge,Wire,Pos,Box,extrude)
    from OCP.OSD import OSD_ThreadPool
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace,BRepBuilderAPI_MakeEdge,BRepBuilderAPI_Sewing,BRepBuilderAPI_MakeSolid
    from OCP.BRepLib import BRepLib
    from OCP.Geom import Geom_BezierSurface,Geom_BezierCurve
    from OCP.TColgp import TColgp_Array2OfPnt,TColgp_Array1OfPnt
    from OCP.gp import gp_Pnt,gp_Vec
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.TopoDS import TopoDS
    from build123d import Solid
    OSD_ThreadPool.DefaultPool_s().Init(1)
    sys.path.insert(0,str(SOURCE.parent.parent/'bionic-20261011/correction-20261013'))
    from corrected_cad import precise_volume
    plan=json.loads((SOURCE/'plan.json').read_text());assert sha(base/'carrier.step')==plan['base_STEP_sha256']
    assert not out.exists();out.mkdir(parents=True)
    (out/'source-snapshot.py').write_bytes(Path(__file__).read_bytes());(out/'construction-plan.json').write_bytes((SOURCE/'plan.json').read_bytes())
    settings=json.loads((base/'study.json').read_text());body=import_step(base/'carrier.step');original=body
    old_faces=list(body.faces());curves=[BRepAdaptor_Surface(old_faces[i].wrapped,True).BasisCurve().BSpline() for i in [188,189,190]]
    assert all(c.NbKnots()==2 and c.Knot(1)==0 and c.Knot(2)==1 and not c.IsRational() for c in curves)
    def polynomial(c,k):
        n=c.NbPoles()-1;t=P([0,1]);return sum((math.comb(n,i)*c.Pole(i+1).Coord()[k]*t**i*(1-t)**(n-i) for i in range(n+1)),P([0.]))
    cap,rib,roof=[[polynomial(c,k) for k in range(3)] for c in curves]
    assert np.linalg.norm(np.array([roof[0](0),roof[2](0)])-[65,30])<1e-8
    assert np.linalg.norm(np.array([roof[0](1),roof[2](1)])-[105,22])<1e-8
    def invert(poly,x):
        lo,hi=0.,1.
        for _ in range(65):
            mid=(lo+hi)/2
            if poly(mid)<x:lo=mid
            else:hi=mid
        return (lo+hi)/2
    def bernstein(poly,n):
        return [sum(poly.coef[j]*math.comb(i,j)/math.comb(n,j) for j in range(min(i,len(poly.coef)-1)+1)) for i in range(n+1)]
    def fit_support(curve,xr,ur):
        ss=np.linspace(0,1,121);mapping=Chebyshev.fit(ss,[invert(curve[0],xr(s)) for s in ss],plan['support_mapping_degree'],domain=[0,1]).convert(kind=P)
        values=[invert(curve[0],xr(s)) for s in [0,1]]
        derivatives=[xr.deriv()(s)/curve[0].deriv()(u) for s,u in zip([0,1],values)]
        h00=P([1,0,-3,2]);h01=P([0,0,3,-2]);h10=P([0,1,-2,1]);h11=P([0,0,-1,1])
        mapping+=(values[0]-mapping(0))*h00+(values[1]-mapping(1))*h01+(derivatives[0]-mapping.deriv()(0))*h10+(derivatives[1]-mapping.deriv()(1))*h11
        error=max(abs(curve[0](mapping(s))-xr(s)) for s in np.linspace(0,1,1001))
        assert error<=plan['maximum_corresponding_support_X_difference_mm'],error
        return [poly(mapping) for poly in curve],mapping,error
    def make_surface(columns,degree,sx):
        controls=[[bernstein(poly,degree) for poly in col] for col in columns]
        net=TColgp_Array2OfPnt(1,degree+1,1,len(columns))
        for i in range(degree+1):
            for j in range(len(columns)):net.SetValue(i+1,j+1,gp_Pnt(sx*controls[j][0][i],controls[j][1][i],controls[j][2][i]))
        surface=Geom_BezierSurface(net);face=Face(BRepBuilderAPI_MakeFace(surface,1e-8).Face());assert face.is_valid
        return face,surface
    def edge_profile(columns,u,sx):
        p=TColgp_Array1OfPnt(1,len(columns))
        for j,col in enumerate(columns,1):p.SetValue(j,gp_Pnt(sx*col[0](u),col[1](u),col[2](u)))
        if max(np.linalg.norm(np.array(p.Value(j).Coord())-p.Value(1).Coord()) for j in range(1,len(columns)+1))<1e-10:return None
        return Edge(BRepBuilderAPI_MakeEdge(Geom_BezierCurve(p)).Edge())
    def make_solid(profiles,degree,sx):
        faces=[];surfaces=[]
        for profile in profiles:
            face,surface=make_surface(profile,degree,sx);faces.append(face);surfaces.append(surface)
        ends=[]
        for u in [0.,1.]:
            es=[edge_profile(p,u,sx) for p in profiles];end=Face(Wire([e for e in es if e is not None]));assert end.is_valid
            faces.append(end);ends.append(end)
        sew=BRepBuilderAPI_Sewing(1e-7)
        for f in faces:sew.Add(f.wrapped)
        sew.Perform();it=TopExp_Explorer(sew.SewedShape(),TopAbs_SHELL);shells=[]
        while it.More():shells.append(TopoDS.Shell_s(it.Current()));it.Next()
        assert len(shells)==1
        solid=BRepBuilderAPI_MakeSolid(shells[0]).Solid();assert BRepLib.OrientClosedSolid_s(solid)
        result=Solid(solid);assert result.is_valid and precise_volume(result)[0]>0
        return result,surfaces[0],ends
    reports=[]
    try:
        # One quintic XY bridge: C2 to exact rib at84.5 and to the existing
        # window's straight boundary at94. It adds only upper-skin material.
        xa,xb=plan['window_bridge_X_range_mm'];L=xb-xa;ta=invert(rib[0],xa)
        ya=rib[1](ta);dy=rib[1].deriv()(ta)/rib[0].deriv()(ta)
        ddy=(rib[1].deriv(2)(ta)*rib[0].deriv()(ta)-rib[1].deriv()(ta)*rib[0].deriv(2)(ta))/rib[0].deriv()(ta)**3
        oldxy=load('r5',SOURCE.parent/'reinforcement-5/build_corner_caps.py')
        _,unrounded,_=oldxy.corner_faces(settings,1)
        # Select the unchanged first-window upper line from its actual BRep.
        line_candidates=[]
        for e in unrounded.edges():
            vs=list(e.vertices())
            if len(vs)==2 and min(v.X for v in vs)>89 and max(v.X for v in vs)>109:
                p,q=[np.array(tuple(v)) for v in vs]
                if abs(q[0]-p[0])<1e-10:continue
                slope=(q[1]-p[1])/(q[0]-p[0])
                if abs(slope+2/3)<1e-8:line_candidates.append((slope,p[1]-slope*p[0]))
        assert len(line_candidates)==1
        slope,intercept=line_candidates[0];yb=slope*xb+intercept
        ys=[ya,ya+L*dy/5,ya+2*L*dy/5+L*L*ddy/20,yb-2*L*slope/5,yb-L*slope/5,yb]
        arch=load('frozen_arch',SOURCE.parent/'normal-builder/cad.py')
        skins=(arch.arm_envelope(44,8)-arch.arm_envelope(41,0,end=268)[0]-arch.arm_envelope(41,0,end=268)[1])&(Pos(0,0,17)*Box(600,200,26))
        for sx in plan['mirror_X']:
            old,_,_=oldxy.corner_faces(settings,sx)
            points=[(sx*(xa+i*L/5),y) for i,y in enumerate(ys)]
            bridge=Edge.make_bezier(*points)
            region=Face(Wire([bridge,Edge.make_line(points[-1],(sx*xb,30)),Edge.make_line((sx*xb,30),(sx*xa,30)),Edge.make_line((sx*xa,30),points[0])]))
            addition=((old+region)-old);assert addition is not None and addition.is_valid
            cap_addition=(Pos(0,0,-44)*extrude(addition,amount=88,dir=(0,0,1)))&skins
            assert cap_addition is not None and cap_addition.is_valid
            export_brep(cap_addition,out/f'upper-cap-bridge-X{sx}.brep')
            body=body+cap_addition;assert body.is_valid and len(body.solids())==1
        (out/'bridge.json').write_text(json.dumps({'X_controls_mm':[xa+i*L/5 for i in range(6)],'Y_controls_mm':ys,'old_line_slope':slope,'old_line_intercept':intercept,'start_dy_dx':dy,'start_d2y_dx2':ddy},indent=2)+'\n')
        # Three U segments share exact endpoint positions/first derivatives.
        # Their only physical width is the declared single2.5mm shoulder.
        for x0,x1 in [(xa,plan['shoulder_full_width_X_mm']),(plan['shoulder_full_width_X_mm'],100.),(100.,105.)]:
            ur=P([invert(rib[0],x0),invert(rib[0],x1)-invert(rib[0],x0)])
            xr,yr=rib[0](ur),rib[1](ur)
            if x1<=100:cap_polys,uc,ec=fit_support(cap,xr,ur)
            else:cap_polys=[xr,P([0.]),P([22.])];uc=None;ec=0.
            roof_polys,ut,et=fit_support(roof,xr,ur)
            xc,zc=cap_polys[0],cap_polys[2];xt,zt=roof_polys[0],roof_polys[2]
            width=plan['maximum_shoulder_width_Y_mm']*(P([0,0,0,10,-15,6]) if x0==xa else P([1.]))
            e=plan['internal_overlap_mm']
            main=[[xc if j<3 else xt,yr-width+width*j/5,zc if j<3 else zt] for j in range(6)]
            r0=[xc,yr-width,zc];r1=[xt,yr,zt];inside_top=[xt,yr+e,zt-e];inside_cap=[xc,yr+e,zc-e];below=[xc,yr-width,zc-e]
            profiles=[main,[r1,inside_top],[inside_top,inside_cap],[inside_cap,below],[below,r0]]
            degree=max(len(p.coef)-1 for profile in profiles for col in profile for p in col);assert degree<=25
            for sx in plan['mirror_X']:
                foot,surface,ends=make_solid(profiles,degree,sx)
                export_brep(foot,out/f'shoulder-X{sx}-{x0}-{x1}.brep')
                # G1 is checked from the actual native surface against the
                # derivative of the exact support polynomial at both rails.
                angles=[];outside=[];native_failures=[];conditioned_angles=[]
                for u in np.linspace(.001,.999,41):
                    for v,polys in [(0.,cap_polys),(1.,roof_polys)]:
                        p=gp_Pnt();du=gp_Vec();dv=gp_Vec();surface.D1(float(u),v,p,du,dv)
                        n=np.cross(du.Coord(),dv.Coord());n/=np.linalg.norm(n)
                        support=np.array([-polys[2].deriv()(u),0,sx*polys[0].deriv()(u)]);support/=np.linalg.norm(support)
                        angle=math.degrees(math.atan2(np.linalg.norm(np.cross(n,support)),abs(n@support)));angles.append(angle)
                        if width(u)>=1e-5:conditioned_angles.append(angle)
                        if angle>plan['G1_normal_angle_degrees_max']:
                            native_failures.append({'u':float(u),'v':v,'width_Y_mm':float(width(u)),
                                  'D1v_norm_mm':float(np.linalg.norm(dv.Coord())),'angle_degrees':angle})
                    if not body.solids()[0].is_inside((sx*xc(u),yr(u)-width(u),zc(u)-.125),tolerance=1e-7):outside.append(float(u))
                # Repeated first/last three X/Z control columns impose exact
                # transverse tangent direction Y. Preserve all native D1 gate
                # failures at the vanishing-width end; export solely for
                # independent seam review, never count them as admitted.
                analytic_G1=(main[0][0] is main[1][0] and main[0][2] is main[1][2]
                             and main[-1][0] is main[-2][0] and main[-1][2] is main[-2][2])
                assert analytic_G1
                assert not outside,('cap rail outside material',x0,x1,sx,outside)
                before=precise_volume(body)[0];body=body+foot
                assert body.is_valid and len(body.solids())==1
                row={'mirror_X':sx,'X_range_mm':[x0,x1],'U_degree':degree,'V_degree':5,'cap_X_fit_error_mm':ec,'roof_X_fit_error_mm':et,
                     'maximum_G1_angle_degrees':max(angles),'native_boundary_G1_gate_pass':not native_failures,
                     'native_D1_gate_failures':native_failures,'analytic_repeated_controls_G1':analytic_G1,
                     'maximum_native_angle_for_width_at_least_1e-5mm':max(conditioned_angles) if conditioned_angles else None,
                     'cap_rail_inside_material':not outside,'actual_added_volume_mm3':precise_volume(body)[0]-before}
                reports.append(row);print(json.dumps(row),flush=True)
        volume,error=precise_volume(body);mass=volume*settings['material']['density_tonne_mm3']*1000
        assert mass<=plan['mass_ceiling_kg'],mass
        removed=original-body;removed_volume=abs(precise_volume(removed)[0]) if removed is not None else 0
        assert removed_volume<=plan['removed_reference_volume_mm3_max'],removed_volume
        pad=Box(130,72,8);a,b=body&pad,original&pad
        pad_difference=sum(abs(precise_volume(s)[0]) if s is not None else 0 for s in [a-b,b-a])
        assert pad_difference<=plan['protected_pad_difference_mm3_max']
        bb=body.bounding_box();assert all(abs(a-b)<1e-6 for a,b in zip(list(bb.min)+list(bb.max),[-296,-36.5,-22,296,36.5,30]))
        export_brep(body,out/'native-body.brep');export_step(body,out/'carrier.step');export_stl(body,out/'carrier.stl',tolerance=.06,angular_tolerance=.10)
        reread=import_step(out/'carrier.step');read_volume,read_error=precise_volume(reread)
        assert reread.is_valid and len(reread.solids())==1
        assert abs(read_volume/volume-1)<=plan['STEP_relative_volume_difference_max']
        settings['design_id']=plan['design_id'];settings['shoulder']=plan
        (out/'study.json').write_text(json.dumps(settings,indent=2)+'\n')
        receipt={'status':'geometry_pending_independent_seams','design_id':plan['design_id'],'mass_kg':mass,'volume_mm3':volume,
          'STEP_readback_volume_mm3':read_volume,'STEP_relative_volume_difference':read_volume/volume-1,'integration_errors':[error,read_error],
          'removed_reference_volume_mm3':removed_volume,'protected_pad_difference_mm3':pad_difference,'bounds_mm':[list(bb.min),list(bb.max)],
          'base_STEP_sha256':sha(base/'carrier.step'),'generator_sha256':sha(__file__),'plan_sha256':sha(SOURCE/'plan.json'),
          'geometry_sha256':{n:sha(out/n) for n in ['carrier.step','carrier.stl']},'shoulders':reports,
          'independent_final_seams_admitted':False,'mechanics_evaluated':False}
        (out/'geometry.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
    except BaseException as error:
        (out/'rejection.json').write_text(json.dumps({'status':'rejected','type':type(error).__name__,'reason':str(error),'completed_shoulders':reports},indent=2)+'\n');raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('base',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();build(a.base,a.output)
