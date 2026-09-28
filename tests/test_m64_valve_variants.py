import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/valvetrain'))


@unittest.skipUnless(importlib.util.find_spec('numpy'), 'optional numpy runtime')
class ValveVariantTests(unittest.TestCase):
    def test_hollow_stem_ratios_and_bad_geometry(self):
        from screen_valve_variants import bore_properties
        result=bore_properties(6.,3.,60.)
        self.assertAlmostEqual(result['axial_area_ratio'],.75)
        self.assertAlmostEqual(result['bending_inertia_ratio'],.9375)
        self.assertAlmostEqual(result['radial_wall_mm'],1.5)
        self.assertEqual(bore_properties(6.,0.,60.)['removed_volume_mm3'],0)
        for args in ((6,6,60),(6,-1,60),(6,3,0),(6,float('nan'),60)):
            with self.assertRaises(ValueError): bore_properties(*args)


if __name__=='__main__': unittest.main()
