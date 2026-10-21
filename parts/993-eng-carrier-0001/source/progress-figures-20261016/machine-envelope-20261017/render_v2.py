"""Actual full-mesh projections and nominal machine envelopes only."""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def fr(value,digits=3):return f'{value:.{digits}f}'.replace('.',',')


def main(output):
    start=time.monotonic();CPU=time.process_time()
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('60s figure budget')))
    signal.setitimer(signal.ITIMER_REAL,60)
    resource.setrlimit(resource.RLIMIT_CPU,(58,59))
    for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
    os.environ['MPLBACKEND']='Agg'
    output=Path(output).absolute()
    if output.exists()or any(p.is_symlink()for p in [output,*output.parents]):raise ValueError('A fresh output without symlinks is required')
    plan=json.loads((HERE/'render-plan-v2.json').read_text());pins={str(HERE/n):h for n,h in plan['files_sha256'].items()}
    pins[str(HERE/'render-plan-v2.json')]=sha(HERE/'render-plan-v2.json')
    def verify():
        if any(sha(p)!=h for p,h in pins.items()):raise ValueError('A source or data file changed')
    verify();data=json.loads((HERE/'data/figure-data.json').read_text())
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.backends.backend_pdf
    import matplotlib.backends.backend_svg
    from matplotlib.collections import PolyCollection
    from matplotlib.patches import Rectangle
    from matplotlib.lines import Line2D
    from matplotlib import font_manager
    import numpy as np
    import PIL
    versions=dict(python=sys.version.split()[0],matplotlib=matplotlib.__version__,numpy=np.__version__,Pillow=PIL.__version__)
    if versions!=data['renderer_runtime_versions']:raise ValueError('The pinned rendering versions differ')
    with np.load(HERE/'data/part.npz',allow_pickle=False)as archive:
        if set(archive.files)!={'vertices','faces'}:raise ValueError('Only the original posed mesh arrays are accepted')
        vertices,faces=archive['vertices'],archive['faces']
    for name,array in [('vertices',vertices),('faces',faces)]:
        actual=dict(dtype=array.dtype.str,shape=list(array.shape),sha256=hashlib.sha256(array.tobytes()).hexdigest())
        if actual!=data['arrays'][name]:raise ValueError('The complete original array changed')
    if len(faces)!=587404 or not np.isfinite(vertices).all()or faces.min()<0 or faces.max()>=len(vertices):raise ValueError('The complete real triangle set is required')
    bounds=np.array([vertices.min(0),vertices.max(0)]);expected=np.asarray(data['posed_bounds_mm'])
    if not np.array_equal(bounds,expected):raise ValueError('The exact posed bounds differ')
    params=json.loads((HERE/'data/inputs-v2.json').read_text())['parameters']
    if params['rotation_degrees_xyz']!=[0,0,45]or params['support_gap_mm']!=10.0 or params['plate_size_mm']!=[500.,500.]or params['plate_thickness_mm']!=20.:raise ValueError('The actual pose/plate parameters differ')
    margins=dict(part_to_study_plate_each_edge_mm=[bounds[0,0]+250,250-bounds[1,0],bounds[0,1]+250,250-bounds[1,1]],
        study_plate_to_650_chamber_each_edge_mm=[75.]*4,
        part_to_650_chamber_each_edge_mm=[bounds[0,0]+325,325-bounds[1,0],bounds[0,1]+325,325-bounds[1,1]],
        EP_M650_occupied_height_including_plate_mm=20+float(bounds[1,2]),
        BLT_S600_occupied_height_excluding_plate_mm=float(bounds[1,2]))
    if margins!=data['margins']:raise ValueError('The exact margins or height conventions differ')
    blue='#176C91';ink='#183347';muted='#536D7D';orange='#B67227';grey='#8D9DA5'
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':10.5,'text.color':ink,'axes.labelcolor':muted,
        'xtick.color':muted,'ytick.color':muted,'axes.edgecolor':'#B5C3CB','svg.fonttype':'none',
        'svg.hashsalt':'carrier-nominal-machine-envelope-001','pdf.fonttype':42,'path.simplify':False})
    fig=plt.figure(figsize=(16,11.3),facecolor='#F8FAFC')
    fig.text(.048,.956,'993 TURBO · CARRIER · POSE CONSERVÉE',fontsize=11,weight='bold',color=muted)
    fig.text(.048,.914,'Encombrement nominal : pièce, plaque et chambre',fontsize=24,weight='bold')
    fig.text(.048,.879,'Rotation Z = 45° · projections du maillage complet · 587 404 triangles · dimensions en millimètres',fontsize=12,color=muted)
    fig.text(.048,.839,'Pièce posée : 451,134 × 451,134 × 52 mm',fontsize=16,weight='bold',color=blue)
    counts={};axes_checks={}
    xy=fig.add_axes([.045,.300,.49,.515],facecolor='white')
    xy.add_patch(Rectangle((-325,-325),650,650,fc='#FCF8EF',ec=orange,lw=2,zorder=0))
    xy.add_patch(Rectangle((-250,-250),500,500,fc='#E9EEF1',ec=grey,lw=1.4,zorder=1))
    xy.add_collection(PolyCollection(vertices[faces][:,:,[0,1]],facecolors=blue,edgecolors='none',rasterized=True,zorder=3))
    counts['XY']=len(faces)
    xy.add_patch(Rectangle(tuple(bounds[0,:2]),*(bounds[1,:2]-bounds[0,:2]),fill=False,ec=blue,lw=.9,ls=':',zorder=4))
    xy.annotate('',xy=(325,350),xytext=(-325,350),arrowprops=dict(arrowstyle='<->',color=orange,lw=1.2))
    xy.text(0,360,'650 — chambre nominale',ha='center',va='bottom',color=orange,fontsize=11)
    xy.annotate('',xy=(325,-281),xytext=(250,-281),arrowprops=dict(arrowstyle='<->',color=orange,lw=1.1))
    xy.text(289,-269,'75',ha='center',color=orange,fontsize=10,weight='bold')
    xy.plot([float(bounds[1,0]),250],[278,278],color=blue,lw=1.1)
    xy.plot([float(bounds[1,0])]*2,[274,282],color=blue,lw=1.1);xy.plot([250,250],[274,282],color=blue,lw=1.1)
    xy.text(240,294,'24,433',ha='center',color=blue,fontsize=9,weight='bold')
    xy.axhline(0,color='#C9D4DC',lw=.5,zorder=2);xy.axvline(0,color='#C9D4DC',lw=.5,zorder=2)
    xy.set(xlim=(-375,375),ylim=(-350,395),xlabel='X (mm)',ylabel='Y (mm)')
    xy.set_aspect('equal',adjustable='box');xy.set_xticks([-325,-250,0,250,325]);xy.set_yticks([-325,-250,0,250,325])
    xy.set_title('Vue XY · même pose, sans nouveau placement',loc='left',pad=3,fontsize=11,weight='bold')
    xy.spines[['top','right']].set_visible(False)
    axes_checks['XY']=dict(xlim=list(xy.get_xlim()),ylim=list(xy.get_ylim()),aspect=xy.get_aspect())
    xy.legend(handles=[Rectangle((0,0),1,1,fc=blue,label='Projection de toutes les faces'),
        Rectangle((0,0),1,1,fc='#E9EEF1',ec=grey,label='Plaque d’étude 500 × 500'),
        Line2D([],[],ls=':',color=blue,label='Boîte d’encombrement pièce')],loc='upper left',bbox_to_anchor=(.02,.92),frameon=True,facecolor='white',edgecolor='white',framealpha=.96,fontsize=8.5)
    side=fig.add_axes([.56,.657,.39,.145],facecolor='white')
    side.add_patch(Rectangle((-250,-20),500,20,fc='#A9B6BE',ec=grey,lw=1,zorder=1))
    side.add_collection(PolyCollection(vertices[faces][:,:,[0,2]],facecolors=blue,edgecolors='none',rasterized=True,zorder=3))
    counts['XZ']=len(faces)
    side.axhline(0,color='#80939E',lw=.8)
    side.axhline(10,color=blue,lw=.5,ls=':');side.axhline(62,color=blue,lw=.5,ls=':')
    side.plot([-275,-275],[0,10],color=blue,lw=1)
    side.plot([-280,-270],[0,0],color=blue,lw=1);side.plot([-280,-270],[10,10],color=blue,lw=1)
    side.text(-285,25,'10',ha='center',color=blue,fontsize=10,weight='bold')
    side.annotate('',xy=(273,62),xytext=(273,10),arrowprops=dict(arrowstyle='<->',color=blue,lw=1))
    side.text(288,36,'52',va='center',color=blue,fontsize=10)
    side.set(xlim=(-330,330),ylim=(-30,100),xlabel='X (mm)',ylabel='Z (mm)')
    side.set_aspect('equal',adjustable='box');side.set_xticks([-250,0,250]);side.set_yticks([-20,0,10,62])
    side.set_title('Détail XZ · même échelle en X et Z',loc='left',fontsize=12,weight='bold',pad=16)
    side.spines[['top','right']].set_visible(False)
    axes_checks['XZ']=dict(xlim=list(side.get_xlim()),ylim=list(side.get_ylim()),aspect=side.get_aspect())
    fig.text(.56,.608,'Z0 = dessus de la plaque ; bas de pièce à Z10, sommet à Z62.',fontsize=10,color=muted)
    fig.text(.56,.581,'Le décalage de 10 mm ne décrit pas une hauteur uniforme des supports.',fontsize=9.5,color=muted)
    zax=fig.add_axes([.57,.323,.16,.205],facecolor='white')
    for x,height,bottom,part_bottom,part_top in [(0,800,0,30,82),(1,850,-20,10,62)]:
        zax.add_patch(Rectangle((x-.18,0),.36,height,fc='#FBF5E9',ec=orange,lw=1.2))
        zax.add_patch(Rectangle((x-.18,bottom),.36,20,fc='#A9B6BE',ec=grey,lw=.5))
        zax.add_patch(Rectangle((x-.18,part_bottom),.36,part_top-part_bottom,fc=blue,ec='none'))
        zax.text(x,height+22,str(height),ha='center',fontsize=10,color=orange,weight='bold')
    zax.set(xlim=(-.5,1.5),ylim=(-40,920),ylabel='Z constructeur (mm)')
    zax.set_xticks([0,1],['EP-M650','BLT-S600'],fontsize=8.5);zax.set_yticks([0,400,800]);zax.spines[['top','right']].set_visible(False)
    zax.set_title('Conventions de hauteur',loc='left',fontsize=11,weight='bold',pad=15)
    fig.text(.765,.506,'EP-M650',fontsize=11,weight='bold',color=orange)
    fig.text(.765,.488,'800 mm avec plaque\nOccupation : 20 + 62 = 82 mm\nRéserve nominale : 718 mm',fontsize=10,color=muted,linespacing=1.6,va='top')
    fig.text(.765,.401,'BLT-S600 révisée',fontsize=11,weight='bold',color=orange)
    fig.text(.765,.383,'850 mm hors substrat\nOccupation au-dessus : 62 mm\nRéserve nominale : 788 mm',fontsize=10,color=muted,linespacing=1.6,va='top')
    table_ax=fig.add_axes([.05,.132,.90,.13]);table_ax.axis('off')
    rows=[['Eplus3D · EP-M650','650 × 650 × 800','Plaque incluse','20–120 µm'],
          ['BLT · S600 révisée','650 × 650 × 850','Substrat exclu','Non précisée ici']]
    table=table_ax.table(cellText=rows,colLabels=['Machine','Volume nominal (mm)','Convention Z','Épaisseur de couche'],cellLoc='left',colLoc='left',loc='center',colWidths=[.28,.26,.23,.23])
    table.auto_set_font_size(False);table.set_fontsize(10.5);table.scale(1,1.8)
    for (row,col),cell in table.get_celld().items():
        cell.set_edgecolor('#DBE3E8');cell.set_facecolor('#E6EEF3'if row==0 else'white')
        if row==0:cell.set_text_props(weight='bold',color=ink)
    fig.text(.05,.099,'Ti64 : variante procédé à choisir · fiches officielles relues le 17 octobre 2026 · liens et empreintes dans le README.',fontsize=10,color=muted)
    fig.text(.05,.067,'Pièce et plaque uniquement ; supports finaux non représentés. Les sept régions ont des formes et des hauteurs différentes.',fontsize=9.5,color=muted)
    fig.text(.05,.043,'Compatibilité d’encombrement nominale : bridage, zones utiles et paramètres de fabrication restent à définir.',fontsize=9.5,color=muted)
    if counts!={'XY':587404,'XZ':587404}or any(r['aspect']!=1. for r in axes_checks.values()):raise ValueError('Every face and equal projection axes are required')
    font=font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans'),fallback_to_default=False)
    runtime_paths={str(Path(sys.executable).resolve()),font}
    runtime_paths.update(str(Path(m.__file__).resolve())for n,m in list(sys.modules.items())if n.split('.')[0]in ['matplotlib','numpy','PIL']and getattr(m,'__file__',None)and Path(m.__file__).is_file())
    runtime={p:sha(p)for p in sorted(runtime_paths)}
    verify();output.mkdir();stem='carrier-pose-et-enveloppes-machines'
    for ext in ['png','svg','pdf']:
        metadata={'Date':None,'Creator':'Actual full-mesh nominal-envelope renderer'}if ext=='svg'else({'CreationDate':None,'ModDate':None,'Creator':'Actual full-mesh nominal-envelope renderer'}if ext=='pdf'else{'Software':'Actual full-mesh nominal-envelope renderer'})
        fig.savefig(output/(stem+'.'+ext),dpi=180,metadata=metadata)
    plt.close(fig);verify()
    if any(sha(p)!=h for p,h in runtime.items()):raise ValueError('A rendering runtime file changed')
    receipt=dict(schema='actual-posed-mesh-nominal-machine-envelope-figure-1',status='rendered_complete_mesh_projections_nominal_envelopes',
        all_faces_used_per_projection=counts,projection_axes_checks=axes_checks,posed_bounds_mm=bounds.tolist(),margins=margins,
        source_data_sha256=pins,renderer_runtime_versions=versions,renderer_runtime_files_sha256=runtime,inputs_runtime_unchanged=True,
        geometry_modified=False,decimation=False,final_supports_rendered=False,global_admission=False,worker_processes=0,threads=1,
        wall_seconds=time.monotonic()-start,CPU_seconds=time.process_time()-CPU,maxRSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        outputs_sha256={p.name:sha(p)for p in output.iterdir()if p.is_file()})
    (output/'render-receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
    signal.setitimer(signal.ITIMER_REAL,0)
    print(json.dumps(dict(status=receipt['status'],wall_seconds=receipt['wall_seconds'],receipt_sha256=sha(output/'render-receipt.json'))))


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: render.py FRESH_OUTPUT')
    main(sys.argv[1])
