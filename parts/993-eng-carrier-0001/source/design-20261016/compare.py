"""Compare actual carrier solves with frozen V6f and check linear identities."""
import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[3]
sys.path.insert(0, str(SOURCE.parent / 'bionic-20261011'))
from simulate import elements
sys.path.insert(0, str(SOURCE.parent / 'revalidation-20261016'))
from audit_energy import audit, sha


def select(criteria, geometry, inspection, rows, consistent):
    failures = []
    mass = geometry['dense_reference_mass_kg']
    if not math.isfinite(mass) or mass <= 0 or mass > criteria['geometry']['nominal_mass_kg_max']:
        failures.append('Declared mass ceiling exceeded')
    if (inspection['central_pad_symmetric_difference_mm3'] != 0
            or len(inspection['end_interface_symmetric_difference_mm3']) != 6
            or any(inspection['end_interface_symmetric_difference_mm3'].values())
            or not inspection['study_assembly_screen_pass']):
        failures.append('Exact protected interface inspection failed')
    combined = [row for row in rows if row['case'].startswith('combined-')]
    expected = {(mesh, case) for mesh in criteria['mechanics']['meshes']
                for case in criteria['mechanics']['cases']}
    if len(combined) != 4 or {(row['mesh'], row['case']) for row in combined} != expected:
        failures.append('Four combined comparisons are required')
    for row in combined:
        for metric in ('displacement_max_mm', 'integration_point_VM_max_MPa'):
            values = row['metrics'][metric]
            if (not all(math.isfinite(values[name]) and values[name] > 0 for name in ('candidate', 'V6f'))
                    or values['candidate'] > values['V6f']):
                failures.append(f"{row['mesh']}/{row['case']}: {metric} exceeds V6f")
    if not consistent:
        failures.append('Linear consistency checks failed')
    return {'selection_pass': not failures, 'failures': failures,
            'nominal_mass_kg': geometry['dense_reference_mass_kg'],
            'declared_mass_ceiling_kg': criteria['geometry']['nominal_mass_kg_max'],
            'original_mass_ceiling_kg': 1.2,
            'original_mass_ceiling_pass': geometry['dense_reference_mass_kg'] <= 1.2,
            'scope': 'Explicit comparative numerical selection; not a material allowable',
            'manufacturing_authorized': False}


