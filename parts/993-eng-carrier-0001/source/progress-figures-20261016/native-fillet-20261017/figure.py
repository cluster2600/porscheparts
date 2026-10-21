"""Read-only native CAD sections, then a portable picture of the actual R1 contour."""
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

X = 81.6750002098722
ZOOM = [[-16., -11.2], [9.9, 14.7]]

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
    require(data['section_X_mm'] == X and [s['role'] for s in data['sections']] == ['before','after'], 'Fixed common CAD section differs')
    for section in data['sections']:
        edges = section['edges'];points = [p for edge in edges for p in edge['points_xyz_mm']]
        require(edges and points and all(len(p)==3 and all(type(c)is float and math.isfinite(c)for c in p)for p in points), 'Invalid CAD samples')
        require(all(len(edge['points_xyz_mm'])>=2 for edge in edges), 'Incomplete curve')
        require(coordinate_sha(edges)==section['sampled_positions_sha256'], 'Native sampled coordinate bits changed')
        require(max(abs(p[0]-X)for p in points)<=section['maximum_native_edge_tolerance_mm'], 'Native section leaves its own plane tolerance')
        require(any(ZOOM[0][0]<=p[1]<=ZOOM[0][1] and ZOOM[1][0]<=p[2]<=ZOOM[1][1]for p in points), 'Actual contour absent from common zoom')

def export(plan_path, output):
    plan_path=Path(plan_path);plan_hash=sha(plan_path);plan=json.loads(plan_path.read_text());root=Path(plan['root'])
    require(plan['section_X_mm']==X and plan['drawing_deflection_mm']==.001 and plan['workers']==0, 'Fixed read-only picture scope differs')
    before={p:sha(root/p)for p in plan['files_sha256']};require(before==plan['files_sha256'], 'A CAD input/runtime changed')
    output=Path(output);fresh(output)
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
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS, TopoDS_Shape
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
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
        operation=BRepAlgoAPI_Section(body,gp_Pln(gp_Pnt(X,0.,0.),gp_Dir(1.,0.,0.)),False)
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
    data=dict(schema='actual-R1-CAD-section-picture-1',section_X_mm=X,zoom_YZ_mm=ZOOM,sections=sections,
        drawing_deflection_mm=.001,drawing_scope='Native CAD section edges, sampled only for drawing; not a new geometric admission.',
        radius_mm=1.,native_added_volume_mm3=receipt['new_minus_old_volume_mm3'],
        STEP_exchange='refused_and_under_control',CAD_status='prototype_native_BREP',source_sha256=before,plan_sha256=plan_hash,
        no_FEA=True,no_geometry_modified=True,source_pose_unchanged=True)
    check(data);check(json.loads(json.dumps(data,allow_nan=False)))
    require(before=={p:sha(root/p)for p in before} and sha(plan_path)==plan_hash,'Input/runtime/plan changed')
    output.mkdir();write(output/'section-data.json',data)
    write(output/'extraction-receipt.json',dict(status='actual_native_CAD_sections_extracted_for_picture',data_sha256=sha(output/'section-data.json'),
        sources_before=before,sources_after={p:sha(root/p)for p in before},source_pose_unchanged=True,no_geometry_modified=True,no_FEA=True,
        edges=[s['edge_count']for s in sections],points=[sum(len(e['points_xyz_mm'])for e in s['edges'])for s in sections],
        maximum_X_residual_mm=max(abs(p[0]-X)for s in sections for e in s['edges']for p in e['points_xyz_mm'])))

