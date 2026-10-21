"""NON-ARMED NEW taper section only; closed baseline/C1 profiles are reused without native replay."""
import hashlib,importlib.util,json,math,os,resource,signal,sys,time,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OLD_PATH=ROOT/'work/carrier-C1-junction-section-figure-003/figure.py'
OLD_SHA='284ebdcb1ef0a94c8fddbc1e51ebd38245c00c50649c2d4a9d5de44e3354d2f9'
CANDIDATE='dde710a2f318545ec99b066bbeddc71af0b526066eed97f8220ae2f61b3a75fb'
VOLUME_PATH=ROOT/'work/carrier-process-20261017/bounded-webs-BREP-volume-method-diagnostic-preparation-001/compare.py'
VOLUME_SHA='6863fdf7055231989208f31112b9c1d7d80ffaec470a0347da790fc817dd3cec'
ADAPTIVE_REFERENCE=285602.88227244973
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
if sha(OLD_PATH)!=OLD_SHA:raise ValueError('Frozen profile authority changed')
spec=importlib.util.spec_from_file_location('_closed003_section_authority',OLD_PATH);OLD=importlib.util.module_from_spec(spec);spec.loader.exec_module(OLD)
require,plane,FOOT,coordinate_sha=OLD.require,OLD.plane,OLD.FOOT,OLD.coordinate_sha
if sha(VOLUME_PATH)!=VOLUME_SHA:raise ValueError('Frozen volume authority changed')
spec=importlib.util.spec_from_file_location('_unchanged_volume_evaluate_only',VOLUME_PATH);VOLUME=importlib.util.module_from_spec(spec);spec.loader.exec_module(VOLUME)
def write(p,d):
 with Path(p).open('x')as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def closed_old(p):
 require(sha(p['old_render_plan'])==p['old_render_plan_sha256'],'Closed profile plan differs')
 plan=json.loads(Path(p['old_render_plan']).read_text());OLD.closed_extraction(plan)
 data=json.loads(Path(plan['data']).read_text());OLD.check(data)
 require(sha(plan['data'])==p['old_data_sha256']and data['section_plane']==p['section_plane']==plane(),'Exact closed source plane/profile differs')
 return data
def closed_volume(p):
 root=json.loads(Path(p['forward_root_review']).read_text());assessment=json.loads(Path(p['forward_assessment']).read_text());authority=json.loads(Path(p['forward_volume_authority']).read_text())
 require(root['actual_tool_RC']==0 and root['all9_whole_outputs_and_logs_matched']and root['assessment_sha256']==sha(p['forward_assessment'])and root['entire_scientific_before_after_maps_equal'],'Closed forward volume context differs')
 require(assessment['master_BREP_sha256']==CANDIDATE and assessment['outputs']['brep-audit.json']['sha256']==sha(p['forward_volume_authority'])and authority['CAD_source']['sha256']==CANDIDATE,'Foreign volume authority')
 require(authority['exact_CAD_volume_mm3']==p['closed_adaptive_volume_mm3']==ADAPTIVE_REFERENCE,'Closed adaptive reference differs')
 return authority
def volume_measurements(solid,BRepGProp,GProp_GProps):
 rows=VOLUME.evaluate(solid,BRepGProp,GProp_GProps)
 return dict(methods=rows,same_Solid_passed_to_all_three_unchanged_calls=True,closed_adaptive_reference_mm3=ADAPTIVE_REFERENCE,adaptive_exact_binary64_equal_to_closed_reference=rows[2]['signed_mass_mm3']==ADAPTIVE_REFERENCE,Gmsh_imported=False,Gmsh_getMass_mm3=None,new_T10_mesh_executed=False,evaluate_source_sha256=VOLUME_SHA)
