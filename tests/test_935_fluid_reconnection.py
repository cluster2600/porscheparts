from pathlib import Path
import sys
import unittest
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0, str(SOURCE))
try:
    import numpy as np
    import reconnect_fluid_tetrahedra as repair
    from import_conforming_volume import exact_orientation
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'Requires NumPy')
class ReconnectionTests(unittest.TestCase):
    def test_checkpoint_binds_sources_and_does_not_qualify_the_mesh(self):
        record=json.loads((ROOT/'docs/research/935-horizontal-cooling/fluid-topology-continuation-20261022.json').read_text())
        for name,digest in record['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest)
        self.assertTrue(all(value is False for value in record['scope'].values()))
        cases=record['native_cases']
        self.assertEqual(len(cases),6)
        self.assertEqual(len({row['native_points_sha256'] for row in cases.values()}),1)
        for row in cases.values():
            self.assertTrue(row['all_cell_orientations_positive'])
            self.assertTrue(row['exact_volume_equal_to_PLC'])
            self.assertTrue(row['complete_boundary_coordinate_triangle_marker_bijection'])
            self.assertTrue(row['original_quality_dictionary_unchanged'])
            self.assertFalse(row['extended_mesh_quality_passed'])
            self.assertEqual(row['failed_native_checks'],4)
        self.assertLess(cases['three_to_two_3']['small_determinant_cells'],cases['baseline']['small_determinant_cells'])

    def fixture(self):
        return np.array([[1.,0,0],[0,1,0],[-1,-1,0],[0,0,1],[0,0,-1]]), np.array([[0,1,2,3],[0,2,1,4]])

    def test_convex_flip_has_exact_unit_volume_and_six_original_outer_faces(self):
        vertices, cells = self.fixture()
        result, edge = repair.convex_flip(vertices, cells, [0,1,2])
        self.assertEqual(edge, (3,4))
        self.assertEqual(result.shape, (3,4))
        proof = exact_orientation(vertices,result)
        self.assertEqual(proof['signed_volume_exact'], '1')
        self.assertEqual(proof['negative'], 0)
        self.assertEqual(proof['zero'], 0)
        expected = np.array([[0,1,3],[0,1,4],[0,2,3],[0,2,4],[1,2,3],[1,2,4]])
        np.testing.assert_array_equal(repair.outer_faces(result), expected)

    def test_concave_and_zero_volume_proposals_are_refused(self):
        vertices, cells = self.fixture()
        for x in (2.,4.):
            vertices[4] = [x,0,-1]
            self.assertIsNone(repair.convex_flip(vertices,cells,[0,1,2]))
        with self.assertRaises(ValueError):
            repair.convex_flip(vertices,cells[:,[1,0,2,3]],[0,1,2])

    def test_face_ownership_counts_the_shared_face_once(self):
        _, cells = self.fixture()
        faces, owners, ids = repair.incidence(cells)
        self.assertEqual(len(faces), 7)
        shared = np.flatnonzero(owners[:,1] >= 0)
        self.assertEqual(len(shared), 1)
        np.testing.assert_array_equal(faces[shared[0]], [0,1,2])
        self.assertEqual(set(owners[shared[0]]), {0,1})
        self.assertEqual(ids.shape, (2,4))

    def test_positive_geometric_flip_can_still_worsen_FV_rank(self):
        vertices, cells = self.fixture()
        children, _ = repair.convex_flip(vertices,cells,[0,1,2])
        outside = {tuple(face):-1 for face in repair.outer_faces(cells)}
        old = repair.patch_quality(vertices,cells,outside,np.empty((0,3)),np.empty(0))
        new = repair.patch_quality(vertices,children,outside,np.empty((0,3)),np.empty(0))
        self.assertEqual(old[0][-1], 2)
        self.assertEqual(new[0][-1], 3)
        self.assertFalse(repair.improves(old,new))

    def test_each_failure_count_and_severity_must_not_worsen(self):
        before = (np.ones(5,dtype=int), np.ones(5))
        self.assertTrue(repair.improves(before,(np.zeros(5,dtype=int),np.zeros(5))))
        for column in range(5):
            count = np.zeros(5,dtype=int); count[column] = 2
            self.assertFalse(repair.improves(before,(count,np.zeros(5))))
            severity = np.zeros(5); severity[column] = 1.01
            self.assertFalse(repair.improves(before,(np.zeros(5,dtype=int),severity)))

    def test_complete_sweep_preserves_mesh_when_every_flip_is_refused(self):
        vertices, cells = self.fixture()
        before = cells.copy()
        result, report, locations = repair.reconnect(vertices,cells)
        np.testing.assert_array_equal(result,before)
        np.testing.assert_array_equal(cells,before)
        self.assertEqual(locations.shape, (0,3))
        self.assertEqual(report['decision_counts'].get('accepted_disjoint_patch',0), 0)
        self.assertEqual(report['input_cells'], report['output_cells'])


if __name__ == '__main__':
    unittest.main()
