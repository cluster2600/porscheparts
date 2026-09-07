import importlib.util
from dataclasses import replace
from pathlib import Path
import math
import hashlib
import json
import sys
import unittest


PATH=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/build_four_valve_distribution.py'
spec=importlib.util.spec_from_file_location('m64_distribution_design',PATH)
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)


class FourValveDistributionTests(unittest.TestCase):
    def test_defaults_and_outward_axes(self):
        p=module.Parameters().validate();valves=module.valve_specs(p)
        self.assertEqual(len(valves),4)
        for v in valves:
            self.assertGreater(v['center'][0]*math.sin(math.radians(v['axis_angle_deg'])),0.)
            self.assertLess(-v['max_lift_mm']*math.cos(math.radians(v['axis_angle_deg'])),0.)

    def test_conical_contact_and_guide_clearance(self):
        p=module.Parameters()
        for spec in module.valve_specs(p):
            profiles,(inner,outer)=module.profiles(p,spec)
            self.assertAlmostEqual(outer-inner,1.)
            valve=profiles['valve'];seat=profiles['seat'];guide=profiles['guide']
            self.assertEqual(valve[3],seat[-1])
            r=spec['diameter_mm']/2
            self.assertAlmostEqual(seat[0][1],(r-seat[0][0])*math.tan(math.radians(p.seat_angle_from_transverse_plane_deg)))
            self.assertAlmostEqual(2*guide[0][0]-p.stem_diameter_mm,spec['guide_diametral_clearance_mm'])

    def test_selected_lifts_not_cam_law(self):
        p=module.Parameters();states=module.lift_states(p)
        self.assertEqual(len(states),7)
        self.assertEqual(states[0]['intake_mm'],0.)
        self.assertEqual(states[4]['intake_mm'],11.5)
        self.assertEqual(states[4]['exhaust_mm'],9.6)

    def test_no_scan_or_manufacturing_claim(self):
        report=module.initial_report(module.Parameters())
        self.assertTrue(all(value is False for value in report['scope'].values()))
        self.assertIn('not_scan',report['length_unit'])

    def test_reject_invalid_guide_and_stem_engagement(self):
        p=module.Parameters()
        for invalid in (replace(p,guide_outer_diameter_mm=5.),replace(p,stem_tip_above_gauge_mm=60.),
                        replace(p,bank_inclination_deg=90.),replace(p,intake_x_mm=20.)):
            with self.assertRaises(ValueError):invalid.validate()

    def test_native_artifact_integrity_and_explicit_limits(self):
        directory=PATH.parent.parent/'evidence/four-valve-design-20260907'
        build=json.loads((directory/'build-report.json').read_text())
        audit=json.loads((directory/'audit-report.json').read_text())
        self.assertEqual(len(build['parts']),12)
        self.assertEqual(len(audit['states']),7)
        self.assertEqual(audit['failed_checks'],[])
        self.assertGreaterEqual(audit['seat_envelope_minimum_gap_mm'],1.5)
        self.assertLess(min(row['minimum_valve_bore_gap_mm'] for row in audit['states']),1.)
        self.assertFalse(audit['manufacturing_authorized'])
        self.assertFalse(build['scope']['M64_fitment_validated'])
        self.assertFalse(build['scope']['springs_selected_or_modeled'])
        for name in ('closed','simultaneous_100pct'):
            self.assertEqual(hashlib.sha256((directory/(name+'.step')).read_bytes()).hexdigest(),build[name+'_step']['sha256'])
            self.assertEqual(build[name+'_step']['solid_count_after_import'],12)
            self.assertTrue(build[name+'_step']['brep_valid_after_import'])

    def test_v2_tradeoff_is_preserved_not_claimed_pareto_improvement(self):
        directory=PATH.parent.parent/'evidence/four-valve-design-v2-20260907'
        report=json.loads((directory/'placement-comparison.json').read_text())
        self.assertEqual(report['translation_X_mm'],1.5)
        self.assertFalse(report['diameters_or_component_profiles_changed'])
        self.assertTrue(report['worst_case_global_improved'])
        self.assertFalse(report['no_regression_in_each_state_minimum'])
        self.assertAlmostEqual(report['maximum_valve_pair_gap_absolute_delta_mm'],0.)
        self.assertGreaterEqual(report['candidate_seat_envelope_gap_mm'],2.)
        decreases=[r['state'] for r in report['state_comparison'] if r['decreased_beyond_numerical_tolerance']]
        self.assertEqual(decreases,['intake_only_max'])
        self.assertFalse(report['manufacturing_authorized'])
        self.assertEqual(hashlib.sha256((directory/'closed.step').read_bytes()).hexdigest(),report['candidate_closed_STEP_sha256'])

    def test_exact_integrity_receipts_bind_both_assemblies(self):
        for name in ('four-valve-design-20260907','four-valve-design-v2-20260907'):
            directory=PATH.parent.parent/'evidence'/name
            report=json.loads((directory/'exact-integrity-report.json').read_text())
            self.assertFalse(report['new_geometry_constructed'])
            self.assertFalse(report['manufacturing_authorized'])
            for pose,record in report['artifacts'].items():
                self.assertTrue(record['BRepCheck_exact_method'])
                self.assertTrue(record['all_solids_BRepCheck_exact_method'])
                self.assertTrue(record['STEP_millimetre_unit_present'])
                self.assertEqual(record['solid_count'],12)
                self.assertEqual(hashlib.sha256((directory/(pose+'.step')).read_bytes()).hexdigest(),record['STEP_sha256'])


if __name__=='__main__':unittest.main()
