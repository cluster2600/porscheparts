#!/usr/bin/env python3
"""Segment the exact native gas-domain C0 edge; retain all failed candidates.

No dimensions, face labels or physical qualification are inferred. Outputs are
private native geometry and diagnostic receipts, never a manufacturing release.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import time

DOMAIN_SHA='3f20f4c56a3f4bfd5c7f580302dfa08e160ebb13abc3c5217a98312cc48653f3'


def parameter_equal(a,b):
    return (math.isfinite(a) and math.isfinite(b) and
            abs(a-b)<=8*max(math.ulp(a),math.ulp(b),math.ulp(1.)))


def complete_partition(bounds,segments):
    """Parameter-space identity, not a spatial or physical error bound."""
    return (len(bounds)==5 and len(segments)==4 and
        all(math.isfinite(x) for x in bounds) and
        all(a<b for a,b in zip(bounds,bounds[1:])) and
        all(len(span)==2 and parameter_equal(span[0],a) and parameter_equal(span[1],b)
            for span,a,b in zip(segments,bounds,bounds[1:])))


def native_checks_pass(report):
    return bool(report.get('input_unchanged') is True and
        report.get('parameter_partition_preserved') is True and
        report.get('local_edge_tolerances_not_increased') is True and
        report.get('valid_after_native_reread') is True and
        report.get('topology')=={'solids':1,'faces':88,'edges':195,'vertices':120} and
        report.get('BOP')=={'has_faulty':False,'has_errors':False,'has_warnings':False,'faults':[]})


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args):
    import OCP
    from OCP.BRep import BRep_Builder,BRep_Tool
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape,TopoDS
    from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_SOLID,TopAbs_VERTEX
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepLib import BRepLib
    from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
    from OCP.ShapeUpgrade import ShapeUpgrade_ShapeDivideContinuity
    from OCP.GeomAbs import GeomAbs_C0,GeomAbs_C1
    started=time.monotonic();domain=args.domain.resolve();output=args.output.resolve()
    if sha(domain)!=DOMAIN_SHA:raise ValueError('exact_native_domain05_required')
    if output.exists() or args.output.is_symlink():raise FileExistsError(output)
    output.mkdir(parents=True,mode=0o700)
    report={'schema':'m64-native-gas-C0-segmentation/v1','status':'running',
        'input_sha256':DOMAIN_SHA,'source_sha256':sha(__file__),'OCP_version':OCP.__version__,
        'CFD_qualified':False,'manufacturing_authorized':False,
        'independent_geometry_review_required':True,
        'target_edge_original_id':97,'adjacent_original_face_ids':[36,37],
        'knot_removal_tolerance_requested':0.,'physical_corners_not_smoothed':True}
    def save():
        report['elapsed_seconds']=time.monotonic()-started
        (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    def indexed(s,k):
        m=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(s,k,m);return m
    def read(p):
        s=TopoDS_Shape()
        if not BRepTools.Read_s(s,str(p),BRep_Builder()):raise ValueError('native_read_failed')
        return s
    def export(s,name):
        p=output/name;BRepTools.Write_s(s,str(p));p.chmod(0o600);return p
    def state(e,faces):
        return {'range_3D':BRep_Tool.Range_s(e),'same_range':BRep_Tool.SameRange_s(e),
            'same_parameter':BRep_Tool.SameParameter_s(e),'tolerance':BRep_Tool.Tolerance_s(e),
            'pcurve_ranges':[BRep_Tool.Range_s(e,TopoDS.Face_s(faces.FindKey(i))) for i in (36,37)]}
    save()
    try:
        original=read(domain);edges=indexed(original,TopAbs_EDGE)
        old=TopoDS.Edge_s(edges.FindKey(97));curve=BRepAdaptor_Curve(old);basis=curve.Curve().Curve()
        knots=[basis.Knot(i) for i in range(2,basis.NbKnots())
            if curve.FirstParameter()<basis.Knot(i)<curve.LastParameter() and basis.Multiplicity(i)==basis.Degree()]
        bounds=[curve.FirstParameter(),*knots,curve.LastParameter()]
        if len(knots)!=3 or BRep_Tool.Tolerance_s(old)!=5e-6:raise ValueError('recorded_C0_curve_required')
        report['split_parameters_private']=bounds
        tool=ShapeUpgrade_ShapeDivideContinuity(original)
        tool.SetBoundaryCriterion(GeomAbs_C1);tool.SetSurfaceCriterion(GeomAbs_C0)
        tool.SetPCurveCriterion(GeomAbs_C0);tool.SetEdgeMode(2)
        tool.SetTolerance(0.);tool.SetTolerance2d(0.);tool.SetPrecision(1e-7)
        tool.SetMinTolerance(1e-7);tool.SetMaxTolerance(5e-6)
        tool.Perform();split=tool.Result();p=export(split,'split-before-range-coherence.brep')
        report['split_sha256']=sha(p);report['stage']='split_native_exported';save()
        split=read(p);faces=indexed(split,TopAbs_FACE);edges=indexed(split,TopAbs_EDGE)
        spans=[BRep_Tool.Range_s(TopoDS.Edge_s(edges.FindKey(i))) for i in range(97,101)]
        report['parameter_partition_preserved']=complete_partition(bounds,spans)
        if not report['parameter_partition_preserved']:raise ValueError('complete_original_parameter_partition_required')
        report['range_coherence_operations']=[]
        for i in range(97,101):
            e=TopoDS.Edge_s(edges.FindKey(i));before=state(e,faces)
            if any(not all(parameter_equal(a,b) for a,b in zip(before['range_3D'],pr))
                   for pr in before['pcurve_ranges']):raise ValueError('unexpected_3D_pcurve_range_mismatch')
            BRepLib.SameRange_s(e,1e-7)
            after=state(e,faces)
            report['range_coherence_operations'].append({'edge_id':i,'before':before,'after':after})
            if after['tolerance']>before['tolerance']:raise ValueError('local_tolerance_increase_rejected')
        report['local_edge_tolerances_not_increased']=True
        report['direct_flag_override']=False;report['SameParameter_called']=False
        p=export(split,'candidate.brep');report['candidate_sha256']=sha(p)
        report['stage']='candidate_exported';save()
        result=read(p)
        report['valid_after_native_reread']=BRepCheck_Analyzer(result,True,False,True).IsValid()
        report['topology']={name:indexed(result,kind).Extent() for name,kind in
            [('solids',TopAbs_SOLID),('faces',TopAbs_FACE),('edges',TopAbs_EDGE),('vertices',TopAbs_VERTEX)]}
        job=BOPAlgo_ArgumentAnalyzer();job.SetShape1(result)
        for mode in ('SelfInterMode','SmallEdgeMode','RebuildFaceMode','ContinuityMode','CurveOnSurfaceMode'):
            setattr(job,mode,True)
        job.Perform()
        report['BOP']={'has_faulty':job.HasFaulty(),'has_errors':job.HasErrors(),'has_warnings':job.HasWarnings(),
            'faults':[str(x.GetCheckStatus()).split('.')[-1] for x in job.GetCheckResult()]}
        report['input_unchanged']=sha(domain)==DOMAIN_SHA
        report['status']='native_checks_passed_pending_independent_geometry_review' if native_checks_pass(report) else 'native_candidate_rejected'
    except Exception as e:
        report['status']='partial_or_rejected';report['error']=type(e).__name__+': '+str(e)
    report['input_unchanged']=sha(domain)==DOMAIN_SHA;save()
    print(json.dumps({k:report.get(k) for k in ('status','candidate_sha256','elapsed_seconds','error')}))
    return 0 if native_checks_pass(report) else 2


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--domain',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    resource.setrlimit(resource.RLIMIT_CPU,(120,125))
    raise SystemExit(run(p.parse_args()))
