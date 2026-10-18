"""Actual C1 junction in the coarse-IP normal-ray plane; no new geometry or FEA."""
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import struct
import sys
import time

FOOT = [82.13095205539072, -14.391865895364598, 12.863956248769874]
OUTWARD = [-0.7470009095927183, -0.4203032123880582, 0.5151066401473878]
ZOOM = [[-.15, .40], [-.30, .25]]

def plane():
    ray = [-v for v in OUTWARD]; length = math.hypot(*ray[:2])
    require(length > 0, 'The actual inward ray must define a plane with Z')
    return dict(origin_mm=FOOT, inward_ray=ray, normal_raw=[ray[1], -ray[0], 0.],
        U=[ray[0]/length, ray[1]/length, 0.], V=[0., 0., 1.])
def project(point):
    basis=plane();delta=[point[i]-FOOT[i] for i in range(3)]
    return [sum(delta[i]*basis['U'][i] for i in range(3)), delta[2]]
def plane_residual(point):
    n=plane()['normal_raw'];return abs(sum((point[i]-FOOT[i])*n[i] for i in range(3)))/math.hypot(*n[:2])
def check_ray(hits):
    require([r['face_index_zero_based'] for r in hits]==[60,62,68,150]
        and [r['transition'].split('_')[-1] for r in hits]==['In','Out','In','Out']
        and all(r['state']=='TopAbs_State.TopAbs_IN' for r in hits)
        and all(a['W_mm']<b['W_mm'] for a,b in zip(hits,hits[1:]))
        and hits[1]['W_mm']==.08651954398105025 and hits[2]['W_mm']==.2650828520317755
        and hits[0]['coincident_with_start_native_tolerance'] is True, 'Closed In/Out chain differs')
def context(actual, review, interpretation, h2):
    require(actual['status']=='actual_C1_common_IP_native_diagnostic_complete'
        and review['status']=='root_closed_actual_native_C1_local_geometry_diagnostic_RC0_no_design_change', 'Closed native diagnostic differs')
    peak=actual['common_peak'];require(peak==review['common_peak'] and peak['element_id']==84037 and peak['IP_one_based']==1, 'Only the coarse84037/IP1 ray defines this plane')
    face=next(r for r in actual['probes'][0]['nearest_faces'] if r['face_index_zero_based']==60);local=face['local_properties'];hits=local['normal_line_intersections']
    require(local['status']=='native_D2_at_reported_UV' and local['point_mm']==review['face60']['point_mm']==FOOT
        and local['normal_outward']==review['face60']['outward_normal']==OUTWARD and hits==review['face60']['raw_intersections'], 'Actual foot/D2/raw-ray provenance differs')
    check_ray(hits)
    require(local['local_chord']==review['face60']['local_chord'], 'Closed local chord differs')
    require(interpretation['observed']['entry_point_mm']==FOOT and interpretation['observed']['short_chord_mm']==hits[1]['W_mm']
        and interpretation['native_added_material_point_membership'] is None, 'Interpretation scope differs')
    require(actual['CAD_source']['sha256']==h2['BREP_sha256'] and h2['status']=='root_closed_two_actual_qualified_C1_h2_linear_cases_energy_PASS_all_peaks_preserved', 'Same master/H2 root evidence differs')
    for case in h2['cases'].values():
        require(all(p['element_id']==90371 and p['IP_one_based']==2 for p in case['all_global_maximum_ties']), 'Actual migrated H2 peak differs')
    return dict(coarse_source_peak=peak, face60_foot_mm=FOOT, outward_D2=OUTWARD, plane=plane(), raw_hits=hits,
        native_tolerance_mm=local['kernel_resolution_mm'], BREP_sha256=actual['CAD_source']['sha256'],
        h2_peak_not_plotted=True, wall_or_global_thickness=False, native_added_material_point_membership=None)


def require(ok, message):
    if not ok: raise ValueError(message)
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, ensure_ascii=False, allow_nan=False, separators=(',', ':'));f.write('\n')
def fresh(path):
    require(not path.exists() and not any(p.is_symlink() for p in [path,*path.parents]), 'Fresh output required')
def coordinate_sha(edges):
    return hashlib.sha256(b''.join(struct.pack('<ddd',*p) for edge in edges for p in edge['points_xyz_mm'])).hexdigest()
