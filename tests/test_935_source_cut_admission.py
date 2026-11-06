"""Adversarial checks for source-supported provisional separation (synthetic only)."""
import copy
import importlib.util
import hashlib
import json
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/research/935-source-cut-admission-20261106/source'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SOURCE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


producer = load('audit_source_cuts')
checker = load('check_source_cuts')


class SourceCutAdmission(unittest.TestCase):
    def test_public_receipt_binds_sources_and_preserves_release_boundary(self):
        receipt = json.loads((SOURCE.parent / 'results.json').read_text())
        for row in receipt['executed_sources']:
            path = SOURCE / row['name']
            with path.open('rb') as stream:
                self.assertEqual(hashlib.file_digest(stream, 'sha256').hexdigest(), row['sha256'])
        partition = receipt['source_partition']
        self.assertEqual(partition['all_acquired_faces_accounted'],
                         partition['retained_source_faces'] + partition['proposed_removed_source_faces']
                         + partition['quarantined_faces_retained_in_original'])
        self.assertEqual(partition['transition_faces_retained'],
                         sum(row['transition_faces'] for row in receipt['regions']))
        self.assertEqual(partition['proposed_removed_source_faces'],
                         sum(row['fully_outward_faces'] for row in receipt['regions']))
        for row in receipt['regions']:
            for stage in ('first_native_export', 'actual_saved_FreeCAD_export'):
                self.assertEqual(row[stage]['source_native_comparison']['vertex_roundtrip_maximum_mm'], 0)
                self.assertTrue(all(row[stage]['source_native_comparison']['checks'].values()))
                self.assertTrue(row[stage]['section_native_comparison']['zero_faces_and_solids'])
        for field in ('complete_bare_head_created', 'anatomical_identity_accepted',
                      'physical_acceptance', 'manufacturing_authorized', 'print_ready', 'all_G0_to_G5'):
            self.assertFalse(receipt['release'][field])
        self.assertNotIn('/Users/', json.dumps(receipt))

    def fixture(self):
        vertices, faces = producer.cylinder()
        ids = np.arange(len(faces))
        plane = np.array([0., 0., 1., 0.])
        report, private = producer.section(vertices, faces, ids, plane)
        return vertices, faces, ids, plane, report, private

    def test_analytic_and_exact_predicate_controls(self):
        self.assertTrue(all(producer.controls().values()))
        self.assertTrue(all(checker.controls().values()))

    def test_original_mesh_fully_rejoined_by_independent_checker(self):
        result, proposals = checker.inspect(*self.fixture())
        self.assertTrue(result['whole_component_partition_bijection'])
        self.assertEqual(len(proposals), 1)
        self.assertTrue(proposals[0]['admitted'])

    def test_shared_negative_edge_does_not_connect_outside_regions(self):
        vertices = np.array([[0., 0., -1.], [1., 0., -1.],
                             [0., 1., 2.], [0., -1., 2.]])
        faces = np.array([[0, 1, 2], [1, 0, 3]])
        ids = np.arange(2)
        plane = np.array([0., 0., 1., 0.])
        report, private = producer.section(vertices, faces, ids, plane)
        self.assertEqual(report['positive_surface_components'], 2)
        result, _ = checker.inspect(vertices, faces, ids, plane, report, private)
        self.assertTrue(result['whole_component_partition_bijection'])
        forged = {k: v.copy() for k, v in private.items()}
        forged['active_component_labels'][:] = 0
        with self.assertRaises(AssertionError):
            checker.inspect(vertices, faces, ids, plane, report, forged)

    def test_mutated_rounded_intersection_refused(self):
        vertices, faces, ids, plane, report, private = self.fixture()
        private['rounded_source_edge_intersections'][0, 0] += 1e-5
        with self.assertRaises(AssertionError):
            checker.inspect(vertices, faces, ids, plane, report, private)

    def test_same_count_scrambled_loop_refused(self):
        vertices, faces, ids, plane, report, private = self.fixture()
        loop = private['component_0_loop_0_edge_codes']
        loop[[1, 3]] = loop[[3, 1]]
        with self.assertRaises(AssertionError):
            checker.inspect(vertices, faces, ids, plane, report, private)

    def test_invented_metric_or_selected_status_refused(self):
        vertices, faces, ids, plane, report, private = self.fixture()
        for key, value in [('area_nominal_mm2', 40.),
                           ('selected_provisional_region', False)]:
            forged = copy.deepcopy(report)
            forged['regions'][0][key] = value
            with self.assertRaises(AssertionError):
                checker.inspect(vertices, faces, ids, plane, forged, private)


if __name__ == '__main__':
    unittest.main()
