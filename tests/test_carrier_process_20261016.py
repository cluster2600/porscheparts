"""Independent geometry witnesses for the optional native PySLM preparation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "parts/993-eng-carrier-0001/source/process-20261016/build_pyslm.py"


@unittest.skipUnless(importlib.util.find_spec("pyslm"), "Optional PySLM runtime is required")
class NativeBuildPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("carrier_pyslm", SCRIPT)
        cls.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.api)

    def test_closed_square_hole_is_preserved_in_contours_and_hatching(self):
        import numpy as np
        import pyslm
        from shapely.geometry import Polygon
        import trimesh
        polygon = Polygon([[-5,-5], [5,-5], [5,5], [-5,5]],
                          holes=[[[-2,-2], [-2,2], [2,2], [2,-2]]])
        part = pyslm.Part("square_hole")
        part.setGeometry(trimesh.creation.extrude_polygon(polygon, 2),
                         fixGeometry=False, mergeVertices=False)
        raw, contours, segments, area = self.api.layer_geometry(part, 1)
        self.assertEqual(len(raw), 2)
        self.assertAlmostEqual(area, 84, places=8)
        self.assertTrue(all(np.array_equal(p[0], p[-1]) for p in raw + contours))
        self.assertGreater(len(segments), 0)
        for point in segments.mean(axis=1):
            self.assertTrue(polygon.covers(__import__("shapely").geometry.Point(point)))

    def test_exact_duplicate_exposures_are_removed_without_rounding(self):
        import numpy as np
        paths = [np.array([[0.,0.], [1.,0.]]), np.array([[1.,0.], [0.,0.]]),
                 np.array([[0.,1e-10], [1.,1e-10]])]
        segments, removed = self.api.unique_segments(paths)
        self.assertEqual(len(segments), 2)
        self.assertEqual(removed, 1)
        empty, removed = self.api.unique_segments([np.empty((0,2))])
        self.assertEqual(empty.shape, (0,2,2))
        self.assertEqual(removed, 0)

    def test_mesh_intake_preserves_all_faces_and_rejects_open_input(self):
        import pyslm
        import trimesh
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "witness.stl"
            box = trimesh.creation.box((20,10,2))
            box.export(path)
            mesh = self.api.exact_mesh(path)
            self.assertEqual(len(mesh.faces), 12)
            self.assertAlmostEqual(mesh.volume, 400)
            box.faces = box.faces[:-1]
            box.export(path)
            with self.assertRaisesRegex(ValueError, "closed"):
                self.api.exact_mesh(path)
            part = pyslm.Part("open_section")
            part.setGeometry(box, fixGeometry=False, mergeVertices=False)
            with self.assertRaisesRegex(ValueError, "Open planar section"):
                self.api.layer_geometry(part, 0)

    def test_native_teeth_join_plate_and_part_bands(self):
        import numpy as np
        import pyslm
        import pyslm.support
        import trimesh
        part = pyslm.Part("support_witness")
        part.setGeometry(trimesh.creation.box((20,10,2)), fixGeometry=False, mergeVertices=False)
        part.dropToPlatform(10)
        generator = pyslm.support.GridBlockSupportGenerator()
        generator.splineSimplificationFactor = None
        blocks = generator.identifySupportRegions(part, 45, True)
        self.assertEqual(len(blocks), 1)
        surface = blocks[0].geometry()
        self.assertTrue(np.isfinite(surface.vertices).all())
        self.assertLess(surface.bounds[0,2], 0)
        self.assertGreater(surface.bounds[0,2], -20)
        self.assertAlmostEqual(surface.bounds[1,2], 10.2)
        lines = trimesh.intersections.mesh_plane(surface, [0,0,1], [0,0,5])
        segments, _ = self.api.unique_segments([line[:, :2] for line in lines])
        self.assertGreater(len(segments), 0)
        face_z = surface.vertices[surface.faces, 2]
        bounds = np.column_stack((face_z.min(axis=1), face_z.max(axis=1)))
        for z in [0, 5, 10, 10.2, float(surface.vertices[0, 2])]:
            original = trimesh.intersections.mesh_plane(surface, [0,0,1], [0,0,z])
            culled = self.api.support_section(surface, z, bounds)
            self.assertTrue(np.array_equal(original, culled))

    def test_wrong_input_hash_cannot_create_output(self):
        import trimesh
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "box.stl", Path(directory) / "output"
            trimesh.creation.box().export(source)
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                self.api.build(source, output, "0" * 64)
            self.assertFalse(output.exists())

    def test_meshing_identity_receipt_is_strict_and_mutually_exclusive(self):
        import json
        import trimesh
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source, receipt, output = directory / "box.stl", directory / "meshing.json", directory / "output"
            trimesh.creation.box().export(source)
            receipt.write_text(json.dumps({"candidate_STL_sha256": "0" * 64}))
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                self.api.build(source, output, identity_receipt=receipt)
            with self.assertRaisesRegex(ValueError, "either"):
                self.api.build(source, output, self.api.digest(source), identity_receipt=receipt)
            receipt.write_text(json.dumps({"another_sha256": self.api.digest(source)}))
            with self.assertRaises(KeyError):
                self.api.build(source, output, identity_receipt=receipt)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
