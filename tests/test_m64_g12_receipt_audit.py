"""Independent receipt arithmetic without numerical dependencies or remote calls."""
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/fourvalve/g12_receipt_audit.py'
SPEC = importlib.util.spec_from_file_location('g12_receipt_audit_test', SOURCE)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class G12ReceiptAuditChecks(unittest.TestCase):
    def test_published_evidence_preserves_hashes_failures_and_unqualified_scope(self):
        evidence = audit.REPO/'twins/m64-cylinder-head/evidence/g12-fea-20260926'
        campaign = audit.read(evidence/'campaign.json')
        report = audit.read(evidence/'receipt-audit.json')
        collection = audit.read(evidence/'collection-verified.json')
        self.assertEqual(report['source_sha256'], audit.sha(SOURCE))
        self.assertEqual(report['summary_sha256'], audit.sha(evidence/'campaign.json'))
        self.assertEqual(report['summary_records'], campaign['records'])
        self.assertEqual(report['baseline_summary_sha256'], audit.sha(audit.BASELINE))
        self.assertEqual(report['archive_sha256'], collection['archive_sha256'])
        self.assertEqual(collection['archive_sha256'], 'fe62eee7cbd3bc65cd30fd2acfea5d63b3468290d2a26f234e865a2513ee2df6')
        self.assertTrue(collection['collection_verified'])
        self.assertEqual(collection['retained_files_verified'], 133)
        self.assertFalse(campaign['complete'])
        self.assertFalse(report['campaign_complete'])
        self.assertIsNone(campaign['selected_variant'])
        self.assertEqual(campaign['assessments'], {})
        self.assertEqual(report['completed_receipt_count'], 3)
        states = [case['status'] for variant in report['variants'].values() for case in variant['planned_cases'].values()]
        self.assertEqual(sorted(states), sorted(['completed']*3+['failed']*2+['not_run']))
        first, second = (report['variants'][ident] for ident in audit.VARIANTS)
        self.assertEqual(first['planned_cases']['1']['status'], 'failed')
        self.assertEqual(second['planned_cases']['1']['reason'], 'prior_mesh_not_completed')
        for variant in (first, second):
            self.assertFalse(variant['accepted_isolated_cold_screen'])
            self.assertFalse(variant['refinement']['1.5_to_1_mm']['evaluated'])
            self.assertIsNone(variant['maximum_fine_journal_motion_mm'])
        raw = [audit.read(evidence/name) for name in ('local24-2mm.json', 'local24-1p5mm.json', 'local28-2mm.json')]
        for name, result in zip(('local24-2mm.json', 'local24-1p5mm.json', 'local28-2mm.json'), raw):
            record = next(row for row in campaign['records'] if row['id'] == result['id'] and row['size_mm'] == result['mesh']['size_mm'])
            self.assertEqual(record['status'], 'completed')
            self.assertEqual(audit.sha(evidence/name), record['sha256'])
            self.assertEqual(report['receipts']['results/'+record['path']], record['sha256'])
            self.assertEqual(result['source_sha256'], campaign['reused_source_sha256'])
        for value in (campaign, report, *raw):
            self.assertEqual(value['campaign_source_sha256'], audit.sha(SOURCE.with_name('g12_campaign.py')))
            self.assertEqual(value['cad_receipt_sha256'], audit.sha(audit.CAD))
            for key in ('manufacturing_authorized', 'engine_start_authorized', 'assembled_stiffness_qualified'):
                self.assertIs(value[key], False)
        for source, expected in campaign['reused_source_sha256'].items():
            self.assertEqual(audit.sha(SOURCE.with_name(source)), expected)
        qualitative = audit.read(evidence/'local24-displacement-loadpath-diagnostic.json')
        self.assertEqual(qualitative['classification'], 'node_sampled_displacement_loadpath_qualitative_only')
        for name in ('local24-1p0-equilibrium-diagnostic.json', 'local28-1p5-equilibrium-diagnostic.json'):
            diagnostic = audit.read(evidence/name)
            self.assertEqual(diagnostic['classification'], 'read_only_failed_case_diagnostic_not_scientific_acceptance')
            self.assertFalse(diagnostic['cases']['minus_z']['guard_passed'])
            self.assertGreater(diagnostic['cases']['minus_z']['force_balance_relative_error'], diagnostic['common']['force_and_moment_threshold'])
            for value in (qualitative, diagnostic):
                for key in ('accepted', 'manufacturing_authorized', 'engine_start_authorized', 'assembled_stiffness_qualified'):
                    self.assertIs(value.get(key, False), False)
        equation = audit.read(evidence/'equation-diagnostic.json')
        execution = audit.read(evidence/'equation-execution.json')
        self.assertEqual(audit.sha(evidence/'equation-diagnostic.json'), execution['artifacts']['diagnostic.json']['sha256'])
        self.assertEqual(audit.sha(evidence/'equation-execution.json'), 'e9120651b45f6a57f714280b4254fadfbde7d525eda955cbc65a89c25b017058')
        self.assertTrue(equation['diagnostic_rows_complete'])
        self.assertTrue(equation['original_failure_preserved'])
        self.assertEqual([row['numerical_crosscheck_passed'] for row in equation['rows']], [True, False])
        bad = equation['rows'][1]
        self.assertLess(bad['relative_residual'], 1e-8)
        self.assertGreater(bad['fresh_direct']['max_nodal_difference_over_max_reference_U'], 1e-4)
        self.assertGreater(bad['fresh_direct']['printed_dat_relative_residual'], bad['fresh_direct']['printed_dat_rounding_residual_bound'])
        self.assertEqual(audit.sha(SOURCE.with_name('g12_equilibrium_audit.sh')), execution['artifacts']['provenance/g12_equilibrium_audit.sh']['sha256'])
        lifecycle = audit.read(evidence/'lifecycle.json')
        self.assertTrue(lifecycle['collection_verified_before_delete'])
        self.assertTrue(lifecycle['proof']['verified_absent'])
        self.assertFalse(lifecycle['manufacturing_authorized'])
        self.assertLess(lifecycle['combined_archive_bytes'], lifecycle['archive_byte_cap'])
        extra = audit.read(evidence/'equation-collection-verified.json')
        self.assertTrue(extra['collection_verified'])
        self.assertEqual(extra['archive_sha256'], lifecycle['archives'][1]['sha256'])

    def test_vector_rotation_and_stress_have_separate_gates(self):
        left = dict(journal_vectors_mm={side: [1, 0, 0] for side in audit.SIDES}, stress_p95_MPa=100)
        right = dict(journal_vectors_mm={side: [0, 1, 0] for side in audit.SIDES}, stress_p95_MPa=100)
        compared = audit.compare(left, right)
        self.assertAlmostEqual(compared['maximum_vector_relative_change'], math.sqrt(2))
        self.assertEqual(compared['journals']['intake']['right_minus_left_mm'], [-1, 1, 0])
        self.assertEqual(compared['journals']['intake']['scalar_norm_relative_change'], 0)
        self.assertFalse(compared['vector_stabilized_1pct'])
        self.assertTrue(compared['stress_stabilized_5pct'])
        compared = audit.compare(left, dict(left, stress_p95_MPa=110))
        self.assertTrue(compared['vector_stabilized_1pct'])
        self.assertFalse(compared['stress_stabilized_5pct'])

    def test_incomplete_campaign_keeps_failure_and_unrun_fine_mesh(self):
        qualified = {direction: dict(numerical_crosscheck_passed=True, equilibrium_passed=True)
                     for direction in audit.DIRECTIONS}
        first, second = audit.VARIANTS
        records = {(first, size): {'status': 'completed'} for size in audit.SIZES}
        records.update({(second, '2'): {'status': 'completed'},
                        (second, '1.5'): {'status': 'failed', 'returncode': 1}})
        data = {first: {size: qualified for size in audit.SIZES}, second: {'2': qualified}}
        states = audit.planned_states(records, data)
        self.assertEqual(sum(len(rows) for rows in states.values()), 6)
        self.assertTrue(all(row['status'] == 'completed' for row in states[first].values()))
        self.assertEqual(states[second]['1.5']['status'], 'failed')
        self.assertEqual(states[second]['1']['status'], 'not_run')
        self.assertEqual(states[second]['1']['reason'], 'prior_mesh_not_completed')
        self.assertFalse(states[second]['1']['qualified_for_comparison'])

    def test_missing_verified_archive_fails_before_any_analysis_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises((FileNotFoundError, ValueError)):
                audit.analyze(root)
            self.assertEqual(list(root.iterdir()), [])
        self.assertEqual(audit.REPO, SOURCE.parents[4])


if __name__ == '__main__':
    unittest.main()
