import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'))


@unittest.skipUnless(importlib.util.find_spec('OCP') and importlib.util.find_spec('numpy'),
                     'optional native geometry runtime')
class NativeChamferTests(unittest.TestCase):
    def test_bounded_chamfer_matches_analytic_box_volume_and_rejects_bad_inputs(self):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        from OCP.TopAbs import TopAbs_EDGE
        from trial_native_junction_chamfer import prepare_chamfer, tolerances_not_increased, indexed
        body = BRepPrimAPI_MakeBox(2., 2., 2.).Shape()
        edge = indexed(body, TopAbs_EDGE)[0]
        for distance in (0, -.01, .03, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                prepare_chamfer(body, edge, distance)
        maker = prepare_chamfer(body, edge, .02)
        maker.Build()
        self.assertTrue(maker.IsDone())
        self.assertTrue(BRepCheck_Analyzer(maker.Shape(), True, False, True).IsValid())
        props = GProp_GProps()
        BRepGProp.VolumeProperties_s(maker.Shape(), props)
        self.assertAlmostEqual(props.Mass(), 8.-.5*.02**2*2, places=10)
        before = {k: {'tolerance_max': 1e-7} for k in ('faces', 'edges', 'vertices')}
        self.assertTrue(tolerances_not_increased(before, before))
        for value in (1e-6, float('nan'), float('inf')):
            after = {**before, 'edges': {'tolerance_max': value}}
            self.assertFalse(tolerances_not_increased(before, after))


if __name__ == '__main__': unittest.main()
