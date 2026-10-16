"""Independent arithmetic/identity guards for the separate analysis representation."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / "twins/962-cylinder-head-f0/source"
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location("prepare_head_analysis", SOURCE / "prepare_head_analysis.py")
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class AnalysisSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.points = np.array([[0., 0, 0], [1., 0, 0], [0., 1, 0], [0., 0, 1]])
        self.faces = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])

    def test_oriented_closed_tetrahedron(self):
        result = analysis.validate_surface(self.points, self.faces)
        self.assertEqual(result["euler_characteristic"], 2)
        self.assertAlmostEqual(result["signed_volume_mm3"], 1/6)

    def test_invalid_surfaces_fail_closed(self):
        for points, faces in ((self.points, self.faces[:-1]),
                (self.points, self.faces[:, ::-1]),
                (self.points, np.array([[0, 0, 1]])),
                (self.points * np.nan, self.faces)):
            with self.subTest(faces=faces.tolist()):
                with self.assertRaises(ValueError):
                    analysis.validate_surface(points, faces)

    def test_compaction_preserves_near_distinct_coordinates_and_orientation(self):
        p = np.vstack([self.points, [1e-12, 0, 0], [2, 2, 2]])
        f = np.array([[0, 4, 1]])
        q, g = analysis.compact_unused(p, f)
        self.assertEqual(len(q), 3)
        self.assertTrue(np.array_equal(q[g], p[f]))
        self.assertNotEqual(q[0, 0], q[2, 0])

    def test_contract_bytes_are_frozen(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "contract.json"
            path.write_bytes(analysis.CONTRACT.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "Frozen contract changed"):
                analysis.verify_contract(path)

    def test_diagnostic_counts_identify_reversed_and_open_faces(self):
        changed = self.faces.copy(); changed[0] = changed[0, ::-1]
        row = analysis.edge_diagnostics(changed)
        self.assertEqual(row["boundary_edges"], 0)
        self.assertEqual(row["orientation_imbalanced_edges"], 3)
        row = analysis.edge_diagnostics(self.faces[:-1])
        self.assertEqual(row["boundary_edges"], 3)

    def test_output_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                analysis.new_output(Path(folder))

    def test_worker_cannot_claim_previous_results(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "fresh controller"):
                analysis.worker(SimpleNamespace(output=Path(folder)))


if __name__ == "__main__":
    unittest.main()
