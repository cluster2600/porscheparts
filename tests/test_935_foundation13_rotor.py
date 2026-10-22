import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0, str(SOURCE))
from assess_foundation13_rotor import assess, history
try:
    import numpy as np
    import trimesh
    from prepare_foundation13_rotor import prepare, write_si_obj
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'Requires numpy/scipy/trimesh')
class Foundation13RotorTests(unittest.TestCase):
    def test_obj_retains_close_vertices_and_connectivity_in_si(self):
        points = np.array([[140, 0, 0], [np.nextafter(np.float32(140), np.float32(141)), 0, 0],
                           [140, 1, 0]], dtype=np.float32)
        faces = np.array([[0, 1, 2]], dtype=np.int32)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'surface.obj'
            write_si_obj(path, points, faces)
            read = np.loadtxt(path, max_rows=3, usecols=(1, 2, 3))
            np.testing.assert_array_equal(read, points.astype(np.float64) * .001)
            self.assertNotEqual(read[0, 0], read[1, 0])
            self.assertTrue(path.read_text().endswith('g rotor\nf 1 2 3\n'))
            with self.assertRaises(FileExistsError):
                write_si_obj(path, points, faces)

    def test_foundation_family_and_private_exact_transport(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            mesh = trimesh.creation.box(extents=[10, 20, 30])
            vertices = mesh.vertices.astype(np.float32)
            faces = mesh.faces.astype(np.int32)
            trimesh.Trimesh(vertices, faces, process=False).export(root / 'rotor.stl')
            np.savez(root / 'rotor.npz', vertices=vertices, faces=faces)
            digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            config = {'rotor_stl_path': str(root / 'rotor.stl'), 'rotor_stl_sha256': digest(root / 'rotor.stl'),
                      'rotor_bundle_path': str(root / 'rotor.npz'), 'rotor_bundle_sha256': digest(root / 'rotor.npz'),
                      'assumed_m_per_source_unit': .001, 'duct_half_width_m': .18, 'duct_half_height_m': .2,
                      'flow_m3_s': .5, 'rotor_rpm': 6000, 'air_density_kg_m3': 1.204,
                      'kinematic_viscosity_m2_s': 1.5e-5, 'rotating_zone_radius_m': .16,
                      'rotating_zone_z_m': [-.06, .07], 'turbulence_intensity': .03,
                      'turbulence_length_m': .007, 'iterations': 20,
                      'mesh_cells': {'coarse': [8, 8, 8], 'medium': [10, 10, 10], 'fine': [12, 12, 12]}}
            case = {'purpose': 'hypothesis_screen', 'scale_verified': False, 'axis_verified': False,
                    'assumptions': [{'rejection_test': 'Physical measurements'}], 'cfd': config}
            path = root / 'case.json'
            path.write_text(json.dumps(case))
            output = prepare(path, root / 'output')
            for name in config['mesh_cells']:
                target = output / name
                metadata = json.loads((target / 'case-metadata.json').read_text())
                self.assertEqual(metadata['solver_family'], 'OpenFOAM_Foundation_13')
                self.assertFalse(metadata['numerical_acceptance'])
                self.assertFalse(metadata['scale_verified'])
                for filename, expected in metadata['prepared_input_sha256'].items():
                    self.assertEqual(digest(target / filename), expected)
                self.assertIn('type MRFnoSlip;', (target / '0/U').read_text())
                self.assertIn('omega 6000 [rpm]', (target / 'constant/MRFProperties').read_text())
                self.assertIn('model kOmegaSST', (target / 'constant/momentumTransport').read_text())
                self.assertIn('solver incompressibleFluid;', (target / 'system/controlDict').read_text())
                self.assertIn('operation average;weightField phi;', (target / 'system/controlDict').read_text())
                self.assertNotIn('regionType', (target / 'system/controlDict').read_text())
                self.assertFalse((target / 'constant/turbulenceProperties').exists())
                self.assertFalse((target / 'constant/triSurface/rotor.stl').exists())
            config['rotor_bundle_sha256'] = '0' * 64
            path.write_text(json.dumps(case))
            with self.assertRaises(ValueError):
                prepare(path, root / 'wrong-hash')
            self.assertFalse((root / 'wrong-hash').exists())
            for key in ('scale_verified', 'axis_verified'):
                invalid = dict(case, **{key: True})
                path.write_text(json.dumps(invalid))
                with self.assertRaises(ValueError):
                    prepare(path, root / 'false-claim')


class Foundation13AssessmentTests(unittest.TestCase):
    def test_history_rejects_duplicate_nonfinite_and_incomplete_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'history.dat'
            for text in ('1 2\n1 3\n', '1 nan\n2 3\n', '1 2 3\n2 3 4\n'):
                p.write_text(text)
                with self.assertRaises(ValueError):
                    history(p, 2)

    def test_force_columns_density_flux_pressure_and_refusal_of_unsteady_data(self):
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            case = Path(folder)
            files = ('system/controlDict', 'system/fvSolution', 'system/fvSchemes', 'constant/MRFProperties',
                     'constant/physicalProperties', 'constant/momentumTransport', 'constant/triSurface/rotor.obj',
                     '0/U', '0/p', '0/k', '0/omega', '0/nut')
            for name in files:
                p = case / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('endTime 500;')
            metadata = {'solver_family': 'OpenFOAM_Foundation_13',
                        'classification': 'conditional_square_duct_not_935_installation',
                        'scale_verified': False, 'axis_verified': False, 'rotor_rpm_assumed': 6000,
                        'specified_volume_flow_m3_s': .5, 'density_kg_m3_assumed': 3,
                        'geometry_sha256': 'synthetic_fixture',
                        'prepared_input_sha256': {n: digest(case / n) for n in files}}
            (case / 'case-metadata.json').write_text(json.dumps(metadata))
            (case / 'execution.json').write_text(json.dumps({'exit': 0, 'stop_reason': None,
                'input_files_unchanged': True, 'input_receipt_sha256': digest(case / 'case-metadata.json')}))
            (case / 'log.foamRun').write_text('End\n')
            (case / 'log.checkMesh').write_text('Mesh OK.\n')
            (case / 'log.checkMesh.allGeometry').write_text('Mesh OK.\n')
            for name, values in [('inletFlow', '-.5'), ('outletFlow', '.5'),
                                 ('inletPressure', '10 4'), ('outletPressure', '30 9')]:
                p = case / f'postProcessing/{name}/0/surfaceFieldValue.dat'
                p.parent.mkdir(parents=True)
                p.write_text(''.join(f'{t} {values}\n' for t in range(10, 501, 10)))
            forces = case / 'postProcessing/rotorForces/0/forces.dat'
            forces.parent.mkdir(parents=True)
            header = '# Time forces(pressure viscous) moments(pressure viscous)\n'
            rows = [f'{t} ((0 0 0) (0 0 0)) ((0 0 -2) (0 0 -.5))\n' for t in range(10, 501, 10)]
            forces.write_text(header + ''.join(rows))
            result = assess(case)
            self.assertTrue(result['single_mesh_pilot_pass'])
            self.assertEqual(result['metrics']['total_pressure_rise_Pa']['final_window_mean'], 67.5)
            self.assertEqual(result['metrics']['resisting_torque_z_Nm']['final_window_mean'], 2.5)
            self.assertAlmostEqual(result['metrics']['shaft_power_W']['final_window_mean'], 500 * 3.141592653589793)
            self.assertFalse(result['accepted_for_935_fan_curve'])
            (case / 'log.checkMesh.allGeometry').write_text('Failed 1 mesh checks.\n')
            self.assertFalse(assess(case)['single_mesh_pilot_pass'])
            (case / 'log.checkMesh.allGeometry').write_text('Mesh OK.\n')
            rows[-1] = rows[-1].replace('-.5', '-1')
            forces.write_text(header + ''.join(rows))
            self.assertFalse(assess(case)['single_mesh_pilot_pass'])
            (case / '0/U').write_text('changed')
            with self.assertRaises(ValueError):
                assess(case)


class Foundation13CouetteTests(unittest.TestCase):
    def test_couette_wall_speeds_and_analytic_torque(self):
        import importlib.util
        import math
        spec = importlib.util.spec_from_file_location('couette_935', SOURCE / 'foundation13-study-20261022/prepare_couette.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertAlmostEqual(module.velocity(module.RI, 0)[1], module.OMEGA * module.RI)
        self.assertAlmostEqual(module.velocity(module.RO, 0)[1], 0)
        self.assertAlmostEqual(module.torque(), -4 * math.pi**2 * .0000002)


if __name__ == '__main__':
    unittest.main()
