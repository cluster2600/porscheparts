"""Analytical controls and forged-ledger refusals for surface-change proofs."""
from fractions import Fraction as Q
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

try:
    import numpy as np
except ImportError:
    np = None

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/replay_surface_conditioning_bounds.py'
if np is not None:
    spec = importlib.util.spec_from_file_location('carrier_bounds', SCRIPT)
    bounds = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bounds)


@unittest.skipUnless(np is not None, 'Optional numerical geometry dependency')
class SurfaceConditioningBoundsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def fixture(self, offset=75., height=.002):
        v = np.array([[offset, 30., 0.], [offset+1, 31., height],
                      [offset, 31., 0.], [offset+1, 30., 0.]])
        f = np.array([[0, 1, 2], [1, 0, 3]])
        cost = Q(height)/2
        operation = dict(face_indices=[0, 1], old_triangles=f.tolist(),
                         new_triangles=[[2, 3, 1], [3, 2, 0]],
                         diagonal_vertex_indices=[0, 1, 2, 3],
                         projection_drop_axis=2,
                         gap_numerator=str(cost.numerator),
                         gap_denominator=str(cost.denominator),
                         intersection_t=['1', '2'], intersection_u=['1', '2'])
        return v, f, cost, operation

    def recipe(self, v, f, cost, operations):
        source = self.directory/'reference.npz'
        np.savez(source, vertices=v, triangles=f)
        ledger = self.directory/'flip-ledger.json'
        ledger.write_text(json.dumps(dict(operations=operations,
                                         total_bound_numerator=str(cost.numerator),
                                         total_bound_denominator=str(cost.denominator))))
        final = f.copy()
        for operation in operations:
            final[operation['face_indices']] = operation['new_triangles']
        recipe = dict(stages=[dict(kind='edge_flip', ledger=str(ledger),
                                  geometry_sha256=bounds.geometry_signature(v, final))])
        return source, recipe, ledger

    def test_saddle_interior_has_nonzero_exact_distance_despite_shared_vertices(self):
        v, _, cost, _ = self.fixture(height=.2)
        observed, t, u = bounds.convex_flip_bound(v, 2)
        self.assertEqual((observed, t, u), (cost, Q(1, 2), Q(1, 2)))

    def test_flat_quad_has_zero_bound(self):
        v, _, _, _ = self.fixture(height=0.)
        self.assertEqual(bounds.convex_flip_bound(v, 2)[0], 0)

    def test_cap_homotopy_bound_handles_a_nonconvex_projection(self):
        v = np.array([[75., 30., 0.], [76., 30., 0.],
                      [75.5, 30.001, 0.], [75.5, 31., .1]])
        with self.assertRaisesRegex(ValueError, 'strictly convex'):
            bounds.convex_flip_bound(v, 2)
        cost, t = bounds.cap_flip_bound(v, 2)
        self.assertEqual(t, Q(1, 2))
        self.assertEqual(cost, 2*(Q(float(v[2, 1]))-Q(float(v[0, 1]))))

    def test_portable_replay_recovers_the_complete_geometry(self):
        v, f, cost, operation = self.fixture()
        source, recipe, _ = self.recipe(v, f, cost, [operation])
        output = self.directory/'replayed.npz'
        report = bounds.replay(source, recipe, output)
        self.assertEqual(Q(**{k:int(x) for k,x in report['whole_surface_additional_bound_exact'].items()}), cost)
        self.assertTrue(np.array_equal(np.load(output)['triangles'], operation['new_triangles']))

    def test_underreported_bound_is_rejected(self):
        v, f, cost, operation = self.fixture()
        operation['gap_numerator'] = '0'
        source, recipe, _ = self.recipe(v, f, cost, [operation])
        with self.assertRaisesRegex(ValueError, 'displacement bound differs'):
            bounds.replay(source, recipe)

    def test_changed_complete_output_is_rejected(self):
        v, f, cost, operation = self.fixture()
        source, recipe, _ = self.recipe(v, f, cost, [operation])
        recipe['stages'][0]['geometry_sha256']['vertices_f64_le'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'geometry signature differs'):
            bounds.replay(source, recipe)

    def test_protected_interface_edit_is_rejected(self):
        v, f, cost, operation = self.fixture(offset=50.)
        source, recipe, _ = self.recipe(v, f, cost, [operation])
        with self.assertRaisesRegex(ValueError, 'protected face'):
            bounds.replay(source, recipe)

    def test_edit_cannot_cross_a_fixed_regional_boundary(self):
        with self.assertRaisesRegex(ValueError, 'regional boundary'):
            bounds.quadrant(np.array([[75., -1., 0.], [75., 1., 0.]]))

    def collapse_fixture(self):
        v = np.array([[75., 30., .000001], [75.000001, 30., 0.],
                      [75., 31., 0.], [74., 30., 0.],
                      [75., 29., 0.], [75., 30., -1.]])
        f = np.array([[0,1,2], [0,2,3], [0,3,4], [0,4,1],
                      [5,2,1], [5,3,2], [5,4,3], [5,1,4]])
        source = self.directory/'collapse-reference.npz'
        np.savez(source, vertices=v, triangles=f)
        mapped = f.copy()
        mapped[mapped == 0] = 1
        keep = np.array([False,True,True,False,True,True,True,True])
        used = np.unique(mapped[keep])
        final_f = np.searchsorted(used, mapped[keep])
        cost = sum(abs(Q(float(a))-Q(float(b))) for a,b in zip(v[0], v[1]))
        operation = dict(removed_vertex=0, retained_vertex=1,
                         affected_face_indices=[0,1,2,3,4,7],
                         deleted_face_indices=[0,3],
                         deleted_triangle_image_segments=[[1,2],[1,4]],
                         l1_bound_numerator=str(cost.numerator),
                         l1_bound_denominator=str(cost.denominator))
        ledger = self.directory/'collapse-ledger.json'
        record = dict(operations=[operation],total_bound_numerator=str(cost.numerator),
                      total_bound_denominator=str(cost.denominator))
        ledger.write_text(json.dumps(record))
        recipe = dict(stages=[dict(kind='edge_collapse', ledger=str(ledger),
                                  geometry_sha256=bounds.geometry_signature(v[used], final_f))])
        return source, recipe, record, ledger, cost

    def test_closed_octahedron_collapse_has_a_complete_image_bound(self):
        source, recipe, _, _, cost = self.collapse_fixture()
        report = bounds.replay(source, recipe)
        exact = report['whole_surface_additional_bound_exact']
        self.assertEqual(Q(int(exact['numerator']), int(exact['denominator'])), cost)

    def test_forged_deleted_triangle_coverage_is_rejected(self):
        source, recipe, record, ledger, _ = self.collapse_fixture()
        record['operations'][0]['deleted_triangle_image_segments'][0] = [1,5]
        ledger.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, 'image receipt differs'):
            bounds.replay(source, recipe)

    def test_disjoint_patch_bounds_combine_by_maximum(self):
        v, f, cost, operation = self.fixture(height=.002)
        other_v, other_f, other_cost, other_op = self.fixture(offset=-75., height=.004)
        other_v[:, 1] -= 60
        other_f += 4
        other_op.update(face_indices=[2, 3], old_triangles=other_f.tolist(),
                        new_triangles=[[6, 7, 5], [7, 6, 4]],
                        diagonal_vertex_indices=[4, 5, 6, 7])
        source, recipe, _ = self.recipe(np.vstack([v, other_v]), np.vstack([f, other_f]),
                                       cost+other_cost, [operation, other_op])
        report = bounds.replay(source, recipe)
        exact = report['whole_surface_additional_bound_exact']
        self.assertEqual(Q(int(exact['numerator']), int(exact['denominator'])), other_cost)
        self.assertAlmostEqual(report['global_sum_for_comparison_mm'], float(cost+other_cost))


if __name__ == '__main__':
    unittest.main()
