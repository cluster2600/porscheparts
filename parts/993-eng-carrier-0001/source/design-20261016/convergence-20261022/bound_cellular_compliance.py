"""Bound force-controlled FE compliance for a hypothetical constitutive substitution."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def compliance_bounds(energy_fraction, eta_min, eta_max):
    if not 0<=energy_fraction<=1 or not 0<eta_min<=eta_max<=1:
        raise ValueError('Valid baseline energy fraction and positive softening eigenvalues required')
    return 1/(1-(1-eta_max)*energy_fraction),1+(1/eta_min-1)*energy_fraction


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--material',type=Path,required=True);p.add_argument('--skin-sweep',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    material=json.loads(a.material.read_text());sweep=json.loads(a.skin_sweep.read_text());C=np.array(material['effective_C_MPa']);dense=np.array(material['dense_C_MPa'])
    if C.shape!=(6,6) or dense.shape!=(6,6) or not np.isfinite(C).all() or np.linalg.norm(C-C.T)>1e-4*np.linalg.norm(C):raise ValueError('Finite symmetric six-strain tensor required')
    E=107000.;nu=.31;G=E/(2*(1+nu));lam=E*nu/((1+nu)*(1-2*nu));expected=np.zeros((6,6));expected[:3,:3]=lam;expected[np.arange(3),np.arange(3)]+=2*G;expected[3:,3:]=np.eye(3)*G
    if not np.allclose(dense,expected,rtol=1e-12,atol=1e-8) or not 0<material['solid_fraction']<1:raise ValueError('Same dense material as the admitted carrier baseline and a cellular solid fraction required')
    d,v=np.linalg.eigh(dense)
    if d.min()<=0:raise ValueError('Dense tensor must be positive definite')
    inv=(v*(1/np.sqrt(d)))@v.T;eigen=np.linalg.eigvalsh(inv@((C+C.T)/2)@inv);lo=float(eigen.min());hi=float(eigen.max());compliance_bounds(0,lo,hi)
    rows=[]
    for row in sweep['rows']:
        if not row['volume_mm3']>0 or not row['skin_mm']>0 or row['selected_cells']<=0:raise ValueError('Positive selected region required')
        lower,upper=compliance_bounds(row['T10_baseline_energy_fraction'],lo,hi)
        rows.append(dict(skin_mm=row['skin_mm'],selected_cells=row['selected_cells'],baseline_core_energy_fraction=row['T10_baseline_energy_fraction'],conditional_saving_at_actual_cell_density_kg=row['volume_mm3']*4420e-9*(1-material['solid_fraction']),compliance_ratio_lower_bound=lower,compliance_ratio_upper_bound=upper))
    report=dict(status='conditional_constitutive_substitution_compliance_bounds',material_resolution=material['resolution'],material_solid_fraction=material['solid_fraction'],eta_min=lo,eta_max=hi,rows=rows,fixed_external_force_vector=True,homogeneous_zero_support_displacements=True,unchanged_mesh_and_selected_element_regions=True,homogenized_uniform_constitutive_substitution_only=True,finite_cell_connections_modelled=False,maximum_displacement_bounded=False,stress_or_strength_bounded=False,carrier_geometry_changed=False,cellular_part_generated=False,carrier_convergence_demonstrated=False,source_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in [a.material,a.skin_sweep,Path(__file__)]})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'figure.facecolor':'#f5f5f1','axes.facecolor':'#f5f5f1','axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(10,6),layout='constrained');x=[1000*r['conditional_saving_at_actual_cell_density_kg']for r in rows];lower=[100*(r['compliance_ratio_lower_bound']-1)for r in rows];upper=[100*(r['compliance_ratio_upper_bound']-1)for r in rows]
    ax.fill_between(x,lower,upper,color='#237a69',alpha=.2,label='Variational compliance envelope');ax.plot(x,lower,'o-',color='#237a69');ax.plot(x,upper,'o-',color='#237a69')
    for i,r in enumerate(rows):ax.annotate(f"{r['skin_mm']:g} mm skin",(x[i],upper[i]),xytext=(4,5),textcoords='offset points',fontsize=9)
    ax.set_xlabel('Conditional mass saving at computed cell density [g]');ax.set_ylabel('Force-controlled compliance increase [%]');ax.set_ylim(bottom=0);ax.grid(axis='y',alpha=.15);ax.legend();fig.suptitle('993 CARRIER / CONDITIONAL CELLULAR STIFFNESS BOUNDS',fontweight='bold');fig.supxlabel('Uniform homogenized material in selected FE cells only / same force vector and zero restraints\nNo finite-cell connections, peak displacement, local stress, strength or printable geometry result.',fontsize=9)
    a.output.mkdir();image=a.output/'conditional-compliance-bounds.png';fig.savefig(image,dpi=160);plt.close(fig);report['figure_sha256']=hashlib.sha256(image.read_bytes()).hexdigest();(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
