import importlib.util
from pathlib import Path
import unittest

PATH=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/audit_transition_implicit_constraint.py'
spec=importlib.util.spec_from_file_location('implicit_bubble',PATH)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ImplicitBubbleTests(unittest.TestCase):
    def test_product_and_derivative(self):
        product=module.multiply({(1,0):1,(0,0):-1},{(0,1):1,(0,0):2})
        self.assertAlmostEqual(module.evaluate(product,.3,.4),(.3-1)*(.4+2))
        self.assertAlmostEqual(module.evaluate(module.derivative(product,0),.3,.4),2.4)

    def test_zero_value_and_gradient_at_squared_border(self):
        bubble={(2,0):1,(3,0):-2,(4,0):1}
        for u in (0.,1.):
            self.assertAlmostEqual(module.evaluate(bubble,u,.2),0.)
            self.assertAlmostEqual(module.evaluate(module.derivative(bubble,0),u,.2),0.)

    def test_bernstein_linear_elevation(self):
        coeff=module.bernstein_coefficients({(1,0):1,(0,1):2},8,8)
        for i in range(9):
            for j in range(9): self.assertAlmostEqual(coeff[i][j],i/8+2*j/8)

    def test_bounded_search_normalizes_symmetric_field(self):
        import numpy as np
        u,v=np.meshgrid(np.linspace(0,1,9),np.linspace(0,1,9))
        result=module.search_localized_exponents(u.ravel(),v.ravel(),np.ones(u.size),.5,.5,1.,3)
        self.assertEqual(result['searched_fields'],16)
        self.assertEqual(result['exponents'],[2,2,2,2])
        self.assertAlmostEqual(result['max_abs_D_scan_units'],.85)


if __name__=='__main__': unittest.main()
