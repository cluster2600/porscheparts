#!/usr/bin/env python3
"""Bounded local repairs at diagnosed acute cylindrical intersections.

No contour propagation, relaxed tolerance, automatic adoption or CAE release.
"""
import argparse
import io
import json
from pathlib import Path
import signal
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_parallel_cad_trials as batch
from trial_fixed_boundary_seam import read_native, indexed, tolerances
from build_local_port_junction_fillet import build_fillet, STRICT_PARAMETERS

PAIRS=((141,142),(142,143),(1647,1648))


def admitted(report, pair, allowed, changed):
    return (set(pair)<=set(changed)<=set(allowed)
        and type(report.get('solid_count')) is int and report['solid_count']==1
        and all(report.get(key) is True for key in ('native_valid','protected_unchanged',
            'source_in_memory_unchanged','tolerances_not_increased')))


def run(args):
    import OCP
    from OCP.BRepTools import BRepTools
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet,BRepFilletAPI_MakeChamfer
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Defeaturing
    from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX,TopAbs_SOLID
    from OCP.TopoDS import TopoDS
    if (args.pair not in PAIRS or args.output.exists()
            or (args.defeature and (args.pair!=(1647,1648) or args.radius is not None))
            or (not args.defeature and args.radius not in (.005,.02,.05))
            or args.body.is_symlink() or batch.native.sha256(args.body)!=batch.BODY_SHA
            or OCP.__version__!='7.9.3.1'):
        raise ValueError('bounded_inputs_required')
    args.output.mkdir(mode=0o700)
    source_sha=batch.native.sha256(__file__)
    report=dict(schema='m64-acute-cylinder-blend/v1',status='incomplete',pair=args.pair,
        size_scan_units=args.radius,operation='defeature_1648' if args.defeature else ('chamfer' if args.chamfer else 'fillet'),
        size_semantics=None if args.defeature else ('symmetric_distance' if args.chamfer else 'fillet_radius'),
        input_sha256=batch.BODY_SHA,source_sha256=source_sha,
        master_replaced=False,manufacturing_authorized=False,surface_deviation_certified=False)
    target=args.output/'report.json'
    def save(): batch.native.save(target,report)
    def encoded(shape):
        stream=io.BytesIO();BRepTools.Write_s(shape,stream);return stream.getvalue()
    start=time.monotonic();signal.alarm(300);save()
    try:
        body=read_native(args.body);before=encoded(body);faces=indexed(body,TopAbs_FACE)
        if len(faces)!=4918 or not BRepCheck_Analyzer(body,True,False,True).IsValid():
            raise ValueError('valid_reference_required')
        ea,eb=[indexed(faces[i-1],TopAbs_EDGE) for i in args.pair]
        shared=[a for a in ea if any(a.IsSame(b) for b in eb)]
        if len(shared)!=1:raise ValueError('one_shared_edge_required')
        vertices=indexed(faces[1647] if args.defeature else shared[0],TopAbs_VERTEX)
        allowed={i for i,f in enumerate(faces,1) if any(v.IsSame(w) for v in indexed(f,TopAbs_VERTEX) for w in vertices)}
        if not set(args.pair)<=allowed or len(allowed)>8:raise ValueError('bounded_endpoint_patch_required')
        protected={i:encoded(f) for i,f in enumerate(faces,1) if i not in allowed}
        before_tol=tolerances(body)
        report['allowed_faces']=sorted(allowed)
        save()
        if args.defeature:
            op=BRepAlgoAPI_Defeaturing();op.SetShape(body);op.SetRunParallel(False)
            op.SetToFillHistory(True);op.AddFaceToRemove(faces[1647]);op.Build()
            # OCP 7.9.3.1 does not expose OCCT's error/warning accessors here.
            build=dict(done=op.IsDone(),warning_introspection_available=False,
                       tolerance_setters_called=False,selected_face_deleted=op.IsDeleted(faces[1647]))
            if not op.IsDone() or not build['selected_face_deleted']:
                report['build']=build;raise ValueError('selected_face_not_removed')
        else:
            op=BRepFilletAPI_MakeChamfer(body) if args.chamfer else BRepFilletAPI_MakeFillet(body)
            if not args.chamfer:op.SetParams(*STRICT_PARAMETERS)
            op.Add(args.radius,TopoDS.Edge_s(shared[0]))
            report.update(contours=op.NbContours(),contour_edges=op.NbEdges(1));save()
            if op.NbContours()!=1 or op.NbEdges(1)!=1:raise ValueError('contour_propagation_rejected')
            if args.chamfer:
                op.Build();build=dict(done=op.IsDone(),contours=op.NbContours(),tolerance_setters_called=False)
            else:
                op,build=build_fillet(body,[TopoDS.Edge_s(shared[0])],args.radius,'strict-approximation-v1')
        report['build']=build
        if not op.IsDone():raise ValueError('native_blend_failed')
        result=op.Shape();after=indexed(result,TopAbs_FACE)
        changed={i for i,f in enumerate(faces,1) if not any(f.IsSame(g) for g in after)}
        after_tol=tolerances(result)
        report.update(changed_faces=sorted(changed),native_valid=BRepCheck_Analyzer(result,True,False,True).IsValid(),
            solid_count=len(indexed(result,TopAbs_SOLID)),
            protected_unchanged=all(encoded(faces[i-1])==v for i,v in protected.items()),
            source_in_memory_unchanged=encoded(body)==before,
            before_max_tolerances={k:max(v) for k,v in before_tol.items()},
            after_max_tolerances={k:max(v) for k,v in after_tol.items()})
        report['tolerances_not_increased']=all(max(after_tol[k])<=max(before_tol[k]) for k in before_tol)
        if not admitted(report,args.pair,allowed,changed):
            if (args.defeature and report['native_valid'] and report['solid_count']==1
                    and report['tolerances_not_increased']):
                # Retain the rejected topology privately to diagnose propagation,
                # not to bypass the locality guard or nominate a master.
                rejected=args.output/'rejected-native.brep'
                if not BRepTools.Write_s(result,str(rejected)):raise ValueError('diagnostic_write_failed')
                rejected.chmod(0o600)
                report['rejected_diagnostic_sha256']=batch.native.sha256(rejected)
                from OCP.TopTools import TopTools_IndexedMapOfShape
                after_map=TopTools_IndexedMapOfShape()
                for face in after:after_map.Add(face)
                report['modified_face_history_private']={str(i):[after_map.FindIndex(m)
                    for m in op.Modified(faces[i-1])] for i in sorted(changed)}
            raise ValueError('native_locality_or_tolerance_guard_failed')
        path=args.output/'candidate.brep'
        if not BRepTools.Write_s(result,str(path)):raise ValueError('native_write_failed')
        path.chmod(0o600)
        if not BRepCheck_Analyzer(read_native(path),True,False,True).IsValid():raise ValueError('readback_invalid')
        report.update(status='candidate_pending_BOP_deviation_volume_and_remesh',candidate_sha256=batch.native.sha256(path))
    except Exception as error:
        report.update(status='rejected',error=type(error).__name__+': '+str(error))
    finally:
        signal.alarm(0)
        report.update(seconds=time.monotonic()-start,inputs_unchanged=batch.native.sha256(args.body)==batch.BODY_SHA and batch.native.sha256(__file__)==source_sha)
        if not report['inputs_unchanged']: report['status']='rejected_input_changed'
        save()
    print(json.dumps(report))
    return 0 if report['status'].startswith('candidate_pending') else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('body','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--pair',nargs=2,type=int,required=True)
    parser.add_argument('--radius','--size',dest='radius',type=float,choices=(.005,.02,.05))
    operation=parser.add_mutually_exclusive_group()
    operation.add_argument('--chamfer',action='store_true',help='Interpret size as symmetric chamfer distance.')
    operation.add_argument('--defeature',action='store_true',help='Remove face 1648 only; omit size.')
    args=parser.parse_args();args.pair=tuple(sorted(args.pair))
    raise SystemExit(run(args))
