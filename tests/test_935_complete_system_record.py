import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class CompleteSystemRecordTests(unittest.TestCase):
    def test_execution_sources_match_and_unfinished_gates_remain_explicit(self):
        r=json.loads((ROOT/'docs/research/935-horizontal-cooling/complete-system-20261022.json').read_text())
        for path,expected in r['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),expected,path)
        self.assertEqual(r['assembly']['current_rotor_geometry_sha256'],r['geometry_sha256'])
        self.assertTrue(r['assembly']['native_concatenation_coordinates_and_order_exact'])
        self.assertEqual(r['warp']['reference_scope'],'complete_target_mesh')
        self.assertEqual(r['warp']['query_misses'],0);self.assertEqual(r['warp']['device']['actual'],'cpu')
        self.assertGreater(r['C3D8I_final_pair_displacement_relative_change'],.05)
        self.assertTrue(all(x['reaction_balance_pass'] for x in r['rotor_formulation_cases']))
        self.assertEqual(len(r['surface_review']['pairs']),6)
        crossed=[x['components'] for x in r['surface_review']['pairs'] if x['surface_crossing']]
        self.assertEqual(crossed,[['engine_context','drive_observed']])
        self.assertTrue(r['rental']['teardown_verified']);self.assertFalse(r['rental']['CUDA_executed'])
        for flag in ('full_system_goal_complete','current_geometry_CFD_accepted','FEA_mesh_convergence_established',
                     'scale_verified','historical_interfaces_verified','material_process_qualified','optimization_complete',
                     'PhysicsNeMo_trained','Omniverse_runtime_review_complete','complete_mechanism_defined',
                     'manufacturing_authorized','physical_validation'):
            self.assertIs(r[flag],False,flag)
