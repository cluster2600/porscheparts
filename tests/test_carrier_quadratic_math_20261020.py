"""Independent polynomial-map and energy controls for the quadratic study."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020'


def load(name):
    spec=importlib.util.spec_from_file_location('_test_'+name,SOURCE/(name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class QuadraticMathTests(unittest.TestCase):
    def test_exact_straight_map_and_negative_orientation(self):
        module=load('audit_quadratic_mapping');corners=[(0,0,0),(1000,0,0),(0,1000,0),(0,0,1000)];points=corners+[tuple((corners[i][k]+corners[j][k])//2 for k in range(3))for i,j in module.EDGES]
        numerator,det,delta=module.integer_cell_bound(points);self.assertEqual((numerator,det,delta),(0,10**9,0));points[1],points[2]=points[2],points[1];self.assertIsNone(module.integer_cell_bound(points))

    def test_nonzero_midside_perturbation_bounds_whole_derivative(self):
        module=load('audit_quadratic_mapping');corners=[(0,0,0),(1000,0,0),(0,1000,0),(0,0,1000)];points=corners+[tuple((corners[i][k]+corners[j][k])//2 for k in range(3))for i,j in module.EDGES];points[4]=(500,0,1)
        numerator,det,delta=module.integer_cell_bound(points);self.assertEqual((numerator,det,delta),(16000000,1000000000,2));self.assertGreaterEqual(numerator/det,.012)

    def test_whole_quadratic_stress_energy_recovers_analytic_polynomial(self):
        reader=load('assess_quadratic_mechanics');corners=np.array([[0.,0,0],[1.,0,0],[0,1.,0],[0,0,1.]]);points=np.vstack([corners,[(corners[i]+corners[j])/2 for i,j in reader.EDGES]]);E=107000.;nu=.31;A=1e-6;mu=E/(2*(1+nu));lam=E*nu/((1+nu)*(1-2*nu));low=(5-np.sqrt(5))/20;bary=np.full((4,4),low);np.fill_diagonal(bary,1-3*low);strain=2*A*bary[:,1]
        stress=np.column_stack([(lam+2*mu)*strain,lam*strain,lam*strain,np.zeros((4,3))])[None,:,:];energy,volume=reader.stress_energy(points,np.arange(10)[None,:],stress,E,nu,np)
        # Integral x^2 over the unit reference tetrahedron is exactly 1/60.
        self.assertAlmostEqual(volume,1/6,places=14);self.assertLess(abs(energy/(2*(lam+2*mu)*A*A/60)-1),1e-13)


if __name__=='__main__':unittest.main()
