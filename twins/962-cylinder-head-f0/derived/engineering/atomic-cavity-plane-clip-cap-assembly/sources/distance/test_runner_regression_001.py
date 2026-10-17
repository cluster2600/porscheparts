"""Prepared six mock-only serial CUB runner tests; never run native/ps/kill/CUB."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import signal
import subprocess
import tempfile
import threading
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[3]
PREP = ROOT/'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-prep-001'
RUNNER_SHA = '7b7cc6da9c5322be5e6ebc74730b9838379bd67b6f5c7aaf2a03fdec71d6238d'
WORKER_SHA = '58a23c788cd0d9053b64c0bab3acff68a5ea33427e79a19f56516d05cb090f0d'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


class CubRunnerTests(unittest.TestCase):
    def harness(self, scenario):
        self.assertEqual(sha(PREP/'run_quality_distance_002.py'), RUNNER_SHA)
        self.assertEqual(sha(PREP/'audit_quality_distance.py'), WORKER_SHA)
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()  # Preserve production canonical path guards on macOS.
        copied = root/'work/962-engineering/copied'; copied.mkdir(parents=True)
        runner = copied/'run_quality_distance_002.py'
        worker = copied/'audit_quality_distance.py'
        runner.write_bytes((PREP/runner.name).read_bytes())
        worker.write_bytes((PREP/worker.name).read_bytes())
        self.assertEqual(sha(runner), RUNNER_SHA); self.assertEqual(sha(worker), WORKER_SHA)
        # This exact copied module imports only stdlib. The copied worker is bytes only.
        spec = importlib.util.spec_from_file_location('mock_only_cub_runner', runner)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        self.assertEqual(module.ROOT, root); self.assertEqual(module.WORKER, worker)
        output = root/'result'; contract_path = root/'child.json'
        query_paths = []
        for name in ['first-to-COMPLETE-second', 'second-to-COMPLETE-first']:
            path = root/(name+'.json')
            path.write_text(json.dumps(dict(id=name, source='never-read-source.bin',
                target='never-read-COMPLETE-target.bin', partition='never-read-mask.npz')))
            query_paths.append(path)
        resources = dict(rss_stop_bytes=4294967296, rss_poll_seconds=.1,
            process_group_deadline_seconds=300, native_library_serial=True,
            thread_environment_limit=2, hard_address_space_quota=False, OS_CPU_quota=False)
        contract = dict(kind='reviewed_head', root_authorised_head_distance=True,
            python='/fake/never-executed-python', resources=resources,
            input_hashes={str(p.relative_to(root)): sha(p) for p in [runner, worker]},
            query_config_hashes={str(p.relative_to(root)): sha(p) for p in query_paths},
            queries=[str(p.relative_to(root)) for p in query_paths])
        contract_path.write_text(json.dumps(contract))
        state = SimpleNamespace(processes=[], popen_order=[], kills=[], waits=[], timers=[],
            ps_calls=0, signal_calls=[], signal_inside_popen_returned=False,
            clock=100., popen_elapsed=301. if scenario == 'late_completed_no_callback' else
                (17. if scenario == 'deadline' else 7.))
        real_handler = signal.getsignal(signal.SIGTERM)
        signals = SimpleNamespace(current=real_handler)

        def getsignal(number):
            self.assertEqual(number, signal.SIGTERM); return signals.current

        def setsignal(number, handler):
            self.assertEqual(number, signal.SIGTERM)
            previous = signals.current; signals.current = handler
            state.signal_calls.append(handler); return previous

        module.signal = SimpleNamespace(SIGTERM=signal.SIGTERM, SIGKILL=signal.SIGKILL,
            getsignal=getsignal, signal=setsignal)
        module.time = SimpleNamespace(monotonic=lambda: state.clock)

        class Process:
            def __init__(self, index):
                self.index = index; self.pid = 424242+index; self.returncode = None
                self.reaped = False

            def poll(self):
                return self.returncode

            def wait(self, timeout=None):
                state.waits.append((self.index, timeout))
                if timeout is not None and scenario == 'normal':
                    self.returncode = 0; state.clock += timeout
                if self.returncode is None:
                    raise AssertionError('Live fake process must be killed before wait completes')
                if timeout is None:
                    self.reaped = True
                return self.returncode

        def popen(command, **kwargs):
            index = len(state.processes)
            self.assertLess(index, 2)
            if index:
                self.assertIn(scenario, ['normal', 'late_completed_no_callback'])
                self.assertTrue(state.processes[0].reaped)
                self.assertEqual(state.processes[0].returncode, 0)
                self.assertTrue((output/query_paths[0].stem/'execution-receipt.json').is_file())
            self.assertEqual(command[0], '/fake/never-executed-python')
            self.assertEqual(command[1:4], ['-B', str(worker), '--worker'])
            self.assertEqual(command[5], str(query_paths[index]))
            self.assertTrue(kwargs['start_new_session']); self.assertEqual(kwargs['cwd'], root)
            self.assertEqual(kwargs['env']['PATH'], '/usr/bin:/bin')
            for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                        'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS']:
                self.assertEqual(kwargs['env'][key], '2')
            self.assertNotIn('shell', kwargs)
            process = Process(index); state.processes.append(process)
            state.popen_order.append(query_paths[index].stem)
            # A minimal fake artifact is sufficient: no worker algorithm or array is imported.
            Path(command[-1]).write_text(json.dumps(dict(mock_only=True, direction=index)))
            state.clock += state.popen_elapsed
            if scenario == 'late_completed_no_callback':
                process.returncode = 0
            if scenario == 'sigterm_inside_popen':
                signals.current(signal.SIGTERM, None)
                state.signal_inside_popen_returned = True
            return process

        def killpg(pid, number):
            self.assertEqual(number, signal.SIGKILL)
            process = next(p for p in state.processes if p.pid == pid)
            state.kills.append((pid, number)); process.returncode = -9

        def ps(command, **kwargs):
            state.ps_calls += 1
            self.assertEqual(command, ['/bin/ps', '-o', 'rss=', '-p', str(state.processes[-1].pid)])
            self.assertEqual(kwargs['timeout'], 2)
            if scenario == 'rss_failure':
                raise subprocess.TimeoutExpired('mock ps', 2)
            return SimpleNamespace(returncode=0, stdout='4096\n')

        class Timer:
            def __init__(self, seconds, callback):
                self.seconds = seconds; self.callback = callback; self.cancelled = False
                self.callback_invoked = False
                state.timers.append(self)

            def start(self):
                if scenario == 'timer_start_error':
                    raise RuntimeError('mock Timer.start failed')
                if scenario == 'deadline':
                    self.callback_invoked = True
                    self.callback()

            def cancel(self):
                self.cancelled = True

        module.os = SimpleNamespace(killpg=killpg)
        module.threading = SimpleNamespace(Lock=threading.Lock, Timer=Timer)
        module.subprocess = SimpleNamespace(Popen=popen, run=ps, STDOUT=subprocess.STDOUT,
            TimeoutExpired=subprocess.TimeoutExpired, SubprocessError=subprocess.SubprocessError)
        return SimpleNamespace(module=module, state=state, signals=signals, real_handler=real_handler,
            output=output, path=contract_path, contract=contract, root=root, query_paths=query_paths,
            runner=runner, worker=worker)

    def run_case(self, scenario):
        h = self.harness(scenario)
        with contextlib.redirect_stdout(io.StringIO()):
            rc = h.module.run(h.path, sha(h.path), h.output)
        summary = json.loads((h.output/'execution-summary.json').read_text())
        expected = 2 if scenario == 'normal' else 1
        self.assertEqual(len(h.state.processes), expected)
        self.assertEqual(summary['completed_queries'], expected)
        self.assertEqual(summary['planned_queries'], 2)
        self.assertEqual(h.state.popen_order, [p.stem for p in h.query_paths[:expected]])
        self.assertTrue(summary['all_bound_inputs_unchanged'])
        self.assertFalse(summary['independent_distance_gate_passed'])
        self.assertEqual(h.signals.current, h.real_handler)
        self.assertEqual(signal.getsignal(signal.SIGTERM), h.real_handler)
        self.assertEqual(len(h.state.timers), expected)
        reports = []
        for index, process in enumerate(h.state.processes):
            receipt = json.loads((h.output/h.query_paths[index].stem/'execution-receipt.json').read_text())
            self.assertTrue(receipt['worker_reaped']); self.assertFalse(receipt['worker_running_after_monitor'])
            self.assertIsNone(receipt['cleanup_error']); self.assertTrue(receipt['SIGTERM_handler_restored'])
            self.assertTrue(process.reaped); self.assertTrue(h.state.timers[index].cancelled)
            self.assertEqual(h.state.timers[index].seconds, max(0., 300.-h.state.popen_elapsed))
            self.assertEqual(h.state.waits.count((index, None)), 1)
            self.assertEqual(h.state.signal_calls[2*index+1], h.real_handler)
            reports.append(receipt)
        if scenario != 'normal':
            self.assertFalse((h.output/h.query_paths[1].stem).exists())
            self.assertEqual(rc, 2); self.assertFalse(summary['native_queries_completed'])
        return h, rc, summary, reports

    def test_normal_first_and_second_progress_only_after_reaping(self):
        h, rc, summary, receipts = self.run_case('normal')
        self.assertEqual(rc, 0); self.assertTrue(summary['native_queries_completed'])
        self.assertEqual(h.state.kills, []); self.assertEqual(h.state.ps_calls, 2)
        for receipt in receipts:
            self.assertEqual(receipt['returncode'], 0); self.assertIsNone(receipt['stopped_by_watchdog'])
            self.assertIsNone(receipt['monitor_error'])
            self.assertEqual(receipt['maximum_observed_worker_RSS_bytes'], 4096*1024)

    def test_SIGTERM_during_fake_Popen_is_captured_then_cleaned_without_second(self):
        h, rc, summary, receipts = self.run_case('sigterm_inside_popen')
        receipt = receipts[0]
        self.assertTrue(h.state.signal_inside_popen_returned)
        self.assertEqual(len(h.state.kills), 1); self.assertEqual(h.state.ps_calls, 0)
        self.assertEqual(receipt['returncode'], -9); self.assertTrue(receipt['SIGTERM_requested'])
        self.assertEqual(receipt['stopped_by_watchdog'], 'controller_SIGTERM')
        self.assertIsNone(receipt['monitor_error'])

    def test_ps_failure_kills_reaps_and_prevents_second(self):
        h, rc, summary, receipts = self.run_case('rss_failure')
        self.assertEqual(len(h.state.kills), 1); self.assertEqual(h.state.ps_calls, 1)
        self.assertEqual(receipts[0]['stopped_by_watchdog'], 'RSS_observation_unavailable')
        self.assertEqual(receipts[0]['returncode'], -9)

    def test_Timer_start_error_kills_reaps_and_prevents_second(self):
        h, rc, summary, receipts = self.run_case('timer_start_error')
        self.assertEqual(len(h.state.kills), 1); self.assertEqual(h.state.ps_calls, 0)
        self.assertEqual(receipts[0]['stopped_by_watchdog'], 'controller_interrupted')
        self.assertIn('mock Timer.start failed', receipts[0]['monitor_error'])
        self.assertEqual(receipts[0]['returncode'], -9)

    def test_deadline_callback_uses_remaining_start_budget_and_prevents_second(self):
        h, rc, summary, receipts = self.run_case('deadline')
        self.assertEqual(h.state.timers[0].seconds, 283.)
        self.assertEqual(len(h.state.kills), 1); self.assertEqual(h.state.ps_calls, 0)
        self.assertEqual(receipts[0]['stopped_by_watchdog'], 'process_group_wall_deadline')
        self.assertEqual(receipts[0]['returncode'], -9)

    def test_already_completed_after_budget_refuses_without_timer_callback(self):
        h, rc, summary, receipts = self.run_case('late_completed_no_callback')
        self.assertEqual(h.state.timers[0].seconds, 0.)
        self.assertFalse(h.state.timers[0].callback_invoked)
        self.assertTrue(h.state.timers[0].cancelled)
        self.assertEqual(receipts[0]['returncode'], 0)
        self.assertEqual(receipts[0]['wall_seconds'], 301.)
        self.assertEqual(receipts[0]['stopped_by_watchdog'], 'process_group_wall_deadline')
        self.assertEqual(h.state.kills, []); self.assertEqual(h.state.ps_calls, 0)
        self.assertEqual(rc, 2); self.assertFalse(summary['native_queries_completed'])

    def test_changed_pin_refuses_before_output_or_any_fake_Popen(self):
        h = self.harness('normal')
        h.contract['input_hashes'][str(h.worker.relative_to(h.root))] = '0'*64
        h.path.write_text(json.dumps(h.contract))
        with self.assertRaisesRegex(ValueError, 'Frozen source, configuration or runtime changed'):
            h.module.run(h.path, sha(h.path), h.output)
        self.assertEqual(h.state.processes, []); self.assertEqual(h.state.timers, [])
        self.assertEqual(h.state.kills, []); self.assertEqual(h.state.ps_calls, 0)
        self.assertEqual(h.state.signal_calls, []); self.assertFalse(h.output.exists())
        self.assertEqual(signal.getsignal(signal.SIGTERM), h.real_handler)


if __name__ == '__main__':
    unittest.main()
