"""Re-evaluate a frozen geometric core selection against an admitted T10 field."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from assess_native_P2 import stress_energy


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__)
    for name in ['linear-preparation','quadratic-preparation','mechanics','budget','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=json.loads((a.mechanics/'assessment.json').read_text());b=json.loads((a.budget/'assessment.json').read_text());q=a.quadratic_preparation/'transport.npz';f=a.mechanics/'results.npz';selected=a.budget/'selected-cells.npz'
    if a.output.exists()or r['status']!='complete_linear_C3D10_results_equilibrium_and_energy_passed' or r['relative_energy_residual']>1e-4 or sha(f)!=r['output_sha256']or sha(q)not in r['source_sha256'].values()or b['cellular_geometry_generated']:raise ValueError('Fresh frozen selection and accepted complete T10 field required')
    with np.load(a.linear_preparation/'transport.npz')as d:lv=d['vertices'].copy();lc=d['tetrahedra'].copy()
    with np.load(q)as d:v=d['vertices'].copy();c=d['tetrahedra'].copy()
    with np.load(selected)as d:ids=d['indices'].copy();old_centres=d['centres'].copy();old_volumes=d['volumes_mm3'].copy()
    if len(ids)!=b['selected_cells']or c.shape!=(len(lc),10)or not np.array_equal(c[:,:4],lc)or not np.array_equal(v[:len(lv)],lv)or len(np.unique(ids))!=len(ids)or not np.all((ids>=0)&(ids<len(c))):raise ValueError('Complete matching linear/quadratic corner rosters and unique selected cells required')
    if not np.array_equal(lv[lc[ids]].mean(1),old_centres):raise ValueError('Frozen selected centroid identity differs')
    with np.load(f)as d:stress=d['stress'].copy()
    if stress.shape!=(len(c),4,6)or not np.isfinite(stress).all():raise ValueError('Complete finite T10 integration roster required')
    material=json.loads((a.quadratic_preparation/'assessment.json').read_text())['material'];energy,volume=stress_energy(v,c[ids],stress[ids],material['E_MPa'],material['nu'],np)
    if not np.isclose(old_volumes.sum(),b['selected_analysis_volume_mm3'],rtol=1e-12,atol=1e-9)or not 0<energy<r['independent_stress_compliance_energy_Nmm']:raise ValueError('Frozen budget volume or positive subset energy refused')
    report=dict(status='frozen_core_T10_baseline_energy_audited',selected_cells=len(ids),selected_T10_volume_mm3=volume,selected_T10_energy_Nmm=energy,original_T10_energy_fraction_in_selected_cells=energy/r['independent_stress_compliance_energy_Nmm'],T4_screen_conditional_mass_saving_kg=b['conditional_mass_reduction_kg'],selection_unchanged=True,cellular_geometry_generated=False,changed_geometry_stiffness_predicted=False,source_sha256={str(x):sha(x)for x in [a.linear_preparation/'transport.npz',q,f,a.mechanics/'assessment.json',a.budget/'assessment.json',selected,Path(__file__),Path(__file__).with_name('assess_native_P2.py')]});a.output.mkdir();(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
