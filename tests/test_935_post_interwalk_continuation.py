"""Independent topology controls for same-walk continuation after inter-walk bands."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class ContinuationTopologyTests(unittest.TestCase):
    def setUp(self):
        self.audit = module('docs/research/935-post-interwalk-continuation-20261106/source/verify_continuation_topology.py', 'continuation_topology')
        self.checker = module('docs/research/935-interwalk-admission-20261106/source/verify_interwalk_pairs.py', 'independent_primal_components')
        theta = np.arange(8)*2*np.pi/8
        points = np.r_[np.c_[np.cos(theta), np.sin(theta), np.zeros(8)], [[0., 0., -1.]]]
        faces = np.array([[8, i, (i+1) % 8] for i in range(8)])
        self.parent = dict(points=points, triangles=faces)
        self.boundary = self.checker.fixture_boundary(faces)
        edges = self.boundary['boundary']
        left = int(np.flatnonzero(np.all(edges == [0, 1], axis=1))[0])
        right = int(np.flatnonzero(np.all(edges == [4, 5], axis=1))[0])
        self.census = dict(selected_pair_edge_ids=np.array([[left, right]]),
                           selected_pair_curve_ids=np.array([0]), edge_curve_ids=np.zeros(len(edges), dtype=int))
        self.mesh = dict(points=points.copy(), triangles=np.r_[faces, [[1, 0, 5], [1, 5, 4]]],
                         source_continuation_pair_ids=np.r_[np.full(8, -1), [21, 21]])

    def inspect(self, mesh=None, census=None):
        mesh = self.mesh if mesh is None else mesh
        boundary = self.checker.fixture_boundary(mesh['triangles'])
        return self.audit.inspect_change(mesh, self.parent, self.census if census is None else census,
                                         boundary, self.boundary, self.checker, 21)

    def test_same_walk_band_measured_combined_topology(self):
        before, after, delta, accepted = self.inspect()
        self.assertEqual(before.tolist(), [[9, 16, 8, 1, 1, 0]])
        self.assertEqual(after.tolist(), [[9, 19, 10, 2, 0, 0]])
        self.assertEqual(delta.tolist(), [[0, 3, 2, 1, -1, 0]])
        self.assertEqual(accepted, 1)

    def test_moved_source_point_refused(self):
        changed = dict(self.mesh, points=self.mesh['points'].copy())
        changed['points'][0, 0] += .01
        with self.assertRaises(AssertionError):
            self.inspect(changed)

    def test_wrong_target_walk_or_global_id_refused(self):
        wrong = dict(self.census, selected_pair_curve_ids=np.array([9]))
        with self.assertRaises(AssertionError):
            self.inspect(census=wrong)
        changed = dict(self.mesh, source_continuation_pair_ids=np.r_[np.full(8, -1), [20, 20]])
        with self.assertRaises(AssertionError):
            self.inspect(changed)

    def test_unmodified_parent_no_topology_change(self):
        unchanged = dict(self.parent, source_continuation_pair_ids=np.full(8, -1))
        before, after, delta, accepted = self.inspect(unchanged)
        self.assertTrue(np.array_equal(before, after))
        self.assertFalse(delta.any())
        self.assertEqual(accepted, 0)


class EmptyFrontierTests(unittest.TestCase):
    def setUp(self):
        self.checker = module('docs/research/935-post-interwalk-continuation-20261106/source/verify_empty_frontier.py', 'empty_frontier')
        self.history = np.arange(1706*6).reshape(1706, 6)
        self.registry = dict(global_pair_ids=np.array([0]), raw_pair_keys=self.history[1705:])
        self.census = dict(eligible_pair_edge_ids=np.empty((0, 2), dtype=np.int64),
            selected_pair_edge_ids=np.empty((0, 2), dtype=np.int64), selected_eligible_pair_indices=np.array([], dtype=int),
            prior_attempted_pair_keys=self.history)
        self.proof = dict(census_independently_verified=True, mesh_sha256='a'*64, census_sha256='b'*64,
                          eligible_pairs=0, selected_pairs=0, all_attempted_raw_pair_identities=len(self.history))
        self.surface = dict(mesh_sha256='a'*64, surface_study_checks_passed=True)
        self.topology = dict(mesh_sha256='a'*64, exact_final_Euler_boundary_genus_verified=True)

    def inspect(self, proof=None, census=None):
        return self.checker.inspect(self.census if census is None else census,
            self.proof if proof is None else proof, self.surface, self.topology,
            self.registry, self.history, 'a'*64, 'b'*64)

    def test_empty_scope_and_history_stop(self):
        self.assertEqual(self.inspect(), (1706, 1))

    def test_nonempty_or_unverified_or_other_mesh_refused(self):
        for change in ({'eligible_pairs': 1}, {'selected_pairs': 1},
                       {'census_independently_verified': False}, {'mesh_sha256': 'c'*64}):
            with self.assertRaises(AssertionError):
                self.inspect(proof=dict(self.proof, **change))

    def test_altered_history_or_hidden_pair_refused(self):
        for change in ({'eligible_pair_edge_ids': np.array([[1, 2]])},
                       {'prior_attempted_pair_keys': self.history[:-1]}):
            with self.assertRaises(AssertionError):
                self.inspect(census=dict(self.census, **change))


class BoundaryFrontierTests(unittest.TestCase):
    def setUp(self):
        self.checker = module('docs/research/935-post-interwalk-continuation-20261106/source/summarize_boundary_frontier.py', 'boundary_inventory')
        self.row = dict(curve=0, edges=4, vertices=4, edge_origin_counts={'1': 4},
            repeated_coordinate_visits=0, affine_rank=3, bounds_diagonal_nominal_mm=2.,
            plane_maximum_residual_nominal_mm=.3, closure_authorized=False, physical_classification='unreviewed')

    def test_compact_nonplanar_count_has_no_admission(self):
        result = self.checker.summarise([self.row], 4, 1)
        self.assertEqual(result['ordered_first_reason_walks'], {'compact_nonplanar_frontier_needs_new_admission': 1})
        self.assertFalse(result['manufacturing_authorized'])
        self.assertTrue(result['projection_normal_ancestry_native_and_support_admission_not_granted'])

    def test_partition_priority_does_not_hide_overlapping_flags(self):
        wide = dict(self.row, bounds_diagonal_nominal_mm=8.)
        result = self.checker.summarise([wide], 4, 1)
        self.assertEqual(result['ordered_first_reason_walks'], {'outside_3_mm_diagonal_study_scope': 1})
        self.assertEqual(result['overlapping_geometry_flags']['over_0_25_nominal_mm_plane_residual'], 1)

    def test_denominator_origin_and_physical_state_forgeries_refused(self):
        for change in ({'curve': 1}, {'edge_origin_counts': {'1': 3}}, {'closure_authorized': True},
                       {'physical_classification': 'accepted'}):
            with self.assertRaises(AssertionError):
                self.checker.summarise([dict(self.row, **change)], 4, 1)

    def test_inferred_edges_supply_no_independent_acquired_normal(self):
        value = dict(self.row, edge_origin_counts={'9': 4})
        self.assertEqual(self.checker.category(value), 'no_actual_acquired_edge')


if __name__ == '__main__':
    unittest.main()
