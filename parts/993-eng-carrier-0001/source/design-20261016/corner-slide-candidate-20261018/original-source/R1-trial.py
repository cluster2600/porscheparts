"""One non-armed declared R1.0 trial on the independently reviewed current d64 seven-edge junction."""
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

H=Path(__file__).resolve().parent;R=H.parents[2];W=H.parent
MASTER='d64a7faf8455735e05198661be823ead7037c23b58d36522e1cca60056aea624'
OBS_ROOT='4c6d3c34d7b42e14b193c426a72f9a458ea84bd0ab2e26277dd3b0e545ae69c6'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
GATE=load('_retained_endfillet_gates',W/'bounded-webs-C1-endfillet-preparation-002/close_end.py')
SELECT=load('_current_d64_concave_selector',H/'selector.py')
sha,require,write=GATE.sha,GATE.require,GATE.write

def closed_observation(p):
    require(sha(R/p['observation_ROOT'])==OBS_ROOT,'Actual two-case observation ROOT differs')
    root=json.loads((R/p['observation_ROOT']).read_text());owner=json.loads((R/p['observation_owner']).read_text());d=json.loads((R/p['observation']).read_text())
    require(root['schema']=='root-current-d64-hotspots-terminal-review-1'and root['status']=='closed_both_actual_RC0_local_native_observations','Both actual observations must be closed')
    require(root['cases']['spring']['owner_sha256']==sha(R/p['observation_owner'])and owner['assessment_sha256']==sha(R/p['observation']),'ROOT/owner/whole observation join differs')
    require(owner['actual_child_returncode']==0 and owner['direct_child_reaped']and owner['owned_group_empty']and owner['fresh_PID_and_PGID_absent'],'Actual observation was not cleanly closed')
    require(owner['candidate_BREP_sha256']==d['CAD_source']['sha256']==p['master_BREP_sha256']==MASTER,'Foreign BREP observation')
    require(d['case_peak']==owner['actual_case_peak']and d['case_peak']['element_id']==81008 and d['case_peak']['IP_one_based']==3,'Actual current spring peak differs')
    rows=[row for row in d['probes'][4]['nearest_edges']if row['edge_index_zero_based']==422]
    require(len(rows)==1 and rows[0]['adjacent_faces_zero_based']==[120,163]and rows[0]['parameter_origin']=='native_ParOnEdgeS2','Actual interior arch/rib observation differs')
    return d,rows[0]

def verify(path,expected,native=False):
    require(sha(path)==expected,'Plan SHA differs');p=json.loads(Path(path).read_text())
    if native:require(p['launch_ready']is True and p['root_GO']is not None and sha(R/p['root_GO'])==p['root_GO_sha256'],'NON-ARMED: ROOT GO required before selection/Build')
    require(p['schema']=='current-d64-seven-edge-R1-plan-1'and type(p['radius_mm'])is float and p['radius_mm']==1.0,'Only the separately declared clearance-derived R1.0 is allowed')
    require(p['bounds']==dict(outer=180,inner=150,CPU=[140,141],threads=1,workers=0)and p['seed_edge']==422 and p['seed_faces']==[120,163]and p['Y_reflection_allowed']is False,'Scope/resources differ')
    before={name:sha(R/name)for name in p['files_sha256']};require(before==p['files_sha256'],'A source/input/runtime pin changed')
    require(sha(R/p['prior_refusal_ROOT'])=='86e44df527f3fa6f35c47fa041ba52acafa08a6b53b241a19f8e7c893b9dcc5e','Actual prior contour refusal ROOT differs')
    prior=json.loads((R/p['prior_refusal_ROOT']).read_text());owner=json.loads((R/p['prior_refusal_owner']).read_text())
    require(prior['owner_terminal_sha256']==sha(R/p['prior_refusal_owner'])and owner['actual_child_returncode']==1 and owner['actual_fillet_Build_executed']is False,'Prior R1.5 no-Build refusal join differs')
    require(owner['all_outputs'][p['reference_graph']]['sha256']==sha(R/p['reference_graph']),'Actual reference graph is not joined to prior owner')
    require(p['radius_design']==dict(existing_tool_clearance_Q='11/10',declared_radius_Q='1',nominal_source_reserve_Q='1/10',cap_upper_bound_Q='3/2',automatic_shrink=False),'Declared clearance-derived design differs')

    require(before[p['master_BREP']]==MASTER,'Actual current d64 master differs')
    settings=json.loads((R/p['settings']).read_text());g=settings['geometry']
    require(g['arm_shell']==dict(depth_mm=44,cap_mm=1.5,web_mm=1.61)and g['thickness_mm']==8 and g['central_back_ribs']==dict(width_mm=2.8,top_z_mm=30,inboard_y_mm=5)and g['window_scale']==.9,'Source cap/arch/rib parameters differ')
    d,row=closed_observation(p);out=R/p['output_directory']
    require(not out.exists()and not any(q.is_symlink()for q in [out,*out.parents]),'Fresh nonsymlink output required')
    if not native:require(not(R/p['execution_directory']).exists(),'Fresh supervision required')
    return p,before,out,d,row

