"""Independent checks of the hypothetical distribution ratio, centres and profile."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'models/917-engine-reconstruction/cam-drive'
spec=importlib.util.spec_from_file_location('cam_drive_study',HERE/'drive.py')
drive=importlib.util.module_from_spec(spec);spec.loader.exec_module(drive)


class CamDriveTests(unittest.TestCase):
    def layout(self):
        y=378.6328391;z=40.588258
        return drive.layout({f'camshaft_{bank}_{role}':[sign*y,r*z] for bank,sign in [('negative',-1),('positive',1)] for role,r in [('intake',1),('exhaust',-1)]})

    def test_four_axes_exact_distances_and_positive_half_speed(self):
        layout=self.layout()
        self.assertEqual(len(layout['search']),16)
        for row in layout['trains']:
            self.assertEqual(row['idler_count'],5)
            self.assertEqual(row['speed_ratio_to_crank'][-1],.5)
            self.assertAlmostEqual(abs(row['centres_yz_mm'][-1][0]),378.6328391,places=9)
            self.assertAlmostEqual(abs(row['centres_yz_mm'][-1][1]),40.588258,places=9)
            for i,(a,b) in enumerate(zip(row['centres_yz_mm'],row['centres_yz_mm'][1:])):
                self.assertAlmostEqual(math.dist(a,b),drive.MODULE*(row['teeth'][i]+row['teeth'][i+1])/2,places=9)
            self.assertGreater(row['nonadjacent_tip_envelope_gap_mm'],50)
            self.assertGreater(min(row['contact_ratios']),1.5)

    def test_all_phases_obey_mesh_equation_over_full_crank_cycle(self):
        for row in self.layout()['trains']:
            for crank_degree in range(721):
                crank=math.radians(crank_degree)
                for i,(a,b) in enumerate(zip(row['centres_yz_mm'],row['centres_yz_mm'][1:])):
                    angle=math.atan2(b[1]-a[1],b[0]-a[0]);za,zb=row['teeth'][i:i+2]
                    pa=row['phase_rad'][i]+row['speed_ratio_to_crank'][i]*crank
                    pb=row['phase_rad'][i+1]+row['speed_ratio_to_crank'][i+1]*crank
                    residual=za*(angle-pa)+zb*(angle+math.pi-pb)-math.pi
                    self.assertAlmostEqual(math.remainder(residual,math.tau),0,places=9)

    def test_tooth_tip_root_pitch_thickness_and_guard(self):
        for teeth in drive.TEETH:
            points=drive.profile(teeth)
            radii=[math.hypot(*p) for p in points]
            pitch=drive.MODULE*teeth/2
            self.assertAlmostEqual(min(radii),pitch-1.25*drive.MODULE)
            self.assertAlmostEqual(max(radii),pitch+drive.MODULE)
            area=sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1]))/2
            self.assertGreater(area,math.pi*(pitch-1.25*drive.MODULE)**2)
            self.assertLess(area,math.pi*(pitch+drive.MODULE)**2)
            half=math.pi/(2*teeth)-drive.BACKLASH/(4*pitch)
            self.assertAlmostEqual(2*half*pitch,math.pi*drive.MODULE/2-drive.BACKLASH/2)
        with self.assertRaises(ValueError):drive.profile(8)
        with self.assertRaises(ValueError):drive.train([378,40],4)

    def test_rounded_ribs_cannot_protrude_into_tooth_spaces(self):
        for teeth in drive.TEETH:
            root=drive.MODULE*teeth/2-1.25*drive.MODULE
            for rib in (2.5,3.5):
                self.assertLess(drive.web_tip_radius(root,rib)+rib,root)
                self.assertGreater(drive.web_tip_radius(root,rib)+rib,root-3)

    def test_release_remains_closed_and_evidence_matches_sources(self):
        receipt=json.loads((HERE/'execution-20261012.json').read_text())
        for relative,digest in receipt['source_hashes'].items():
            self.assertEqual(hashlib.sha256((ROOT/relative).read_bytes()).hexdigest(),digest)
        for gate in ('manufacturing_authorized','engine_start_authorized','full_assembly_interference_checked','torsional_dynamics_checked','bearing_supports_defined'):
            self.assertIs(receipt[gate],False)
        for field in ('actual_alloy','manufacturing_process','professional_review'):
            self.assertIsNone(receipt[field])
        self.assertEqual(receipt['prototype_count'],142)
        self.assertEqual(receipt['instance_count'],1325)
        self.assertTrue(receipt['prior_turbo_prototypes_unchanged'])
        self.assertEqual(receipt['turbo_occurrences'],78)
        self.assertEqual(hashlib.sha256((HERE/'engine-surfaces.png').read_bytes()).hexdigest(),receipt['engine_preview_sha256'])
        self.assertTrue(receipt['all_sampled_gear_pairs_clear'])
        self.assertFalse(receipt['native_web_exact_containment_passed'])
        self.assertEqual(len(receipt['web_envelope_checks']),3)
        self.assertTrue(all(r['outside_dense_mm3']>0 for r in receipt['web_envelope_checks']))
        self.assertEqual(sum(r['phases_checked'] for r in receipt['mesh_motion']),144)
        self.assertEqual(hashlib.sha256((HERE/'drive-surfaces.png').read_bytes()).hexdigest(),receipt['preview_sha256'])


if __name__=='__main__':unittest.main()
