"""Prepared unrun stdlib tests; no solver or scientific modules."""
import importlib.util
import itertools
import math
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('material_bar_assessor', HERE/'assess_material_bar.py')
M = importlib.util.module_from_spec(spec)
old = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    spec.loader.exec_module(M)
finally:
    sys.dont_write_bytecode = old


class ConstantOracle:
    """Hypothetical constant-k arithmetic test double, never measured-column evidence."""
    AREA_MM2 = 2
    @staticmethod
    def conductivity(direction, temperature):
        if direction not in ('Z', 'XY') or not 23 <= temperature <= 250:
            raise ValueError('Range')
        return 0.16
    @staticmethod
    def temperature(direction, z):
        return 23+227*z/10
    @staticmethod
    def axial_flux_density(direction):
        return -0.16*227/10


def synthetic():
    nodes = [dict(id=i, x=float(x), y=2.0*y, z=j*M.H, temperature=23+227*j/16)
             for i, (x, y, j) in enumerate(itertools.product((0, 1), (0, 1), range(17)))]
    properties = [dict(id=i, x=0.5, y=1.0, z=(i+0.5)*M.H, k_seen=0.16) for i in range(16)]
    q = 2*0.16*227/10
    return nodes, properties, [dict(time=1, cold_outward_W=q, hot_outward_W=-q)]


class BarAssessorTests(unittest.TestCase):
    def test_full_constant_arithmetic_and_row_reordering(self):
        nodes, properties, powers = synthetic()
        result = M.assess_fields('Z', list(reversed(nodes)), properties[7:]+properties[:7], powers, ConstantOracle)
        self.assertTrue(result['passed'])
        self.assertEqual((result['nodes'], result['cells']), (68, 16))
        self.assertEqual(len(result['cell_records']), 16)
        self.assertEqual(sum(len(c['actual_Gauss_temperatures_C']) for c in result['cell_records']), 128)
        self.assertFalse(result['all_intermediate_nonlinear_evaluations_observed'])
        self.assertFalse(result['head_or_process_qualified'])

    def test_duplicate_coordinate_or_fractional_id_rejected(self):
        for mutation in ('duplicate', 'id'):
            nodes, properties, powers = synthetic()
            if mutation == 'duplicate':
                nodes[1].update({k:nodes[0][k] for k in ('x','y','z')})
            else:
                nodes[0]['id'] = 0.5
            with self.assertRaises(ValueError):
                M.assess_fields('Z', nodes, properties, powers, ConstantOracle)

    def test_wrong_cell_center_and_final_range_refused(self):
        nodes, properties, powers = synthetic()
        properties[0]['z'] += 0.01
        with self.assertRaisesRegex(ValueError, 'spatial coordinate'):
            M.assess_fields('Z', nodes, properties, powers, ConstantOracle)
        nodes, properties, powers = synthetic()
        nodes[0]['temperature'] = 22.99
        with self.assertRaisesRegex(ValueError, 'outside measured range'):
            M.assess_fields('Z', nodes, properties, powers, ConstantOracle)

    def test_field_and_property_corruption_yields_failed_checks(self):
        nodes, properties, powers = synthetic()
        nodes[1]['temperature'] += 0.01
        properties[2]['k_seen'] += 0.001
        result = M.assess_fields('Z', nodes, properties, powers, ConstantOracle)
        self.assertFalse(result['passed'])
        names = {c['name'] for c in result['failed_checks']}
        self.assertIn('cross_section_uniformity_1', names)
        self.assertIn('k_Gauss_average_cell_2', names)
        self.assertIn('consistent_cell_flux_relative_deviation_about_mean', names)

    def test_wrong_end_sign_or_multiple_final_rows_refused(self):
        nodes, properties, powers = synthetic()
        powers[0]['hot_outward_W'] *= -1
        with self.assertRaisesRegex(ValueError, 'signs'):
            M.assess_fields('Z', nodes, properties, powers, ConstantOracle)
        with self.assertRaisesRegex(ValueError, 'one final'):
            M.assess_fields('Z', nodes, properties, powers*2, ConstantOracle)

    def test_csv_partial_duplicate_header_nonfinite_empty(self):
        texts = ['id,x,y,z,temperature\n0,0,0,0\n',
                 'id,x,y,z,temperature,temperature\n0,0,0,0,23,23\n',
                 'id,x,y,z,temperature\n0,0,0,0,nan\n',
                 'id,x,y,z,temperature\n']
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'nodes.csv'
            for text in texts:
                path.write_text(text)
                with self.assertRaises(ValueError):
                    M.csv_rows(path, ('id','x','y','z','temperature'))

    def test_missing_or_ambiguous_export_refused(self):
        for pins in ({}, {'conductivity-z_nodes_0001.csv':'a', 'conductivity-z_nodes_0002.csv':'b'}):
            with self.assertRaisesRegex(ValueError, 'ambiguous'):
                M.selected(pins, 'conductivity-z', 'nodes')

    def test_nonfinite_field_refused(self):
        nodes, properties, powers = synthetic()
        nodes[8]['temperature'] = math.inf
        with self.assertRaisesRegex(ValueError, 'Nonfinite'):
            M.assess_fields('XY', nodes, properties, powers, ConstantOracle)


if __name__ == '__main__':
    unittest.main()
