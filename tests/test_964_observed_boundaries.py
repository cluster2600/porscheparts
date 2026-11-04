"""Controls for the distinction between scan holes and selection boundaries."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

try:
    import numpy as np
    import scipy
except ImportError:
    np = None

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/964-chassis/monocoque/observed-boundaries-20261029"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SOURCE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipIf(np is None, "NumPy and SciPy required")
class ObservedBoundaryControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.author = load("inspect_boundaries")
        cls.reader = load("verify_boundaries")

    def test_square_cut_keeps_the_diagonal_distinct_from_original_edges(self):
        faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)
        keys, counts, _, summary = self.author.edge_table(faces, 4)
        local_keys, local_counts, _, _ = self.author.edge_table(faces[:1], 4)
        edges, origins = self.author.classify_boundary(local_keys, local_counts, keys, counts, 4)
        self.assertEqual(summary["open_edges"], 4)
        self.assertEqual(dict(zip(map(tuple, edges), origins)), {(0, 1): 0, (0, 2): 1, (1, 2): 0})

    def test_large_int32_source_indices_do_not_collide_in_edge_keys(self):
        faces = np.array([[2_000_000, 2_000_001, 2_000_002], [2_000_000, 2_000_002, 2_000_003]], dtype=np.int32)
        keys, counts, labels, summary = self.author.edge_table(faces, 2_400_031)
        pairs, reference_counts, reference_labels, reference = self.reader.pair_inventory(faces)
        np.testing.assert_array_equal(np.column_stack((keys // 2_400_031, keys % 2_400_031)), pairs)
        np.testing.assert_array_equal(counts, reference_counts)
        np.testing.assert_array_equal(labels, reference_labels)
        self.assertEqual(summary, reference)
        self.assertEqual(summary["unique_edges"], 5)

    def test_nonmanifold_source_incidence_remains_ambiguous(self):
        faces = np.array([[0, 1, 2], [1, 0, 3], [0, 1, 4]])
        keys, counts, _, summary = self.author.edge_table(faces, 5)
        local_keys, local_counts, _, _ = self.author.edge_table(faces[:1], 5)
        edges, origins = self.author.classify_boundary(local_keys, local_counts, keys, counts, 5)
        self.assertEqual(summary["nonmanifold_edges"], 1)
        self.assertEqual(dict(zip(map(tuple, edges), origins))[(0, 1)], 2)

    def test_vertex_contact_does_not_merge_surface_components(self):
        faces = np.array([[0, 1, 2], [0, 3, 4]])
        keys, counts, labels, summary = self.author.edge_table(faces, 5)
        self.assertEqual(summary["edge_connected_surface_components"], 2)
        self.assertNotEqual(labels[0], labels[1])
        edges = np.column_stack((keys[counts == 1] // 5, keys[counts == 1] % 5))
        self.assertEqual(self.author.boundary_graph(edges), {"components": 1, "simple_cycles": 0, "other_components": 1})

    def test_same_direction_shared_edge_is_reported(self):
        faces = np.array([[0, 1, 2], [0, 1, 3]])
        _, _, _, summary = self.author.edge_table(faces, 4)
        self.assertEqual(summary["same_direction_two_face_edges"], 1)
        self.assertEqual(summary, self.reader.pair_inventory(faces)[3])

    def test_foreign_boundary_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not in the original"):
            self.author.classify_boundary(np.array([9]), np.array([1]), np.array([1, 2]), np.array([1, 1]), 4)

    def test_invalid_input_does_not_publish_an_output(self):
        (ROOT / "work").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as temp:
            temp = Path(temp)
            fake = temp / "fake.obj"
            fake.write_text("not the original scan")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                self.author.run(fake, fake, fake, temp / "result")
            self.assertFalse((temp / "result").exists())
            with self.assertRaisesRegex(ValueError, "new directory"):
                self.author.run(fake, fake, fake, temp)


if __name__ == "__main__":
    unittest.main()
