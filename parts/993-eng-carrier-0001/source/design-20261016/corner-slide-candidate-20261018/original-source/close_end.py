"""One NON-ARMED R1 prototype at the measured C1 blend/window edge; no FEA."""
import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PENDING=('protected_interfaces','surface_topology_and_distance','STEP_exchange','FEA')
MASTER='a42e6942722957076410d4a89b24f9bd0f11677dfa8319103d6733a0db8a1cf9'
BASELINE='de0e55a3150dacc5428bbc301d18d2e43477f038c3f4df295d9373af8e906b63'
def require(value,message):
    if not value:raise ValueError(message)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()
def write(path,value):
    with Path(path).open('x')as f:
        json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def verify(path,expected,native=False):
    require(sha(path)==expected,'Plan SHA differs');p=json.loads(Path(path).read_text())
    if native:require(p['launch_ready']is True,'NON-ARMED: no native Build before root review')
    require(p['schema']=='single-C1-window-end-R1-plan-1'and p['radius_mm']==1. and type(p['radius_mm'])is float,'Only the existing R1 is allowed')
    require(p['edge_index']==267 and p['adjacent_faces']==[60,62]and p['bounds']==dict(outer=180,inner=150,CPU=[140,141],threads=1,workers=0),'Reviewed local scope/resources differ')
    require(p['files_sha256'][p['C1_BREP']]==MASTER and p['files_sha256'][p['baseline_STEP']]==BASELINE,'Actual C1 or original baseline identity differs')
    before={n:sha(ROOT/n)for n in p['files_sha256']};require(before==p['files_sha256'],'Pinned inputs/source/runtime changed')
    out=ROOT/p['output_directory'];require(not out.exists()and not any(q.is_symlink()for q in [out,*out.parents]),'Fresh nonsymlink output required')
    if not native:require(not(ROOT/p['execution_directory']).exists(),'Fresh supervision required at preflight only')
    return p,before,out
def edge_record(diagnostic):
    require(diagnostic['status']=='actual_C1_common_IP_native_diagnostic_complete'and diagnostic['sources_unchanged'],'Closed actual C1 diagnostic required')
    require(diagnostic['CAD_source']['sha256']==MASTER,'Foreign BREP diagnostic')
    require(diagnostic['common_peak']['element_id']==84037 and diagnostic['common_peak']['IP_one_based']==1,'Only the actual coarse common IP is authority')
    rows=[r for r in diagnostic['probes'][0]['nearest_edges']if r['edge_index_zero_based']==267]
    require(len(rows)==1,'One measured edge267 required');r=rows[0]
    require(r['adjacent_faces_zero_based']==[60,62]and r['native_continuity'].endswith('GeomAbs_C0'),'Measured blend/window adjacency differs')
    return r
def retain_cut_helpers(path,namespace):
    run=next(n for n in ast.parse(Path(path).read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='run')
    names=('entities','bbox','summary');nodes=[]
    for key in names:
        matches=[n for n in ast.walk(run)if isinstance(n,ast.FunctionDef)and n.name==key]
        require(len(matches)==1,'Unique retained raw-cut helper required');nodes.append(matches[0])
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace);return namespace['summary']
def local_gate_flags(residue,valid,solid_count,mass,bounds,plan):
    require(residue['native_topologically_empty'],'Baseline material removed: strict native Cut is nonempty')
    require(valid and solid_count==1,'Exactly one valid Solid required')
    require(math.isfinite(mass)and 0<mass<=1.3,'Existing 1.30kg mass ceiling failed')
    require(all(math.isfinite(c)for row in bounds for c in row),'Nonfinite bounds')
    require(all(bounds[0][i]>=plan['minimum_xyz_mm'][i]-plan['existing_bound_guard_mm']and bounds[1][i]<=plan['maximum_xyz_mm'][i]+plan['existing_bound_guard_mm']for i in range(3)),'Existing global bounds failed')
    return dict(local_geometry_checks_passed=True,candidate_qualified=False,downstream_checks={k:'PENDING'for k in PENDING})

