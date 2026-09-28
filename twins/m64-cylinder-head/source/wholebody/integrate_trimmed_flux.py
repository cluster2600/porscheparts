#!/usr/bin/env python3
"""Independent trimmed-surface flux quadrature, not BRepGProp integration.

Divergence theorem: f=S dot (S_u cross S_v)/3. Green's theorem:
integral_D f du dv = integral_boundary [integral_u0^u f(s,v) ds] dv.
Split integration at B-spline knots; preserve every native trimming edge.
Compare two Gauss orders and adaptive QUADPACK outer integration. This is a
numerical cross-check, not a rigorous interval bound or measured part volume.
"""
import argparse
import json
import math
from pathlib import Path
import time
import warnings
from run_local_surface_trial import BODY_SHA,native


def integrate_face(face,order,adaptive):
    import numpy as np
    from scipy.integrate import quad,IntegrationWarning
    from OCP.BRepAdaptor import BRepAdaptor_Surface,BRepAdaptor_Curve2d
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_EDGE,TopAbs_FORWARD,TopAbs_REVERSED
    from OCP.TopoDS import TopoDS
    from OCP.GeomAbs import GeomAbs_BSplineSurface,GeomAbs_BSplineCurve,GeomAbs_Line
    from OCP.gp import gp_Pnt,gp_Vec,gp_Pnt2d,gp_Vec2d,gp_Dir2d,gp_Ax2d
    from OCP.Geom2d import Geom2d_Line,Geom2d_TrimmedCurve
    from OCP.Geom2dAPI import Geom2dAPI_InterCurveCurve,Geom2dAPI_ProjectPointOnCurve
    surface=BRepAdaptor_Surface(face); nodes,weights=np.polynomial.legendre.leggauss(order)
    u0=surface.FirstUParameter(); uknots=[]; vknots=[]
    if surface.GetType()==GeomAbs_BSplineSurface:
        spline=surface.BSpline();uknots=[spline.UKnot(i) for i in range(1,spline.NbUKnots()+1)]
        vknots=[spline.VKnot(i) for i in range(2,spline.NbVKnots())]
    p,du,dv=gp_Pnt(),gp_Vec(),gp_Vec(); pc,dc=gp_Pnt2d(),gp_Vec2d()
    def primitive(u,v):
        total=[]; cuts=sorted({u0,u,*[k for k in uknots if u0<k<u]})
        if u<u0: raise ValueError('trim_outside_reference_parameter_range')
        for left,right in zip(cuts,cuts[1:]):
            width=(right-left)/2;mid=(right+left)/2; terms=[]
            for node,weight in zip(nodes,weights):
                surface.D1(float(mid+width*node),float(v),p,du,dv)
                n=du.Crossed(dv)
                terms.append(float(weight)*(p.X()*n.X()+p.Y()*n.Y()+p.Z()*n.Z())/3)
            total.append(width*math.fsum(terms))
        return math.fsum(total)
    explorer=TopExp_Explorer(face,TopAbs_EDGE); values=[];errors=[];edges=0
    with warnings.catch_warnings():
        warnings.simplefilter('error',IntegrationWarning)
        while explorer.More():
            edge=TopoDS.Edge(explorer.Current());explorer.Next();edges+=1
            if edge.Orientation() not in (TopAbs_FORWARD,TopAbs_REVERSED):
                raise ValueError('unsupported_edge_orientation')
            sign=1 if edge.Orientation()==TopAbs_FORWARD else -1
            curve=BRepAdaptor_Curve2d(edge,face);a,b=curve.FirstParameter(),curve.LastParameter()
            cuts=[a,b]
            if curve.GetType()==GeomAbs_BSplineCurve:
                spline=curve.BSpline();cuts.extend(spline.Knot(i) for i in range(1,spline.NbKnots()+1) if a<spline.Knot(i)<b)
            # Surface v-knot crossings are breakpoints of the composed integrand,
            # even when the trimming curve itself has no knot there.
            for vk in vknots:
                if curve.GetType()==GeomAbs_Line:
                    va,vb=curve.Value(a).Y(),curve.Value(b).Y()
                    if min(va,vb)<vk<max(va,vb):cuts.append(a+(b-a)*(vk-va)/(vb-va))
                    continue
                line=Geom2d_Line(gp_Ax2d(gp_Pnt2d(0,vk),gp_Dir2d(1,0)))
                bounded_line=Geom2d_TrimmedCurve(line,u0-1,surface.LastUParameter()+1)
                crossing=Geom2dAPI_InterCurveCurve(Geom2d_TrimmedCurve(curve.Curve(),a,b),bounded_line,1e-12)
                # Use the high-level result. OCP 8.0.1 Intersector().IsDone()
                # reports False even for the analytic perpendicular-lines witness.
                for i in range(1,crossing.NbPoints()+1):
                    projection=Geom2dAPI_ProjectPointOnCurve(crossing.Point(i),curve.Curve(),a,b)
                    if projection.NbPoints()<1 or projection.LowerDistance()>1e-10:
                        raise ValueError('v_knot_parameter_recovery_failed')
                    parameter=projection.LowerDistanceParameter()
                    if a<parameter<b:cuts.append(parameter)
            def integrand(t):
                curve.D1(float(t),pc,dc)
                u,v,dvdt=pc.X(),pc.Y(),dc.Y()
                return 0. if dvdt==0 else primitive(u,v)*dvdt
            cuts=sorted(set(cuts))
            for left,right in zip(cuts,cuts[1:]):
                if adaptive:
                    value,error=quad(integrand,left,right,epsabs=1e-8,epsrel=1e-12,limit=300)
                    errors.append(error)
                else:
                    width=(right-left)/2;mid=(right+left)/2
                    value=width*math.fsum(float(w)*integrand(mid+width*x) for x,w in zip(nodes,weights))
                values.append(sign*value)
    return {'signed_flux':math.fsum(values),'outer_estimated_absolute_error':math.fsum(errors) if adaptive else None,
            'edges':edges,'inner_Gauss_order':order,'outer_method':'QUADPACK' if adaptive else 'GaussLegendre'}


