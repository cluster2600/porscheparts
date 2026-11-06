"""Exercise the precision handoff without optional native geometry runtimes."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

try:
    import numpy as np
except ImportError:
    np = None

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/transfer_void_to_float32.py"


@unittest.skipIf(np is None, "numpy unavailable")
class CarrierFloat32TransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("carrier_float32_transfer", SOURCE)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vertices = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
        self.faces = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])

    def run_transfer(self, vertices, faces, origin=(0., 0., 0.)):
        source = self.root / "source.npz"
        np.savez(source, vertices=vertices, triangles=faces)
        return self.module.transfer(source, self.root/"output", np.array(origin))

    def assert_tetra_volume(self):
        z = np.load(self.root/"output/candidate.npz")
        v, f = z["vertices"], z["triangles"]
        t = v[f]-v[0]
        volume = np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum()/6
        self.assertAlmostEqual(volume, 1/6, places=14)

    def test_short_edge_quantization_preserves_tetrahedron(self):
        v = self.vertices + [75., 30., 1.]
        v = np.vstack([v, v[0]+[1e-9, 0., 0.]])
        f = np.array([[0, 2, 4], [4, 2, 1], [0, 4, 3], [4, 1, 3], *self.faces[2:]])
        report = self.run_transfer(v, f, (74., 29., 0.))
        self.assertEqual(report["removed_repeated_index_faces"], 2)
        self.assertTrue(report["local_to_world_addition_exact"])
        self.assertEqual(report["retained_faces"], 4)
        self.assert_tetra_volume()

    def test_exact_collinear_partition_preserves_volume(self):
        v = np.vstack([self.vertices, [0., .5, 0.]])
        f = np.array([[0, 4, 1], [4, 2, 1], *self.faces[1:], [0, 2, 4]])
        report = self.run_transfer(v, f)
        self.assertEqual(len(report["collinear_partition_flips"]), 1)
        self.assertEqual(report["cleanup_complete_geometric_change_bound_mm"], 0)
        self.assert_tetra_volume()

    def test_uncovered_zero_face_is_refused(self):
        v = np.vstack([self.vertices, [3., 3., 3.], [4., 3., 3.]])
        with self.assertRaisesRegex(ValueError, "not covered"):
            self.run_transfer(v, np.vstack([self.faces, [4, 4, 5]]))

    def test_open_surface_is_refused(self):
        with self.assertRaisesRegex(ValueError, "edge contract"):
            self.run_transfer(self.vertices, self.faces[:-1])

    def test_nonmanifold_positive_face_is_refused(self):
        with self.assertRaisesRegex(ValueError, "edge contract"):
            self.run_transfer(self.vertices, np.vstack([self.faces, self.faces[0]]))

    def test_small_translation_lost_at_large_coordinates_is_refused(self):
        with self.assertRaisesRegex(ValueError, "translation is not exact"):
            self.run_transfer(self.vertices*1e20, self.faces, (1., 0., 0.))

    def test_nonfinite_origin_is_refused(self):
        with self.assertRaisesRegex(ValueError, "origin"):
            self.run_transfer(self.vertices, self.faces, (float("nan"), 0., 0.))

    def test_nonfinite_input_is_refused(self):
        self.vertices[0, 0] = float("inf")
        with self.assertRaisesRegex(ValueError, "vertices"):
            self.run_transfer(self.vertices, self.faces)

    def test_existing_output_is_preserved(self):
        (self.root/"output").mkdir()
        marker = self.root/"output/marker"
        marker.write_text("preserve")
        with self.assertRaisesRegex(ValueError, "exists"):
            self.run_transfer(self.vertices, self.faces)
        self.assertEqual(marker.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
