from _deps import require_modules
require_modules("numpy")

import importlib.util
from pathlib import Path
import unittest

PATH=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/trial_transition_bernstein.py'
spec=importlib.util.spec_from_file_location('bernstein_patch',PATH)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class BernsteinPatchTests(unittest.TestCase):
    def test_product_matches_factored_evaluation(self):
        a=[[.1,2.],[-.3,1.]];b=[[1.,-.1],[2.,.2],[.3,4.]]
        product=module.bernstein_product(a,b)
        for u,v in [(0.,0.),(.31,.62),(.99,.21),(1.,1.)]:
            self.assertAlmostEqual(module.bernstein_value(product,u,v),module.bernstein_value(a,u,v)*module.bernstein_value(b,u,v),places=12)

    def test_sparse_beta_factor(self):
        import math
        import numpy as np
        p,q,r,s=6,2,7,12
        coeff=np.zeros((p+q+1,r+s+1));coeff[p,r]=1/(math.comb(p+q,p)*math.comb(r+s,r))
        for u,v in [(.3,.7),(.8,.4),(0.,.3),(1.,.3)]:
            self.assertAlmostEqual(module.bernstein_value(coeff,u,v),u**p*(1-u)**q*v**r*(1-v)**s,places=15)


if __name__=='__main__':unittest.main()
