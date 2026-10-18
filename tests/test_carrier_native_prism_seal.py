"""Synthetic receipt transport witnesses, distinct from native CSG executions."""
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

if importlib.util.find_spec('numpy') is None:
    raise unittest.SkipTest('Optional NumPy runtime required')
import numpy as np

SOURCE = Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0, str(SOURCE))
import seal_prism_native_case as sealer


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True)+'\n')


def fixture(root):
    """A tetrahedron plus synthetic receipts exercises only proof-file transport."""
    original, final, distance = [root/name for name in ('original', 'final', 'distance')]
    for path in (original, final, distance):
        path.mkdir()
    vertices = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
    faces = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]], dtype=np.int64)
    raw = dict(vertices=vertices, faces=faces, source=np.zeros(4, dtype=np.int64), source_face=np.arange(4),
               all_parent_offsets=np.arange(5), all_parent_faces=np.arange(4))
    np.savez(original/'result.npz', **raw)
    np.savez(final/'result.npz', **raw, autorefine_input_face=np.arange(4, dtype=np.int64))
    (original/'result.mesh64.exact').write_text('Synthetic tetrahedron exact-payload identity fixture\n')
    native = dict(exact_output_self_intersection_free=True, exact_collinear_output_triangles=0,
                  source_face_lineage_complete=True, maximum_coordinate_rounding_squared_mm2_exact='0')
    write(original/'native.json', native)
    write(original/'audit.json', dict(native_exact_gate_pass=True, native=native,
        exact_result_sha256=sealer.sha(original/'result.mesh64.exact'), result_sha256=sealer.sha(original/'result.npz'),
        leaf_role_order=['positive_roof_prisms', 'mask', 'part', 'clip_bbox'], leaf_face_counts=[8, 4, 4, 12]))
    execution = dict(status='executed', returncode=0, identities_unchanged=True, owned_scope_inactive=True)
    write(original/'execution-receipt.json', dict(execution, output_files_sha256={name:sealer.sha(original/name)
        for name in ('result.npz', 'result.mesh64.exact', 'native.json', 'audit.json')}))
    steps = [math.ldexp(1., -49)]*3
    bound = 5*math.sqrt(sum(s*s for s in steps))/2
    snapped = dict(native_return=True, post_double_self_intersection_free=True, exact_collinear_output_triangles=0,
        all_output_coordinates_exactly_double=True, snap_grid_bits=51, iteration_budget=5,
        maximum_absolute_coordinates_mm=[1., 1., 1.], grid_step_mm=steps, cumulative_rounding_budget_mm=bound)
    write(final/'native.json', snapped)
    topology = dict.fromkeys(['boundary_edges', 'nonmanifold_edges', 'nonmanifold_vertices',
                              'unused_vertices', 'inconsistent_orientation_edges'], 0)
    write(final/'audit.json', dict(native_gate_pass=True, topology_gate_pass=True, native=snapped,
        output_topology=dict(topology, **{'pass':True, 'signed_volume_mm3':1/6}),
        result_sha256=sealer.sha(final/'result.npz'), input_sha256=sealer.sha(original/'result.npz')))
    write(final/'execution-receipt.json', execution)
    directions = {name:dict(maximum_distance_squared_exact='0', samples=8, **{'pass':True})
                  for name in ('input_to_output', 'output_to_input')}
    write(distance/'audit.json', dict(native_geometry_gate_pass=True, topology_gate_pass=True,
        input_sha256=sealer.sha(original/'result.npz'), result_sha256=sealer.sha(final/'result.npz'),
        origin_native_sha256=sealer.sha(final/'native.json'), origin_audit_sha256=sealer.sha(final/'audit.json'),
        origin_execution_receipt_sha256=sealer.sha(final/'execution-receipt.json'),
        shape_drift_limit_mm=bound, exact_distance=directions, **{'pass':True}))
    write(distance/'execution-receipt.json', execution)
    bound_inputs = [original/name for name in ('result.npz', 'result.mesh64.exact', 'native.json', 'audit.json')]
    bound_inputs += [final/'result.npz', distance/'audit.json']
    write(root/'composed.json', dict(identities_unchanged=True, original_shape_drift_limit_mm=bound,
        inputs_sha256={str(p):sealer.sha(p) for p in bound_inputs},
        conversion=dict(maximum_distance_squared_exact='0'), directions={name:dict(
            distance_witness_upper_bound_squared_exact='0', conversion_upper_bound_squared_exact='0',
            composed_upper_bound_mm_approx=0., finite_samples=8, **{'pass':True}) for name in directions}, **{'pass':True}))
    np.savez(root/'pairs.npz', pairs=np.empty((0, 2), dtype=np.int64))
    write(root/'contacts.json', dict(mesh_npz_sha256=sealer.sha(final/'result.npz'),
        raw_pairs_npz_sha256=sealer.sha(root/'pairs.npz'), raw_detector_pair_count_unchanged=0, remaining_pair_count=0))
    write(root/'plan.json', dict(downstream_frozen=dict(original_shape_drift_limit_mm=bound)))
    write(root/'schema.json', dict(scope='Synthetic transport fixture, not a native prism proof'))
    return dict(original_native_job=original, final_snap_job=final, distance_job=distance,
        composed=root/'composed.json', contacts=root/'contacts.json', pairs=root/'pairs.npz',
        frozen_plan=root/'plan.json', schema=root/'schema.json', output=root/'sealed', source_index=0)


