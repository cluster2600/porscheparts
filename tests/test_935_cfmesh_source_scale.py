"""Regression for the coordinate scale used by the cfMesh distance query."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

path = (Path(__file__).resolve().parents[1] / 'twins/935-horizontal-cooling-system-f0/source'
        / 'cfmesh-face-location-20261104/reverse_triangle_source_scale.py')
spec = importlib.util.spec_from_file_location('reverse_triangle_source_scale', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourceScaleDistanceTest(unittest.TestCase):
    def test_wall_is_converted_before_query(self):
        triangle = np.array([[0., 0., 0.], [.2, .6, 0.], [.2, .6, .7]])
        normal = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
        normal /= np.linalg.norm(normal)
        point = triangle.mean(axis=0) + .0004 * normal
        source = SimpleNamespace(triangles_center=point[None, :])
        wall = SimpleNamespace(vertices=triangle / 1000, faces=np.array([[0, 1, 2]]))
        observed = []

        def mesh(vertices, faces, process):
            self.assertFalse(process)
            np.testing.assert_array_equal(faces, wall.faces)
            return SimpleNamespace(vertices=vertices)

        def closest(target, points):
            observed.append(True)
            np.testing.assert_allclose(target.vertices, triangle, atol=1e-15)
            np.testing.assert_allclose(points[0], point, atol=1e-15)
            # The projected point is the triangle centroid, so its perpendicular
            # plane distance is also its analytically known triangle distance.
            distance = np.abs((points - target.vertices.mean(axis=0)) @ normal)
            return points, distance, np.zeros(len(points), dtype=int)

        fake = SimpleNamespace(Trimesh=mesh, proximity=SimpleNamespace(closest_point=closest))
        with patch.dict(sys.modules, {'trimesh': fake}):
            result = module.sampled_distances(source, wall, np.array([0]))
        self.assertEqual(len(observed), 1)
        np.testing.assert_allclose(result, [.0004], rtol=0, atol=1e-12)


if __name__ == '__main__':
    unittest.main()
