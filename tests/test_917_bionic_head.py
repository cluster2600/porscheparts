"""Bounded design searches and cam geometry must preserve their stated assumptions."""
import importlib.util
import math
import json
import hashlib
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'models/917-engine-reconstruction/head-bionic'
sys.path.insert(0,str(HERE))
import optimize
import cams
sys.path.remove(str(HERE))


@unittest.skipUnless(importlib.util.find_spec('numpy'),'numerical runtime unavailable')
class BionicHeadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout,cls.packing=optimize.packing()
        cls.timing,cls.campaign=optimize.timing(cls.layout)

    def test_packing_is_feasible_and_maximal_over_declared_search(self):
        self.assertEqual(len(self.packing),625)
        self.assertGreaterEqual(self.layout['seat_ligament_mm'],2)
        self.assertGreaterEqual(self.layout['conservative_bore_margin_mm'],1.5)
        self.assertEqual(self.layout['face_area_mm2'],max(r['face_area_mm2'] for r in self.packing if r['passed']))

    def test_twelve_cycle_offsets_match_crank_tdc(self):
        cycles=cams.cycles()
        self.assertEqual(sorted(r['fire_tdc_deg'] for r in cycles),list(range(0,720,60)))
        self.assertEqual(len({(r['bank'],r['pair_index']) for r in cycles}),12)
        for row in cycles:
            self.assertEqual((row['fire_tdc_deg']+row['crank_phase_deg'])%360,0 if row['bank']==1 else 180)
            self.assertEqual((row['overlap_tdc_deg']-row['fire_tdc_deg'])%720,360)

    def test_selected_timing_carries_continuous_bound_and_mass_assumption(self):
        import numpy as np
        phi=np.linspace(0,4*math.pi,144001)
        for role in ('intake','exhaust'):
            selected=self.timing['roles'][role]
            self.assertEqual(len(self.campaign[role]),270)
            law=cams.cam_law(role,selected)
            diameter=self.layout[role+'_mm']
            gap=self.timing['face_z_mm']-diameter/2*math.sin(math.radians(8))+2
            gaps=gap+optimize.VT.piston_drop(phi,.066,.132)*1000-law.valve_lift(phi)*1000*math.cos(math.radians(8))
            self.assertLessEqual(selected['continuous_ideal_plane_gap_lower_bound_mm'],float(gaps.min()))
            self.assertGreaterEqual(selected['continuous_ideal_plane_gap_lower_bound_mm'],2)
            self.assertGreaterEqual(selected['quasistatic_outer_spring_margin_assumed_mass_kg_0_11'],1.25)

    def test_cam_offset_has_positive_area_and_avoids_declared_undercut_screen(self):
        import numpy as np
        for role in ('intake','exhaust'):
            for bank in (-1,1):
                for cycle in (r for r in cams.cycles() if r['bank']==bank):
                    polygon,screen=cams.section(role,self.timing['roles'][role],bank,cycle['overlap_tdc_deg'])
                    area=np.sum(polygon[:,0]*np.roll(polygon[:,1],-1)-polygon[:,1]*np.roll(polygon[:,0],-1))/2
                    self.assertGreater(area,math.pi*20**2)
                    self.assertGreater(screen['minimum_positive_pitch_curvature_radius_mm'],8)
                    self.assertLess(screen['max_ideal_pressure_angle_deg'],35)

    def test_inner_spring_is_not_counted_as_force_validation(self):
        p=optimize.law_parameters('intake',9.5,240,120)
        self.assertEqual(p['spring_wire_diameter_mm']['value'],4)
        self.assertEqual(p['lash_cold_mm']['value'],.1)
        self.assertEqual(p['spring_wire_diameter_mm']['status'],'assumed')

    def test_interface_contract_does_not_promote_assumed_attachments(self):
        contract=json.loads((HERE/'interface-contract.json').read_text())
        self.assertEqual(contract['status'],'open_measured_interfaces_required')
        for row in contract['interfaces']:
            self.assertIsNone(row['measured_datums'])
            self.assertIsNone(row['approved_tolerances'])
        for name in ('actual_alloy','professional_review','approved_physical_validation_plan'):
            self.assertIsNone(contract[name])
        for name in ('functional_assembly_accepted','manufacturing_authorized','engine_start_authorized'):
            self.assertIs(contract[name],False)

    def test_execution_is_bound_to_current_sources_and_keeps_release_closed(self):
        record=json.loads((HERE/'execution-20261012.json').read_text())
        self.assertEqual(record['definitions'],137)
        self.assertEqual(record['assembly_occurrences'],1285)
        for name in ('manufacturing_authorized','engine_start_authorized','functional_assembly_accepted'):
            self.assertIs(record[name],False)
        for relative,digest in record['source_sha256'].items():
            path=(ROOT/relative).resolve()
            self.assertTrue(path.is_relative_to(ROOT))
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),digest,relative)
        preview=HERE/'head-surfaces-20261012.png'
        self.assertEqual(hashlib.sha256(preview.read_bytes()).hexdigest(),record['head_preview_sha256'])
        self.assertTrue(record['sampled_valve_piston_cylinder_and_head_contacts_zero'])
        self.assertIsNone(record['actual_alloy'])
        self.assertIsNone(record['measured_interfaces'])


if __name__=='__main__':unittest.main()
