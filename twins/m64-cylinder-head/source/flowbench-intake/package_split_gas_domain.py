#!/usr/bin/env python3
"""Export private faces from the exact reviewed C0-segmented native domain.

This is a provenance-preserving packet, not a new gas construction or a release.
No STEP, local-neck acceptance or manufacturing permission is inferred.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import resource
import shutil
import time

OLD='3f20f4c56a3f4bfd5c7f580302dfa08e160ebb13abc3c5217a98312cc48653f3'
NEW='7fc114c1a8229665047c734fd22129783df420deb5e01e809995c6b3efdc5de8'
MANIFEST='e95d7aa7000d0c82d5bdb9e83b57151cb041795d31380f4a802ab47bda155536'
REVIEW='7cb1fecc8b4f710e74824e9cfdac4bf2fb8e845288fb4ec07973fbab3d665e00'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verified_face_transfer(review):
    """Require the reviewed complete correspondence, not face numbers alone."""
    return bool(review.get('input_sha256')==[OLD,NEW]
        and review.get('inputs_unchanged') is True
        and review.get('candidate_exact_valid') is True
        and review.get('all_contours_preserved') is True
        and len(review.get('contours',[]))==88
        and {r['face_id_private'] for r in review['contours']}==set(range(1,89))
        and all(r.get('same_face_orientation') is True and
                r.get('same_oriented_edge_multiset_in_each_wire_after_target_expansion') is True
                for r in review['contours'])
        and review.get('summary',{}).get('surfaces',{}).get('count')==88
        and all(review.get('summary',{}).get(k,{}).get('incompatible_count')==0
                for k in ('surfaces','pcurves','unchanged_edges')))


def run(args):
    import OCP
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape,TopoDS
    from OCP.TopAbs import TopAbs_FACE,TopAbs_SOLID,TopAbs_EDGE,TopAbs_VERTEX
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
    start=time.monotonic()
    supplied={args.domain:NEW,args.original_manifest:MANIFEST,args.review:REVIEW}
    if any(p.is_symlink() or sha(p)!=h for p,h in supplied.items()):
        raise ValueError('exact_candidate_manifest_and_independent_review_required')
    old=json.loads(args.original_manifest.read_text());review=json.loads(args.review.read_text())
    if not verified_face_transfer(review):raise ValueError('complete_reviewed_face_correspondence_required')
    old_domain=args.original_manifest.parent/old['exports']['domain_brep']['file']
    supplied[old_domain]=OLD
    for row in old['boundary_faces']:
        path=args.original_manifest.parent/row['file']
        if path.is_symlink() or args.original_manifest.parent.resolve() not in path.resolve().parents:
            raise ValueError('old_face_must_remain_in_private_packet')
        supplied[path]=row['sha256']
    if any(sha(p)!=h for p,h in supplied.items()):raise ValueError('old_source_geometry_changed')
    if args.output.exists() or args.output.is_symlink():raise FileExistsError(args.output)
    args.output.mkdir(parents=True,mode=0o700);(args.output/'faces').mkdir(mode=0o700)
    def read(path):
        shape=TopoDS_Shape()
        if not BRepTools.Read_s(shape,str(path),BRep_Builder()):raise ValueError('native_read_failed')
        return shape
    def indexed(shape,kind):
        result=TopTools_IndexedMapOfShape();TopExp.MapShapes_s(shape,kind,result);return result
    native=args.output/'domain.brep';shutil.copyfile(args.domain,native);native.chmod(0o600)
    shape=read(native);faces=indexed(shape,TopAbs_FACE)
    topology={name:indexed(shape,kind).Extent() for name,kind in
        [('faces',TopAbs_FACE),('edges',TopAbs_EDGE),('vertices',TopAbs_VERTEX),('solids',TopAbs_SOLID)]}
    if topology!={'faces':88,'edges':195,'vertices':120,'solids':1}:
        raise ValueError('exact_segmented_native_topology_required')
    valid=BRepCheck_Analyzer(shape,True,False,True).IsValid()
    job=BOPAlgo_ArgumentAnalyzer();job.SetShape1(shape)
    for mode in ('SelfInterMode','SmallEdgeMode','RebuildFaceMode','ContinuityMode','CurveOnSurfaceMode'):
        setattr(job,mode,True)
    job.Perform()
    bop={'has_faulty':job.HasFaulty(),'has_errors':job.HasErrors(),'has_warnings':job.HasWarnings(),
         'faults':[str(x.GetCheckStatus()).split('.')[-1] for x in job.GetCheckResult()]}
    report={'schema':'m64-intake-gas-domain/v1','status':'native_packet_prepared_local_neck_review_pending',
        'source_sha256':sha(__file__),'OCP_version':OCP.__version__,'units':old['units'],
        'exports':{'domain_brep':{'file':'domain.brep','sha256':sha(native)}},
        'native_BOP':bop,'native_roundtrip_BOP':bop,'topology':topology,
        'gates':{'single_solid':True,'brep_valid':valid,'native_roundtrip_valid':valid,
            'bop_no_faults':bop=={'has_faulty':False,'has_errors':False,'has_warnings':False,'faults':[]},
            'step_roundtrip_valid':None,'boundary_assignment_complete':False,
            'positive_intake_curtain':None,'guide_extensions_communicate':None},
        'STEP_BOP_qualified':False,'STEP_status':'not_executed_on_this_candidate',
        'boundary_role_transfer':{'original_domain_sha256':OLD,'original_manifest_sha256':MANIFEST,
            'independent_geometry_review_sha256':REVIEW,'surface_and_contour_correspondence_verified':True,
            'face_index_bijection':[[i,i] for i in range(1,89)],
            'source_match_labels_inherited_not_new_boolean_overlap_measurements':True},
        'boundary_faces':[],'unmatched_faces':[],'ambiguous_faces':[],
        'receiver':old['receiver'],'lifts_design_mm':old['lifts_design_mm'],
        'CFD_executed':False,'manufacturing_authorized':False,'M64_fitment_validated':False,
        'independent_closure_audit_accepted':False,'master_modified':False}
    for row in old['boundary_faces']:
        i=row['id'];face=TopoDS.Face_s(faces.FindKey(i));p=GProp_GProps()
        BRepGProp.SurfaceProperties_s(face,p);c=p.CentreOfMass()
        box=Bnd_Box();BRepBndLib.AddOptimal_s(face,box,False,False)
        target=args.output/'faces'/('face-%04d.brep'%i)
        BRepTools.Write_s(face,str(target));target.chmod(0o600)
        report['boundary_faces'].append({'id':i,'role':row['role'],
            'file':str(target.relative_to(args.output)),'sha256':sha(target),
            'area':p.Mass(),'center':[c.X(),c.Y(),c.Z()],
            'surface_type':str(BRepAdaptor_Surface(face,True).GetType()).split('.')[-1],
            'bbox':list(box.Get()),'original_face_sha256':row['sha256'],
            'source_match':[{'source':s['source'],'role':s['role']} for s in row['source_match']]})
    roles=Counter(r['role'] for r in report['boundary_faces']);report['boundary_role_counts']=dict(roles)
    report['gates']['boundary_assignment_complete']=dict(roles)==old['boundary_role_counts']
    p=GProp_GProps();err=BRepGProp.VolumeProperties_s(shape,p,1e-9,True)
    report['domain_volume']={'value':p.Mass(),'relative_quadrature_estimate_not_bound':err}
    ap=GProp_GProps();BRepGProp.SurfaceProperties_s(shape,ap)
    report['properties']={'volume':p.Mass(),'area':ap.Mass(),'solids':1}
    report['inputs_unchanged']=all(sha(p)==h for p,h in supplied.items())
    report['elapsed_seconds']=time.monotonic()-start
    out=args.output/'gas-domain-report-prepared.json'
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');out.chmod(0o600)
    accepted=valid and report['gates']['bop_no_faults'] and report['gates']['boundary_assignment_complete'] and report['inputs_unchanged']
    print(json.dumps({'packet_prepared':accepted,'report_sha256':sha(out),
        'faces':len(report['boundary_faces']),'elapsed_seconds':report['elapsed_seconds']}))
    return 0 if accepted else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('domain','original-manifest','review','output'):parser.add_argument('--'+key,type=Path,required=True)
    resource.setrlimit(resource.RLIMIT_CPU,(120,125))
    raise SystemExit(run(parser.parse_args()))