class NativePrismSeal(unittest.TestCase):
    def test_synthetic_receipts_are_verified_packaged_and_portable_without_rewriting_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            args = fixture(root)
            before = {p:sealer.sha(p) for p in root.rglob('*') if p.is_file()}
            receipt = sealer.seal(**args)
            self.assertIs(receipt['process_anchor_admission'], False)
            self.assertEqual(sealer.load_case(args['output']/'native_audit.json').source_index, 0)
            mapping = json.loads((args['output']/'local-evidence-map.json').read_text())
            self.assertTrue(all(not Path(row['path']).is_absolute() and '..' not in Path(row['path']).parts
                                for row in mapping['files'].values()))
            self.assertTrue(all(sealer.sha(path) == digest for path, digest in before.items()))
            moved = root/'moved'
            shutil.move(args['output'], moved)
            self.assertTrue(sealer.load_case(moved/'native_audit.json').verify())
            assessment = json.loads((moved/'seal-assessment.json').read_text())
            self.assertIs(assessment['strict_reader_verified'], True)
            self.assertIs(assessment['native_calculation_executed_by_sealer'], False)
            payload = moved/next(iter(mapping['files'].values()))['path']
            with payload.open('ab') as stream:
                stream.write(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
                sealer.load_case(moved/'native_audit.json')

    def test_false_topology_or_contact_identity_never_publishes_an_accepted_package(self):
        for corrupt in ('topology', 'contacts'):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                args = fixture(root)
                if corrupt == 'topology':
                    path = args['final_snap_job']/'audit.json'
                    value = json.loads(path.read_text())
                    value['topology_gate_pass'] = False
                else:
                    path = args['contacts']
                    value = json.loads(path.read_text())
                    value['mesh_npz_sha256'] = 'wrong'
                write(path, value)
                with self.assertRaises(ValueError):
                    sealer.seal(**args)
                self.assertFalse(args['output'].exists())
                self.assertFalse(list(root.glob('.sealed-pending-*')))

    def test_repair_arguments_are_explicit_and_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            args = fixture(root)
            with self.assertRaisesRegex(ValueError, 'together'):
                sealer.seal(**args, repair_candidate_dir=root/'repair')
            with self.assertRaisesRegex(ValueError, 'central0'):
                sealer.seal(**dict(args, source_index=2))
            args['output'].mkdir()
            (args['output']/'user.txt').write_text('retain')
            with self.assertRaisesRegex(ValueError, 'must be new'):
                sealer.seal(**args)
            self.assertEqual((args['output']/'user.txt').read_text(), 'retain')

    def test_an_unapproved_reader_is_refused_before_publishing(self):
        with tempfile.TemporaryDirectory() as directory:
            args = fixture(Path(directory).resolve())
            with mock.patch.object(sealer, 'READER_SHA256', 'wrong'):
                with self.assertRaisesRegex(ValueError, 'approved strict reader'):
                    sealer.seal(**args)
            self.assertFalse(args['output'].exists())

    def test_composed_path_label_is_retained_and_ambiguous_hash_lookup_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root/'evidence').mkdir()
            path = root/'receipt.json'
            path.write_text('{}\n')
            evidence = sealer.Evidence(root, dict(inputs_sha256={'original-label':sealer.sha(path)}))
            self.assertEqual(evidence.add(path, linked=True)['path'], 'original-label')
            evidence.composed['inputs_sha256']['ambiguous-same-payload'] = sealer.sha(path)
            with self.assertRaisesRegex(ValueError, 'uniquely bind'):
                evidence.add(path, linked=True)

    def test_unknown_final_ids_are_derived_without_using_a_negative_lookup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            np.savez(root/'final.npz', faces=np.array([[0, 1, 2], [1, 2, 3]]),
                     autorefine_input_face=np.array([1, 0], dtype=np.int64))
            np.savez(root/'repair.npz', faces=np.array([[0, 1, 2], [1, 2, 3]]), repair_changed_face=np.array([True, False]))
            self.assertEqual(sealer.changed_faces(root/'final.npz', root/'repair.npz'), [1])
            np.savez(root/'final.npz', faces=np.array([[0, 1, 2]]), autorefine_input_face=np.array([-1], dtype=np.int64))
            with self.assertRaisesRegex(ValueError, 'changed-face mask'):
                sealer.changed_faces(root/'final.npz', root/'repair.npz')


if __name__ == '__main__':
    unittest.main()
