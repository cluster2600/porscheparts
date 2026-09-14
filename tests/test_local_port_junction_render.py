"""Pure guards for the semantic labels of the actual local CAD rendering."""
import copy
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/render_local_port_junction.py'
SPEC = importlib.util.spec_from_file_location('local_port_renderer', SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class NewFaceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.identities = {
            'records': {
                'before': {'BSpline_carrier_signatures': {'1': 'old-a', '2': 'old-b'}},
                'after': {'BSpline_carrier_signatures': {
                    '2': 'new-a', '3': 'new-b', '4': 'new-c', '5': 'old-a', '6': 'old-b'}},
            },
            'new_BSpline_carrier_face_ids_after': [2, 3, 4],
            'expected_generated_faces_from_builder_history': 3,
            'identified_by_full_degree_poles_weights_knots_mults_not_index_transfer': True,
        }

    def test_actual_set_of_new_carriers_is_accepted(self):
        self.assertEqual(MODULE.checked_new_face_ids(self.identities), [2, 3, 4])

    def test_relabelled_original_face_and_duplicate_ids_are_rejected(self):
        for ids in ([5], [2, 3, 5], [2, 2, 4], [], [True, 3, 4]):
            with self.subTest(ids=ids):
                data = copy.deepcopy(self.identities)
                data['new_BSpline_carrier_face_ids_after'] = ids
                with self.assertRaises(ValueError):
                    MODULE.checked_new_face_ids(data)

    def test_builder_history_count_must_agree(self):
        self.identities['expected_generated_faces_from_builder_history'] = 4
        with self.assertRaises(ValueError):
            MODULE.checked_new_face_ids(self.identities)

    def test_unverified_identity_comparison_is_rejected(self):
        self.identities['identified_by_full_degree_poles_weights_knots_mults_not_index_transfer'] = False
        with self.assertRaises(ValueError):
            MODULE.checked_new_face_ids(self.identities)


if __name__ == '__main__':
    unittest.main()
