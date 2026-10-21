"""Material support connections require actual positive intersections."""
from pathlib import Path
import sys
import tempfile
import shutil
import subprocess
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0, str(SOURCE))
try:
    import numpy as np
    from material_connections import connected_material
except ImportError:
    np = None


@unittest.skipIf(np is None, 'Native support runtime unavailable')
class MaterialConnectionTests(unittest.TestCase):
    def run_groups(self, rectangles, contacts):
        vertices, faces, groups = [], [], []
        for i, (rectangle, contact) in enumerate(zip(rectangles, contacts)):
            offset = len(vertices)
            vertices.extend(rectangle)
            faces.extend([[offset, offset+1, offset+2], [offset, offset+2, offset+3]])
            groups.append(dict(id=str(i), face_range=[2*i, 2*i+2],
                upper_contact_trace_mm=contact[0], lower_contact_trace_mm=contact[1]))
        return connected_material(np.array(vertices, dtype=np.float64),
                                  np.array(faces, dtype=np.int64), groups)

    def test_perpendicular_positive_length_anchors_an_island(self):
        first = [[0, 0, 0], [0, 2, 0], [0, 2, 2], [0, 0, 2]]
        second = [[-1, 1, 0], [1, 1, 0], [1, 1, 2], [-1, 1, 2]]
        result = self.run_groups([first, second], [(1, 1), (0, 0)])
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(len(result['components']), 1)
        self.assertEqual(len(result['positive_intersection_witnesses']), 1)

    def test_point_contact_does_not_anchor(self):
        first = [[0, 0, 0], [0, 2, 0], [0, 2, 2], [0, 0, 2]]
        second = [[0, 2, 2], [1, 2, 2], [1, 2, 3], [0, 2, 3]]
        self.assertEqual(self.run_groups([first, second], [(1, 1), (0, 0)])['status'], 'rejected')

    def test_coplanar_area_anchors_but_only_edge_does_not(self):
        first = [[0, 0, 0], [0, 2, 0], [0, 2, 2], [0, 0, 2]]
        overlapping = [[0, 1, 0], [0, 3, 0], [0, 3, 2], [0, 1, 2]]
        touching = [[0, 2, 0], [0, 3, 0], [0, 3, 2], [0, 2, 2]]
        self.assertEqual(self.run_groups([first, overlapping], [(1, 1), (0, 0)])['status'], 'passed')
        self.assertEqual(self.run_groups([first, touching], [(1, 1), (0, 0)])['status'], 'rejected')

    def test_one_ulp_gap_remains_disconnected(self):
        first = [[0, 0, 0], [0, 2, 0], [0, 2, 2], [0, 0, 2]]
        gap = np.nextafter(0., 1.)
        second = [[gap, 1, 0], [1, 1, 0], [1, 1, 2], [gap, 1, 2]]
        self.assertEqual(self.run_groups([first, second], [(1, 1), (0, 0)])['status'], 'rejected')

    def test_disconnected_faces_cannot_share_group_contact_flags(self):
        vertices = np.array([[0, 0, 0], [0, 1, 0], [0, 0, 1],
                             [0, 2, 0], [0, 3, 0], [0, 2, 1]], dtype=np.float64)
        faces = np.array([[0, 1, 2], [3, 4, 5]], dtype=np.int64)
        groups = [dict(id='both', face_range=[0, 2], upper_contact_trace_mm=1, lower_contact_trace_mm=1)]
        result = connected_material(vertices, faces, groups)
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['internal_connectivity'][0]['remaining_components'], 2)

    def test_face_omission_is_refused(self):
        vertices = np.array([[0, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64)
        with self.assertRaisesRegex(ValueError, 'partition'):
            connected_material(vertices, np.array([[0, 1, 2]]),
                [dict(id='bad', face_range=[1, 2], upper_contact_trace_mm=1, lower_contact_trace_mm=1)])

    def test_zero_area_singleton_cannot_inherit_contacts(self):
        vertices = np.array([[0, 0, 0], [1, 1, 1], [2, 2, 2]], dtype=np.float64)
        with self.assertRaisesRegex(ValueError, 'zero area'):
            connected_material(vertices, np.array([[0, 1, 2]]),
                [dict(id='null', face_range=[0, 1], upper_contact_trace_mm=1, lower_contact_trace_mm=1)])

    def test_tiny_nonzero_triangle_uses_exact_fallback(self):
        vertices = np.array([[0, 0, 0], [1e-200, 0, 0], [0, 1e-200, 0]], dtype=np.float64)
        result = connected_material(vertices, np.array([[0, 1, 2]]),
            [dict(id='tiny', face_range=[0, 1], upper_contact_trace_mm=1, lower_contact_trace_mm=1)])
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['exact_degeneracy_fallbacks'], 1)

    def test_flat_source_snapshot_can_load_sibling_classifier(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy2(SOURCE/'material_connections.py', root/'material_connections.py')
            shutil.copy2(SOURCE.parent/'design-20261016/classify_mesh_contacts.py', root/'classify_mesh_contacts.py')
            result = subprocess.run([sys.executable, '-B', '-c',
                'import material_connections as m; assert m.CLASSIFIER.parent == m.Path.cwd()'],
                cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
