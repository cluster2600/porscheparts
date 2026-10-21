"""Prepared mock-only runner tests: no worker, mesh, ps or process is executed."""
from pathlib import Path
import hashlib
import importlib.util
import json
import signal
import subprocess
import tempfile
import threading
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[3]
PREP = ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-openings-prep-001'
RUNNER_SHA = '4a0cb41f61c583716117b5fa8b17b31c908c3bf3f9d3d7a40fc39f306d58d08f'
WORKER_SHA = 'c8546f7363deb8f0511b87b1ef8d9fc03d48d95016eab30d78f558047a49d506'
MONITOR = ROOT/'twins/962-cylinder-head-f0/source/run_quality_distance_002.py'
MONITOR_SHA = '6aeb8be558054b6cb4e8d1b7904adfe17d57b0c11d17a134cbe574a8cafa085c'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


class RunnerTests(unittest.TestCase):
    def harness(self, scenario):
        self.assertEqual(sha(PREP/'run_openings.py'), RUNNER_SHA)
        self.assertEqual(sha(PREP/'audit_openings.py'), WORKER_SHA)
        self.assertEqual(sha(MONITOR), MONITOR_SHA)
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name); prep = root/'work/962-engineering/prepared'
        prep.mkdir(parents=True); source = root/'source'; source.mkdir()
        runner = prep/'run_openings.py'; runner.write_bytes((PREP/'run_openings.py').read_bytes())
        worker = prep/'audit_openings.py'; worker.write_bytes((PREP/'audit_openings.py').read_bytes())
        monitor = source/MONITOR.name; monitor.write_bytes(MONITOR.read_bytes())
        # Only the exact copied standard-library runner definitions are loaded.
        # The worker is bytes only and its import hook is replaced below.
        spec = importlib.util.spec_from_file_location('mock_only_opening_runner', runner)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        output = root/'result'; contract_path = root/'child.json'
        pins = {str(p.relative_to(root)): sha(p) for p in (runner, worker, monitor)}
        contract = dict(interpreter='/fake/never-executed-python', input_hashes=pins)
        contract_path.write_text(json.dumps(contract))
        state = SimpleNamespace(process=None, kills=[], waits=[], timers=[], loads=0,
            guard_calls=0, ps_calls=0, signal_calls=[], signal_during_popen_returned=False)
        real_handler = signal.getsignal(signal.SIGTERM)
        signals = SimpleNamespace(current=real_handler, SIGTERM=signal.SIGTERM, SIGKILL=signal.SIGKILL)

        def getsignal(number):
            self.assertEqual(number, signal.SIGTERM); return signals.current

        def setsignal(number, handler):
            self.assertEqual(number, signal.SIGTERM)
            previous = signals.current; signals.current = handler
            state.signal_calls.append(handler); return previous

        module.signal = SimpleNamespace(SIGTERM=signal.SIGTERM, SIGKILL=signal.SIGKILL,
                                        getsignal=getsignal, signal=setsignal)

        def save(path, value):
            with path.open('x') as stream:
                json.dump(value, stream, allow_nan=False)

        def guard(path, expected):
            state.guard_calls += 1
            self.assertEqual(sha(path), expected)
            current = json.loads(path.read_text())
            for name, expected_hash in current['input_hashes'].items():
                self.assertEqual(sha(root/name), expected_hash)
            return current

        fake_worker = SimpleNamespace(ROOT=root, SOURCE=source, OUTPUT=output, digest=sha,
            save=save, load_contract=guard, QUALIFICATION={'engineering_accepted': False},
            RESOURCES=dict(process_group_deadline_seconds=120, rss_stop_bytes=4*1024**3,
                           rss_poll_seconds=.1))

        def fake_load(path, name):
            state.loads += 1
            self.assertEqual(path, worker)
            return fake_worker

        module.load = fake_load

        class Process:
            pid = 424242
            returncode = None

            def poll(self):
                return self.returncode

            def wait(self, timeout=None):
                state.waits.append(timeout)
                if timeout is not None and scenario == 'normal':
                    self.returncode = 0
                if self.returncode is None:
                    raise AssertionError('A live fake process must be killed before unbounded wait')
                return self.returncode

        def popen(command, **kwargs):
            self.assertEqual(command[0], '/fake/never-executed-python')
            self.assertTrue(kwargs['start_new_session'])
            self.assertEqual(kwargs['cwd'], root)
            self.assertEqual(kwargs['env']['PATH'], '/usr/bin:/bin')
            for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                        'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
                self.assertEqual(kwargs['env'][key], '2')
            self.assertNotIn('shell', kwargs)
            state.process = Process()
            save(output/'worker-report.json', dict(opening_subgate_passed=True, bound_inputs_unchanged=True))
            if scenario == 'sigterm_inside_popen':
                signals.current(signal.SIGTERM, None)
                state.signal_during_popen_returned = True
            return state.process

        def killpg(pid, number):
            self.assertEqual(pid, Process.pid); self.assertEqual(number, signal.SIGKILL)
            state.kills.append((pid, number)); state.process.returncode = -9

        def ps(command, **kwargs):
            state.ps_calls += 1
            self.assertEqual(command, ['/bin/ps', '-o', 'rss=', '-p', str(Process.pid)])
            self.assertEqual(kwargs['timeout'], 2)
            if scenario == 'rss_failure':
                raise subprocess.TimeoutExpired('mock ps', 2)
            return SimpleNamespace(returncode=0, stdout='4096\n')

        class Timer:
            def __init__(self, seconds, callback):
                self.seconds = seconds; self.callback = callback; self.cancelled = False
                state.timers.append(self)

            def start(self):
                if scenario == 'timer_start_error':
                    raise RuntimeError('mock timer start failed')
                if scenario == 'deadline':
                    self.callback()

            def cancel(self):
                self.cancelled = True

        module.os = SimpleNamespace(killpg=killpg)
        module.threading = SimpleNamespace(Lock=threading.Lock, Timer=Timer)
        module.subprocess = SimpleNamespace(Popen=popen, run=ps, STDOUT=subprocess.STDOUT,
            TimeoutExpired=subprocess.TimeoutExpired, SubprocessError=subprocess.SubprocessError)
        return SimpleNamespace(module=module, state=state, signals=signals, real_handler=real_handler,
            output=output, contract=contract, path=contract_path, root=root)

    def run_case(self, scenario):
        h = self.harness(scenario)
        rc = h.module.run(h.path, sha(h.path), h.output)
        report = json.loads((h.output/'receipt.json').read_text())
        observation = report['monitor_observation']
        self.assertEqual(h.state.loads, 1); self.assertEqual(h.state.guard_calls, 2)
        self.assertTrue(observation['worker_reaped']); self.assertFalse(observation['worker_running_after_monitor'])
        self.assertIsNone(observation['cleanup_error'])
        self.assertTrue(observation['SIGTERM_handler_restored'])
        self.assertEqual(h.signals.current, h.real_handler)
        self.assertEqual(signal.getsignal(signal.SIGTERM), h.real_handler)
        self.assertEqual(h.state.signal_calls[-1], h.real_handler)
        self.assertEqual(h.state.waits.count(None), 1)
        self.assertEqual(len(h.state.timers), 1); self.assertTrue(h.state.timers[0].cancelled)
        self.assertEqual(h.state.timers[0].seconds, 120)
        self.assertTrue(report['all_inputs_unchanged']); self.assertFalse(report['automatic_retry'])
        return h, rc, report, observation

    def test_normal_success_is_reaped_without_kill(self):
        h, rc, report, o = self.run_case('normal')
        self.assertEqual(rc, 0); self.assertEqual(report['returncode'], 0)
        self.assertEqual(h.state.kills, []); self.assertIsNone(o['stopped_by_watchdog'])
        self.assertEqual(o['maximum_observed_worker_RSS_bytes'], 4096*1024)
        self.assertIsNone(o['monitor_error'])
        self.assertEqual(report['status'], 'eight_openings_subgate_passed_no_admission')

    def test_sigterm_inside_popen_is_nonraising_then_killed_and_reaped(self):
        h, rc, report, o = self.run_case('sigterm_inside_popen')
        self.assertTrue(h.state.signal_during_popen_returned)
        self.assertEqual(rc, 2); self.assertEqual(report['returncode'], -9)
        self.assertEqual(len(h.state.kills), 1); self.assertEqual(h.state.ps_calls, 0)
        self.assertTrue(o['SIGTERM_requested']); self.assertEqual(o['stopped_by_watchdog'], 'controller_SIGTERM')
        self.assertIsNone(o['monitor_error'])

    def test_rss_observer_timeout_kills_and_reaps(self):
        h, rc, report, o = self.run_case('rss_failure')
        self.assertEqual(rc, 2); self.assertEqual(report['returncode'], -9)
        self.assertEqual(len(h.state.kills), 1); self.assertEqual(h.state.ps_calls, 1)
        self.assertEqual(o['stopped_by_watchdog'], 'RSS_observation_unavailable')
        self.assertIsNone(o['monitor_error'])

    def test_timer_start_error_after_popen_kills_and_reaps(self):
        h, rc, report, o = self.run_case('timer_start_error')
        self.assertEqual(rc, 2); self.assertEqual(report['returncode'], -9)
        self.assertEqual(len(h.state.kills), 1)
        self.assertEqual(o['stopped_by_watchdog'], 'controller_interrupted')
        self.assertIn('mock timer start failed', o['monitor_error'])

    def test_deadline_callback_kills_and_reaps(self):
        h, rc, report, o = self.run_case('deadline')
        self.assertEqual(rc, 2); self.assertEqual(report['returncode'], -9)
        self.assertEqual(len(h.state.kills), 1); self.assertEqual(h.state.ps_calls, 0)
        self.assertEqual(o['stopped_by_watchdog'], 'process_group_wall_deadline')
        self.assertIsNone(o['monitor_error'])

    def test_changed_source_pin_refuses_before_fake_worker_load(self):
        h = self.harness('normal')
        h.contract['input_hashes'][str((h.module.PREP/'run_openings.py').relative_to(h.root))] = '0'*64
        h.path.write_text(json.dumps(h.contract))
        with self.assertRaisesRegex(ValueError, 'source changed before import'):
            h.module.run(h.path, sha(h.path), h.output)
        self.assertEqual(h.state.loads, 0); self.assertIsNone(h.state.process)
        self.assertFalse(h.output.exists())
        self.assertEqual(signal.getsignal(signal.SIGTERM), h.real_handler)


if __name__ == '__main__':
    unittest.main()
