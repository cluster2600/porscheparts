"""Exercise extracted stdlib-only guards; never import the scientific worker."""
import ast
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

SOURCE = Path(__file__).with_name('mesh_atomic_volume.py')
TREE = ast.parse(SOURCE.read_text())
RUN = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
WORKER = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == 'worker')
COUNT_GUARD = next(n for n in ast.walk(WORKER) if isinstance(n, ast.If)
    and any(isinstance(c, ast.Constant) and c.value ==
            'Every metric distribution must cover every actual tetrahedron' for c in ast.walk(n)))


def extracted_run(namespace):
    exec(compile(ast.Module(body=[RUN], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace['run']


class VolumeGuards(unittest.TestCase):
    def context(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        script = root/'source.py'; script.write_text('frozen mock source\n')
        admission = root/'admission.json'; admission.write_text('{}\n')
        state = dict(running=True, returncode=None)
        process = Mock(pid=1729)
        process.poll.side_effect = lambda: None if state['running'] else state['returncode']
        def wait(timeout=None):
            if state['running']:
                raise subprocess.TimeoutExpired('mock-child', timeout)
            return state['returncode']
        process.wait.side_effect = wait
        def killpg(pid, signum):
            self.assertEqual((pid, signum), (1729, signal.SIGKILL))
            state.update(running=False, returncode=-9); process.returncode = -9
        timer = Mock()
        previous = object(); registrations = []
        register = Mock(side_effect=lambda sig, handler: registrations.append((sig, handler)))
        def finished(*args, **kwargs):
            state.update(running=False, returncode=2); process.returncode = 2
            return SimpleNamespace(stdout='1\n')
        sp = SimpleNamespace(Popen=Mock(return_value=process), run=Mock(side_effect=finished),
            STDOUT=subprocess.STDOUT, TimeoutExpired=subprocess.TimeoutExpired,
            SubprocessError=subprocess.SubprocessError)
        namespace = dict(Path=Path, ROOT=root, OUTPUT=root/'output', __file__=str(script),
            sys=sys, json=json, time=time, OPTIONS={}, DEADLINE=300, RSS_STOP=8*1024**3,
            require_admission=Mock(return_value={}), new_output=lambda p:p.mkdir(),
            source_files=lambda:[script], sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest(),
            save=lambda p,v:p.write_text(json.dumps(v)), matching_mesh=lambda *_:False,
            os=SimpleNamespace(environ={}, killpg=Mock(side_effect=killpg)),
            signal=SimpleNamespace(SIGTERM=signal.SIGTERM, SIGKILL=signal.SIGKILL,
                getsignal=Mock(return_value=previous), signal=register),
            threading=SimpleNamespace(Lock=threading.Lock, Timer=Mock(return_value=timer)),
            subprocess=sp)
        args = SimpleNamespace(output=root/'output', admission=admission, admission_sha256='a'*64)
        return SimpleNamespace(root=root, namespace=namespace, run=extracted_run(namespace),
            args=args, state=state, process=process, timer=timer, sp=sp,
            previous=previous, registrations=registrations)

    def restored(self, c):
        self.assertEqual(c.registrations[0][0], signal.SIGTERM)
        self.assertEqual(c.registrations[-1][0], signal.SIGTERM)
        self.assertIs(c.registrations[-1][1], c.previous)
        self.assertEqual(len(c.registrations), 2)

    def test_all_four_metric_counts_must_match_actual_tetrahedra(self):
        fn = ast.FunctionDef(name='check', args=ast.arguments(posonlyargs=[], args=[
            ast.arg(arg='quality'), ast.arg(arg='cells')], vararg=None, kwonlyargs=[], kw_defaults=[],
            kwarg=None, defaults=[]), body=[COUNT_GUARD], decorator_list=[])
        ns = {}; exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])),
            str(SOURCE), 'exec'), ns)
        names = ['minimum_jacobian', 'native_volume_mm3', 'minimum_SICN',
                 'independent_signed_volume_mm3']
        rows = {name:dict(count=3) for name in names}
        ns['check'](rows, [None]*3)
        for name in names:
            for bad in [2, 4, 3.0, True, None]:
                with self.subTest(metric=name, count=bad):
                    changed = {k:dict(v) for k,v in rows.items()}; changed[name]['count'] = bad
                    with self.assertRaisesRegex(ValueError, 'every actual tetrahedron'):
                        ns['check'](changed, [None]*3)

    def test_SIGTERM_during_Popen_return_does_not_lose_owned_child(self):
        c = self.context(); returned = []
        def popen(*args, **kwargs):
            c.registrations[0][1](signal.SIGTERM, None)
            self.assertTrue(c.state['running'])
            returned.append(True)
            return c.process
        c.sp.Popen.side_effect = popen
        self.assertEqual(c.run(c.args), 2)
        self.assertEqual(returned, [True]); c.namespace['os'].killpg.assert_called_once()
        c.process.wait.assert_called_once_with(); c.timer.cancel.assert_called_once()
        self.assertEqual(json.loads((c.args.output/'receipt.json').read_text())['stop_reason'],
                         'controller_SIGTERM')
        self.restored(c)

    def test_SIGTERM_during_monitor_kills_reaps_and_restores(self):
        c = self.context()
        def observe(*args, **kwargs):
            c.registrations[0][1](signal.SIGTERM, None)
            return SimpleNamespace(stdout='1\n')
        c.sp.run.side_effect = observe
        self.assertEqual(c.run(c.args), 2)
        c.namespace['os'].killpg.assert_called_once(); self.assertFalse(c.state['running'])
        self.assertEqual(c.process.wait.call_args_list[-1].kwargs, {})
        self.restored(c)

    def test_Popen_error_restores_without_killing_unowned_process(self):
        c = self.context(); c.sp.Popen.side_effect = OSError('mock Popen refusal')
        with self.assertRaisesRegex(OSError, 'mock Popen refusal'): c.run(c.args)
        c.namespace['os'].killpg.assert_not_called(); c.process.wait.assert_not_called()
        self.restored(c)

    def test_watchdog_start_error_still_kills_reaps_and_restores(self):
        c = self.context(); c.timer.start.side_effect = RuntimeError('mock Timer refusal')
        with self.assertRaisesRegex(RuntimeError, 'mock Timer refusal'): c.run(c.args)
        c.namespace['os'].killpg.assert_called_once(); c.process.wait.assert_called_once_with()
        c.timer.cancel.assert_called_once(); self.restored(c)

    def test_monitor_error_stops_owned_child_and_cannot_pass(self):
        c = self.context(); c.sp.run.side_effect = OSError('mock observation refusal')
        self.assertEqual(c.run(c.args), 2); c.namespace['os'].killpg.assert_called_once()
        receipt = json.loads((c.args.output/'receipt.json').read_text())
        self.assertEqual(receipt['stop_reason'], 'RSS_observation_failed')
        self.assertFalse(receipt['geometric_volume_gate_passed']); self.restored(c)

    def test_cleanup_wait_error_still_restores_handler(self):
        c = self.context(); c.timer.start.side_effect = RuntimeError('mock Timer refusal')
        c.process.wait.side_effect = RuntimeError('mock wait refusal')
        with self.assertRaisesRegex(RuntimeError, 'mock wait refusal'): c.run(c.args)
        c.namespace['os'].killpg.assert_called_once(); self.restored(c)

    def test_late_SIGTERM_during_reap_marks_failure_without_signaling_reaped_PID(self):
        c = self.context()
        def wait(timeout=None):
            self.assertFalse(c.state['running'])
            c.registrations[0][1](signal.SIGTERM, None)
            return 2
        c.process.wait.side_effect = wait
        self.assertEqual(c.run(c.args), 2); c.namespace['os'].killpg.assert_not_called()
        self.assertEqual(json.loads((c.args.output/'receipt.json').read_text())['stop_reason'],
                         'controller_SIGTERM')
        self.restored(c)

    def test_input_options_runtime_and_output_constants_are_unchanged(self):
        old = SOURCE.parent.parent/'atomic-cavity-volume-prep-001/mesh_atomic_volume.py'
        previous = ast.parse(old.read_text())
        names = {'CANDIDATE','CANDIDATE_SHA','CANDIDATE_VOLUME','OUTPUT','GATES','DEADLINE',
                 'RSS_STOP','OPTIONS','RUNTIME_HASHES','IMPORT_HASHES','PROJECT_SOURCE'}
        def assigned(tree):
            return {n.targets[0].id:ast.dump(n.value) for n in tree.body
                if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id in names}
        self.assertEqual(set(assigned(TREE)), names)
        self.assertEqual(assigned(TREE), assigned(previous))
        self.assertEqual(hashlib.sha256(old.read_bytes()).hexdigest(),
            'da089adac87bb098467e687a0b0bdb72bbd296ba5a14d125343173b9abda63ef')


if __name__ == '__main__':
    unittest.main()
