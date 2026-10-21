"""Small byte-copy checks; no USD import or full head asset access."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "usd_profile_alias", ROOT / "twins/962-cylinder-head-f0/source/copy_bore95_profile_alias.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProfileAliasTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.content = b"Known local byte-copy fixture\x00\xff\n"
        self.source = self.root / "source.usdc"
        self.source.write_bytes(self.content)
        self.expected = hashlib.sha256(self.content).hexdigest()

    def test_exact_copy_preserves_source(self):
        destination = self.root / "new-alias"
        result = module.copy_identity(self.source, destination, self.expected, len(self.content))
        self.assertEqual((destination / "solid-face-normals.usd").read_bytes(), self.content)
        self.assertEqual(self.source.read_bytes(), self.content)
        for key in ("source_before_sha256", "source_after_sha256", "alias_sha256"):
            self.assertEqual(result[key], self.expected)
        self.assertIs(result["byte_identical"], True)
        self.assertEqual(result["bytes"], len(self.content))

    def test_wrong_hash_refuses_before_output(self):
        destination = self.root / "wrong-hash"
        with self.assertRaisesRegex(ValueError, "Exact unchanged source bytes required"):
            module.copy_identity(self.source, destination, "0" * 64, len(self.content))
        self.assertFalse(destination.exists())
        self.assertEqual(self.source.read_bytes(), self.content)

    def test_existing_target_is_refused_and_preserved(self):
        destination = self.root / "existing"
        destination.mkdir()
        target = destination / "solid-face-normals.usd"
        target.write_bytes(b"Preserved existing bytes")
        with self.assertRaisesRegex(FileExistsError, "Fresh alias directory required"):
            module.copy_identity(self.source, destination, self.expected, len(self.content))
        self.assertEqual(target.read_bytes(), b"Preserved existing bytes")
        self.assertEqual(self.source.read_bytes(), self.content)


if __name__ == "__main__":
    unittest.main()
