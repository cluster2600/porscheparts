import json
from pathlib import Path
import unittest
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'twins/m64-cylinder-head/source/picogk-local-junction'


class PreregistrationTests(unittest.TestCase):
    def test_fixed_local_screen_and_stop_gate(self):
        policy = json.loads((SOURCE/'criteria.json').read_text())
        self.assertEqual(policy['radius_scan_units'], 1)
        self.assertEqual(policy['resolutions_scan_units'], [.2, .1])
        self.assertEqual(policy['outside_ROI_occupancy_changes_allowed'], 0)
        self.assertEqual(policy['protected_occupancy_changes_allowed'], 0)
        self.assertEqual(policy['source_gas_occupancy_losses_allowed'], 0)
        self.assertTrue(policy['stop_before_private_geometry_if_witness_fails'])
        self.assertFalse(policy['manufacturing_authorized'])
        self.assertFalse(policy['two_resolutions_establish_asymptotic_convergence'])

    def test_witness_only_no_private_geometry_fallback(self):
        source = (SOURCE/'Program.cs').read_text()
        self.assertIn('args[0] != "--witness"', source)
        self.assertIn('original.voxFillet(1f)', source)
        self.assertIn('rawAdded.voxBoolIntersect(roi)', source)
        self.assertIn('original.voxBoolAdd(added)', source)
        self.assertNotIn('TripleOffset(', source)
        self.assertIn('private_head_processed=false', source)

    def test_both_native_zero_conventions_and_rebuild_changes_are_measured(self):
        source = (SOURCE/'Program.cs').read_text()
        self.assertIn('b<0 : b<=0', source)
        self.assertIn('a<0 : a<=0', source)
        self.assertIn('outside.All(n=>n==0)', source)
        self.assertIn('protectedChanges.All(n=>n==0)', source)
        self.assertIn('losses.All(n=>n==0)', source)
        self.assertIn('addedAtBoundary.All(n=>n==0)', source)
        self.assertIn('float.PositiveInfinity', source)


@unittest.skipUnless(importlib.util.find_spec('trimesh'), 'trimesh QA runtime required')
class RawMeshAuditTests(unittest.TestCase):
    def test_exact_duplicate_indexing_does_not_hide_degenerate_faces(self):
        import numpy as np
        import trimesh
        spec = importlib.util.spec_from_file_location('local_junction_audit', SOURCE/'audit_mesh.py')
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        box = trimesh.creation.box()
        self.assertTrue(audit.topology(box)['strict_raw_mesh_screen_pass'])
        broken = trimesh.Trimesh(box.vertices.copy(), np.vstack([box.faces, [0, 0, 1]]), process=False)
        result = audit.topology(broken)
        self.assertEqual(result['faces'], len(box.faces)+1)
        self.assertEqual(result['exact_zero_area_faces'], 1)
        self.assertFalse(result['strict_raw_mesh_screen_pass'])
        inverted = trimesh.Trimesh(box.vertices.copy(), box.faces[:, ::-1], process=False)
        self.assertFalse(audit.topology(inverted)['strict_raw_mesh_screen_pass'])


if __name__ == '__main__':
    unittest.main()
