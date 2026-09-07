import importlib.util
import itertools
import json
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/picogk-local-junction-direct-union'


class DirectUnionContracts(unittest.TestCase):
    def test_set_identity_requires_no_extensivity_assumption(self):
        for a, c, r in itertools.product((False, True), repeat=3):
            self.assertEqual(a or ((c and not a) and r), a or (c and r))

    def test_preregistered_guards_and_single_resolution(self):
        p = json.loads((SOURCE/'criteria.json').read_text())
        self.assertEqual(p['resolutions_scan_units'], [.2])
        for k in ('outside_ROI_occupancy_changes_allowed', 'protected_occupancy_changes_allowed',
                  'source_gas_occupancy_losses_allowed', 'addition_at_ROI_boundary_allowed'):
            self.assertEqual(p[k], 0)
        self.assertTrue(p['native_VDB_fields_must_be_saved'])
        self.assertTrue(p['no_finer_or_private_geometry_automatic_followup'])

    def test_construction_is_direct_and_difference_is_diagnostic_only(self):
        s = (SOURCE/'Program.cs').read_text()
        self.assertIn('candidate = original.voxBoolAdd(closedInRoi)', s)
        self.assertLess(s.index('candidate ='), s.index('rawAdded ='))
        self.assertNotIn('original.voxBoolAdd(added)', s)
        self.assertIn('h != 0.2f', s)
        self.assertIn('native-fields.vdb', s)
        self.assertIn('outsideSdfChanges++', s)
        self.assertIn('protectedSdfChanges++', s)
        self.assertIn('unavailableSdfPairs++', s)

    def test_component_audit_disables_implicit_repair(self):
        s = (SOURCE/'audit_mesh.py').read_text()
        self.assertIn('split(only_watertight=False, repair=False)', s)


if __name__ == '__main__':
    unittest.main()
