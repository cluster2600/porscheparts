"""Rational source contact must not borrow a rounded positive part overlap."""
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

if any(importlib.util.find_spec(name) is None for name in ('numpy', 'trimesh', 'shapely')):
    raise unittest.SkipTest('Optional geometry runtime required')
import numpy as np
import shapely
from shapely.geometry import box, Polygon

SOURCE = Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016'
sys.path.insert(0, str(SOURCE))
import audit_support_scanpaths_exact_anchors as audit
import audit_complete_supports_exact_anchors as complete


def restored(value):
    if isinstance(value, dict) and {'numerator', 'denominator', 'nearest_float'} == set(value):
        return Q(int(value['numerator']), int(value['denominator']))
    if isinstance(value, dict):
        return {k: restored(v) for k, v in value.items()}
    if isinstance(value, list):
        return [restored(v) for v in value]
    return value


def section(polygon):
    rings = [np.asarray(r.coords) for r in [polygon.exterior, *polygon.interiors]]
    return audit.section_domain(np.vstack(rings), np.r_[0, np.cumsum([len(r) for r in rings])].astype(np.int64))


class ExactExposureAnchors(unittest.TestCase):
    def test_negative_fixture_reproduces_old_false_positive_then_new_refusal(self):
        data = restored(json.loads((SOURCE/'exact-anchor-evidence/negative-ieee-hole.json').read_text()))
        part = shapely.from_wkb(data['measured_part_domain_wkb_hex'])
        self.assertEqual(hashlib.sha256(part.wkb).hexdigest(), data['source_geometry_sha256'])
        segment = tuple(tuple(p) for p in data['segment'])
        material = shapely.from_wkb(data['group']['component_geometry_wkb_hex'])
        self.assertTrue(audit.utilities.contact_encoding_check(material,
            data['group']['upper_interface_traces_2d_mm'], data['group']['upper_contact_traces_2d_mm']))
        self.assertEqual(audit.utilities.clip_contacts(material, data['group']['upper_interface_traces_2d_mm']),
                         [tuple(tuple(p) for p in interval) for interval in data['group']['_exact_upper_contact_traces']])
        args = ([segment], {segment: [(0, 0)]}, [np.array([0])], [data['group']], 1., .2)
        lower, upper, witnesses = audit.utilities.contacts_at_layer(*args, part, 1)
        self.assertEqual(upper, {0})
        self.assertGreater(witnesses[0]['part_overlap_length_mm'], .8)
        self.assertEqual(witnesses, data['legacy_witnesses'])
        lower, upper, witnesses = audit.contacts_at_layer(*args, section(part), 1)
        self.assertEqual((lower, upper, witnesses), (set(), set(), []))

    def test_rational_non_dyadic_hit_is_not_encoded_before_inside_test(self):
        domain = section(box(0, 0, 1, 1))
        segment = ((Q(1, 3), Q(1, 2)), (Q(2, 3), Q(1, 2)))
        self.assertEqual(audit.positive_part_intervals(segment, domain), [segment])

    def test_positive_shared_boundary_is_contact_but_a_single_point_is_not(self):
        domain = section(box(0, 0, 1, 1))
        self.assertTrue(audit.positive_part_intervals(((Q(0), Q(0)), (Q(1), Q(0))), domain))
        self.assertEqual(audit.positive_part_intervals(((Q(-1), Q(0)), (Q(0), Q(0))), domain), [])

    def test_part_hole_is_used_from_original_rings_without_overlay_coordinates(self):
        part = Polygon(box(0, 0, 4, 4).exterior.coords, [box(1, 1, 3, 3).exterior.coords])
        domain = section(part)
        actual = audit.positive_part_intervals(((Q(0), Q(2)), (Q(4), Q(2))), domain)
        self.assertEqual(actual, [((Q(0), Q(2)), (Q(1), Q(2))), ((Q(3), Q(2)), (Q(4), Q(2)))])

    def test_real_positive_contact_is_retained(self):
        segment = ((Q(0), Q(0)), (Q(2), Q(0)))
        group = dict(id='known', region=0, kind='grid', fixed_axis=1, plane_coordinate_mm=0.,
                     upper_contact_traces_2d_mm=[[[0., 1.], [2., 1.]]], lower_contact_traces_2d_mm=[])
        result = audit.contacts_at_layer([segment], {segment: [(0, 0)]}, [np.array([0])], [group], 1., .2,
                                         section(box(.5, -.5, 1.5, .5)), 3)
        self.assertEqual(result[1], {0})
        self.assertTrue(result[2][0]['exact_part_overlap_intervals'])

    def test_plate_anchor_only_at_first_layer_and_a_true_zero_height_trace(self):
        segment = ((Q(0), Q(0)), (Q(2), Q(0)))
        group = dict(id='plate', region=0, kind='grid', fixed_axis=1, plane_coordinate_mm=0.,
                     lower_contact_traces_2d_mm=[[[0., 0.], [2., 0.]]], upper_contact_traces_2d_mm=[])
        args = ([segment], {segment: [(0, 0)]}, [np.array([0])], [group], .03, .2, audit.RecordedPartSection([]))
        self.assertEqual(audit.contacts_at_layer(*args, 0)[0], {0})
        self.assertEqual(audit.contacts_at_layer(*args, 1)[0], set())

    def test_complete_wrapper_retains_frozen_every_group_exposure_guard(self):
        module = complete.frozen_complete_module()
        vertices = np.array([[0., 0., .04], [1., 0., .05], [0., 0., .05]])
        witness = module.group_witness(vertices, np.array([[0, 1, 2]]),
            dict(id='between', face_range=[0, 1]), np.array([.03, .09]), lambda _: set())
        self.assertFalse(witness['passed'])
        self.assertEqual(module.base, audit)
        self.assertEqual(audit.sha(audit.__file__), complete.BASE_SHA256)

    def test_frozen_legacy_and_two_domain_modules_are_unchanged(self):
        self.assertEqual(audit.sha(SOURCE/'audit_support_scanpaths.py'), audit.previous.LEGACY_SHA256)
        self.assertEqual(audit.sha(SOURCE/'audit_support_scanpaths_both.py'), audit.PREVIOUS_SHA256)
        self.assertEqual(audit.sha(SOURCE/'audit_complete_supports_both.py'), complete.FROZEN_COMPLETE_SHA256)

    def test_complete_wrapper_requires_and_propagates_the_rational_contact_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'audit'
            def measured(*args):
                (output/'scanpaths').mkdir(parents=True)
                (output/'scanpaths/assessment.json').write_text(json.dumps(dict(
                    rational_part_contact_intersections=True, part_contact_intermediate_encoding=False,
                    encoded_anchor_scope='known test scope')))
                return dict(status='passed', complete_build_audited=True)
            module = SimpleNamespace(__file__=str(SOURCE/'audit_complete_supports_both.py'), audit=measured)
            with mock.patch.object(complete, 'frozen_complete_module', return_value=module):
                receipt = complete.audit(directory, output, 'unused-synthetic-source.stl')
            self.assertIs(receipt['rational_part_contact_intersections'], True)
            self.assertIs(receipt['part_contact_intermediate_encoding'], False)
            self.assertEqual(json.loads((output/'assessment.json').read_text()), receipt)

    def test_complete_wrapper_refuses_an_old_or_false_contact_predicate_receipt(self):
        for flag in (None, False):
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory)/'audit'
                def measured(*args):
                    (output/'scanpaths').mkdir(parents=True)
                    (output/'scanpaths/assessment.json').write_text(json.dumps(dict(
                        rational_part_contact_intersections=flag, part_contact_intermediate_encoding=False)))
                    return dict(status='passed')
                module = SimpleNamespace(__file__=str(SOURCE/'audit_complete_supports_both.py'), audit=measured)
                with mock.patch.object(complete, 'frozen_complete_module', return_value=module):
                    with self.assertRaisesRegex(ValueError, 'did not use rational'):
                        complete.audit(directory, output, 'unused-synthetic-source.stl')


if __name__ == '__main__':
    unittest.main()
