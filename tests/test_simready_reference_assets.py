"""The fixture importer must reject damaged files before opening OpenUSD."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'twins/simready-reference-assets/fetch.py'
SPEC = importlib.util.spec_from_file_location('simready_reference_fetch', SCRIPT)
FETCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FETCH)


class ReferenceIntegrityTests(unittest.TestCase):
    def test_both_upstream_hash_formats_reject_same_size_corruption(self):
        original = b'reference data'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'asset'
            for algorithm in ('sha256', 'git-blob-sha1'):
                with self.subTest(algorithm=algorithm):
                    digest = (hashlib.sha256(original).hexdigest() if algorithm == 'sha256'
                              else hashlib.sha1(b'blob 14\0' + original).hexdigest())
                    record = {'path': 'asset', 'size': len(original),
                              'hash_algorithm': algorithm, 'hash': digest}
                    path.write_bytes(original)
                    FETCH.verify(path, record)
                    path.write_bytes(b'Reference data')
                    with self.assertRaisesRegex(ValueError, 'Hash mismatch'):
                        FETCH.verify(path, record)

    def test_offline_missing_file_and_parent_path_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            with self.assertRaises(FileNotFoundError):
                FETCH.fetch(cache, {}, {'path': 'missing'}, offline=True)
            with self.assertRaisesRegex(ValueError, 'Unsafe package path'):
                FETCH.fetch(cache, {}, {'path': '../outside'}, offline=True)


if __name__ == '__main__':
    unittest.main()