def run(plan_path,expected):
    started=time.monotonic();p,before,out=verify(plan_path,expected,True);out.mkdir();code=1
    report=dict(schema='single-C1-window-end-R1-prototype-1',status='refused_or_incomplete',candidate_qualified=False,
        downstream_checks={k:'PENDING'for k in PENDING},FEA_executed=False,baseline_material_removal_allowed=False,sources_before=before)
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150s native end-fillet prototype bound')))
    signal.alarm(150);resource.setrlimit(resource.RLIMIT_CPU,(140,141))
    events=(out/'events.jsonl').open('x')
    def event(name,**values):
        events.write(json.dumps(dict(event=name,seconds=time.monotonic()-started,**values),allow_nan=False)+'\n');events.flush();os.fsync(events.fileno())
    try:
        require(os.getpriority(os.PRIO_PROCESS,0)==10,'nice10 child required')
        sys.path.insert(0,str(ROOT/p['native_site']))
        from build123d import Solid,import_step,import_brep,export_brep
        from OCP.BRep import BRep_Tool
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
        from OCP.BRepBndLib import BRepBndLib
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
        from OCP.BRepGProp import BRepGProp
        from OCP.Bnd import Bnd_Box
        from OCP.GProp import GProp_GProps
        from OCP.OSD import OSD_ThreadPool
        from OCP.TopAbs import TopAbs_SOLID,TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX
        from OCP.TopExp import TopExp
        from OCP.TopTools import TopTools_IndexedMapOfShape,TopTools_ListOfShape
        from OCP.TopoDS import TopoDS,TopoDS_Iterator
        OSD_ThreadPool.DefaultPool_s().Init(1)
        old=load('_retained_postfillet4652',ROOT/p['postfillet_source']);volume=load('_retained_precise_volume',ROOT/p['volume_source'])
        d=json.loads((ROOT/p['diagnostic']).read_text());r=edge_record(d)
        body=import_brep(ROOT/p['C1_BREP']);baseline=import_step(ROOT/p['baseline_STEP'])
        require(body.is_valid and baseline.is_valid and len(body.solids())==len(baseline.solids())==1,'Actual C1 and baseline must be one valid Solid')
        faces,edges=list(body.faces()),list(body.edges());require(len(faces)==d['BREP_faces']and len(edges)==d['BREP_edges'],'Native topology counts differ')
        selected=edges[267];adj=[i for i,f in enumerate(faces)if any(selected.wrapped.IsSame(e.wrapped)for e in f.edges())]
        box=selected.bounding_box();require(adj==r['adjacent_faces_zero_based']and selected.length==r['length_mm']and [list(box.min),list(box.max)]==r['bounds_mm'],'Reimported measured edge identity differs')
        require(str(BRep_Tool.Continuity_s(selected.wrapped,faces[60].wrapped,faces[62].wrapped))==r['native_continuity'],'Reimported measured continuity differs')
        for i in adj:
            measured=next(f for f in d['probes'][0]['nearest_faces']if f['face_index_zero_based']==i);face=faces[i];box=face.bounding_box()
            require(str(BRepAdaptor_Surface(face.wrapped,True).GetType())==measured['surface_type']and str(face.wrapped.Orientation())==measured['orientation']and face.area==measured['area_mm2']and [list(box.min),list(box.max)]==measured['bounds_mm'],'Reimported supporting face differs')
        report.update(selected_edge_record=r,source_BREP_sha256=sha(ROOT/p['C1_BREP']),baseline_STEP_sha256=sha(ROOT/p['baseline_STEP']),radius_mm=1.)
        builder=BRepFilletAPI_MakeFillet(body.solids()[0].wrapped);builder.Add(1.,selected.wrapped)
        require(builder.NbContours()==1,'Only one contour may be retouched')
        actual=[next(i for i,e in enumerate(edges)if e.wrapped.IsSame(builder.Edge(1,j)))for j in range(1,builder.NbEdges(1)+1)]
        require(actual==[267]and builder.IsConstant(1)and builder.Radius(1)==1.,'Native contour propagated or radius changed')
        event('before_unique_R1_Build',edges=actual);builder.Build();event('after_unique_R1_Build',IsDone=builder.IsDone())
        report['native_build_status']=dict(IsDone=builder.IsDone(),HasResult=builder.HasResult(),NbFaultyContours=builder.NbFaultyContours(),NbFaultyVertices=builder.NbFaultyVertices(),StripeStatus=[str(builder.StripeStatus(i))for i in range(1,builder.NbContours()+1)])
        require(builder.IsDone(),'Unique native R1 end-fillet did not complete')
        def children(shape):
            it=TopoDS_Iterator(shape)
            while it.More():yield it.Value();it.Next()
        leaf,structure=old.unwrap_one_solid(builder.Shape(),children);candidate=Solid(TopoDS.Solid_s(leaf));report['native_container_structure']=structure
        require(candidate.is_valid and len(candidate.solids())==1,'Exactly one valid candidate Solid required')
        export_brep(candidate,out/'candidate-native.brep')
        report.update(raw_native_candidate_preserved_before_admission=True,outputs_sha256={'candidate-native.brep':sha(out/'candidate-native.brep')})
        report['native_history']={name:{kind:[dict(native_type=str(q.ShapeType()),candidate_face_indices=[j for j,f in enumerate(candidate.faces())if f.wrapped.IsSame(q)])for q in getattr(builder,kind)(shape)]for kind in ('Generated','Modified')}for name,shape in [('edge267',selected.wrapped),('face60',faces[60].wrapped),('face62',faces[62].wrapped)]}
        report['native_history_scope']='Actual native Generated/Modified only; empty lists do not infer provenance.'
        summary=retain_cut_helpers(ROOT/p['strict_cut_source'],dict(TopTools_IndexedMapOfShape=TopTools_IndexedMapOfShape,TopExp=TopExp,Bnd_Box=Bnd_Box,BRepBndLib=BRepBndLib,TopAbs_SOLID=TopAbs_SOLID,TopAbs_FACE=TopAbs_FACE,TopAbs_EDGE=TopAbs_EDGE,TopAbs_VERTEX=TopAbs_VERTEX,BRepCheck_Analyzer=BRepCheck_Analyzer,volume=volume,SimpleNamespace=SimpleNamespace,TopoDS=TopoDS,BRep_Tool=BRep_Tool,GProp_GProps=GProp_GProps,BRepGProp=BRepGProp,BRepAdaptor_Surface=BRepAdaptor_Surface))
        cut=BRepAlgoAPI_Cut();args=TopTools_ListOfShape();tools=TopTools_ListOfShape();args.Append(baseline.wrapped);tools.Append(candidate.wrapped)
        cut.SetArguments(args);cut.SetTools(tools);cut.SetNonDestructive(True);cut.SetRunParallel(False);cut.SetFuzzyValue(0.)
        event('before_strict_baseline_Cut',NonDestructive=True,RunParallel=False,FuzzyValue=0.);cut.Build();event('after_strict_baseline_Cut',IsDone=cut.IsDone())
        require(cut.IsDone(),'Strict baseline native Cut incomplete');residue=summary(cut.Shape());write(out/'baseline-minus-candidate.json',residue)
        native_volume,error=volume.precise_volume(candidate);old_volume,old_error=volume.precise_volume(body)
        study=json.loads((ROOT/p['study']).read_text());mass=native_volume*study['material']['density_tonne_mm3']*1000;box=candidate.bounding_box();bounds=[list(box.min),list(box.max)]
        report.update(local_gate_flags(residue,candidate.is_valid,len(candidate.solids()),mass,bounds,p),strict_baseline_residue=residue,native_volume_mm3=native_volume,native_volume_estimated_relative_error=error,C1_parent_volume_mm3=old_volume,C1_parent_volume_estimated_relative_error=old_error,delta_from_C1_volume_mm3=native_volume-old_volume,mass_kg=mass,bounds_mm=bounds)
        write(out/'study.json',study);report['outputs_sha256']['study.json']=sha(out/'study.json')
        report.update(status='native_R1_end_candidate_local_checks_complete_PENDING_downstream',no_Clean_or_shape_healing_called=True,no_STEP_export_or_readback=True);code=0
    except BaseException as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:
        signal.alarm(0);after={n:sha(ROOT/n)for n in before};report.update(sources_after=after,sources_unchanged=before==after,elapsed_seconds=time.monotonic()-started)
        if before!=after:report['status']='refused_input_drift';code=1
        write(out/'assessment.json',report);event('assessment_written',sha256=sha(out/'assessment.json'));events.close()
    print(json.dumps(dict(status=report['status'],candidate_qualified=False,assessment_sha256=sha(out/'assessment.json'))),flush=True);return code

if __name__=='__main__':
    mode,path,expected=sys.argv[1:]
    if mode=='preflight':p,_,_=verify(path,expected);print(json.dumps(dict(status='source_and_pins_only_no_native',armed=p['launch_ready'])))
    elif mode=='run':raise SystemExit(run(path,expected))
    else:raise ValueError('Use preflight or run with exact plan/SHA')
