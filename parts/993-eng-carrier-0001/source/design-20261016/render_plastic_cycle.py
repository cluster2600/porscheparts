"""Plot retained Flat1 load/unload fields and a single fixed node history."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
import numpy as np

SOURCE=Path(__file__).resolve().parent
ROOT=SOURCE.parents[3]
sys.path.insert(0,str(SOURCE))
from analyze_plastic900 import fields
sys.path.insert(0,str(SOURCE.parent/'revalidation-20261016'))
from audit_energy import read_mesh,sha
spec=importlib.util.spec_from_file_location('carrier_field_projection',ROOT/'scripts/render_carrier_fields.py')
projection=importlib.util.module_from_spec(spec);spec.loader.exec_module(projection)


def render(folder,analysis_path,work_path,output):
    folder,output=Path(folder),Path(output)
    assert all(not output.with_suffix(suffix).exists() for suffix in ('.png','.svg','.json'))
    runtime=json.loads((folder/'runtime.json').read_text())
    analysis=json.loads(Path(analysis_path).read_text());work=json.loads(Path(work_path).read_text())
    assert runtime['status']=='executed' and analysis['unloading_complete'] and work['all_frames_pass']
    assert analysis['within_measured_pre_necking_domain']
    assert analysis['runtime_sha256']==work['runtime_sha256']==sha(folder/'runtime.json')
    name=runtime['name'];dat=folder/(name+'.dat')
    assert analysis['inputs_sha256'][name+'.dat']==work['solver_dat_sha256']==sha(dat)
    assert analysis['inputs_sha256']['mesh.inp']==runtime['mesh_sha256']==sha(folder/'mesh.inp')
    tags,xyz,eids,connectivity=read_mesh(folder/'mesh.inp')
    with np.load(folder/'mesh.npz',allow_pickle=False) as mesh:
        assert np.array_equal(tags,mesh['tags']) and np.allclose(xyz,mesh['xyz'],rtol=0,atol=1e-10)
        faces=mesh['faces']
    indices=np.searchsorted(tags,faces);assert np.array_equal(tags[indices],faces)
    data=fields(dat);times=sorted(data['displacements'])
    assert 1. in times and times[-1]==2.
    for values in data['displacements'].values():assert np.array_equal(values[:,0],tags)
    expected=np.column_stack((np.repeat(eids,4),np.tile(np.arange(1,5),len(eids))))
    plastic=data['equivalent plastic strain'][1.]
    assert np.array_equal(plastic[:,:2],expected)
    # Initial midsides are affine, so official Gauss coordinates are barycentric.
    a,b=.585410196624968,.138196601125011
    natural=np.array([[b,b,b],[a,b,b],[b,a,b],[b,b,a]])
    barycentric=np.column_stack((1-natural.sum(1),natural))
    gauss_xyz=np.einsum('qi,eij->eqj',barycentric,xyz[connectivity[:,:4]]).reshape(-1,3)
    active=plastic[:,2]>analysis['frames'][-1]['PEEQ_detection_threshold']
    full=data['displacements'][1.][:,1:];residual=data['displacements'][2.][:,1:]
    fixed_index=int(np.linalg.norm(full,axis=1).argmax());fixed_node=int(tags[fixed_index])
    residual_norm=np.linalg.norm(residual,axis=1);residual_index=int(residual_norm.argmax())
    factors=np.array([frame['load_factor'] for frame in analysis['frames']])
    assert np.array_equal(times,np.array([frame['total_time'] for frame in analysis['frames']]))
    fixed_u=np.array([data['displacements'][time][fixed_index,1:] for time in times])
    basis=projection.camera_basis(8,22);factor=20
    rest,_=projection.project(xyz,basis)
    figure=plt.figure(figsize=(15.5,12.5),facecolor='white')
    grid=figure.add_gridspec(3,2,height_ratios=[1,1,1.3],width_ratios=[1,.02],hspace=.50,wspace=.025)
    for row,points,values,title,label,vmax in (
        (0,xyz,None,'Plasticité à pleine charge — points d’intégration de la zone centrale','PEEQ aux points d’intégration (%)',100*plastic[:,2].max()),
        (1,xyz+factor*residual,residual_norm[indices].max(1),f'Après décharge : déplacement résiduel amplifié ×{factor}','|u résiduel| réel (mm)',residual_norm.max())):
        ax=figure.add_subplot(grid[row,0]);bar_ax=figure.add_subplot(grid[row,1])
        projected,depth=projection.project(points,basis)
        order=np.argsort(depth[indices].mean(1),kind='stable')
        norm=Normalize(0,float(vmax));cmap=plt.get_cmap('plasma' if row==0 else 'viridis')
        ax.add_collection(PolyCollection(rest[indices],facecolors='#dce1e6',edgecolors='none',rasterized=True))
        if row:
            ax.add_collection(PolyCollection(projected[indices][order],facecolors=cmap(norm(values[order])),edgecolors='none',rasterized=True))
        else:
            locations,_=projection.project(gauss_xyz,basis)
            visible=np.flatnonzero(active);visible=visible[np.argsort(plastic[visible,2],kind='stable')]
            ax.scatter(locations[visible,0],locations[visible,1],c=100*plastic[visible,2],s=9,cmap=cmap,norm=norm,linewidths=0,rasterized=True)
            peak=int(plastic[:,2].argmax())
            ax.scatter(*locations[peak],marker='*',s=110,facecolors='none',edgecolors='#151515',linewidths=.8)
        if row==0:
            chosen=rest[np.abs(xyz[:,0])<112];lower,upper=chosen.min(0),chosen.max(0)
        else:
            combined=np.vstack((rest,projected));lower,upper=combined.min(0),combined.max(0)
        ax.set(xlim=(lower[0]-5,upper[0]+5),ylim=(lower[1]-5,upper[1]+5),xlabel='U projeté (mm)',ylabel='V projeté (mm)',title=title)
        ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.12);ax.set_axisbelow(True)
        figure.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=bar_ax,label=label)
    lower=grid[2,0].subgridspec(1,2,width_ratios=[1,.9],wspace=.20)
    ax=figure.add_subplot(lower[0,0]);notes=figure.add_subplot(lower[0,1]);notes.axis('off')
    loading=np.array(times)<=1
    ax.plot(np.r_[0,-fixed_u[loading,2]],np.r_[0,factors[loading]],'o-',color='#136a9b',label='Chargement : sorties calculées',markersize=4)
    ax.plot(np.r_[-full[fixed_index,2],-fixed_u[~loading,2]],np.r_[1,factors[~loading]],'s-',color='#bb481f',label='Décharge : sorties calculées',markersize=4)
    ax.set(xlabel=f'−uZ au même nœud {fixed_node} (mm)',ylabel='Facteur λ des charges',title='Cycle au point fixe choisi à pleine charge')
    ax.grid(alpha=.2);ax.legend(fontsize=9)
    full_record=next(frame for frame in analysis['frames'] if frame['total_time']==1.)
    final=analysis['unloaded_residual']
    notes.text(0,1,
        f"Ti Grade 23 ELI · Z · détente 670 °C / 5 h\nLoi publiée Flat1 ; E = 106 000 MPa ; ν = 0,31\n\n"
        f"Pleine charge : |u|max = {full_record['displacement_max_mm']:.4f} mm\nPEEQmax = {100*full_record['PEEQ_max']:.3f} %\n"
        f"Après décharge : |u|max = {residual_norm.max():.4f} mm\nNœud {int(tags[residual_index])}, XYZ initial :\n{np.round(xyz[residual_index],3).tolist()} mm\n"
        f"Au point fixe : −uZ résiduel = {-residual[fixed_index,2]:.4f} mm\n\n"
        f"Fz = −4 000 λ N ; My = 850 000 λ N·mm\nAppuis élastiques conservés à la décharge.\n"
        f"Bilan indépendant : {max(frame['relative_to_gross_work'] for frame in work['frames']):.3g} (seuil 10⁻⁴)",
        va='top',fontsize=10,linespacing=1.15)
    figure.suptitle('Support 993 — plasticité et retour après décharge',fontsize=19,weight='bold',y=.985)
    figure.text(.5,.947,'ad12 · C3D10 / maillage 9 · NLGEOM · charges et appuis K1000 conservés',ha='center',fontsize=11)
    figure.text(.5,.018,
        'Plasticité : positions réelles des points d’intégration plastifiés, toutes profondeurs projetées ; aucune extrapolation nodale.\n'
        'Déplacement résiduel : normes nodales réelles, maximum des 3 sommets par face. Gris : géométrie au repos.\n'
        'La courbe relie uniquement les sorties du solveur ; le même nœud est suivi pendant tout le cycle.\n'
        f'Maillage {sha(folder/"mesh.inp")[:16]}… · DAT {sha(dat)[:16]}… · Projection orthographique 8° / 22°.',ha='center',fontsize=9.5)
    figure.subplots_adjust(left=.065,right=.93,bottom=.13,top=.90)
    output.parent.mkdir(parents=True,exist_ok=True)
    figure.savefig(output.with_suffix('.png'),dpi=180);figure.savefig(output.with_suffix('.svg'));plt.close(figure)
    receipt={'source_sha256':sha(__file__),'projection_helper_sha256':sha(ROOT/'scripts/render_carrier_fields.py'),
        'analysis_sha256':sha(analysis_path),'work_audit_sha256':sha(work_path),
        'mesh_sha256':sha(folder/'mesh.inp'),'mesh_npz_sha256':sha(folder/'mesh.npz'),'solver_dat_sha256':sha(dat),
        'fixed_node':fixed_node,'fixed_node_original_xyz_mm':xyz[fixed_index].tolist(),
        'times':times,'load_factors':factors.tolist(),'fixed_node_displacement_mm':fixed_u.tolist(),
        'residual_displacement_max_mm':float(residual_norm.max()),'residual_peak_node':int(tags[residual_index]),
        'residual_deformation_amplification':factor,'plasticity_field':'actual PEEQ at each active integration point, projected through all depths without occlusion or nodal extrapolation',
        'scope':'Published Grade23 ELI reference sensitivity. Residual displacement is computed at zero external force with the same springs retained.',
        'outputs_sha256':{suffix:sha(output.with_suffix(suffix)) for suffix in ('.png','.svg')}}
    output.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path);parser.add_argument('analysis',type=Path)
    parser.add_argument('work_audit',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();print(json.dumps(render(args.folder,args.analysis,args.work_audit,args.output)))