def run(args):
    import OCP
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS,TopoDS_Shape
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.gp import gp_Pnt
    if args.output.exists() or OCP.__version__!='8.0.1.0' or native.sha256(args.input)!=BODY_SHA:
        raise ValueError('exact_input_runtime_and_new_output_required')
    start=time.monotonic();source_hash=native.sha256(__file__)
    def faces(shape):
        result=[];ex=TopExp_Explorer(shape,TopAbs_FACE)
        while ex.More():result.append(TopoDS.Face(ex.Current()));ex.Next()
        return result
    witness=faces(BRepPrimAPI_MakeBox(gp_Pnt(31,-27,48),2,3,4).Shape())
    witness_sum=math.fsum(integrate_face(f,16,False)['signed_flux'] for f in witness)
    if abs(witness_sum-24)>1e-10: raise ValueError('translated_box_witness_failed')
    shape=TopoDS_Shape()
    if not BRepTools.Read_s(shape,str(args.input),BRep_Builder()):raise ValueError('native_read_failed')
    allfaces=faces(shape)
    if len(allfaces)!=4918:raise ValueError('exact_face_count_required')
    report={'schema':'m64-independent-trim-flux/v1','status':'incomplete','input_sha256':BODY_SHA,
        'source_sha256':source_hash,'OCP_version':OCP.__version__,'witness_volume':witness_sum,
        'analytic_witness_expected':24,'CAD_modified':False,'manufacturing_authorized':False,
        'rigorous_interval_certificate':False,'results':[]}
    native.save(args.output,report)
    try:
        for index in args.faces:
            if not 1<=index<=len(allfaces):raise ValueError('invalid_face_index')
            for order,adaptive in ((32,False),(64,False),(64,True),(128,True)):
                began=time.monotonic();row=integrate_face(allfaces[index-1],order,adaptive)
                row.update(face_index=index,elapsed_seconds=time.monotonic()-began)
                report['results'].append(row);native.save(args.output,report)
                print(json.dumps(row),flush=True)
        report['status']='completed'
    except Exception as exc:report.update(status='failed',error_type=type(exc).__name__,error=str(exc))
    finally:
        report.update(elapsed_seconds=time.monotonic()-start,
            inputs_unchanged=native.sha256(args.input)==BODY_SHA and native.sha256(__file__)==source_hash)
        native.save(args.output,report)
    return 0 if report['status']=='completed' else 2


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('input','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--faces',type=int,nargs='+',default=[582,710,711,712,713])
    raise SystemExit(run(p.parse_args()))
