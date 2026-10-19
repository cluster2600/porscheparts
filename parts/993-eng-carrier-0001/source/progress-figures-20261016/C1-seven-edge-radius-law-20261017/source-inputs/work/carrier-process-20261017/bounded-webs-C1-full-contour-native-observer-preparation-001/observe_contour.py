"""NON-ARMED isolated whole-contour law Build observation; no geometry admission."""
import importlib.util,json,math,os,resource,signal,sys,time,traceback
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
GATE=load('_retained_endfillet_geometry_gates',HERE.with_name('bounded-webs-C1-endfillet-preparation-002')/'close_end.py')
LAW=load('_retained_closed_terminal_law',HERE.with_name('bounded-webs-C1-terminal-law-observation-preparation-001')/'observe_law.py')
FUNCTION=load('_exact_full_contour_function',HERE.with_name('bounded-webs-C1-full-contour-law-contract-preparation-001')/'law_contract.py')
CONTEXT=load('_actual_isolated_runtime_context',HERE/'runtime_context.py')
require,sha,write=GATE.require,GATE.sha,GATE.write
IDS=LAW.IDS
def validate_laws(rows,observed,physical,zero):
    LAW.other_six(rows);r=rows[0];old=observed['simulated_laws'][0]
    keys=['native_law_bounds','native_degree','native_poles','native_knots','native_multiplicities','native_rational','native_periodic']
    require('unavailable_reason'not in r and r.get('is_constant')is False and all(r.get(k)==old[k]for k in keys),'Post-Build target law differs from the closed physical-interval law')
    require(rows[1:]==observed['simulated_laws'][1:],'Other six complete native law records changed')
    result=LAW.proof(r['native_poles'],r['native_knots'],r['native_multiplicities'],r['native_degree'],physical,zero)
    require(result==observed['attached_exact_law_proof'],'Exact physical-interval coefficient proof differs');return result
def physical_observations(builder,edges,vertices,point_tool,curve_type):
    rows=[]
    for i in IDS:
        row=dict(edge_index_zero_based=i,endpoints=[])
        try:
            edge=edges[i];curve=curve_type(edge.wrapped)
            row.update(source_edge_length_mm=edge.length,source_edge_curve_parameters=[curve.FirstParameter(),curve.LastParameter()])
            for vertex in edge.vertices():
                ids=[j for j,v in enumerate(vertices)if v.wrapped.IsSame(vertex.wrapped)]
                require(len(ids)==1,'Unique original source vertex required')
                row['endpoints'].append(dict(vertex_index_zero_based=ids[0],source_point_mm=list(point_tool.Pnt_s(vertex.wrapped).Coord()),native_contour_abscissa_mm=builder.Abscissa(1,vertex.wrapped)))
            require(len(row['endpoints'])==2,'Two complete source endpoints required')
            row['endpoints'].sort(key=lambda r:r['native_contour_abscissa_mm'])
        except Exception as error:row['unavailable_reason']=dict(type=type(error).__name__,message=str(error))
        rows.append(row)
    return rows
def verify(path,expected,native=False):
    require(sha(path)==expected,'Plan hash differs');p=json.loads(Path(path).read_text())
    if native:require(p['launch_ready']is True and p['root_GO']and sha(ROOT/p['root_GO'])==p['root_GO_sha256'],'NON-ARMED: ROOT native GO required')
    require(p['variant']in['stock-rebuilt','patched'],'One explicit isolated control role required');CONTEXT.closed_context(p)
    require(p['schema']=='isolated-C1-complete-functional-law-Build-observer-1'and p['contour']==IDS and p['zero_vertex']==302 and p['terminal_edge']==431,'Original one-terminal scope required')
    require(p['bounds']==dict(outer=180,inner=150,CPU=[140,160],threads=1,workers=0),'Reviewed prototype bounds differ')
    require(p['files_sha256'][p['baseline_STEP']]==GATE.BASELINE,'Unchanged original baseline required')
    before={k:sha(ROOT/k)for k in p['files_sha256']};require(before==p['files_sha256'],'Pinned source/input/runtime changed')
    out=ROOT/p['output_directory'];require(not out.exists()and not any(x.is_symlink()for x in [out,*out.parents]),'Fresh nonsymlink output required')
    if not native:require(not(ROOT/p['execution_directory']).exists(),'Fresh supervision required at preflight')
    return p,before,out
