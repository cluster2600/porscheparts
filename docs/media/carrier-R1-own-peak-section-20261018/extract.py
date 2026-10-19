"""One actual R1 X-plane section at its closed global peak; no mesh, FEA or drawing."""
import hashlib,importlib.util,json,math,os,resource,signal,struct,sys,time,traceback
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[2]

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,value):
 with Path(path).open('x')as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def require(ok, message):
    if not ok: raise ValueError(message)

def coordinate_sha(edges):
    return hashlib.sha256(b''.join(struct.pack('<ddd',*p) for edge in edges for p in edge['points_xyz_mm'])).hexdigest()

def native_section(body, role, plane_record, section_path):
    from OCP.BRep import BRep_Tool
    from OCP.BRepTools import BRepTools
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
    operation = BRepAlgoAPI_Section(body, gp_Pln(gp_Pnt(*plane_record['origin_mm']), gp_Dir(*plane_record['normal_raw'])), False)
    operation.SetRunParallel(False)
    operation.Approximation(False)
    operation.Build()
    require(operation.IsDone(), 'Native section failed')
    raw = operation.Shape()
    require(not raw.IsNull() and BRepTools.Write_s(raw, str(section_path)) is True, 'Raw native section preservation failed')
    write(section_path.with_suffix('.json'), dict(path=section_path.name, sha256=sha(section_path), raw_native_curves_preserved=True, plane=plane_record, Approximation=False, RunParallel=False))
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
        edges.append(dict(edge_index=len(edges), curve_type=str(curve.GetType()), parameter_domain=[float(curve.FirstParameter()),float(curve.LastParameter())], sampled_parameters=[float(sampler.Parameter(i)) for i in range(1, sampler.NbPoints() + 1)], points_xyz_mm=points))
        tolerances.append(max(float(BRep_Tool.Tolerance_s(edge)), float(Precision.Confusion_s())))
        explorer.Next()
    sections.append(dict(role=role, native_solids=count, edges=edges, edge_count=len(edges), maximum_native_edge_tolerance_mm=max(tolerances), sampled_positions_sha256=coordinate_sha(edges)))
    return sections[0]

def check_section(section,plane_record):
    edges=section['edges'];points=[p for e in edges for p in e['points_xyz_mm']]
    require(edges and all(2<=len(e['points_xyz_mm'])==len(e['sampled_parameters'])<=100000 for e in edges),'Complete original drawing samples required')
    require(all(len(p)==3 and all(type(v)is float and math.isfinite(v)for v in p)for p in points),'Finite native XYZ samples required')
    require(all(len(e['parameter_domain'])==2 and all(math.isfinite(v)for v in e['parameter_domain']+e['sampled_parameters'])for e in edges),'Finite native curve parameters required')
    require(coordinate_sha(edges)==section['sampled_positions_sha256'],'Original sampled coordinate bytes differ')
    residual=max(abs(p[0]-plane_record['origin_mm'][0])for p in points)
    require(residual<=section['maximum_native_edge_tolerance_mm'],'Sampled section leaves its own native plane tolerance')
    return dict(edge_count=len(edges),drawing_points=len(points),maximum_plane_residual_mm=residual,maximum_native_edge_tolerance_mm=section['maximum_native_edge_tolerance_mm'])

