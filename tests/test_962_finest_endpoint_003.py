"""Pure index/fingerprint checks; no CGAL, compiler, Docker or head run."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "twins/962-cylinder-head-f0/source"
SPEC = importlib.util.spec_from_file_location("endpoint003_ids", SOURCE / "check_finest_endpoint_003.py")
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)


class OriginalReferenceIds(unittest.TestCase):
    def test_original_incidence_patch_order_and_referenced_vertex_ids(self):
        faces = [(0, 1, 2), (2, 3, 4), (4, 5, 6), (7, 8, 9), (9, 10, 11)]
        face_ids, vertex_ids = M.patch_reference_ids(faces, [3, 1], 12)
        self.assertEqual(face_ids, [0, 1, 2, 3, 4])
        self.assertEqual(vertex_ids, list(range(12)))
        self.assertEqual(M.patch_reference_ids(faces, [1, 3], 12), (face_ids, vertex_ids))
        # Selection is the one-ring original incidence, not recursive expansion.
        chain = [(0, 1, 2), (2, 3, 4), (4, 5, 6), (6, 7, 8)]
        self.assertEqual(M.patch_reference_ids(chain, [0], 9), ([0, 1], [0, 1, 2, 3, 4]))

    def test_raw_little_endian_ids_and_changed_export_refusal(self):
        self.assertEqual(M.id_bytes([0, 257, 2**32]), struct.pack("<QQQ", 0, 257, 2**32))
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "patch-reference-face-ids.u64").write_bytes(M.id_bytes([2, 5]))
            (directory / "patch-reference-vertex-ids.u64").write_bytes(M.id_bytes([1, 3, 8]))
            self.assertEqual(M.verify_reference_exports(directory, [2, 5], [1, 3, 8])[
                "patch-reference-face-ids.u64"]["count"], 2)
            (directory / "patch-reference-face-ids.u64").write_bytes(M.id_bytes([2, 6]))
            with self.assertRaises(ValueError):
                M.verify_reference_exports(directory, [2, 5], [1, 3, 8])

    def test_invalid_or_reordered_ids_and_symlink_refused(self):
        for ids in [[True], [-1], [1, 1], [2, 1], [2**64]]:
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                M.id_bytes(ids)
        for bad in [[True], [1, 1], [-1], [2]]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                M.patch_reference_ids([(0, 1, 2), (2, 3, 4)], bad, 5)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary); target = directory / "target"
            target.write_bytes(M.id_bytes([0]))
            (directory / "patch-reference-face-ids.u64").symlink_to(target)
            with self.assertRaises(ValueError):
                M.verify_reference_exports(directory, [0], [0])


if __name__ == "__main__":
    unittest.main()