def run(path,expected):
    started=time.monotonic();p,before,out=verify(path,expected,True);out.mkdir();code=1
    report=dict(schema='isolated-C1-complete-functional-law-Build-observer-1',status='refused_or_incomplete',method='isolated_C1_whole_contour_exact_smoothstep_then_six_R1_SetRadius_function_one_Build_1',candidate_qualified=False,downstream_checks={k:'PENDING'for k in GATE.PENDING},FEA_executed=False,sources_before=before,outputs_sha256={},Simulate_calls=0,SetLaw_calls=0,SetRadius_function_calls=0,final_Build_calls=0,separate_native_gates={k:'PENDING'for k in ['baseline_retention','positive_addition','mass_and_bounds','protected_interfaces']},zero_radius_scope='Same original vertex302; no smooth-solid or strength claim')
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150s original-C1 taper prototype bound')));signal.alarm(150);resource.setrlimit(resource.RLIMIT_CPU,(140,160));runtime_context=None
    events=(out/'events.jsonl').open('x')
    def event(name,**values):events.write(json.dumps(dict(event=name,seconds=time.monotonic()-started,**values),allow_nan=False)+'\n');events.flush();os.fsync(events.fileno())
    try:
        require(os.getpriority(os.PRIO_PROCESS,0)==10,'nice10 child required');runtime_context=CONTEXT.begin(p,out);report['isolated_runtime_before_CAD']=runtime_context['record']
        from build123d import Solid,import_step,export_brep
        from OCP.BRep import BRep_Tool
        from OCP.BRepAdaptor import BRepAdaptor_Curve,BRepAdaptor_Surface
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
        from OCP.BRepBndLib import BRepBndLib
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
        from OCP.Law import Law_BSpline,Law_BSpFunc
        from OCP.TColStd import TColStd_Array1OfReal,TColStd_Array1OfInteger
        from OCP.BRepGProp import BRepGProp
        from OCP.Bnd import Bnd_Box
        from OCP.GProp import GProp_GProps
        from OCP.OSD import OSD_ThreadPool
        from OCP.TopAbs import TopAbs_SOLID,TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX
        from OCP.TopExp import TopExp
        from OCP.TopTools import TopTools_IndexedMapOfShape,TopTools_ListOfShape
        from OCP.TopoDS import TopoDS,TopoDS_Iterator
        report['isolated_runtime_after_CAD_imports']=CONTEXT.end(runtime_context,out,'after-CAD-imports')
        OSD_ThreadPool.DefaultPool_s().Init(1)
        old=load('_retained_postfillet4652_unwrap',ROOT/p['postfillet_source'])
        report['closed_import_context_validated_before_CAD']=True
        body=import_step(ROOT/p['baseline_STEP']);faces,edges,vertices=list(body.faces()),list(body.edges()),list(body.vertices());require(body.is_valid and len(body.solids())==1 and len(faces)==240 and len(edges)==733,'Actual original baseline topology required')
        prior=json.loads((ROOT/p['contour_diagnostic']).read_text())['initial_contours'][0];require([r['edge_index_zero_based']for r in prior['edges']]==IDS,'Closed original contour differs')
        face_edges=[list(f.edges())for f in faces]
        for row in prior['edges']:
            i=row['edge_index_zero_based'];e=edges[i];curve=BRepAdaptor_Curve(e.wrapped);adj=[j for j,es in enumerate(face_edges)if any(e.wrapped.IsSame(x.wrapped)for x in es)]
            require(e.length==row['length_mm']and str(curve.GetType())==row['curve_type']and[curve.FirstParameter(),curve.LastParameter()]==row['domain']and adj==row['adjacent_faces_zero_based'],'Original contour edge geometry differs')
            actual=sorted(tuple(BRep_Tool.Pnt_s(v.wrapped).Coord())for v in e.vertices());wanted=sorted(tuple(r['point_mm'])for r in row['vertices']);require(actual==wanted,'Original contour endpoint coordinates differ')
        require(edges[431].length==21.430826650472525,'Whole measured original edge431 required')
        builder=BRepFilletAPI_MakeFillet(body.solids()[0].wrapped)
        for i in IDS:builder.Add(1.,edges[i].wrapped)
        def contour_ids():return [next(i for i,e in enumerate(edges)if e.wrapped.IsSame(builder.Edge(1,j)))for j in range(1,builder.NbEdges(1)+1)]
        def endpoint_ids():return [[i for i,v in enumerate(vertices)if v.wrapped.IsSame(x)]for x in [builder.FirstVertex(1),builder.LastVertex(1)]]
        require(builder.NbContours()==1 and contour_ids()==IDS and endpoint_ids()==[[302],[125]],'Only the original complete contour and endpoints are allowed')
        zero=vertices[302].wrapped;require(list(BRep_Tool.Pnt_s(zero).Coord())==[82.202665223312,-14.18196820123,12.756757217282],'Original zero endpoint differs')
        physical=sorted(builder.Abscissa(1,v.wrapped)for v in edges[431].vertices());zero_at=builder.Abscissa(1,zero);require(zero_at==0.,'Fresh original vertex302 must be the native contour origin')
        report.update(original_contour=IDS,physical_edge431_abscissae_mm=physical,zero_vertex=302,zero_at_native_abscissa_mm=zero_at,baseline_STEP_sha256=sha(ROOT/p['baseline_STEP']),full_contour_contract_ROOT_sha256=sha(ROOT/p['contract_ROOT']),runtime_role=p['variant'])
        report['pre_Build_physical_source_edges']=physical_observations(builder,edges,vertices,BRep_Tool,BRepAdaptor_Curve)
        require(all('unavailable_reason'not in r for r in report['pre_Build_physical_source_edges']),'Complete pre-Build native source-edge abscissae required')
        report['requested_complete_function']=FUNCTION.requested_spec(report['pre_Build_physical_source_edges'])
        law,specification=FUNCTION.make_native(report['pre_Build_physical_source_edges'],Law_BSpline,Law_BSpFunc,TColStd_Array1OfReal,TColStd_Array1OfInteger)
        report['constructed_native_law']=CONTEXT.law_record(law)
        constructed=[dict(edge_index_zero_based=i,**report['constructed_native_law'])for i in IDS]
        report['exact_constructed_function_proof']=FUNCTION.validate_native(constructed,report['pre_Build_physical_source_edges'])
        report['stage']='before_unique_whole_contour_SetRadius_function';write(out/'setup-before-SetRadius-function.json',report)
        report['SetRadius_function_calls']=1;event('before_unique_whole_contour_SetRadius_function');builder.SetRadius(law,1,1);event('after_unique_whole_contour_SetRadius_function')
        report['attached_laws_before_Build']=LAW.read_laws(builder,edges)
        require(builder.NbContours()==1 and contour_ids()==IDS and endpoint_ids()==[[302],[125]],'Original contour changed before final Build')
        report['final_Build_calls']=1;event('before_unique_explicit_terminal_Build',contour=IDS,zero_vertex=302);builder.Build();event('after_unique_explicit_terminal_Build',IsDone=builder.IsDone())
        report['native_build_status']=dict(IsDone=builder.IsDone(),HasResult=builder.HasResult(),NbFaultyContours=builder.NbFaultyContours(),NbFaultyVertices=builder.NbFaultyVertices(),FaultyVertices_mm=[list(BRep_Tool.Pnt_s(builder.FaultyVertex(k)).Coord())for k in range(1,builder.NbFaultyVertices()+1)],StripeStatus=[str(builder.StripeStatus(i))for i in range(1,builder.NbContours()+1)])
        require(builder.IsDone(),'Original scalar-terminal C1 Build did not complete')
        def children(shape):
            it=TopoDS_Iterator(shape)
            while it.More():yield it.Value();it.Next()
        leaf,structure=old.unwrap_one_solid(builder.Shape(),children);candidate=Solid(TopoDS.Solid_s(leaf));report['native_container_structure']=structure
        require(candidate.is_valid and len(candidate.solids())==1,'Exactly one valid candidate Solid required')
        export_brep(candidate,out/'candidate-native.brep')
        report.update(raw_native_candidate_preserved_before_admission=True,outputs_sha256={'candidate-native.brep':sha(out/'candidate-native.brep')})
        report['stage']='post_Build_native_law_and_abscissa_observation';rows=LAW.read_laws(builder,edges);report['post_Build_laws']=rows
        report['post_Build_physical_source_edges']=physical_observations(builder,edges,vertices,BRep_Tool,BRepAdaptor_Curve)
        require(all('unavailable_reason'not in r for r in report['post_Build_physical_source_edges']),'Complete independent post-Build native source-edge abscissae required')
        target=report['post_Build_physical_source_edges'][0]['endpoints'];post_physical=[r['native_contour_abscissa_mm']for r in target]
        post_zero=[r['native_contour_abscissa_mm']for r in target if r['vertex_index_zero_based']==302];require(len(post_zero)==1,'Unique post-Build zero endpoint required')
        report.update(post_Build_edge431_interval_mm=post_physical,post_Build_zero_abscissa_mm=post_zero[0],post_Build_interval_observed_independently=True)
        report['exact_post_Build_law_proof']=FUNCTION.validate_native(rows,report['post_Build_physical_source_edges'])
        require(builder.NbContours()==1 and contour_ids()==IDS and endpoint_ids()==[[302],[125]],'Original contour or opposite endpoint changed')
        report.update(other_six_functional_restrictions_exact_R1=True,opposite_source_contour_endpoint125_unchanged=True)
        report.update(status='complete_functional_law_Build_observed_PENDING_separate_geometry_gates',stage='law_Build_observation_complete',no_Cut_or_volume_or_protected_gate_called=True,no_Clean_or_shape_healing_called=True,no_STEP_export_or_readback=True);code=0
    except BaseException as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:
        signal.alarm(0)
        if runtime_context is not None:
            try:report['isolated_runtime_after_CAD']=CONTEXT.end(runtime_context,out)
            except BaseException as error:report['final_runtime_provenance_failure']=dict(type=type(error).__name__,message=str(error));code=1
        after={k:sha(ROOT/k)for k in before};report.update(sources_after=after,sources_unchanged=before==after,elapsed_seconds=time.monotonic()-started)
        if before!=after:report['status']='refused_input_drift';code=1
        write(out/'assessment.json',report);event('assessment_written',sha256=sha(out/'assessment.json'));events.close()
    print(json.dumps(dict(status=report['status'],candidate_qualified=False,assessment_sha256=sha(out/'assessment.json'))),flush=True);return code
if __name__=='__main__':
    mode,path,expected=sys.argv[1:]
    if mode=='preflight':p,_,_=verify(path,expected);print(json.dumps(dict(status='stdlib_only_preflight_no_native',armed=p['launch_ready'])))
    elif mode=='run':raise SystemExit(run(path,expected))
    else:raise ValueError('Use preflight or run PLAN SHA')
