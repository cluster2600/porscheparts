"""Synthetic evidence: recover circle geometry without inventing mechanical datums."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from _deps import require_modules

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/935-horizontal-cooling-system-f0/source/inspect_private_interfaces.py"


class InterfaceInspectionTests(unittest.TestCase):
    def setUp(self):
        require_modules("numpy", "scipy")
        import numpy as np
        self.np = np
        spec = importlib.util.spec_from_file_location("private_935_interfaces", SOURCE)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def circle(self, extent=2):
        np = self.np
        angle = np.linspace(0, extent * np.pi, 120, endpoint=False)
        u = np.asarray([1, 2, 3.]) / np.sqrt(14)
        v = np.asarray([2, -1, 0.]) / np.sqrt(5)
        return np.asarray([13, -7, 23]) + 6 * (np.cos(angle)[:, None] * u + np.sin(angle)[:, None] * v)

    def test_tilted_circle_recovered_without_physical_role(self):
        r = self.module.fit_circle(self.circle())
        self.assertTrue(r["candidate"])
        self.np.testing.assert_allclose(r["centre_source_units"], [13, -7, 23], atol=1e-9)
        self.assertAlmostEqual(r["radius_source_units"], 6)
        self.assertIsNone(r["functional_role"])
        self.assertFalse(r["independent_measurement_verified"])

    def test_partial_arc_cannot_become_a_hole_datum(self):
        r = self.module.fit_circle(self.circle(extent=1))
        self.assertFalse(r["candidate"])
        self.assertLess(r["angular_coverage_deg"], 190)

    def test_warped_ring_is_rejected(self):
        p = self.circle()
        normal = self.np.cross([1, 2, 3], [2, -1, 0]); normal = normal / self.np.linalg.norm(normal)
        p += 0.5 * self.np.cos(self.np.linspace(0, 4 * self.np.pi, len(p), endpoint=False))[:, None] * normal
        self.assertFalse(self.module.fit_circle(p)["candidate"])

    def test_invalid_and_collinear_points(self):
        np = self.np
        with self.assertRaises(ValueError):
            self.module.fit_circle(np.full((30, 3), np.nan))
        p = np.zeros((30, 3)); p[:, 0] = np.arange(30)
        self.assertEqual(self.module.fit_circle(p)["reason"], "collinear_or_coincident")

    def test_pinched_boundaries_remain_unclassified(self):
        np = self.np
        vertices = np.asarray([[0, 0, 0], [1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0.]])
        r = self.module.inspect(vertices, np.asarray([[0, 1, 2], [0, 3, 4]]))
        self.assertEqual(r["boundary_edges"], 6)
        self.assertEqual(r["features"][0]["reason"], "branched_boundary")
        self.assertFalse(r["hole_filling_executed"])

    def test_disconnected_scan_surfaces_are_not_registered_or_welded(self):
        np = self.np
        # Coincident coordinates with distinct source indices remain separate.
        p = np.asarray([[0, 0, 0], [1, 0, 0], [0, 1, 0]] * 2, dtype=float)
        before = p.copy()
        r = self.module.inspect(p, np.asarray([[0, 1, 2], [3, 4, 5]]))
        self.assertEqual(len(r["surface_components"]), 2)
        self.assertEqual(r["boundary_edges"], 6)
        np.testing.assert_array_equal(p, before)
        self.assertIsNone(r["assembly_transform"])
        self.assertFalse(r["scale_verified"])
        self.assertFalse(r["measured_datum_established"])
        self.assertFalse(r["solver_ready"])

    def test_hash_and_output_guards_preserve_existing_data(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "scan.obj"
            source.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            output = Path(directory) / "inspection"
            with self.assertRaises(ValueError):
                self.module.run(source, output, "0" * 64)
            self.assertFalse(output.exists())
            output.mkdir(); marker = output / "owner-data.txt"; marker.write_text("preserve")
            with self.assertRaises(ValueError):
                self.module.run(source, output, sha)
            self.assertEqual(marker.read_text(), "preserve")

    def test_private_receipt_does_not_promote_an_open_mesh(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "scan.obj"
            source.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
            before = source.read_bytes()
            with patch.object(self.module, "render_review"):
                r = self.module.run(source, Path(directory) / "inspection", hashlib.sha256(before).hexdigest())
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(r["boundary_edges"], 3)
            self.assertFalse(r["geometry_or_parameters_publication_permitted"])
            self.assertFalse(r["solver_ready"])


if __name__ == "__main__":
    unittest.main()
