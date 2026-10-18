"""Synthetic exact-indexing controls; no head solver or Gmsh dependency in unit tests."""
import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("head_volume_mesh", ROOT / "twins/962-cylinder-head-f0/source/mesh_head.py")
mesh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mesh)


class ExactHeadMeshTests(unittest.TestCase):
    def setUp(self):
        self.points = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]], dtype=np.float32)
        self.faces = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]])
        self.triangles = self.points[self.faces]

    def binary_stl(self, path, triangles):
        records = np.zeros(len(triangles), dtype=mesh.RECORD)
        records["vertices"] = triangles
        path.write_bytes(bytes(80) + struct.pack("<I", len(triangles)) + records.tobytes())

    def test_exact_binary_index_reconstruction_keeps_oriented_faces(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "control.stl"
            self.binary_stl(path, self.triangles)
            original, points, faces = mesh.read_binary_stl(path)
            self.assertEqual(mesh.RECORD.itemsize, 50)
            self.assertTrue(np.array_equal(original, self.triangles))
            self.assertTrue(np.array_equal(points[faces], self.triangles))
            self.assertEqual((len(points), len(faces)), (4, 4))
            self.assertEqual(mesh.topology(faces)["boundary_edges"], 0)

    def test_near_distinct_coordinates_are_never_tolerance_welded(self):
        triangles = self.triangles.copy()
        triangles[0, 0, 0] = np.nextafter(np.float32(0), np.float32(1))
        points, faces = mesh.index_triangles(triangles)
        self.assertEqual(len(points), 5)
        self.assertTrue(np.array_equal(points[faces], triangles))

    def test_invalid_nonfinite_and_zero_area_faces_are_rejected(self):
        controls = [np.empty((0, 3, 3)), np.zeros((1, 3, 3)), np.zeros((3, 3))]
        for value in (float("nan"), float("inf")):
            triangles = self.triangles.copy()
            triangles[0, 0, 0] = value
            controls.append(triangles)
        repeated = self.triangles.copy()
        repeated[0, 1] = repeated[0, 0]
        controls.append(repeated)
        for triangles in controls:
            with self.subTest(shape=triangles.shape), self.assertRaises(ValueError):
                mesh.index_triangles(triangles)

    def test_binary_size_and_zero_record_count_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.stl"
            for data in (b"short", bytes(84), bytes(80) + struct.pack("<I", 1),
                         bytes(80) + struct.pack("<I", 0) + b"trailing"):
                path.write_bytes(data)
                with self.assertRaises(ValueError):
                    mesh.read_binary_stl(path)

    def test_nonfinite_binary_normal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad-normal.stl"
            records = np.zeros(4, dtype=mesh.RECORD)
            records["vertices"] = self.triangles
            records["normal"][0, 0] = np.nan
            path.write_bytes(bytes(80) + struct.pack("<I", 4) + records.tobytes())
            with self.assertRaisesRegex(ValueError, "Nonfinite STL normals"):
                mesh.read_binary_stl(path)

    def test_open_or_reversed_surface_fails_connectivity(self):
        with self.assertRaises(ValueError):
            mesh.topology(self.faces[:-1])
        changed = self.faces.copy()
        changed[0] = changed[0, ::-1]
        with self.assertRaises(ValueError):
            mesh.topology(changed)

    def test_independent_signed_tetra_volume_and_oriented_boundary(self):
        cells = np.array([[0, 1, 2, 3]])
        self.assertAlmostEqual(mesh.tetra_volumes(self.points, cells)[0], 1 / 6)
        self.assertTrue(mesh.tetra_boundary(cells, self.faces)["exact_oriented_tetra_boundary"])
        with self.assertRaises(ValueError):
            mesh.tetra_boundary(cells, self.faces[:, ::-1])
        reversed_cells = np.array([[0, 2, 1, 3]])
        self.assertLess(mesh.tetra_volumes(self.points, reversed_cells)[0], 0)

    def test_quality_distribution_keeps_nonpositive_counts(self):
        result = mesh.distribution([1., .5, 0., -.1])
        self.assertEqual(result["nonpositive_count"], 2)
        self.assertEqual(result["minimum"], -.1)
        with self.assertRaises(ValueError):
            mesh.distribution([float("nan")])

    def test_post_mesh_cyclic_rotation_and_retagging_preserve_exact_oriented_surface(self):
        permuted = np.roll(self.faces[[2, 0, 3, 1]] + 1, 1, axis=1)
        api = SimpleNamespace(model=SimpleNamespace(mesh=SimpleNamespace(
            getNodes=lambda: (np.arange(1, 5), self.points.ravel(), []),
            getElements=lambda dimension: ([2], [np.arange(101, 105)], [permuted.ravel()]))))
        with self.assertRaisesRegex(ValueError, "connectivity"):
            mesh.surface_roundtrip(api, self.points, self.faces)
        result = mesh.surface_roundtrip(api, self.points, self.faces, exact_tagged_order=False)
        self.assertTrue(result["exact_source_oriented_connectivity"])
        self.assertFalse(result["source_element_tags_preserved"])
        reversed_faces = permuted.copy()
        reversed_faces[0] = reversed_faces[0, ::-1]
        api.model.mesh.getElements = lambda dimension: ([2], [np.arange(101, 105)], [reversed_faces.ravel()])
        with self.assertRaisesRegex(ValueError, "connectivity"):
            mesh.surface_roundtrip(api, self.points, self.faces, exact_tagged_order=False)

    def test_existing_output_and_excessive_deadline_are_rejected_before_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "evidence"
            output.mkdir()
            marker = output / "kept.txt"
            marker.write_text("prior evidence")
            with self.assertRaisesRegex(ValueError, "must be new"):
                mesh.run(argparse.Namespace(output=output, bore=95, deadline_s=300))
            self.assertEqual(marker.read_text(), "prior evidence")
            other = Path(temporary) / "new"
            with self.assertRaisesRegex(ValueError, "1..300"):
                mesh.run(argparse.Namespace(output=other, bore=95, deadline_s=301))
            self.assertFalse(other.exists())

    def test_hidden_worker_cannot_overwrite_or_reuse_controller_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            marker = output / "worker-report.json"
            marker.write_text("previous evidence")
            with self.assertRaisesRegex(ValueError, "fresh controller directory"):
                mesh.claim_worker(output)
            self.assertEqual(marker.read_text(), "previous evidence")
            marker.unlink()
            source = Path(mesh.__file__).resolve()
            (output / "source-executed.py").write_bytes(source.read_bytes())
            (output / "native.log").write_text("")
            argv = [str(source), "--worker", "--bore", "95", "--output", str(output)]
            receipt = dict(status="running", command=[sys.executable, *argv],
                source_sha256=mesh.sha(source), native_deadline_s=300)
            (output / "receipt.json").write_text(json.dumps(receipt))
            with mock.patch.object(sys, "argv", argv):
                self.assertEqual(mesh.claim_worker(output), 300)
                with self.assertRaisesRegex(ValueError, "fresh controller directory"):
                    mesh.claim_worker(output)


if __name__ == "__main__":
    unittest.main()
