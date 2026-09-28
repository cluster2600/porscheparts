"""G13 exact-input, thread-policy and no-cherry-picking reference checks."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/fourvalve'))
try:
    import g13_reference as g13
except ImportError:
    g13 = None


@unittest.skipIf(g13 is None, 'optional numerical runtime unavailable')
class G13ReferenceChecks(unittest.TestCase):
    def test_exact_sources_and_inputs_reject_changed_deck(self):
        for name, expected in g13.SOURCES.items():
            self.assertEqual(g13.sha(g13.g8.REPO/name), expected)
        self.assertEqual(g13.INPUTS['minus_z.inp'], 'd5e2d625ec1f65f56e9a0f8896a43505ccec1a474f887dfd2400dc96bb09dc08')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pins = {}
            for name in g13.INPUTS:
                data = '*HEADING\nsame geometry\n*STEP\n'+name
                (root/name).write_text(data)
                pins[name] = hashlib.sha256(data.encode()).hexdigest()
            with patch.object(g13, 'INPUTS', pins):
                self.assertEqual(set(g13.inputs(root)), {'x', 'minus_z'})
                (root/'minus_z.inp').write_text('changed')
                with self.assertRaisesRegex(ValueError, 'input fingerprint'):
                    g13.inputs(root)

    def test_explicit_threads_are_observed_and_timeout_kills_group(self):
        for threads in (1, 4):
            with tempfile.TemporaryDirectory() as folder:
                case = Path(folder)
                def started(*args, **kwargs):
                    kwargs['stdout'].write(f'CalculiX Version 2.21\nUsing up to {threads} cpu(s) for spooles.\nJob finished\n')
                    kwargs['stdout'].flush()
                    return Mock(pid=12345, returncode=0, **{'poll.return_value': 0, 'wait.return_value': 0})
                with patch.object(g13.subprocess, 'Popen', side_effect=started) as launch, \
                        patch.object(g13.os, 'killpg') as kill:
                    result = g13.ccx(case, 'minus_z', threads, 2)
                    env = launch.call_args.kwargs['env']
                    self.assertTrue(all(env[k] == str(threads) for k in g13.THREAD_KEYS))
                    self.assertTrue(launch.call_args.kwargs['start_new_session'])
                    self.assertEqual(result['observed_cpu_counts'], [threads])
                    kill.assert_called_once_with(12345, g13.signal.SIGKILL)
        for exception in (subprocess.TimeoutExpired('ccx', 1), KeyboardInterrupt()):
            with tempfile.TemporaryDirectory() as folder, \
                    patch.object(g13.subprocess, 'Popen') as launch, patch.object(g13.os, 'killpg') as kill:
                p = launch.return_value
                p.pid, p.returncode = 12345, None
                p.poll.return_value = None
                p.wait.side_effect = [exception, -9]
                with self.assertRaises(type(exception)):
                    g13.ccx(Path(folder), 'minus_z', 1, 1)
                kill.assert_called_once_with(12345, g13.signal.SIGKILL)

    def test_all_repeats_required_and_no_failed_serial_selection(self):
        rows = [dict(id=i, direction=d, threads=t, compared=True, passed=True) for i,d,t in g13.PLAN]
        self.assertEqual(g13.assess(rows)['outcome'], 'inconsistency_not_reproduced')
        rows[0]['passed'] = False
        self.assertTrue(g13.assess(rows)['serial_runtime_candidate'])
        for serial_index in (2, 3, 4):
            bad = [dict(r) for r in rows]; bad[serial_index]['passed'] = False
            self.assertFalse(g13.assess(bad)['serial_runtime_candidate'])
        self.assertFalse(g13.assess(rows[:-1])['complete'])
        duplicate = rows[:4]+[rows[3]]
        self.assertFalse(g13.assess(duplicate)['complete'])
        rows[0]['compared'] = False
        self.assertFalse(g13.assess(rows)['serial_runtime_candidate'])
        self.assertFalse(g13.assess(rows)['causal_SPOOLES_race_proven'])

    def test_deadline_and_unchanged_crosscheck_gates(self):
        with self.assertRaises(TimeoutError):
            g13.remaining(SimpleNamespace(deadline=0), 900)
        with tempfile.TemporaryDirectory() as folder:
            case = Path(folder); (case/'x.inp').write_text('fixture')
            points, loads, support = {1: g13.np.zeros(3)}, {(1,1): 1.}, set()
            reference = {1: (1.,0.,0.)}; matrix = g13.np.eye(3); rhs = g13.np.array([1.,0.,0.])
            mapping = [(1,1),(1,2),(1,3)]
            with patch.object(g13.g9, 'deck', return_value=(points,loads,support)), \
                    patch.object(g13.g9, 'mechanics', return_value=(reference, {'equilibrium_passed': True})):
                self.assertTrue(g13.compare(case,'x',matrix,mapping,dict(u=rhs,passed=True),rhs,points,support)['passed'])
                self.assertFalse(g13.compare(case,'x',matrix,mapping,dict(u=rhs*1.001,passed=True),rhs,points,support)['passed'])
                self.assertFalse(g13.compare(case,'x',matrix,mapping,dict(u=rhs,passed=False),rhs,points,support)['passed'])
            with patch.object(g13.g9, 'deck', return_value=(points,loads,support)), \
                    patch.object(g13.g9, 'mechanics', return_value=(reference, {'equilibrium_passed': False})):
                self.assertFalse(g13.compare(case,'x',matrix,mapping,dict(u=rhs,passed=True),rhs,points,support)['passed'])

    def test_mock_full_run_retains_all_five_and_original_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root/'inputs'; source.mkdir()
            header = '*NODE\n1,0,0,1\n2,0,0,0\n*NSET,NSET=SUPPORT\n2\n*STEP\n*STATIC\n*BOUNDARY\nSUPPORT,1,3\n*CLOAD\n'
            texts = {'x': header+'1,1,1\n', 'minus_z': header+'1,3,-1\n'}
            for name in g13.INPUTS:
                (source/name).write_text(texts[name[:-4]] if name.endswith('.inp') else 'original failed field')
            binary = root/'ccx'; binary.write_text('fixture runtime')
            def solve(case, name, threads, timeout):
                for ext in (('.sti','.dof','.mas') if name == 'matrix' else ('.dat',)):
                    (case/(name+ext)).write_text('fixture output')
                (case/(name+'.log')).write_text('fixture log')
                return dict(threads=threads, seconds=0.)
            def mechanics(case, name, points, loads, support):
                vector = (1.,0.,0.) if name == 'x' else (0.,0.,-1.)
                bad = name == 'minus_z' and case.name in ('original-rejected','t4-z-r1')
                return {1: vector, 2: (0.,0.,0.)}, {'equilibrium_passed': not bad}
            args = SimpleNamespace(input=source, output=root/'new', deadline=time.time()+4000, case_timeout=5, ccx_binary=binary)
            with patch.object(g13.sys, 'platform', 'linux'), patch.object(g13, 'inputs', return_value=texts), \
                    patch.object(g13, 'CCX_BINARY_SHA', g13.sha(binary)), \
                    patch.object(g13.shutil, 'which', return_value=str(binary)), \
                    patch.object(g13, 'ccx', side_effect=solve) as direct, \
                    patch.object(g13.bench, 'read_matrix', return_value=(g13.np.eye(3),[(1,1),(1,2),(1,3)])), \
                    patch.object(g13.bench, 'solve', side_effect=lambda matrix,rhs,backend,max_seconds:(rhs.copy(),{'info':0})), \
                    patch.object(g13.g9, 'mechanics', side_effect=mechanics):
                self.assertEqual(g13.run(args), 0)
            summary = json.loads((args.output/'summary-0001.json').read_text())
            self.assertEqual(len(summary['rows']), 5)
            self.assertTrue(summary['serial_runtime_candidate'])
            self.assertTrue(summary['original_failure_preserved'])
            self.assertFalse(summary['rows'][0]['passed'])
            self.assertEqual([c.args[2] for c in direct.call_args_list], [4,1,4,1,1,1])
            self.assertEqual(len(list(args.output.glob('*/case.json'))), 5)
            self.assertFalse(list(args.output.rglob('result.json')))
            self.assertLess((args.output/'summary-0001.json').stat().st_size,40000)
            prior = json.loads((args.output/'matrix/minus_z-reference.json').read_text())
            self.assertFalse(prior['original_rejected_comparison']['passed'])
            identity = json.loads((args.output/'identity.json').read_text())
            self.assertEqual(identity['real_ccx_binary_sha256'], g13.sha(binary))


if __name__ == '__main__':
    unittest.main()
