import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

try:import numpy as np
except ImportError:np=None
SOURCE=Path(__file__).resolve().parents[1]/'twins/935-horizontal-cooling-system-f0/source';sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('conforming_volume',SOURCE/'import_conforming_volume.py')
module=importlib.util.module_from_spec(spec)
if np is not None:spec.loader.exec_module(module)


@unittest.skipIf(np is None,'NumPy unavailable')
class ConformingVolumeTests(unittest.TestCase):
    def test_exact_orientation_distinguishes_positive_negative_and_flat_cells(self):
        v=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
        for cell,negative,zero in [([0,1,2,3],0,0),([0,2,1,3],1,0),([0,1,2,2],0,1)]:
            r=module.exact_orientation(v,np.array([cell]))
            self.assertEqual((r['negative'],r['zero']),(negative,zero))
            if not negative and not zero:self.assertAlmostEqual(r['signed_volume_native_units_cubed'],1/6)

    def test_small_positive_dyadic_cell_is_not_rounded_to_a_flat_tetrahedron(self):
        v=np.array([[0.,0,0],[1,0,0],[1,2.**-40,0],[1,2.**-40,2.**-40]])
        r=module.exact_orientation(v,np.array([[0,1,2,3]]))
        self.assertEqual((r['negative'],r['zero']),(0,0))
        self.assertEqual(r['signed_volume_native_units_cubed'],2.**-80/6)

    def test_table_rejects_missing_records_or_changed_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'a.node'
            for text in ('2 3 0 0\n0 0 0 0\n','1 3 0 0\n1 0 0 0\n','1 3 1 0\n0 0 0 0\n'):
                p.write_text(text)
                with self.assertRaises(ValueError):module.table(p,'node')
