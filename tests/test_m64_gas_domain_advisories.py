import importlib.util
import copy
from pathlib import Path
import sys
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake'
sys.path.insert(0,str(SOURCE))
import audit_gas_domain_advisories as audit


class MeshAttemptTests(unittest.TestCase):
    def fixture(self):
        return {'native_check':{'BRep_valid_exact_method':True,'topology_counts':{'solid':1}},
            'original_native_BOP':{'has_errors':False,'faults':['BOPAlgo_GeomAbs_C0']},
            'C0_entities':[{'shape_kind':'TopAbs_EDGE','status':'BOPAlgo_GeomAbs_C0',
                'curve':{'C0_internal_knots':[{'position_jump_native_numeric':0.,'tangent_angle_degrees':20.}]}}],
            'ambiguous_face_ownership':[{'ownership_evidence_pass':True} for _ in range(4)],
            'classified_boundary_assignment_complete':True,'all_inputs_unchanged':True}

    def test_geometric_kink_is_not_a_universal_C1_rejection(self):
        self.assertTrue(audit.diagnostic_mesh_attempt_allowed(self.fixture()))

    def test_gap_other_fault_or_incomplete_boundary_is_not_waived(self):
        base=self.fixture()
        mutations=[lambda r:r['C0_entities'][0]['curve']['C0_internal_knots'][0].update(position_jump_native_numeric=1e-10),
            lambda r:r['original_native_BOP']['faults'].append('BOPAlgo_SelfIntersect'),
            lambda r:r.update(classified_boundary_assignment_complete=False),
            lambda r:r.update(all_inputs_unchanged=False),
            lambda r:r['ambiguous_face_ownership'][0].update(ownership_evidence_pass=False)]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                report=copy.deepcopy(base);mutate(report)
                self.assertFalse(audit.diagnostic_mesh_attempt_allowed(report))


@unittest.skipUnless(importlib.util.find_spec('OCP'),'native OCP runtime required')
class KnotTests(unittest.TestCase):
    def curve(self,coordinates):
        from OCP.Geom import Geom_BSplineCurve
        from OCP.TColgp import TColgp_Array1OfPnt
        from OCP.TColStd import TColStd_Array1OfReal,TColStd_Array1OfInteger
        from OCP.gp import gp_Pnt
        poles=TColgp_Array1OfPnt(1,3);knots=TColStd_Array1OfReal(1,3);mult=TColStd_Array1OfInteger(1,3)
        for i,p in enumerate(coordinates,1):poles.SetValue(i,gp_Pnt(*p))
        for i,(u,m) in enumerate(((0.,2),(1.,1),(2.,2)),1):knots.SetValue(i,u);mult.SetValue(i,m)
        return Geom_BSplineCurve(poles,knots,mult,1,False)

    def test_actual_right_angle_is_continuous_not_called_smooth(self):
        r=audit.bspline_knots(self.curve([(0,0,0),(1,0,0),(1,1,0)]),0.,2.)
        self.assertEqual(r['C0_internal_knots'][0]['position_jump_native_numeric'],0.)
        self.assertAlmostEqual(r['C0_internal_knots'][0]['tangent_angle_degrees'],90.)
        self.assertEqual(len(r['spans']),2)
        self.assertTrue(all(s['positive_weights'] for s in r['spans']))

    def test_parameter_speed_jump_need_not_be_tangent_break(self):
        r=audit.bspline_knots(self.curve([(0,0,0),(1,0,0),(3,0,0)]),0.,2.)
        k=r['C0_internal_knots'][0]
        self.assertEqual(k['tangent_angle_degrees'],0.)
        self.assertGreater(k['derivative_jump_norm'],0.)

    def test_knot_outside_trim_is_not_a_fault_within_trim(self):
        r=audit.bspline_knots(self.curve([(0,0,0),(1,0,0),(1,1,0)]),0.,.5)
        self.assertEqual(r['C0_internal_knots'],[])
        self.assertAlmostEqual(r['spans'][0]['arc_length_numeric_quadrature_not_bound'],.5)


if __name__=='__main__':unittest.main()
