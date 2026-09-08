import importlib.util
import math
from pathlib import Path
import sys
import unittest

DIRECTORY=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake'
sys.path.insert(0,str(DIRECTORY))
spec=importlib.util.spec_from_file_location('candidate_roof',DIRECTORY/'build_candidate_chamber.py')
roof=importlib.util.module_from_spec(spec);spec.loader.exec_module(roof)


class CandidateRoofTests(unittest.TestCase):
    def test_plane_passes_through_each_existing_seat_lip(self):
        p=roof.inspection.design.Parameters(intake_x_mm=-18.,exhaust_x_mm=23.5)
        r=roof.roof_definition(p)
        s=math.sin(math.radians(p.bank_inclination_deg));c=math.cos(math.radians(p.bank_inclination_deg))
        for part in roof.inspection.design.valve_specs(p):
            profiles,_=roof.inspection.design.profiles(p,part)
            lip=min(z for _,z in profiles['seat'])
            sign=1 if part['kind']=='intake' else -1
            y=-part['center'][0]+sign*s*lip
            z=3+c*lip
            computed=r[part['kind']+'_intercept']-sign*r['slope_magnitude']*y
            self.assertAlmostEqual(computed,z,places=12)

    def test_ridge_and_base_are_derived_not_arbitrary_depth(self):
        r=roof.roof_definition(roof.inspection.design.Parameters(intake_x_mm=-18.,exhaust_x_mm=23.5))
        self.assertAlmostEqual(r['intake_intercept']-r['slope_magnitude']*r['ridge_y'],r['ridge_z'])
        self.assertAlmostEqual(r['exhaust_intercept']+r['slope_magnitude']*r['ridge_y'],r['ridge_z'])
        self.assertAlmostEqual(r['intake_intercept']-r['slope_magnitude']*r['intake_zero_y'],0.)
        self.assertAlmostEqual(r['exhaust_intercept']+r['slope_magnitude']*r['exhaust_zero_y'],0.)
        self.assertAlmostEqual(r['ridge_y'],-2.75)
        self.assertEqual(r['bounding_cylinder_radius'],50.)

    def test_unsupported_zero_inclination_rejected(self):
        with self.assertRaises(ValueError):
            roof.roof_definition(roof.inspection.design.Parameters(bank_inclination_deg=0.))


if __name__=='__main__':unittest.main()
