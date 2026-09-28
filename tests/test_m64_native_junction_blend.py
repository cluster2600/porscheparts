import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'))


@unittest.skipUnless(importlib.util.find_spec('OCP') and importlib.util.find_spec('numpy'),
                     'optional native geometry runtime')
class NativeJunctionTests(unittest.TestCase):
    def test_air_material_and_ambiguous_segments(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
        from OCP.gp import gp_Pnt
        from trial_native_junction_blend import segment_kind
        body = BRepPrimAPI_MakeBox(.06, 1., 1.).Shape()
        cavity = BRepPrimAPI_MakeBox(gp_Pnt(.02, .2, .2), .02, 1., 1.).Shape()
        body = BRepAlgoAPI_Cut(body, cavity).Shape()
        kind, width = segment_kind(body, [0, .5, .5], [.02, .5, .5])
        self.assertEqual(kind, 'material_lip'); self.assertAlmostEqual(width, .02)
        kind, width = segment_kind(body, [.02, .5, .5], [.04, .5, .5])
        self.assertEqual(kind, 'air_gap'); self.assertAlmostEqual(width, .02)
        for a, b in (([.005, .5, .5], [.02, .5, .5]),
                     ([0, .5, .5], [0, .5, .5]),
                     ([float('nan'), .5, .5], [.02, .5, .5])):
            with self.assertRaises(ValueError): segment_kind(body, a, b)


if __name__ == '__main__': unittest.main()
