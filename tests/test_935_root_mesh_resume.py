"""Keep geometric qualification separate from the refused real fluid mesh."""
import ast
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT/'docs/research/935-horizontal-cooling/root-mesh-resume-20261025.json'


class RootMeshResumeTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(RECORD.read_text())

    def test_executed_sources_are_preserved_and_parse(self):
        self.assertEqual(len(self.record['source_sha256']), 20)
        for name, expected in self.record['source_sha256'].items():
            path = ROOT/name
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected, name)
            if path.suffix == '.py': ast.parse(path.read_text())

    def test_actual_root_correction_protects_original_triangles_and_keeps_refusal(self):
        g = self.record['geometry']
        self.assertTrue(g['zero_closing_exact_original_STL_reproduction'])
        self.assertNotEqual(g['original_PicoGK_master_sha256'], g['candidate_sha256'])
        self.assertEqual((g['original_genus'], g['candidate_genus'], g['closed_inferred_root_passages']), (6, 1, 5))
        self.assertEqual((g['vertices'], g['triangles'], g['self_intersection_pairs']), (660003, 1320006, 0))
        self.assertTrue(all(g['protected_triangle_identity_to_original'].values()))
        self.assertEqual(g['protected_triangles'], {'acquired_region_r98': 544882, 'bore_region_r24': 83376})
        self.assertEqual(g['rejected_radius_1_2']['status'], 'refused_topology')
        self.assertEqual([g['analytic_controls'][name]['exit'] for name in ['closed', 'open', 'crossing']], [0, 3, 4])
        self.assertFalse(self.record['diagnostic_view']['decimation'])
        self.assertTrue(self.record['diagnostic_view']['colours_show_triangle_identity_only'])

    def test_changed_cube_catches_no_op_and_real_mesh_is_still_refused(self):
        r = self.record['reconstruction']; cube = r['moved_cube']
        self.assertTrue(r['legacy_Foundation13_zero_exit_was_no_op'])
        self.assertTrue(r['old_static_cube_did_not_prove_changed_mesh_reconstruction'])
        self.assertEqual(cube['Foundation13_legacy_command_exit'], 0)
        self.assertFalse(cube['legacy_command_wrote_mesh'])
        self.assertEqual(cube['translation_source_units'], [.125, 0, 0])
        self.assertEqual(cube['reconstructed_points'], 343)
        self.assertTrue(cube['every_reconstructed_coordinate_exact'])
        self.assertTrue(cube['native_full_quality_passed'])
        self.assertFalse(cube['original_global_mesh_copied'])
        self.assertFalse(cube['parent_processor_addressing_copied'])
        self.assertEqual(r['actual_utility'], 'reconstructPar')
        self.assertTrue(r['global_mesh_not_copied'])
        self.assertTrue(r['stale_processor_addressing_not_copied'])
        self.assertTrue(r['source_inputs_unchanged'])
        self.assertEqual((r['cells'], r['points'], r['faces']), (4666166, 6056698, 15223252))
        self.assertEqual((r['failed_native_checks'], r['concave_cells'], r['duplicate_non_baffle_face_warning']), (1, 316996, 2))
        self.assertFalse(r['extended_native_quality_passed'])
        self.assertTrue(r['complete_point_union_readback_pending'])
        self.assertTrue(r['complete_wall_and_volume_admission_pending'])
        self.assertTrue(self.record['snapping']['uses_previous_analysis_geometry'])
        self.assertFalse(self.record['snapping']['uses_new_root_candidate'])

    def test_mass_units_and_all_physical_admissions_remain_explicit(self):
        m = self.record['mass_properties']
        self.assertTrue(m['source_unit_assumed_mm'])
        self.assertFalse(m['scale_verified'])
        self.assertEqual(m['geometry_sha256'], self.record['geometry']['candidate_sha256'])
        self.assertEqual(len(m['mass_cases']), 10)
        for material in m['mass_cases']:
            self.assertAlmostEqual(material['conditional_mass_kg'],
                m['conditional_volume_mm3']*material['density_g_cm3']*1e-6, places=12)
        for name, value in self.record['scope'].items(): self.assertFalse(value, name)

    def test_complete_private_archives_are_verified_before_delivery(self):
        archives = self.record['private_archives']
        for name in ['root_geometry', 'native_mesh']:
            archive = archives[name]
            for flag in ['verified_on_Mac', 'verified_on_Kali1', 'server_digest_verified']:
                self.assertTrue(archive[flag], (name, flag))
            self.assertFalse(archive['CFD_accepted'])
            self.assertFalse(archive['manufacturing_authorized'])
        self.assertEqual(archives['root_geometry']['payloads'], 128)
        self.assertEqual((archives['native_mesh']['case_files'], archives['native_mesh']['unique_payloads']), (297, 143))
        self.assertTrue(archives['native_mesh']['all_members_and_references_verified'])


if __name__ == '__main__':
    unittest.main()
