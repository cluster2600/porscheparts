"""The field pilot rejects a tampered reference and nonfinite neural output."""
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/fourvalve'))
try:
    import scipy.sparse.linalg
    import g10_physicsnemo_field as pilot
except ImportError:
    pilot = None


@unittest.skipIf(pilot is None, 'optional numerical runtime unavailable')
class FieldPilotChecks(unittest.TestCase):
    def test_reference_hash_and_error_metric(self):
        import numpy as np
        root = Path(__file__).resolve().parents[1]
        path = root/'twins/m64-cylinder-head/evidence/g9-reference-requalification-20260925/campaign.json'
        self.assertEqual(pilot.g8.sha256(path), pilot.CAMPAIGN_SHA)
        campaign = json.loads(path.read_text())
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)/'carrier_base_p-2.0'
            folder.mkdir()
            (folder/'x.inp').write_text('tampered')
            with self.assertRaisesRegex(ValueError, 'reference hash mismatch'):
                pilot.checked_cases(folder, campaign)
        a = np.array([[1., 2., 3.], [0., 0., 0.]])
        self.assertAlmostEqual(pilot.field_errors(a*1.01, a)['relative_nodal_L2'], .01)
        with self.assertRaises(ValueError):
            pilot.field_errors(a*np.nan, a)


class PublishedEvidenceChecks(unittest.TestCase):
    def test_failed_neural_fields_are_not_released(self):
        root = Path(__file__).resolve().parents[1]
        base = root/'twins/m64-cylinder-head/evidence/g10-physicsnemo-20260926'
        report = json.loads((base/'report.json').read_text())
        execution = json.loads((base/'execution.json').read_text())
        source = root/'twins/m64-cylinder-head/source/fourvalve'
        sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(report['source_sha256'], sha(source/'g10_physicsnemo_field.py'))
        self.assertEqual(execution['source_sha256'], report['source_sha256'])
        self.assertEqual(execution['job_shell_sha256'], sha(source/'g10_gpu_job.sh'))
        self.assertEqual(execution['published_report_sha256'], sha(base/'report.json'))
        self.assertEqual(report['training']['history'][-1]['step'], 10000)
        for row in report['cases']:
            self.assertFalse(row['raw_field_gate_passed'])
            self.assertGreater(row['relative_nodal_L2'], report['thresholds']['nodal_L2'])
            self.assertGreater(row['neural_equation_relative_residual'], 1)
            self.assertEqual(len(row['CG']), 4)
            for corrected in row['CG']:
                self.assertTrue(corrected['passed'])
                self.assertLessEqual(corrected['relative_residual'], 1e-8)
                self.assertLessEqual(corrected['max_nodal_difference_over_max_reference_U'], 1e-4)
        for obj in (report, execution):
            for gate in ('geometry_changed', 'geometry_surrogate_qualified', 'manufacturing_authorized', 'engine_start_authorized'):
                self.assertFalse(obj[gate])
        life = execution['lifecycle']
        for gate in ('provider_destroyed', 'provider_verified_absent', 'external_guard_verified_absent',
                     'final_inventory_empty', 'required_outputs_collected_and_hash_verified_before_deletion'):
            self.assertTrue(life[gate])
        self.assertLessEqual(life['successful_attempt_cap_USD'] + life['failed_start_cost_upper_bound_from_duration_and_transfer_allocations_USD'], life['total_cap_USD'])
        self.assertLessEqual(life['successful_planned_with_cleanup_reserve_USD'], life['successful_attempt_cap_USD'])


if __name__ == '__main__':
    unittest.main()
