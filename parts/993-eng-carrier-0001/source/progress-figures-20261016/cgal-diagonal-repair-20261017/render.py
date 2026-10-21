"""Draw two real topology changes; fixed diagram positions, explicitly out of scale."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import time

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load():
    pins=json.loads((HERE/'inputs.json').read_text())['files_sha256']
    if any(sha(HERE/n)!=h for n,h in pins.items()):raise ValueError('Frozen data/helper changed')
    data=json.loads((HERE/'data.json').read_text())
    spec=importlib.util.spec_from_file_location('private_cgal_figure_oriented',HERE/'oriented_triangles.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    if data['native_summary']!={'native_cases':146,'diagonals_changed':146,
       'all_coordinates_exactly_unchanged':True,'all_directed_boundaries_preserved':True,'global_admission':False}:
        raise ValueError('Native finite batch summary differs')
    if [r['original_face_ids'] for r in data['examples']]!=[[3341,3475],[8753,8754]]:
        raise ValueError('The two specified real examples are required')
    for example in data['examples']:
        row,quad=example['native'],example['quad']
        if row['case']!=example['case'] or quad['name']!=example['case']:raise ValueError('Case identity differs')
        if row['coordinates_exactly_unchanged'] is not True or row['directed_boundary_preserved'] is not True:
            raise ValueError('Native coordinate/boundary proof missing')
        if row['exactly_coplanar'] is not quad['expected_exact_coplanarity'] or row['kept_source_diagonal'] is not False:
            raise ValueError('Unexpected native case verdict')
        if helper.normalise_oriented_triangles(row['triangles_original_vertex_ids'])!=helper.normalise_oriented_triangles(example['operation']['steps'][0]['new_triangles']):
            raise ValueError('Oriented native triangles differ from frozen operation plan')
        if row['source_diagonal_original_vertex_ids']!=quad['original_diagonal_ids']:raise ValueError('Original diagonal differs')
    return data


def main():
    start=time.monotonic()
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('60 s figure budget')))
    signal.setitimer(signal.ITIMER_REAL,60)
    for n in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[n]='1'
    data=load();output=Path(sys.argv[1]).absolute()
    if output.exists() or output.is_symlink():raise FileExistsError('Fresh output required')
    frozen={str(HERE/n):sha(HERE/n) for n in ['render.py','inputs.json','data.json','oriented_triangles.py']}
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.backends.backend_agg
    import matplotlib.backends.backend_svg
    import matplotlib.backends.backend_pdf
    from matplotlib.patches import Polygon, FancyArrowPatch
    from matplotlib import font_manager
    import numpy as np
    import PIL
    versions={'python':sys.version.split()[0],'matplotlib':matplotlib.__version__,'numpy':np.__version__,'Pillow':PIL.__version__}
    if versions!=data['runtime_versions']:raise ValueError('Pinned rendering versions required')
    font=font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans'),fallback_to_default=False)
    runtime_paths={str(Path(sys.executable).resolve()),font}
    runtime_paths.update(str(Path(m.__file__).resolve()) for name,m in list(sys.modules.items())
                         if name.split('.')[0] in ['matplotlib','numpy','PIL']
                         and getattr(m,'__file__',None) and Path(m.__file__).is_file())
    runtime={p:sha(p) for p in sorted(runtime_paths)}
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':11,
       'text.color':'#192C3B','svg.fonttype':'none','svg.hashsalt':'carrier-cgal-two-quads-001',
       'pdf.fonttype':42,'path.simplify':False})
    fig=plt.figure(figsize=(15.2,11.2),facecolor='#FAFCFE')
    fig.text(.065,.951,'COMPRENDRE LA RETRIANGULATION · DEUX EXEMPLES RÉELS',fontsize=11,weight='bold',color='#506C7D')
    fig.text(.065,.913,'146 quads traités par CGAL · pas d’admission globale',fontsize=22,weight='bold')
    fig.text(.065,.878,'Quatre sommets fixes, même contour : seule la diagonale interne change.',fontsize=14,color='#334D5E')
    fig.text(.065,.844,'SCHÉMAS TOPOLOGIQUES HORS ÉCHELLE · les formes dessinées ne représentent pas la géométrie 3D',
             fontsize=10.5,color='#647A88')
    positions=np.asarray([[.09,.12],[.95,.13],[.87,.89],[.12,.84]],dtype=np.float64)
    labels=[(-.03,-.055),(.035,-.03),(.035,.035),(-.035,.035)]
    view_receipts=[]

    def draw_patch(example,bounds,after):
        ax=fig.add_axes(bounds);ax.set_aspect('equal');ax.axis('off');ax.set_xlim(-.04,1.08);ax.set_ylim(-.07,1.06)
        ids=example['quad']['boundary_ids'];points={i:p for i,p in zip(ids,positions)}
        row=example['native'];triangles=row['triangles_original_vertex_ids'] if after else example['operation']['expected_before']
        faces=['N1','N2'] if after else [str(i) for i in example['operation']['face_ids']]
        fills=['#D9EDF5','#B8D9E8'] if after else ['#F6E8D5','#EDD0AA']
        color='#086C99' if after else '#C87520'
        for t,label,fill in zip(triangles,faces,fills):
            pts=np.asarray([points[i] for i in t])
            ax.add_patch(Polygon(pts,closed=True,facecolor=fill,edgecolor='none',zorder=1))
            center=pts.mean(axis=0)
            ax.text(*center,label,ha='center',va='center',fontsize=12,weight='bold',color=color)
        closed=np.vstack([positions,positions[0]])
        ax.plot(closed[:,0],closed[:,1],color='#334D5E',lw=2.2,zorder=3)
        diagonal=row['chosen_diagonal_original_vertex_ids'] if after else row['source_diagonal_original_vertex_ids']
        d=np.asarray([points[i] for i in diagonal])
        ax.plot(d[:,0],d[:,1],color=color,lw=3.0,ls='-' if after else '--',zorder=4)
        ax.scatter(positions[:,0],positions[:,1],s=48,color='#192C3B',edgecolors='white',linewidths=.8,zorder=5)
        for i,point,offset in zip(ids,positions,labels):
            ax.text(*(point+offset),str(i),fontsize=12,weight='bold',
                    ha='right' if offset[0]<0 else 'left',va='top' if offset[1]<0 else 'bottom')
        view_receipts.append({'case':example['case'],'after':after,
             'diagram_positions_by_boundary_ID':{str(i):p.tolist() for i,p in zip(ids,positions)},
             'drawn_triangles_exact_ID_order':triangles,'drawn_diagonal_IDs':diagonal,
             'physical_scale_claimed':False})
        return triangles,faces

    for k,example in enumerate(data['examples']):
        top=.768 if k==0 else .410
        row=example['native'];face_text='/'.join(str(i) for i in example['original_face_ids'])
        fig.text(.065,top+.026,example['kind']+' · faces '+face_text,fontsize=16,weight='bold')
        fig.text(.355,top+.026,'AVANT',fontsize=11,weight='bold',color='#9B601F')
        fig.text(.745,top+.026,'APRÈS CGAL',fontsize=11,weight='bold',color='#086C99')
        y=top-.232
        before,before_labels=draw_patch(example,[.10,y,.32,.25],False)
        after,after_labels=draw_patch(example,[.56,y,.32,.25],True)
        fig.add_artist(FancyArrowPatch((.46,top-.10),(.54,top-.10),transform=fig.transFigure,
                        arrowstyle='-|>',mutation_scale=22,lw=1.8,color='#8195A2'))
        old='–'.join(map(str,row['source_diagonal_original_vertex_ids']))
        new='–'.join(map(str,row['chosen_diagonal_original_vertex_ids']))
        fig.text(.50,top-.145,'Diagonale\n'+old+'\n↓\n'+new,ha='center',va='center',fontsize=10.5,linespacing=1.35,color='#506C7D')
        for x,triangles,names,color in [(.095,before,before_labels,'#9B601F'),(.56,after,after_labels,'#086C99')]:
            text='\n'.join(label+' : '+ ' · '.join(map(str,t)) for label,t in zip(names,triangles))
            fig.text(x,top-.246,text,fontsize=10.5,color=color,linespacing=1.55,va='top')
        note=('GRID : quatre points exactement coplanaires.' if row['exactly_coplanar'] else
              'SKIN : quatre points non coplanaires ; même surface 3D exacte non revendiquée.')
        fig.text(.065,top-.292,note,fontsize=11,color='#506C7D')
    fig.text(.065,.044,'IDs de sommets et triangles issus des reçus réels ; N1/N2 désignent les deux lignes retournées par CGAL.\n'
             'Plan 050b04b6… · quads 080fb715… · natif 5d012815… · liaison orientée 26e2cac8… · données et empreintes jointes.',
             fontsize=9.3,color='#506C7D',linespacing=1.55)
    if any(view_receipts[i]['diagram_positions_by_boundary_ID']!=view_receipts[i+1]['diagram_positions_by_boundary_ID'] for i in [0,2]):
        raise ValueError('Drawn vertex positions changed between before/after')
    output.mkdir();stem='carrier-cgal-deux-quads-avant-apres'
    fig.savefig(output/(stem+'.png'),dpi=200,metadata={'Software':'Frozen CGAL topology figure renderer'})
    fig.savefig(output/(stem+'.svg'),metadata={'Date':None,'Creator':'Frozen CGAL topology figure renderer'})
    fig.savefig(output/(stem+'.pdf'),metadata={'CreationDate':None,'ModDate':None,'Creator':'Frozen CGAL topology figure renderer'})
    plt.close(fig)
    if any(sha(p)!=h for p,h in frozen.items()) or any(sha(p)!=h for p,h in runtime.items()):raise ValueError('Input/source/runtime changed')
    receipt={'schema':'real-cgal-two-quad-figure-render-1','status':'rendered_topology_only_out_of_scale',
             'source_and_data_sha256':frozen,'source_evidence':data['sources'],
             'render_runtime_versions':versions,'runtime_files_sha256':runtime,'inputs_and_runtime_unchanged':True,
             'drawn_views':view_receipts,'same_drawn_positions_before_after':True,'mesh_published_or_modified':False,
             'physical_scale_claimed':False,'same_exact_3D_SKIN_surface_claimed':False,
             'global_admission':False,'wall_seconds':time.monotonic()-start,'worker_processes':0,
             'outputs_sha256':{p.name:sha(p) for p in output.iterdir() if p.is_file()}}
    (output/'render-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    signal.setitimer(signal.ITIMER_REAL,0)
    print(json.dumps({'status':receipt['status'],'wall_seconds':receipt['wall_seconds'],'receipt_sha256':sha(output/'render-receipt.json')}))


if __name__=='__main__':
    main()
