"""Small stdlib publication refusals; no ZIP or scientific execution."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('_fixed_C1_h2_publication', HERE / 'check_publication.py')
checker = importlib.util.module_from_spec(spec); spec.loader.exec_module(checker)


def fixture(folder):
    (folder / 'unconsumed.txt').write_bytes(b'preserve the entire file\n')
    rows = {'unconsumed.txt': checker.sha(folder / 'unconsumed.txt')}
    (folder / 'archive.json').write_text(json.dumps({'files_sha256': rows}))


class Checks(unittest.TestCase):
    def test_complete_inventory_keeps_unconsumed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); fixture(folder)
            self.assertEqual(set(checker.inventory(folder)), {'unconsumed.txt'})

    def test_unknown_file_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); fixture(folder); (folder / 'foreign').touch()
            with self.assertRaisesRegex(ValueError, 'inventory'): checker.inventory(folder)

    def test_whole_file_change_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); fixture(folder); (folder / 'unconsumed.txt').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'SHA'): checker.inventory(folder)

    def test_symlink_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); fixture(folder); original = folder / 'unconsumed.txt'
            target = folder / 'target'; original.rename(target); original.symlink_to(target)
            rows = {'unconsumed.txt': checker.sha(target), 'target': checker.sha(target)}
            (folder / 'archive.json').write_text(json.dumps({'files_sha256': rows}))
            with self.assertRaisesRegex(ValueError, 'nonsymlink'): checker.inventory(folder)

    def test_same_size_changed_receipt_cross_link_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); a = folder / 'a'; b = folder / 'b'
            a.write_bytes(b'{"RC":0}'); b.write_bytes(b'{"RC":1}')
            record = {'receipt': checker.sha(a)}
            checker.link(record, 'receipt', a)
            with self.assertRaisesRegex(ValueError, 'cross-link'): checker.link(record, 'receipt', b)

    def test_actual_owned_close_required(self):
        good = dict(status='executed', actual_returncode=0, direct_child_reaped=True,
                    no_non_zombie_group_members=True, final_group_members=[], timeout=False,
                    interrupted=False, failure=None, cleanup_error=None, sources_and_plan_unchanged=True)
        checker.closed(good)
        for key, value in [('actual_returncode', 1), ('timeout', True), ('direct_child_reaped', False),
                           ('final_group_members', [123]), ('sources_and_plan_unchanged', False)]:
            bad = copy.deepcopy(good); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): checker.closed(bad)

    def test_all_four_real_small_report_bytes(self):
        checker.reports(HERE / 'evidence/replay')
        self.assertEqual(len(checker.REPORTS), 4)

    def test_report_whitespace_change_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for name in checker.REPORTS:
                source = HERE / 'evidence/replay' / name
                self.assertLess(source.stat().st_size, 4000)
                (folder / name).write_bytes(source.read_bytes())
            path = folder / 'rigid-energy.json'; path.write_bytes(path.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'report bytes'): checker.reports(folder)


if __name__ == '__main__':
    unittest.main()
