"""Exact occupancy fixtures, not mocks of the flood-fill implementation."""
import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/picogk-connectivity'
spec = importlib.util.spec_from_file_location('picogk_connectivity', SOURCE / 'connectivity.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def index(x, y, z, shape):
    return x + shape[0] * (y + shape[1] * z)


def hollow_cube(tunnel=False):
    shape = (11, 11, 11)
    mask = bytearray([1]) * 1331
    for z in range(3, 8):
        for y in range(3, 8):
            for x in range(3, 8):
                if x in (3, 7) or y in (3, 7) or z in (3, 7):
                    mask[index(x, y, z, shape)] = 0
    if tunnel:
        mask[index(3, 5, 5, shape)] = 1
    return shape, mask


class PicoGKConnectivityTests(unittest.TestCase):
    def test_hollow_cube_has_one_isolated_volume_not_two_surface_shells(self):
        shape, mask = hollow_cube()
        for neighbours in (6, 26):
            result = module.classify(mask, shape, 1.0, neighbours)
            self.assertEqual(result['potential_isolated_component_count'], 1)
            self.assertEqual(result['isolated_sample_count'], 27)
            self.assertEqual(result['exterior_connected_sample_count'], 1206)

    def test_face_tunnel_connects_cavity_to_seeded_exterior(self):
        shape, mask = hollow_cube(tunnel=True)
        for neighbours in (6, 26):
            result = module.classify(mask, shape, 1.0, neighbours)
            self.assertEqual(result['isolated_sample_count'], 0)
            self.assertEqual(result['exterior_connected_sample_count'], 1234)

    def test_single_voxel_seal_restores_closed_component(self):
        shape, mask = hollow_cube(tunnel=True)
        mask[index(3, 5, 5, shape)] = 0
        self.assertEqual(module.classify(mask, shape, 1.0, 6)['isolated_sample_count'], 27)

    def test_diagonal_contact_depends_on_connectivity_not_flow_area(self):
        shape = (5, 5, 5)
        mask = bytearray(125)
        for position in ((0, 0, 0), (1, 1, 1), (2, 2, 2)):
            mask[index(*position, shape)] = 1
        six = module.classify(mask, shape, 1.0, 6)
        twenty_six = module.classify(mask, shape, 1.0, 26)
        self.assertEqual(six['potential_isolated_component_count'], 2)
        self.assertEqual(six['isolated_sample_count'], 2)
        self.assertEqual(twenty_six['isolated_sample_count'], 0)
        self.assertFalse(twenty_six['physical_sealed_cavity_proved'])

    def test_no_periodic_wrapping_between_rows_or_planes(self):
        shape = (5, 5, 5)
        mask = bytearray(125)
        # Adjacent flattened indices 54/55, but not face neighbours in 3D.
        for position in ((4, 0, 2), (0, 1, 2), (1, 1, 2)):
            mask[index(*position, shape)] = 1
        self.assertEqual(module.classify(mask, shape, 1.0, 6)['isolated_sample_count'], 0)
        # An isolated interior cell must not join a boundary through a flat stride.
        mask = bytearray(125)
        mask[index(4, 0, 2, shape)] = 1
        mask[index(1, 1, 2, shape)] = 1
        self.assertEqual(module.classify(mask, shape, 1.0, 26)['isolated_sample_count'], 1)

    def test_all_six_outer_faces_are_seeded(self):
        shape = (5, 5, 5)
        for position in ((0, 2, 2), (4, 2, 2), (2, 0, 2), (2, 4, 2), (2, 2, 0), (2, 2, 4)):
            mask = bytearray(125)
            mask[index(*position, shape)] = 1
            self.assertEqual(module.classify(mask, shape, 1.0, 6)['exterior_connected_sample_count'], 1)

    def test_all_void_and_no_void(self):
        for value in (0, 1):
            result = module.classify(bytes([value]) * 125, (5, 5, 5), 0.6, 26)
            self.assertEqual(result['exterior_connected_sample_count'], 125 * value)
            self.assertEqual(result['isolated_sample_count'], 0)

    def test_input_is_preserved_and_volume_is_grid_estimate(self):
        shape, mask = hollow_cube()
        original = bytes(mask)
        result = module.classify(mask, shape, 0.5, 6)
        self.assertEqual(bytes(mask), original)
        self.assertEqual(result['voxel_sum_isolated_volume_mm3_estimate'], 27 * 0.5**3)
        self.assertFalse(result['CFD_domain_qualified'])
        self.assertFalse(result['manufacturing_authorized'])

    def test_invalid_shape_mask_spacing_connectivity_and_memory_bound(self):
        for mask, shape, step, adjacency in ((bytes(27), (3, 3, 2), 1, 6),
                (bytes(26), (3, 3, 3), 1, 6), (bytes([2])*27, (3, 3, 3), 1, 6),
                (bytes(27), (3, 3, 3), float('nan'), 6), (bytes(27), (3, 3, 3), 0, 6),
                (bytes(27), (3, 3, 3), 1, 18), (b'', (1000, 1000, 1000), 1, 6)):
            with self.assertRaises(ValueError):
                module.classify(mask, shape, step, adjacency)

    def test_cli_refuses_failed_native_partition_before_connectivity(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'sampling-report.json').write_text(json.dumps({'status': 'native_partition_failed'}))
            result = subprocess.run([sys.executable, '-B', str(SOURCE / 'connectivity.py'),
                str(root), str(root / 'new-report.json')], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Native sampling did not pass', result.stderr)
            self.assertFalse((root / 'new-report.json').exists())

    def test_cli_refuses_occupancy_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'sampling-report.json').write_text(json.dumps({
                'status': 'native_sampling_passed_not_topology_qualification',
                'occupancy_sha256': '0' * 64}))
            (root / 'void-occupancy.bin').write_bytes(bytes(125))
            result = subprocess.run([sys.executable, '-B', str(SOURCE / 'connectivity.py'),
                str(root), str(root / 'new-report.json')], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Occupancy hash mismatch', result.stderr)
            self.assertFalse((root / 'new-report.json').exists())

    def test_cli_preserves_both_exact_zero_boundary_conventions(self):
        shape, primary = hollow_cube()
        _, sensitivity = hollow_cube(tunnel=True)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            metadata = {
                'status': 'native_sampling_passed_not_topology_qualification',
                'shape_xyz': shape, 'sample_spacing_mm': 1.0, 'sample_phase': 0.371,
                'native_voxel_mm': 0.3, 'VDB_sha256': None, 'source_body_STL_sha256': None,
                'enclosure_bounds_private': {}, 'overlap_exact_zero_both_fields_samples': 1,
                'primary_boundary_convention': 'exact zero belongs to material',
                'sensitivity_boundary_convention': 'exact zero belongs to void',
                'occupancy_sha256': hashlib.sha256(primary).hexdigest(),
                'zero_as_void_occupancy_sha256': hashlib.sha256(sensitivity).hexdigest(),
            }
            (root / 'sampling-report.json').write_text(json.dumps(metadata))
            (root / 'void-occupancy.bin').write_bytes(primary)
            (root / 'void-occupancy-zero-as-void.bin').write_bytes(sensitivity)
            result = subprocess.run([sys.executable, '-B', str(SOURCE / 'connectivity.py'),
                str(root), str(root / 'new-report.json')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((root / 'new-report.json').read_text())
            self.assertEqual(report['shared_exact_zero_samples'], 1)
            self.assertEqual([r['isolated_sample_count'] for r in report['results']], [27, 27])
            self.assertEqual([r['isolated_sample_count'] for r in report['zero_as_void_sensitivity_results']], [0, 0])
            self.assertFalse(report['continuous_geometric_connectivity_proved'])


if __name__ == '__main__':
    unittest.main()