def check_new(data,old):
 require(data['cached_sections']==old['sections']and data['closed_reference_context']==old['diagnostic_context'],'Cached profiles/context must remain entire and unchanged')
 require(data['section_plane']==old['section_plane']==plane()and data['candidate_BREP_sha256']==CANDIDATE,'Foreign taper/plane')
 section=data['taper_section'];require(section['role']=='taper'and section['native_solids']==1,'One new taper profile required')
 edges=section['edges'];points=[p for edge in edges for p in edge['points_xyz_mm']]
 require(edges and all(len(e['points_xyz_mm'])>=2 for e in edges)and all(len(p)==3 and all(type(v)is float and math.isfinite(v)for v in p)for p in points),'Complete finite native drawing points required')
 require(coordinate_sha(edges)==section['sampled_positions_sha256'],'New native coordinate bytes differ')
 require(max(OLD.plane_residual(p)for p in points)<=section['maximum_native_edge_tolerance_mm'],'New native profile leaves its own plane tolerance')
 require(data['reference_ray_is_old_C1_only']is True and data['new_ray_hits_computed']is False and data['global_thickness_claimed']is False and data['candidate_qualified']is False,'No new normal-ray/thickness/admission claim permitted')
 require(data['native_volume_methods']['adaptive_exact_binary64_equal_to_closed_reference']is True and data['native_volume_methods']['Gmsh_getMass_mm3']is None,'Actual same-Solid native volumes required; no Gmsh volume claim')
def verify(path,expected,native=False):
 require(sha(path)==expected,'Plan SHA differs');p=json.loads(Path(path).read_text())
 if native:require(p['launch_ready']is True and p['root_GO_sha256']is not None and sha(p['root_GO'])==p['root_GO_sha256'],'NON-ARMED: ROOT review/GO required')
 require(p['bounds']==dict(outer=180,inner=150,CPU=[140,160],threads=1,workers=0)and p['drawing_deflection_mm']==.001,'Original diagnostic resources/sampling differ')
 require(p['files_sha256'][p['BREP']]==CANDIDATE,'Preserved raw taper required')
 before={k:sha(ROOT/k)for k in p['files_sha256']};require(before==p['files_sha256'],'Pinned source/input/runtime changed');old=closed_old(p);closed_volume(p)
 out=ROOT/p['output_directory'];OLD.fresh(out)
 if not native:require(not(ROOT/p['execution_directory']).exists(),'Fresh supervision required at preflight')
 return p,before,old,out

def native_section(body, role):
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection
    from OCP.Precision import Precision
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
    sections = []
    require(not body.IsNull() and BRepCheck_Analyzer(body).IsValid(), 'Invalid actual CAD shape')
    solids = TopExp_Explorer(body, TopAbs_SOLID)
    count = 0
    while solids.More():
        count += 1
        solids.Next()
    require(count == 1, 'Exactly one actual native solid required')
    operation = BRepAlgoAPI_Section(body, gp_Pln(gp_Pnt(*FOOT), gp_Dir(*plane()['normal_raw'])), False)
    operation.SetRunParallel(False)
    operation.Approximation(False)
    operation.Build()
    require(operation.IsDone(), 'Native section failed')
    explorer = TopExp_Explorer(operation.Shape(), TopAbs_EDGE)
    edges = []
    tolerances = []
    while explorer.More():
        edge = TopoDS.Edge_s(explorer.Current())
        curve = BRepAdaptor_Curve(edge)
        sampler = GCPnts_QuasiUniformDeflection()
        sampler.Initialize(curve, 0.001, curve.FirstParameter(), curve.LastParameter())
        require(sampler.IsDone() and 2 <= sampler.NbPoints() <= 100000, 'Native curve drawing sampling failed')
        points = [list(map(float, curve.Value(sampler.Parameter(i)).Coord())) for i in range(1, sampler.NbPoints() + 1)]
        edges.append(dict(edge_index=len(edges), curve_type=str(curve.GetType()), points_xyz_mm=points))
        tolerances.append(max(float(BRep_Tool.Tolerance_s(edge)), float(Precision.Confusion_s())))
        explorer.Next()
    sections.append(dict(role=role, native_solids=count, edges=edges, edge_count=len(edges), maximum_native_edge_tolerance_mm=max(tolerances), sampled_positions_sha256=coordinate_sha(edges)))
    return sections[0]

