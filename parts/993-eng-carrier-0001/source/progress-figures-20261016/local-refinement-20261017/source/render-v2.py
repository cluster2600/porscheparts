"""Extract complete real T10 corner edges, then render a portable comparison."""
import hashlib
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import resource
import signal
import struct
import sys
import time

PAIRS=[(i,j)for i in range(4)for j in range(i)]
def require(ok,message):
    if not ok:raise ValueError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
    with Path(path).open('x')as f:json.dump(value,f,ensure_ascii=False,allow_nan=False,separators=(',',':'));f.write('\n')
def load(path):
    spec=importlib.util.spec_from_file_location('_figure_'+Path(path).stem,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def inside(point,bounds):return all(a<=v<=b for v,a,b in zip(point,*bounds))
def edge(a,b):return tuple(sorted((int(a),int(b))))
def position_sha(points):
    return hashlib.sha256(b''.join(struct.pack('<qddd',int(tag),*xyz)for tag,xyz in sorted(points.items()))).hexdigest()

def select(points,elements,region):
    """Literal8e38 centroid predicate and whole edges; deduplicate only node-ID pairs."""
    selected=[];inner=set();incidences=0;selected_edges=set();lengths=[];inner_lengths=[]
    for eid,ids in elements:
        ids=list(map(int,ids[:4]));corners=[points[n]for n in ids]
        centre=[sum(p[d]for p in corners)/4 for d in range(3)]
        chosen=inside(centre,region['bounds_mm'])
        if chosen:selected.append(dict(element_id=int(eid),corner_ids=ids))
        for i,j in PAIRS:
            pair=edge(ids[i],ids[j]);length=math.dist(corners[i],corners[j])
            if chosen:selected_edges.add(pair);lengths.append(length)
            if inside(corners[i],region['bounds_mm'])and inside(corners[j],region['bounds_mm']):
                inner.add(pair);incidences+=1;inner_lengths.append(length)
    require(selected and lengths and inner_lengths and min(lengths)>0 and min(inner_lengths)>0,'Missing or zero whole edges')
    edges=sorted(selected_edges|inner);used=sorted({n for pair in edges for n in pair});coordinates={n:list(map(float,points[n]))for n in used}
    return dict(region_id=region['id'],bounds_mm=region['bounds_mm'],target_h_mm=region['target_h_mm'],
        selected_cells=selected,centroid_selected_six_edge_incidences=6*len(selected),
        whole_inside_edges=[list(p)for p in sorted(inner)],whole_inside_edge_incidences=incidences,
        edges=[list(p)for p in edges],points=[[n,*coordinates[n]]for n in used],positions_sha256=position_sha(coordinates),
        measured_h_mm=max(max(lengths),max(inner_lengths)),selected_lengths_min_max=[min(lengths),max(lengths)],
        inside_lengths_min_max=[min(inner_lengths),max(inner_lengths)])

def check_record(record):
    points={row[0]:row[1:]for row in record['points']}
    require(len(points)==len(record['points'])and all(len(p)==3 and all(math.isfinite(v)for v in p)for p in points.values()),'Invalid positions')
    require(position_sha(points)==record['positions_sha256'],'Coordinate bits changed')
    cells=record['selected_cells'];require(len({c['element_id']for c in cells})==len(cells),'Duplicate selected cell')
    expected=set()
    for cell in cells:
        ids=cell['corner_ids'];require(len(set(ids))==4,'Four distinct original corners required')
        require(inside([sum(points[n][d]for n in ids)/4 for d in range(3)],record['bounds_mm']),'Selected centroid outside box')
        expected.update(edge(ids[i],ids[j])for i,j in PAIRS)
    inner={tuple(p)for p in record['whole_inside_edges']}
    require(all(inside(points[a],record['bounds_mm'])and inside(points[b],record['bounds_mm'])for a,b in inner),'Inside edge changed')
    require(record['edges']==[list(p)for p in sorted(expected|inner)]and record['centroid_selected_six_edge_incidences']==6*len(cells),'A full cell edge omitted')
    require(record['measured_h_mm']==max(math.dist(points[a],points[b])for a,b in record['edges']),'Measured whole-edge h differs')
    return points

def export(plan_path,output):
    plan_path=Path(plan_path);plan=json.loads(plan_path.read_text());root=Path(plan['source_root']);plan_sha=sha(plan_path)
    require(plan['launch_ready']is True and all(type(h)is str and len(h)==64 for h in plan['files_sha256'].values()),'Actual002 bindings pending; no geometry read')
    required={plan[k]for k in ['energy_source','measure_source','specification','final_terminal','final_assessment','final_supervision']}
    required.update(folder+'/'+name for folder in [plan['before_mesh'],plan['after_mesh']]for name in ['mesh.inp','mesh.npz'])
    require(required<=set(plan['files_sha256'])and plan['schema']=='actual-local-refinement-figure-plan-1','Missing complete input/source bindings')
    before={p:sha(root/p)for p in plan['files_sha256']};require(before==plan['files_sha256'],'A real source changed')
    output=Path(output);require(not output.exists()and not any(p.is_symlink()for p in [output,*output.parents]),'Fresh export required')
    terminal=json.loads((root/plan['final_terminal']).read_text());assessment=json.loads((root/plan['final_assessment']).read_text())
    require(terminal['actual_tool_returncode']==0 and terminal['pins_unchanged']is True and
        assessment['status']=='local_adaptive_discrete_h2_mesh_checked_no_FEA'and assessment['h2_qualified']is True and assessment['pins_unchanged']is True,'Real002 not passed')
    require(terminal['assessment_sha256']==sha(root/plan['final_assessment']),'Actual002 assessment/terminal mismatch')
    supervision=json.loads((root/plan['final_supervision']).read_text())
    require(terminal['supervision_sha256']==sha(root/plan['final_supervision'])and supervision['actual_returncode']==0 and
        supervision['direct_child_reaped']is True and supervision['no_non_zombie_group_members']is True and
        supervision['sources_and_plan_unchanged']is True,'Actual002 supervision not successfully closed')
    for key in ('mesh.inp','mesh.npz'):
        name=plan['after_mesh']+'/'+key;require(terminal['output_files'][name]['sha256']==before[name],'Actual002 mesh binding differs')
    energy=load(root/plan['energy_source']);measure=load(root/plan['measure_source'])
    regions=json.loads((root/plan['specification']).read_text())['regions'];records=[]
    for label,folder in [('before',plan['before_mesh']),('after',plan['after_mesh'])]:
        tags,xyz,eids,indices=energy.read_mesh(root/folder/'mesh.inp')
        points={int(tag):list(map(float,p))for tag,p in zip(tags,xyz)}
        elements=[(int(eid),tags[row].tolist())for eid,row in zip(eids,indices)]
        rows=[]
        for region in regions:
            actual=measure.region_edges(points,elements,region);record=select(points,elements,region);check_record(record)
            require([c['element_id']for c in record['selected_cells']]==actual['centroid_selected_element_ids']and
                record['whole_inside_edge_incidences']==actual['all_mesh_whole_edge_incidences_with_both_endpoints_in_box_count']and
                record['measured_h_mm']==actual['measured_h_mm'],'Selection differs from unchanged8e38')
            if label=='after':require(actual==next(r for r in assessment['measurements']if r['region_id']==region['id']),'Real002 complete measurement differs')
            rows.append(dict(record,measurement=actual))
        records.append(dict(role=label,nodes=len(tags),elements=len(eids),regions=rows));del points,elements,xyz,indices
    data=dict(schema='actual-local-T10-corner-edge-comparison-1',regions=regions,meshes=records,source_files_sha256=before,
        final_terminal_sha256=sha(root/plan['final_terminal']),export_plan_sha256=plan_sha,adaptive_passes=terminal['adaptive_passes'],coordinates='Original INP binary64, unchanged axes, no pose/deformation',
        all_selected_cell_six_edges=True,all_whole_inside_edges=True,FEA_started=False,geometry_modified=False)
    encoded=json.dumps(data,ensure_ascii=False,allow_nan=False);roundtrip=json.loads(encoded)
    for mesh in roundtrip['meshes']:
        for record in mesh['regions']:check_record(record)
    require({p:sha(root/p)for p in before}==before and sha(plan_path)==plan_sha,'Input changed during export')
    output.mkdir();write(output/'figure-data.json',data);write(output/'export-receipt.json',dict(status='actual_geometry_only_exported',data_sha256=sha(output/'figure-data.json'),
        source_files_sha256=before,all_positions_roundtrip_bitexact=True,FEA_started=False,global_admission=False))

def render(data_path,expected,output):
    started=time.monotonic();source_sha=sha(__file__);data_path=Path(data_path);require(sha(data_path)==expected,'Figure data SHA differs')
    data=json.loads(data_path.read_text());require(data['schema']=='actual-local-T10-corner-edge-comparison-1','Wrong figure scope')
    require(len(data['regions'])==2 and [m['role']for m in data['meshes']]==['before','after'],'Two ordered real meshes/boxes required')
    output=Path(output);require(not output.exists()and not any(p.is_symlink()for p in [output,*output.parents]),'Fresh render required')
    os.environ['MPLBACKEND']='Agg'
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.backends.backend_pdf,matplotlib.backends.backend_svg
    import PIL
    from matplotlib.font_manager import findfont,FontProperties
    from matplotlib.collections import LineCollection
    from matplotlib.patches import Rectangle
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'text.color':'#183347','axes.labelcolor':'#536D7D',
        'svg.fonttype':'none','svg.hashsalt':'carrier-local-refinement-001','pdf.fonttype':42,'path.simplify':False})
    fig,axes=plt.subplots(2,4,figsize=(17,10.5),facecolor='#F8FAFC');fig.subplots_adjust(left=.055,right=.98,top=.775,bottom=.14,wspace=.28,hspace=.38)
    fig.text(.055,.95,'993 TURBO · MAILLAGE LOCAL RÉEL · DEUX BOÎTES FIXES',fontsize=11,color='#536D7D',weight='bold')
    fig.text(.055,.904,'Raffiner les éléments sans redessiner la géométrie',fontsize=23,weight='bold')
    fig.text(.055,.862,'Cibles fixes : moitié de la plus grande arête du tétraèdre du pic initial — pas moitié du maximum de chaque boîte.',fontsize=10.5)
    fig.text(.055,.839,f"{data['meshes'][0]['elements']:,} → {data['meshes'][1]['elements']:,} élémentsT10 · {data['adaptive_passes']} passes · critères géométriques PASS".replace(',',' '),fontsize=10,color='#087E8B')
    checks=[]
    for r,region in enumerate(data['regions']):
        records=[mesh['regions'][r]for mesh in data['meshes']];points=[check_record(record)for record in records]
        require(all(record['bounds_mm']==region['bounds_mm']and record['target_h_mm']==region['target_h_mm']for record in records)and
            records[1]['measured_h_mm']<=region['target_h_mm'],'The final measured target or fixed box differs')
        require(all(points[0][n]==points[1][n]for n in points[0].keys()&points[1].keys()),'A shared original node position changed')
        for view,projection in enumerate([(0,1),(0,2)]):
            lo,hi=region['bounds_mm'];allpoints=[p for mapping in points for p in mapping.values()]+[lo,hi]
            limits=[(min(p[d]for p in allpoints)-1,max(p[d]for p in allpoints)+1)for d in projection]
            for state,(record,mapping)in enumerate(zip(records,points)):
                ax=axes[r,view*2+state];color='#758895'if state==0 else'#087E8B'
                lines=[[[mapping[n][d]for d in projection]for n in pair]for pair in record['edges']]
                require(len(lines)==len(record['edges'])and all(limits[d][0]<=p[d]<=limits[d][1]for line in lines for p in line for d in range(2)),'A whole edge is clipped')
                ax.add_collection(LineCollection(lines,colors=color,linewidths=.45,rasterized=True))
                ax.add_patch(Rectangle((lo[projection[0]],lo[projection[1]]),hi[projection[0]]-lo[projection[0]],hi[projection[1]]-lo[projection[1]],
                    fill=False,edgecolor='#D47732',linestyle='--',linewidth=1.25))
                ax.set(xlim=limits[0],ylim=limits[1],xlabel='XYZ'[projection[0]]+' (mm)',ylabel='XYZ'[projection[1]]+' (mm)');ax.set_aspect('equal',adjustable='box')
                ax.set_title(('Avant — EF7'if state==0 else'Après — adaptatif002')+' · '+''.join('XYZ'[i]for i in projection),fontsize=10,loc='left',weight='bold')
                label=f"h BOÎTE = {record['measured_h_mm']:.6f} mm\nCible (h pic / 2) = {region['target_h_mm']:.6f} mm".replace('.',',')
                ax.text(.02,.02,label,transform=ax.transAxes,fontsize=8.8,
                    bbox=dict(facecolor='white',edgecolor='none',alpha=.92,pad=2))
                ax.tick_params(labelsize=8);ax.spines[['top','right']].set_visible(False)
                checks.append(dict(region=region['id'],role=data['meshes'][state]['role'],projection=list(projection),all_unique_edges_submitted=len(lines),
                    selected_cell_six_edge_incidences=record['centroid_selected_six_edge_incidences'],whole_inside_edge_incidences=record['whole_inside_edge_incidences'],
                    positions_sha256=record['positions_sha256'],xlim=limits[0],ylim=limits[1],aspect=ax.get_aspect(),edge_clipping=False))
                checks[-1].update(measured_scope_h_mm=record['measured_h_mm'],target_mm=region['target_h_mm'],initial_peak_tetrahedron_h_mm=region['measured_reference_h_mm'],
                    unrounded_target_attained=record['measured_h_mm']<=region['target_h_mm'],comparison_uses_unrounded_binary64=True)
        fig.text(.055,.817-r*.365,('Boîte1 — pic rigide EF7'if r==0 else'Boîte2 — pic K1000 EF7'),fontsize=11.5,weight='bold')
    fig.text(.055,.085,'Contours orange : boîtes de mesure fixes. h : maximum des arêtes entières des cellules à centroïde dans la boîte et des arêtes à deux extrémités dans la boîte.',fontsize=9.1,color='#536D7D')
    fig.text(.055,.055,'Arêtes de coin des vrais T10 à milieux droits, non déformés. Déduplication des seules paires d’IDs ; aucune arête raccourcie aux boîtes.',fontsize=9.1,color='#536D7D')
    fig.text(.055,.025,'Objectifs vérifiés aux valeurs non arrondies. Aucun raffinement global par2, nouveau calcul de contraintes ou résultat de convergence mécanique n’est revendiqué.',fontsize=9.1,color='#536D7D')
    font=findfont(FontProperties(family='DejaVu Sans'),fallback_to_default=False)
    paths={str(Path(sys.executable).resolve()),font}
    paths.update(str(Path(module.__file__).resolve())for name,module in list(sys.modules.items())if name.split('.')[0]in ['matplotlib','numpy','PIL']and getattr(module,'__file__',None)and Path(module.__file__).is_file())
    runtime={p:sha(p)for p in sorted(paths)}
    require(sha(data_path)==expected and sha(__file__)==source_sha,'Data/source changed before render output');output.mkdir()
    for ext in ['png','svg','pdf']:
        metadata={'Date':None,'Creator':'Actual local tetrahedron edges'}if ext=='svg'else({'CreationDate':None,'ModDate':None,'Creator':'Actual local tetrahedron edges'}if ext=='pdf'else{'Software':'Actual local tetrahedron edges'})
        fig.savefig(output/('carrier-raffinement-local.'+ext),dpi=180,metadata=metadata)
    plt.close(fig);require(sha(data_path)==expected and sha(__file__)==source_sha and all(sha(p)==h for p,h in runtime.items()),'Data/source/runtime changed during render')
    write(output/'render-receipt.json',dict(status='rendered_actual_local_edges_no_FEA',data_sha256=expected,checks=checks,wall_seconds=time.monotonic()-started,
        cwd=os.getcwd(),source_sha256=source_sha,runtime_files_sha256=runtime,runtime_versions=dict(python=sys.version.split()[0],matplotlib=matplotlib.__version__,Pillow=PIL.__version__),
        maxRSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,FEA_started=False,geometry_modified=False,outputs_sha256={p.name:sha(p)for p in output.iterdir()}))

if __name__=='__main__':
    for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
    seconds=150 if sys.argv[1]=='export'else 95;CPU=140 if sys.argv[1]=='export'else 90
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError(str(seconds)+'s geometry/figure budget')))
    signal.setitimer(signal.ITIMER_REAL,seconds);resource.setrlimit(resource.RLIMIT_CPU,(CPU,CPU+1))
    if sys.argv[1]=='export':export(sys.argv[2],sys.argv[3])
    elif sys.argv[1]=='render':render(sys.argv[2],sys.argv[3],sys.argv[4])
    elif sys.argv[1]=='build':
        output=Path(sys.argv[3]);require(not output.exists()and not any(p.is_symlink()for p in [output,*output.parents]),'Fresh build required')
        output.mkdir();export(sys.argv[2],output/'data');render(output/'data/figure-data.json',sha(output/'data/figure-data.json'),output/'render')
    else:raise SystemExit('usage: figure.py export PLAN FRESH_DATA | render DATA SHA FRESH_OUTPUT')
