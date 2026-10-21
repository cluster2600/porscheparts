"""Integration-volume and unequal-volume percentile controls for carrier reports."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/compare_accepted_fields.py'
spec=importlib.util.spec_from_file_location('_carrier_comparison',SOURCE);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ComparisonTests(unittest.TestCase):
    def test_alternative_solver_changes_one_directive_and_preserves_physics(self):
        path=SOURCE.with_name('prepare_iterative_solver.py');spec=importlib.util.spec_from_file_location('_carrier_solver',path);solver=importlib.util.module_from_spec(spec);spec.loader.exec_module(solver)
        deck='*STATIC,SOLVER=SPOOLES\n*BOUNDARY\nFIXED,1,3\n*CLOAD\n1,3,-4000\n';changed=solver.iterative_deck(deck)
        self.assertEqual(changed.replace('ITERATIVE CHOLESKY','SPOOLES'),deck)
        for bad in ['',deck+deck,'** *STATIC,SOLVER=SPOOLES\n']:
            with self.assertRaises(ValueError):solver.iterative_deck(bad)

    def test_volume_weighting_does_not_count_small_elements_as_equal_material(self):
        self.assertEqual(module.weighted_quantile(np.array([10.,100.]),np.array([99.,1.]),.95),10.)
        with self.assertRaises(ValueError):module.weighted_quantile(np.array([10.]),np.array([-1.]),.95)

    def test_linear_and_quadratic_unit_simplex_have_same_integrated_volume(self):
        corners=np.array([[0.,0,0],[1.,0,0],[0,1.,0],[0,0,1.]])
        edges=[(0,1),(1,2),(0,2),(0,3),(1,3),(2,3)];vertices=np.vstack([corners,[(corners[i]+corners[j])/2 for i,j in edges]])
        for count in [4,10]:
            positions,weights=module.samples(vertices,np.arange(count)[None,:],None)
            self.assertAlmostEqual(float(weights.sum()),1/6,places=14)
            np.testing.assert_allclose(np.average(positions,axis=0,weights=weights),[.25,.25,.25],atol=1e-14)
            self.assertTrue(np.all(weights>0))


if __name__=='__main__':unittest.main()