def check(data):
    require(data['section_plane']==plane() and data['zoom_UZ_relative_mm']==ZOOM and [s['role'] for s in data['sections']]==['before','after'], 'Fixed common oblique CAD section differs')
    c=data['diagnostic_context'];require(c['plane']==plane() and c['face60_foot_mm']==FOOT and c['outward_D2']==OUTWARD
        and c['coarse_source_peak']['element_id']==84037 and c['coarse_source_peak']['IP_one_based']==1
        and c['h2_peak_not_plotted'] is True and c['wall_or_global_thickness'] is False
        and c['native_added_material_point_membership'] is None, 'Coarse ray and H2 scope must remain separate')
    check_ray(c['raw_hits'])
    for section in data['sections']:
        edges=section['edges'];points=[p for edge in edges for p in edge['points_xyz_mm']]
        require(edges and points and all(len(p)==3 and all(type(v)is float and math.isfinite(v) for v in p) for p in points), 'Invalid CAD samples')
        require(all(len(edge['points_xyz_mm'])>=2 for edge in edges), 'Incomplete curve')
        require(coordinate_sha(edges)==section['sampled_positions_sha256'], 'Native sampled coordinate bits changed')
        require(max(plane_residual(p) for p in points)<=section['maximum_native_edge_tolerance_mm'], 'Native section leaves its own plane tolerance')
        require(any(ZOOM[0][0]<=project(p)[0]<=ZOOM[0][1] and ZOOM[1][0]<=project(p)[1]<=ZOOM[1][1] for p in points), 'Actual contour absent from common zoom')
    require(all(plane_residual(h['point_mm'])<=c['native_tolerance_mm'] for h in c['raw_hits']), 'Recorded ray point leaves the actual section plane')

def checked_plan(path):
    plan=json.loads(Path(path).read_text())
    require(plan['launch_ready'] is True and plan['root_GO_sha256'] is not None, 'NON-ARMED: no CAD extraction or drawing')
    require(sha(plan['root_GO'])==plan['root_GO_sha256'], 'Actual picture GO differs')
    return plan

def persist_sections(output,data,before,plan_path,plan_hash):
    # Preserve all raw native profiles even if a later display/identity guard refuses.
    output.mkdir();write(output/'section-data.json',data)
    check(data);check(json.loads(json.dumps(data,allow_nan=False)))
    root=Path(json.loads(Path(plan_path).read_text())['root'])
    require(before=={p:sha(root/p)for p in before} and sha(plan_path)==plan_hash,'Input/runtime/plan changed')
    sections=data['sections']
    write(output/'extraction-receipt.json',dict(status='actual_native_CAD_sections_extracted_for_picture',data_sha256=sha(output/'section-data.json'),
        sources_before=before,sources_after={p:sha(root/p)for p in before},source_pose_unchanged=True,no_geometry_modified=True,no_FEA=True,
        edges=[s['edge_count']for s in sections],points=[sum(len(e['points_xyz_mm'])for e in s['edges'])for s in sections],
        maximum_plane_residual_mm=max(plane_residual(p)for s in sections for e in s['edges']for p in e['points_xyz_mm'])))

def closed_extraction(plan):
    require(plan['data_sha256'] is not None and plan['extraction_receipt_sha256'] is not None
        and plan['extraction_supervision_sha256'] is not None, 'Closed validated extraction is required; raw data alone is insufficient')
    require(sha(plan['data'])==plan['data_sha256'] and sha(plan['extraction_receipt'])==plan['extraction_receipt_sha256']
        and sha(plan['extraction_supervision'])==plan['extraction_supervision_sha256'], 'Closed extraction/data identities differ')
    receipt=json.loads(Path(plan['extraction_receipt']).read_text());supervision=json.loads(Path(plan['extraction_supervision']).read_text())
    require(receipt['status']=='actual_native_CAD_sections_extracted_for_picture' and receipt['data_sha256']==plan['data_sha256']
        and receipt['sources_before']==receipt['sources_after'] and receipt['source_pose_unchanged'] and receipt['no_geometry_modified'] and receipt['no_FEA'], 'Validated native extraction receipt differs')
    require(supervision['status']=='executed' and supervision['actual_returncode']==0 and supervision['direct_child_reaped']
        and not supervision['final_group_members'] and not supervision['timeout'] and not supervision['interrupted']
        and supervision['sources_and_plan_unchanged'], 'Actual extraction group is not closed successfully')
    data=json.loads(Path(plan['data']).read_text());command=supervision['command'];root=Path(supervision['cwd'])
    require(len(command)==7 and command[4]=='export' and Path(command[3]).absolute()==Path(__file__).absolute()
        and Path(command[6]).absolute()==Path(plan['data']).absolute().parent, 'Successful supervision belongs to another producer/output')
    export_plan=Path(command[5]);require(export_plan.is_absolute(), 'Supervised export plan must be absolute')
    plan_key=str(export_plan.relative_to(root));producer_key=str(Path(command[3]).relative_to(root))
    require(sha(export_plan)==data['plan_sha256']==supervision['sources_before'].get(plan_key)==supervision['sources_after'].get(plan_key), 'Supervised export plan does not belong to these data')
    require(sha(__file__)==data['source_sha256'].get(producer_key)==supervision['sources_before'].get(producer_key)==supervision['sources_after'].get(producer_key), 'Supervised producer identity differs')
    require(receipt['sources_before']==data['source_sha256'] and all(supervision['sources_before'].get(k)==supervision['sources_after'].get(k)==v
        for k,v in data['source_sha256'].items()), 'Supervised source context does not belong to these profiles')


