"""Independent strain-energy identities, not carrier qualification."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'parts/993-eng-carrier-0001/source/revalidation-20261016/audit_energy.py'
HAS_NUMPY = importlib.util.find_spec('numpy') is not None
if HAS_NUMPY:
    import numpy as np
    spec = importlib.util.spec_from_file_location('carrier_energy', SOURCE)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)


class PublishedEvidenceTests(unittest.TestCase):
    def test_current_inputs_results_and_rejection_remain_bound(self):
        folder = SOURCE.parent
        summary = json.loads((folder / 'results.json').read_text())
        for name, expected in summary['evidence_sha256'].items():
            self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), expected, name)
        step = ROOT / 'parts/993-eng-carrier-0001/derived/correction-20261013/carrier.step'
        self.assertEqual(hashlib.sha256(step.read_bytes()).hexdigest(), summary['STEP_sha256'])
        inventory = json.loads((folder.parent / 'bionic-20261011/correction-20261013/raw-inventory.json').read_text())
        original = {item['path']: item['sha256'] for item in inventory}
        cases = []
        for mesh in ('9', '7'):
            report = json.loads((folder / f'energy-mesh-{mesh}.json').read_text())
            self.assertEqual(report['source_sha256'], summary['evidence_sha256']['audit_energy.py'])
            for case in report['cases']:
                for name, expected in case['inputs_sha256'].items():
                    self.assertEqual(original['v6f/' + name], expected, name)
                self.assertTrue(case['energy_closure_pass'])
            cases.extend(report['cases'])
        self.assertEqual(len(cases), summary['energy']['case_count'])
        self.assertEqual(max(case['relative_energy_closure_error'] for case in cases), summary['energy']['maximum_relative_error'])
        native = json.loads((folder / 'dfam/carrier-checker.stdout.log').read_text().splitlines()[0])
        assessment = json.loads((folder / 'dfam/assessment.json').read_text())
        for name, expected in native.items():
            self.assertEqual(assessment['metrics'][name], expected, name)
        self.assertEqual(assessment['screen_status'], 'rejected')
        self.assertEqual(summary['DfAM']['needle_triangles'], native['needle_triangles'])
        self.assertEqual(summary['DfAM']['thin_wall_area_fraction'], native['thin_wall_area_fraction'])
        for name in ('fitment_validated', 'strength_qualified', 'fatigue_qualified',
                     'mesh_convergence_established', 'full_build_process_simulated', 'manufacturing_authorized'):
            self.assertFalse(summary[name], name)


@unittest.skipUnless(HAS_NUMPY, 'Optional NumPy runtime is needed for energy audit fixtures')
class EnergyAuditTests(unittest.TestCase):
    def setUp(self):
        corners = np.array([[0., 0, 0], [2, 0, 0], [.2, 3, 0], [.1, .4, 4]])
        pairs = audit.EDGE_PAIRS
        self.points = np.vstack((corners, (corners[pairs[:, 0]] + corners[pairs[:, 1]]) / 2))[None]
        self.E, self.nu = 107000., .31

    def test_constant_affine_strain_and_scale(self):
        strain = np.array([[.001, .0002, -.0001], [.0002, -.0003, .0004], [-.0001, .0004, .0007]])
        shear = self.E / (2 * (1 + self.nu))
        lame = self.E * self.nu / ((1 + self.nu) * (1 - 2 * self.nu))
        stress = 2 * shear * strain + lame * np.trace(strain) * np.eye(3)
        tensor = stress[[0, 1, 2, 0, 0, 1], [0, 1, 2, 1, 2, 2]]
        energy, volume = audit.strain_energy(self.points, np.tile(tensor, (1, 4, 1)), self.E, self.nu)
        self.assertAlmostEqual(volume, 4.)
        self.assertAlmostEqual(energy, .5 * np.sum(stress * strain) * volume)
        scaled, scaled_volume = audit.strain_energy(self.points * 2, np.tile(tensor, (1, 4, 1)), self.E, self.nu)
        self.assertAlmostEqual(scaled, energy * 8)
        self.assertAlmostEqual(scaled_volume, volume * 8)

    def test_shear_and_hydrostatic_energy(self):
        tau, pressure = 123., 42.
        shear = self.E / (2 * (1 + self.nu))
        for tensor, density in [([0, 0, 0, tau, 0, 0], tau**2 / (2 * shear)),
                                ([pressure] * 3 + [0] * 3, 3 * (1 - 2 * self.nu) * pressure**2 / (2 * self.E))]:
            energy, volume = audit.strain_energy(self.points, np.tile(tensor, (1, 4, 1)), self.E, self.nu)
            self.assertAlmostEqual(energy, volume * density)

    def test_rejects_curved_inverted_and_nonfinite_inputs(self):
        tensor = np.ones((1, 4, 6))
        curved = self.points.copy()
        curved[0, 4, 0] += .01
        inverted = self.points.copy()
        inverted[..., 0] *= -1
        for points in (curved, inverted, self.points * np.nan):
            with self.assertRaises(ValueError):
                audit.strain_energy(points, tensor, self.E, self.nu)
        with self.assertRaises(ValueError):
            audit.strain_energy(self.points, tensor * np.nan, self.E, self.nu)

    def test_duplicate_mesh_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'mesh.inp'
            path.write_text('*NODE\n1,0,0,0\n1,1,0,0\n*ELEMENT,TYPE=C3D10\n1,1,2,3,4,5,6,7,8,9,10\n')
            with self.assertRaisesRegex(ValueError, 'Node IDs'):
                audit.read_mesh(path)

    def test_force_print_block_is_not_a_displacement_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'case.dat'
            path.write_text('displacements (vx,vy,vz)\n1 .1 .2 .3\nforces (fx,fy,fz)\n1 10 20 30\nstresses (elem,ip,sxx,syy,szz,sxy,sxz,syz)\n1 1 1 2 3 4 5 6\n')
            fields = audit.dat_fields(path)
            np.testing.assert_array_equal(fields['displacements'], [[1, .1, .2, .3]])
            np.testing.assert_array_equal(fields['stresses'], [[1, 1, 1, 2, 3, 4, 5, 6]])

    def test_complete_synthetic_case_and_corrupted_identities(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'mesh'
            folder.mkdir()
            xyz, tags = self.points[0], np.arange(1, 11)
            nodes = '\n'.join(','.join(map(str, [tag, *point])) for tag, point in zip(tags, xyz))
            (folder / 'mesh.inp').write_text('*NODE\n' + nodes + '\n*ELEMENT,TYPE=C3D10\n1,1,2,3,4,5,6,7,8,9,10\n')
            np.savez(folder / 'mesh.npz', tags=tags, xyz=xyz)
            for name in ('carrier.step', 'study.json', 'geometry.json'):
                (root / name).write_text('synthetic identity fixture')
            (folder / 'mesh.json').write_text(json.dumps({'STEP_sha256': audit.sha(root / 'carrier.step')}))
            case = 'synthetic-spring-static'
            deck = folder / (case + '.inp')
            deck.write_text('*INCLUDE,INPUT=mesh.inp\n*ELASTIC\n100,0\n*ELEMENT,TYPE=SPRING1,ELSET=S\n2,2\n*SPRING,ELSET=S\n1\n10\n*STEP\n*STATIC\n*CLOAD\n2,1,4.4\n*END STEP\n')
            receipt = {'name': case, 'procedure': 'static', 'mesh_sha256': audit.sha(folder / 'mesh.inp'), 'input_sha256': audit.sha(deck)}
            (folder / (case + '.json')).write_text(json.dumps(receipt))
            u = np.zeros_like(xyz)
            u[:, 0] = .02 * xyz[:, 0]
            force = np.zeros_like(xyz)
            force[1, 0] = 4.4
            stress = np.tile([2., 0, 0, 0, 0, 0], (4, 1))
            displacement_lines = '\n'.join(' '.join(map(str, [tag, *point])) for tag, point in zip(tags, u))
            stress_lines = '\n'.join(' '.join(map(str, [1, ip, *tensor])) for ip, tensor in enumerate(stress, 1))
            (folder / (case + '.dat')).write_text('displacements (vx,vy,vz)\n' + displacement_lines + '\nstresses (elem,ip,components)\n' + stress_lines + '\n')
            result = dict(tags=tags, xyz=xyz, displacement=u, force=force, element_ids=np.ones(4), stress=stress, fixed=np.array([], dtype=int))
            np.savez(folder / (case + '.npz'), **result)
            report = audit.audit(folder, case)
            self.assertTrue(report['energy_closure_pass'])
            self.assertAlmostEqual(report['solid_strain_energy_Nmm'], .08)
            self.assertAlmostEqual(report['spring_strain_energy_Nmm'], .008)
            self.assertAlmostEqual(report['half_load_dot_displacement_Nmm'], .088)
            result['tags'] = tags[::-1]
            np.savez(folder / (case + '.npz'), **result)
            with self.assertRaisesRegex(ValueError, 'NPZ mesh identity'):
                audit.audit(folder, case)
            deck.write_text(deck.read_text() + '** altered deck\n')
            with self.assertRaisesRegex(ValueError, 'Solver deck hash'):
                audit.audit(folder, case)


if __name__ == '__main__':
    unittest.main()
