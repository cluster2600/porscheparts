"""Reproduce and assess the frozen V5 load campaign, with tensor superposition."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np

from simulate import eigenvalues, elements, execute, solve, von_mises

CASES = ('lateral', 'longitudinal', 'gravity', 'torsion_x_100Nm',
         'torque_y_850Nm', 'torsion_z_100Nm')
SCALES = np.array([2000, 2000, -2000, 100000, 850000, 100000])


def campaign(folder):
    for k in (None, 1000, 10000):
        for case in (*CASES, 'combined'): solve(folder, case, support=k)
    for k in (None, 1000):
        for procedure in ('modal', 'buckling', 'nonlinear'):
            solve(folder, 'combined', support=k, procedure=procedure)


def engine_mass_modes(folder, fixture):
    """200 kg distributed equally between bores; engine inertia/CG are unmeasured."""
    data = np.load(folder/'mesh.npz'); lines = []; eid = 1000000; total = 0.
    assert max(elements(folder/'mesh.inp')) < eid
    for i in range(4):
        nodes = data[f'bolt{i}']; mass = .05/len(nodes)
        lines += [f'*ELEMENT,TYPE=MASS,ELSET=ENGINE{i}']
        for node in nodes: lines.append(f'{eid},{node}'); eid += 1; total += mass
        lines += [f'*MASS,ELSET=ENGINE{i}', str(mass)]
    assert abs(total-.2) < 1e-12
    original = (folder/f'combined-{fixture}-modal.inp').read_text()
    assert original.count('*STEP') == 1
    name = f'engine-200kg-{fixture}-modal'; assert not (folder/(name+'.inp')).exists()
    (folder/(name+'.inp')).write_text(original.replace('*STEP', '\n'.join(lines)+'\n*STEP', 1))
    seconds = execute(folder, name)
    frequency = eigenvalues((folder/(name+'.dat')).read_text(), 'modal')[:, 3]
    result = {'name': name, 'seconds': seconds, 'added_mass_kg': total*1000,
              'frequencies_Hz': frequency.tolist(), 'engine_CG_and_rotational_inertia_measured': False,
              'scope': 'Distributed mass sensitivity only; not a coupled powertrain modal validation'}
    (folder/(name+'.json')).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


def assess(folder):
    report = {'geometry': 'Frozen V5, no shape changes', 'fixtures': {},
              'assumption': 'Independent signed axis limits are an envelope, not a measured event spectrum',
              'reference_yield_MPa': 955, 'assumed_yield_factor': 1.5,
              'physical_acceptance': False, 'fatigue_life_cycles': None}
    for fixture in ('rigid', 'spring-1000', 'spring-10000'):
        data = [np.load(folder/f'{case}-{fixture}-static.npz') for case in CASES]
        unit = np.array([d['force']/s for d, s in zip(data, SCALES)])
        u = np.array([d['displacement'] for d in data])
        tensors = np.array([d['stress'] for d in data])
        C = np.einsum('inc,jnc->ij', unit, u)/SCALES[None, :]
        reciprocity = float(np.linalg.norm(C-C.T)/np.linalg.norm(C))
        assert reciprocity < 1e-5 and np.linalg.eigvalsh((C+C.T)/2).min() > 0
        combined = np.load(folder/f'combined-{fixture}-static.npz')
        stress_error = float(abs(2*tensors[2]+tensors[4]-combined['stress']).max())
        displacement_error = float(abs(2*u[2]+u[4]-combined['displacement']).max())
        assert stress_error < .01 and displacement_error < .0001
        worst = None
        for signs in itertools.product((-1, 1), repeat=5):
            coeff = np.array([signs[0], signs[1], 2, signs[2], signs[3], signs[4]])
            s = np.einsum('i,inj->nj', coeff, tensors)
            disp = np.einsum('i,inj->nj', coeff, u)
            vm = von_mises(s); peak = float(vm.max())
            if worst is None or peak > worst['VM_max_MPa']:
                worst = {'coefficients_in_case_order': coeff.tolist(), 'VM_max_MPa': peak,
                         'U_max_mm_at_stress_worst_corner': float(np.linalg.norm(disp, axis=1).max()),
                         'reference_yield_to_elastic_demand': 955/peak,
                         'peak_integration_row': int(vm.argmax()),
                         'peak_element': int(data[0]['element_ids'][vm.argmax()])}
        cycles = {}
        for name, amplitude, mean in (
            ('gravity_to_combined', (combined['stress']-tensors[2])/2, (combined['stress']+tensors[2])/2),
            ('gravity_plus_reversing_850Nm_Y', tensors[4], tensors[2]),
            ('gravity_plus_reversing_100Nm_X', tensors[3], tensors[2])):
            amp = von_mises(amplitude); i = int(amp.argmax())
            cycles[name] = {'equivalent_stress_amplitude_max_MPa': float(amp[i]),
                            'mean_stress_tensor_at_amplitude_peak_MPa': mean[i].tolist(),
                            'mean_correction_applied': False, 'life_cycles': None}
        report['fixtures'][fixture] = {
            'compliance_matrix_mm_N_rad_Nmm': C.tolist(), 'Maxwell_reciprocity_relative_error': reciprocity,
            'combined_superposition_stress_error_MPa': stress_error,
            'combined_superposition_displacement_error_mm': displacement_error,
            'axis_rotations_degrees_at_test_moment': (np.diag(C)[3:]*SCALES[3:]*180/np.pi).tolist(),
            'axis_rotational_stiffness_Nm_per_degree': (np.pi/(180000*np.diag(C)[3:])).tolist(),
            'combined_elastic_reference_yield_ratio': float(955/combined['VM'].max()),
            'combined_meets_assumed_factor_1_5_screen': bool(combined['VM'].max() <= 955/1.5),
            'signed_32_corner_linear_envelope': worst, 'fatigue_demand': cycles}
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('folder', type=Path)
    p.add_argument('--run', action='store_true'); a = p.parse_args()
    if a.run: campaign(a.folder)
    else:
        r = assess(a.folder)
        (a.folder.parent.parent/'structural-assessment.json').write_text(json.dumps(r, indent=2)+'\n')
        print(json.dumps(r, indent=2))
