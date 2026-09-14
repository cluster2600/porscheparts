"""Synthetic shell-classification witnesses, never a head fabrication claim."""
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
import audit_roundtrip_shells as audit


def synthetic_args(root, mesh):
    candidate = root / 'synthetic-roundtrip.stl'
    mesh.export(candidate)
    receipt = root / 'synthetic-run-report.json'
    receipt.write_text(json.dumps({
        'input_sha256': 'a' * 64, 'input_unchanged': True, 'transform': 'identity', 'voxel_mm': .3,
        'roundtrip': {'sha256': audit.sha256(candidate), 'filename': candidate.name,
                      'triangles': len(mesh.faces)}}))
    return SimpleNamespace(candidate=candidate, candidate_sha256=audit.sha256(candidate),
                           run_report=receipt, master_sha256='a' * 64, voxel_size=.3,
                           output=root / 'private-shell-report.json')


@unittest.skipUnless(all(importlib.util.find_spec(name) for name in ('numpy', 'trimesh', 'scipy')),
                     'optional mesh QA runtime')
class PicoGKRoundtripShellTests(unittest.TestCase):
    def test_hollow_witness_preserves_negative_shell_and_oriented_volume(self):
        import trimesh
        outer = trimesh.creation.box(extents=[20., 20., 20.])
        inner = trimesh.creation.box(extents=[12., 12., 12.]); inner.invert()
        mesh = trimesh.util.concatenate([outer, inner])
        with tempfile.TemporaryDirectory(prefix='synthetic-shell-audit-') as directory:
            args = synthetic_args(Path(directory), mesh)
            unchanged = args.candidate.read_bytes()
            self.assertEqual(audit.run(args), 0)
            report = json.loads(args.output.read_text())
            self.assertEqual(report['boundary_shell_count'], 2)
            self.assertEqual(report['positive_oriented_shells'], 1)
            self.assertEqual(report['negative_oriented_shells'], 1)
            self.assertEqual(sorted(row['signed_volume_scan_units_cubed'] for row in report['boundary_shells']),
                             [-1728., 8000.])
            self.assertAlmostEqual(report['oriented_shell_volume_sum_scan_units_cubed'], 6272.)
            self.assertTrue(report['source_files_unchanged_after_read_only_audit'])
            self.assertTrue(report['boundary_shell_counts_are_not_connected_fluid_volume_counts'])
            self.assertFalse(report['repair_or_small_shell_removal_performed'])
            self.assertFalse(report['manufacturing_authorized'])
            self.assertEqual(args.output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(args.candidate.read_bytes(), unchanged)

    def test_small_disconnected_positive_island_is_not_deleted(self):
        import trimesh
        large = trimesh.creation.box(extents=[10., 10., 10.])
        tiny = trimesh.creation.box(extents=[.01, .01, .01]); tiny.apply_translation([6., 0., 0.])
        with tempfile.TemporaryDirectory() as directory:
            args = synthetic_args(Path(directory), trimesh.util.concatenate([large, tiny]))
            self.assertEqual(audit.run(args), 0)
            report = json.loads(args.output.read_text())
            self.assertEqual(report['positive_oriented_shells'], 2)
            self.assertEqual(report['negative_oriented_shells'], 0)
            smallest = min(report['boundary_shells'], key=lambda row: row['signed_volume_scan_units_cubed'])
            self.assertEqual(smallest['triangles'], 12)
            self.assertGreater(smallest['signed_volume_scan_units_cubed'], 0.)
            self.assertLess(smallest['signed_volume_scan_units_cubed'], 2e-6)

    def test_wrong_sha_resolution_frame_and_triangle_count_cannot_pass(self):
        import trimesh
        for field in ('sha256', 'voxel_mm', 'transform', 'triangles', 'input_sha256', 'input_unchanged'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                args = synthetic_args(Path(directory), trimesh.creation.box())
                receipt = json.loads(args.run_report.read_text())
                if field == 'sha256':
                    receipt['roundtrip'][field] = 'b' * 64
                elif field == 'triangles':
                    receipt['roundtrip'][field] = 99
                else:
                    receipt[field] = {'voxel_mm': .6, 'transform': 'translation',
                                      'input_sha256': 'b' * 64, 'input_unchanged': False}[field]
                args.run_report.write_text(json.dumps(receipt))
                with self.assertRaises(ValueError):
                    audit.run(args)
                self.assertFalse(args.output.exists())

    def test_open_surface_is_diagnostic_failure_not_an_accepted_volume(self):
        import trimesh
        mesh = trimesh.creation.box()
        mesh.update_faces(range(len(mesh.faces) - 1))
        with tempfile.TemporaryDirectory() as directory:
            args = synthetic_args(Path(directory), mesh)
            self.assertEqual(audit.run(args), 2)
            report = json.loads(args.output.read_text())
            self.assertFalse(report['trimesh_watertight'])
            self.assertFalse(report['oriented_volume_crosscheck_passed'])

    def test_failed_shell_sum_and_changed_source_cannot_pass(self):
        import trimesh
        for failure in ('volume', 'triangles', 'mutation'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                args = synthetic_args(Path(directory), trimesh.creation.box())
                real_shells = audit.boundary_shells

                def broken(mesh):
                    shells = real_shells(mesh)
                    if failure == 'volume':
                        shells[0]['signed_volume_scan_units_cubed'] *= 2
                    elif failure == 'triangles':
                        shells[0]['triangles'] -= 1
                    else:
                        data = args.candidate.read_bytes()
                        args.candidate.write_bytes(b'X' + data[1:])
                    return shells

                with mock.patch.object(audit, 'boundary_shells', side_effect=broken):
                    if failure == 'mutation':
                        with self.assertRaisesRegex(ValueError, 'source_changed'):
                            audit.run(args)
                        self.assertFalse(args.output.exists())
                    else:
                        self.assertEqual(audit.run(args), 2)
                        self.assertFalse(json.loads(args.output.read_text())['oriented_volume_crosscheck_passed'])


if __name__ == '__main__':
    unittest.main()
