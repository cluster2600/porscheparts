"""Admit the two collected N64 tensors under the original C3D8 refinement criteria."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np


def sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()


def load_case(folder,floor):
    r=json.loads((folder/'assessment.json').read_text());audit=json.loads((folder/'saved-field-audit.json').read_text());terminal=json.loads((folder.parent/(folder.name+'-terminal.json')).read_text());collection=json.loads((folder.parent/(folder.name+'-collection.json')).read_text())
    assert terminal['actual_returncode']==0 and terminal['process_reaped']and terminal['runner_unchanged']and collection['all_case_file_hashes_verified']
    assert r['status']=='independent_operator_energy_checks_passed'and r['resolution']==64 and r['void_relative_stiffness']==floor and len(r['relative_energy_residuals'])==6 and max(r['relative_energy_residuals'])<=1e-4 and r['periodic_corrector_error']<=1e-8 and r['relative_antisymmetry']<=1e-4
    assert audit['status']=='complete_saved_field_rosters_and_boundary_work_passed'and audit['actual_cases']==6 and audit['stress_points_per_case']==8*64**3 and len(audit['cases'])==6 and max(x['relative_work_error']for x in audit['cases'])<=1e-4
    assert r['runner_sha256']==sha(Path(__file__).parent/'run_shared.py')
    for name,expected in audit['file_sha256'].items():assert Path(name).name==name and sha(folder/name)==expected
    C=np.array(r['effective_C_MPa']);dense=np.array(r['dense_C_MPa']);d,v=np.linalg.eigh(dense);inv=(v*(1/np.sqrt(d)))@v.T;eigs=np.linalg.eigvalsh(inv@((C+C.T)/2)@inv)
    assert np.allclose(eigs,r['normalized_stiffness_eigenvalues'],rtol=1e-12,atol=1e-12) and eigs.min()>0 and eigs.max()<=r['solid_fraction']+(1-r['solid_fraction'])*floor+1e-4
    return r


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--soft-void-case',type=Path,required=True);p.add_argument('--stiff-void-case',type=Path,required=True);p.add_argument('--previous-case',type=Path,required=True);p.add_argument('--previous-progress',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
    soft=load_case(a.soft_void_case,1e-6);stiff=load_case(a.stiff_void_case,1e-4);prior=json.loads(a.previous_case.read_text());history=json.loads(a.previous_progress.read_text())
    assert prior['status']=='periodic_gyroid_six_strain_energy_checks_passed'and prior['resolution']==48 and prior['void_relative_stiffness']==1e-6 and len(prior['cases'])==6 and all(x['relative_energy_residual']<=1e-4 and x['pbc_max_mm']<=1e-8 for x in prior['cases'])
    assert history[-1]['resolution']==48 and history[-1]['solid_fraction']==prior['solid_fraction']and history[-1]['minimum_tensor_stiffness_ratio']==prior['minimum_tensor_stiffness_ratio']
    C=np.array(soft['effective_C_MPa']);dense=np.array(soft['dense_C_MPa']);assert np.array_equal(dense,np.array(stiff['dense_C_MPa']))and np.allclose(dense,prior['dense_C_MPa'],rtol=1e-12,atol=1e-8)and soft['solid_fraction']==stiff['solid_fraction']
    change=float(np.linalg.norm(C-np.array(prior['effective_C_MPa']))/np.linalg.norm(C));void=float(np.linalg.norm(C-np.array(stiff['effective_C_MPa']))/np.linalg.norm(C));last=dict(resolution=64,solid_fraction=soft['solid_fraction'],minimum_tensor_stiffness_ratio=soft['minimum_tensor_stiffness_ratio'],relative_tensor_resolution_change=change,resolution_change_passed=change<=.02,relative_void_floor_tensor_change=void,void_floor_test_passed=void<=.01);history.append(last)
    converged=all(x['resolution_change_passed']and x['void_floor_test_passed']for x in history[-2:])
    sources=[a.previous_case,a.previous_progress,Path(__file__),Path(__file__).parent/'run_shared.py']+[folder/name for folder in [a.soft_void_case,a.stiff_void_case] for name in ['assessment.json','saved-field-audit.json']]
    report=dict(status='collected_N64_C3D8_tensor_refinement_assessed',required_successive_refinement_comparisons=2,relative_refinement_limit=.02,relative_void_floor_limit=.01,rows=history,unitcell_stiffness_converged=converged,carrier_convergence_demonstrated=False,cellular_part_generated=False,all_twelve_actual_N64_strain_fields_collected=True,source_sha256={str(x):sha(x)for x in sources})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'figure.facecolor':'#f5f5f1','axes.facecolor':'#f5f5f1','axes.spines.top':False,'axes.spines.right':False});fig,axes=plt.subplots(1,2,figsize=(12,5.5),layout='constrained');labels=[str(x['resolution'])for x in history]
    axes[0].plot(labels,[x['solid_fraction']for x in history],'o--',color='#636e75',label='Actual solid fraction');axes[0].plot(labels,[x['minimum_tensor_stiffness_ratio']for x in history],'o-',color='#237a69',label='Minimum stiffness ratio');axes[0].set_ylim(0,.5);axes[0].set_ylabel('Fraction of dense titanium');axes[0].set_title('Same periodic C3D8 cell / five grid levels',loc='left',fontweight='bold');axes[0].legend()
    changes=[100*x['relative_tensor_resolution_change']for x in history[1:]];axes[1].plot(labels[1:],changes,'o-',color='#bd493f');axes[1].axhline(2,color='#323d43',linestyle='--',label='Unchanged 2% refinement condition');axes[1].set_ylim(bottom=0);axes[1].set_ylabel('Full tensor change [%]');axes[1].set_title('Two successive passes' if converged else 'Cell refinement remains open',loc='left',fontweight='bold');axes[1].legend()
    for ax in axes:ax.set_xlabel('Cells per periodic direction');ax.grid(axis='y',alpha=.13)
    fig.suptitle('993 CARRIER / ACTUAL N64 CELL REFINEMENT',fontweight='bold',fontsize=16);fig.supxlabel('Six actual strains at each void floor / independent field, boundary work and energy checks\nCell stiffness only. Carrier stress convergence and explicit cellular geometry remain separate.',fontsize=9)
    a.output.mkdir();image=a.output/'periodic-cell-N64-refinement.png';fig.savefig(image,dpi=160);plt.close(fig);report['figure_sha256']=sha(image);(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
