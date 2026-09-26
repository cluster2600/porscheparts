"""G12 receipt binding, immutable checkpoints and fail-closed refinement."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/fourvalve'))
try:
    import g12_campaign as g12
except ImportError:
    g12 = None


@unittest.skipIf(g12 is None, 'optional numerical runtime unavailable')
class G12CampaignChecks(unittest.TestCase):
    def test_published_cad_binding_rejects_changed_receipt_and_step(self):
        published = g12.g8.REPO/'twins/m64-cylinder-head/evidence/g12-local-buttresses-20260926/cad.json'
        self.assertEqual(g12.g8.sha256(published), g12.CAD_SHA256)
        data = json.loads(published.read_text())
        self.assertEqual(tuple(v['id'] for v in data['variants'] if v['cad_accepted']), g12.ACCEPTED)
        baseline = json.loads(g12.g8.BASELINE.read_text())
        forces = g12.g11.forces(baseline, 'central_diaphragm')
        self.assertAlmostEqual(forces['intake'], 6881.35243458258)
        self.assertAlmostEqual(forces['exhaust'], 6702.484411298031)
        self.assertEqual((g12.g8.E, g12.g8.NU), (70000., .33))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); receipt = root/'receipt.json'
            receipt.write_bytes(published.read_bytes())
            for variant in data['variants']:
                step = root/variant['step']; step.parent.mkdir(); step.write_text('untrusted STEP')
            with self.assertRaisesRegex(ValueError, 'invalid G12 STEP'):
                g12.inputs(receipt)
            receipt.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'published fingerprint'):
                g12.inputs(receipt)

    def test_recovery_binds_artifacts_source_and_case(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); artifact = root/'x.dat'; artifact.write_text('original')
            variant = dict(id=g12.ACCEPTED[0], component='central_diaphragm', step_sha256='step')
            result = dict(variant, mesh={'size_mm':2.}, backend='cpu', cad_receipt_sha256=g12.CAD_SHA256,
                          source_sha256=g12.g11.source_hashes(), campaign_source_sha256=g12.g8.sha256(Path(g12.__file__)),
                          cases=[], hashes={'x.dat':g12.g8.sha256(artifact)})
            path = root/'result.json'; g12.g11.publish(path, result)
            record = dict(id=variant['id'],size_mm=2.,path='result.json',sha256=g12.g8.sha256(path))
            self.assertEqual(g12.recover(root, record, {variant['id']:variant}, 'cpu'), result)
            with self.assertRaisesRegex(ValueError, 'binding changed'):
                g12.recover(root, dict(record,size_mm=1.), {variant['id']:variant}, 'cpu')
            artifact.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'artifact changed'):
                g12.recover(root, record, {variant['id']:variant}, 'cpu')

    def test_deadline_failed_screen_and_interruption_do_not_promote_results(self):
        for mode in ('deadline', 'failed', 'interrupt'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                variants = {i: {'volume_mm3':1., 'projected_land':{'structural_contact_qualified':False}} for i in g12.ACCEPTED}
                args = SimpleNamespace(cad=root/'receipt.json', output=root/'out', backend='cpu',
                                       deadline=time.time()+(0 if mode=='deadline' else 100), case_timeout=10,reserve_seconds=1)
                with patch.object(g12, 'inputs', return_value=({}, {}, variants)), \
                        patch.object(g12.subprocess, 'Popen') as launch, patch.object(g12.os, 'killpg') as kill:
                    process = launch.return_value; process.pid = 987654; process.wait.return_value = 1
                    if mode == 'interrupt':
                        process.wait.side_effect = [KeyboardInterrupt(), -9]
                        with self.assertRaises(KeyboardInterrupt):
                            g12.run(args)
                        kill.assert_called_once_with(987654, g12.signal.SIGKILL)
                        self.assertFalse(list(args.output.glob('checkpoint-*.json')))
                        continue
                    self.assertEqual(g12.run(args), 0)
                    self.assertEqual(launch.call_count, 0 if mode=='deadline' else 2)
                    summary = json.loads((args.output/'summary-0001.json').read_text())
                    self.assertFalse(summary['complete'])
                    self.assertIsNone(summary['selected_variant'])
                    self.assertFalse(summary['manufacturing_authorized'])
                    self.assertFalse(summary['assembled_stiffness_qualified'])
                    self.assertTrue(all(r['size_mm']==2 for r in summary['records']))


if __name__ == '__main__':
    unittest.main()
