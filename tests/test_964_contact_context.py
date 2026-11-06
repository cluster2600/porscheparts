"""Original boundary topology must remain separate from physical aperture identity."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from _deps import require_modules

require_modules('numpy')
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'twins/964-chassis/contact-context-20261106/audit_boundaries.py'
SPEC = importlib.util.spec_from_file_location('contact_boundary_audit', SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class ContactContextTests(unittest.TestCase):
    def setUp(self):
        self.faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)
        self.edges = np.array([[2, 3], [0, 1], [3, 0], [1, 2]], dtype=np.int32)
        self.loops = {'component_1223': np.array([0, 1, 2, 3], dtype=np.int64)}

    def test_sole_boundary_preserves_original_rows_without_aperture_identity(self):
        report, ids = AUDIT.component_incidence(self.faces, 4, self.edges, self.loops)
        self.assertEqual(report['source_unique_edges'], 5)
        self.assertEqual(report['source_boundary_edges'], 4)
        self.assertEqual(report['euler_characteristic_V_minus_E_plus_F'], 1)
        self.assertEqual(report['original_boundary_cycles'][0]['boundary_component_id'], 1223)
        np.testing.assert_array_equal(np.sort(ids['source_open_edge_row_ids']), [0, 1, 2, 3])
        np.testing.assert_array_equal(ids['boundary_1223_source_vertex_ids'], [0, 1, 2, 3])
        self.assertFalse(report['inner_aperture_in_surrounding_plate_identified'])
        self.assertEqual(report['physical_rim_vs_acquisition_gap'], 'unresolved')
        self.assertNotIn('genus', report)

    def test_surrounding_strip_retains_two_distinct_original_boundary_cycles(self):
        # Four quadrilateral strips between nested square boundaries, triangulated.
        faces = np.array([[0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
                          [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
        edges = np.vstack([self.edges, self.edges + 4])
        loops = {'component_1414': np.arange(4), 'component_1415': np.arange(4, 8)}
        report, ids = AUDIT.component_incidence(faces, 8, edges, loops)
        self.assertEqual(report['euler_characteristic_V_minus_E_plus_F'], 0)
        self.assertEqual(report['source_unique_edges'], 16)
        self.assertEqual([row['boundary_component_id'] for row in report['original_boundary_cycles']],
                         [1414, 1415])
        np.testing.assert_array_equal(np.sort(ids['boundary_1415_source_open_edge_row_ids']), [4, 5, 6, 7])
        self.assertFalse(report['inner_aperture_in_surrounding_plate_identified'])
        # Combining disconnected cycles under one ID must not pass degree counts alone.
        with self.assertRaisesRegex(ValueError, 'disconnected cycles'):
            AUDIT.component_incidence(faces, 8, edges, {'component_0': np.arange(8)})

    def test_missing_foreign_repeated_ids_or_artificial_crop_edges_fail_closed(self):
        changes = [({}, self.edges, self.faces),
                   ({'component_0': np.array([0, 1, 2, 4])}, self.edges, self.faces),
                   ({'component_0': np.array([0, 1, 2, 2])}, self.edges, self.faces),
                   (self.loops, np.array([[2, 3], [0, 4], [3, 0], [1, 2]]), self.faces),
                   (self.loops, np.vstack([self.edges, self.edges[0]]), self.faces),
                   (self.loops, self.edges, self.faces[:1])]
        for loops, edges, faces in changes:
            with self.subTest(loops=loops, faces=len(faces)), self.assertRaises(ValueError):
                AUDIT.component_incidence(faces, 5, edges, loops)

    def test_original_ids_above_int32_packed_key_range_remain_exact(self):
        faces = self.faces + 50_000
        edges = self.edges + 50_000
        loops = {'component_7': np.arange(50_000, 50_004)}
        report, ids = AUDIT.component_incidence(faces, 70_000, edges, loops)
        self.assertEqual(report['source_boundary_edges'], 4)
        self.assertGreater(AUDIT.edge_keys(edges, 70_000).min(), np.iinfo(np.int32).max)
        np.testing.assert_array_equal(ids['source_vertex_ids'], np.arange(50_000, 50_004))
        with self.assertRaises(ValueError):
            AUDIT.edge_keys(edges, 3_037_000_500)

    def test_wrong_pinned_input_hash_rejects_before_output_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'wrong.npy'
            source.write_bytes(b'not the acquired source')
            output = ROOT / 'work' / ('context-rejected-' + Path(folder).name)
            command = [sys.executable, str(SCRIPT), '--output', str(output)]
            for name in AUDIT.PINNED:
                command.extend(['--' + name.replace('_', '-'), str(source)])
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Pinned original input hash mismatch', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
