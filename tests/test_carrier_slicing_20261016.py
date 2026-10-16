"""Native sections preserve holes, open-section refusal, coordinates and exposure order."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'parts/993-eng-carrier-0001/source/process-slicing-20261016'
sys.path.insert(0, str(SOURCE))
try:
    import numpy as np
    import trimesh
    import layers
    from benchmark import equal_result, HISTORICAL
    from parallel_layers import ParallelLayers
    spec = importlib.util.spec_from_file_location('carrier_slicing_reference', HISTORICAL)
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
except ImportError:
    reference = None


@unittest.skipIf(reference is None, 'Pinned PySLM native runtime required')
class CarrierSlicingTests(unittest.TestCase):
    def test_holes_and_native_boundary_cases_match_without_reordering(self):
        mesh = trimesh.creation.annulus(r_min=2, r_max=5, height=4, sections=32)
        part = SimpleNamespace(geometry=mesh)
        bounds = layers.face_z_bounds(mesh)
        for z in (-2.01, -2, -2 + trimesh.constants.tol.merge / 2, -.13, 0, 1.99, 2, 2.01):
            with self.subTest(z=z):
                old = reference.layer_geometry(part, z)
                new = layers.layer_geometry(part, z, reference.PARAMETERS, bounds)
                self.assertTrue(equal_result(old, new))
        middle = layers.layer_geometry(part, 0, reference.PARAMETERS, bounds)
        self.assertEqual(len(middle[0]), 2)
        self.assertGreater(len(middle[2]), 0)

    def test_open_section_is_refused_by_both_paths(self):
        box = trimesh.creation.box(extents=[10, 10, 4])
        keep = box.face_normals[:, 0] > -.9
        mesh = trimesh.Trimesh(vertices=box.vertices, faces=box.faces[keep], process=False)
        part = SimpleNamespace(geometry=mesh)
        with self.assertRaisesRegex(ValueError, 'Open planar section'):
            reference.layer_geometry(part, 0)
        with self.assertRaisesRegex(ValueError, 'Open planar section'):
            layers.layer_geometry(part, 0, reference.PARAMETERS, layers.face_z_bounds(mesh))

    def test_worker_group_preserves_exact_order_and_closes(self):
        mesh = trimesh.creation.annulus(r_min=2, r_max=5, height=4, sections=32)
        part = SimpleNamespace(geometry=mesh)
        heights = [-1.7, -.2, .3, 1.8]
        expected = [reference.layer_geometry(part, z) for z in heights]
        with ParallelLayers(reference.PARAMETERS, workers=2, heights=heights) as calculate:
            for z, old in zip(heights, expected):
                self.assertTrue(equal_result(old, calculate(part, z)))
        result = calculate.receipt()
        self.assertTrue(result['worker_group_closed'])
        self.assertEqual(result['completed_layers'], len(heights))

    def test_invalid_midplane_or_face_bounds_is_refused(self):
        mesh = trimesh.creation.box()
        with self.assertRaises(ValueError):
            layers.section(mesh, float('nan'), layers.face_z_bounds(mesh))
        with self.assertRaises(ValueError):
            layers.section(mesh, 0, np.zeros((1, 2)))
        with self.assertRaises(ValueError):
            ParallelLayers(reference.PARAMETERS, workers=3)


if __name__ == '__main__':
    unittest.main()
