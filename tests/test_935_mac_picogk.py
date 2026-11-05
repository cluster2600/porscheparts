import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0, str(SOURCE))
try:
    from assess_mac_fea import assess
except ImportError:
    assess = None


@unittest.skipIf(assess is None, 'NumPy is unavailable')
class MacFeaAuditTests(unittest.TestCase):
    def setUp(self):
        (ROOT / 'work').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'work')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prepared, self.solved = self.root / 'prepared', self.root / 'solved'
        self.prepared.mkdir(); self.solved.mkdir()
        self.grid = self.root / 'grid.json'
        self.grid.write_text(json.dumps({'input_sha256': '0'*64, 'pitch_mm': 1, 'cells': [[25, 0, 0]]}))
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        case = {'purpose': 'hypothesis_screen', 'scale_verified': False,
                'grid_path': '/repo/' + str(self.grid.relative_to(ROOT)), 'grid_sha256': sha(self.grid),
                'material_id': 'alsi10mg', 'rotor_rpm': 6000}
        (self.prepared / 'case.json').write_text(json.dumps(case))
        corners = [(25,0,0),(26,0,0),(26,1,0),(25,1,0),(25,0,1),(26,0,1),(26,1,1),(25,1,1)]
        deck = '*NODE\n' + ''.join(f'{i},{x},{y},{z}\n' for i,(x,y,z) in enumerate(corners,1))
        deck += '*ELEMENT,TYPE=C3D8\n1,1,2,3,4,5,6,7,8\n*END\n'
        for folder in (self.prepared, self.solved):
            (folder / 'rotor.inp').write_text(deck)
        cards = ROOT / 'twins/935-horizontal-cooling-system-f0/vast-omniverse-screen/materials.json'
        receipt = {'deck_sha256': sha(self.prepared / 'rotor.inp'), 'geometry_sha256': '0'*64,
                   'C3D8_elements': 1, 'clamped_bore_nodes': 8, 'material_cards_sha256': sha(cards),
                   'CAD_volume_relative_error': 0}
        (self.prepared / 'receipt.json').write_text(json.dumps(receipt))
        for name in ('ccx.log', 'log.rotor'):
            (self.solved / name).write_text('CalculiX Version 2.21\nJob finished\n')
        (self.solved / 'ccx.exit').write_text('0\n')
        factor = 2.67e-9 * (6000 * math.pi / 30)**2
        data = ' forces (fx,fy,fz)\n'
        data += ''.join(f'{i} {-25.5*factor/8:.17g} {-.5*factor/8:.17g} 0\n' for i in range(1,9))
        data += ' displacements (vx,vy,vz)\n' + ''.join(f'{i} 0 0 0\n' for i in range(1,9))
        data += ' stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz)\n'
        data += ''.join(f'1 {i} 10 0 0 0 0 0\n' for i in range(1,9))
        (self.solved / 'rotor.dat').write_text(data)

    def test_complete_cube_force_and_moment_closure_and_sparse_units(self):
        # Synthetic fully restrained cube: reaction = -rho*volume*omega^2*centroid.
        result = assess(self.prepared, self.solved, self.root / 'out')
        self.assertTrue(result['reaction_balance_pass'])
        self.assertAlmostEqual(result['relative_force_balance_error'], 0)
        self.assertAlmostEqual(result['relative_moment_balance_error'], 0)
        self.assertEqual(result['element_peak_p95_outside_r25_MPa'], 10)
        self.assertAlmostEqual(result['conditional_grid_mass_kg'], 2.67e-6)
        for flag in ('scale_verified', 'mesh_convergence_established', 'manufacturing_authorized', 'physical_validation'):
            self.assertIs(result[flag], False)

    def test_missing_integration_point_is_rejected(self):
        path = self.solved / 'rotor.dat'; path.write_text(path.read_text().replace('1 8 10 0 0 0 0 0\n', ''))
        with self.assertRaisesRegex(ValueError, 'eight-point'):
            assess(self.prepared, self.solved, self.root / 'out')

    def test_changed_grid_and_log_alias_are_rejected(self):
        self.grid.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Grid changed'):
            assess(self.prepared, self.solved, self.root / 'out')
        (self.solved / 'log.rotor').write_text('Other log')
        with self.assertRaisesRegex(ValueError, 'alias differs'):
            assess(self.prepared, self.solved, self.root / 'out')

    def test_nonfinite_stress_is_rejected(self):
        path = self.solved / 'rotor.dat'; path.write_text(path.read_text().replace('10 0 0 0 0 0', 'nan 0 0 0 0 0'))
        with self.assertRaisesRegex(ValueError, 'finite'):
            assess(self.prepared, self.solved, self.root / 'out')

    def test_wrong_reaction_cannot_pass_equilibrium(self):
        path = self.solved / 'rotor.dat'
        text = path.read_text().splitlines(); text[1] = '1 1 0 0'
        path.write_text('\n'.join(text) + '\n')
        result = assess(self.prepared, self.solved, self.root / 'out')
        self.assertFalse(result['reaction_balance_pass'])


class MacExecutionTests(unittest.TestCase):
    def test_execution_pins_sources_and_preserves_failed_quality_gates(self):
        record = json.loads((ROOT / 'docs/research/935-horizontal-cooling/mac-picogk-20261012.json').read_text())
        for path, expected in record['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected, path)
        self.assertEqual(record['target'], '935')
        self.assertEqual(record['geometry_platform'], 'osx-arm64')
        self.assertTrue(record['roots']['protected_triangles_exactly_preserved'])
        self.assertTrue(record['fea']['all_material_reaction_balances_pass'])
        for flag in ('scale_verified', 'manufacturing_authorized', 'physical_validation', 'vast_rental_used'):
            self.assertIs(record[flag], False)
        self.assertFalse(record['cfd']['single_mesh_pilot_pass'])
        self.assertFalse(record['fea']['mesh_convergence_established'])
        self.assertEqual(record['thickness']['resolved_probes'] + record['thickness']['unresolved_probes'], 432)

    def test_independent_density_and_elastic_scaling_matches_fresh_solves(self):
        record = json.loads((ROOT / 'docs/research/935-horizontal-cooling/mac-picogk-20261012.json').read_text())
        cases = {r['material_id']: r for r in record['fea']['material_cases'] if r['pitch_mm'] == 1.5}
        base = cases['alsi10mg']
        for material, rho, young in [('we43', 1.83, 44.1), ('ti64', 4.4, 110)]:
            result = cases[material]
            self.assertAlmostEqual(result['von_mises_max_MPa'] / base['von_mises_max_MPa'], rho / 2.67, places=5)
            self.assertAlmostEqual(result['maximum_displacement_mm'] / base['maximum_displacement_mm'], rho / 2.67 * 70 / young, places=5)


if __name__ == '__main__':
    unittest.main()
