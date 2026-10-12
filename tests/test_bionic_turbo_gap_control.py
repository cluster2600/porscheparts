import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/bionic-turbo-f1/cfd'))
from prepare_gap_control import gap_spec,dictionary

class GapControlTests(unittest.TestCase):
    def test_resolution_comes_from_actual_block_height_and_source_gap(self):
        c=[dict(closed=True,bounds_mm=[[-3,-3,-1],[3,3,2]]),dict(closed=True,bounds_mm=[[-1,-1,2.5],[1,1,4]])]
        text='vertices ((0 0 0) (.01 0 0) (.01 .01 0) (0 .01 0) (0 0 .004) (.01 0 .004) (.01 .01 .004) (0 .01 .004)); blocks (hex (0 1 2 3 4 5 6 7) rotorZone (2 2 5));'
        s=gap_spec(c,text);self.assertEqual(s['level'],3);self.assertEqual(s['parent_max_axial_cell_mm'],.8);self.assertLessEqual(s['predicted_axial_cell_mm'],.5/4)
        out=dictionary('geometry {} refinementRegions {} snap false;',s)
        self.assertIn('levels ((1e15 3))',out);self.assertIn('snap false;',out)
        with self.assertRaises(ValueError):dictionary(out,s)
        c[1]['bounds_mm'][0][2]=2
        with self.assertRaises(ValueError):gap_spec(c,text)
        c[1]['bounds_mm'][0][2]=2.01
        with self.assertRaises(ValueError):gap_spec(c,text)
        with self.assertRaises(ValueError):gap_spec(c[:1],text)
