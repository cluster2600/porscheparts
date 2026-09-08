"""Unit tests for provenance, role transfer and inherited-evidence boundaries.

The real OCP exporter is exercised separately against the pinned private BRep;
these synthetic records do not constitute a native-geometry test.
"""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/flowbench-intake/package_unified_gas_domain.py'
spec = importlib.util.spec_from_file_location('m64_unified_package', SOURCE)
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class UnifiedPacketContractTests(unittest.TestCase):
    def review(self):
        return {'schema': 'm64-private-independent-three-face-native-merge-control-audit/v2',
            'status': 'native_merge_matches_serialization_control_exactly',
            'original_sha256': package.OLD, 'candidate_sha256': package.NEW,
            'source_sha256': package.REVIEW_SOURCE, 'independent_noop_control_sha256': package.NOOP,
            'inputs_unchanged': True, 'raw_original_and_candidate_descriptor_identity': False,
            'CAD_or_mesh_modified_by_audit': False, 'manufacturing_authorized': False,
            'CFD_qualified': False, 'native_BOP': copy.deepcopy(package.CLEAN_BOP),
            'gates': dict.fromkeys(package.REVIEW_GATES, True),
            'topology_before': {'faces': 88, 'edges': 195, 'vertices': 120, 'solids': 1, 'shells': 1},
            'topology_after': {'faces': 86, 'edges': 191, 'vertices': 118, 'solids': 1, 'shells': 1},
            'candidate_merged_face_ids_private': [37], 'external_rim_edge_count': 16,
            'unmatched_old_face_ids': [], 'ambiguous_old_face_ids': [],
            'unchanged_face_map_private': {str(i): i if i < 37 else i - 1 if i == 39 else i - 2
                for i in range(1, 89) if i not in package.GROUP}}

    def original(self):
        return {'schema': 'm64-intake-gas-domain/v1',
            'exports': {'domain_brep': {'file': 'domain.brep', 'sha256': package.OLD}},
            'gates': {'single_solid': True, 'brep_valid': True, 'native_roundtrip_valid': True,
                'bop_no_faults': True, 'boundary_assignment_complete': True,
                'positive_intake_curtain': True, 'guide_extensions_communicate': True,
                'step_roundtrip_valid': None},
            'inputs_unchanged': True, 'STEP_BOP_qualified': False,
            'manufacturing_authorized': False, 'CFD_executed': False,
            'boundary_faces': [{'id': i, 'role': 'walls_port', 'sha256': str(i),
                'source_match': [{'source': 'raw_intake_face_8', 'role': 'walls_port'}]}
                for i in range(1, 89)],
            'boundary_role_counts': {'walls_port': 88},
            'local_intake_necks': [{'local_volume': 123., 'passes': True}],
            'guide_extensions': [{'communication_with_original_negative_volume': 3.4}],
            'fixture_stem_seal_authority': 'idealized_bench_only',
            'guide_extension_evidence_transfer': {'new_intersection_executed': False},
            'local_neck_recheck': {'both_current_necks_recomputed_and_passed': True}}

    def test_reviewed_relation_is_many_to_one_not_bijection(self):
        relation, rows = package.transfer_rows(self.original(), self.review())
        self.assertEqual(len(relation), 88)
        self.assertEqual(set(rows), set(range(1, 87)))
        self.assertEqual({i for i, j in relation.items() if j == 37}, {37, 38, 40})
        self.assertEqual(relation[39], 38)
        self.assertEqual([relation[i] for i in (55, 56, 57, 58, 61, 62, 63, 64)],
                         [53, 54, 55, 56, 59, 60, 61, 62])

    def test_missing_false_or_extra_review_gate_rejected(self):
        for mode in ('missing', 'false', 'extra'):
            review = self.review()
            key = package.REVIEW_GATES[0]
            if mode == 'missing':
                del review['gates'][key]
            elif mode == 'false':
                review['gates'][key] = False
            else:
                review['gates']['unreviewed_extension'] = True
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                package.reviewed_face_relation(review)

    def test_wrong_review_candidate_or_raw_identity_claim_rejected(self):
        for key, value in (('candidate_sha256', package.OLD), ('original_sha256', package.NEW),
                           ('independent_noop_control_sha256', '0' * 64),
                           ('source_sha256', '0' * 64), ('raw_original_and_candidate_descriptor_identity', True),
                           ('inputs_unchanged', False)):
            review = self.review()
            review[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                package.reviewed_face_relation(review)

    def test_count_preserving_but_wrong_face_map_rejected(self):
        review = self.review()
        mapping = review['unchanged_face_map_private']
        mapping['1'], mapping['2'] = mapping['2'], mapping['1']
        with self.assertRaises(ValueError):
            package.reviewed_face_relation(review)

    def test_duplicate_and_missing_source_faces_rejected(self):
        original = self.original()
        original['boundary_faces'][-1]['id'] = 87
        with self.assertRaises(ValueError):
            package.transfer_rows(original, self.review())

    def test_changed_merge_source_or_role_rejected(self):
        for mode in ('source', 'role'):
            original = self.original()
            row = original['boundary_faces'][37]
            if mode == 'source':
                row['source_match'][0]['source'] = 'unrelated_port'
            else:
                row['role'] = 'walls_seat'
                row['source_match'][0]['role'] = 'walls_seat'
                original['boundary_role_counts'] = {'walls_port': 87, 'walls_seat': 1}
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                package.transfer_rows(original, self.review())

    def test_multiple_historical_overlap_labels_preserve_reviewed_final_role(self):
        original = self.original()
        row = original['boundary_faces'][2]
        row['role'] = 'walls_seat'
        row['source_match'] = [{'source': 'chamber_tool_face_3', 'role': 'walls_chamber'},
                               {'source': 'intake_1_seat_face_1', 'role': 'walls_seat'}]
        original['boundary_role_counts'] = {'walls_port': 87, 'walls_seat': 1}
        _, grouped = package.transfer_rows(original, self.review())
        self.assertEqual(grouped[3][0]['role'], 'walls_seat')
        self.assertEqual(grouped[3][0]['source_match'], row['source_match'])
        row['source_match'].pop()
        with self.assertRaises(ValueError):
            package.transfer_rows(original, self.review())

    def test_native_only_authority_does_not_inherit_STEP_or_CFD(self):
        for key in ('STEP_BOP_qualified', 'manufacturing_authorized', 'CFD_executed'):
            original = self.original()
            original[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                package.transfer_rows(original, self.review())

    def test_historical_numbers_are_nested_not_fresh_candidate_measurements(self):
        inherited = package.inherited_evidence(self.original())
        self.assertFalse(inherited['new_neck_intersection_executed'])
        self.assertFalse(inherited['new_guide_intersection_executed'])
        self.assertFalse(inherited['raw_original_descriptor_identity_claimed'])
        self.assertTrue(inherited['historical_measurements_not_current_candidate_measurements'])
        self.assertNotIn('local_neck_recheck', inherited)
        self.assertEqual(inherited['historical_source_records']['local_intake_necks'][0]['local_volume'], 123.)

    def test_packet_path_escape_or_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / 'packet'
            parent.mkdir()
            outside = Path(directory) / 'outside'
            outside.touch()
            (parent / 'link').symlink_to(outside)
            for name in ('../outside', str(outside), 'link'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    package.private_member(parent, name)


if __name__ == '__main__':
    unittest.main()