def run(path,expected):
 started=time.monotonic();p,before,old,out=verify(path,expected,True);out.mkdir();code=1
 report=dict(schema='new-only-preserved-taper-native-section-1',status='refused_or_incomplete',candidate_qualified=False,original_law_RC1_preserved=True,old_CAD_recomputed=False,new_ray_hits_computed=False,global_thickness_claimed=False,FEA_executed=False,sources_before=before)
 signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150s new-only native profile cap')));signal.alarm(150);resource.setrlimit(resource.RLIMIT_CPU,(140,160))
 try:
  require(os.getpriority(os.PRIO_PROCESS,0)==10 and all(os.environ.get(k)=='1'for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')),'nice10/BLAS1 child required');sys.path.insert(0,str(ROOT/p['native_site']))
  from OCP.BRep import BRep_Builder
  from OCP.BRepTools import BRepTools
  from OCP.TopoDS import TopoDS_Shape,TopoDS
  from OCP.TopAbs import TopAbs_SOLID
  from OCP.TopExp import TopExp_Explorer
  from OCP.BRepCheck import BRepCheck_Analyzer
  from OCP.BRepGProp import BRepGProp
  from OCP.GProp import GProp_GProps
  from OCP.OSD import OSD_ThreadPool
  OSD_ThreadPool.DefaultPool_s().Init(1)
  body=TopoDS_Shape();require(BRepTools.Read_s(body,str(ROOT/p['BREP']),BRep_Builder()),'New preserved BREP read failed')
  explorer=TopExp_Explorer(body,TopAbs_SOLID);solids=[]
  while explorer.More():solids.append(TopoDS.Solid_s(explorer.Current()));explorer.Next()
  require(len(solids)==1 and BRepCheck_Analyzer(solids[0]).IsValid(),'One imported valid Solid required for all volume calls')
  solid=solids[0];identity=TopoDS.Solid_s(solid);volumes=volume_measurements(solid,BRepGProp,GProp_GProps)
  volumes.update(same_native_Solid_identity_before_after=solid.IsSame(identity),solid_IsSame_imported_body=solid.IsSame(body),forward_root_review_sha256=sha(p['forward_root_review']),forward_volume_authority_sha256=sha(p['forward_volume_authority']))
  write(out/'native-volume-methods.json',volumes);report['native_volume_methods_sha256']=sha(out/'native-volume-methods.json')
  require(volumes['same_native_Solid_identity_before_after']and volumes['adaptive_exact_binary64_equal_to_closed_reference']and BRepCheck_Analyzer(solid).IsValid()and 'gmsh'not in sys.modules,'Same-Solid volume identity/reference differs')
  new=native_section(body,'taper')
  data=dict(schema='closed-baseline-C1-and-new-taper-profile-comparison-1',section_plane=plane(),closed_reference_context=old['diagnostic_context'],cached_sections=old['sections'],taper_section=new,native_volume_methods=volumes,old_data_sha256=p['old_data_sha256'],candidate_BREP_sha256=CANDIDATE,reference_ray_is_old_C1_only=True,new_ray_hits_computed=False,global_thickness_claimed=False,candidate_qualified=False,original_law_RC1_preserved=True,drawing_deflection_mm=.001,no_geometry_modified=True,no_FEA=True,source_sha256=before,producer_sha256=sha(__file__),plan_sha256=expected)
  write(out/'section-data.json',data);report['raw_profile_data_sha256']=sha(out/'section-data.json');check_new(data,old)
  report.update(status='new_only_taper_profile_extracted_closed_profiles_reused_no_admission',new_native_edges=new['edge_count'],new_native_points=sum(len(e['points_xyz_mm'])for e in new['edges']),maximum_plane_residual_mm=max(OLD.plane_residual(q)for e in new['edges']for q in e['points_xyz_mm']));code=0
 except BaseException as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
 finally:
  signal.alarm(0);after={k:sha(ROOT/k)for k in before};report.update(sources_after=after,sources_unchanged=before==after,elapsed_seconds=time.monotonic()-started)
  if before!=after:report['status']='refused_input_drift';code=1
  write(out/'assessment.json',report)
 print(json.dumps(dict(status=report['status'],assessment_sha256=sha(out/'assessment.json'))),flush=True);return code
if __name__=='__main__':
 mode,path,expected=sys.argv[1:]
 if mode=='preflight':p,_,_,_=verify(path,expected);print(json.dumps(dict(status='stdlib_closed_profiles_and_pins_only_no_native',armed=p['launch_ready'])))
 elif mode=='run':raise SystemExit(run(path,expected))
 else:raise ValueError('Use preflight or run PLAN SHA')
