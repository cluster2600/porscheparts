import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

try:
    import numpy as np
    import scipy
    import trimesh
except ImportError:
    np = None


@unittest.skipIf(np is None, "boundary inventory requires scan audit dependencies")
class BoundaryInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scripts = Path(__file__).parents[1] / "scripts"
        sys.path.insert(0, str(scripts))
        try:
            spec = importlib.util.spec_from_file_location("boundary_inventory", scripts / "inventory_935_scan_boundaries.py")
            cls.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.module)
        finally:
            sys.path.pop(0)

    def test_distinct_cycles_and_source_edge_mapping(self):
        points = np.array([[0,0,0], [1,0,0], [0,1,0], [0,0,2], [1,0,2], [0,1,2]])
        edges = np.array([[0,1], [1,2], [2,0], [3,4], [4,5], [5,3]])
        rows, labels = self.module.inventory(points, edges)
        self.assertEqual(len(rows), 2)
        self.assertEqual(labels.tolist(), [0,0,0,1,1,1])
        for row in rows:
            self.assertTrue(row["simple_cycle_topology"])
            self.assertAlmostEqual(row["length_source_units"], 2 + np.sqrt(2))
            self.assertEqual(row["plane_max_source_units"], 0)
            self.assertFalse(row["closure_authorized"])
        _, reordered = self.module.inventory(points, edges[::-1])
        self.assertEqual(reordered.tolist(), labels[::-1].tolist())

    def test_touching_loops_do_not_become_one_simple_cycle(self):
        points = np.array([[0,0,0], [1,0,0], [0,1,0], [-1,0,0], [0,-1,1]])
        rows, _ = self.module.inventory(points, np.array([[0,1],[1,2],[2,0],[0,3],[3,4],[4,0]]))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["max_vertex_degree"], 4)
        self.assertFalse(rows[0]["simple_cycle_topology"])
        self.assertGreater(rows[0]["plane_max_source_units"], 0)

    def test_empty_boundary_and_invalid_edges(self):
        points = np.zeros((3,3))
        rows, labels = self.module.inventory(points, np.empty((0,2), dtype=int))
        self.assertEqual(rows, [])
        self.assertEqual(len(labels), 0)
        for edges in ([[0,3]], [[0,0]], [[0,1],[1,0]], [[0.,1.]]):
            with self.subTest(edges=edges), self.assertRaises(ValueError):
                self.module.inventory(points, np.array(edges))

    def test_collinear_cycle_does_not_define_a_plane(self):
        rows, _ = self.module.inventory(np.array([[0,0,0], [1,0,0], [2,0,0]]),
                                         np.array([[0,1], [1,2], [2,0]]))
        self.assertEqual(rows[0]["affine_rank"], 1)
        self.assertIsNone(rows[0]["plane_rms_source_units"])

    def test_wrong_scan_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.obj"
            source.write_text("not the frozen scan")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                self.module.run(source, root / "out")
            self.assertFalse((root / "out").exists())
