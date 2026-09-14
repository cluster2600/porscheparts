#!/usr/bin/env python3
"""One native same-support partition experiment, not CFD or manufacturing release.

Only edges 101/102/103/104 of exact gas7fc may lose their face-partition role.
An explicit second mode also allows recontextualizing face40's native seam105.
Every other edge is protected; no edge unification or BSpline concatenation.
The resulting BRep requires an independent geometry and boundary-role review.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import resource
import time

DOMAIN='7fc114c1a8229665047c734fd22129783df420deb5e01e809995c6b3efdc5de8'
NEIGHBORHOOD='c904246872807c237bdd7f2e77fad928ba7f10e92cb5b0f33e2e179e052a89e5'
RIM='2986093394e5cf86056b32623842d68726678c1977062220f10389a543ea43aa'
SUPPORT='99e3d4e8ec46410ee7aee6340936038148514675fcd80bb9b67a8c4459df7f3f'
SELECTED=(37,38,40)
INTERNAL={101:(37,40),102:(37,38),103:(38,40),104:(38,40)}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_selection(faces,incidences):
    if set(faces)!=set(SELECTED):raise ValueError('exact_three_port_faces_required')
    for row in faces.values():
        if (row.get('role')!='walls_port' or row.get('support_sha256')!=SUPPORT or
                row.get('source_match')!=[{'source':'raw_intake_face_8','role':'walls_port'}]):
            raise ValueError('same_support_same_source_same_physical_role_required')
    if incidences!=INTERNAL:raise ValueError('only_four_recorded_internal_edges_may_be_unprotected')


def unprotected_edges(allow_seam, seam_incidence, native_seam_closed):
    if type(allow_seam) is not bool:raise ValueError('explicit_boolean_seam_mode_required')
    if allow_seam and (seam_incidence!=(40,) or native_seam_closed is not True):
        raise ValueError('only_native_closed_face40_seam105_may_be_recontextualized')
    return set(INTERNAL)|({105} if allow_seam else set())


def protected_geometry_retained(report):
    allowed=set(report.get('unprotected_original_edges',[]))
    retained=report.get('in_memory_edge_identity_retained_original_ids',[])
    original=set(range(1,196))
    return (report.get('source_in_memory_serialization_unchanged') is True and
        allowed in (set(INTERNAL),set(INTERNAL)|{105}) and
        len(retained)==len(set(retained)) and set(retained)<=original and
        original-allowed<=set(retained))


def run(args):
    import OCP
    from OCP.BRep import BRep_Builder,BRep_Tool
    from OCP.BRepTools import BRepTools
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
    from OCP.GeomTools import GeomTools
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    from OCP.TopAbs import TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX,TopAbs_SOLID
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopoDS import TopoDS,TopoDS_Shape

    started=time.monotonic();domain=args.domain.resolve();output=args.output.resolve()
    inputs={domain:DOMAIN,args.neighborhood.resolve():NEIGHBORHOOD,args.rim.resolve():RIM,Path(__file__).resolve():sha(__file__)}
    if any(sha(p)!=h for p,h in inputs.items()):raise ValueError('exact_native_inputs_required')
    if output.exists() or args.output.is_symlink():raise FileExistsError(output)
    output.mkdir(parents=True,mode=0o700)
    report={'schema':'m64-native-port-partition-unification/v1','status':'running',
        'native_input_sha256':DOMAIN,'neighborhood_sha256':NEIGHBORHOOD,'rim_inventory_sha256':RIM,'source_sha256':sha(__file__),
        'OCP_version':OCP.__version__,'selected_original_faces':list(SELECTED),
        'unprotected_original_edges':sorted(INTERNAL),'UnifyEdges':False,'UnifyFaces':True,
        'ConcatBSplines':False,'safe_input_mode':True,'allow_internal_edges':False,
        'tolerance_setters_called':False,'CFD_executed':False,'manufacturing_authorized':False,
        'boundary_roles_transferred':False,'independent_geometry_review_required':True}
    def save():
        report['elapsed_seconds']=time.monotonic()-started
        (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    def indexed(shape,kind):
        result=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(shape,kind,result);return result
    def read(path):
        shape=TopoDS_Shape()
        if not BRepTools.Read_s(shape,str(path),BRep_Builder()):raise ValueError('native_read_failed')
        return shape
    def encoded(shape):
        stream=io.BytesIO();BRepTools.Write_s(shape,stream);return stream.getvalue()
    def support_hash(face):
        stream=io.BytesIO();GeomTools.Write_s(BRep_Tool.Surface_s(face),stream)
        return hashlib.sha256(stream.getvalue()).hexdigest()
    save()
    try:
        source=read(domain);faces=indexed(source,TopAbs_FACE);edges=indexed(source,TopAbs_EDGE)
        if (faces.Extent(),edges.Extent())!=(88,195):raise ValueError('source_topology_mismatch')
        neighbor=json.loads(args.neighborhood.read_text())
        metadata={r['native_face_id']:r for r in neighbor['faces']}
        selected={i:{'role':metadata[i]['role'],'source_match':metadata[i]['source_match'],
            'support_sha256':support_hash(TopoDS.Face_s(faces.FindKey(i)))} for i in SELECTED}
        memberships={i:indexed(faces.FindKey(i),TopAbs_EDGE) for i in range(1,89)}
        all_incidence={eid:tuple(i for i,m in memberships.items() if m.Contains(edges.FindKey(eid))) for eid in range(1,196)}
        incidence={eid:fs for eid,fs in all_incidence.items() if len(fs)==2 and set(fs)<=set(SELECTED)}
        validate_selection(selected,incidence)
        seam_closed=BRep_Tool.IsClosed_s(TopoDS.Edge_s(edges.FindKey(105)),TopoDS.Face_s(faces.FindKey(40)))
        allowed=unprotected_edges(args.allow_native_seam105,all_incidence[105],seam_closed)
        report['seam105']={'explicit_recontextualization_requested':args.allow_native_seam105,
            'native_closed_on_face40':seam_closed,'unique_incident_faces':list(all_incidence[105]),
            'not_a_physical_patch_interface':all_incidence[105]==(40,)}
        report['unprotected_original_edges']=sorted(allowed)
        supports=[BRep_Tool.Surface_s(TopoDS.Face_s(faces.FindKey(i))) for i in SELECTED]
        report['selected_support_handles_equal']=all(supports[0]==s for s in supports[1:])
        report['selected_locations_equal']=all(faces.FindKey(SELECTED[0]).Location().IsEqual(faces.FindKey(i).Location()) for i in SELECTED[1:])
        source_encoded=encoded(source)
        tool=ShapeUpgrade_UnifySameDomain(source,False,True,False)
        tool.SetSafeInputMode(True);tool.AllowInternalEdges(False)
        for eid in range(1,196):
            if eid not in allowed:tool.KeepShape(edges.FindKey(eid))
        report['protected_edge_count']=195-len(allowed)
        report['stage']='native_unification';save();tool.Build();candidate=tool.Shape()
        report['source_in_memory_serialization_unchanged']=encoded(source)==source_encoded
        newfaces=indexed(candidate,TopAbs_FACE);newedges=indexed(candidate,TopAbs_EDGE)
        report['in_memory_edge_identity_retained_original_ids']=[i for i in range(1,196) if newedges.Contains(edges.FindKey(i))]
        history=tool.History();history_rows=[]
        for i in range(1,89):
            old=faces.FindKey(i)
            history_rows.append({'original_face_id':i,'retained_by_identity':newfaces.Contains(old),
                'modified_candidate_face_ids':[newfaces.FindIndex(s) for s in history.Modified(old)],
                'removed':history.IsRemoved(old)})
        report['face_history_private']=history_rows
        path=output/'candidate.brep'
        if not BRepTools.Write_s(candidate,str(path)):raise ValueError('candidate_export_failed')
        path.chmod(0o600);report['candidate_sha256']=sha(path);report['stage']='candidate_exported';save()
        result=read(path)
        report['topology']={name:indexed(result,kind).Extent() for name,kind in
            (('solids',TopAbs_SOLID),('faces',TopAbs_FACE),('edges',TopAbs_EDGE),('vertices',TopAbs_VERTEX))}
        report['BRep_valid_after_reread']=BRepCheck_Analyzer(result,True,False,True).IsValid()
        job=BOPAlgo_ArgumentAnalyzer();job.SetShape1(result)
        for mode in ('SelfInterMode','SmallEdgeMode','RebuildFaceMode','ContinuityMode','CurveOnSurfaceMode'):
            setattr(job,mode,True)
        job.Perform()
        report['BOP']={'has_faulty':job.HasFaulty(),'has_errors':job.HasErrors(),'has_warnings':job.HasWarnings(),
            'faults':[str(x.GetCheckStatus()).split('.')[-1] for x in job.GetCheckResult()]}
        report['status']='candidate_generated_pending_independent_equivalence_review'
        if all(row['retained_by_identity'] and not row['modified_candidate_face_ids'] for row in history_rows):
            report['status']='native_noop_no_partition_correction'
        if not report['BRep_valid_after_reread'] or any(report['BOP'][k] for k in ('has_faulty','has_errors','has_warnings')):
            report['status']='native_candidate_rejected'
        report['protected_geometry_guard_passed']=protected_geometry_retained(report)
        if not report['protected_geometry_guard_passed']:
            report['status']='rejected_protected_geometry_contract'
    except Exception as exc:
        report['status']='partial_or_rejected';report['error']=type(exc).__name__+': '+str(exc)
    report['inputs_unchanged']=all(sha(p)==h for p,h in inputs.items());save()
    print(json.dumps({k:report.get(k) for k in ('status','candidate_sha256','topology','elapsed_seconds','error')}))
    return 0 if report['status']=='candidate_generated_pending_independent_equivalence_review' and report['inputs_unchanged'] else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('domain','neighborhood','rim','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--allow-native-seam105',action='store_true',help='Explicitly permit recontextualizing the verified closed seam of native face40; no functional boundary is unprotected')
    resource.setrlimit(resource.RLIMIT_CPU,(60,65))
    raise SystemExit(run(parser.parse_args()))
