"""Known exact intersections and negative exposure-contact witnesses."""
import importlib.util
from pathlib import Path
import sys
import unittest
import tempfile
import hashlib
import json

if any(importlib.util.find_spec(name) is None for name in ('numpy', 'trimesh', 'shapely')):
    raise unittest.SkipTest('Optional native geometry runtime required')
import numpy as np
import shapely
from shapely.geometry import Polygon
import trimesh
from fractions import Fraction as Q

sys.path.insert(0, str(Path(__file__).resolve().parent))
from exact_support_section import support_section
from exact_contacts import clip_contacts, round_contact_traces, contact_encoding_check
from audit_support_scanpaths import (triangle_section, exact_sections, check_vectors,
    ExposureGraph, contact_band_segments, contacts_at_layer, segments_intersect, intersection_pairs,
    load_supports, sha, ADMISSIONS)


def segment(a, b):
    return tuple(tuple(Q(c) for c in p) for p in (a, b))


class SupportExposureAudit(unittest.TestCase):
    def test_exact_contact_can_require_an_encoded_endpoint_outside_the_IEEE_polygon(self):
        material = Polygon([[0., 0.], [1., 3.], [3., 0.]])
        interface = [[[0., 1.], [3., 1.]]]
        exact = clip_contacts(material, interface)
        self.assertEqual(exact, [segment((Q(1, 3), 1), (Q(7, 3), 1))])
        encoded = round_contact_traces(material, interface)
        self.assertFalse(material.covers(shapely.LineString(encoded[0])))
        self.assertTrue(contact_encoding_check(material, interface, encoded))
        encoded[0][0][0] = np.nextafter(encoded[0][0][0], -np.inf)
        self.assertFalse(contact_encoding_check(material, interface, encoded))

    def test_exact_contacts_preserve_holes_and_include_closed_boundary_intervals(self):
        material = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)],
                           holes=[[(4, 4), (4, 6), (6, 6), (6, 4)]])
        self.assertEqual(clip_contacts(material, [[[-1., 5.], [11., 5.]]]),
                         [segment((0, 5), (4, 5)), segment((6, 5), (10, 5))])
        self.assertEqual(clip_contacts(material, [[[-1., 0.], [11., 0.]]]), [segment((0, 0), (10, 0))])
        self.assertEqual(clip_contacts(material, [[[-1., -1.], [0., 0.]]]), [])
    def test_cached_exact_inputs_preserve_all_rational_sections(self):
        mesh = trimesh.Trimesh([[0., 0., 0.], [1., 2., 3.], [3., 1., 0.]], [[0, 1, 2]], process=False)
        prepared = {}
        for z in [0., .06, 1., 2.99, 3., 4.]:
            cached = exact_sections([mesh], z, prepared)
            self.assertEqual(cached, exact_sections([mesh], z))
            independent = triangle_section(mesh.triangles[0], z)
            self.assertEqual(set(cached[0]), set() if independent is None else {independent})
        with self.assertRaisesRegex(ValueError, 'inputs changed'):
            exact_sections([mesh.copy()], 1., prepared)
    def test_non_dyadic_cut_is_certified_as_rounding_not_exact_float_geometry(self):
        mesh = trimesh.Trimesh([[0., 0., 0.], [1., 0., 3.], [3., 0., 0.]], [[0, 1, 2]], process=False)
        bound = np.column_stack((mesh.vertices[mesh.faces, 2].min(axis=1), mesh.vertices[mesh.faces, 2].max(axis=1)))
        native = support_section(mesh, 1., bound)[:, :, :2]
        exact, encoded, receipt = exact_sections([mesh], 1.)
        self.assertEqual(len(exact), 1)
        self.assertEqual(next(iter(exact))[0][0], Q(1, 3))
        self.assertTrue(check_vectors(native, encoded)['passed'])
        self.assertGreater(receipt['strict_encoded_endpoint_mismatches'], 0)
        self.assertGreater(receipt['encoding_error_Linf_mm_upper'], 0)
        self.assertLess(receipt['encoding_error_Linf_mm_upper'], 1e-15)

    def test_entire_cut_rejects_bridge_missing_split_and_one_ulp_change(self):
        mesh = trimesh.Trimesh([[0., 0., 0.], [1., 0., 2.], [2., 0., 0.]], [[0, 1, 2]], process=False)
        _, encoded, _ = exact_sections([mesh], 1.)
        correct = np.asarray(list(encoded), dtype=np.float64)
        self.assertTrue(check_vectors(correct, encoded)['passed'])
        wrong = correct.copy(); wrong[0, 0, 0] = np.nextafter(wrong[0, 0, 0], -np.inf)
        self.assertFalse(check_vectors(wrong, encoded)['passed'])
        self.assertFalse(check_vectors(np.empty((0, 2, 2)), encoded)['passed'])
        bridge = np.asarray([[[0., 0.], [2., 0.]]])
        self.assertFalse(check_vectors(bridge, encoded)['passed'])

    def test_nonfinite_zero_and_reversed_duplicate_are_rejected(self):
        valid = np.asarray([[[0., 0.], [1., 0.]]])
        encoded = {((0., 0.), (1., 0.)): segment((0, 0), (1, 0))}
        with self.assertRaisesRegex(ValueError, 'finite'):
            check_vectors(valid*np.nan, encoded)
        duplicate = np.concatenate((valid, valid[:, ::-1]))
        self.assertEqual(check_vectors(duplicate, encoded)['exact_duplicate_segments'], 1)
        self.assertFalse(check_vectors(np.zeros((1, 2, 2)), {})['passed'])

    def test_tol_merge_near_plane_does_not_become_a_vertex_on_plane(self):
        z0 = 5e-9
        mesh = trimesh.Trimesh([[0., 0., z0], [1., 0., -1.], [2., 0., 1.]], [[0, 1, 2]], process=False)
        native = trimesh.intersections.mesh_plane(mesh, [0, 0, 1], [0, 0, 0])[:, :, :2]
        _, encoded, _ = exact_sections([mesh], 0.)
        self.assertFalse(check_vectors(native, encoded)['passed'])
        bound = np.column_stack((mesh.vertices[mesh.faces, 2].min(axis=1), mesh.vertices[mesh.faces, 2].max(axis=1)))
        self.assertTrue(check_vectors(support_section(mesh, 0., bound)[:, :, :2], encoded)['passed'])

    def test_distinct_exact_sections_keep_their_identity_when_encoding_collides(self):
        vertices = [[1e15, 0., 0.], [1e15+10, 0., 0.],
                    [1e15+1, 0., 3.], [1e15+2, 0., 3.]]
        mesh = trimesh.Trimesh(vertices, [[0, 2, 1], [0, 3, 1]], process=False)
        sections, encoded, receipt = exact_sections([mesh], 1e-9)
        self.assertEqual(len(sections), 2)
        self.assertEqual(len(encoded), 1)
        self.assertEqual(receipt['distinct_rational_sections_sharing_one_encoding'], 1)
        self.assertTrue(check_vectors(np.array(list(encoded)), encoded)['passed'])
        self.assertLessEqual(receipt['encoding_error_ULP_max_upper'], .5)

    def test_coplanar_sheet_is_rejected_instead_of_silently_omitted(self):
        mesh = trimesh.Trimesh([[0., 0., 1.], [1., 0., 1.], [0., 1., 1.]], [[0, 1, 2]], process=False)
        with self.assertRaisesRegex(ValueError, 'Coplanar'):
            exact_sections([mesh], 1.)

    def test_exact_crossing_and_sub_ulp_gap_are_distinct(self):
        first = segment((0, 0), (2, 0))
        crossing = segment((1, -1), (1, 1))
        gap = segment((0, Q(1, 10**30)), (2, Q(1, 10**30)))
        self.assertTrue(segments_intersect(first, crossing))
        self.assertFalse(segments_intersect(first, gap))
        self.assertEqual(intersection_pairs([first, crossing]), [(0, 1)])
        self.assertEqual(intersection_pairs([first], [gap]), [])

    def test_contact_between_layer_planes_is_not_an_exposure_contact(self):
        group = dict(kind='grid', fixed_axis=1, plane_coordinate_mm=0.,
            upper_contact_traces_2d_mm=[[[0., .10], [1., .10]]])
        self.assertEqual(contact_band_segments(group, 'upper', .03, .001), [])
        self.assertEqual(contact_band_segments(group, 'upper', .15, .001), [])
        self.assertEqual(len(contact_band_segments(group, 'upper', .10, .001)), 1)

    def test_valid_exposure_chain_and_crossed_sheet_can_share_anchors(self):
        graph = ExposureGraph()
        horizontal = segment((0, 0), (2, 0))
        vertical = segment((1, -1), (1, 1))
        graph.add([horizontal], {0}, set())
        graph.add([horizontal, vertical], set(), set())
        graph.add([vertical], set(), {0})
        self.assertTrue(graph.report()['passed'])
        self.assertEqual(graph.report()['exposure_components'], 1)

    def test_floating_earlier_sheet_is_not_rescued_by_a_later_geometric_join(self):
        graph = ExposureGraph()
        anchored = segment((0, 0), (1, 0))
        floating = segment((2, 0), (3, 0))
        graph.add([anchored, floating], {0}, set())
        graph.add([segment((0, 0), (3, 0))], set(), {0})
        self.assertFalse(graph.report()['passed'])
        self.assertEqual(graph.report()['unanchored_layer_components'], 1)

    def test_a_missing_exposure_layer_breaks_the_contact_path(self):
        graph = ExposureGraph()
        line = segment((0, 0), (1, 0))
        graph.add([line], {0}, set())
        graph.add([], set(), set())
        graph.add([line], set(), {0})
        self.assertFalse(graph.report()['passed'])

    def test_tooth_requires_real_part_overlap_not_only_a_named_trace(self):
        cut = segment((0, 0), (2, 0))
        sections = {cut: [(0, 0)]}
        group = dict(id='fixture', region=0, kind='grid', fixed_axis=1, plane_coordinate_mm=0.,
            lower_contact_traces_2d_mm=[[[0., 0.], [2., 0.]]],
            upper_contact_traces_2d_mm=[[[0., 2.], [2., 2.]]])
        lower, upper, _ = contacts_at_layer([cut], sections, [np.array([0])], [group], 2., .2,
            shapely.box(5, 5, 6, 6), 10)
        self.assertEqual((lower, upper), (set(), set()))
        _, upper, _ = contacts_at_layer([cut], sections, [np.array([0])], [group], 2., .2,
            shapely.box(.5, -1, 1.5, 1), 10)
        self.assertEqual(upper, {0})

    def test_remote_part_overlap_cannot_be_borrowed_for_a_different_contact_piece(self):
        cut = segment((0, 0), (10, 0))
        group = dict(id='fixture', region=0, kind='grid', fixed_axis=1, plane_coordinate_mm=0.,
            lower_contact_traces_2d_mm=[[[0., 0.], [1., 0.]]],
            upper_contact_traces_2d_mm=[[[0., 2.], [1., 2.]]])
        _, upper, _ = contacts_at_layer([cut], {cut: [(0, 0)]}, [np.array([0])], [group], 2., .2,
            shapely.box(8, -1, 9, 1), 10)
        self.assertEqual(upper, set())

    def test_a_lower_trace_above_the_plate_is_not_a_first_layer_anchor(self):
        cut = segment((0, 0), (1, 0))
        group = dict(id='fixture', region=0, kind='grid', fixed_axis=1, plane_coordinate_mm=0.,
            lower_contact_traces_2d_mm=[[[0., .01], [1., .01]]],
            upper_contact_traces_2d_mm=[[[0., 2.], [1., 2.]]])
        lower, _, _ = contacts_at_layer([cut], {cut: [(0, 0)]}, [np.array([0])], [group], .03, .2,
            shapely.GeometryCollection(), 0)
        self.assertEqual(lower, set())

    def test_a_lower_trace_outside_the_real_plate_is_not_an_anchor(self):
        cut = segment((300, 0), (301, 0))
        group = dict(id='fixture', region=0, kind='grid', fixed_axis=1, plane_coordinate_mm=0.,
            lower_contact_traces_2d_mm=[[[300., 0.], [301., 0.]]],
            upper_contact_traces_2d_mm=[[[300., 2.], [301., 2.]]])
        lower, _, _ = contacts_at_layer([cut], {cut: [(0, 0)]}, [np.array([0])], [group], .03, .2,
            shapely.GeometryCollection(), 0)
        self.assertEqual(lower, set())

    def test_support_group_cannot_borrow_an_admission_or_omit_a_face(self):
        # Minimal receipt-format fixture; this is not a native envelope approval.
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve()
            material = shapely.box(0., 0., 1., 2.)
            contact = dict(kind='generated_material_component', passed=True,
                component_geometry_sha256=hashlib.sha256(material.wkb).hexdigest(),
                upper_contact_traces_2d_mm=[[[0., 2.], [1., 2.]]],
                lower_contact_traces_2d_mm=[[[0., 0.], [1., 0.]]],
                upper_interface_traces_2d_mm=[[[0., 2.], [1., 2.]]],
                lower_interface_traces_2d_mm=[[[0., 0.], [1., 0.]]])
            group = dict(contact, id='grid-fixture', kind='grid', order=0, type=0, face_range=[0, 2],
                component_geometry_wkb_hex=material.wkb_hex, fixed_axis=1, plane_coordinate_mm=0.,
                contact_reference='/grid_coverage/contacts/0')
            support = dict(index=0, faces=2, grid_coverage=dict(contacts=[contact]),
                peripheral_skin=dict(support_surface_face_groups=[group]))
            np.savez_compressed(directory/'support-000.npz',
                vertices=np.asarray([[0., 0., 0.], [1., 0., 0.], [1., 0., 2.], [0., 0., 2.]]),
                faces=np.asarray([[0, 1, 2], [0, 2, 3]]), order=np.zeros(2), type=np.zeros(2))
            report = dict(manufacturing_preparation_admitted=True, input_sha256='a'*64,
                admission={}, outputs_sha256={}, supports=[support])
            report['outputs_sha256']['support-000.npz'] = sha(directory/'support-000.npz')
            def seal_fixture():
                for name in ADMISSIONS:
                    receipt = dict(status='passed', passed=True, input_sha256='a'*64)
                    if name in ('skins', 'grids'):
                        receipt['regions'] = [dict(region=0, passed=True,
                            receipt=support['peripheral_skin' if name == 'skins' else 'grid_coverage'])]
                    path = directory/f'admission-{name}.json'
                    path.write_text(json.dumps(receipt))
                    report['admission'][name] = dict(status='passed', receipt=path.name, receipt_sha256=sha(path))
                    report['outputs_sha256'][path.name] = sha(path)
            seal_fixture()
            self.assertEqual(len(load_supports(directory, report, report)[0]), 1)
            group['face_range'] = [0, 1]
            with self.assertRaisesRegex(ValueError, 'sealed skins'):
                load_supports(directory, report, report)
            seal_fixture()
            with self.assertRaisesRegex(ValueError, 'actual admitted material'):
                load_supports(directory, report, report)
            group['face_range'] = [0, 2]
            seal_fixture()
            (directory/'support-000.npz').write_bytes(b'changed fixture mesh')
            with self.assertRaisesRegex(ValueError, 'changed process file'):
                load_supports(directory, report, report)


if __name__ == '__main__':
    unittest.main()