def verify(path,expected,native=False):
    require(sha(path)==expected,'Plan SHA differs');p=read(path)
    if native:require(p['launch_ready']is True and p['root_GO_sha256']is not None and sha(R/p['root_GO'])==p['root_GO_sha256'],'NON-ARMED: ROOT review/GO required')
    require(p['schema']=='R1-actual-common-peak-X-section-plan-1'and p['bounds']==dict(outer=180,inner=150,CPU=[140,160],threads=1,workers=0),'Original section resource bounds differ')
    require(p['drawing_deflection_mm']==.001 and p['new_ray_hits_computed']is False and p['R1_stress_inferred']is False,'Original sampling/no new mechanics scope differs')
    before={n:sha(R/n)for n in p['files_sha256']};require(before==p['files_sha256'],'Pinned source/input/runtime differs')
    records=load('_closed_R1_reference_planes',H/'records.py');require(before[p['BREP']]==p['BREP_sha256']==records.R1,'Foreign R1 BREP');records.closed(p,R)
    out=R/p['output_directory'];require(not out.exists()and not any(q.is_symlink()for q in [out,*out.parents]),'Fresh nonsymlink output required')
    if not native:require(not(R/p['execution_directory']).exists(),'Fresh supervision required')
    return p,before,out

def run(path,expected):
    began=time.monotonic();p,before,out=verify(path,expected,True);out.mkdir();code=1
    report=dict(schema='R1-actual-common-peak-native-section-1',status='incomplete_or_refused',sections=[],sources_before=before,candidate_BREP_sha256=p['BREP_sha256'],observation_ROOT_sha256=p['observation_ROOT_sha256'],drawing_deflection_mm=.001,geometry_modified=False,new_ray_hits_computed=False,R1_stress_inferred=False,FEA_executed=False,candidate_qualified=False)
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150s native section budget')));signal.alarm(150);resource.setrlimit(resource.RLIMIT_CPU,(140,160))
    try:
        require(os.getpriority(os.PRIO_PROCESS,0)==10 and all(os.environ.get(k)=='1'for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']),'Inherited nice10/BLAS1 required')
        sys.path.insert(0,str(R/p['native_site']))
        from OCP.BRep import BRep_Builder
        from OCP.BRepTools import BRepTools
        from OCP.TopoDS import TopoDS_Shape
        from OCP.OSD import OSD_ThreadPool
        OSD_ThreadPool.DefaultPool_s().Init(1)
        body=TopoDS_Shape();require(BRepTools.Read_s(body,str(R/p['BREP']),BRep_Builder()),'R1 native BREP read failed')
        for plane_record in p['planes']:
            role=plane_record['role'];raw=out/(role+'-section.brep')
            section=native_section(body,role,plane_record,raw)
            data=dict(schema='actual-R1-common-peak-X-section-data-1',candidate_BREP_sha256=p['BREP_sha256'],reference_scope='Closed actual R1 common FE peak X plane; no new stress',plane=plane_record,raw_native_curves_BREP=dict(path=raw.name,sha256=sha(raw)),section=section,drawing_deflection_mm=.001,Approximation=False,RunParallel=False,producer_sha256=sha(__file__),plan_sha256=expected)
            pathdata=out/(role+'-section-data.json');write(pathdata,data)
            measured=check_section(section,plane_record)
            report['sections'].append(dict(role=role,raw_BREP_sha256=sha(raw),data_sha256=sha(pathdata),**measured))
        report['status']='R1_actual_peak_native_section_and_raw_curves_preserved_no_drawing_or_FEA';code=0
    except BaseException as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:
        signal.alarm(0);after={n:sha(R/n)for n in before};report.update(sources_after=after,sources_unchanged=before==after,elapsed_seconds=time.monotonic()-began,outputs_sha256={str(q.relative_to(out)):sha(q)for q in sorted(out.iterdir())if q.is_file()})
        if before!=after:report['status']='refused_input_drift';code=1
        write(out/'assessment.json',report)
    print(json.dumps(dict(status=report['status'],assessment_sha256=sha(out/'assessment.json'))),flush=True);return code

if __name__=='__main__':
    mode,path,expected=sys.argv[1:]
    if mode=='preflight':p,_,_=verify(Path(path),expected);print(json.dumps(dict(status='closed_metadata_and_pins_only_no_native',armed=p['launch_ready'])))
    elif mode=='run':raise SystemExit(run(Path(path),expected))
    else:raise ValueError('Use preflight or run PLAN SHA')
