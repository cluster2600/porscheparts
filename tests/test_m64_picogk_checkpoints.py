"""Synthetic software witnesses only; no private head geometry or CAE claims."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/picogk'
sys.path.insert(0, str(SOURCE))
import compare_meshes as audit


def synthetic_args(root):
    import trimesh
    cube = trimesh.creation.box(extents=[2., 2., 2.])
    master = root / 'synthetic-master.stl'
    cube.export(master)
    receipt = root / 'synthetic-export.json'
    receipt.write_text(json.dumps({'mesh_sha256': audit.sha256(master),
                                  'voxel_input_topology_gate_passed': True,
                                  'source_STEP_sha256': 'synthetic_only_no_STEP'}))
    candidates = []
    for resolution, offset in ((.8, .08), (.4, .04), (.2, .02)):
        folder = root / str(resolution)
        folder.mkdir()
        path = folder / 'head-roundtrip.stl'
        shifted = cube.copy(); shifted.apply_translation([offset, 0., 0.]); shifted.export(path)
        (folder / 'run-report.json').write_text(json.dumps({
            'input_sha256': audit.sha256(master), 'input_unchanged': True, 'transform': 'identity',
            'voxel_mm': resolution, 'roundtrip': {'sha256': audit.sha256(path),
                                                'filename': path.name, 'triangles': 12}}))
        candidates.append((str(resolution), str(path)))
    return SimpleNamespace(master=master, master_report=receipt, candidate=candidates,
                           output=root / 'audit-private', samples=64, chord_samples=64,
                           seed=17, query_chunk_size=8, render=False, resume=False)


@unittest.skipUnless(all(importlib.util.find_spec(name) for name in ('trimesh', 'rtree', 'scipy')),
                     'optional mesh QA runtime')
class PicoGKAuditCheckpointTests(unittest.TestCase):
    def test_checkpoint_survives_later_worker_failure_and_resume_does_not_repeat_it(self):
        with tempfile.TemporaryDirectory(prefix='synthetic-audit-checkpoints-') as directory:
            args = synthetic_args(Path(directory))

            def fail_second_candidate(args, context, index):
                if index == 1:
                    raise RuntimeError('synthetic_exit_137')
                audit.audit_worker(args, context, index)

            with mock.patch.object(audit, 'launch_worker', side_effect=fail_second_candidate):
                with self.assertRaisesRegex(RuntimeError, 'synthetic_exit_137'):
                    audit.run(args)
            first = args.output / 'candidate-0-checkpoint.json'
            preserved = first.read_bytes(), first.stat().st_mtime_ns
            self.assertFalse((args.output / 'mesh-comparison-report.json').exists())
            status = json.loads((args.output / 'audit-status.json').read_text())
            self.assertEqual(status['status'], 'failed_or_interrupted')
            self.assertEqual(status['completed_checkpoints'], ['master', 'candidate-0'])
            args.resume = True
            with mock.patch.object(audit, 'launch_worker', side_effect=audit.audit_worker) as worker:
                self.assertEqual(audit.run(args), 0)
                self.assertEqual([call.args[2] for call in worker.call_args_list], [1, 2])
            self.assertEqual((first.read_bytes(), first.stat().st_mtime_ns), preserved)
            report_path = args.output / 'mesh-comparison-report.json'
            report = json.loads(report_path.read_text())
            self.assertTrue(report['audit_complete'])
            self.assertFalse(report['manufacturing_authorized'])
            self.assertEqual(len(report['runs']), 3)
            status = json.loads((args.output / 'audit-status.json').read_text())
            self.assertEqual(status['report_sha256'], audit.sha256(report_path))
            self.assertEqual(args.output.stat().st_mode & 0o777, 0o700)
            self.assertTrue(all(path.stat().st_mode & 0o777 == 0o600 for path in args.output.iterdir()))

    def test_resume_rejects_changed_settings_code_candidate_and_master_even_with_updated_receipts(self):
        for change in ('settings', 'code', 'candidate', 'master', 'receipt'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                args = synthetic_args(Path(directory))
                # A crash before the first calculation still leaves the original binding.
                with mock.patch.object(audit, 'launch_worker', side_effect=RuntimeError('stopped')):
                    with self.assertRaisesRegex(RuntimeError, 'stopped'):
                        audit.run(args)
                args.resume = True
                real_hash = audit.sha256
                if change == 'settings':
                    args.seed += 1
                elif change == 'candidate':
                    path = Path(args.candidate[0][1])
                    data = path.read_bytes(); path.write_bytes(b'X' + data[1:])
                    receipt = path.parent / 'run-report.json'
                    record = json.loads(receipt.read_text())
                    record['roundtrip']['sha256'] = real_hash(path)
                    receipt.write_text(json.dumps(record))
                elif change == 'master':
                    data = args.master.read_bytes(); args.master.write_bytes(b'X' + data[1:])
                    record = json.loads(args.master_report.read_text())
                    record['mesh_sha256'] = real_hash(args.master)
                    args.master_report.write_text(json.dumps(record))
                    for _, filename in args.candidate:
                        path = Path(filename).parent / 'run-report.json'
                        record = json.loads(path.read_text()); record['input_sha256'] = real_hash(args.master)
                        path.write_text(json.dumps(record))
                elif change == 'receipt':
                    args.master_report.write_text(args.master_report.read_text() + '\n')

                def code_hash(path):
                    if change == 'code' and Path(path) == Path(audit.__file__):
                        return 'f' * 64
                    return real_hash(path)

                with mock.patch.object(audit, 'sha256', side_effect=code_hash):
                    with mock.patch.object(audit, 'launch_worker') as worker:
                        with self.assertRaisesRegex(ValueError, 'resume_context_mismatch'):
                            audit.run(args)
                        worker.assert_not_called()
                self.assertFalse((args.output / 'mesh-comparison-report.json').exists())

    def test_damaged_or_incomplete_checkpoint_never_becomes_a_complete_report(self):
        with tempfile.TemporaryDirectory() as directory:
            args = synthetic_args(Path(directory))

            def first_only(args, context, index):
                if index == 0:
                    raise RuntimeError('stopped')
                audit.audit_worker(args, context, index)

            with mock.patch.object(audit, 'launch_worker', side_effect=first_only):
                with self.assertRaises(RuntimeError):
                    audit.run(args)
            checkpoint = args.output / 'master-checkpoint.json'
            original = json.loads(checkpoint.read_text())
            args.resume = True
            for corruption in ('status', 'result'):
                with self.subTest(corruption=corruption):
                    record = json.loads(json.dumps(original))
                    if corruption == 'status':
                        record['status'] = 'incomplete'
                    else:
                        record['result']['master_mesh']['triangles'] += 1
                    audit.atomic_private_json(checkpoint, record)
                    with mock.patch.object(audit, 'launch_worker') as worker:
                        with self.assertRaisesRegex(ValueError, 'checkpoint_binding_status_or_integrity'):
                            audit.run(args)
                        worker.assert_not_called()
                    self.assertFalse((args.output / 'mesh-comparison-report.json').exists())

    def test_query_chunk_invariance_on_cube_and_hollow_shell_and_bounded_calls(self):
        import trimesh
        from trimesh.ray.ray_triangle import RayMeshIntersector
        cube = trimesh.creation.box(extents=[4., 4., 4.])
        inner = trimesh.creation.box(extents=[2., 2., 2.]); inner.invert()
        hollow = trimesh.util.concatenate([cube, inner])
        for mesh in (cube, hollow):
            with self.subTest(triangles=len(mesh.faces)):
                expected = audit.normal_chord_screen(mesh, 128, 11, chunk_size=512)
                reference = audit.surface_distances(mesh, cube, 128, 11, chunk_size=512)
                for size in (1, 7, 32):
                    self.assertEqual(audit.normal_chord_screen(mesh, 128, 11, chunk_size=size), expected)
                    measured = audit.surface_distances(mesh, cube, 128, 11, chunk_size=size)
                    for key, value in reference['distance_scan_units'].items():
                        self.assertAlmostEqual(measured['distance_scan_units'][key], value)
        real_intersection = RayMeshIntersector.intersects_location
        sizes = []

        def checked(tracer, origins, directions, **kwargs):
            sizes.append(len(origins))
            return real_intersection(tracer, origins, directions, **kwargs)

        with mock.patch.object(RayMeshIntersector, 'intersects_location', new=checked):
            audit.normal_chord_screen(hollow, 128, 11, chunk_size=7)
        self.assertGreater(len(sizes), 1)
        self.assertLessEqual(max(sizes), 7)
        for value in (0, -1, 513, 1.5, True):
            with self.assertRaises(ValueError):
                audit.validate_chunk_size(value)

    def test_atomic_write_failure_preserves_prior_complete_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'checkpoint.json'
            audit.atomic_private_json(path, {'complete': 'original'})
            original = path.read_bytes()
            with mock.patch.object(audit.os, 'replace', side_effect=OSError('synthetic_disk_failure')):
                with self.assertRaises(OSError):
                    audit.atomic_private_json(path, {'complete': 'new'})
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_forced_contains_fallback_is_seeded_chunk_invariant_and_rejects_remaining_ambiguity(self):
        import numpy as np
        import trimesh
        cube = trimesh.creation.box(extents=[4., 4., 4.])
        points = np.array([[.1, 0., 0.], [.2, 0., 0.], [.3, 0., 0.]])
        primary = np.array([0.4395064455, 0.617598629942, 0.652231566745])
        runs = []

        class SyntheticParityIntersector:
            def __init__(self):
                self.batches = []

            def intersects_location(self, origins, directions, multiple_hits=True):
                self.batches.append(len(origins))
                locations, ray_ids = [], []
                for index, (origin, direction) in enumerate(zip(origins, directions)):
                    # Force first pass odd/even disagreement with no free-space
                    # ray. The fallback resolves two points, not the third.
                    is_primary = np.array_equal(direction, primary) or np.array_equal(direction, -primary)
                    ambiguous = is_primary or origin[0] == .3
                    hits = 2 if ambiguous and direction[0] < 0 else 1
                    for step in range(hits):
                        locations.append(origin + (step + 1) * direction); ray_ids.append(index)
                return np.array(locations), np.array(ray_ids), np.zeros(len(ray_ids), dtype=int)

        for chunk in (1, 2, 7, 32):
            for _ in range(2):
                tracer = audit.BoundedRayIntersector(cube, chunk)
                witness = SyntheticParityIntersector(); tracer.tracer = witness
                # A global RNG/library fallback would be an error here.
                with mock.patch('trimesh.util.random_generator', side_effect=AssertionError('unseeded_rng')):
                    inside, evidence = audit.seeded_contains_points(tracer, points, 917)
                self.assertEqual(inside.tolist(), [True, True, False])
                self.assertEqual(evidence['fallback_samples'], 3)
                self.assertEqual(evidence['samples_still_ambiguous_after_fallback_rejected'], 1)
                self.assertIsNotNone(evidence['fallback_direction'])
                self.assertLessEqual(max(witness.batches), chunk)
                runs.append((inside.tolist(), evidence))
        self.assertTrue(all(run == runs[0] for run in runs))

    def test_concurrent_resume_is_rejected_by_live_output_lock(self):
        import fcntl
        import os
        with tempfile.TemporaryDirectory() as directory:
            args = synthetic_args(Path(directory))
            with mock.patch.object(audit, 'launch_worker', side_effect=RuntimeError('stopped')):
                with self.assertRaisesRegex(RuntimeError, 'stopped'):
                    audit.run(args)
            prior_status = (args.output / 'audit-status.json').read_bytes()
            args.resume = True
            descriptor = os.open(args.output / '.audit.lock', os.O_RDWR)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with mock.patch.object(audit, 'launch_worker') as worker:
                    with self.assertRaisesRegex(RuntimeError, 'locked_by_a_live_process'):
                        audit.run(args)
                    worker.assert_not_called()
                self.assertEqual((args.output / 'audit-status.json').read_bytes(), prior_status)
            finally:
                os.close(descriptor)


if __name__ == '__main__':
    unittest.main()
