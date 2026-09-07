import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'twins/m64-cylinder-head'


class LocalRepairSummaryTests(unittest.TestCase):
    def setUp(self):self.data=json.loads((BASE/'bernstein-local-repair-summary-20260907.json').read_text())

    def test_research_geometry_never_released_as_M64(self):
        p=self.data['provenance']
        self.assertEqual(p['geometry_role'],'935_scan_derived_research_reference')
        self.assertFalse(p['M64_interfaces_validated'])
        self.assertFalse(p['absolute_scale_certified'])
        self.assertTrue(p['master_unchanged'])
        self.assertFalse(any(self.data['readiness'].values()))
        self.assertFalse(self.data['evidence']['raw_geometry_published'])

    def test_paired_counts_and_local_gain(self):
        r=self.data['paired_rays']
        self.assertEqual(sum(r[k] for k in ('unchanged_within_1e_minus_5','increased','decreased','not_paired_resolved')),r['count'])
        self.assertAlmostEqual(r['target_after_scan_units']-r['target_before_scan_units'],.85,places=10)
        self.assertFalse(r['exhaustive_wall_thickness_proof'])
        self.assertEqual(r['remaining_known_weak_nonadjacent_rays'],4)

    def test_image_and_global_bound_have_exact_identity(self):
        e=self.data['evidence'];self.assertEqual(hashlib.sha256((BASE/e['image']).read_bytes()).hexdigest(),e['image_sha256'])
        b=self.data['global_scalar_displacement_bound'];receipt=json.loads((BASE/b['receipt']).read_text())
        self.assertEqual(receipt['input_sha256'],b['input_sha256'])
        self.assertTrue(receipt['proven_on_full_square'])
        self.assertEqual(receipt['max_absolute_value_bound_rounded_outward'],b['upper_bound_scan_units'])
        self.assertFalse(b['native_OCCT_roundoff_bound_included'])

    def test_summary_has_no_private_coordinates_or_indices(self):
        forbidden={'probe_private','entry_face_private','exit_face_private','target_uv_normalized_private','poles','source_poles','entry_xyz_scan_units','rows_private'}
        def walk(value):
            if isinstance(value,dict):
                self.assertFalse(forbidden & set(value))
                for child in value.values():walk(child)
            elif isinstance(value,list):
                for child in value:walk(child)
        walk(self.data)


if __name__=='__main__':unittest.main()
