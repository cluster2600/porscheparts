"""Keep a passing surface certificate separate from singular-volume admission."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AnalysisMeshRecordTests(unittest.TestCase):
    def test_singular_volumes_remain_refused_despite_surface_and_balance_passes(self):
        r = json.loads((ROOT / 'docs/research/935-horizontal-cooling/analysis-mesh-20261022.json').read_text())
        for path, expected in r['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected, path)
        surface = r['surface']
        self.assertTrue(surface['certificate']['complete_containment_pass'])
        self.assertEqual(surface['certificate']['candidate_faces'], surface['candidate']['faces'])
        for flag, value in r['scope'].items():
            self.assertIs(value, False, flag)
        for volume in r['gmsh_initial_volumes'].values():
            self.assertGreater(volume['exact_zero_cells'], 0)
            self.assertTrue(volume['indexed_connectivity']['boundary_matches'])
            self.assertLess(volume['volume_relative_difference_from_analysis_surface'], 1e-8)
            self.assertEqual(volume['status'], 'volume_refused')
            self.assertFalse(volume['mechanical_mesh_admitted'])
            self.assertFalse(volume['manufacturing_authorized'])
        for case in r['rejected_executions']:
            self.assertNotEqual(case['exit'], 0)
            self.assertFalse(case['accepted'])
