import importlib.util
from pathlib import Path
import sys
import unittest


@unittest.skipUnless(importlib.util.find_spec('OCP') and importlib.util.find_spec('numpy'), 'optional native CAD runtime')
class UpperSupportTest(unittest.TestCase):
    def test_stepped_support_preserves_washer_and_spring_space(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'))
        from trial_upper_spring_support import CAD, annulus, support_pad, operation
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
        cad=CAD();row=dict(axis_origin=[0.,0.,0.],axis_direction=[0.,0.,1.])
        washer=annulus(cad,row,55.1,58.1,16.,7.)
        bore=annulus(cad,row,58.1,110.,16.,7.)
        spring=annulus(cad,row,59.6,100.,15.,7.75)
        for height in (0.,3.):
            pad=support_pad(cad,row,height)
            self.assertTrue(cad.valid(pad))
            self.assertEqual(cad.indexed(pad,cad.TopAbs_SOLID).Extent(),1)
            self.assertAlmostEqual(cad.volume(operation(cad,BRepAlgoAPI_Cut,washer,pad)),0.)
            for keepout in (bore,spring):
                overlap=operation(cad,BRepAlgoAPI_Common,pad,keepout)
                self.assertEqual(cad.indexed(overlap,cad.TopAbs_SOLID).Extent(),0)
                self.assertAlmostEqual(cad.volume(overlap),0.)
        for bad in (True,-1.,.01,float('nan')):
            with self.assertRaises(ValueError):support_pad(cad,row,bad)
        with self.assertRaises(ValueError):annulus(cad,{**row,'axis_direction':[0.,0.,2.]},0.,1.,2.,1.)
