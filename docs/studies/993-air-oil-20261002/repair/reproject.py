#!/usr/bin/env python3
"""Reproject only reported pcurves; reject any changed 3D geometry/tolerance."""
import argparse,json
from pathlib import Path
import build123d as b
import numpy as np
from OCP.BRep import BRep_Tool,BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.ShapeAnalysis import ShapeAnalysis_Surface
from OCP.Geom2dAPI import Geom2dAPI_Interpolate
from OCP.TColgp import TColgp_HArray1OfPnt2d
from OCP.TColStd import TColStd_HArray1OfReal
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Pnt,gp_Vec,gp_Vec2d
from diagnose import check,maps,sha
from local_fix import snapshots,sections

def projection(edge,face,n):
    curve=BRepAdaptor_Curve(edge);lo,hi=curve.FirstParameter(),curve.LastParameter()
    old=BRep_Tool.CurveOnSurface_s(edge,face,0.,0.)
    surf=BRep_Tool.Surface_s(face); projector=ShapeAnalysis_Surface(surf)
    points=TColgp_HArray1OfPnt2d(1,n); params=TColStd_HArray1OfReal(1,n)
    uvpoints=[];errors=[]
    for i,t in enumerate(np.linspace(lo,hi,n),1):
        p=curve.Value(float(t));uv=projector.NextValueOfUV(old.Value(float(t)),p,1e-12,1e-8)
        errors.append(surf.Value(uv.X(),uv.Y()).Distance(p));uvpoints.append(uv)
        points.SetValue(i,uv);params.SetValue(i,float(t))
    interp=Geom2dAPI_Interpolate(points,params,False,1e-12)
    tangent=[]
    for t,uv in [(lo,uvpoints[0]),(hi,uvpoints[-1])]:
        p=gp_Pnt();du=gp_Vec();dv=gp_Vec();surf.D1(uv.X(),uv.Y(),p,du,dv)
        p3=gp_Pnt();d3=gp_Vec();curve.D1(t,p3,d3)
        jac=np.array([[du.X(),dv.X()],[du.Y(),dv.Y()],[du.Z(),dv.Z()]])
        derivative=np.linalg.lstsq(jac,np.array([d3.X(),d3.Y(),d3.Z()]),rcond=None)[0]
        tangent.append(gp_Vec2d(*derivative))
    interp.Load(*tangent,False);interp.Perform()
    if not interp.IsDone():raise ValueError('pcurve_interpolation_failed')
    return interp.Curve(),max(errors)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('input',type=Path);ap.add_argument('output',type=Path)
    ap.add_argument('--nodes',type=int,default=129);a=ap.parse_args();a.output.mkdir()
    original=sha(a.input);s=b.import_step(a.input);idx=maps(s.wrapped)
    before=check(s,['CurveOnSurfaceMode'],True);r={'input_sha256':original,'method':'localized_projected_pcurve_with_constrained_endpoint_derivatives','nodes':a.nodes,'before':before,'changes':[]}
    BRepTools.Write_s(s.wrapped,str(a.output/'before.brep'));tolbefore=snapshots(idx)
    for fault in before['faults']:
        es=[x['ids']['edge'] for x in fault['faulty_shapes_1'] if x.get('ids',{}).get('edge')]
        fs=[x['ids']['face'] for x in fault['faulty_shapes_1'] if x.get('ids',{}).get('face')]
        if len(es)!=1 or len(fs)!=1:raise ValueError('requires_one_edge_face_pair')
        eid,fid=es[0],fs[0];e=TopoDS.Edge_s(idx['edge'].FindKey(eid));f=TopoDS.Face_s(idx['face'].FindKey(fid));tol=BRep_Tool.Tolerance_s(e)
        pc,floor=projection(e,f,a.nodes)
        if floor>tol:raise ValueError('3D_curve_outside_surface_tolerance_cannot_pcurve_fix')
        BRep_Builder().UpdateEdge(e,pc,f,tol)
        r['changes'].append({'edge':eid,'face':fid,'sampled_projection_floor_not_continuous_bound':floor,'edge_tolerance_before':tol,'edge_tolerance_after':BRep_Tool.Tolerance_s(e)})
    BRepTools.Write_s(s.wrapped,str(a.output/'corrected.brep'))
    r['all_tolerances_unchanged']=tolbefore==snapshots(idx)
    r['serialized_3D_geometry_unchanged']=sections(a.output/'before.brep')==sections(a.output/'corrected.brep')
    r['after_native']=check(s,['CurveOnSurfaceMode'],True)
    (a.output/'preexport.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        # Rewrap topology to avoid retaining the importer's XDE scene hierarchy.
        b.export_step(b.Compound.cast(s.wrapped),a.output/'corrected.step')
        reread=b.import_step(a.output/'corrected.step');r['after_STEP']=check(reread,['CurveOnSurfaceMode'],True)
        r['relative_volume_delta']=abs(s.volume-reread.volume)/s.volume
    except Exception as exc:
        r['after_STEP']={'passed':False};r['export_error']=str(exc)
    r['input_unchanged']=sha(a.input)==original
    r['accepted']=r['all_tolerances_unchanged'] and r['serialized_3D_geometry_unchanged'] and r['after_native']['passed'] and r['after_STEP']['passed']
    (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ['before','after_native','after_STEP']}),flush=True)
    print('native',r['after_native']['passed'],'STEP',r['after_STEP']['passed'],flush=True)

if __name__=='__main__':main()
