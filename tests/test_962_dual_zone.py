import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/962-cylinder-head-f0/source/coolant_flow'
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location('dual_zone', SOURCE / 'repair_dual_zone.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class DualZoneTests(unittest.TestCase):
    def test_cell_count_is_derived_from_connectivity_and_checked_against_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'owner').write_text('note "nCells:2";\n4\n(\n0\n0\n1\n1\n)\n')
            (root / 'neighbour').write_text('1\n(\n1\n)\n')
            self.assertEqual(module.cell_count(root), 2)
            (root / 'owner').write_text('note "nCells:3";\n4\n(\n0\n0\n2\n2\n)\n')
            (root / 'neighbour').write_text('0\n(\n)\n')
            with self.assertRaises(ValueError): module.cell_count(root)

    def test_truncated_or_negative_native_labels_fail_closed(self):
        for text in ('2\n(0)', '2\n(0 -1)'):
            with self.assertRaises(ValueError): module.labels(text)


if __name__ == '__main__': unittest.main()
