"""Keep the paused hex-mesh evidence distinct from geometry and CFD admission."""
import ast
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
RECORD=ROOT/'docs/research/935-horizontal-cooling/hex-mesh-continuation-20261022.json'


class HexMeshCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.record=json.loads(RECORD.read_text())

    def test_executed_sources_are_byte_preserved_and_parse(self):
        self.assertEqual(len(self.record['source_sha256']),16)
        for name,expected in self.record['source_sha256'].items():
            path=ROOT/name
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),expected,name)
            ast.parse(path.read_text())

    def test_user_pause_is_distinct_from_a_timeout_or_saved_snapped_mesh(self):
        self.assertEqual(self.record['status'],'paused_by_user_before_snapping_completion')
        serial,first,second=self.record['attempts']
        self.assertEqual([serial['actual_stop_cause'],first['actual_stop_cause']],['wall_time_limit']*2)
        self.assertEqual(second['actual_stop_cause'],'user_requested_pause')
        self.assertIsNone(second['runner_stop_reason'])
        self.assertEqual(second['exit'],-15)
        self.assertLess(second['elapsed_s'],second['timeout_s'])
        self.assertTrue(self.record['pause']['owned_mesh_processes_absent'])
        self.assertFalse(self.record['pause']['automatic_resume_allowed'])
        self.assertEqual(self.record['geometry']['last_written_mesh_stage'],'castellated_before_snapping')
        self.assertFalse(self.record['geometry']['snapped_mesh_completed'])

    def test_exact_cube_control_and_rounded_views_do_not_admit_the_real_wall(self):
        cube=self.record['analytic_parallel_cube']
        self.assertEqual((cube['cells'],cube['vertices'],cube['faces']),(216,343,756))
        self.assertTrue(cube['native_parallel_and_reconstructed_quality_passed'])
        self.assertLess(cube['exact_boundary_volume_error'],1e-12)
        control=self.record['export_control']
        self.assertTrue(control['OBJ_coordinates_exact_native_boundary_subset'])
        self.assertTrue(control['VTK_views_are_not_exact_coordinate_evidence'])
        self.assertGreater(control['VTK_maximum_coordinate_distance_to_native_unit_cube'],0)
        self.assertEqual(control['VTK_native_reader_output_dtype'],'float32')
        self.assertFalse(control['actual_snapped_rotor_export_admitted'])
        view=self.record['diagnostic_view']
        self.assertTrue(view['all_boundary_vertices_queried'])
        self.assertFalse(view['decimation'])
        self.assertFalse(view['complete_bidirectional_surface_bound'])

    def test_preserved_pause_case_keeps_all_admissions_closed(self):
        backup=self.record['private_archives']['parallel-snap-pause']
        self.assertEqual((backup['case_files'],backup['new_payloads'],backup['reused_parent_files']),(69,5,64))
        self.assertEqual(backup['case_files'],backup['new_payloads']+backup['reused_parent_files'])
        for key,value in self.record['scope'].items():
            self.assertFalse(value,key)
        self.assertTrue(self.record['runtime']['network_isolation_unchanged'])
        for attempt in self.record['attempts']:
            self.assertFalse(attempt['full_native_quality_passed'])
            self.assertFalse(attempt['CFD_executed'])
        self.assertFalse(self.record['geometry']['boundary_layers_completed'])
        self.assertFalse(self.record['geometry']['complete_snapped_wall_certificate'])


if __name__=='__main__':unittest.main()
