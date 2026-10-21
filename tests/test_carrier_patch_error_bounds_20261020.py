"""Analytic controls for the complete-surface rational error bounds."""
from fractions import Fraction as F
import importlib.util
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/bounded_patch_tessellation.py'
SPEC=importlib.util.spec_from_file_location('bounded_carrier_patch',SOURCE)
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


class PatchErrorBoundTests(unittest.TestCase):
    def test_known_cubic_power_basis_has_exact_Bernstein_coefficients(self):
        self.assertEqual(M.power_to_bernstein([F(0),F(0),F(3),F(-2)],3),[0,0,1,1])

    def test_straight_curve_has_zero_parameterwise_chord_error(self):
        self.assertEqual(M.chord_bound([(F(0),F(0)),(F(1,2),F(1)),(F(1),F(2))]),0)

    def test_quadratic_subdivision_reduces_analytic_bound_by_four(self):
        points=[(F(0),F(0)),(F(1,2),F(1)),(F(1),F(0))]
        left,right=M.split_bezier(points)
        self.assertEqual(left[-1],right[0])
        self.assertEqual(M.chord_bound(points),1)
        self.assertEqual(M.chord_bound(left),F(1,4))
        self.assertEqual(M.chord_bound(right),F(1,4))

    def test_saddle_quad_triangle_difference_bound_is_exact_at_center(self):
        points=[(0,0,0),(0,1,0),(1,0,0),(1,1,1)]
        self.assertEqual(M.quad_triangle_bound(*[tuple(F(x)for x in p)for p in points]),F(1,4))

    def test_v_refinement_is_affine_and_bounds_every_accepted_interval(self):
        row={'A':(F(100),F(5),F(21)),'P':(F(100),F(5),F(20)),'B':(F(100),F(4),F(20))}
        segments=M.v_refine([F(1),F(.5**.5),F(1)],[row],F(3,200))
        self.assertTrue(all(s['V_error_L1']<=F(3,200)for s in segments))
        self.assertEqual(segments[0]['mixes'][0],(1,0,0))
        self.assertEqual(segments[-1]['mixes'][-1],(0,0,1))
        self.assertTrue(all(sum(mix)==1 and all(x>=0 for x in mix)for s in segments for mix in s['mixes']))

    def row(self):
        radii=[0,0,F(8,3),0,0];columns={k:[]for k in 'APBCD'}
        for i,r in enumerate(radii):
            x=F(i,4)
            for key,point in dict(A=(x,0,r),P=(x,0,0),B=(x,-r,0),C=(x,F(3,50),F(-3,50)),D=(x,F(3,50),r)).items():columns[key].append(point)
        return dict(aligned_curve=dict(degree=4,knots=[0,1],multiplicities=[5,5]),surfaces=[dict(name='arc',weights=[1,.5**.5,1],control_columns={k:columns[k]for k in 'APB'}),dict(name='bottom',control_columns={k:columns[k]for k in 'BC'}),dict(name='inside',control_columns={k:columns[k]for k in 'CD'}),dict(name='top',control_columns={k:columns[k]for k in 'DA'})])

    def test_complete_separated_monotone_section_sweep_is_proved(self):
        _,_,proof=M.profiles_and_injectivity(self.row())
        self.assertTrue(proof['strict_X_monotone'])
        self.assertTrue(proof['complete_control_separation_inequalities'])

    def test_shared_curve_mismatch_is_not_averaged(self):
        row=self.row();row['surfaces'][3]['control_columns']['A']=list(row['surfaces'][3]['control_columns']['A'])
        row['surfaces'][3]['control_columns']['A'][2]=(F(1,2),0,F(8,3)+F(1,10**15))
        with self.assertRaises(ValueError):M.profiles_and_injectivity(row)