def export(plan_path, output):
    plan_path=Path(plan_path);plan_hash=sha(plan_path);plan=checked_plan(plan_path);root=Path(plan['root'])
    require(plan['section_plane']==plane() and plan['drawing_deflection_mm']==.001 and plan['workers']==0, 'Fixed read-only picture scope differs')
    before={p:sha(root/p)for p in plan['files_sha256']};require(before==plan['files_sha256'], 'A CAD input/runtime changed')
    output=Path(output);fresh(output)
    actual=json.loads((root/plan['diagnostic_assessment']).read_text());review=json.loads((root/plan['diagnostic_root_review']).read_text())
    require(review['assessment_sha256']==before[plan['diagnostic_assessment']], 'Root diagnostic/assessment SHA join differs')
    diagnostic=context(actual,review,json.loads((root/plan['interpretation']).read_text()),json.loads((root/plan['h2_root_review']).read_text()))
    require(diagnostic['BREP_sha256']==before[plan['BREP']], 'Actual BREP diagnostic input differs')
    receipt=json.loads((root/plan['candidate_assessment']).read_text())
    require(receipt['outputs_sha256']['candidate-native.brep']==before[plan['BREP']] and receipt['baseline_STEP_sha256']==before[plan['STEP']]
        and receipt['radius_mm']==1. and receipt['old_minus_new_native_empty']is True
        and receipt['new_minus_old_volume_mm3']>0 and receipt['status']=='refused'
        and receipt['failure']['message']=='STEP readback removed material', 'Actual C1 native prototype/exchange status differs')
    sys.path.insert(0,str(root/plan['native_site']))
    from OCP.BRep import BRep_Builder, BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepTools import BRepTools
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.Precision import Precision
    from OCP.OSD import OSD_ThreadPool
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS, TopoDS_Shape
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
    OSD_ThreadPool.DefaultPool_s().Init(1)
    reader=STEPControl_Reader();require(reader.ReadFile(str(root/plan['STEP']))==IFSelect_RetDone,'STEP read failed')
    reader.SetSystemLengthUnit(1.);require(reader.SystemLengthUnit()==1. and reader.TransferRoots()==reader.NbRootsForTransfer(),'Incomplete mm STEP transfer')
    old=reader.OneShape();new=TopoDS_Shape()
    require(BRepTools.Read_s(new,str(root/plan['BREP']),BRep_Builder()),'Native BREP read failed')
    sections=[]
    for role,body in [('before',old),('after',new)]:
        require(not body.IsNull() and BRepCheck_Analyzer(body).IsValid(),'Invalid actual CAD shape')
        solids=TopExp_Explorer(body,TopAbs_SOLID);count=0
        while solids.More():count+=1;solids.Next()
        require(count==1,'Exactly one actual native solid required')
        operation=BRepAlgoAPI_Section(body,gp_Pln(gp_Pnt(*FOOT),gp_Dir(*plane()['normal_raw'])),False)
        operation.SetRunParallel(False)
        operation.Approximation(False);operation.Build();require(operation.IsDone(),'Native section failed')
        explorer=TopExp_Explorer(operation.Shape(),TopAbs_EDGE);edges=[];tolerances=[]
        while explorer.More():
            edge=TopoDS.Edge_s(explorer.Current());curve=BRepAdaptor_Curve(edge);sampler=GCPnts_QuasiUniformDeflection()
            sampler.Initialize(curve,.001,curve.FirstParameter(),curve.LastParameter())
            require(sampler.IsDone() and 2<=sampler.NbPoints()<=100000,'Native curve drawing sampling failed')
            points=[list(map(float,curve.Value(sampler.Parameter(i)).Coord()))for i in range(1,sampler.NbPoints()+1)]
            edges.append(dict(edge_index=len(edges),curve_type=str(curve.GetType()),points_xyz_mm=points))
            tolerances.append(max(float(BRep_Tool.Tolerance_s(edge)),float(Precision.Confusion_s())));explorer.Next()
        sections.append(dict(role=role,native_solids=count,edges=edges,edge_count=len(edges),
            maximum_native_edge_tolerance_mm=max(tolerances),sampled_positions_sha256=coordinate_sha(edges)))
    data=dict(schema='actual-C1-coarse-ray-oblique-section-picture-1',section_plane=plane(),zoom_UZ_relative_mm=ZOOM,diagnostic_context=diagnostic,sections=sections,
        drawing_deflection_mm=.001,drawing_scope='Native CAD section edges, sampled only for drawing; not a new geometric admission.',
        radius_mm=1.,native_added_volume_mm3=receipt['new_minus_old_volume_mm3'],
        STEP_exchange='refused',CAD_status='native_C1_master_BREP',source_sha256=before,plan_sha256=plan_hash,
        no_FEA=True,no_geometry_modified=True,source_pose_unchanged=True)
    persist_sections(output,data,before,plan_path,plan_hash)


