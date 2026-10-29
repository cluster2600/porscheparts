"""Keep surface-resolution sensitivity separate from fixed-STEP mesh convergence."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--level',nargs=2,action='append',required=True,metavar=('MESH','MECHANICS'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    assert not a.output.exists() and len(a.level)==3
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    rows=[]; sources=[Path(__file__)]
    for mesh,mechanics in a.level:
        mesh,mechanics=Path(mesh),Path(mechanics)
        g=json.loads((mesh/'assessment.json').read_text());m=json.loads((mechanics/'assessment.json').read_text())
        assert m['status']=='explicit_periodic_T10_six_strain_checks_passed' and m['kind']=='gyroid'
        assert sorted(c['mode']for c in m['cases'])==list(range(6))
        assert g['mesh_size']==.05 and g['gyroid_threshold']==.6170021750539874
        assert abs(g['CAD_volume_mm3']-m['solid_fraction'])<1e-10
        assert all(sha(mesh/n)in m['source_sha256'].values()for n in ['cell.step','transport.npz'])
        for i in range(6):
            receipt=mechanics/f'case-{i}/actual-terminal.json';r=json.loads(receipt.read_text())
            assert r['actual_returncode']==0 and r['process_reaped'] and r['inputs_unchanged'] and r['solver_finished_marker']
            assert sha(mechanics/f'case-{i}/case/job.dat')==r['output_sha256']['job.dat']
            sources.append(receipt)
        sources += [mesh/'assessment.json',mesh/'cell.step',mesh/'transport.npz',mechanics/'assessment.json']
        rows.append(dict(resolution=g['resolution'],tetrahedra=g['tetrahedra'],solid_fraction=m['solid_fraction'],
                         minimum_stiffness_ratio=m['minimum_tensor_stiffness_ratio'],effective_C_MPa=m['effective_C_MPa'],dense_C_MPa=m['dense_C_MPa']))
    assert [r['resolution']for r in rows]==[24,32,48]
    assert all(np.array_equal(r['dense_C_MPa'],rows[0]['dense_C_MPa'])for r in rows)
    changes=[float(np.linalg.norm(np.array(b['effective_C_MPa'])-a['effective_C_MPa'])/np.linalg.norm(b['effective_C_MPa']))for a,b in zip(rows,rows[1:])]
    report=dict(status='coupled_surface_resolution_and_mesh_sensitivity_assessed',levels=rows,relative_tensor_changes=changes,
                both_observed_changes_below_two_percent=all(c<=.02 for c in changes),nominal_size_mm=.05,
                threshold_or_density_retuned=False,isolated_geometry_convergence_demonstrated=False,
                carrier_convergence_demonstrated=False,cellular_carrier_generated=False,
                source_sha256={str(f):sha(f)for f in sources})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    axes[0].plot([r['resolution']for r in rows],[r['minimum_stiffness_ratio']for r in rows],'o-',color='#286864')
    axes[0].set(xlabel='Implicit surface sampling resolution',ylabel='Minimum normalized stiffness eigenvalue',title='Same analytic threshold / different STEP geometries')
    axes[1].bar(['24 → 32','32 → 48'],100*np.array(changes),color='#286864')
    axes[1].axhline(2,color='#a74833',linestyle='--',label='2% limit');axes[1].legend()
    axes[1].set(ylabel='Full tensor change (%)',title='Separate geometry/mesh sensitivity')
    fig.suptitle('Explicit gyroid / surface-resolution sensitivity\nNominal h = 0.05; geometry and local mesh change together')
    a.output.mkdir();fig.savefig(a.output/'surface-sensitivity.png',dpi=160);plt.close(fig)
    report['figure_sha256']=sha(a.output/'surface-sensitivity.png')
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(changes=changes,both_below_two_percent=report['both_observed_changes_below_two_percent'])))


if __name__=='__main__':main()