def strict_empty(row):
    require(row['native_topologically_empty']is True and row.get('native_valid')is True and row['counts']==dict(solids=0,faces=0,edges=0,vertices=0)and row.get('highest_topological_dimension')is None,'Whole current d64 retention is not strictly empty in every dimension')
def positive_addition(row):
    require(not row['native_topologically_empty']and row.get('native_valid')is True and row['material_solid_volume_mm3']>0 and len(row.get('solids',[]))>0 and all(s['native_valid']and s['volume_mm3']>0 for s in row['solids']),'Positive valid added material required')
def preserved_shape(raw,path,writer):
    if raw is None:return dict(path=None,sha256=None,reason='no_safe_native_result_available')
    if raw.IsNull():return dict(path=None,sha256=None,reason='native_result_is_null')
    require(writer(raw,str(path))is True,'Raw native BREP preservation failed');return dict(path=path.name,sha256=sha(path),reason=None)
def build_raw(builder):
    # Shape() can call Build() when !IsDone in the retained OCCT MakeShape source.
    # BadShape() exposes an available partial result without that implicit retry.
    if builder.IsDone():return builder.Shape(),'Shape_after_IsDone'
    if builder.HasResult():return builder.BadShape(),'BadShape_after_HasResult'
    return None,'no_result_available'

