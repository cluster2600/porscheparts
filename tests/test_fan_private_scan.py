"""Reject malformed input and preserve holes in scan diagnostics."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import sys
from _deps import require_modules

SOURCE = Path(__file__).resolve().parents[1] / "twins/993-engine-cooling-fan-system-f0/source/audit_private_scan.py"


class PrivateScanTests(unittest.TestCase):
    def setUp(self):
        require_modules("numpy")
        spec = importlib.util.spec_from_file_location("scan_audit", SOURCE)
        self.audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.audit)

    def run_obj(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.obj"
            path.write_text(text)
            before = path.read_bytes()
            report = self.audit.audit(path)
            self.assertEqual(path.read_bytes(), before)
            return report

    def test_open_triangle_stays_open_and_unqualified(self):
        report = self.run_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nf -3 -2 -1\n")
        self.assertEqual(report["boundary_edges"], 3)
        self.assertFalse(report["watertight_edge_topology"])
        self.assertFalse(report["solver_ready"])
        self.assertIsNone(report["units"])

    def test_closed_tetrahedron_does_not_establish_identity(self):
        report = self.run_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 3 2\nf 1 2 4\nf 2 3 4\nf 3 1 4\n")
        self.assertTrue(report["watertight_edge_topology"])
        self.assertEqual(report["inconsistent_two_face_edges"], 0)
        self.assertFalse(report["identity_verified"])
        self.assertFalse(report["solver_ready"])

    def test_invalid_index_and_nonfinite_coordinates_rejected(self):
        for text in ["v 0 0 0\nv 1 0 0\nv 0 1 0\nf 0 2 3\n",
                     "v nan 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n",
                     "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 4\n"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.run_obj(text)

    def test_private_normalization_is_rigid_and_only_removes_zero_area(self):
        import numpy as np
        sys.path.insert(0, str(SOURCE.parent))
        try:
            from prepare_private_scan import normalize
            vertices = np.asarray([[10., 2, 30], [12., 2, 30], [10., 3, 30], [10., 2, 34]])
            faces = np.asarray([[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3], [0, 0, 1]])
            original = vertices.copy()
            pose, kept, report = normalize(vertices, faces)
            self.assertTrue(np.array_equal(vertices, original))
            self.assertTrue(np.array_equal(kept, faces[:4]))
            self.assertEqual(report["removed_face_indices_zero_based"], [4])
            self.assertTrue(np.allclose(np.linalg.norm(pose[:, None] - pose[None, :], axis=2),
                                        np.linalg.norm(vertices[:, None] - vertices[None, :], axis=2)))
            self.assertFalse(report["hole_filling_executed"])
            self.assertFalse(report["component_registration_executed"])
            self.assertFalse(report["solver_ready"])
        finally:
            sys.path.remove(str(SOURCE.parent))


if __name__ == "__main__":
    unittest.main()
