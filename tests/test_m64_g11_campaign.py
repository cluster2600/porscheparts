"""G11 changed journal widths, frozen loads, strict gates and bounded resume."""
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
    import g11_campaign as g11
except ImportError:
    g11 = None


def result(value=.035):
    return {'complete': True, 'cases': [
        {'direction': d, 'numerical_crosscheck_passed': True, 'mechanics': {
            'equilibrium_passed': True,
            'journal_weighted_displacement_mm': {s: [value, 0., 0.] for s in ('intake', 'exhaust')},
            'von_Mises_p95_MPa': 40.}}
        for d in ('x', 'minus_z')]}


@unittest.skipIf(g11 is None, 'optional numerical runtime unavailable')
class CampaignChecks(unittest.TestCase):
    def test_surface_width_and_frozen_reactions(self):
        np = g11.np
        for width in (10., 11., 12.):
            corners = np.array([[1., -width/2, 0.], [0., width/2, 1.], [-1., 0., 0.]])
            self.assertTrue(g11.is_journal(corners, 'Cylinder', [0., 0., 0.], 1., (-width/2, width/2)))
            self.assertFalse(g11.is_journal(corners, 'Plane', [0., 0., 0.], 1., (-width/2, width/2)))
            corners[0, 1] -= .01
            self.assertFalse(g11.is_journal(corners, 'Cylinder', [0., 0., 0.], 1., (-width/2, width/2)))
        baseline = json.loads(g11.g8.BASELINE.read_text())
        outer = g11.forces(baseline, 'carrier_base_p')
        central = g11.forces(baseline, 'central_diaphragm')
        self.assertAlmostEqual(outer['intake'], 4370.41776865, places=5)
        self.assertAlmostEqual(outer['exhaust'], 3566.85521520, places=5)
        self.assertAlmostEqual(central['intake'], 6881.35243458, places=5)
        self.assertAlmostEqual(central['exhaust'], 6702.48441130, places=5)
        p = baseline['values']
        self.assertEqual(g11.journal_interval(p, 'intake', 'central_diaphragm', 12), (-6, 6))
        lo, hi = g11.journal_interval(p, 'intake', 'carrier_base_p', 8)
        self.assertAlmostEqual(hi-lo, 8)
        self.assertAlmostEqual((lo+hi)/2, 38.59375)

    def test_vector_gate_is_not_norm_only_or_manufacturing_release(self):
        self.assertTrue(g11.assessment(result(), result())['accepted'])
        self.assertTrue(g11.assessment(result(.040), result(.040))['accepted'])
        self.assertFalse(g11.assessment(result(.04001), result(.04001))['accepted'])
        medium, fine = result(), result()
        fine['cases'][0]['mechanics']['journal_weighted_displacement_mm']['intake'] = [.035, .0005, 0.]
        self.assertFalse(g11.assessment(medium, fine)['accepted'])
        fine = result()
        fine['cases'][1]['mechanics']['von_Mises_p95_MPa'] = 45.
        self.assertFalse(g11.assessment(medium, fine)['accepted'])
        fine = result()
        fine['cases'][0]['numerical_crosscheck_passed'] = False
        self.assertFalse(g11.assessment(medium, fine)['accepted'])
        fine = result()
        fine['cases'].pop()
        self.assertFalse(g11.assessment(medium, fine)['accepted'])

    def test_checkpoint_hash_and_source_are_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root/'x.dat'
            artifact.write_text('unchanged output')
            receipt = root/'result.json'
            row = {'cad_receipt_sha256': 'cad', 'source_sha256': g11.source_hashes(),
                   'hashes': {'x.dat': g11.g8.sha256(artifact)}, 'id': 'centre_w10',
                   'component': 'central_diaphragm', 'step_sha256': 'step', 'mesh': {'size_mm': 2.},
                   'backend': 'cpu', 'cases': []}
            variant = {k: row[k] for k in ('id', 'component', 'step_sha256')}
            g11.publish(receipt, row)
            fingerprint = g11.g8.sha256(receipt)
            self.assertEqual(g11.verify_result(receipt, fingerprint, 'cad', variant, 2., 'cpu'), row)
            with self.assertRaisesRegex(ValueError, 'binding changed'):
                g11.verify_result(receipt, fingerprint, 'cad', variant, 1.5, 'cpu')
            artifact.write_text('tampered output')
            with self.assertRaisesRegex(ValueError, 'artifact changed'):
                g11.verify_result(receipt, fingerprint, 'cad', variant, 2., 'cpu')
            with self.assertRaisesRegex(ValueError, 'fingerprint mismatch'):
                g11.verify_result(receipt, '0'*64, 'cad', variant, 2., 'cpu')
            with self.assertRaises(FileExistsError):
                g11.publish(receipt, row)

    def test_rejected_cad_and_insufficient_time_never_launch_solver(self):
        for accepted in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                cad = root/'cad.json'
                cad.write_text('{}')
                variants = [{'id': i, 'cad_accepted': accepted, 'component': 'central_diaphragm'}
                            for i in ('centre_w10', 'centre_w12', 'centre_w11')]
                args = SimpleNamespace(cad=cad, output=root/'output', backend='cpu', deadline=time.time(),
                                       case_timeout=10, reserve_seconds=1)
                with patch.object(g11, 'inputs', return_value=({'variants': variants}, {})), patch.object(g11.subprocess, 'Popen') as launch:
                    g11.run(args)
                    launch.assert_not_called()
                summary = json.loads((args.output/'summary-0001.json').read_text())
                self.assertFalse(summary['manufacturing_authorized'])
                self.assertFalse(summary['engine_start_authorized'])
                self.assertFalse(summary['both_components_below_0p040_mm_and_mesh_stable'])
                self.assertEqual(summary['screening_attempted'], not accepted)
                self.assertFalse(summary['screening_complete'])
                self.assertFalse(summary['complete'])

    def test_controller_interruption_reaps_worker_process_group(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cad = root/'cad.json'
            cad.write_text('{}')
            variants = [{'id': i, 'cad_accepted': i == 'centre_w10', 'component': 'central_diaphragm'}
                        for i in ('centre_w10', 'centre_w12', 'centre_w11')]
            args = SimpleNamespace(cad=cad, output=root/'output', backend='cpu', deadline=time.time()+100,
                                   case_timeout=10, reserve_seconds=1)
            with patch.object(g11, 'inputs', return_value=({'variants': variants}, {})), \
                    patch.object(g11.subprocess, 'Popen') as launch, patch.object(g11.os, 'killpg') as kill:
                process = launch.return_value
                process.pid = 987654
                process.wait.side_effect = [KeyboardInterrupt(), -9]
                with self.assertRaises(KeyboardInterrupt):
                    g11.run(args)
                kill.assert_called_once_with(987654, g11.signal.SIGKILL)
                self.assertEqual(process.wait.call_count, 2)
                self.assertFalse(list(args.output.glob('checkpoint-*.json')))


if __name__ == '__main__':
    unittest.main()
