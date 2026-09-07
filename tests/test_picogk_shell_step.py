"""Synthetic OCCT region/containment witnesses, independent of private CAD."""
import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/picogk'
sys.path.insert(0, str(SOURCE))
import audit_shell_against_step as audit


@unittest.skipUnless(importlib.util.find_spec('OCP'), 'optional OCCT runtime')
class PicoGKShellSTEPTests(unittest.TestCase):
    def test_negative_tetrahedron_becomes_separate_positive_diagnostic_region(self):
        vertices = [[0., 0., 0.], [.1, 0., 0.], [0., .1, 0.], [0., 0., .1]]
        faces = [[0, 1, 2], [0, 3, 1], [0, 2, 3], [1, 3, 2]]
        triangles = [[vertices[index] for index in face] for face in faces]
        region = audit.region_from_triangles(triangles)
        self.assertTrue(audit.valid_shape(region))
        self.assertEqual(audit.shape_counts(region)['solids'], 1)
        self.assertEqual(audit.shape_counts(region)['faces'], 4)
        self.assertAlmostEqual(audit.shape_volume(region), .001 / 6)

    def test_boolean_whole_region_inside_outside_and_crossing(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.gp import gp_Pnt
        master = BRepPrimAPI_MakeBox(gp_Pnt(-1., -1., -1.), 2., 2., 2.).Solid()
        for x, contained, outside_fraction in ((0., True, 0.), (2., False, 1.), (.9, False, .5)):
            with self.subTest(x=x):
                region = BRepPrimAPI_MakeBox(gp_Pnt(x, 0., 0.), .2, .2, .2).Solid()
                report = audit.boolean_partition(region, master)
                self.assertTrue(report['partition_volume_crosscheck_passed'])
                self.assertEqual(report['full_region_inside_master_supported_under_OCCT_tolerances'], contained)
                self.assertEqual(report['region_minus_master_topologically_empty'], contained)
                self.assertAlmostEqual(report['region_minus_master']['signed_volume'] / .008, outside_fraction)
                self.assertFalse(report['geometrically_exact_or_physical_containment_certified'])


if __name__ == '__main__':
    unittest.main()
