"""Independent small checks of the contour construction and mass bound."""
import importlib.util
import json
from math import comb
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('reinforcement_contour',SOURCE/'build.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def bezier(points,t):
    n=len(points)-1
    return [sum(comb(n,i)*t**i*(1-t)**(n-i)*p[k] for i,p in enumerate(points))
            for k in range(len(points[0]))]


class ContourTest(unittest.TestCase):
    def test_degree_elevation_keeps_original_centreline(self):
        plan=json.loads((SOURCE/'plan.json').read_text())
        for name in ('root_centreline_XY_mm','central_centreline_XY_mm'):
            points=plan[name];elevated=module.elevated(points)
            for i in range(101):
                original=bezier(points,i/100);new=bezier(elevated,i/100)
                self.assertLess(max(abs(a-b) for a,b in zip(original,new)),1e-12)

    def test_width_is_positive_bounded_and_C1_at_the_ends(self):
        for peak in (6.0,5.2):
            controls=module.width_controls(2.8,peak)
            self.assertEqual(controls[:2],[2.8,2.8]);self.assertEqual(controls[-2:],[2.8,2.8])
            self.assertAlmostEqual(bezier([[w] for w in controls],.5)[0],peak)
            for i in range(101):
                value=bezier([[w] for w in controls],i/100)[0]
                self.assertGreaterEqual(value,2.8-1e-12);self.assertLessEqual(value,peak+1e-12)

    def test_enclosing_volume_bound_stays_below_mass_ceiling(self):
        # Integrate 10t²(1-t)² dx/dt as exact rational coefficients.
        from fractions import Fraction as F
        plan=json.loads((SOURCE/'plan.json').read_text())
        def area(derivative,peak):
            f=[0,0,10,-20,10]
            result=sum(F(a*b,i+j+1) for i,a in enumerate(f) for j,b in enumerate(derivative))
            return result*(F(str(peak))-F('2.8'))/F('.625')
        volume=4*26*(area([45,-30,30],6.0)+area([15,-18,21],5.2))
        self.assertAlmostEqual(float(volume),plan['maximum_added_volume_upper_bound_mm3'],places=8)
        mass=float(volume)*plan['density_kg_mm3']
        self.assertAlmostEqual(mass,plan['maximum_added_mass_upper_bound_kg'],places=12)
        self.assertLess(plan['base_mass_kg']+mass,plan['mass_ceiling_kg'])


if __name__=='__main__':
    unittest.main()
