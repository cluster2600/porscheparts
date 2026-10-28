"""Recognize only the four certified root arcs as analytic cylindrical faces.

Rebuild their pcurves after the parameter change, as required by OCCT's
ShapeCustom_Surface API. All failed replacements remain saved for inspection.
"""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import signal
import sys
import time
import traceback


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--body',type=Path,required=True);p.add_argument('--native-site',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);start=time.monotonic();report=dict(status='incomplete',recognition_tolerance_mm=1e-8,faces=[],manufacturing_authorized=False)
    resource.setrlimit(resource.RLIMIT_CPU,(120,135));signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150 second CAD bound')));signal.alarm(150)
    try:
        sys.path.insert(0,str(a.native_site.resolve()))
        from build123d import import_brep,export_brep,export_step,export_stl,Shape
        from OCP.BRep import BRep_Builder
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.BRepTools import BRepTools,BRepTools_ReShape
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.ShapeCustom import ShapeCustom_Surface
        from OCP.ShapeAnalysis import ShapeAnalysis_Surface
        from OCP.ShapeFix import ShapeFix_Edge,ShapeFix_Face
        from OCP.TopoDS import TopoDS,TopoDS_Face
        from OCP.TopExp import TopExp_Explorer
        from OCP import TopAbs
        from OCP.GeomLProp import GeomLProp_SLProps
        from OCP.gp import gp_Pnt,gp_Vec
        from OCP.OSD import OSD_ThreadPool
        OSD_ThreadPool.DefaultPool_s().Init(1)
        body=import_brep(a.body);replacement=BRepTools_ReShape();builder=BRep_Builder()
        for face in body.faces():
            box=face.bounding_box()
            if not((69<box.min.X<73 or -73<box.max.X<-69)and box.min.Z>-3 and box.max.Z<3):continue
            adaptor=BRepAdaptor_Surface(face.wrapped)
            if not str(adaptor.GetType()).endswith('GeomAbs_BSplineSurface'):continue
            if not face.wrapped.Location().IsIdentity():raise ValueError('Nonidentity local face frame not supported')
            recognition=ShapeCustom_Surface(adaptor.BSpline());surface=recognition.ConvertToAnalytical(1e-8,False)
            if surface is None or surface.DynamicType().Name()!='Geom_CylindricalSurface':raise ValueError('Root face did not recognize as cylinder')
            u0,u1,v0,v1=BRepTools.UVBounds_s(face.wrapped);point=gp_Pnt();du=gp_Vec();dv=gp_Vec();adaptor.D1((u0+u1)/2,(v0+v1)/2,point,du,dv);oldnormal=du.Crossed(dv);uv=ShapeAnalysis_Surface(surface).ValueOfUV(point,1e-8);newnormal=GeomLProp_SLProps(surface,uv.X(),uv.Y(),1,1e-12).Normal();reversed_u=oldnormal.Dot(gp_Vec(newnormal))<0
            if reversed_u:surface.UReverse()
            newface=TopoDS_Face();builder.MakeFace(newface,surface,1e-7);forward=TopoDS.Face_s(face.wrapped.Oriented(TopAbs.TopAbs_FORWARD));wires=TopExp_Explorer(forward,TopAbs.TopAbs_WIRE);pc=[]
            while wires.More():
                wire=TopoDS.Wire_s(wires.Current());builder.Add(newface,wire);edges=TopExp_Explorer(wire,TopAbs.TopAbs_EDGE)
                while edges.More():
                    edge=TopoDS.Edge_s(edges.Current());pc.append(bool(ShapeFix_Edge().FixAddPCurve(edge,newface,False,1e-8)));edges.Next()
                wires.Next()
            fix=ShapeFix_Face(newface);fix.SetPrecision(1e-8);fix.Perform();newface=fix.Face();newface.Orientation(face.wrapped.Orientation());replacement.Replace(face.wrapped,newface)
            cylinder=surface.Cylinder();report['faces'].append(dict(old_bounds_mm=[list(box.min),list(box.max)],recognized_gap_mm=recognition.Gap(),radius_mm=cylinder.Radius(),axis_location_mm=list(cylinder.Location().Coord()),axis_direction=list(cylinder.Axis().Direction().Coord()),parameter_U_reversed=reversed_u,rebuilt_pcurves=pc,new_face_valid=BRepCheck_Analyzer(newface).IsValid()))
            (a.output/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
        if len(report['faces'])!=4:raise ValueError('Expected exactly four replacements')
        raw=replacement.Apply(body.wrapped);BRepTools.Write_s(raw,str(a.output/'candidate-native.brep'));candidate=Shape.cast(raw);valid=BRepCheck_Analyzer(raw).IsValid();report.update(valid=valid,solids=len(candidate.solids()),shells=len(candidate.shells()),source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.body,Path(__file__)]})
        passed=valid and len(candidate.solids())==1 and len(candidate.shells())==1 and all(row['new_face_valid']for row in report['faces'])
        report['status']='four_analytic_root_faces_rebuilt_native_valid'if passed else'analytic_root_rebuild_refused'
        if passed:export_step(candidate,a.output/'candidate.step');BRepTools.Clean_s(raw);export_stl(candidate,a.output/'candidate.stl',tolerance=.015,angular_tolerance=.08)
    except BaseException as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc());raise
    finally:signal.alarm(0);report['elapsed_seconds']=time.monotonic()-start;(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','valid','solids','shells']}));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