def run(path,expected):
    began=time.monotonic();p,before,out,d,measured=verify(path,expected,True);out.mkdir();code=1
    report=dict(schema='current-d64-seven-edge-R1-trial-1',status='refused_or_incomplete',candidate_qualified=False,master_BREP_sha256=MASTER,radius_mm=1.0,Y_reflection_used=False,FEA_executed=False,downstream_checks={key:'PENDING'for key in GATE.PENDING},sources_before=before)
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150s one concave-rounding trial bound')));signal.alarm(150);resource.setrlimit(resource.RLIMIT_CPU,(140,141))
    events=(out/'events.jsonl').open('x')
    def event(name,**values):
        events.write(json.dumps(dict(event=name,seconds=time.monotonic()-began,**values),allow_nan=False)+'\n');events.flush();os.fsync(events.fileno())
    try:
        require(os.getpriority(os.PRIO_PROCESS,0)==10,'nice10 child required');sys.path.insert(0,str(R/p['native_site']))
        from build123d import Solid,import_brep
        from OCP.BRep import BRep_Tool
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
        from OCP.BRepBndLib import BRepBndLib
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
        from OCP.BRepGProp import BRepGProp
        from OCP.BRepTools import BRepTools
        from OCP.Bnd import Bnd_Box
        from OCP.GProp import GProp_GProps
        from OCP.OSD import OSD_ThreadPool
        from OCP.TopAbs import TopAbs_SOLID,TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX
        from OCP.TopExp import TopExp
        from OCP.TopTools import TopTools_IndexedMapOfShape,TopTools_ListOfShape
        from OCP.TopoDS import TopoDS,TopoDS_Iterator
        OSD_ThreadPool.DefaultPool_s().Init(1)
        normals=load('_retained_pcurve_normals',R/p['boundary_normal_source']);volume=load('_original_adaptive_volume',R/p['volume_source']);old=load('_retained_one_solid_container',R/p['postfillet_source'])
        summary=GATE.retain_cut_helpers(R/p['strict_cut_source'],dict(TopTools_IndexedMapOfShape=TopTools_IndexedMapOfShape,TopExp=TopExp,Bnd_Box=Bnd_Box,BRepBndLib=BRepBndLib,TopAbs_SOLID=TopAbs_SOLID,TopAbs_FACE=TopAbs_FACE,TopAbs_EDGE=TopAbs_EDGE,TopAbs_VERTEX=TopAbs_VERTEX,BRepCheck_Analyzer=BRepCheck_Analyzer,volume=volume,SimpleNamespace=SimpleNamespace,TopoDS=TopoDS,BRep_Tool=BRep_Tool,GProp_GProps=GProp_GProps,BRepGProp=BRepGProp,BRepAdaptor_Surface=BRepAdaptor_Surface))
        body=import_brep(R/p['master_BREP']);require(body.is_valid and len(body.solids())==1,'One valid original d64 Solid required')
        faces,edges,graph=SELECT.topology(body);report['input_counts']={key:len(graph[key])for key in graph};write(out/'full-original-adjacency.json',graph)
        require(len(faces)==d['BREP_faces']==236 and len(edges)==d['BREP_edges']==721 and len(graph['vertices'])==478,'Fresh original topology differs')
        seed=graph['edges'][422];require(seed['length_mm']==measured['length_mm']and seed['bounds_mm']==measured['bounds_mm'],'Original measured seed edge differs')
        selection={};report['selection']=selection
        try:selected=SELECT.select(body,faces,edges,graph,normals,selection,json.loads((R/p['reference_graph']).read_text()))
        finally:write(out/'native-selection.json',selection)
        builder=BRepFilletAPI_MakeFillet(body.solids()[0].wrapped)
        try:
            builder.Add(1.0,edges[422].wrapped)
        finally:
            contours=SELECT.contour_rows(builder,edges);report['fillet_contours_before_Build']=contours;write(out/'fillet-contours-before-Build.json',dict(selected_edge_indices=selected,contours=contours,Build_called=False))
        SELECT.require_contours(contours,selected,1.0)
        event('before_unique_declared_R1_Build',selected=selected,contours=contours)
        try:builder.Build()
        finally:
            state=dict(IsDone=bool(builder.IsDone()),HasResult=bool(builder.HasResult()),NbFaultyContours=builder.NbFaultyContours(),NbFaultyVertices=builder.NbFaultyVertices(),StripeStatus=[str(builder.StripeStatus(i))for i in range(1,builder.NbContours()+1)])
            report['native_build_status']=state;raw,method=build_raw(builder);saved=preserved_shape(raw,out/'raw-Build-result.brep',BRepTools.Write_s);saved['access_method']=method;report['raw_Build_preservation']=saved;write(out/'raw-Build-preservation.json',saved);event('after_unique_declared_R1_Build',**state)
        require(builder.IsDone(),'One declared R1.0 Build failed; no radius reduction/retry')
        def children(shape):
            it=TopoDS_Iterator(shape)
            while it.More():yield it.Value();it.Next()
        leaf,structure=old.unwrap_one_solid(raw,children);candidate=Solid(TopoDS.Solid_s(leaf));report['native_container_structure']=structure
        whole=summary(candidate.wrapped);write(out/'candidate-native-summary.json',whole);report['whole_candidate']=whole
        require(candidate.is_valid and len(candidate.solids())==1,'Exactly one valid candidate Solid required')
        # Preserve the admitted-name Solid separately from the unmodified raw Build container.
        report['candidate_BREP']=preserved_shape(candidate.wrapped,out/'candidate-native.brep',BRepTools.Write_s)
        sums={}
        for name in ('current-minus-candidate','candidate-minus-current'):
            original=import_brep(R/p['master_BREP']);require(original.is_valid and len(original.solids())==1,'Fresh current d64 Cut authority invalid')
            left,right=(original,candidate)if name=='current-minus-candidate'else(candidate,original)
            cut=BRepAlgoAPI_Cut();args=TopTools_ListOfShape();tools=TopTools_ListOfShape();args.Append(left.wrapped);tools.Append(right.wrapped);cut.SetArguments(args);cut.SetTools(tools);cut.SetNonDestructive(True);cut.SetRunParallel(False);cut.SetFuzzyValue(0.)
            event('before_'+name,NonDestructive=True,RunParallel=False,FuzzyValue=0.);cut.Build();event('after_'+name,IsDone=cut.IsDone());require(cut.IsDone(),'Strict native Cut incomplete')
            residue=cut.Shape();saved=preserved_shape(residue,out/(name+'-raw.brep'),BRepTools.Write_s);write(out/(name+'-raw-preservation.json'),saved);report.setdefault('raw_Cut_preservation',{})[name]=saved
            sums[name]=summary(residue);write(out/(name+'.json'),sums[name]);report['native_Cut_summaries']=sums
        native_volume,error=volume.precise_volume(candidate);fresh_current=import_brep(R/p['master_BREP']);current_volume,current_error=volume.precise_volume(fresh_current)
        study=json.loads((R/p['study']).read_text());mass=native_volume*study['material']['density_tonne_mm3']*1000;box=candidate.bounding_box();bounds=[list(box.min),list(box.max)]
        measurements=dict(native_adaptive_volume_mm3=native_volume,native_adaptive_error_estimate=error,fresh_current_adaptive_volume_mm3=current_volume,fresh_current_adaptive_error_estimate=current_error,delta_adaptive_volume_mm3=native_volume-current_volume,mass_kg=mass,bounds_mm=bounds)
        write(out/'local-measurements-before-gates.json',measurements);report['measurements']=measurements
        strict_empty(sums['current-minus-candidate']);positive_addition(sums['candidate-minus-current']);require(math.isfinite(native_volume-current_volume)and native_volume>current_volume,'Actual positive adaptive addition required')
        report.update(GATE.local_gate_flags(sums['current-minus-candidate'],candidate.is_valid,len(candidate.solids()),mass,bounds,p),status='local_concave_rounding_retention_mass_bounds_complete_downstream_PENDING')
        write(out/'study.json',study);code=0
    except BaseException as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:
        signal.alarm(0);after={name:sha(R/name)for name in before};report.update(sources_after=after,sources_unchanged=before==after,elapsed_seconds=time.monotonic()-began)
        if before!=after:code=1;report['status']='refused_sources_changed'
        write(out/'assessment.json',report);event('assessment_written',sha256=sha(out/'assessment.json'));events.close()
    print(json.dumps(dict(status=report['status'],candidate_qualified=False,assessment_sha256=sha(out/'assessment.json'))),flush=True);return code

if __name__=='__main__':
    mode,path,expected=sys.argv[1:]
    if mode=='preflight':verify(path,expected);print('SOURCE_ONLY: actual d64/observation/source/runtime bindings verified')
    elif mode=='run':raise SystemExit(run(path,expected))
    else:raise ValueError('Use preflight or run PLAN SHA')
