"""Pure support/locality guards; native private CAD execution remains separate."""
import importlib.util
import math
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'
sys.path.insert(0,str(HERE))
SPEC = importlib.util.spec_from_file_location('seat_pads',HERE/'build_spring_seat_pads.py')
pads = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pads)


class SeatPadTests(unittest.TestCase):
    def test_fixed_local_design(self):
        self.assertEqual((pads.PAD_BOTTOM,pads.FLOOR,pads.OUTER_RADIUS,pads.INNER_RADIUS),(55.1,58.1,16.,7.))
        self.assertAlmostEqual(pads.AREA,650.3096792930871)

    def test_full_support_requires_no_missing_native_faces(self):
        self.assertTrue(pads.full_support(0,0.,pads.AREA))
        for args in [(1,0.,pads.AREA),(0,1.,pads.AREA),(0,0.,pads.AREA-25.),(False,0.,pads.AREA),
                     (0,math.nan,pads.AREA),(0,0.,math.inf),(0,-1.,pads.AREA),(0,False,pads.AREA)]:
            with self.subTest(args=args): self.assertFalse(pads.full_support(*args))

    def test_bbox_gate_is_finite_and_six_dimensional(self):
        before=[0.,0.,0.,1.,1.,1.]
        self.assertTrue(pads.unchanged_box(before,before[:]))
        self.assertFalse(pads.unchanged_box(before,before[:-1]))
        for v in (2.,math.nan,math.inf,True):
            self.assertFalse(pads.unchanged_box(before,[0.,0.,0.,1.,1.,v]))

    def test_exact_hash_gate_rejects_tamper_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'source';path.write_bytes(b'exact')
            pins={'source':pads.sha(path)}
            pads.exact_files(root,pins)
            path.write_bytes(b'tampered')
            with self.assertRaises(ValueError):pads.exact_files(root,pins)
            path.unlink();(root/'target').write_bytes(b'exact');path.symlink_to(root/'target')
            with self.assertRaises(ValueError):pads.exact_files(root,pins)


if __name__=='__main__':unittest.main()
