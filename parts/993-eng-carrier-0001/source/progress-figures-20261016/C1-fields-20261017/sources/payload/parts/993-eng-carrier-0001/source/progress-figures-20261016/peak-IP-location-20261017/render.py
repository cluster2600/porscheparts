"""Four retained IP locations on the real, undeformed FE mesh; no field solve."""
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time

HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def compact(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def fr(value,digits=6):return f'{value:.{digits}f}'.replace('.',',')
def require(value,message):
    if not value:raise ValueError(message)


def project_point(point,axes):
    return tuple(point[index]for index in axes)


def coincident_groups(cases,labels,axes):
    result={}
    for case,label in zip(cases,labels):
        for peak in case['all_global_maximum_ties']:
            key=project_point(peak['reference_undeformed_IP_xyz_mm'],axes)
            result.setdefault(key,[]).append(label)
    return result


def validate_data(data,source_cases,assessment,terminal,geometry,study,mesh):
    expected=[('mesh-9','combined-rigid-static'),('mesh-9','combined-spring-1000-static'),
              ('mesh-7','combined-rigid-static'),('mesh-7','combined-spring-1000-static')]
    require([(c['mesh'],c['case'])for c in data['cases']]==expected,'Exactly four ordered real cases are required')
    require(compact(data['cases'])==compact(source_cases)==compact(assessment['cases']),'The complete four-case receipts differ')
    require(assessment['runtime_unchanged']and assessment['inputs_unchanged']and assessment['returncode']==0,
            'The actual peak postprocessor did not finish unchanged')
    require(terminal['actual_tool_returncode']==0 and terminal['group_reaped_and_empty_no_signals']and
            terminal['all_four_global_maximum_ties_retained'],'The real terminal closure differs')
    require(data['labels']==['A','B','C','D'],'The four visible case identities differ')
    for case in data['cases']:
        peaks=case['all_global_maximum_ties']
        require(case['no_peak_excluded']and case['maximum_ties']==len(peaks)==1,'Every exact global maximum must be retained')
        for peak in peaks:
            require(peak['VM_MPa']==case['maximum_VM_MPa']and math.isfinite(peak['VM_MPa']),'Maximum stress differs')
            require(len(peak['reference_undeformed_IP_xyz_mm'])==3 and all(math.isfinite(x)for x in peak['reference_undeformed_IP_xyz_mm']),
                    'A finite actual reference IP is required')
            measure=peak['corner_measure']
            require(len(measure['six_corner_edge_lengths_mm'])==6 and measure['measured_h_mm']==max(measure['six_corner_edge_lengths_mm']),
                    'The preserved h is not the measured maximum corner edge')
    require(data['cases'][0]['all_global_maximum_ties'][0]['reference_undeformed_IP_xyz_mm']==
            data['cases'][1]['all_global_maximum_ties'][0]['reference_undeformed_IP_xyz_mm'],'The real mesh9 coincidence changed')
    require(data['force_N']==study['load_cases']['combined']['force_N']==[0,0,-4000]and
            data['moment_Nmm']==study['load_cases']['combined']['moment_Nmm']==[0,850000,0],'The actual combined load differs')
    require(data['spring_stiffness_N_per_mm_per_eye_and_axis']==1000. and 1000. in study['support_sensitivity_per_eye_N_mm'],
            'The distributed spring case differs')
    require(data['CAD_mass_kg']==geometry['dense_reference_mass_kg']and
            data['CAD_mass_ceiling_kg']==geometry['declared_mass_ceiling_kg']==1.3 and data['CAD_mass_kg']<=1.3,
            'The mass of the unchanged CAD model differs')
    require(data['reference_density_kg_m3']==4420. and study['material']['density_tonne_mm3']==4.42e-9,'Reference mass density differs')
    require(mesh['element_order']==2 and mesh['straight_midsides'],'The linear corner-facet background scope differs')
    require(data['background']['faces']==45654 and data['background']['arrays']['faces']['shape']==[45654,3],
            'All real mesh7 surface faces are required')
    require(all(data[k]is True for k in ['no_continuous_stress_map','no_geometry_amplification','no_point_jitter',
                                        'distances_are_to_discrete_nodes_only']),'The figure scope changed')


def verify(plan):
    require(plan['schema']=='four-real-IP-localisation-render-plan-1'and plan['resources']==
            dict(inner_wall_seconds=95,CPU_soft_seconds=90,CPU_hard_seconds=91,outer_wall_seconds=120,
                 cleanup_grace_seconds=[10,10],threads=1,workers=0,nice=10),'The fixed rendering bounds differ')
    before={name:sha(HERE/name)for name in plan['files_sha256']}
    require(before==plan['files_sha256'],'A figure source or retained data file changed')
    data=json.loads((HERE/'data/figure-data.json').read_text())
    cases=[json.loads((HERE/'data'/name).read_text())for name in data['case_source_files']]
    load=lambda name:json.loads((HERE/'data'/name).read_text())
    terminal=load('peak-root-terminal.json');assessment=load('peak-assessment.json')
    require(sha(HERE/'data/peak-assessment.json')==terminal['assessment_sha256'],'The real assessment binding differs')
    for row in terminal['case_files']:
        require(sha(HERE/'data'/row['file'])==row['sha256'],'A real case no longer matches its root closure')
    for name,binding in data['original_sources'].items():
        require(sha(HERE/'data'/name)==binding['sha256']==binding['copied_sha256'],'A byte-identical source copy differs')
    validate_data(data,cases,assessment,terminal,load('geometry.json'),load('study.json'),load('mesh-7.json'))
    return before,data


def main(output):
    started,cpu=time.monotonic(),time.process_time();plan_hash=sha(HERE/'render-plan.json')
    plan=json.loads((HERE/'render-plan.json').read_text());pins,data=verify(plan)
    output=Path(output).absolute()
    require(not output.exists()and not any(p.is_symlink()for p in [output,*output.parents]),'A fresh nonsymlink output is required')
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('95s scientific rendering budget')))
    signal.setitimer(signal.ITIMER_REAL,95);resource.setrlimit(resource.RLIMIT_CPU,(90,91))
    for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='1'
    os.environ['MPLBACKEND']='Agg'
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.backends.backend_pdf
    import matplotlib.backends.backend_svg
    from matplotlib.collections import PolyCollection
    from matplotlib.patches import Rectangle
    from matplotlib import font_manager
    import numpy as np
    import PIL
    versions=dict(python=sys.version.split()[0],matplotlib=matplotlib.__version__,numpy=np.__version__,Pillow=PIL.__version__)
    require(versions==data['renderer_runtime_versions'],'The pinned plotting runtime differs')
    with np.load(HERE/'data/mesh-7.npz',allow_pickle=False)as archive:
        tags,xyz,faces=archive['tags'],archive['xyz'],archive['faces']
    for name,array in [('tags',tags),('xyz',xyz),('faces',faces)]:
        actual=dict(dtype=array.dtype.str,shape=list(array.shape),sha256=hashlib.sha256(array.tobytes()).hexdigest())
        require(actual==data['background']['arrays'][name],'A complete native mesh array differs')
    require(np.isfinite(xyz).all()and np.all(tags[1:]>tags[:-1]),'The original finite coordinates/sorted node IDs are required')
    indices=np.searchsorted(tags,faces)
    require(indices.max()<len(tags)and np.array_equal(tags[indices],faces),'A real surface face references an unknown node')
    triangles=xyz[indices];bounds=np.array([xyz.min(0),xyz.max(0)])
    ink,muted,grey='#183347','#536D7D','#B9C5CC'
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':10.5,'text.color':ink,'axes.labelcolor':muted,
        'xtick.color':muted,'ytick.color':muted,'axes.edgecolor':'#BBC8D0','svg.fonttype':'none',
        'svg.hashsalt':'carrier-four-actual-peak-IP-001','pdf.fonttype':42,'path.simplify':False})
    fig=plt.figure(figsize=(16,11.5),facecolor='#F8FAFC')
    fig.text(.05,.961,'993 TURBO · MODÈLE BOUNDED-WEBS · QUATRE CAS ÉLASTIQUES CONSERVÉS',fontsize=10.5,weight='bold',color=muted)
    fig.text(.05,.917,'Localiser les quatre pics aux points d’intégration',fontsize=24,weight='bold')
    fig.text(.05,.880,'Fz = −4 000 N · My = +850 000 N·mm · rigide ou K = 1 000 N/mm par œil et par axe',fontsize=12,color=muted)
    fig.text(.05,.846,'Masse du modèle CAD à 4 420 kg/m³ : 1,262 kg ≤ plafond déclaré 1,30 kg',fontsize=11.5,weight='bold')
    counts,checks={},{}
    for panel in data['panels']:
        axes=panel['axes'];ax=fig.add_axes(panel['rect'],facecolor='white')
        ax.add_collection(PolyCollection(triangles[:,:,axes],facecolors=grey,edgecolors='none',rasterized=True,zorder=1))
        counts[panel['id']]=len(faces)
        for case,label,style in zip(data['cases'],data['labels'],data['styles']):
            for peak in case['all_global_maximum_ties']:
                p=project_point(peak['reference_undeformed_IP_xyz_mm'],axes)
                ax.plot(*p,marker=style['marker'],markersize=math.sqrt(style['size']),markeredgecolor=style['color'],
                    markerfacecolor=style['color']if style['fill']else'none',markeredgewidth=1.6,linestyle='None',zorder=8)
        for point,labels in coincident_groups(data['cases'],data['labels'],axes).items():
            if panel['xlim'][0]<=point[0]<=panel['xlim'][1]and panel['ylim'][0]<=point[1]<=panel['ylim'][1]:
                ax.annotate('+'.join(labels),xy=point,xytext=(7,7),textcoords='offset points',fontsize=10,weight='bold',
                    bbox=dict(fc='white',ec='none',alpha=.85,pad=1.5),zorder=12)
        ax.set(xlim=panel['xlim'],ylim=panel['ylim'],xlabel='XYZ'[axes[0]]+' (mm)',ylabel='XYZ'[axes[1]]+' (mm)')
        ax.set_aspect('equal',adjustable='box');ax.set_title(panel['title'],loc='left',fontsize=11.5,weight='bold',pad=8)
        ax.spines[['top','right']].set_visible(False);ax.tick_params(labelsize=9)
        if panel['id']in ('XY','XZ'):
            require(all(panel['xlim'][0]<=q<=panel['xlim'][1]for q in bounds[:,axes[0]])and
                    all(panel['ylim'][0]<=q<=panel['ylim'][1]for q in bounds[:,axes[1]]),'A whole-part view clips real geometry')
        if panel['id']=='XY':
            ax.add_patch(Rectangle((60,-26),50,52,fill=False,ec=ink,lw=.8,ls=':',zorder=3))
        if panel['id']=='XZ':
            ax.add_patch(Rectangle((250,-25),50,50,fill=False,ec=ink,lw=.8,ls=':',zorder=3))
        checks[panel['id']]=dict(axes=axes,xlim=list(ax.get_xlim()),ylim=list(ax.get_ylim()),aspect=ax.get_aspect(),
            all_peak_markers_submitted=4,marker_coordinate_jitter=False)
    # Numerical table retains all four cases, including the coincident A/B.
    fig.text(.705,.405,'TOUS LES MAXIMA GLOBAUX',fontsize=10.5,weight='bold',color=muted)
    for i,(case,label,style)in enumerate(zip(data['cases'],data['labels'],data['styles'])):
        y=.373-i*.041;peak=case['all_global_maximum_ties'][0]
        title=('mesh9'if case['mesh']=='mesh-9'else'mesh7')+' · '+('rigide'if'rigid'in case['case']else'K1000')
        fig.text(.705,y,label+'  '+title,fontsize=10.3,weight='bold',color=style['color'])
        fig.text(.705,y-.017,fr(case['maximum_VM_MPa'])+' MPa  |  h = '+fr(peak['corner_measure']['measured_h_mm'])+' mm',fontsize=9.2)
    fig.text(.705,.190,'A et B : même position exacte ;\ncercle et croix concentriques, sans décalage.',fontsize=9.2,color=muted,linespacing=1.5)
    table_ax=fig.add_axes([.05,.059,.90,.112]);table_ax.axis('off');rows=[]
    for label,case in zip(data['labels'],data['cases']):
        peak=case['all_global_maximum_ties'][0];support=peak['nearest_prescribed_displacement_node']or peak['nearest_grounded_spring_node'];load=peak['nearest_applied_load_node']
        rows.append([label,str(peak['element_id'])+' / '+str(peak['IP_one_based']),
            str(support['node_id']),fr(support['distance_mm'],3),str(load['node_id']),fr(load['distance_mm'],3)])
    table=table_ax.table(cellText=rows,colLabels=['Repère','Élément / IP','Nœud appui¹','Distance¹ (mm)','Nœud chargé','Distance (mm)'],
        colWidths=[.08,.19,.20,.18,.19,.16],loc='center',cellLoc='left',colLoc='left')
    table.auto_set_font_size(False);table.set_fontsize(10.);table.scale(1,1.45)
    for (row,col),cell in table.get_celld().items():
        cell.set_edgecolor('#DDE5EB');cell.set_facecolor('#E7EEF3'if row==0 else'white')
        if row==0:cell.set_text_props(weight='bold',color=ink)
    fig.text(.05,.035,'Fond : 45 654 facettes linéaires du vrai maillage EF7, non déformées. Couleur uniforme ; aucune carte continue interpolée.',fontsize=9.5,color=muted)
    fig.text(.05,.016,'h : plus grande des six arêtes de coin de l’élément du pic. ¹ Déplacement imposé ou ressort au sol ; distances aux seuls nœuds, pas aux surfaces.',fontsize=9.5,color=muted)
    require(counts=={p['id']:45654 for p in data['panels']}and all(c['aspect']==1. for c in checks.values()),'Every surface face and equal metric axes are required')
    font=font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans'),fallback_to_default=False)
    runtime_paths={str(Path(sys.executable).resolve()),font}
    runtime_paths.update(str(Path(m.__file__).resolve())for name,m in list(sys.modules.items())if name.split('.')[0]in ['matplotlib','numpy','PIL']and getattr(m,'__file__',None)and Path(m.__file__).is_file())
    runtime={p:sha(p)for p in sorted(runtime_paths)}
    require({n:sha(HERE/n)for n in pins}==pins and sha(HERE/'render-plan.json')==plan_hash,'A source or plan changed before output')
    output.mkdir();stem='carrier-quatre-pics-IP-localisation'
    for ext in ['png','svg','pdf']:
        metadata={'Date':None,'Creator':'Actual four-IP location renderer'}if ext=='svg'else({'CreationDate':None,'ModDate':None,'Creator':'Actual four-IP location renderer'}if ext=='pdf'else{'Software':'Actual four-IP location renderer'})
        fig.savefig(output/(stem+'.'+ext),dpi=180,metadata=metadata)
    plt.close(fig)
    require({n:sha(HERE/n)for n in pins}==pins and sha(HERE/'render-plan.json')==plan_hash,'A figure source or plan changed')
    require(all(sha(p)==h for p,h in runtime.items()),'A plotting runtime file changed')
    receipt=dict(schema='four-real-IP-location-render-receipt-1',status='rendered_four_actual_peak_locations_no_new_FEA',
        source_files_sha256=pins,plan_sha256=plan_hash,all_faces_per_panel=counts,projection_checks=checks,
        exact_source_peak_cases=data['cases'],all_four_maxima_preserved=True,coincident_mesh9_preserved_without_jitter=True,
        geometry_modified=False,deformation_amplified=False,stress_map_interpolated=False,FEA_started=False,mesh_generated=False,
        mass_scope='Unchanged CAD model at4420kg/m3; no FE mass computed',distance_scope='Retained discrete node sets only',
        worker_processes=0,threads=1,wall_seconds=time.monotonic()-started,CPU_seconds=time.process_time()-cpu,
        maxRSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,renderer_runtime_versions=versions,
        renderer_runtime_files_sha256=runtime,inputs_runtime_unchanged=True,global_admission=False,
        outputs_sha256={p.name:sha(p)for p in output.iterdir()if p.is_file()})
    (output/'render-receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    signal.setitimer(signal.ITIMER_REAL,0)
    print(json.dumps(dict(status=receipt['status'],wall_seconds=receipt['wall_seconds'],receipt_sha256=sha(output/'render-receipt.json'))))


if __name__=='__main__':
    if sys.argv[1]=='preflight':
        pins,_=verify(json.loads((HERE/'render-plan.json').read_text()))
        print(json.dumps(dict(status='scientific_figure_prepared_no_render',files_sha256=pins,rendered=False,FEA_started=False)))
    elif len(sys.argv)==2:main(sys.argv[1])
    else:raise SystemExit('usage: render.py preflight | FRESH_OUTPUT')