def render(data_path, expected, output, runtime_expected):
    started=time.monotonic();data_path=Path(data_path);source=sha(__file__);require(sha(data_path)==expected,'Data hash differs')
    data=json.loads(data_path.read_text());check(data);output=Path(output);fresh(output)
    require(all(sha(p)==h for p,h in runtime_expected.items()), 'Pinned render runtime changed before import')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.backends.backend_pdf,matplotlib.backends.backend_svg
    from matplotlib.collections import LineCollection
    from matplotlib.font_manager import findfont,FontProperties
    from matplotlib.patches import Rectangle
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'text.color':'#183347','axes.labelcolor':'#536D7D',
        'svg.fonttype':'none','svg.hashsalt':'carrier-actual-R1-001','pdf.fonttype':42,'path.simplify':False})
    fig,axes=plt.subplots(1,2,figsize=(14.5,8),facecolor='#F8FAFC');fig.subplots_adjust(left=.065,right=.96,top=.75,bottom=.25,wspace=.2)
    fig.text(.06,.94,'993 TURBO · C1 JUNCTION / WINDOW BOUNDARY · ACTUAL CAD SECTION',fontsize=11,weight='bold',color='#536D7D')
    fig.text(.06,.886,'The C1 fillet end at the window boundary',fontsize=24,weight='bold')
    fig.text(.06,.834,'Section containing the native normal ray and Z · source: coarse peak 84037/IP1, before H2 refinement',fontsize=10.4)
    def lines(section):return [[project(p)for p in e['points_xyz_mm']]for e in section['edges']]
    old,new=map(lines,data['sections']);checks=[]
    for index,ax in enumerate(axes):
        ax.set_facecolor('white');ax.grid(color='#DCE4E9',linewidth=.6);ax.set_axisbelow(True)
        if index:ax.add_collection(LineCollection(old,colors='#899AA5',linewidths=1.3,linestyles='dashed',alpha=.8,label='Before contour — reference'))
        ax.add_collection(LineCollection(old if index==0 else new,colors='#30576E'if index==0 else'#087E8B',linewidths=2.4,label='Native CAD section edges'))
        ax.set(xlim=ZOOM[0],ylim=ZOOM[1],xlabel='Oblique horizontal U from the foot (mm)',ylabel='Z − foot Z (mm)');ax.set_aspect('equal',adjustable='box')
        ax.set_title('BEFORE · reference STEP'if index==0 else'AFTER · native C1 BREP master, R1',loc='left',weight='bold',pad=12)
        if index:ax.legend(loc='lower left',fontsize=8,frameon=True)
        for spine in ax.spines.values():spine.set_color('#B8C8D2')
        checks.append(dict(role=data['sections'][index]['role'],xlim=list(ax.get_xlim()),ylim=list(ax.get_ylim()),aspect=ax.get_aspect(),
            full_native_section_edges_submitted=data['sections'][index]['edge_count'],zoom_is_display_crop_only=True))
    hits=data['diagnostic_context']['raw_hits'];ray=[project(h['point_mm'])for h in hits[:3]]
    axes[1].plot([p[0]for p in ray[:2]],[p[1]for p in ray[:2]],color='#D47732',lw=2.0,marker='o',ms=4,label='Local chord inside material')
    axes[1].plot([p[0]for p in ray[1:]],[p[1]for p in ray[1:]],color='#536D7D',lw=1.2,ls=':',marker='o',ms=4)
    for text,xy,target in [('In · face 60',ray[0],(-.13,.17)),('Out · face 62',ray[1],(.18,.13)),('In · face 68',ray[2],(.19,-.25))]:
        axes[1].annotate(text,xy=xy,xytext=target,fontsize=9,color='#536D7D',arrowprops=dict(arrowstyle='->',color='#536D7D',lw=.9))
    inset=fig.add_axes([.075,.084,.22,.12]);inset.add_collection(LineCollection(old,colors='#899AA5',linewidths=.7));inset.autoscale();inset.set_aspect('equal')
    inset.add_patch(Rectangle((ZOOM[0][0],ZOOM[1][0]),ZOOM[0][1]-ZOOM[0][0],ZOOM[1][1]-ZOOM[1][0],fill=False,edgecolor='#D47732',linewidth=1.2))
    inset.set_title('Zoom location in the complete section',fontsize=8);inset.tick_params(labelsize=7)
    fig.text(.33,.187,'Coarse-peak ray: local chord, not whole-wall thickness',fontsize=13,weight='bold',color='#A55A25')
    fig.text(.33,.146,'In60 → Out62: 0.086520 mm inside material; re-entry In68 at W = 0.265083 mm.',fontsize=9.5)
    fig.text(.33,.108,'Native contours; local added/old membership unmeasured. H2 peak not shown; STEP exchange refused.',fontsize=9)
    fig.text(.06,.032,'Complete native edges sampled for drawing (0.001 mm). Display crop only; no whole-wall or global minimum-thickness measurement.',fontsize=9,color='#536D7D')
    font=findfont(FontProperties(family='DejaVu Sans'),fallback_to_default=False)
    paths={str(Path(sys.executable).resolve()),font}
    paths.update(str(Path(m.__file__).resolve())for name,m in list(sys.modules.items())if name.split('.')[0]in ['matplotlib','numpy','PIL']and getattr(m,'__file__',None)and Path(m.__file__).is_file())
    runtime={p:sha(p)for p in sorted(paths)};output.mkdir()
    for ext in ['png','svg','pdf']:
        metadata={'Date':None,'Creator':'Actual R1 CAD section'}if ext=='svg'else({'CreationDate':None,'ModDate':None,'Creator':'Actual R1 CAD section'}if ext=='pdf'else{'Software':'Actual R1 CAD section'})
        fig.savefig(output/('carrier-C1-jonction-coupe-oblique.'+ext),dpi=180,metadata=metadata)
    plt.close(fig)
    paths.update(str(Path(m.__file__).resolve())for name,m in list(sys.modules.items())if name.split('.')[0]in ['matplotlib','numpy','PIL']and getattr(m,'__file__',None)and Path(m.__file__).is_file())
    require(paths<=set(runtime_expected) and all(sha(p)==h for p,h in runtime_expected.items()), 'Post-export runtime outside pinned authority or changed')
    runtime={p:sha(p)for p in sorted(paths)};require(sha(data_path)==expected and sha(__file__)==source and all(sha(p)==h for p,h in runtime.items()),'Data/source/runtime changed during render')
    write(output/'render-receipt.json',dict(status='rendered_actual_native_CAD_contour_picture',data_sha256=expected,source_sha256=source,
        common_axes_and_aspect=True,checks=checks,annotation_ray_actual_XYZ_mm=[h['point_mm']for h in hits[:3]],coarse_source_peak=data['diagnostic_context']['coarse_source_peak'],h2_peak_plotted=False,runtime_files_sha256=runtime,
        elapsed_seconds=time.monotonic()-started,maxRSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        no_geometry_modified=True,no_FEA=True,outputs_sha256={p.name:sha(p)for p in output.iterdir()}))

if __name__=='__main__':
    for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OSD_NUM_THREADS']:os.environ[name]='1'
    mode=sys.argv[1];signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Bounded CAD figure wall cap')))
    signal.setitimer(signal.ITIMER_REAL,150 if mode=='export'else 95);resource.setrlimit(resource.RLIMIT_CPU,(140,160)if mode=='export'else(90,100))
    if mode=='export':export(sys.argv[2],sys.argv[3])
    elif mode=='render':
        require(len(sys.argv)==5 and sha(sys.argv[2])==sys.argv[3], 'Actual render plan hash required');p=checked_plan(sys.argv[2])
        closed_extraction(p);render(p['data'],p['data_sha256'],sys.argv[4],p['runtime_sha256'])
    else:raise ValueError('Use export PLAN FRESH_DIR or render PLAN SHA FRESH_DIR')
