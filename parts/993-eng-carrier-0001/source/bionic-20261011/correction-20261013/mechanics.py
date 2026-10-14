"""Bounded corrected-carrier load, torsion and fatigue-demand study.

Signed unit loads identify compliance. They are not a measured duty cycle, and
the bare-carrier eigenmodes exclude engine and body inertia.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

from corrected_cad import BASE, sha
sys.path.insert(0,str(BASE))
from simulate import solve, von_mises

CASES=('lateral','longitudinal','gravity','roll','pitch','yaw')
SCALES=np.array([2000.,2000.,2000.,850000.,850000.,850000.])


def run_one(folder,case,support=None,procedure='static'):
    name=case+(f'-spring-{support:g}' if support else '-rigid')+'-'+procedure
    path=folder/(name+'.json')
    if path.exists():
        result=json.loads(path.read_text())
        assert result['mesh_sha256']==sha(folder/'mesh.inp')
        assert result['input_sha256']==sha(folder/(name+'.inp'))
        return result
    return solve(folder,case,support,procedure)


def campaign(folder):
    for case in (*CASES,'combined','reverse_torque_combined'):
        run_one(folder,case)
    for stiffness in (1000,10000):
        run_one(folder,'combined',stiffness)
    for procedure in ('nonlinear','buckling','modal'):
        run_one(folder,'combined',procedure=procedure)


def assess(folder):
    data=[np.load(folder/f'{case}-rigid-static.npz',allow_pickle=False) for case in CASES]
    for d in data[1:]:
        assert np.array_equal(d['tags'],data[0]['tags'])
        assert np.array_equal(d['element_ids'],data[0]['element_ids'])
    unit=np.array([d['force']/scale for d,scale in zip(data,SCALES)])
    displacements=np.array([d['displacement'] for d in data])
    tensors=np.array([d['stress'] for d in data])
    compliance=np.einsum('inc,jnc->ij',unit,displacements)/SCALES[None,:]
    reciprocity=float(np.linalg.norm(compliance-compliance.T)/np.linalg.norm(compliance))
    assert reciprocity<1e-5
    assert np.linalg.eigvalsh((compliance+compliance.T)/2).min()>0
    combined=np.load(folder/'combined-rigid-static.npz',allow_pickle=False)
    reverse=np.load(folder/'reverse_torque_combined-rigid-static.npz',allow_pickle=False)
    errors={}
    for label,actual,sign in [('combined',combined,1),('reverse',reverse,-1)]:
        s=2*tensors[2]+sign*tensors[4]
        u=2*displacements[2]+sign*displacements[4]
        errors[label]={'stress_MPa':float(abs(s-actual['stress']).max()),
                       'displacement_mm':float(abs(u-actual['displacement']).max())}
        assert errors[label]['stress_MPa']<.02 and errors[label]['displacement_mm']<.0002
    cycles={}
    for label,amplitude,mean in [
        ('gravity_to_combined',(combined['stress']-tensors[2])/2,(combined['stress']+tensors[2])/2),
        ('gravity_reversing_850Nm_Y',tensors[4],tensors[2]),
        ('gravity_reversing_100Nm_X',tensors[3]*(100/850),tensors[2]),
    ]:
        vm=von_mises(amplitude);i=int(vm.argmax())
        cycles[label]={'equivalent_stress_amplitude_max_MPa':float(vm[i]),
                       'mean_stress_tensor_at_amplitude_peak_MPa':mean[i].tolist(),
                       'peak_element':int(data[0]['element_ids'][i]),
                       'mean_stress_correction_applied':False,'life_cycles':None}
    loads={}
    for path in sorted(folder.glob('*.json')):
        d=json.loads(path.read_text())
        if 'procedure' in d and 'input_sha256' in d:
            assert sha(folder/(d['name']+'.inp'))==d['input_sha256']
            loads[d['name']]=d
    r={'geometry_id':json.loads((folder.parent/'study.json').read_text())['design_id'],
       'mesh_sha256':sha(folder/'mesh.inp'),'loads':loads,
       'basis_order':['Fx','Fy','minus_Fz','Mx','My','Mz'],
       'basis_loads_N_or_Nmm':SCALES.tolist(),
       'compliance_mm_per_N_and_rad_per_Nmm':compliance.tolist(),
       'Maxwell_reciprocity_relative_error':reciprocity,'superposition_errors':errors,
       'axis_rotational_stiffness_Nm_per_degree':(np.pi/(180000*np.diag(compliance)[3:])).tolist(),
       'fatigue_demand':cycles,'fatigue_life_cycles':None,
       'qualification_limits':['Assumed bore loads and support stiffnesses; no bolt contact/preload',
                               'Pure moments are unit-load identification cases, not a measured vehicle spectrum',
                               'No qualified AM material allowable or S-N/strain-life curve',
                               'Bare-carrier modal study excludes engine and body inertia'],
       'static_strength_qualified':False,'fatigue_qualified':False,'manufacturing_authorized':False}
    (folder/'mechanics-summary.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'load_jobs':len(loads),'reciprocity':reciprocity,'fatigue_demand':cycles}))
    return r


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('folder',type=Path)
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    if args.run: campaign(args.folder)
    assess(args.folder)
