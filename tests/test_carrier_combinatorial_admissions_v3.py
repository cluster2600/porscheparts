"""Exact interval replay and preservation of the six historical seal gates."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

if importlib.util.find_spec('pyslm') is None:
    raise unittest.SkipTest('Optional coverage runtime required')
from pyslm.support import support as native_support
if not hasattr(native_support, '_triangulate_exact_projected_domain'):
    raise unittest.SkipTest('Pinned coverage runtime required')
import numpy as np
import shapely

SOURCE = Path(__file__).resolve().parents[1] / 'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0, str(SOURCE))
import admissions_v3 as admission
from continuous_combinatorial_interfaces import repair
from grid_intervals import contacts


class CombinatorialAdmissionsV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        free = shapely.box(0., 0., 10., 1.)
        cls.interfaces = dict(upper=[[[0., 1.], [10., 1.]]], lower=[[[0., 0.], [10., 0.]]])
        cls.material, cls.receipt = repair(shapely.Polygon(), free, cls.interfaces, .2)
        cls.actual = contacts(cls.material, free, cls.interfaces)

    def test_actual_planar_reconstruction_and_contacts_are_replayed(self):
        result = admission.continuous_admission(self.receipt, self.actual, .2)
        self.assertTrue(result['passed'])
        self.assertTrue(result['exact_final_component_boundaries_identical'])
        self.assertTrue(result['intervals'][0]['required_contacts_recomputed'])
        self.assertFalse(result['intervals'][0]['legacy_overlay_used_as_authority'])

    def test_retained_real_left_grid_domain_is_replayed_without_overlay(self):
        fixture = SOURCE.parent / 'process-scanpath-audit-20261016/band-union-evidence/left-grid.json'
        value = json.loads(fixture.read_text())
        free = shapely.from_wkb(bytes.fromhex(value['geometry_wkb_hex']['free']))
        interfaces = dict(upper=[], lower=[])
        material, receipt = repair(shapely.Polygon(), free, interfaces, .2)
        self.assertTrue(admission.continuous_admission(receipt, contacts(material, free, interfaces), .2)['passed'])
        # Planar confinement is not an independent anchor/material-graph proof.

    def test_source_interfaces_and_construction_cannot_be_self_attested(self):
        mutations = [
            lambda row: row['attested_source_interfaces']['upper'][0][0].__setitem__(1, .9),
            lambda row: row.__setitem__('attested_source_interfaces_sha256', '0' * 64),
            lambda row: row['combinatorial_construction'].__setitem__('included_strips', 0),
            lambda row: row.__setitem__('continuous_interface_selected', False),
            lambda row: row.__setitem__('band_authority', 'geos_zero_area'),
            lambda row: row['exact_free_domain_coverage'].__setitem__('passed', False),
            lambda row: row['exact_intended_band_union_confinement'].__setitem__('passed', False),
        ]
        for mutate in mutations:
            bad = copy.deepcopy(self.receipt); mutate(bad['intervals'][0])
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                admission.continuous_admission(bad, self.actual, .2)

    def test_changed_exported_component_and_omitted_interval_are_refused(self):
        for kind in ['component', 'interval', 'order', 'whole_identity', 'contact']:
            bad = copy.deepcopy(self.receipt); actual = copy.deepcopy(self.actual)
            if kind == 'component':
                other = shapely.box(0, 0, 10, .8)
                actual[-1].update(component_geometry_wkb_hex=other.wkb_hex,
                    component_geometry_sha256=hashlib.sha256(other.wkb).hexdigest())
            elif kind == 'interval': bad['intervals'] = []
            elif kind == 'order': bad['intervals'][0]['domain_index'] = -1
            elif kind == 'whole_identity': bad['generated_material_geometry_sha256'] = '0' * 64
            else: actual[0]['upper_contact_trace_mm'] = 99.
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                admission.continuous_admission(bad, actual, .2)

    def test_distinct_required_intervals_are_preserved(self):
        free = shapely.MultiPolygon([shapely.box(0, 0, 10, 1), shapely.box(0, 3, 10, 4)])
        interfaces = dict(upper=[[[0, 1], [10, 1]], [[0, 4], [10, 4]]],
                          lower=[[[0, 0], [10, 0]], [[0, 3], [10, 3]]])
        material, receipt = repair(shapely.Polygon(), free, interfaces, .2)
        self.assertEqual(len(admission.continuous_admission(receipt, contacts(material, free, interfaces), .2)['intervals']), 2)

    def fixture_seal(self, directory):
        """Synthetic metadata fixture; exact unit predicates are explicitly mocked.

        This isolates seal decisions, not a manufactured support or graph proof.
        All actual planar mathematical checks are tested above without mocks.
        """
        class Store:
            report = dict(expected_regions=7, status='passed', regions=[{}] * 7, coordinate_error_bounds=[])
            manifest_sha256 = 'software-fixture-store'
            def verify(self): pass
        supports = []
        points = np.array([[0., 0., 0.], [1., 0., 0.], [0., 0., 1.]])
        faces = np.array([[0, 1, 2]] * 3, dtype=np.int64)
        geometry_sha = hashlib.sha256(points.tobytes() + faces.tobytes()).hexdigest()
        for index in range(7):
            contact = copy.deepcopy(self.actual)
            infill = dict(outside_free_domain_and_contact_band_area_mm2=4.99e-30,
                interface_contacts=contact, required_free_intervals=1, generated_material_components=1,
                continuous_interface_reconstruction=copy.deepcopy(self.receipt))
            component = dict(index=0, unfolding=dict(source_vertical_area_mm2=1., unfolded_domain_area_mm2=1.,
                numerical_area_tolerance_mm2=0., source_coordinate_roundtrip_max_mm=0., numerical_coordinate_tolerance_mm=0.),
                remapping=dict(split_planar_area_mm2=1., remapped_area_mm2=1., numerical_area_tolerance_mm2=0.), infill=infill)
            plane = dict(order=0, fixed_axis=0, passed=True, whole_surface_outside_admitted_domain_area_mm2=4.99e-30,
                contacts=contact, required_free_intervals=1, generated_material_components=1,
                continuous_interface_reconstruction=copy.deepcopy(self.receipt))
            axes = [dict(expected_planes=1, generated_planes=1, planes=[copy.deepcopy(plane)]) for _ in range(2)]
            groups = []
            for group_index in range(3):
                reference = (f'/grid_coverage/axes/{group_index}/planes/0/contacts/1' if group_index < 2 else
                             '/peripheral_skin/components/0/infill/interface_contacts/1')
                groups.append(dict(id=str(group_index), face_range=[group_index, group_index + 1], contact_reference=reference,
                    component_geometry_sha256=contact[1]['component_geometry_sha256'],
                    component_geometry_wkb_hex=contact[1]['component_geometry_wkb_hex']))
            graph = dict(status='passed', input_geometry_sha256=geometry_sha, groups=3,
                components=[dict(group_ids=['0', '1', '2'], passed=True, upper_contact_group_ids=['0'], lower_contact_group_ids=['1'])],
                internal_connectivity=[dict(passed=True, remaining_components=1)] * 3)
            skin = dict(status='generated', continuous_fragmented_interfaces=True, generated_vertical_components=1,
                expected_vertical_components=1, explicitly_unexposed_vertical_components=0, components=[component],
                support_surface_face_groups=groups, material_connection_graph=graph)
            supports.append(dict(index=index, peripheral_skin=skin, grid_coverage=dict(status='passed', axes=axes)))
            np.savez(directory / f'support-{index:03d}.npz', vertices=points, faces=faces)
        coverage = dict(region_projection_admission_passed=True, expected_regions=7, generated_regions=7,
                        regions=[{}] * 7, configured_area_exclusions=[])
        (directory / 'region-coverage.json').write_text(json.dumps(coverage))
        checkpoint = dict(supports=supports, input_sha256='software-fixture-part',
                          parameters=dict(support_teeth_upper_penetration_mm=.2))
        units = {'grid-0-0': dict(passed=True), 'grid-1-0': dict(passed=True), 'skin-0': dict(passed=True)}
        return checkpoint, Store(), units

    def test_six_receipts_keep_real_diagnostics_and_v3_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); checkpoint, store, units = self.fixture_seal(directory)
            original = copy.deepcopy(checkpoint['supports'])
            with patch.object(admission, '_exact_support_units', return_value=units):
                result, passed = admission.seal(directory, checkpoint, store)
            self.assertTrue(passed); self.assertEqual(set(result), set(admission.KEYS))
            self.assertEqual(checkpoint['supports'], original)
            for key, reference in result.items():
                path = directory / reference['receipt']; receipt = json.loads(path.read_text())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), reference['receipt_sha256'])
                self.assertEqual(receipt['admission_schema'], admission.SCHEMA)
                self.assertEqual(receipt['admission_source_sha256'], admission.sha(admission.__file__))
            skins = json.loads((directory / 'admission-skins.json').read_text())
            self.assertEqual(skins['regions'][0]['receipt']['components'][0]['infill']['outside_free_domain_and_contact_band_area_mm2'], 4.99e-30)

    def test_all_historical_non_overlay_gates_remain_required(self):
        for kind in ['unfold_area', 'unfold_coordinates', 'remap_area', 'graph_hash', 'graph_anchor',
                     'contacts', 'plane_completeness', 'skin_completeness', 'envelopes', 'regions', 'exact_unit']:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp); checkpoint, store, units = self.fixture_seal(directory)
                skin = checkpoint['supports'][0]['peripheral_skin']; component = skin['components'][0]
                if kind == 'unfold_area': component['unfolding']['source_vertical_area_mm2'] = 2.
                elif kind == 'unfold_coordinates': component['unfolding']['source_coordinate_roundtrip_max_mm'] = 1.
                elif kind == 'remap_area': component['remapping']['split_planar_area_mm2'] = 2.
                elif kind == 'graph_hash': skin['material_connection_graph']['input_geometry_sha256'] = 'wrong'
                elif kind == 'graph_anchor': skin['material_connection_graph']['components'][0]['upper_contact_group_ids'] = []
                elif kind == 'contacts': component['infill']['interface_contacts'][0]['upper_contact_trace_mm'] = 0.
                elif kind == 'plane_completeness': checkpoint['supports'][0]['grid_coverage']['axes'][0]['generated_planes'] = 0
                elif kind == 'skin_completeness': skin['expected_vertical_components'] = 2
                elif kind == 'envelopes': store.report = dict(store.report, status='rejected')
                elif kind == 'regions':
                    path = directory / 'region-coverage.json'; value = json.loads(path.read_text())
                    value['region_projection_admission_passed'] = False; path.write_text(json.dumps(value))
                else: units['grid-0-0']['passed'] = False
                with patch.object(admission, '_exact_support_units', return_value=units):
                    _, passed = admission.seal(directory, checkpoint, store)
                self.assertFalse(passed)

    def test_changed_face_group_component_or_range_is_refused(self):
        for kind in ['component', 'range', 'contact_reference']:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp); checkpoint, store, units = self.fixture_seal(directory)
                group = checkpoint['supports'][0]['peripheral_skin']['support_surface_face_groups'][0]
                if kind == 'component': group['component_geometry_sha256'] = '0' * 64
                elif kind == 'range': group['face_range'] = [1, 2]
                else: group['contact_reference'] = '/grid_coverage/axes/0/planes/0/contacts/0'
                with patch.object(admission, '_exact_support_units', return_value=units), self.assertRaises(ValueError):
                    admission.seal(directory, checkpoint, store)


if __name__ == '__main__':
    unittest.main()
