"""Stdlib-only AST/mocked lifecycle cases adapted from the volume002 harness."""
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
from unittest.mock import Mock

SOURCE = Path(__file__).with_name('run_readback.py')
MAIN = next(n for n in ast.parse(SOURCE.read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == 'main')


class ReadbackRunnerGuards(unittest.TestCase):
    def context(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
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


if __name__ == '__main__':
    unittest.main()
