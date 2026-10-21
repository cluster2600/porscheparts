"""Small standard-library fixtures only; no AM import, mesh, graph or calendar."""
import copy
from fractions import Fraction as Q
import importlib.util
import math
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('closed_point_v1', HERE/'closed_encoded_point_coverage_v1.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def record(face, cut, **changes):
    row = dict(npz_sha256='a'*64, source_index=3, region=0, owner='skin-0-0', layer=7,
               face=face, cut=cut)
    row.update(changes)
    return row


class ClosedPointTests(unittest.TestCase):
    def setUp(self):
        self.p = (Q(1), Q(2))
        d = Q(1, 2**60)
        self.tiny = (self.p, (self.p[0]+d, self.p[1]+d))
        self.line = ((Q(0), Q(2)), (Q(2), Q(2)))

    def test_frozen_nine_fixtures(self):
        self.assertEqual(len(helper._proof.fixtures(helper._exact['contains_point'])), 9)

    def test_interior_and_endpoint_are_closed(self):
        for line in (self.line, (self.p, (Q(2), Q(2)))):
            result = helper.encode_from_owned_cuts([record(8, self.tiny), record(9, line)])
            self.assertEqual(result['covered_points'][0]['covering_face_ids'], [9])
            self.assertEqual(len(result['sections']), 2)
            self.assertEqual(len(result['encodings']), 1)

    def test_wrong_identity_never_covers(self):
        for changes in (dict(owner='other'), dict(npz_sha256='b'*64), dict(layer=8),
                        dict(source_index=9), dict(region=1)):
            with self.assertRaisesRegex(ValueError, 'same NPZ/source/region/owner/layer'):
                helper.encode_from_owned_cuts([record(8, self.tiny), record(9, self.line, **changes)])

    def test_only_points_cannot_witness_each_other(self):
        with self.assertRaisesRegex(ValueError, 'lacks a nonzero vector'):
            helper.encode_from_owned_cuts([record(8, self.tiny), record(9, self.tiny)])

    def test_nonzero_offset_is_not_a_tolerance(self):
        offset = tuple((x, y+Q(1, 2**51)) for x, y in self.line)
        with self.assertRaises(ValueError):
            helper.encode_from_owned_cuts([record(8, self.tiny), record(9, offset)])

    def test_distinct_q_cuts_and_duplicate_provenance_are_preserved(self):
        d = Q(1, 2**60)
        other = ((Q(0), Q(2)+d), (Q(2), Q(2)+d))
        result = helper.encode_from_owned_cuts([record(9, self.line), record(10, other),
                                               record(11, self.line)])
        self.assertEqual(len(result['sections']), 2)
        self.assertEqual(result['sections'][self.line], [(0, 9), (0, 11)])
        self.assertEqual(len(result['encodings']), 1)
        self.assertEqual(next(iter(result['encoded_sections'].values())), [(0, 9), (0, 10), (0, 11)])
        self.assertEqual(len(next(iter(result['encodings'].values()))), 2)

    def test_coverage_uses_only_encoded_q_not_original_q(self):
        d = Q(1, 2**60)
        source_line = tuple((x, y+d) for x, y in self.line)
        self.assertFalse(helper._exact['contains_point'](source_line, self.p))
        result = helper.encode_from_owned_cuts([record(8, self.tiny), record(9, source_line)])
        self.assertEqual(result['covered_points'][0]['covering_face_ids'], [9])

    def test_zero_point_source_never_transfers_its_anchor(self):
        result = helper.encode_from_owned_cuts([record(8, self.tiny), record(9, self.line)])
        def contacts(segments, sections):
            return {i for i, segment in enumerate(segments) if (0, 8) in sections[segment]}
        rational = contacts(sorted(result['sections']), result['sections'])
        encoded = contacts(sorted(result['encoded_sections']), result['encoded_sections'])
        self.assertTrue(rational)
        self.assertEqual(encoded, set())
        self.assertNotIn((0, 8), sum(result['encoded_sections'].values(), []))

    def test_encoded_contact_witness_uses_its_own_provenance(self):
        result = helper.encode_from_owned_cuts([record(8, self.tiny), record(9, self.line)])
        segments = sorted(result['encoded_sections'])
        self.assertEqual([result['encoded_sections'][s] for s in segments], [[(0, 9)]])
        self.assertTrue(all(type(c) is Q for s in segments for p in s for c in p))
        self.assertTrue(all(a != b for a, b in result['encodings']))

    def test_no_input_list_is_mutated(self):
        rows = [record(8, [list(p) for p in self.tiny]), record(9, [list(p) for p in self.line])]
        before = copy.deepcopy(rows)
        helper.encode_from_owned_cuts(rows)
        self.assertEqual(rows, before)

    def test_fraction_shapes_zero_and_nonfinite_refuse(self):
        for cut in ((self.p, self.p), ((1., 2.), (2., 2.)), ((Q(1),), (Q(2),)),
                    ((Q(10**400), Q(0)), (Q(10**400), Q(1)))):
            with self.assertRaises((ValueError, OverflowError)):
                helper.encode_from_owned_cuts([record(9, cut)])

    def test_signed_zero_and_ties_keep_original_cell_proof(self):
        tiny = ((Q(-1, 2**1075), Q(0)), (Q(1, 2**1075), Q(0)))
        line = ((Q(-1), Q(0)), (Q(1), Q(0)))
        self.assertEqual(len(helper.encode_from_owned_cuts([record(8, tiny), record(9, line)])['covered_points']), 1)
        even = (Q(math.nextafter(1., -math.inf))+Q(1))/2
        tied = ((even, Q(2)), self.p)
        helper.encode_from_owned_cuts([record(8, tied), record(9, self.line)])

    def test_empty_input_is_empty(self):
        self.assertEqual(helper.encode_from_owned_cuts([]), dict(sections={}, encodings={},
                         encoded_sections={}, covered_points=[]))


if __name__ == '__main__':
    unittest.main()
