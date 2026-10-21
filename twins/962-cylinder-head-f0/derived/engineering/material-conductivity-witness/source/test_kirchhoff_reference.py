"""Prepared stdlib oracle selfchecks; no solver, scientific import or CSV parser."""
from decimal import Decimal as D
import unittest
from kirchhoff_reference import conductivity, primitive, temperature, axial_flux_density, gauss2_average


class KirchhoffReference(unittest.TestCase):
    def test_exact_literal_integrals_and_signed_powers(self):
        for direction,integral,power in [('Z','37.10525','7.42105'),('XY','35.0315','7.0063')]:
            self.assertEqual(primitive(direction,250),D(integral))
            self.assertEqual(-2*axial_flux_density(direction),D(power))
            self.assertEqual(primitive(direction,23),0)

    def test_literal_measured_knots(self):
        for direction,values in [('Z',['.1629','.1636','.1654','.1605']),('XY',['.1546','.1544','.1549','.1522'])]:
            for t,k in zip([23,150,200,250],values):
                self.assertEqual(conductivity(direction,t),D(k))

    def test_exact_endpoints_and_non_linear_midpoint(self):
        for direction in ['Z','XY']:
            self.assertEqual(temperature(direction,0),23)
            self.assertEqual(temperature(direction,10),250)
            self.assertNotEqual(temperature(direction,5),D('136.5'))
            self.assertLess(abs(primitive(direction,temperature(direction,5))-primitive(direction,250)/2),D('1e-50'))

    def test_strict_range_and_nonfinite_refusal(self):
        for value in [22,251,'NaN','Infinity',True]:
            with self.assertRaises(ValueError):conductivity('Z',value)
            with self.assertRaises(ValueError):primitive('Z',value)
        for value in [-1,11,'NaN',True]:
            with self.assertRaises(ValueError):temperature('XY',value)
        with self.assertRaises(ValueError):conductivity('CP1',150)

    def test_linear_segment_gauss_average_and_sign(self):
        self.assertEqual(gauss2_average('Z',23,150),(D('.1629')+D('.1636'))/2)
        self.assertEqual(gauss2_average('XY',200,200),D('.1549'))
        self.assertLess(axial_flux_density('Z'),0)
        self.assertLess(axial_flux_density('XY'),0)


if __name__=='__main__':unittest.main()
