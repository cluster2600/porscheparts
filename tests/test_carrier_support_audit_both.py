"""The two-domain adapter must fail closed and retain complete exposure guards."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

if any(importlib.util.find_spec(name) is None for name in ('numpy', 'trimesh', 'shapely')):
    raise unittest.SkipTest('Optional geometry runtime required')
import numpy as np
from shapely.geometry import Polygon, box

SOURCE = Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016'
sys.path.insert(0, str(SOURCE))
import audit_support_scanpaths_both as audit
import audit_complete_supports_both as complete


def fixture(domain=None):
    material = box(0, 0, 10, 10)
    if domain is None:
        domain = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)],
                         holes=[[(4, 4), (6, 4), (6, 6), (4, 6)]])
    contact = dict(free_domain_geometry_wkb_hex=domain.wkb_hex,
        free_domain_geometry_sha256=hashlib.sha256(domain.wkb).hexdigest(),
        contact_clip_scope=audit.CONTRACT,
        upper_interface_traces_2d_mm=[[[0., 5.], [10., 5.]]],
        lower_interface_traces_2d_mm=[[[0., 0.], [10., 0.]]])
    group = dict(contact, id='known', contact_reference='/contact',
                 component_geometry_wkb_hex=material.wkb_hex)
    return material, dict(supports=[dict(contact=contact,
        peripheral_skin=dict(support_surface_face_groups=[group]))])


class BothAuditContract(unittest.TestCase):
    def domains(self, report):
        return audit.ContactDomains(report, audit.legacy_module().pointer)

    def test_source_material_only_bridge_across_domain_hole_is_rejected(self):
        material, report = fixture()
        domains = self.domains(report)
        raw = report['supports'][0]['contact']['upper_interface_traces_2d_mm']
        self.assertFalse(domains.encoding_check(material, raw, [[[0., 5.], [10., 5.]]]))
        self.assertTrue(domains.encoding_check(material, raw,
                                              [[[0., 5.], [4., 5.]], [[6., 5.], [10., 5.]]]))
        self.assertEqual(len(domains.clip(material, raw)), 2)

    def test_free_domain_hash_and_group_contact_link_are_both_required(self):
        _, report = fixture()
        report['supports'][0]['peripheral_skin']['support_surface_face_groups'][0]['free_domain_geometry_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'identity differs'):
            self.domains(report)
        report['supports'][0]['contact']['free_domain_geometry_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'WKB hash mismatch'):
            self.domains(report)

    def test_missing_scope_is_not_a_legacy_fallback(self):
        _, report = fixture()
        for item in (report['supports'][0]['contact'], report['supports'][0]['peripheral_skin']['support_surface_face_groups'][0]):
            del item['contact_clip_scope']
        with self.assertRaisesRegex(ValueError, 'Missing explicit'):
            self.domains(report)

    def test_ambiguous_domain_tuple_fails_instead_of_using_iteration_order(self):
        _, report = fixture()
        _, second = fixture(box(0, 0, 10, 10))
        report['supports'].extend(second['supports'])
        with self.assertRaisesRegex(ValueError, 'Ambiguous free domain'):
            self.domains(report)

    def test_isolated_callback_adaptation_does_not_mutate_frozen_module(self):
        first, second = audit.legacy_module(), audit.legacy_module()
        original = second.clip_contacts
        first.clip_contacts = lambda *_: 'known witness'
        self.assertIs(second.clip_contacts, original)
        self.assertNotEqual(first.clip_contacts, second.clip_contacts)
        self.assertEqual(audit.sha(SOURCE/'audit_support_scanpaths.py'), audit.LEGACY_SHA256)

    def test_complete_adapter_keeps_the_no_exposure_group_guard(self):
        vertices = np.array([[0., 0., .04], [1., 0., .05], [0., 0., .05]])
        row = complete.group_witness(vertices, np.array([[0, 1, 2]]),
            dict(id='between', face_range=[0, 1]), np.array([.03, .09]), lambda _: set())
        self.assertFalse(row['passed'])
        self.assertEqual(audit.sha(audit.__file__), complete.BASE_SHA256)


if __name__ == '__main__':
    unittest.main()
