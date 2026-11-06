"""Independent known-loop, retracing and benign-profile controls for F2 admission."""
from pathlib import Path
import importlib.util
import unittest

try:
    import numpy as np
except ImportError:
    np=None

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipIf(np is None,'NumPy is required for canonical curve controls')
class SculptedProfileControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=ROOT/'twins/964-chassis/sculpted-cell-f2-20261106/audit_profile_curves.py'
        spec=importlib.util.spec_from_file_location('f2_profile_curve_audit',path)
        cls.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.module)

    def test_known_profile_loop_and_rigid_transform(self):
        points=np.array([[0,420,60],[0,395,370],[0,395,400],[0,430,400]],float)
        transform=np.array([[0,-1,0],[0,0,-1],[1,0,0]],float)
        for curve in [points,points@transform.T+[100,-200,300]]:
            loops,stationary=self.module.cubic_defects(*self.module.coefficients(curve,1,False))
            self.assertEqual(len(loops),1)
            np.testing.assert_allclose(loops[0]['parameters'],[.3144979199413828,.7518004226000536],rtol=0,atol=1e-10)
            self.assertLess(loops[0]['position_residual_mm'],1e-9)
            self.assertFalse(stationary)

    def test_collinear_retracing_is_nonregular(self):
        points=np.array([[-100,0,0],[0,0,0],[1,0,0],[100,0,0]],float)
        _,stationary=self.module.cubic_defects(*self.module.coefficients(points,1,False))
        self.assertEqual(len(stationary),2)
        self.assertTrue(all(0<x['parameter']<1 for x in stationary))

    def test_benign_closed_ellipse_at_rows_and_midpoint(self):
        theta=np.arange(12)*2*np.pi/12
        section=np.column_stack([np.zeros(12),30*np.cos(theta),20*np.sin(theta)])
        model={'components':[{'name':'ellipse','type':'tensor_catmull_rom_loft','closed_profile':True,
                              'sections_mm':[section.tolist(),(section+[100,0,0]).tolist()]}]}
        result=self.module.audit(model)
        self.assertTrue(result['profile_screen_passed'])
        self.assertEqual(result['profile_count'],3)

    def test_sampled_global_crossing_at_vertices_is_rejected(self):
        profile=[[0,-1,-1],[0,1,1],[0,-1,1],[0,1,-1]]
        model={'components':[{'name':'bow_tie','type':'planar_profile_cap','profile_mm':profile}]}
        result=self.module.audit(model)
        self.assertFalse(result['profile_screen_passed'])
        self.assertGreater(result['sampled_global_crossing_count'],0)


if __name__=='__main__':unittest.main()
