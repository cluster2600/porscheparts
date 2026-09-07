#!/usr/bin/env python3
"""Diagnose native adaptor evaluation and STEP tolerance healing, read-only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source-step','trial-directory','helpers','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2]);resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    prior=json.loads((a.trial_directory/'topology-report.json').read_text())
    face_path=a.trial_directory/'private-replacement-face.step'
    if sha(a.source_step)!=prior['source_sha256']['step'] or sha(face_path)!=prior['replacement_face_sha256']:
        raise ValueError('geometry provenance mismatch')
    sys.path.insert(0,str(a.helpers))
    from audit_brep_f42 import read_step,brepcheck
    from repair_topology_f42_1 import indexed
    from OCP.BRep import BRep_Tool,BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE
    from OCP.TopoDS import TopoDS,TopoDS_Face
    from OCP.BRepAdaptor import BRepAdaptor_Curve,BRepAdaptor_Curve2d,BRepAdaptor_Surface
    from OCP.Adaptor3d import Adaptor3d_CurveOnSurface
    from OCP.GeomLib import GeomLib_CheckCurveOnSurface
    original=BRepBuilderAPI_Copy(read_step(a.source_step)[0],True,False).Shape()
    source=TopoDS.Face_s(indexed(original,TopAbs_FACE).FindKey(prior['selected_face_private']))
    builder=BRep_Builder();control=TopoDS_Face();builder.MakeFace(control,BRep_Tool.Surface_s(source),BRep_Tool.Tolerance_s(source))
    control.Orientation(source.Orientation());builder.Add(control,BRepTools.OuterWire_s(source))
    imported=TopoDS.Face_s(indexed(read_step(face_path)[0],TopAbs_FACE).FindKey(1));edges=indexed(imported,TopAbs_EDGE)
    rows=[]
    for i in range(1,edges.Extent()+1):
        edge=TopoDS.Edge_s(edges.FindKey(i));curve=BRepAdaptor_Curve(edge);pc=BRepAdaptor_Curve2d(edge,imported)
        cos=Adaptor3d_CurveOnSurface(pc,BRepAdaptor_Surface(imported));check=GeomLib_CheckCurveOnSurface(curve);check.Perform(cos)
        row={'edge_order':i,'type':str(pc.GetType()),'imported_edge_tolerance':BRep_Tool.Tolerance_s(edge),
             'done':check.IsDone(),'error_status':check.ErrorStatus()}
        if check.IsDone():
            t=check.MaxParameter();uv=pc.Value(t)
            row.update(reported_adaptor_max=check.MaxDistance(),
                 direct_surface_distance_at_same_parameter=curve.Value(t).Distance(BRep_Tool.Surface_s(imported).Value(uv.X(),uv.Y())),
                 adaptor_distance_at_same_parameter=curve.Value(t).Distance(cos.Value(t)),
                 parameter_fraction=(t-curve.FirstParameter())/(curve.LastParameter()-curve.FirstParameter()))
        rows.append(row)
    result={'schema':'m64-reference-bernstein-adaptor-boundary-diagnostic/v1','source_sha256':sha(a.source_step),
            'replacement_face_sha256':sha(face_path),'topology_report_sha256':sha(a.trial_directory/'topology-report.json'),
            'source_face_reassembly_brepcheck':brepcheck(control),'before_import_face_brepcheck':prior['replacement_face_brepcheck'],
            'imported_face_brepcheck':brepcheck(imported),'original_edge_tolerances':[BRep_Tool.Tolerance_s(TopoDS.Edge_s(indexed(source,TopAbs_EDGE).FindKey(i))) for i in range(1,6)],
            'curve_adaptor_checks':rows,'rejected_despite_import_validity':True,
            'status':'rejected_step_reader_increased_edge_tolerances_do_not_requalify',
            'geometry_modified':False,'manufacturing_authorized':False}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'report_sha256':sha(a.output),'status':result['status'],'curve_adaptor_checks':rows},indent=2))


if __name__=='__main__':main()
