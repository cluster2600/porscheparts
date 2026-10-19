"""Simultaneous exact clipping must never round a first polygon intersection."""
from fractions import Fraction as Q
from pathlib import Path
import importlib.util
import unittest

if importlib.util.find_spec('shapely') is None:
    raise unittest.SkipTest('Optional Shapely runtime required')
import shapely
from shapely.geometry import Polygon, box

SOURCE = Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/exact_contacts_both.py'
spec = importlib.util.spec_from_file_location('carrier_exact_contacts_both', SOURCE)
contacts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contacts)


class BothContactDomains(unittest.TestCase):
    def test_partial_source_is_clipped_by_both_domains(self):
        result = contacts.clip_contacts_in_both(box(0, 0, 4, 2), box(1, 0, 3, 2), [[[-1, 1], [5, 1]]])
        self.assertEqual(result, [((Q(1), Q(1)), (Q(3), Q(1)))])

    def test_holes_from_each_polygon_are_both_excluded(self):
        ring = [(0, 0), (6, 0), (6, 2), (0, 2)]
        material = Polygon(ring, [[(1, .5), (2, .5), (2, 1.5), (1, 1.5)]])
        domain = Polygon(ring, [[(4, .5), (5, .5), (5, 1.5), (4, 1.5)]])
        result = contacts.clip_contacts_in_both(material, domain, [[[0, 1], [6, 1]]])
        self.assertEqual(result, [((Q(0), Q(1)), (Q(1), Q(1))),
                                  ((Q(2), Q(1)), (Q(4), Q(1))),
                                  ((Q(5), Q(1)), (Q(6), Q(1)))])

    def test_non_dyadic_endpoint_is_not_encoded_before_second_clip(self):
        material = Polygon([(0, 0), (1, 0), (0, 3)])
        domain = box(0, 0, .5, 2)
        source = [[[0, 1], [1, 1]]]
        exact = contacts.clip_contacts_in_both(material, domain, source)
        self.assertEqual(exact, [((Q(0), Q(1)), (Q(1, 2), Q(1)))])
        # Swapping the two polygons preserves the exact source partition/result.
        self.assertEqual(exact, contacts.clip_contacts_in_both(domain, material, source))
        # This separate polygon leaves the non-dyadic endpoint in the final result.
        final = contacts.clip_contacts_in_both(material, box(0, 0, 2, 2), source)
        self.assertEqual(final[-1][-1], (Q(2, 3), Q(1)))
        encoded = contacts.round_contacts_in_both(material, box(0, 0, 2, 2), source)
        self.assertEqual(encoded[-1][-1], [float(Q(2, 3)), 1.])

    def test_material_cannot_supply_contact_outside_free_domain(self):
        self.assertEqual(contacts.clip_contacts_in_both(box(0, 0, 3, 3), box(1, 1, 2, 2),
                                                       [[[0, 0], [3, 0]]]), [])

    def test_closed_shared_boundary_is_a_valid_whole_interval(self):
        result = contacts.clip_contacts_in_both(box(0, 0, 2, 2), box(0, 0, 1, 1), [[[0, 0], [1, 0]]])
        self.assertEqual(result, [((Q(0), Q(0)), (Q(1), Q(0)))])

    def test_one_ulp_recording_change_is_rejected(self):
        import math
        material = domain = box(0, 0, 1, 1)
        raw = [[[0, 0], [1, 0]]]
        encoded = contacts.round_contacts_in_both(material, domain, raw)
        self.assertTrue(contacts.contact_encoding_check_in_both(material, domain, raw, encoded))
        encoded[0][1][0] = math.nextafter(1., 2.)
        self.assertFalse(contacts.contact_encoding_check_in_both(material, domain, raw, encoded))

    def test_collapsed_nonzero_final_interval_is_rejected(self):
        # Distinct exact intersections lie within one float64 rounding cell.
        from math import nextafter
        a = 1.; b = nextafter(1., 2.)
        material = Polygon([(a, 0), (b, 0), (a, 3)])
        with self.assertRaisesRegex(ValueError, 'collapses in float64'):
            contacts.round_contacts_in_both(material, box(0, 0, 2, 3), [[[a, 2], [b, 2]]])

    def test_zero_source_segment_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Zero source'):
            contacts.clip_contacts_in_both(box(0, 0, 1, 1), box(0, 0, 1, 1), [[[0, 0], [0, 0]]])


if __name__ == '__main__':
    unittest.main()
