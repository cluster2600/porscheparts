"""Storage-order and checksum controls for the exact all-cell checker adapter."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / 'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/describe_stored_tet_archive.py'
SPEC = importlib.util.spec_from_file_location('carrier_tet_archive_layout', SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ArchiveLayoutTest(unittest.TestCase):
    def check_layout(self, fortran):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'case.npz'
            t = np.array([[0, 1, 2, 3], [0, 2, 1, 4]], dtype='<i8', order='F' if fortran else 'C')
            np.savez(p, vertices=np.zeros((5, 3)), tetrahedra=t)
            report = MODULE.describe(p, hashlib.sha256(p.read_bytes()).hexdigest())
            layout = report['layout']['tetrahedra.npy']
            self.assertEqual(layout['fortran_order'], fortran)
            raw = np.frombuffer(p.read_bytes(), dtype='<i8', count=8, offset=layout['offset'])
            np.testing.assert_array_equal(raw.reshape((2, 4), order='F' if fortran else 'C'), t)

    def test_c_order_exact_payload(self):
        self.check_layout(False)

    def test_fortran_order_exact_payload(self):
        self.check_layout(True)

    def test_compressed_archive_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'case.npz'
            np.savez_compressed(p, vertices=np.zeros((5, 3)), tetrahedra=np.zeros((2, 4), dtype=np.int64))
            with self.assertRaisesRegex(ValueError, 'stored'):
                MODULE.describe(p, hashlib.sha256(p.read_bytes()).hexdigest())

    def test_changed_checksum_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'case.npz'
            p.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                MODULE.describe(p, '0' * 64)

    def test_wrong_cell_width_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'case.npz'
            np.savez(p, vertices=np.zeros((5, 3)), tetrahedra=np.zeros((2, 5), dtype=np.int64))
            with self.assertRaisesRegex(ValueError, 'shape'):
                MODULE.describe(p, hashlib.sha256(p.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
