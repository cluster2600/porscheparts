import importlib.util
from pathlib import Path
import tempfile
import unittest

try:
    import numpy as np
    import trimesh
    import scipy
except ImportError:
    np = None


@unittest.skipIf(np is None, "scan audit requires numpy, scipy and trimesh")
class FaithfulScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "audit", Path(__file__).parents[1] / "scripts/audit_935_faithful_scan.py")
        cls.audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.audit)

    def test_closed_and_missing_face(self):
        mesh = trimesh.creation.box()
        closed, _, _, _ = self.audit.inspect(mesh)
        self.assertTrue(closed["watertight_edge_incidence"])
        opened = trimesh.Trimesh(mesh.vertices, mesh.faces[:-1], process=False)
        report, edges, _, _ = self.audit.inspect(opened)
        self.assertEqual(report["boundary_edges"], 3)
        self.assertEqual(len(edges), 3)

    def test_export_preserves_surface_without_closing(self):
        mesh = trimesh.creation.box()
        mesh = trimesh.Trimesh(mesh.vertices + 0.123456789012345,
                               mesh.faces[:-1], process=False)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "observed.obj"
            result = self.audit.write_observed_component(
                mesh, np.ones(len(mesh.faces), dtype=bool), target)
            self.assertTrue(result["float64_roundtrip_exact"])
            restored = trimesh.load_mesh(target, process=False)
            self.assertEqual(self.audit.inspect(restored)[0]["boundary_edges"], 3)
            with self.assertRaises(FileExistsError):
                self.audit.write_observed_component(mesh, np.ones(len(mesh.faces), dtype=bool), target)

    def test_bad_source_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.obj"
            source.write_text("not the source")
            output = Path(directory) / "result"
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                self.audit.run(source, output, {})
            self.assertFalse(output.exists())

    def test_bidirectional_deviation_detects_translation(self):
        if importlib.util.find_spec("rtree") is None:
            self.skipTest("rtree required for surface-distance check")
        a = trimesh.creation.box()
        same, _ = self.audit.sampled_deviation(a, a, 100)
        self.assertLess(same["reference_to_candidate"]["sample_max_source_units"], 1e-12)
        b = a.copy()
        b.apply_translation([3, 0, 0])
        shifted, _ = self.audit.sampled_deviation(a, b, 100)
        for direction in ("reference_to_candidate", "candidate_to_reference"):
            self.assertGreaterEqual(shifted[direction]["median_source_units"], 2)


if __name__ == "__main__":
    unittest.main()
