"""Keep the carrier correction tied to independent interfaces and failed mechanics."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'parts/993-eng-carrier-0001/source/bionic-20261011/correction-20261013'


def read(name):
    return json.loads((SOURCE/name).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CorrectionEvidenceTests(unittest.TestCase):
    def test_independent_comparator_and_unknowns_are_preserved(self):
        contract = read('interface-study.json')
        for name, expected in contract['sources_sha256'].items():
            self.assertEqual(digest(ROOT/name), expected, name)
        for name in ('OEM_hole_coordinates', 'OEM_datums_and_tolerances',
                     'OEM_pad_thickness_mm', 'OEM_fastener_grip_mm', 'OEM_packaging_envelope'):
            self.assertIsNone(contract[name])
        selected = read('selected-study.json')['geometry']
        self.assertEqual(selected['central_bolt_centres_xy_mm'], contract['study_central_centres_xy_mm'])
        self.assertNotEqual(selected['central_bolt_centres_xy_mm'], [[-48,-23],[-48,23],[48,-23],[48,23]])
        self.assertEqual(selected['thickness_mm'], 8)
        self.assertFalse(contract['fitment_validated'])

    def test_all_retained_sources_and_assets_match(self):
        r = read('results.json')
        for name, expected in r['source_sha256'].items():
            self.assertEqual(digest(SOURCE/name), expected, name)
        for field in ('assets_sha256', 'retained_dependencies_sha256'):
            for name, expected in r[field].items():
                self.assertEqual(digest(ROOT/name), expected, name)

    def test_independent_inspection_does_not_grant_bolt_or_engine_fit(self):
        r = read('results.json'); i = r['inspection']
        self.assertTrue(i['study_assembly_screen_pass'])
        self.assertLessEqual(i['maximum_axis_error_vs_fitted_bracket_mm'], .001)
        self.assertEqual(i['whole_pair_mesh_intersection_mm3'], 0)
        self.assertLessEqual(max(i['end_interface_symmetric_difference_mm3'].values()), 1e-5)
        self.assertEqual(len(i['shank_checks']), 4)
        self.assertFalse(i['bolt_stack']['thread_engagement_verified'])
        self.assertEqual(i['bolt_stack']['remaining_for_nut_washers_protrusion_mm'], 4)
        for name in ('fitment_validated', 'strength_qualified', 'fatigue_qualified', 'manufacturing_authorized'):
            self.assertFalse(r[name])
        self.assertIsNone(r['fatigue_life_cycles'])

    def test_mass_pass_cannot_hide_unconverged_failed_structural_screen(self):
        r = read('results.json')
        self.assertLessEqual(r['geometry']['dense_reference_mass_kg'], 1.2)
        self.assertGreater(r['geometry']['dense_reference_mass_kg'], 1.0)
        self.assertEqual(r['status'], 'geometry_corrected_structural_screen_rejected')
        self.assertEqual(len(r['mechanics']['loads']), 13)
        self.assertFalse(r['refinement']['mesh_convergence_established'])
        self.assertGreater(r['refinement']['peak_stress_change_fraction'], .05)
        self.assertGreater(r['refined_mesh_7']['combined-spring-1000-static']['integration_point_VM_max_MPa'], 2000)
        self.assertLess(r['mechanics']['Maxwell_reciprocity_relative_error'], 1e-5)
        for cycle in r['mechanics']['fatigue_demand'].values():
            self.assertIsNone(cycle['life_cycles'])
        self.assertIsNone(r['material']['qualified_AM_allowable_MPa'])

    def test_native_field_identity_and_export_rejection_are_explicit(self):
        r = read('results.json'); n = r['native']; a = r['native_surface_audit']
        stl = r['geometry']['geometry_sha256']['carrier.stl']
        self.assertEqual(n['source_geometry_sha256'], stl)
        self.assertEqual(r['transfer']['inputs_sha256']['carrier.stl'], stl)
        self.assertEqual(n['source_samples_sha256'], r['transfer']['samples_sha256'])
        self.assertEqual(r['transfer']['inputs_sha256']['mesh.inp'], r['mechanics']['mesh_sha256'])
        self.assertTrue(n['corrected_STEP_solver_executed'])
        self.assertFalse(n['BCC_comparison_solver_executed'])
        self.assertTrue(a['baseline']['export_accepted'])
        self.assertEqual(a['baseline']['removed_positive_area_faces'], 0)
        self.assertEqual(a['baseline']['components'], 1)
        self.assertFalse(a['candidate']['export_accepted'])
        self.assertGreater(a['candidate']['components'], 1)
        self.assertGreater(n['exports']['candidate']['nominal_mass_kg'], 1.2)
        self.assertEqual(n['vdb']['exact_scalar_samples'], r['transfer']['stress_transfer']['occupied_bins'])
        self.assertEqual(n['vdb']['exact_vector_samples'], r['transfer']['displacement_transfer']['occupied_bins'])

    def test_flat_geometry_is_not_a_qualified_print_prediction(self):
        r = read('results.json'); f = r['flat_build']
        self.assertEqual(f['orientation']['rotation_degrees_xyz'], [0,0,45])
        self.assertTrue(f['all_contours_closed'])
        self.assertFalse(f['print_distortion_qualified'])
        self.assertFalse(r['whole_part_print_control']['qualified_print_prediction'])
        self.assertFalse(r['staged_print_distortion_corrected_or_qualified'])
        self.assertLess(abs(f['refined_volume_audit']['relative_error']), .001)
        self.assertTrue(r['raw_solver_retention']['transport_hash_matches_container'])


@unittest.skipUnless(importlib.util.find_spec('trimesh') and importlib.util.find_spec('numpy'),
                     'Optional mesh runtime is needed for surface regression fixtures')
class SurfaceRegressionTests(unittest.TestCase):
    def setUp(self):
        import trimesh
        sys.path.insert(0, str(SOURCE))
        try:
            import inspect_candidate
        finally:
            sys.path.remove(str(SOURCE))
        self.inspector = inspect_candidate
        self.trimesh = trimesh
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def inspect(self, mesh):
        path = Path(self.directory.name)/'fixture.stl'
        mesh.export(path)
        return self.inspector.normalized_mesh(path)

    def test_zero_area_face_can_be_removed_without_changing_volume(self):
        import numpy as np
        mesh = self.trimesh.creation.box()
        mesh.faces = np.vstack([mesh.faces, [0,0,0]])
        _, r = self.inspect(mesh)
        self.assertEqual(r['exact_zero_faces_removed'], 1)
        self.assertEqual(r['removed_positive_area_faces'], 0)
        self.assertEqual(r['volume_mm3'], 1)

    def test_open_or_inverted_mesh_is_rejected(self):
        opened = self.trimesh.creation.box(); opened.faces = opened.faces[:-1]
        inverted = self.trimesh.creation.box(); inverted.invert()
        for mesh in (opened, inverted):
            with self.assertRaises(self.inspector.SurfaceGateError): self.inspect(mesh)

    def test_disconnected_positive_components_cannot_be_silently_dropped(self):
        a = self.trimesh.creation.box(); b = a.copy(); b.apply_translation([5,0,0])
        with self.assertRaises(self.inspector.SurfaceGateError) as error:
            self.inspect(self.trimesh.util.concatenate([a,b]))
        self.assertEqual(error.exception.report['components'], 2)
        self.assertEqual(error.exception.report['removed_positive_area_faces'], 0)