def render(data_path, expected, output):
    started=time.monotonic();data_path=Path(data_path);source=sha(__file__);require(sha(data_path)==expected,'Data hash differs')
    data=json.loads(data_path.read_text());check(data);output=Path(output);fresh(output)
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
    fig.text(.06,.94,'993 TURBO · RACCORD CAPOT–NERVURE · COUPE CAO RÉELLE',fontsize=11,weight='bold',color='#536D7D')
    fig.text(.06,.886,'La forme du congé R1, avant et après',fontsize=24,weight='bold')
    fig.text(.06,.834,f'Coupe YZ commune à X = {X:.13f} mm · mêmes axes et mêmes coordonnées · aucun déplacement graphique',fontsize=10.4)
    def lines(section):return [[(p[1],p[2])for p in e['points_xyz_mm']]for e in section['edges']]
    old,new=map(lines,data['sections']);checks=[]
    for index,ax in enumerate(axes):
        ax.set_facecolor('white');ax.grid(color='#DCE4E9',linewidth=.6);ax.set_axisbelow(True)
        if index:ax.add_collection(LineCollection(old,colors='#899AA5',linewidths=1.3,linestyles='dashed',alpha=.8,label='Contour avant — repère'))
        ax.add_collection(LineCollection(old if index==0 else new,colors='#30576E'if index==0 else'#087E8B',linewidths=2.4,label='Arêtes de la coupe CAO'))
        ax.set(xlim=ZOOM[0],ylim=ZOOM[1],xlabel='Y (mm)',ylabel='Z (mm)');ax.set_aspect('equal',adjustable='box')
        ax.set_title('AVANT · STEP de référence'if index==0 else'APRÈS · prototype BREP natif, R1',loc='left',weight='bold',pad=12)
        if index:ax.legend(loc='lower left',fontsize=8,frameon=True)
        for spine in ax.spines.values():spine.set_color('#B8C8D2')
        checks.append(dict(role=data['sections'][index]['role'],xlim=list(ax.get_xlim()),ylim=list(ax.get_ylim()),aspect=ax.get_aspect(),
            full_native_section_edges_submitted=data['sections'][index]['edge_count'],zoom_is_display_crop_only=True))
    points=[p for e in data['sections'][1]['edges']for p in e['points_xyz_mm']if ZOOM[0][0]<=p[1]<=ZOOM[0][1]and ZOOM[1][0]<=p[2]<=ZOOM[1][1]]
    anchor=min(points,key=lambda p:(p[1]+13.8)**2+(p[2]-12.3)**2)
    axes[1].annotate('R1 natif',xy=anchor[1:],xytext=(-15.6,13.9),fontsize=11,weight='bold',color='#087E8B',
        arrowprops=dict(arrowstyle='->',color='#087E8B',lw=1.2))
    inset=fig.add_axes([.075,.084,.22,.12]);inset.add_collection(LineCollection(old,colors='#899AA5',linewidths=.7));inset.autoscale();inset.set_aspect('equal')
    inset.add_patch(Rectangle((ZOOM[0][0],ZOOM[1][0]),ZOOM[0][1]-ZOOM[0][0],ZOOM[1][1]-ZOOM[1][0],fill=False,edgecolor='#D47732',linewidth=1.2))
    inset.set_title('Position du zoom dans la coupe complète',fontsize=8);inset.tick_params(labelsize=7)
    fig.text(.33,.187,'Prototype CAO, échange STEP en contrôle',fontsize=13,weight='bold',color='#A55A25')
    fig.text(.33,.146,f"Le reçu natif constate un ajout de {data['native_added_volume_mm3']:.3f} mm³, sans retrait détecté par le booléen natif.",fontsize=9.5)
    fig.text(.33,.108,'Le STEP réexporté reste refusé : cette image utilise directement le BREP natif candidat.',fontsize=9.5)
    fig.text(.06,.032,'Arêtes natives échantillonnées pour le dessin (déflexion graphique 0,001 mm). La planche décrit la forme ; elle ne vaut pas admission de fabrication ou de résistance.',fontsize=9,color='#536D7D')
    font=findfont(FontProperties(family='DejaVu Sans'),fallback_to_default=False)
    paths={str(Path(sys.executable).resolve()),font}
    paths.update(str(Path(m.__file__).resolve())for name,m in list(sys.modules.items())if name.split('.')[0]in ['matplotlib','numpy','PIL']and getattr(m,'__file__',None)and Path(m.__file__).is_file())
    runtime={p:sha(p)for p in sorted(paths)};output.mkdir()
    for ext in ['png','svg','pdf']:
        metadata={'Date':None,'Creator':'Actual R1 CAD section'}if ext=='svg'else({'CreationDate':None,'ModDate':None,'Creator':'Actual R1 CAD section'}if ext=='pdf'else{'Software':'Actual R1 CAD section'})
        fig.savefig(output/('carrier-conge-R1.'+ext),dpi=180,metadata=metadata)
    plt.close(fig);require(sha(data_path)==expected and sha(__file__)==source and all(sha(p)==h for p,h in runtime.items()),'Data/source/runtime changed during render')
    write(output/'render-receipt.json',dict(status='rendered_actual_native_CAD_contour_picture',data_sha256=expected,source_sha256=source,
        common_axes_and_aspect=True,checks=checks,annotation_anchor_actual_XYZ_mm=anchor,runtime_files_sha256=runtime,
        elapsed_seconds=time.monotonic()-started,maxRSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        no_geometry_modified=True,no_FEA=True,outputs_sha256={p.name:sha(p)for p in output.iterdir()}))

if __name__=='__main__':
    for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OSD_NUM_THREADS']:os.environ[name]='1'
    mode=sys.argv[1];signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Bounded CAD figure wall cap')))
    signal.setitimer(signal.ITIMER_REAL,150 if mode=='export'else 95);resource.setrlimit(resource.RLIMIT_CPU,(140,160)if mode=='export'else(90,100))
    if mode=='export':export(sys.argv[2],sys.argv[3])
    elif mode=='render':render(sys.argv[2],sys.argv[3],sys.argv[4])
    else:raise ValueError('Use export PLAN FRESH_DIR or render DATA SHA FRESH_DIR')
