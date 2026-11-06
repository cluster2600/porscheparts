"""Analytical sign controls and malformed-boundary refusal for crease diagnostics."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / 'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/audit_surface_features.py'
SPEC = importlib.util.spec_from_file_location('carrier_surface_features', SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def prism(outline, top):
    vertices = np.array([[x, y, z] for z in [0, 1] for x, y in outline], dtype=float)
    count = len(outline)
    faces = [list(reversed(face)) for face in top]
    faces += [[i + count for i in face] for face in top]
    for i in range(count):
        j = (i + 1) % count
        faces += [[i, j, j + count], [i, j + count, i + count]]
    return vertices, np.array(faces)


class SurfaceFeaturesTest(unittest.TestCase):
    def test_convex_cube_has_no_reentrant_edges(self):
        v, f = prism([(0, 0), (1, 0), (1, 1), (0, 1)], [(0, 1, 2), (0, 2, 3)])
        result = MODULE.audit(v, f)
        self.assertEqual(result['reentrant_edges_above_degrees']['45'], 0)
        self.assertEqual(result['convex_edges_above_45_degrees'], 12)

    def test_extruded_l_has_one_unit_reentrant_edge(self):
        v, f = prism([(0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)],
                     [(0, 1, 3), (1, 2, 3), (0, 3, 5), (3, 4, 5)])
        result = MODULE.audit(v, f)
        self.assertEqual(result['reentrant_edges_above_degrees']['45'], 1)
        worst = result['most_reentrant_edges'][0]
        self.assertAlmostEqual(worst['normal_turn_degrees'], -90)
        self.assertAlmostEqual(worst['length_mm'], 1)
        self.assertEqual(worst['midpoint_mm'], [1, 1, .5])
        self.assertFalse(result['singularity_proved'])

    def test_missing_face_is_refused(self):
        v, f = prism([(0, 0), (1, 0), (1, 1), (0, 1)], [(0, 1, 2), (0, 2, 3)])
        with self.assertRaisesRegex(ValueError, 'exactly two'):
            MODULE.audit(v, f[:-1])

    def test_reversed_single_face_is_refused(self):
        v, f = prism([(0, 0), (1, 0), (1, 1), (0, 1)], [(0, 1, 2), (0, 2, 3)])
        f[0] = f[0, ::-1]
        with self.assertRaisesRegex(ValueError, 'Opposite'):
            MODULE.audit(v, f)


if __name__ == '__main__':
    unittest.main()
