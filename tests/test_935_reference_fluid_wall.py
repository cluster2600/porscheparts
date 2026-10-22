from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0, str(SOURCE))
try:
    import numpy as np
    from import_conforming_volume import exact_orientation
    spec = importlib.util.spec_from_file_location('restore_reference_wall', SOURCE / 'reference-fluid-wall-study-20261022/restore-reference-edge-001.py')
    restore = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(restore)
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'Requires NumPy and SciPy')
class ReferenceWallConeTests(unittest.TestCase):
    def test_analytic_unit_cone_has_exact_unit_tetrahedron_volume(self):
        points = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
        target, proof = restore.cone(points, restore.base.FACE_NODES, [])
        self.assertEqual(Fraction(proof['signed_volume_exact']), Fraction(1, 6))
        self.assertEqual((proof['negative'], proof['zero'], proof['cells']), (0, 0, 4))
        self.assertTrue(np.all(target > 0))
        self.assertLess(target.sum(), 1)

    def test_translated_small_cone_preserves_exact_serialized_boundary_volume(self):
        points = np.array([.2, -.3, .4]) + .001 * np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
        _, proof = restore.cone(points, restore.base.FACE_NODES, [])
        parent = exact_orientation(points, np.array([[0, 1, 2, 3]]))
        self.assertEqual(Fraction(proof['signed_volume_exact']), Fraction(parent['signed_volume_exact']))
        self.assertEqual((proof['negative'], proof['zero']), (0, 0))

    def test_inverted_surface_is_refused(self):
        points = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
        with self.assertRaises(ValueError):
            restore.cone(points, restore.base.FACE_NODES[:, ::-1], [])

    def test_open_cavity_is_refused(self):
        points = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
        with self.assertRaises((ValueError, AssertionError)):
            restore.cone(points, restore.base.FACE_NODES[:-1], [])

    def test_zero_volume_cavity_is_refused(self):
        points = np.array([[0., 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]])
        with self.assertRaises(ValueError):
            restore.cone(points, restore.base.FACE_NODES, [])


class ReferenceWallCheckpointTests(unittest.TestCase):
    def test_executed_sources_remain_byte_identical(self):
        r = json.loads((ROOT / 'docs/research/935-horizontal-cooling/reference-fluid-wall-20261022.json').read_text())
        for name, expected in r['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)

    def test_exact_wall_identity_does_not_qualify_flow_or_physical_scope(self):
        r = json.loads((ROOT / 'docs/research/935-horizontal-cooling/reference-fluid-wall-20261022.json').read_text())
        self.assertTrue(r['new_boundary']['reference_surface_set_distance_exactly_zero'])
        self.assertEqual(r['new_boundary']['rotor_triangles'], 873444)
        self.assertEqual(r['volume']['tetrahedra'], 3685053)
        self.assertEqual((r['volume']['negative_exact_determinants'], r['volume']['zero_exact_determinants']), (0, 0))
        self.assertTrue(r['volume']['exact_PLC_volume_equal'])
        self.assertEqual(r['native']['failed_quality_checks'], 6)
        self.assertFalse(r['native']['full_quality_passed'])
        self.assertFalse(r['native']['CFD_executed'])
        for key in ['full_system_goal_complete', 'scale_verified', 'current_geometry_CFD_accepted', 'manufacturing_authorized', 'physical_validation']:
            self.assertFalse(r['scope'][key])


if __name__ == '__main__':
    unittest.main()
