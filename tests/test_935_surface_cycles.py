"""Check cycle topology against analytic surfaces and reject pinched/open inputs."""
from pathlib import Path
import sys
import unittest

try:
    import numpy as np
    import scipy
except ImportError:
    np = None

SOURCE = Path(__file__).resolve().parents[1]/'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0, str(SOURCE))
if np is not None:
    from locate_surface_cycles import surface_cycles


@unittest.skipIf(np is None, 'NumPy/SciPy unavailable')
class SurfaceCycleTests(unittest.TestCase):
    def sphere(self):
        v = np.array([[1., 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]])
        f = np.array([[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4],
                      [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]])
        return v, f

    def test_sphere_has_no_homology_cycles_and_input_stays_exact(self):
        v, f = self.sphere(); before = (v.copy(), f.copy())
        cycles, report = surface_cycles(v, f)
        self.assertEqual(cycles, [])
        self.assertEqual((report['Euler_characteristic'], report['genus']), (2, 0))
        np.testing.assert_array_equal(v, before[0]); np.testing.assert_array_equal(f, before[1])

    def torus(self, m, n):
        theta, phi = np.meshgrid(np.arange(m)*2*np.pi/m, np.arange(n)*2*np.pi/n, indexing='ij')
        v = np.column_stack(((3+np.cos(phi)).ravel()*np.cos(theta).ravel(),
                             (3+np.cos(phi)).ravel()*np.sin(theta).ravel(), np.sin(phi).ravel()))
        f = []
        for i in range(m):
            for j in range(n):
                a, b, c, d = i*n+j, ((i+1)%m)*n+j, ((i+1)%m)*n+(j+1)%n, i*n+(j+1)%n
                f.extend([[a, b, c], [a, c, d]])
        return v, np.array(f)

    def test_large_dual_graph_preserves_two_independent_torus_cycles(self):
        v, f = self.torus(160, 160)
        cycles, report = surface_cycles(v, f)
        self.assertEqual((report['genus'], len(cycles)), (1, 2))

    def test_torus_cycles_have_independent_integer_windings_and_use_real_edges(self):
        v, f = self.torus(16, 12)
        cycles, report = surface_cycles(v, f)
        self.assertEqual((report['genus'], len(cycles)), (1, 2))
        unsigned_cycles, unsigned_report = surface_cycles(v, f.astype(np.uint8))
        self.assertEqual(unsigned_report, report)
        for signed, unsigned in zip(cycles, unsigned_cycles):
            np.testing.assert_array_equal(signed, unsigned)
        edges = {tuple(sorted(e)) for face in f for e in zip(face, np.roll(face, -1))}
        winding = []
        for cycle in cycles:
            self.assertEqual(cycle[0], cycle[-1])
            self.assertTrue(all(tuple(sorted(e)) in edges for e in zip(cycle[:-1], cycle[1:])))
            p = v[cycle]
            angles = [np.arctan2(p[:, 1], p[:, 0]), np.arctan2(p[:, 2], np.linalg.norm(p[:, :2], axis=1)-3)]
            winding.append([np.unwrap(angle)[-1]/(2*np.pi)-np.unwrap(angle)[0]/(2*np.pi) for angle in angles])
        np.testing.assert_allclose(winding, np.rint(winding), rtol=0, atol=1e-12)
        self.assertAlmostEqual(abs(np.linalg.det(winding)), 1)

    def test_open_flipped_duplicated_and_disconnected_surfaces_are_refused(self):
        v, f = self.sphere(); flipped = f.copy(); flipped[0] = flipped[0, ::-1]
        for points, triangles in [(v, f[:-1]), (v, flipped), (v, np.vstack((f, f[0]))),
                                  (np.vstack((v, v+[4, 0, 0])), np.vstack((f, f+len(v))))]:
            with self.subTest(triangles=len(triangles)), self.assertRaises(ValueError):
                surface_cycles(points, triangles)

    def test_vertex_pinch_is_refused_even_when_all_edges_have_two_faces(self):
        v, f = self.sphere()
        second = v+[2, 0, 0]
        points = np.vstack((v, second[1:]))
        mapping = np.r_[0, np.arange(len(v), len(points))]
        with self.assertRaisesRegex(ValueError, 'one circular link'):
            surface_cycles(points, np.vstack((f, mapping[f])))

    def test_nonfinite_unused_noninteger_and_out_of_range_inputs_are_refused(self):
        v, f = self.sphere(); bad = v.copy(); bad[0, 0] = np.nan
        for points, triangles in [(bad, f), (np.vstack((v, [[4, 4, 4]])), f), (v, f+.1), (v, f+len(v))]:
            with self.subTest(points=len(points)), self.assertRaises(ValueError):
                surface_cycles(points, triangles)


if __name__ == '__main__':
    unittest.main()
