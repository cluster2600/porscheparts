"""Analytic circle/counterexample checks for complete rational radial bounds."""
from fractions import Fraction as F
import importlib.util
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/rational_cylinder_certificate.py'
spec=importlib.util.spec_from_file_location('_rational_radial_math',SOURCE);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class RationalRadiusTests(unittest.TestCase):
    def test_exact_rational_circle_has_zero_complete_residual(self):
        # Tangents at (1,0) and (-7/25,24/25) meet at (1,4/3).
        poles=[[(F(1),F(0))],[(F(1),F(4,3))],[(F(-7,25),F(24,25))]]
        result=module.radial_bound(poles,[[F(1)],[F(3,5)],[F(1)]],(0,0),1)
        self.assertEqual(F(result['complete_radial_deviation_bound_mm']),0)
        self.assertTrue(all(F(x)==0 for row in result['residual_Bernstein_coefficients']for x in row))

    def test_constant_point_radial_error_is_covered(self):
        result=module.radial_bound([[(F(61,100),F(0))]],[[1]],(0,0),F(3,5))
        self.assertGreaterEqual(F(result['complete_radial_deviation_bound_mm']),F(1,100))
        self.assertEqual(F(result['maximum_squared_radius_residual_mm2']),F(121,10000))

    def test_nonpositive_weights_are_refused(self):
        for weight in [0,-1]:
            with self.assertRaises(ValueError):module.radial_bound([[(1,0)]],[[weight]],(0,0),1)

    def test_exact_circle_centre_is_recovered_from_three_points(self):
        centre=module.centre_through_three([(1,0),(0,1),(-1,0)])
        self.assertEqual(centre,(F(0),F(0)))
        with self.assertRaises(ValueError):module.centre_through_three([(0,0),(1,0),(2,0)])

    def test_native_certificate_replays_with_independent_power_basis_algebra(self):
        import hashlib
        import json
        from math import comb
        root=Path(__file__).resolve().parents[1]
        evidence=root/'docs/reports/carrier-resume-20261020/evidence/rounded-native-radius-certificate-002/assessment.json'
        data=json.loads(evidence.read_text())
        body=SOURCE.parent/'rounded-native-study/candidate-native.brep'
        self.assertIn(hashlib.sha256(body.read_bytes()).hexdigest(),data['source_sha256'].values())
        self.assertEqual(len(data['faces']),4)
        self.assertEqual(data['fixed_readback_limit_mm'],1e-8)
        def square(a):
            result=[F(0)]*5
            for i,x in enumerate(a):
                for j,y in enumerate(a):result[i+j]+=x*y
            return result
        maximum=F(0)
        for face in data['faces']:
            points=face['poles_xyz_mm'];weights=face['weights'];cx,cz=map(F,face['axis_parallel_Y_centre_XZ_Q'])
            for i in range(3):
                self.assertTrue(all((points[i][j][0],points[i][j][2],weights[i][j])==(points[i][0][0],points[i][0][2],weights[i][0])for j in range(5)))
            w=[F(weights[i][0])for i in range(3)]
            def power(b):return[b[0],2*(b[1]-b[0]),b[0]-2*b[1]+b[2]]
            x=power([w[i]*(F(points[i][0][0])-cx)for i in range(3)])
            z=power([w[i]*(F(points[i][0][2])-cz)for i in range(3)])
            ww=square(power(w));xx=square(x);zz=square(z)
            polynomial=[xx[i]+zz[i]-F(9,25)*ww[i]for i in range(5)]
            bernstein=[sum(polynomial[i]*F(comb(k,i),comb(4,i))for i in range(k+1))for k in range(5)]
            declared=face['pieces'][0]
            self.assertEqual(bernstein,[F(row[0])for row in declared['residual_Bernstein_coefficients']])
            bound=max(map(abs,bernstein))/(min(w)**2*F(3,5))
            self.assertEqual(bound,F(face['complete_radial_deviation_bound_mm']))
            maximum=max(maximum,bound)
        self.assertEqual(maximum,F(data['maximum_complete_radial_deviation_mm']))
        self.assertLessEqual(maximum,F(1,100000000))
