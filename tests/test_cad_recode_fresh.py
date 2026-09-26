"""Small regression contract for the new raw-only reconstruction path."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.cad_recode import pipeline as p

try:
    import numpy as np
    import trimesh
    import cadquery
    HAS_CAD = True
except ImportError:
    HAS_CAD = False


class FreshRecodeTests(unittest.TestCase):
    def test_missing_physics_stays_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            result = p.readiness(p.ROOT / 'deploy/vast/cad-recode/engineering-inputs.json', Path(t) / 'report')
            self.assertEqual(len(result['missing']), 6)
            self.assertFalse(result['solver_authorized'])

    def test_mutable_image_rejected_before_docker(self):
        with patch('subprocess.run') as run:
            with self.assertRaises(ValueError):
                p.export_sandbox('none', 'none', 'none', 'cad:latest')
            run.assert_not_called()

    @unittest.skipUnless(HAS_CAD, 'run with the dedicated CAD requirements')
    def test_raw_roundtrip_and_integrity(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            raw = root / 'box.obj'
            mesh = trimesh.creation.box(extents=[20, 40, 60]); mesh.apply_translation([12, -7, 30]); mesh.export(raw)
            intake = root / 'intake'
            with self.assertRaises(ValueError):
                p.prepare(raw, intake, '0' * 64)
            report = p.prepare(raw, intake, p.digest(raw))
            self.assertEqual(report['legacy_inputs_used'], [])
            self.assertFalse(report['scale_verified'])
            center, scale = p.normalization(mesh.vertices)
            generated = (mesh.vertices - center) * scale * 100
            np.testing.assert_allclose(generated / 100 / scale + center, mesh.vertices, atol=1e-12)
            with self.assertRaises(FileExistsError): p.new_output(intake)
            (intake / 'points.npy').write_bytes(b'changed')
            with self.assertRaises(ValueError): p.verify_intake(intake)
            with self.assertRaises(ValueError): p.normalization([[float('nan'), 0, 0]])
            with self.assertRaises(ValueError): p.normalization([[0, 0, 0]])

    @unittest.skipUnless(HAS_CAD, 'run with the dedicated CAD requirements')
    def test_step_deviation_and_invalid_step(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            raw = root / 'box.obj'; trimesh.creation.box(extents=[20, 40, 60]).export(raw)
            p.prepare(raw, root / 'intake', p.digest(raw))
            step = root / 'box.step'
            cadquery.exporters.export(cadquery.Workplane('XY').box(20, 40, 60), str(step))
            report = p.evaluate(root / 'intake', step, root / 'evaluation')
            self.assertLess(report['scan_to_cad']['p95'], 1e-6)
            self.assertLess(report['cad_to_scan']['p95'], 1e-6)
            self.assertFalse(report['geometry_accepted'])
            step.write_text('not a STEP')
            with self.assertRaises(Exception): p.evaluate(root / 'intake', step, root / 'bad')



class SandboxFailureTests(unittest.TestCase):
    def test_timeout_and_nonzero_are_reported(self):
        import subprocess
        for error, expected in [(subprocess.TimeoutExpired('docker', 1), 'timeout'),
                                 (subprocess.CompletedProcess([], 1), 'failed')]:
            with tempfile.TemporaryDirectory() as t:
                root = Path(t); code = root / 'candidate.py'; code.write_text('raise RuntimeError()')
                with patch.object(p, 'verify_intake', return_value={}), patch('subprocess.run', side_effect=[error, subprocess.CompletedProcess([], 0)]) as run:
                    report = p.export_sandbox(code, root, root / 'out', 'sha256:' + 'a' * 64, 1)
                self.assertEqual(report['status'], expected)
                command = run.call_args_list[0].args[0]
                self.assertIn('--network=none', command)
                self.assertIn('--read-only', command)
                self.assertIn('--memory=4g', command)
                self.assertEqual(run.call_args_list[-1].args[0][:3], ['docker', 'rm', '-f'])

class QueueAndAssemblyTests(unittest.TestCase):
    def test_queue_contract_rejects_injection_and_fourth_attempt(self):
        import importlib.util
        import sys
        sys.path.insert(0, str(p.ROOT / 'scripts/cad_recode'))
        try:
            spec = importlib.util.spec_from_file_location('cad_dispatch_test', p.ROOT / 'scripts/cad_recode/dispatch.py')
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            self.assertEqual(module.request_stage({'stage':'export', 'attempt':1}), ('export', 1))
            for value in [{'stage':'export','attempt':4}, {'stage':'export','attempt':True},
                          {'stage':'exec','attempt':1}, {'stage':'export','attempt':1,'image':'evil'}]:
                with self.assertRaises(ValueError): module.request_stage(value)
            with tempfile.TemporaryDirectory() as t:
                with self.assertRaises(ValueError): module.contained(Path(t), Path(t) / '../outside')
        finally: sys.path.pop(0)

    @unittest.skipUnless(__import__('importlib').util.find_spec('pxr'), 'USD runtime required')
    def test_usd_composition_keeps_display_only_status(self):
        import subprocess
        import sys
        from pxr import Usd, UsdGeom
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            source = root / 'synthetic.usda'
            stage = Usd.Stage.CreateNew(str(source)); cube = UsdGeom.Cube.Define(stage, '/Cube')
            stage.SetDefaultPrim(cube.GetPrim()); stage.GetRootLayer().Save()
            output = root / 'comparison.usda'
            subprocess.run([sys.executable, str(p.ROOT / 'scripts/cad_recode/assemble.py'),
                str(source), str(source), str(output), '--scan-display-scale','1', '--cad-display-scale','1'], check=True)
            result = Usd.Stage.Open(str(output))
            self.assertTrue(result.GetPrimAtPath('/Comparison/Candidate'))
            self.assertFalse(result.GetRootLayer().customLayerData['physicsValidated'])
            reference = result.GetPrimAtPath('/Comparison/Candidate').GetMetadata('references').GetAddedOrExplicitItems()[0]
            self.assertEqual(reference.assetPath, 'synthetic.usda')
            empty = root / 'empty.usda'
            stage = Usd.Stage.CreateNew(str(empty)); node = UsdGeom.Xform.Define(stage, '/Empty')
            stage.SetDefaultPrim(node.GetPrim()); stage.GetRootLayer().Save()
            invalid_output = root / 'invalid.usda'
            rejected = subprocess.run([sys.executable, str(p.ROOT / 'scripts/cad_recode/assemble.py'),
                str(source), str(empty), str(invalid_output), '--scan-display-scale','1',
                '--cad-display-scale','1'], capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b'no renderable geometry', rejected.stderr)
            self.assertFalse(invalid_output.exists())

if __name__ == '__main__': unittest.main()
