"""Reproducible G6 limits: candidate CAD, heat balance, beam and cavity counterexamples."""
import math
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FV = ROOT/'twins/m64-cylinder-head/source/fourvalve'
sys.path[:0] = [str(FV),str(FV/'cad')]
import g6_screen as g

try:
    import cadquery as cq
    import audit_g6 as audit
    import carrier
    import assembly
    import components as comp
except ImportError:
    cq = None


class G6Screens(unittest.TestCase):
    def test_fin_two_methods_converge_and_reject_invalid_input(self):
        args=(.15,.003,.0155,150.,160.)
        exact=g.fin_conductance(*args)
        errors=[abs(g.fin_conductance(*args,cells=n)/exact-1) for n in (8,16,32)]
        self.assertGreater(errors[0],errors[1]);self.assertGreater(errors[1],errors[2])
        self.assertLess(errors[-1],1e-4)
        self.assertLess(exact,160*2*(.15+.003)*.0155)
        for k in (0,-1,math.nan):
            with self.assertRaises(ValueError):g.fin_conductance(.15,.003,.0155,k,160)

    def test_beam_finite_elements_match_closed_form_and_scaling(self):
        a=g.shaft_beam(1000,110,20,10)
        self.assertAlmostEqual(a['centre_deflection_mm'],a['beam_FE_deflection_mm'],places=10)
        b=g.shaft_beam(1000,110,20,20)
        self.assertAlmostEqual(a['centre_deflection_mm']/b['centre_deflection_mm'],16)
        self.assertAlmostEqual(a['bending_stress_MPa']/b['bending_stress_MPa'],8)
        with self.assertRaises(ValueError):g.shaft_beam(1000,110,56,10)

    def test_thermal_budget_is_failed_not_promoted_to_qualification(self):
        p,c=g.inputs();t=g.thermal(p,c)
        self.assertFalse(t['any_scenario_meets_heat_budget'])
        self.assertGreater(t['smallest_deficit_W'],0)
        self.assertEqual(t['fin_count'],10)
        self.assertGreater(t['minimum_hypothetical_demand_W'],17000)
        for case in t['oil_scenarios']:
            self.assertFalse(case['actual_gravity_return_flow_or_cooling_validated'])

    def test_hot_fit_and_load_failures_remain_visible(self):
        p,c=g.inputs();fit=g.hot_fits(p);m=g.mechanics(p,c)
        self.assertFalse(fit['retention_qualified'])
        self.assertIsNone(fit['seat_cold_interference_selected_mm'])
        # Worst listed case: 13.06*(1+10e-6*175) - 13*(1+22e-6*275).
        self.assertAlmostEqual(min(r['guide_free_interference_mm'] for r in fit['cases']),.004205,places=9)
        self.assertTrue(any(not r['no_forced_lift_contact_loss'] for r in m['force_scenarios']))
        self.assertTrue(all(not r['shaft_deflection_below_assumed_budget'] for r in m['force_scenarios']))
        for row in m['force_scenarios']:
            beam=row['shaft_beam_bound']
            self.assertAlmostEqual(beam['centre_deflection_mm'],beam['beam_FE_deflection_mm'],places=9)
        self.assertTrue(all(r['max_separation_mm']>1 for r in m['compliant_contact_time_step_study']))

    @unittest.skipUnless(cq,'cadquery absent')
    def test_closed_cavity_is_detected_and_open_bore_is_not(self):
        box=cq.Solid.makeBox(10,10,10)
        closed=box.cut(cq.Solid.makeBox(4,4,4,cq.Vector(3,3,3)))
        result=audit.closed_voids(closed)
        self.assertFalse(result['no_enclosed_void_detected'])
        self.assertAlmostEqual(sum(result['enclosed_void_volumes_mm3']),64)
        opened=closed.cut(cq.Solid.makeCylinder(1,10,cq.Vector(5,5,5)))
        self.assertTrue(audit.closed_voids(opened)['no_enclosed_void_detected'])

    @unittest.skipUnless(cq,'cadquery absent')
    def test_carrier_is_separate_valid_connected_and_clear_of_existing_parts(self):
        p,_=g.inputs();parts=carrier.parts(p)
        self.assertEqual(len(parts),18)
        self.assertTrue(all(assembly.brep_valid(s) and len(s.Solids())==1 for s in parts.values()))
        head=carrier.modify_head(p,comp.head(p))
        self.assertTrue(assembly.brep_valid(head));self.assertEqual(len(head.Solids()),1)
        studs=comp.studs(p)
        for name,shape in parts.items():
            self.assertLess(audit.overlap(shape,head),1e-5,name)
            self.assertLess(audit.overlap(shape,studs),1e-5,name)
        for sy in (-1,1):self.assertLess(audit.overlap(carrier.returns(p,sy),head),1e-5)
        with self.assertRaises(ValueError):carrier.parts(dict(p,carrier_wall_thickness=30))


if __name__=='__main__':
    unittest.main()
