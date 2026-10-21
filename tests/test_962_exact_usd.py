"""Source-coordinate serialization controls; native USD acceptance is separate."""
import importlib.util
from pathlib import Path
import re
import struct
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "author_exact_usd", ROOT / "twins/962-cylinder-head-f0/source/author_exact_usd.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExactUsdSourceTests(unittest.TestCase):
    def write_stl(self, path, triangles):
        records = np.zeros(len(triangles), dtype=module.reader().RECORD)
        records["vertices"] = triangles
        path.write_bytes(bytes(80) + struct.pack("<I", len(records)) + records.tobytes())

    def recover_triangles(self, text):
        body = re.search(r"point3f\[\] points = \[(.*?)\n        \]", text, re.S)[1]
        points = np.array([[float(x) for x in value.split(",")]
                           for value in re.findall(r"\(([^)]+)\)", body)], dtype=np.float32)
        indices = re.search(r"int\[\] faceVertexIndices = \[(.*?)\n        \]", text, re.S)[1]
        faces = np.array([int(x) for x in re.findall(r"\d+", indices)]).reshape(-1, 3)
        return points, points[faces]

    def test_nearly_distinct_float32_coordinates_roundtrip_without_welding(self):
        near = np.nextafter(np.float32(1), np.float32(2))
        triangles = np.array([[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                              [[near, 0, 0], [0, 1, 0], [0, 0, 1]]], dtype=np.float32)
        with tempfile.TemporaryDirectory() as temporary:
            source, target = Path(temporary) / "source.stl", Path(temporary) / "exact.usda"
            self.write_stl(source, triangles)
            original_hash = module.sha(source)
            report = module.author(source, target)
            points, recovered = self.recover_triangles(target.read_text())
            self.assertEqual(len(points), 4)
            self.assertTrue(np.array_equal(recovered, triangles))
            self.assertEqual(recovered.tobytes(), triangles.tobytes())
            self.assertEqual(report["source_triangles"], 2)
            self.assertEqual(module.sha(source), original_hash)

    def test_orientation_duplicate_multiplicity_frame_and_no_physics_are_preserved(self):
        triangle = np.array([[2, 3, 4], [5, 3, 4], [2, 7, 4]], dtype=np.float32)
        triangles = np.array([triangle, triangle[::-1], triangle])
        with tempfile.TemporaryDirectory() as temporary:
            source, target = Path(temporary) / "source.stl", Path(temporary) / "exact.usda"
            self.write_stl(source, triangles)
            module.author(source, target)
            text = target.read_text(); _, recovered = self.recover_triangles(text)
            self.assertEqual(recovered.tobytes(), triangles.tobytes())
            self.assertIn('metersPerUnit = 0.001', text)
            self.assertIn('upAxis = "Z"', text)
            self.assertIn('subdivisionScheme = "none"', text)
            self.assertNotIn('xformOp', text)
            self.assertNotIn('Physics', text)
            self.assertNotIn('Material', text)

    def test_existing_output_or_symlink_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "kept.usda"; target.write_text("prior evidence")
            link = Path(temporary) / "link.usda"; link.symlink_to(target)
            for output in [target, link]:
                for function in [module.author, module.save_native]:
                    with self.assertRaises(FileExistsError):
                        function(Path(temporary) / "missing.stl", output)
                self.assertEqual(target.read_text(), "prior evidence")

    def test_invalid_geometry_is_rejected_without_creating_an_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, target = Path(temporary) / "bad.stl", Path(temporary) / "exact.usda"
            self.write_stl(source, np.zeros((1, 3, 3), dtype=np.float32))
            with self.assertRaisesRegex(ValueError, "Zero-area"):
                module.author(source, target)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
