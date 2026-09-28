#!/usr/bin/env python3
"""Remove only the verified coplanar partition 1243/1481 of the pinned body.

All other native edges are protected. This is a private topology candidate,
not an accepted assembly, deviation certificate or manufacturing release.
"""
import argparse
import io
import json
from pathlib import Path
import signal
import time

from run_local_surface_trial import BODY_SHA, native

SELECTED={1243,1481}


def protected_partition(changed, removed, allowed, faces, edges):
    return (set(changed)==SELECTED and len(changed)==2 and len(allowed)==5
            and set(removed)==set(allowed) and len(removed)==5
            and faces==4917 and edges==10205)


def run(args):
    import OCP
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_SOLID,TopAbs_SHELL
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopoDS import TopoDS,TopoDS_Shape
    if args.input.is_symlink() or native.sha256(args.input)!=BODY_SHA or OCP.__version__!='7.9.3.1':
        raise ValueError('exact_native_body_and_OCP_required')
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    started=time.monotonic(); source_hash=native.sha256(__file__)
    receipt={'schema':'m64-coplanar-mesh-partition/v1','status':'incomplete','input_sha256':BODY_SHA,
        'source_sha256':source_hash,'OCP_version':OCP.__version__,'selected_source_faces':sorted(SELECTED),
        'master_replaced':False,'manufacturing_authorized':False,'CAE_authorized':False,
        'tolerance_setters_called':False,'UnifyEdges':False,'ConcatBSplines':False,
        'safe_input_mode':True,'boundary_roles_transferred':False}
    target=args.output/'report.json'; native.save(target,receipt)
    def read(path):
        result=TopoDS_Shape()
        if not BRepTools.Read_s(result,str(path),BRep_Builder()): raise ValueError('native_read_failed')
        return result
    def indexed(shape,kind):
        result=TopTools_IndexedMapOfShape(); TopExp.MapShapes_s(shape,kind,result); return result
    def encoded(shape):
        stream=io.BytesIO(); BRepTools.Write_s(shape,stream); return stream.getvalue()
    def properties(shape):
        area,volume=GProp_GProps(),GProp_GProps()
        BRepGProp.SurfaceProperties_s(shape,area); BRepGProp.VolumeProperties_s(shape,volume)
        return {'area':area.Mass(),'volume':volume.Mass()}
    try:
        body=read(args.input); original=encoded(body)
        faces=indexed(body,TopAbs_FACE); edges=indexed(body,TopAbs_EDGE)
        if (faces.Extent(),edges.Extent())!=(4918,10210): raise ValueError('exact_source_topology_required')
        a,b=[TopoDS.Face_s(faces.FindKey(i)) for i in sorted(SELECTED)]
        sa,sb=[BRepAdaptor_Surface(f) for f in (a,b)]
        if sa.GetType()!=GeomAbs_Plane or sb.GetType()!=GeomAbs_Plane: raise ValueError('planar_pair_required')
        pa,pb=sa.Plane(),sb.Plane()
        receipt['plane_angle']=pa.Axis().Direction().Angle(pb.Axis().Direction())
        receipt['plane_distance']=pa.Distance(pb.Location())
        if (receipt['plane_angle']>1e-12 or receipt['plane_distance']>1e-12
                or a.Orientation()!=b.Orientation()): raise ValueError('coincident_oriented_planes_required')
        ea,eb=[indexed(f,TopAbs_EDGE) for f in (a,b)]
        allowed={i for i in range(1,edges.Extent()+1) if ea.Contains(edges.FindKey(i)) and eb.Contains(edges.FindKey(i))}
        if len(allowed)!=5: raise ValueError('exact_five_shared_edges_required')
        incidence={i:[] for i in allowed}
        for fi in range(1,faces.Extent()+1):
            face_edges=indexed(faces.FindKey(fi),TopAbs_EDGE)
            for ei in allowed:
                if face_edges.Contains(edges.FindKey(ei)): incidence[ei].append(fi)
        if any(set(ids)!=SELECTED for ids in incidence.values()): raise ValueError('nonmanifold_partition')
        receipt['unprotected_edge_incidence_private']=incidence
        tool=ShapeUpgrade_UnifySameDomain(body,False,True,False)
        tool.SetSafeInputMode(True); tool.AllowInternalEdges(False)
        for i in range(1,edges.Extent()+1):
            if i not in allowed: tool.KeepShape(edges.FindKey(i))
        tool.Build(); result=tool.Shape()
        nf,ne=indexed(result,TopAbs_FACE),indexed(result,TopAbs_EDGE)
        changed=[i for i in range(1,faces.Extent()+1) if not nf.Contains(faces.FindKey(i))]
        removed=[i for i in range(1,edges.Extent()+1) if not ne.Contains(edges.FindKey(i))]
        merged=[i for i in range(1,nf.Extent()+1) if not faces.Contains(nf.FindKey(i))]
        receipt.update(changed_source_faces=changed,removed_source_edges=removed,
                       candidate_faces=nf.Extent(),candidate_edges=ne.Extent(),merged_candidate_faces=merged)
        if not protected_partition(changed,removed,allowed,nf.Extent(),ne.Extent()) or len(merged)!=1:
            raise ValueError('protected_partition_guard_failed')
        mf=TopoDS.Face_s(nf.FindKey(merged[0])); boundary=indexed(mf,TopAbs_EDGE)
        expected={i for i in range(1,edges.Extent()+1) if i not in allowed and
                  (ea.Contains(edges.FindKey(i)) or eb.Contains(edges.FindKey(i)))}
        got={i for i in range(1,edges.Extent()+1) if boundary.Contains(edges.FindKey(i))}
        m=BRepAdaptor_Surface(mf)
        if (boundary.Extent()!=len(expected) or got!=expected or m.GetType()!=GeomAbs_Plane
                or m.Plane().Distance(pa.Location())>1e-12
                or m.Plane().Axis().Direction().Angle(pa.Axis().Direction())>1e-12
                or mf.Orientation()!=a.Orientation()): raise ValueError('merged_support_or_perimeter_changed')
        receipt['merged_perimeter_original_edge_ids']=sorted(expected)
        receipt['source_in_memory_unchanged']=encoded(body)==original
        if not receipt['source_in_memory_unchanged']: raise ValueError('source_mutated')
        output=args.output/'candidate.brep'
        if not BRepTools.Write_s(result,str(output)): raise ValueError('native_export_failed')
        output.chmod(0o600); reread=read(output)
        receipt['candidate_sha256']=native.sha256(output)
        receipt['native_readback_exact_valid']=BRepCheck_Analyzer(reread,True,False,True).IsValid()
        receipt['readback_counts']={k:indexed(reread,v).Extent() for k,v in
            [('solids',TopAbs_SOLID),('shells',TopAbs_SHELL),('faces',TopAbs_FACE),('edges',TopAbs_EDGE)]}
        before,after=properties(body),properties(reread)
        receipt.update(before=before,after=after)
        receipt['relative_integral_differences']={k:abs(after[k]/before[k]-1) for k in before}
        if (not receipt['native_readback_exact_valid'] or receipt['readback_counts']!=
                {'solids':1,'shells':1,'faces':4917,'edges':10205}
                or any(v>1e-10 for v in receipt['relative_integral_differences'].values())):
            raise ValueError('native_readback_invariants_failed')
        receipt['status']='candidate_generated_pending_independent_review_and_remesh'
    except Exception as error:
        receipt.update(status='failed',error_type=type(error).__name__,error=str(error))
    finally:
        receipt['inputs_unchanged']=native.sha256(args.input)==BODY_SHA and native.sha256(__file__)==source_hash
        receipt['elapsed_seconds']=time.monotonic()-started
        native.save(target,receipt)
    print(json.dumps({k:receipt.get(k) for k in ('status','candidate_sha256','candidate_faces','elapsed_seconds','error')}))
    return 0 if receipt['status'].startswith('candidate_generated') and receipt['inputs_unchanged'] else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('input','output'): parser.add_argument('--'+name,type=Path,required=True)
    signal.alarm(300)
    raise SystemExit(run(parser.parse_args()))
