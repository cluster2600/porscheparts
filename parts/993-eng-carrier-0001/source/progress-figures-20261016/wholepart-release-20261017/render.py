"""Render the real four native64 fields; no section worker, solve or remeshing."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import sys
import time

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_module(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def main(output):
    started=time.monotonic();output=Path(output).absolute()
    if output.exists()or output.is_symlink()or any(p.is_symlink()for p in output.parents):raise FileExistsError('Fresh output, without symlinks, required')
    output=output.resolve()
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in()).throw(TimeoutError('60-second rendering budget')))
    signal.setitimer(signal.ITIMER_REAL,60)
    inputs=HERE/'inputs.json';manifest=json.loads(inputs.read_text());pins=manifest['files_sha256']
    if any(Path(n).name!=n or sha(HERE/n)!=h for n,h in pins.items()):raise ValueError('Local figure source/input differs')
    frozen={**{n:sha(HERE/n)for n in pins},'inputs.json':sha(inputs)}
    evidence=json.loads((HERE/'evidence.json').read_text())
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    from matplotlib import font_manager
    import numpy as np
    import vispy
    versions=dict(python=sys.version.split()[0],numpy=np.__version__,matplotlib=matplotlib.__version__,vispy=vispy.__version__)
    if versions!=manifest['runtime_versions']:raise ValueError('Historical figure runtime versions differ')
    with np.load(HERE/'plot-data.npz',allow_pickle=False)as z:
        xyz=z['xyz'].copy();faces=z['faces'].copy();u=z['u'].copy();tags=z['tags'].copy();times=z['times'].copy()
    if (xyz.shape!=(103534,3)or faces.shape!=(31408,3)or u.shape!=(4,103534,3)or not np.array_equal(times,[1.,2.,3.,4.])or
        len(set(tags))!=103534 or not np.isfinite(xyz).all()or not np.isfinite(u).all()or faces.min()<0 or faces.max()>=len(xyz)):
        raise ValueError('Complete actual surface and four fields required')
    if sha(HERE/'plot-data.npz')!=evidence['plot_data_sha256']or not evidence['summary']['uniform_control']['passed']:
        raise ValueError('Native numerical proof differs')
    magnitudes=np.linalg.norm(u,axis=2)*1000.;maxima=magnitudes.max(axis=1)
    if not np.allclose(maxima,np.array(evidence['maximum_u_mm'])*1000,rtol=1e-13,atol=0):raise ValueError('Native field extrema differ')
    unlit=load_module(HERE/'raster_unlit.py','_frozen_carrier_unlit');ghost=load_module(HERE/'raster_ghost.py','_frozen_carrier_ghost')
    amp=500.;norm=Normalize(0.,float(maxima[3]));palette=plt.get_cmap('viridis')
    colors=palette(norm(magnitudes[3][faces].mean(axis=1)))
    # Every original provided surface facet is drawn, retaining its original IDs.
    image_real=unlit.raster(xyz,faces,colors,30.,0.)
    combined=np.vstack([xyz,xyz+amp*u[3]])
    both_faces=np.vstack([faces,faces+len(xyz)])
    grey=np.tile(matplotlib.colors.to_rgba('#80909a'),(len(faces),1))
    image_amplified=ghost.raster(combined,both_faces,np.vstack([grey,colors]),30.,0.,part_faces=len(faces))
    font=font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans'),fallback_to_default=False)
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'text.color':'#163247','svg.fonttype':'none',
        'svg.hashsalt':'carrier-wholepart-native64-release-20261017','pdf.fonttype':42,'path.simplify':False})
    fig=plt.figure(figsize=(15.6,11.5),facecolor='#f5f7f9')
    fig.text(.055,.955,'PIÈCE ENTIÈRE · RETRAIT IMPOSÉ ET DÉBRIDAGE',fontsize=23,weight='bold')
    fig.text(.055,.923,'103 534 nœuds · 54 149 C3D10 · quatre champs natifs en double précision',fontsize=12,color='#435e6f')
    fig.text(.055,.885,'Sensibilité : champ quadratique + bridage provisoire — pas une prévision LPBF',fontsize=12.5,weight='bold',color='#9a5a19')
    ax=fig.add_axes([.045,.535,.83,.30]);ax.imshow(image_real);ax.axis('off')
    ax.set_title('Après libération · forme non amplifiée, couleur |u| en µm',loc='left',fontsize=12.5,pad=8)
    cax=fig.add_axes([.903,.574,.015,.205]);bar=fig.colorbar(ScalarMappable(norm=norm,cmap=palette),cax=cax,ticks=[0,20,40,float(maxima[3])])
    bar.ax.set_yticklabels(['0','20','40','58,09']);bar.set_label('|u| [µm]',labelpad=9);bar.outline.set_visible(False)
    ax=fig.add_axes([.045,.28,.83,.245]);ax.imshow(image_amplified);ax.axis('off')
    ax.set_title('Déformée visuelle ×500 · référence initiale gris transparent',loc='left',fontsize=12.5,pad=8)
    fig.text(.90,.379,'×500',fontsize=24,weight='bold',color='#316881')
    fig.text(.90,.348,'forme seule',fontsize=9,color='#536f7e')
    tableax=fig.add_axes([.057,.105,.39,.15]);tableax.axis('off')
    labels=['Zéro','Uniforme libre','Quadratique bridé','Quadratique libéré']
    rows=[[label,('%0.3f'%value).replace('.',',')]for label,value in zip(labels,maxima)]
    table=tableax.table(cellText=rows,colLabels=['État calculé','Max. |u| [µm]'],cellLoc='left',colLoc='left',bbox=[0,0,1,1],colWidths=[.68,.32])
    table.auto_set_font_size(False);table.set_fontsize(10.5)
    for (r,c),cell in table.get_celld().items():
        cell.set_edgecolor('#d5dfe5');cell.set_linewidth(.6);cell.set_facecolor('#e7eef2'if r==0 else'#f5f7f9')
        if r==0:cell.set_text_props(weight='bold')
    summary=evidence['summary'];released=summary['release'];uniform=summary['uniform_control']
    metric=[('Débridage max.',released['release_increment_max_u_mm']*1000,'µm'),
            ('Variation entraxe principal',released['center_distances']['end0__end1']['change_mm']*1000,'µm')]
    for y,(label,value,unit)in zip([.233,.20],metric):
        fig.text(.495,y,label,fontsize=11,color='#435e6f');fig.text(.795,y,('%+.3f'%value).replace('.',',')+' '+unit,fontsize=15,weight='bold',ha='right')
    fig.text(.495,.166,'Masse EF : 1,261484 kg · Δm = 0 (ρ₀V₀)',fontsize=11.5,weight='bold')
    fig.text(.495,.133,'Contrôle uniforme : erreur ε = 1,24×10⁻¹⁴ < 10⁻⁷',fontsize=10.8,color='#216e52')
    fig.text(.495,.105,'Zéro exact · force/moment et detF vérifiés sur les quatre états',fontsize=9.3,color='#435e6f')
    fig.text(.055,.064,'ε*(Z) = −10⁻⁴ ((Z−Zmin)/H)² I · plan inférieur provisoirement fixé, puis six jauges de corps rigide.',fontsize=9.7,color='#536f7e')
    fig.text(.055,.040,'31 408 facettes sources conservées ; couleur moyenne nodale par facette. Aucun dépôt, support physique ou cycle thermique simulé.',fontsize=9.2,color='#536f7e')
    output.mkdir(exist_ok=False);exports={}
    for suffix in ('png','svg','pdf'):
        target=output/('carrier-wholepart-release-native64.'+suffix);metadata={'Creator':'Carrier native64 numerical evidence renderer'}
        if suffix=='svg':metadata['Date']=None
        if suffix=='pdf':metadata.update(CreationDate=None,ModDate=None)
        fig.savefig(target,dpi=180,facecolor=fig.get_facecolor(),metadata=metadata)
        exports[target.name]=sha(target)
    plt.close(fig)
    if any(sha(HERE/n)!=h for n,h in frozen.items()):raise ValueError('Source/input changed while rendering')
    receipt=dict(status='rendered_real_wholepart_four_native64_fields',source_inputs_sha256=frozen,exports_sha256=exports,
        runtime_versions=versions,font_sha256=sha(Path(font)),faces_drawn=31408,native_nodes=103534,all_four_fields_retained=True,
        visual_amplification=amp,amplification_does_not_change_color_values=True,global_node_maxima_um=maxima.tolist(),
        cameras=[dict(elevation=30.,azimuth=0.)]*2,original_geometry_not_subdivided=True,new_solver_run=False,section_workers=0,
        numerical_pilot_passed=True,physical_print_prediction=False,real_print_supports_simulated=False,global_admission=False,
        seconds=time.monotonic()-started)
    with(output/'receipt.json').open('x')as f:json.dump(receipt,f,indent=2,allow_nan=False);f.write('\n')
    signal.setitimer(signal.ITIMER_REAL,0)
    print(json.dumps(dict(status=receipt['status'],seconds=receipt['seconds'],exports_sha256=exports)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);args=parser.parse_args();main(args.output)