def compare(folder, output, criteria_path=SOURCE / 'selection-criteria.json'):
    folder, output = Path(folder), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    baseline_path = SOURCE.parent / 'bionic-20261011/correction-20261013/results.json'
    baseline = json.loads(baseline_path.read_text())
    selected_path = baseline_path.parent / 'selected-study.json'
    selected = json.loads(selected_path.read_text())
    current = json.loads((folder / 'study.json').read_text())
    assert current['material'] == selected['material']
    assert current['load_cases'] == selected['load_cases']
    plan = json.loads((SOURCE / 'comparison-plan.json').read_text())
    criteria_path = Path(criteria_path)
    criteria = json.loads(criteria_path.read_text())
    if 'geometry_STEP_sha256' in criteria:
        assert sha(folder / 'carrier.step') == criteria['geometry_STEP_sha256']
    rows, energies, peaks = [], [], []
    for mesh, cases in plan['solver_cases'].items():
        for case in cases:
            path = folder / mesh / (case + '.json')
            result = json.loads(path.read_text())
            with np.load(folder / mesh / (case + '.npz'), allow_pickle=False) as values:
                stress = values['stress']
                normal = ((stress[:,0]-stress[:,1])**2 + (stress[:,1]-stress[:,2])**2
                          + (stress[:,2]-stress[:,0])**2)/2
                vm = np.sqrt(normal + 3*np.sum(stress[:,3:]**2, axis=1))
                assert np.isfinite(vm).all() and np.allclose(vm, values['VM'], rtol=1e-12, atol=1e-12)
                assert float(vm.max()) == result['integration_point_VM_max_MPa']
                assert float(np.linalg.norm(values['displacement'], axis=1).max()) == result['displacement_max_mm']
            reference = baseline['mechanics']['loads'][case] if mesh == 'mesh-9' else baseline['refined_mesh_7'][case]
            row = {'mesh': mesh, 'case': case, 'result_sha256': sha(path), 'metrics': {}}
            for metric in ('displacement_max_mm', 'integration_point_VM_max_MPa', 'external_work_Nmm'):
                old, new = reference[metric], result[metric]
                row['metrics'][metric] = {'V6f': old, 'candidate': new, 'change_percent': 100 * (new / old - 1)}
            rows.append(row)
            energies.append(audit(folder / mesh, case))
            # CLOAD is printed with 12 significant digits; use the audit's load
            # identity tolerance, independently of its 1e-4 energy closure gate.
            assert np.isclose(result['external_work_Nmm'], 2*energies[-1]['half_load_dot_displacement_Nmm'], rtol=1e-10, atol=1e-9)
            if case == 'combined-rigid-static':
                with np.load(folder / mesh / (case + '.npz'), allow_pickle=False) as data:
                    index = int(data['VM'].argmax())
                    element = int(data['element_ids'][index])
                    corners = elements(folder / mesh / 'mesh.inp')[element][:4]
                    centre = data['xyz'][np.searchsorted(data['tags'], corners)].mean(0)
                    peaks.append({'mesh': mesh, 'integration_point_VM_max_MPa': float(data['VM'][index]),
                                  'element': element, 'element_corner_centroid_mm': centre.tolist(),
                                  'location_scope': 'Element corner centroid, not the integration-point coordinate'})
    mesh = folder / 'mesh-9'
    with np.load(mesh / 'gravity-rigid-static.npz', allow_pickle=False) as gravity, \
         np.load(mesh / 'pitch-rigid-static.npz', allow_pickle=False) as pitch, \
         np.load(mesh / 'combined-rigid-static.npz', allow_pickle=False) as combined:
        for field in ('tags', 'element_ids'):
            assert np.array_equal(gravity[field], pitch[field]) and np.array_equal(gravity[field], combined[field])
        superposition = {'stress_abs_error_MPa': float(np.abs(2 * gravity['stress'] + pitch['stress'] - combined['stress']).max()),
                         'displacement_abs_error_mm': float(np.abs(2 * gravity['displacement'] + pitch['displacement'] - combined['displacement']).max())}
    pitch_result = json.loads((mesh / 'pitch-rigid-static.json').read_text())
    gravity_result = json.loads((mesh / 'gravity-rigid-static.json').read_text())
    moment = current['load_cases']['pitch']['moment_Nmm'][1]
    force = current['load_cases']['gravity']['force_N'][2]
    stiffness = {'model_Y_Nm_per_degree': np.pi * moment**2 / (180000 * pitch_result['external_work_Nmm']),
                 'work_conjugate_vertical_N_per_mm': force**2 / gravity_result['external_work_Nmm'],
                 'V6f_model_Y_Nm_per_degree': baseline['mechanics']['axis_rotational_stiffness_Nm_per_degree'][1],
                 'V6f_work_conjugate_vertical_N_per_mm': force**2 / baseline['mechanics']['loads']['gravity-rigid-static']['external_work_Nmm']}
    passed = (all(case['energy_closure_pass'] for case in energies)
              and superposition['stress_abs_error_MPa'] <= plan['superposition_stress_abs_tolerance_MPa']
              and superposition['displacement_abs_error_mm'] <= plan['superposition_displacement_abs_tolerance_mm'])
    geometry = json.loads((folder / 'geometry.json').read_text())
    inspection = json.loads((folder / 'protected-interfaces.json').read_text())
    assert geometry['geometry_sha256']['carrier.step'] == sha(folder / 'carrier.step')
    assert inspection['candidate_STEP_sha256'] == sha(folder / 'carrier.step')
    selection = select(criteria, geometry, inspection, rows, passed)
    selection['criteria_sha256'] = sha(criteria_path)
    selection['criteria_file'] = criteria_path.name
    report = {'design_id': current['design_id'], 'STEP_sha256': sha(folder / 'carrier.step'),
              'source_sha256': sha(__file__), 'baseline_results_sha256': sha(baseline_path),
              'comparison_plan_sha256': sha(SOURCE / 'comparison-plan.json'),
              'cases': rows, 'energy_checks': energies, 'superposition': superposition,
              'linear_consistency_pass': passed, 'selection': selection,
              'stiffness': stiffness, 'peak_element_locations': peaks,
              'mesh_convergence_established': False, 'strength_qualified': False,
              'manufacturing_authorized': False}
    (output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    (output / 'selection.json').write_text(json.dumps(selection, indent=2) + '\n')
    (output / 'source-snapshot.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'design_id': report['design_id'], 'linear_consistency_pass': passed,
                      'selection_pass': selection['selection_pass'],
                      'stiffness': stiffness, 'peak_element_locations': peaks}))
    if not selection['selection_pass']:
        raise SystemExit(1)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--criteria', type=Path, default=SOURCE / 'selection-criteria.json')
    args = parser.parse_args()
    compare(args.folder, args.output, args.criteria)
