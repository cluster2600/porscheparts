"""Small stdlib path/archive/case invariants; no real fields or scientific imports."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


a = load('_capsule_restore_fixture', HERE / 'restore.py')
r = load('_capsule_replay_fixture', HERE / 'replay_analysis.py')


def encoded():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        info = zipfile.ZipInfo('work/fixed/file.dat', (1980, 1, 1, 0, 0, 0))
        info.create_system = 3; info.external_attr = 0o100644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED; info._compresslevel = 6
        archive.writestr(info, b'original\n')
    return stream.getvalue()


def row():
    return dict(members={'work/fixed/file.dat': dict(bytes=9, sha256=hashlib.sha256(b'original\n').hexdigest())})


class Tests(unittest.TestCase):
    def test_relative_paths_only(self):
        for value in ['', '/absolute', '../escape', 'a/../b', './a', 'a//b']:
            with self.assertRaises(ValueError): a.relative(value)
        self.assertEqual(a.relative('a/b'), Path('a/b'))

    def test_deterministic_fixed_ZIP_metadata(self):
        self.assertEqual(encoded(), encoded())

    def test_transfer_original_bytes_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); (root / 'common.zip').write_bytes(encoded()); output = root / 'out'; output.mkdir()
            with patch.object(a, 'HERE', root):
                a.transfer('common.zip', row(), output)
                self.assertEqual((output / 'work/fixed/file.dat').read_bytes(), b'original\n')
                with self.assertRaises(FileExistsError): a.transfer('common.zip', row(), output)

    def test_missing_duplicate_or_changed_member_refused(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); (root / 'common.zip').write_bytes(encoded())
            with patch.object(a, 'HERE', root):
                bad = row(); bad['members']['work/fixed/file.dat']['sha256'] = '0' * 64
                with self.assertRaises(ValueError): a.transfer('common.zip', bad)
                with self.assertRaises(ValueError): a.transfer('common.zip', dict(members={}))
                with zipfile.ZipFile(root / 'common.zip', 'a') as archive:
                    archive.writestr('extra', b'not authorized')
                with self.assertRaises(ValueError): a.transfer('common.zip', row())

    def test_archive_tamper_refused_before_restore(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); (root / 'manifest.json').write_text('{}\n')
            with patch.object(a, 'HERE', root):
                with self.assertRaises(ValueError): a.manifest('0' * 64)

    def test_existing_or_dangling_output_refused_before_manifest(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); dangling = root / 'dangling'; dangling.symlink_to(root / 'missing')
            with patch.object(a, 'manifest', side_effect=AssertionError('No reading allowed')):
                for target in [root, dangling]:
                    with self.assertRaises(ValueError): a.restore(target, 'not consulted')

    def test_wrong_case_or_mesh_refused(self):
        case = dict(name='combined-rigid-static')
        valid = dict(procedure='static', name=case['name'], mesh_sha256='fixed')
        r.checked_case(case, valid, 'fixed')
        for change in [dict(valid, name='different'), dict(valid, procedure='dynamic'), dict(valid, mesh_sha256='changed')]:
            with self.assertRaises(ValueError): r.checked_case(case, change, 'fixed')

    def test_no_scientific_import_at_load(self):
        import sys
        self.assertNotIn('numpy', sys.modules); self.assertNotIn('gmsh', sys.modules)


if __name__ == '__main__': unittest.main()
