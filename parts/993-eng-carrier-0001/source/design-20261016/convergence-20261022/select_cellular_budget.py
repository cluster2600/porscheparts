"""Use validated CUDA distances to budget a protected low-energy analysis core."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def eligible_core(distance,radii,probe_error,surface_error,allowed,skin):
    return (distance-.0001-surface_error-probe_error-radii>=skin)&allowed


def main():
    p=argparse.ArgumentParser(__doc__)
    for name in ['prepared','cpu','cuda','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh screen result required')
    oracle=a.prepared/'oracle-report.json';metadata=json.loads(oracle.read_text());parameters=metadata['parameters'];reports=[json.loads((path/'report.json').read_text())for path in [a.cpu,a.cuda]]
    for report in reports:
        if report['status']!='passed'or report['fixed_absolute_error_limit_mm']!=.0001 or report['queries']!=metadata['queries']or sha(oracle)not in report['source_sha256'].values()or metadata['bundle_sha256']not in report['source_sha256'].values():raise ValueError('Complete fixed-limit oracle validation required')
    if not reports[1]['gpu_validated']or reports[1]['actual_device']!='cuda:0'or reports[0]['source_sha256']!=reports[1]['source_sha256']:raise ValueError('Paired actual CUDA validation required')
    source=a.prepared/'screen-fields.npz';distances=a.cuda/'distances.npz'
    if sha(source)!=metadata['screen_fields_sha256']or sha(distances)!=reports[1]['output_distances_sha256']:raise ValueError('Complete screen input identities differ')
    with np.load(source,allow_pickle=False)as data:fields={key:data[key].copy()for key in data.files}
    with np.load(distances,allow_pickle=False)as data:distance=data['distances_mm'].astype(np.float64);hits=data['hits'].copy()
    if len(distance)!=len(fields['radii'])or not np.all(hits==1):raise ValueError('Complete query roster required')
    eligible=eligible_core(distance,fields['radii'],fields['probe_transport_L1_mm'],metadata['surface_float32_transport_L1_bound_mm'],fields['interface_allowed'],parameters['skin_mm']);volume=fields['volumes_mm3'];energy=fields['energy_Nmm'];ids=np.flatnonzero(eligible);ids=ids[np.argsort(energy[ids]/volume[ids],kind='stable')];selected=ids[np.cumsum(volume[ids])<=parameters['maximum_selected_volume_fraction']*volume.sum()]
    rho=metadata['material']['density_tonne_mm3']*1000;selected_volume=float(volume[selected].sum());saved=(1-parameters['relative_density_scenario'])*selected_volume*rho;mass=float(volume.sum())*rho
    result=dict(status='protected_analysis_core_budget_screen_completed',parameters=parameters,analysis_cells=len(volume),eligible_cells=int(eligible.sum()),selected_cells=len(selected),eligible_analysis_volume_mm3=float(volume[eligible].sum()),selected_analysis_volume_mm3=selected_volume,selected_volume_fraction=selected_volume/float(volume.sum()),original_energy_fraction_in_selected_cells=float(energy[selected].sum()/energy.sum()),analysis_proxy_mass_kg=mass,conditional_mass_reduction_kg=saved,conditional_remaining_analysis_proxy_mass_kg=mass-saved,reference_geometry_changed=False,cellular_geometry_generated=False,cellular_strength_validated=False,exact_arithmetic_certificate=False,scope='Whole-cell numerical clearance and energy ranking on the auxiliary analysis volume; relative-density arithmetic is conditional, not a new part mass or stiffness prediction',source_sha256={str(path):sha(path)for path in [oracle,source,distances,a.cpu/'report.json',a.cuda/'report.json',Path(__file__)]})
    a.output.mkdir(parents=True);np.savez_compressed(a.output/'selected-cells.npz',indices=selected,centres=fields['centres'][selected],volumes_mm3=volume[selected]);(a.output/'assessment.json').write_text(json.dumps(result,indent=2)+'\n')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'figure.facecolor':'#f5f5f1','axes.facecolor':'#f5f5f1','axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,1,figsize=(14,7),layout='constrained');points=fields['centres'];chosen=points[selected]
    for ax,coordinates,title in zip(axes,[[0,1],[0,2]],['Plan view / protected interior candidates','Side view / existing thin arms remain outside the core screen']):
        ax.scatter(points[:,coordinates[0]],points[:,coordinates[1]],s=.15,c='#a0aaa6',alpha=.15,rasterized=True);ax.scatter(chosen[:,coordinates[0]],chosen[:,coordinates[1]],s=.4,c='#087caa',alpha=.6,rasterized=True);ax.set_aspect('equal');ax.set_xlabel('X [mm]');ax.set_ylabel('Y [mm]'if coordinates[1]==1 else'Z [mm]');ax.set_title(title,loc='left',fontweight='bold');ax.grid(alpha=.12)
    fig.suptitle('993 R2 / CELLULAR REPLACEMENT BUDGET SCREEN',fontsize=18,fontweight='bold');fig.supxlabel(f"Blue: {selected_volume/1000:.2f} cm³ analysis core · conditional saving at relative density {parameters['relative_density_scenario']:.2f}: {saved*1000:.1f} g\nAll analysis-cell centroids shown. No lattice geometry or changed-geometry resistance has been calculated.",fontsize=11);image=a.output/'carrier-cellular-budget-screen.png';fig.savefig(image,dpi=160);plt.close(fig)
    (a.output/'figure-provenance.json').write_text(json.dumps({'figure_sha256':sha(image),'assessment_sha256':sha(a.output/'assessment.json'),'source_sha256':sha(Path(__file__))},indent=2)+'\n');print(json.dumps({key:result[key]for key in ['status','selected_cells','conditional_mass_reduction_kg','original_energy_fraction_in_selected_cells']}))


if __name__=='__main__':main()
