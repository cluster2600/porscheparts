"""Small preparation guards and exact deck reparse check; no real mesh or solve."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import fine_deck_prepare as f


class FineDeckPreparation(unittest.TestCase):
    def test_medium_hash_tamper_stops_before_any_output_or_process(self):
        with tempfile.TemporaryDirectory() as d, patch.object(f, 'SUMMARY_SHA', '0'*64), \
                patch.object(f.subprocess, 'Popen') as spawn:
            output = Path(d)/'never-created'
            with self.assertRaisesRegex(ValueError, 'medium summary changed'):
                f.control(output)
            self.assertFalse(output.exists()); spawn.assert_not_called()

    def test_worker_writes_two_exact_decks_without_solver(self):
        points = {n:(-float(n) if n < 6 else float(n), 0., 0. if n in (1, 2) else 12.) for n in range(1, 11)}
        elements = [(1, list(range(1, 11)))]; support = [1, 2]
        weights = {'intake':{3:.25, 4:.75}, 'exhaust':{9:1.}}
        forces = {'intake':1234.56789012345, 'exhaust':987.65432109876}
        baseline = {'values':{'carrier_face_height':0.}}
        variant = dict(step_path=Path('fixture.step'), step_sha256='fixture', component='central_diaphragm')
        proof = {'fixture':'not physical evidence'}
        mesh = dict(size_mm=1., nodes=10, elements=1, fixed_nodes=2, nominal_journal_width_mm=11)
        def fake_mesh(step, size, values, selected, output):
            (output/'mesh.msh').write_text('test fixture only')
            return points, elements, support, weights, mesh
        with tempfile.TemporaryDirectory() as d:
            output = Path(d); f.c.g11.publish(output/'identity.json', proof)
            with patch.object(f, 'inputs', return_value=(baseline, variant, proof)), \
                    patch.dict(os.environ, f.c.THREAD_ENV), patch.object(f.sys, 'platform', 'darwin'), \
                    patch.object(f.c.g11, 'mesh', side_effect=fake_mesh), \
                    patch.object(f.c.g11, 'forces', return_value=forces), \
                    patch.object(f.c.g8, 'solve', side_effect=AssertionError('no direct solve')) as direct, \
                    patch.object(f.c.g9.bench, 'solve', side_effect=AssertionError('no CG solve')) as cg, \
                    patch.object(f.m, 'ccx', side_effect=AssertionError('no CCX')) as ccx, \
                    patch.object(f.subprocess, 'Popen', side_effect=AssertionError('no child solver')) as spawn:
                self.assertEqual(f.worker(output), 0)
                direct.assert_not_called(); cg.assert_not_called(); ccx.assert_not_called(); spawn.assert_not_called()
            receipt = json.loads((output/'receipt.json').read_text())
            self.assertTrue(receipt['complete']); self.assertFalse(receipt['FEA_executed'])
            self.assertFalse(receipt['remote_Linux_job_operational'])
            self.assertEqual(receipt['kinematic_free_dofs'], 24)
            self.assertEqual(len(receipt['deck_checks']['cases']), 2)
            with self.assertRaises(FileExistsError):
                f.m.write_deck(output, points, elements, support, weights, forces, [1, 0, 0], 'x')
            p = output/'minus_z.inp'; p.write_text(p.read_text().replace(',3,-', ',3,'))
            with self.assertRaisesRegex(ValueError, 'load-direction mismatch'):
                f.check_decks(output, mesh, support, weights, forces, 0.)

    def test_low_disk_and_combined_memory_guard_preserve_peer(self):
        with tempfile.TemporaryDirectory() as d, patch.object(f, 'inputs', return_value=({}, {}, {})), \
                patch.object(f.shutil, 'disk_usage', return_value=SimpleNamespace(free=f.FREE_DISK-1)), \
                patch.object(f.subprocess, 'Popen') as spawn:
            with self.assertRaisesRegex(ValueError, 'free disk'):
                f.control(Path(d)/'never-created')
            spawn.assert_not_called()
        with tempfile.TemporaryDirectory() as d:
            process = Mock(pid=123456, returncode=-15); process.poll.return_value=None
            rows = f'123456 123456 {10*1024**2}\n{f.PEER_PGID} {f.PEER_PGID} {20*1024**2}\n'
            with patch.object(f, 'inputs', return_value=({}, {}, {})), \
                    patch.object(f.shutil, 'disk_usage', return_value=SimpleNamespace(free=40*1024**3)), \
                    patch.object(f.subprocess, 'Popen', return_value=process), \
                    patch.object(f.subprocess, 'check_output', return_value=rows), patch.object(f.os, 'killpg') as kill:
                output = Path(d)/'prepared'
                self.assertEqual(f.control(output), 2)
                summary = json.loads((output/'summary.json').read_text())
                self.assertEqual(summary['error'], '28GiB_combined_RSS_limit')
                self.assertTrue(summary['worker_reaped']); self.assertFalse(summary['complete'])
                kill.assert_called_once_with(123456, f.signal.SIGTERM)
                self.assertEqual(process.wait.call_count, 2)


if __name__ == '__main__':
    unittest.main()
