"""G7 independent reduced models and native support geometry; not release tests."""
import math
import sys
import unittest
from pathlib import Path

FV = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/fourvalve'
sys.path[:0] = [str(FV),str(FV/'cad')]
import g7

try:
    import cadquery as cq
    import assembly
    import audit_g6
except ImportError:
    cq = None


class G7Checks(unittest.TestCase):
    def test_shaft_two_methods_scaling_and_explicit_carrier_exclusion(self):
        for a in (10.,17.,23.):
            b = g7.point_span(7800,38,a,12.5)
            self.assertAlmostEqual(b['load_point_deflection_mm'],b['independent_FE_at_load_mm'],places=10)
            self.assertFalse(b['carrier_compliance_included'])
            larger = g7.point_span(7800,38,a,25.)
            self.assertAlmostEqual(b['load_point_deflection_mm']/larger['load_point_deflection_mm'],16.)
        for bad in (0.,-1.,math.nan,38.):
            with self.assertRaises(ValueError):g7.point_span(7800,38,bad,12.5)

    def test_finite_air_energy_balance_and_convergence(self):
        exact = g7.air_capacity(45,50,210)
        self.assertLess(exact,45*210);self.assertLess(exact,50*210)
        errors = [abs(g7.air_capacity(45,50,210,n)/exact-1) for n in (8,32,128)]
        self.assertGreater(errors[0],errors[1]);self.assertGreater(errors[1],errors[2])
        self.assertLess(errors[2],.003)
        with self.assertRaises(ValueError):g7.air_capacity(45,0,210)

    def test_design_comparison_preserves_failed_heat_and_valve_gates(self):
        p,c = g7.g6.inputs(); p['rocker_pivot_radius']=g7.DESIGN['rocker_pivot_radius']
        result = g7.screens(p,c,g7.baseline())
        self.assertEqual(len(result['shaft_comparison']),72)
        self.assertTrue(all(x['shaft_only_below_0p04_mm'] for x in result['shaft_comparison']))
        self.assertTrue(all(not x['clearance_plus_shaft_below_0p04_mm'] for x in result['shaft_comparison']))
        self.assertTrue(all(not x['assembly_stiffness_qualified'] for x in result['shaft_comparison']))
        self.assertEqual(sum(x['unchanged_forced_lift_contact_loss'] for x in result['shaft_comparison']),26)
        for rows in result['cooling_comparison'].values():
            for case in rows:
                self.assertFalse(case['fan_operating_point_verified'])
                if case['heat_W'] is not None:
                    self.assertGreater(case['deficit_to_lowest_G6_hypothetical_duty_W'],0)
        q = dict(p,**{k:v for k,v in g7.DESIGN.items() if k.startswith('fin_')})
        self.assertIsNone(g7.channel_case(q,.1,187)['heat_W'])
        self.assertIsNone(g7.channel_case(q,.001,187)['heat_W'])
        self.assertGreater(g7.channel_case(q,.05,187)['heat_W'],g7.channel_case(p,.05,187)['heat_W'])
        self.assertGreater(g7.channel_case(q,.05,187)['pressure_drop_Pa'],g7.channel_case(p,.05,187)['pressure_drop_Pa'])

    @unittest.skipUnless(cq,'cadquery absent')
    def test_native_supports_and_head_keep_no_penetrations(self):
        p,_ = g7.g6.inputs();p['rocker_pivot_radius']=g7.DESIGN['rocker_pivot_radius']
        p.update({k:v for k,v in g7.DESIGN.items() if k.startswith('fin_')})
        shapes,added=g7.parts(p)
        before=g7.native_bounds(shapes['head'])
        shapes['head'].tessellate(.05,.15)
        self.assertEqual(before,g7.native_bounds(shapes['head']))
        self.assertAlmostEqual(before['ymax'],79.)
        self.assertEqual(len(shapes),64)
        self.assertTrue(all(assembly.brep_valid(s) and len(s.Solids())==1 for s in shapes.values() if s is not shapes['studs']))
        names=list(shapes)
        for i,a in enumerate(names):
            for b in names[i+1:]:
                if a in added or b in added:
                    self.assertLess(audit_g6.overlap(shapes[a],shapes[b]),1e-5,(a,b))
        self.assertAlmostEqual(p['rocker_boss_radius']-p['rocker_pivot_radius']-p['rocker_radial_clearance'],1.7)
        self.assertTrue(audit_g6.closed_voids(shapes['central_diaphragm'])['no_enclosed_void_detected'])
        with self.assertRaises(ValueError):g7.support_positions(dict(p,rocker_width=60),'exhaust')


if __name__=='__main__':unittest.main()
