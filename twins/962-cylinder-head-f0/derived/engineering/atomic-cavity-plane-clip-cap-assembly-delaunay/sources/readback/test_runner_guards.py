"""Stdlib-only AST/mocked lifecycle and output-limit checks; no real processes."""
import ast
import hashlib
import json
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().with_name('run_readback.py')
SOURCE_SHA = '4fb37080e1f3847b8b1d14d5df467799d8e9f7bf81b0a09170e5850857de3943'
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA:
    raise ValueError('Frozen assembled readback runner changed before AST extraction')
MAIN = next(n for n in ast.parse(SOURCE.read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == 'main')


class ReadbackRunnerGuards(unittest.TestCase):
    def context(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        for name in ['reader.py', 'run_readback.py', 'python.bin']:
            (root/name).write_text('frozen mock input '+name+'\n')
        sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        contract = dict(native_python=str(root/'python.bin'), reader_sha256=sha(root/'reader.py'),
            runner_sha256=sha(root/'run_readback.py'),
            runtime=dict(python_executable_sha256=sha(root/'python.bin')))
        (root/'frozen-contract.json').write_text(json.dumps(contract))
        parser = Mock(); parser.parse_args.return_value = SimpleNamespace(
            contract_sha256=sha(root/'frozen-contract.json'))
        state = dict(running=True, returncode=None)
        process = Mock(pid=1729, returncode=None)
        process.poll.side_effect = lambda: None if state['running'] else state['returncode']
        def wait(timeout=None):
            if state['running']: raise subprocess.TimeoutExpired('mock-reader', timeout)
            return state['returncode']
        process.wait.side_effect = wait
        def killpg(pid, signum):
            self.assertEqual((pid, signum), (1729, signal.SIGKILL))
            state.update(running=False, returncode=-9); process.returncode = -9
        timer = Mock(); previous = object(); registrations = []
        register = Mock(side_effect=lambda sig, handler:registrations.append((sig, handler)))
        def finished(*args, **kwargs):
            state.update(running=False, returncode=0); process.returncode = 0
            (root/'readback-report.json').write_text('{}\n')
            return SimpleNamespace(stdout='1\n')
        sp = SimpleNamespace(Popen=Mock(return_value=process), run=Mock(side_effect=finished),
            STDOUT=subprocess.STDOUT, TimeoutExpired=subprocess.TimeoutExpired,
            SubprocessError=subprocess.SubprocessError)
        ns = dict(Path=Path, OUT=root, __file__=str(root/'run_readback.py'), __doc__='mock',
            argparse=SimpleNamespace(ArgumentParser=Mock(return_value=parser)),
            sha=sha, re=re, json=json, time=time, subprocess=sp,
            os=SimpleNamespace(killpg=Mock(side_effect=killpg)),
            signal=SimpleNamespace(SIGTERM=signal.SIGTERM, SIGKILL=signal.SIGKILL,
                getsignal=Mock(return_value=previous), signal=register),
            threading=SimpleNamespace(Lock=threading.Lock, Timer=Mock(return_value=timer)))
        exec(compile(ast.Module(body=[MAIN], type_ignores=[]), str(SOURCE), 'exec'), ns)
        return SimpleNamespace(root=root, ns=ns, main=ns['main'], state=state, process=process,
            timer=timer, sp=sp, previous=previous, registrations=registrations)

    def restored(self, c):
        self.assertEqual(len(c.registrations), 2)
        self.assertEqual(c.registrations[0][0], signal.SIGTERM)
        self.assertEqual(c.registrations[-1][0], signal.SIGTERM)
        self.assertIs(c.registrations[-1][1], c.previous)

    def test_SIGTERM_during_Popen_return_keeps_assigned_child_owned(self):
        c = self.context(); returned = []
        def popen(*args, **kwargs):
            c.registrations[0][1](signal.SIGTERM, None)
            returned.append(True); return c.process
        c.sp.Popen.side_effect = popen
        self.assertEqual(c.main(), 2); self.assertEqual(returned, [True])
        c.ns['os'].killpg.assert_called_once(); c.process.wait.assert_called_once_with()
        self.assertEqual(json.loads((c.root/'execution-receipt.json').read_text())['stop_reason'],
                         'controller_SIGTERM')
        self.restored(c)

    def test_SIGTERM_during_monitor_kills_reaps_and_restores(self):
        c = self.context()
        def observe(*args, **kwargs):
            c.registrations[0][1](signal.SIGTERM, None)
            return SimpleNamespace(stdout='1\n')
        c.sp.run.side_effect = observe
        self.assertEqual(c.main(), 2); c.ns['os'].killpg.assert_called_once()
        self.assertFalse(c.state['running']); self.restored(c)

    def test_Popen_refusal_restores_and_does_not_kill_unowned_process(self):
        c = self.context(); c.sp.Popen.side_effect = OSError('mock Popen refusal')
        with self.assertRaisesRegex(OSError, 'mock Popen refusal'):c.main()
        c.ns['os'].killpg.assert_not_called(); c.process.wait.assert_not_called()
        self.restored(c)

    def test_timer_start_refusal_still_kills_reaps_and_restores(self):
        c = self.context(); c.timer.start.side_effect = RuntimeError('mock Timer refusal')
        with self.assertRaisesRegex(RuntimeError, 'mock Timer refusal'):c.main()
        c.ns['os'].killpg.assert_called_once(); c.process.wait.assert_called_once_with()
        c.timer.cancel.assert_called_once(); self.restored(c)

    def test_monitor_refusal_stops_child_without_success(self):
        c = self.context(); c.sp.run.side_effect = OSError('mock observation refusal')
        self.assertEqual(c.main(), 2); c.ns['os'].killpg.assert_called_once()
        self.assertEqual(json.loads((c.root/'execution-receipt.json').read_text())['stop_reason'],
                         'RSS_observation_failed')
        self.restored(c)

    def test_wait_refusal_still_restores_handler(self):
        c = self.context(); c.timer.start.side_effect = RuntimeError('mock Timer refusal')
        c.process.wait.side_effect = RuntimeError('mock wait refusal')
        with self.assertRaisesRegex(RuntimeError, 'mock wait refusal'):c.main()
        c.ns['os'].killpg.assert_called_once(); self.restored(c)

    def test_late_SIGTERM_marks_interruption_without_signaling_reaped_PID(self):
        c = self.context()
        def wait(timeout=None):
            self.assertFalse(c.state['running'])
            c.registrations[0][1](signal.SIGTERM, None); return 0
        c.process.wait.side_effect = wait
        self.assertEqual(c.main(), 2); c.ns['os'].killpg.assert_not_called()
        self.assertEqual(json.loads((c.root/'execution-receipt.json').read_text())['stop_reason'],
                         'controller_SIGTERM')
        self.restored(c)

    def test_normal_reader_completion_reaps_restores_and_does_not_kill(self):
        c = self.context(); self.assertEqual(c.main(), 0)
        c.ns['os'].killpg.assert_not_called(); c.process.wait.assert_called_once_with()
        c.timer.cancel.assert_called_once(); self.restored(c)


    def test_Popen_creation_time_is_subtracted_from_timer_budget(self):
        c = self.context(); clock = [100.]
        c.ns['time'] = SimpleNamespace(monotonic=lambda:clock[0])
        def popen(*args, **kwargs):
            clock[0] += 17.; return c.process
        c.sp.Popen.side_effect = popen
        self.assertEqual(c.main(), 0)
        self.assertEqual(c.ns['threading'].Timer.call_args.args[0], 103.)
        report = json.loads((c.root/'execution-receipt.json').read_text())
        self.assertEqual(report['wall_seconds'], 17.)
        c.ns['os'].killpg.assert_not_called(); c.process.wait.assert_called_once_with()
        self.restored(c)

    def test_late_valid_RC0_without_timer_callback_cannot_pass(self):
        c = self.context(); clock = [100.]
        c.ns['time'] = SimpleNamespace(monotonic=lambda:clock[0])
        def popen(*args, **kwargs):
            clock[0] += 121.
            c.state.update(running=False, returncode=0); c.process.returncode = 0
            (c.root/'readback-report.json').write_text('{}\n')
            return c.process
        c.sp.Popen.side_effect = popen
        self.assertEqual(c.main(), 2)
        self.assertEqual(c.ns['threading'].Timer.call_args.args[0], 0.)
        report = json.loads((c.root/'execution-receipt.json').read_text())
        self.assertEqual(report['wall_seconds'], 121.)
        self.assertEqual(report['returncode'], 0)
        self.assertEqual(report['stop_reason'], 'readback_deadline')
        c.timer.start.assert_called_once_with()  # Mock never invokes the callback.
        c.ns['os'].killpg.assert_not_called(); c.process.wait.assert_called_once_with()
        self.restored(c)



    def test_output_limit_while_running_kills_reaps_and_restores(self):
        c = self.context(); c.sp.run.side_effect = lambda *a, **k:SimpleNamespace(stdout='1\n')
        original = Path.stat
        def metadata(path, *args, **kwargs):
            result = original(path, *args, **kwargs)
            return SimpleNamespace(st_size=1024**3, st_mode=result.st_mode) if path == c.root/'native.log' else result
        with patch.object(Path, 'stat', metadata):self.assertEqual(c.main(), 2)
        c.ns['os'].killpg.assert_called_once(); self.assertFalse(c.state['running'])
        self.assertEqual(json.loads((c.root/'execution-receipt.json').read_text())['stop_reason'], 'sampled_output_disk_stop')
        self.restored(c)

    def test_already_exited_output_over_limit_is_not_credited(self):
        c = self.context(); original = Path.stat
        def metadata(path, *args, **kwargs):
            result = original(path, *args, **kwargs)
            return SimpleNamespace(st_size=1024**3, st_mode=result.st_mode) if path == c.root/'native.log' else result
        with patch.object(Path, 'stat', metadata):self.assertEqual(c.main(), 2)
        c.ns['os'].killpg.assert_not_called(); c.process.wait.assert_called_once_with()
        self.assertEqual(json.loads((c.root/'execution-receipt.json').read_text())['stop_reason'], 'sampled_output_disk_stop')
        self.restored(c)

    def test_declared_eight_GiB_RSS_limit_stops_owned_child(self):
        c = self.context(); c.sp.run.side_effect = lambda *a, **k:SimpleNamespace(stdout=str(8*1024**2)+'\n')
        self.assertEqual(c.main(), 2); c.ns['os'].killpg.assert_called_once()
        report = json.loads((c.root/'execution-receipt.json').read_text())
        self.assertEqual(report['sampled_RSS_stop_bytes'], 8*1024**3)
        self.assertEqual(report['stop_reason'], 'sampled_RSS_stop'); self.restored(c)

if __name__ == '__main__':
    unittest.main()
