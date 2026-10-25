"""Boundary preservation cannot be inferred from matching counts or point sets."""
import importlib.util
import json
from pathlib import Path
import unittest
import numpy as np

SOURCE = Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/optimize_tetrahedra_gmsh.py'
spec = importlib.util.spec_from_file_location('carrier_optimizer', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BoundaryIdentityTests(unittest.TestCase):
    def test_doubled_volume_is_refused_before_the_extracted_candidate_is_admitted(self):
        evidence = SOURCE.parents[5]/'docs/reports/carrier-convergence-20261022/evidence/mesh-quality-20261025'
        raw = json.loads((evidence/'carrier-Netgen-exact-002/assessment.json').read_text())
        candidate = json.loads((evidence/'carrier-Netgen-appended-exact-001/assessment.json').read_text())
        self.assertEqual(raw['status'], 'volume_screen_refused')
        self.assertGreater(raw['indexed_connectivity']['nonmanifold_faces'], 0)
        self.assertEqual(candidate['status'], 'full_exact_orientation_and_indexed_volume_screens_passed')
        self.assertEqual(candidate['exact_orientation']['negative'], 0)
        self.assertEqual(candidate['exact_orientation']['zero'], 0)
        self.assertTrue(candidate['indexed_connectivity']['boundary_matches'])
        self.assertAlmostEqual(raw['exact_orientation']['total_signed_volume_mm3_float'],
                               2*candidate['exact_orientation']['total_signed_volume_mm3_float'], places=8)
        self.assertFalse(candidate['mechanical_mesh_admitted'])

    def test_reindexing_and_reversed_faces_preserve_geometry(self):
        vertices = np.array([[0., 0, 0], [1., 0, 0], [1., 1, 0], [0., 1, 0]])
        faces = np.array([[0, 1, 2], [0, 2, 3]])
        permutation = np.array([3, 1, 0, 2])
        inverse = np.argsort(permutation)
        self.assertEqual(module.boundary_coordinates(vertices, faces),
                         module.boundary_coordinates(vertices[permutation], inverse[faces[::-1, ::-1]]))

    def test_same_counts_with_changed_diagonal_or_moved_point_are_refused(self):
        vertices = np.array([[0., 0, 0], [1., 0, 0], [1., 1, 0], [0., 1, 0]])
        faces = np.array([[0, 1, 2], [0, 2, 3]])
        baseline = module.boundary_coordinates(vertices, faces)
        self.assertNotEqual(baseline, module.boundary_coordinates(vertices, np.array([[0, 1, 3], [1, 2, 3]])))
        changed = vertices.copy()
        changed[0, 2] = 1e-12
        self.assertNotEqual(baseline, module.boundary_coordinates(changed, faces))

    def test_appended_extraction_requires_every_original_cell_and_coordinate(self):
        spec = importlib.util.spec_from_file_location('netgen_extraction', SOURCE.with_name('extract_appended_netgen.py'))
        extraction = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(extraction)
        v = np.array([[0., 0, 0], [1., 0, 0], [0, 1., 0], [0, 0, 1.]])
        t = np.array([[0, 1, 2, 3]])
        f = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
        combined = np.vstack([t, t])
        result = extraction.extract((v, t, f), (v.copy(), combined, f.copy()))
        np.testing.assert_array_equal(result[1], t)
        changed = v.copy()
        changed[0, 0] = 1e-12
        with self.assertRaises(ValueError):
            extraction.extract((v, t, f), (changed, combined, f))
        with self.assertRaises(ValueError):
            extraction.extract((v, t, f), (v, combined[:, ::-1], f))


if __name__ == '__main__':
    unittest.main()
