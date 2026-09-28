"""Bounded collection preserves evidence and rejects unsafe or changed archives."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/fourvalve/g11_collect.py'
SPEC = importlib.util.spec_from_file_location('g11_collect', SOURCE)
collect = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collect)


class CollectionChecks(unittest.TestCase):
    def fixture(self, root):
        source = root/'job'
        case = source/'results/case'
        case.mkdir(parents=True)
        for name in ('x.inp', 'x.dat', 'mesh.msh', 'matrix.inp', 'matrix.dof', 'matrix.sti', 'matrix.mas', 'result.json'):
            (case/name).write_text('original '+name)
        (source/'input-checksums.txt').write_text('input fingerprint')
        (source/'environment.txt').write_text('numpy==2.2.6')
        (source/'account.private.json').write_text('must not be collected')
        return source, case

    def test_round_trip_preserves_results_and_records_omissions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, case = self.fixture(root)
            archive = root/'collection.tgz'
            result = collect.pack(source, archive)
            self.assertEqual(result['omitted_files'], 2)
            self.assertFalse(result['directly_checkpoint_resumable'])
            checked = collect.verify(archive, result['archive_sha256'])
            self.assertEqual(checked['verification'], 'streamed_content_sha256_no_extraction')
            with tarfile.open(archive) as handle:
                inventory = json.load(handle.extractfile(collect.JOB+'/'+collect.INVENTORY))
                self.assertEqual(handle.extractfile(collect.JOB+'/results/case/result.json').read(), (case/'result.json').read_bytes())
                members = set(handle.getnames())
            self.assertFalse(inventory['original_result_hashes_modified'])
            self.assertIn(collect.JOB+'/results/case/matrix.dof', members)
            self.assertNotIn(collect.JOB+'/results/case/matrix.sti', members)
            self.assertNotIn(collect.JOB+'/account.private.json', members)
            with self.assertRaisesRegex(ValueError, 'fingerprint mismatch'):
                collect.verify(archive, '0'*64)
            xz = root/'collection.tar.xz'
            packed = collect.pack(source, xz, xz_preset=1)
            self.assertEqual(collect.verify(xz, packed['archive_sha256'])['retained_files_verified'], checked['retained_files_verified'])

    def test_cap_symlink_and_traversal_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, case = self.fixture(root)
            with self.assertRaisesRegex(ValueError, 'transfer cap'):
                collect.pack(source, root/'too-big.tgz', max_bytes=100)
            self.assertFalse((root/'too-big.tgz').exists())
            (case/'linked.dat').symlink_to(source/'account.private.json')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                collect.pack(source, root/'linked.tgz')
            (case/'linked.dat').unlink()
            good = root/'good.tgz'
            collect.pack(source, good)
            bad = root/'bad.tgz'
            with tarfile.open(good, 'r:gz') as original, tarfile.open(bad, 'w:gz') as malicious:
                for member in original:
                    malicious.addfile(member, original.extractfile(member))
                entry = tarfile.TarInfo('g11-collection/../../escape')
                entry.size = 1
                malicious.addfile(entry, io.BytesIO(b'x'))
            sha = hashlib.sha256(bad.read_bytes()).hexdigest()
            with self.assertRaises((ValueError, RuntimeError)):
                collect.verify(bad, sha)
            self.assertFalse((root/'escape').exists())

    def test_inner_hash_rejects_changed_payload_even_with_matching_archive_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, _ = self.fixture(root)
            good, bad = root/'good.tgz', root/'changed.tgz'
            collect.pack(source, good)
            with tarfile.open(good, 'r:gz') as original, tarfile.open(bad, 'w:gz') as changed:
                for member in original:
                    payload = original.extractfile(member).read()
                    if member.name.endswith('/x.dat'):
                        payload = b'X'+payload[1:]
                    changed.addfile(member, io.BytesIO(payload))
            sha = hashlib.sha256(bad.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, 'retained file fingerprint mismatch'):
                collect.verify(bad, sha)


if __name__ == '__main__':
    unittest.main()
