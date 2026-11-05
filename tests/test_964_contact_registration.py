"""Geometric compatibility cannot grant an unobserved physical correspondence."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from _deps import require_modules

require_modules('numpy', 'scipy')
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'twins/964-chassis/contact-registration-20261106/screen.py'
SPEC = importlib.util.spec_from_file_location('contact_screen', SCRIPT)
SCREEN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCREEN)


class ContactRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'twins/964-chassis/owner-frame-data-20261105/source-data.json').read_text())
        self.source = SCREEN.nominal_network(self.data)

    def test_rigid_motion_recovers_metric_pattern_with_decoy_but_no_admission(self):
        # Axis permutation plus two sign changes is a proper rotation.
        rotation = np.array([[0, -1, 0], [0, 0, -1], [1, 0, 0]])
        points = self.source @ rotation.T + [1300, -500, 77]
        points = np.vstack([points, [9000, 8000, 7000]])
        result = SCREEN.screen(self.source, points)
        self.assertGreater(result['diagnostic_rejection']['compatible_ordered_quartets'], 0)
        self.assertAlmostEqual(result['minimum_six_edge_rms_mm'], 0)
        self.assertIn(1330, result['source_edge_lengths_mm'])
        self.assertIn(1236, result['source_edge_lengths_mm'])
        self.assertTrue(SCREEN.verify_metrics(self.source, points, result)['passed'])
        self.assertIsNone(result['rigid_transform'])
        self.assertFalse(result['engineering_admission'])

    def test_matching_both_widths_does_not_match_the_network(self):
        wrong = self.source.copy()
        wrong[2:, 0] += 800
        self.assertEqual(np.linalg.norm(wrong[0] - wrong[1]), 1330)
        self.assertEqual(np.linalg.norm(wrong[2] - wrong[3]), 1236)
        result = SCREEN.screen(self.source, wrong)
        self.assertEqual(result['diagnostic_rejection']['compatible_ordered_quartets'], 0)
        SCREEN.verify_metrics(self.source, wrong, result)

    def test_planar_reflection_preserves_distances_without_contact_normal_evidence(self):
        self.assertEqual(np.linalg.matrix_rank(self.source - self.source.mean(axis=0)), 2)
        reflected = self.source * [1, 1, -1]
        result = SCREEN.screen(self.source, reflected)
        self.assertGreater(result['diagnostic_rejection']['compatible_ordered_quartets'], 0)
        self.assertEqual(result['new_contacts_identified'], 0)
        self.assertFalse(result['engineering_admission'])
        self.assertIsNone(result['rigid_transform'])

    def test_contact_or_projection_substitution_is_rejected(self):
        for change in ('contact', 'unknown_width', 'direct_length'):
            data = copy.deepcopy(self.data)
            if change == 'contact':
                next(p for p in data['mi']['points'] if p['point_id'] == 'F')['contact_definition_printed'] = 'Bolt head'
            elif change == 'unknown_width':
                next(p for p in data['mi']['points'] if p['point_id'] == 'F')['half_width_if_equal_sides'] = None
            else:
                next(e for e in data['mi']['longitudinal_projections'] if (e['from'], e['to']) == ('F', 'G'))['dimension_kind'] = 'direct_length'
            with self.subTest(change=change), self.assertRaises(ValueError):
                SCREEN.nominal_network(data)

    def test_missing_foreign_or_reassigned_original_ids_are_rejected(self):
        vertices = np.arange(24, dtype=float).reshape(8, 3)
        ids = {f'component_{i}': np.array([2 * i, 2 * i + 1]) for i in range(4)}
        rows = [{'component_id': i, 'vertices': 2, 'broad_25x34_size_candidate': True,
                 'centroid_vehicle_mm': vertices[ids[f'component_{i}']].mean(axis=0).tolist()} for i in range(4)]
        audit = {'candidates': rows, 'broad_25x34_size_candidates': 4}
        SCREEN.candidate_points(audit, ids, vertices)
        for change in ('missing', 'foreign', 'reassigned', 'repeated'):
            changed = copy.deepcopy(ids)
            if change == 'missing': del changed['component_0']
            if change == 'foreign': changed['component_0'] = np.array([100, 101])
            if change == 'reassigned': changed['component_0'] = np.array([6, 7])
            if change == 'repeated': changed['component_0'] = np.array([0, 0])
            with self.subTest(change=change), self.assertRaises(ValueError):
                SCREEN.candidate_points(audit, changed, vertices)

    def test_independent_scalar_checker_rejects_changed_metrics_and_admission(self):
        result = SCREEN.screen(self.source, self.source)
        for key, value in [('minimum_worst_edge_error_mm', 1), ('engineering_admission', True),
                           ('rigid_transform', np.eye(4).tolist()), ('candidate_count', 20)]:
            changed = copy.deepcopy(result)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                SCREEN.verify_metrics(self.source, self.source, changed)

    def test_wrong_pinned_source_hash_fails_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.json'
            path.write_text('{}')
            output = ROOT / 'work' / ('rejected-' + Path(folder).name)
            command = [sys.executable, str(SCRIPT), '--source-data', str(path), '--audit', str(path),
                       '--candidate-ids', str(path), '--vertices', str(path), '--output', str(output)]
            for name in ('source', 'audit', 'candidate-ids'):
                command.extend(['--' + name + '-sha256', '0' * 64])
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('hash mismatch', result.stderr)
            self.assertFalse(output.exists())

    def test_same_centroid_substitution_with_correct_individual_hashes_breaks_audit_binding(self):
        angle = np.linspace(0, 2 * np.pi, 32, endpoint=False)
        rim = np.column_stack([17 * np.cos(angle), 12.5 * np.sin(angle), np.zeros(32)])
        patches = [rim + centre for centre in self.source]
        # Coincident unused vertices permit a false ID reassignment without
        # changing any centroid or network distance.
        vertices = np.vstack([*patches, patches[0]])
        edges = np.vstack([np.column_stack([np.arange(32) + 32 * i,
                                            np.roll(np.arange(32) + 32 * i, -1)])
                           for i in range(4)])
        audit, ids = EXTRACT.extract(vertices, edges)
        self.assertEqual(audit['broad_25x34_size_candidates'], 4)
        substituted = copy.deepcopy(ids)
        substituted['component_0'] = np.arange(128, 160)
        np.testing.assert_allclose(SCREEN.candidate_points(audit, substituted, vertices), self.source,
                                   rtol=0, atol=1e-10)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            vertices_path = root / 'verts_vehicle.npy'
            ids_path = root / 'candidate-source-ids.npz'
            audit_path = root / 'audit.json'
            np.save(vertices_path, vertices)
            np.savez_compressed(ids_path, **ids)
            audit['candidate_source_ids_sha256'] = hashlib.sha256(ids_path.read_bytes()).hexdigest()
            audit['input_sha256'] = {'verts_vehicle.npy': hashlib.sha256(vertices_path.read_bytes()).hexdigest()}
            audit_path.write_text(json.dumps(audit))
            np.savez_compressed(ids_path, **substituted)
            source_path = ROOT / 'twins/964-chassis/owner-frame-data-20261105/source-data.json'
            output = ROOT / 'work' / ('binding-rejected-' + root.name)
            command = [sys.executable, str(SCRIPT), '--source-data', str(source_path),
                       '--audit', str(audit_path), '--candidate-ids', str(ids_path),
                       '--vertices', str(vertices_path), '--output', str(output)]
            for name, path in [('source', source_path), ('audit', audit_path), ('candidate-ids', ids_path)]:
                command.extend(['--' + name + '-sha256', hashlib.sha256(path.read_bytes()).hexdigest()])
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('extractor audit binding', result.stderr)
            self.assertFalse(output.exists())


EXTRACT_SPEC = importlib.util.spec_from_file_location('candidate_extractor', SCRIPT.with_name('extract_candidates.py'))
EXTRACT = importlib.util.module_from_spec(EXTRACT_SPEC)
EXTRACT_SPEC.loader.exec_module(EXTRACT)


class CandidateExtractionTests(unittest.TestCase):
    def setUp(self):
        angle = np.linspace(0, 2 * np.pi, 64, endpoint=False)
        ellipse = np.column_stack([17 * np.cos(angle), 12.5 * np.sin(angle), np.zeros(64)])
        tilt = np.array([[1, 0, 0], [0, .8, -.6], [0, .6, .8]])
        self.vertices = np.vstack([np.zeros((3, 3)), ellipse @ tilt.T + [100, 200, 300]])
        self.ids = np.arange(3, 67)
        self.edges = np.column_stack([self.ids, np.roll(self.ids, -1)])

    def test_closed_tilted_shape_preserves_original_ids_without_hole_identity(self):
        report, ids = EXTRACT.extract(self.vertices, self.edges)
        self.assertEqual(report['broad_25x34_size_candidates'], 1)
        self.assertEqual(report['simple_cycles'], 1)
        np.testing.assert_array_equal(ids['component_0'], self.ids)
        np.testing.assert_allclose(report['candidates'][0]['centroid_vehicle_mm'], [100, 200, 300])
        self.assertFalse(report['physical_vs_occlusion_resolved'])
        self.assertFalse(report['candidates'][0]['physical_hole_identified'])

    def test_open_or_branched_shape_is_preserved_but_not_accepted_as_a_cycle(self):
        extended = np.vstack([self.vertices, [100, 200, 300]])
        for edges in (self.edges[:-1], np.vstack([self.edges, [3, 67]])):
            with self.subTest(edges=len(edges)):
                report, ids = EXTRACT.extract(extended, edges)
                self.assertEqual(report['boundary_graph_components'], 1)
                self.assertEqual(report['simple_cycles'], 0)
                self.assertEqual(report['broad_25x34_size_candidates'], 0)
                np.testing.assert_array_equal(ids['component_0'], np.unique(edges))

    def test_foreign_repeated_and_noninteger_edges_and_wrong_hash_fail_closed(self):
        for edges in (self.edges.astype(float), np.vstack([self.edges, self.edges[0]]),
                      np.array([[3, 999]]), np.array([[3, 3]])):
            with self.subTest(edges=edges.shape), self.assertRaises(ValueError):
                EXTRACT.extract(self.vertices, edges)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.npy'
            np.save(path, self.vertices)
            output = ROOT / 'work' / ('extract-rejected-' + Path(folder).name)
            result = subprocess.run([sys.executable, str(SCRIPT.with_name('extract_candidates.py')),
                                     '--vertices', str(path), '--vertices-sha256', '0' * 64,
                                     '--source-open-edges', str(path), '--edges-sha256', '0' * 64,
                                     '--output', str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('hash mismatch', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
