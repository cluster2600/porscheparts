"""G9 directional load/support integrity and fail-closed RHS mapping."""
from pathlib import Path
import copy
import hashlib
import json
import tempfile
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/fourvalve'))
from g9_mesh_summary import summarize
try:
    import scipy.sparse.linalg
    import g9_reference_campaign as g9
    import g9_finish_carrier as resume
except ImportError:
    g9 = None


@unittest.skipIf(g9 is None, 'optional numerical runtime unavailable')
class ReferenceChecks(unittest.TestCase):
    def test_negative_z_load_and_rejection(self):
        text = ('*NODE\n1,0,0,0\n2,1,2,3\n*NSET,NSET=SUPPORT\n1,\n'
                '*STEP\n*STATIC\n*BOUNDARY\nSUPPORT,1,3\n*CLOAD\n2,3,-10\n*END STEP\n')
        points, loads, support = g9.deck(text)
        self.assertEqual(support, {1})
        self.assertEqual(loads, {(2, 3): -10})
        self.assertEqual(g9.rhs_for([(2, 3), (2, 1), (2, 2)], loads).tolist(), [-10, 0, 0])
        with self.assertRaises(ValueError):
            g9.rhs_for([(2, 1)], loads)
        for bad in (text.replace('2,3,-10', '1,3,-10'), text.replace('2,3,-10', '2,4,-10'),
                    text.replace('2,3,-10', '2,3,nan'), text.replace('SUPPORT,1,3', 'SUPPORT,1,2'),
                    text.replace('2,3,-10', '2,3,-10\n2,3,-10')):
            with self.assertRaises(ValueError):
                g9.deck(bad)
        self.assertEqual(len(g9.HISTORICAL), 9)

    def test_resume_rejects_changed_checkpoint_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [{'case': c+'-'+str(s), 'direction': d, 'numerical_crosscheck_passed': True,
                     'hashes': {'x.dat': hashlib.sha256(b'original').hexdigest()}}
                    for c, sizes in (('central_diaphragm', (3., 2., 1.5)), ('carrier_base_p', (3., 2.)))
                    for s in sizes for d in ('x', 'minus_z')]
            rows.append({'case': 'witness-2.0', 'direction': 'x', 'numerical_crosscheck_passed': True})
            report = {'complete': False, 'cases': rows, 'source_sha256': g9.g8.sha256(Path(g9.__file__))}
            (root / 'report.partial.json').write_text(json.dumps(report))
            (root / rows[0]['case']).mkdir()
            (root / rows[0]['case'] / 'x.dat').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'checkpoint artifact changed'):
                resume.finish(SimpleNamespace(partial=root))


class MeshSummaryChecks(unittest.TestCase):
    def test_stabilization_does_not_release_failed_geometry(self):
        mechanics = {'journal_weighted_displacement_mm': {'intake': [.08, 0, 0], 'exhaust': [.09, 0, 0]},
                     'von_Mises_p95_MPa': 50., 'von_Mises_max_MPa': 400.}
        rows = [{'case': c+'-'+str(s), 'direction': d, 'numerical_crosscheck_passed': True,
                 'mechanics': copy.deepcopy(mechanics)} for c in ('central_diaphragm', 'carrier_base_p')
                for s in (3., 2., 1.5) for d in ('x', 'minus_z')]
        rows.append({'case': 'witness-2.0', 'direction': 'x', 'numerical_crosscheck_passed': True})
        report = {'complete': True, 'cases': rows}
        result = summarize(report)
        self.assertTrue(all(g['selected_observables_stabilized'] for g in result['groups']))
        self.assertFalse(any(g['G7_working_motion_screen_passed'] for g in result['groups']))
        self.assertFalse(result['manufacturing_authorized'])
        self.assertFalse(result['maximum_stress_convergence_qualified'])
        rows[2]['mechanics']['von_Mises_p95_MPa'] = 60
        self.assertFalse(summarize(report)['groups'][0]['selected_observables_stabilized'])
        rows[0]['numerical_crosscheck_passed'] = False
        with self.assertRaises(ValueError):
            summarize(report)

    def test_published_campaign_keeps_failed_engineering_gates(self):
        root = Path(__file__).resolve().parents[1]
        evidence = root / 'twins/m64-cylinder-head/evidence/g9-reference-requalification-20260925'
        path = evidence / 'campaign.json'
        report = json.loads(path.read_text())
        summary = json.loads((evidence / 'mesh-summary.json').read_text())
        source = root / 'twins/m64-cylinder-head/source/fourvalve'
        self.assertEqual(report['source_sha256'], hashlib.sha256((source / 'g9_reference_campaign.py').read_bytes()).hexdigest())
        self.assertEqual(report['resume_source_sha256'], hashlib.sha256((source / 'g9_finish_carrier.py').read_bytes()).hexdigest())
        self.assertEqual(summary.pop('source_sha256'), hashlib.sha256((source / 'g9_mesh_summary.py').read_bytes()).hexdigest())
        self.assertEqual(summary.pop('campaign_sha256'), hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(summary, summarize(report))
        for row in report['cases']:
            self.assertLessEqual(row['relative_residual'], 1e-8)
            self.assertLessEqual(row['fresh_direct']['max_nodal_difference_over_max_reference_U'], 1e-4)
            self.assertTrue(row['mechanics']['equilibrium_passed'])
        failed_old = [(r['case'], r['direction']) for r in report['cases'] if r['historical_comparison']
                      and r['historical_comparison']['max_nodal_difference_over_max_reference_U'] > 1e-4]
        self.assertEqual(failed_old, [('carrier_base_p-3.0', 'x')])
        self.assertFalse(report['manufacturing_authorized'])
        self.assertFalse(report['engine_start_authorized'])
        self.assertFalse(report['assembled_stiffness_qualified'])
        self.assertFalse(summary['groups'][2]['selected_observables_stabilized'])
        self.assertFalse(summary['groups'][2]['G7_working_motion_screen_passed'])
        execution = json.loads((evidence / 'execution.json').read_text())
        life = execution['lifecycle']
        for key in ('external_guard_armed_before_rental', 'provider_destroyed', 'provider_verified_absent',
                    'external_guard_verified_absent', 'inventory_empty_after_cleanup',
                    'required_numerical_evidence_collected_and_hash_verified_before_deletion'):
            self.assertTrue(life[key])
        self.assertLessEqual(life['planned_with_cleanup_reserve_USD'], life['run_budget_USD'])
        self.assertLessEqual(life['run_budget_USD'], 4)
        self.assertLessEqual(sum(execution['private_archives'][n]['bytes'] for n in ('first_results', 'final_results')),
                             life['output_allocation_GB'] * 1e9)
        self.assertFalse(execution['manufacturing_authorized'])


if __name__ == '__main__':
    unittest.main()
