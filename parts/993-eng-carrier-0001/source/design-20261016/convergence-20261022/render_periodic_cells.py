"""Plot admitted periodic-cell tensors and their still-open spatial refinement."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--cases',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    rows=[];sources=[Path(__file__)]
    for case in a.cases:
        report=case/'assessment.json';contract=case/'contract.json';r=json.loads(report.read_text());c=json.loads(contract.read_text())
        if r['status']!='periodic_gyroid_six_strain_energy_checks_passed' or r['void_relative_stiffness']!=1e-6 or r['source_sha256']!=c['source_sha256']:raise ValueError('Complete fixed-contrast gyroid report and bound source required')
        C=np.array(r['effective_C_MPa']);dense=np.array(r['dense_C_MPa']);d,v=np.linalg.eigh(dense);inv=(v*(1/np.sqrt(d)))@v.T;eig=np.linalg.eigvalsh(inv@((C+C.T)/2)@inv)
        if not np.allclose(eig,r['normalized_stiffness_eigenvalues'],rtol=1e-12,atol=1e-12) or len(r['cases'])!=6 or any(x['relative_energy_residual']>1e-4 or x['pbc_max_mm']>1e-8 for x in r['cases']):raise ValueError('Tensor identity or original energy/periodicity limits refused')
        rows.append(r);sources +=[report,contract]
    if len(rows)<3 or any(y['resolution']<=x['resolution']for x,y in zip(rows,rows[1:])):raise ValueError('At least three increasing resolutions required')
    last=rows[-1];N=last['resolution'];threshold=last['gyroid_threshold'];x=2*np.pi*(np.arange(N)+.5)/N;X,Y=np.meshgrid(x,x);z=2*np.pi*(int(N/4)+.5)/N;solid=abs(np.sin(X)*np.cos(Y)+np.sin(Y)*np.cos(z)+np.sin(z)*np.cos(X))<=threshold
    changes=[float(np.linalg.norm(np.array(y['effective_C_MPa'])-np.array(x['effective_C_MPa']))/np.linalg.norm(y['effective_C_MPa']))for x,y in zip(rows,rows[1:])]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'figure.facecolor':'#f5f5f1','axes.facecolor':'#f5f5f1','axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(15,5.5),layout='constrained');axes[0].imshow(solid,origin='lower',extent=[0,1,0,1],cmap=matplotlib.colors.ListedColormap(['#e4e7e5','#237a69']),interpolation='nearest');axes[0].set_title(f'Actual voxel slice / N = {N}',loc='left',fontweight='bold');axes[0].set_xlabel('x / cell pitch');axes[0].set_ylabel('y / cell pitch')
    labels=[str(r['resolution'])for r in rows];axes[1].plot(labels,[r['solid_fraction']for r in rows],'o--',color='#636e75',label='Solid fraction');axes[1].plot(labels,[min(r['normalized_stiffness_eigenvalues'])for r in rows],'o-',color='#237a69',label='Minimum stiffness ratio');axes[1].plot(labels,[max(r['normalized_stiffness_eigenvalues'])for r in rows],'o-',color='#cc8436',label='Maximum stiffness ratio');axes[1].set_ylim(0,.5);axes[1].set_xlabel('Cells per periodic direction');axes[1].set_ylabel('Fraction of dense titanium');axes[1].set_title('Six-strain tensor / not density = stiffness',loc='left',fontweight='bold');axes[1].legend(fontsize=8)
    axes[2].plot(labels[1:],100*np.array(changes),'o-',color='#bd493e');axes[2].axhline(2,color='#323d43',linestyle='--',label='Fixed refinement target: 2%');axes[2].set_ylim(bottom=0);axes[2].set_xlabel('Refined cells per direction');axes[2].set_ylabel('Relative full tensor change [%]');axes[2].set_title('Spatial refinement remains under test',loc='left',fontweight='bold');axes[2].legend(fontsize=8)
    for ax in axes[1:]:ax.grid(axis='y',alpha=.13)
    fig.suptitle('993 CARRIER / PERIODIC GYROID RESEARCH',fontsize=18,fontweight='bold');fig.supxlabel('C3D8 full integration · six independent strains · periodic boundary equations · void modulus 10⁻⁶ of solid\nCell experiment only. No cellular carrier geometry, printable pitch or carrier strength claim.',fontsize=10)
    a.output.mkdir(parents=True,exist_ok=False);image=a.output/'periodic-cell-stiffness.png';fig.savefig(image,dpi=160);plt.close(fig);sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();(a.output/'figure-provenance.json').write_text(json.dumps(dict(figure_sha256=sha(image),source_sha256={str(x):sha(x)for x in sources},resolutions=[r['resolution']for r in rows],relative_tensor_changes=changes,unitcell_stiffness_converged=False,carrier_geometry_changed=False),indent=2)+'\n')


if __name__=='__main__':main()
