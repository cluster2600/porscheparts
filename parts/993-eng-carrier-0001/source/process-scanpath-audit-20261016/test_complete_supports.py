"""Every material group must occur in the actual exposures, even if tiny."""
import importlib.util
from pathlib import Path
import sys
import unittest

if any(importlib.util.find_spec(name) is None for name in ('numpy', 'trimesh', 'shapely')):
    raise unittest.SkipTest('Optional geometry runtime required')
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_support_scanpaths as base
from audit_complete_supports import group_witness, BASE_SHA256


class CompleteSupportAudit(unittest.TestCase):
    def test_group_between_layer_planes_is_not_silently_ignored(self):
        vertices = np.array([[0., 0., .04], [1., 0., .05], [0., 0., .05]])
        row = group_witness(vertices, np.array([[0, 1, 2]]),
            dict(id='between', face_range=[0, 1]), np.array([.03, .09]), lambda _: set())
        self.assertFalse(row['passed'])

    def test_group_witness_requires_its_real_encoded_vector(self):
        vertices = np.array([[0., 0., 0.], [1., 0., 1.], [2., 0., 0.]])
        faces = np.array([[0, 1, 2]])
        heights = np.array([.03, .09])
        expected = base.encode(base.triangle_section(vertices, .03))
        row = group_witness(vertices, faces, dict(id='real', face_range=[0, 1]), heights,
                            lambda layer: {expected} if layer == 0 else set())
        self.assertTrue(row['passed'])
        self.assertEqual(row['source_face'], 0)
        self.assertEqual(row['layer'], 0)
        self.assertFalse(group_witness(vertices, faces, dict(id='missing', face_range=[0, 1]),
                                       heights, lambda _: set())['passed'])

    def test_mandatory_base_source_stays_frozen(self):
        self.assertEqual(base.sha(base.__file__), BASE_SHA256)


if __name__ == '__main__':
    unittest.main()
