"""Guardrails for the private, photo-guided visual-repair command."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "twins/935-horizontal-cooling-system-f0/source/photo_guided_surface_repair.py"
spec = importlib.util.spec_from_file_location("photo_guided_surface_repair", SOURCE)
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


class PhotoGuidedRepairGuardrailTests(unittest.TestCase):
    def test_https_photo_references_are_preserved(self):
        references = ["https://example.test/fan-a", "https://example.test/fan-b"]
        self.assertEqual(repair.require_photo_references(references), references)

    def test_photo_references_require_unique_https_urls(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            repair.require_photo_references(["http://example.test/fan"])
        with self.assertRaisesRegex(ValueError, "unique"):
            repair.require_photo_references(["https://example.test/fan", "https://example.test/fan"])

    def test_output_must_remain_under_work_in_a_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".git").mkdir()
            repair.require_private_output(root / "work" / "new-run")
            with self.assertRaisesRegex(ValueError, "work"):
                repair.require_private_output(root / "published" / "new-run")

    def test_hash_is_byte_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture"
            path.write_bytes(b"935 private fixture")
            self.assertEqual(repair.sha256(path), hashlib.sha256(b"935 private fixture").hexdigest())


if __name__ == "__main__":
    unittest.main()
