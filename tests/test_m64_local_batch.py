"""Local Python fixtures and protocol mocks; no remote/native engineering work."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/run_local_batch.py'
spec = importlib.util.spec_from_file_location('local_batch_test', SOURCE)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


class LocalBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='m64-local-batch-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / 'output'
        self.manifest = self.root / 'manifest.json'
        self.python = str(Path(sys.executable).resolve())
        self.doc = {'schema': 'm64-local-batch/v1', 'campaign_timeout_seconds': 8,
                    'inputs': {}, 'commands': []}

    def add(self, text='print("private log content")\n', *, timeout=2, gate=None, args=()):
        script = self.root / f'script-{len(self.doc["commands"])}.py'
        script.write_text(text)
        self.doc['inputs'][str(script)] = b.digest(script)
        command = {'argv': [self.python, str(script), *args], 'script': str(script),
                   'timeout_seconds': timeout}
        if gate is not None:
            command['gate'] = gate
        self.doc['commands'].append(command)
        return script

    def execute(self):
        self.manifest.write_text(json.dumps(self.doc))
        with redirect_stdout(io.StringIO()) as stream:
            code = b.run_batch(self.manifest, self.output)
        self.stdout = stream.getvalue()
        self.summary = json.loads(self.stdout)
        report = self.output / 'batch-report.json'
        self.report = json.loads(report.read_text()) if report.exists() else None
        return code

    def test_success_two_steps_gate_logs_and_private_summary(self):
        self.add('from pathlib import Path\nPath("first").write_text("ready")\nprint("PRIVATE_VALUE")\n')
        self.add('from pathlib import Path\nimport json,sys\nassert Path("first").read_text()=="ready"\n'
                 'Path(sys.argv[1]).write_text(json.dumps({"ok":True}))\n',
                 gate={'report': 'gate.json', 'key': 'ok'}, args=('{output}/gate.json',))
        self.assertEqual(self.execute(), 0)
        self.assertEqual(self.summary['commands_completed'], 2)
        self.assertTrue(self.report['steps'][1]['gate_passed'])
        self.assertTrue(self.report['inputs_unchanged'])
        self.assertIn('PRIVATE_VALUE', (self.output / 'step-01.log').read_text())
        self.assertNotIn('PRIVATE_VALUE', self.stdout)
        self.assertNotIn(str(self.root), self.stdout)
        self.assertLessEqual(len(self.stdout.encode()), 4096)
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.output / 'batch-report.json').stat().st_mode), 0o600)

    def test_nonzero_stops_without_retry_or_second_step(self):
        self.add('from pathlib import Path\nPath("attempt").write_text("once")\nraise SystemExit(7)\n')
        self.add('from pathlib import Path\nPath("second").touch()\n')
        self.assertEqual(self.execute(), 2)
        self.assertEqual(self.summary['reason'], 'command_failed')
        self.assertEqual(self.report['steps'][0]['exit_code'], 7)
        self.assertEqual(len(self.report['steps']), 1)
        self.assertFalse((self.output / 'second').exists())

    def test_gate_false_one_null_and_missing_are_not_true(self):
        for value in (False, 1, None, 'true'):
            with self.subTest(value=value):
                self.output = self.root / ('gate-' + str(value))
                self.doc['commands'] = []; self.doc['inputs'] = {}
                self.add('from pathlib import Path\nPath("gate.json").write_text('+repr(json.dumps({'ok': value}))+')\n',
                         gate={'report': 'gate.json', 'key': 'ok'})
                self.assertEqual(self.execute(), 2)
                self.assertEqual(self.summary['reason'], 'gate_not_true')
                self.assertEqual(self.summary['commands_completed'], 0)

    def test_gate_missing_key_stops(self):
        self.add('from pathlib import Path\nPath("gate.json").write_text("{}")\n',
                 gate={'report': 'gate.json', 'key': 'missing'})
        self.assertEqual(self.execute(), 2)
        self.assertEqual(self.summary['reason'], 'gate_not_true')

    def test_gate_missing_file_stops(self):
        self.add(gate={'report': 'missing.json', 'key': 'ok'})
        self.assertEqual(self.execute(), 2)
        self.assertEqual(self.summary['commands_completed'], 0)

    def test_oversize_manifest_stops_before_launch(self):
        self.add(); self.doc['padding'] = 'x' * (b.MAX_JSON + 1)
        with mock.patch.object(b.subprocess, 'Popen') as launch:
            self.assertEqual(self.execute(), 2); launch.assert_not_called()
        self.assertEqual(self.summary['reason'], 'bounded_regular_json_required')

    def test_script_pin_required_before_any_command(self):
        script = self.add(); self.doc['inputs'][str(script)] = '0' * 64
        with mock.patch.object(b.subprocess, 'Popen') as launch:
            self.assertEqual(self.execute(), 2); launch.assert_not_called()
        self.assertEqual(self.summary['reason'], 'input_changed')

    def test_unpinned_script_rejected(self):
        script = self.add()
        data = self.root / 'data'; data.write_text('input')
        self.doc['inputs'] = {str(data): b.digest(data)}
        with self.assertRaisesRegex(b.StopBatch, 'explicit_pinned_script'):
            b.validate(self.doc)
        self.assertNotIn(str(script), self.doc['inputs'])

    def test_input_changed_by_first_command_stops_next_command(self):
        data = self.root / 'data'; data.write_text('old')
        self.doc['inputs'][str(data)] = b.digest(data)
        self.add('from pathlib import Path\nimport sys\nPath(sys.argv[1]).write_text("changed")\n', args=(str(data),))
        self.add('raise RuntimeError("must not run")\n')
        self.assertEqual(self.execute(), 2)
        self.assertEqual(self.summary['reason'], 'input_changed')
        self.assertEqual(len(self.report['steps']), 1)
        self.assertFalse((self.output / 'step-02.log').exists())

    def test_later_command_cannot_change_a_passed_gate(self):
        self.add('from pathlib import Path\nPath("gate.json").write_text("{\\"ok\\":true}")\n',
                 gate={'report': 'gate.json', 'key': 'ok'})
        self.add('from pathlib import Path\nPath("gate.json").write_text("{\\"ok\\":false}")\n')
        self.assertEqual(self.execute(), 2)
        self.assertEqual(self.summary['reason'], 'input_changed')
        self.assertEqual(self.summary['commands_completed'], 1)
        self.assertFalse(self.report['inputs_unchanged'])

    def test_manifest_pin_cannot_be_silently_replaced(self):
        self.add(); self.doc['inputs'][str(self.manifest)] = '0' * 64
        with mock.patch.object(b.subprocess, 'Popen') as launch:
            self.assertEqual(self.execute(), 2); launch.assert_not_called()
        self.assertEqual(self.summary['reason'], 'manifest_pin_mismatch')

    def test_output_existing_is_untouched(self):
        self.add(); self.output.mkdir(); marker = self.output / 'kept'; marker.write_text('unchanged')
        self.assertEqual(self.execute(), 2)
        self.assertEqual(self.summary['reason'], 'fresh_output_required')
        self.assertEqual(list(self.output.iterdir()), [marker])
        self.assertEqual(marker.read_text(), 'unchanged')

    def test_literal_shell_characters_are_not_executed(self):
        argument = '$(touch injected); echo PRIVATE_ARG'
        self.add('import sys\nassert sys.argv[1]=='+repr(argument)+'\nprint(sys.argv[1])\n', args=(argument,))
        with mock.patch.object(b.subprocess, 'Popen', wraps=subprocess.Popen) as launch:
            self.assertEqual(self.execute(), 0)
            self.assertIs(launch.call_args.kwargs['shell'], False)
            self.assertIs(launch.call_args.kwargs['start_new_session'], True)
            self.assertEqual(launch.call_args.args[0][-1], argument)
        self.assertFalse((self.output / 'injected').exists())
        self.assertNotIn('PRIVATE_ARG', self.stdout)

    def test_timeout_kills_and_waits_for_process_group(self):
        self.add('import time\ntime.sleep(10)\n', timeout=.1)
        with mock.patch.object(b.os, 'killpg', wraps=os.killpg) as kill:
            start = time.monotonic(); self.assertEqual(self.execute(), 2)
        self.assertLess(time.monotonic() - start, 2)
        self.assertEqual(self.summary['reason'], 'command_timeout')
        self.assertEqual(kill.call_args.args[1], signal.SIGKILL)
        self.assertTrue(self.report['steps'][0]['process_group_cleanup_completed'])

    def test_descendant_is_killed_not_only_parent(self):
        child = 'import time;from pathlib import Path;time.sleep(.8);Path("escaped").touch()'
        self.add('import subprocess,sys,time\nsubprocess.Popen([sys.executable,"-c",'+repr(child)+'])\ntime.sleep(10)\n', timeout=.25)
        self.assertEqual(self.execute(), 2)
        time.sleep(.9)
        self.assertFalse((self.output / 'escaped').exists())

    def test_campaign_caps_cumulative_command_time(self):
        self.doc['campaign_timeout_seconds'] = 2
        self.add('import time\ntime.sleep(.6)\n'); self.add('import time\ntime.sleep(.6)\n')
        started = time.monotonic(); self.assertEqual(self.execute(), 2)
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(self.summary['commands_completed'], 1)
        self.assertEqual(len(self.report['steps']), 2)

    def test_interruption_cleans_child_and_restores_signal_handlers(self):
        self.add(); process = mock.Mock(pid=12345)
        process.wait.side_effect = [b.StopBatch('interrupted'), 0]
        before = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
        with mock.patch.object(b.subprocess, 'Popen', return_value=process), mock.patch.object(b.os, 'killpg') as kill:
            self.assertEqual(self.execute(), 2)
            kill.assert_called_once_with(12345, signal.SIGKILL)
        self.assertEqual(process.wait.call_count, 2)
        self.assertEqual(self.summary['reason'], 'interrupted')
        self.assertEqual({s: signal.getsignal(s) for s in before}, before)

    def test_signal_callback_stops(self):
        with self.assertRaisesRegex(b.StopBatch, 'interrupted'):
            b.interrupted(signal.SIGTERM, None)

    def test_cleanup_failure_not_claimed_complete(self):
        self.add(); process = mock.Mock(pid=12345)
        process.wait.side_effect = [subprocess.TimeoutExpired('private', .1), subprocess.TimeoutExpired('private', 1)]
        with mock.patch.object(b.subprocess, 'Popen', return_value=process), mock.patch.object(b.os, 'killpg'):
            self.assertEqual(self.execute(), 2)
        self.assertEqual(self.summary['reason'], 'process_cleanup_timeout')
        self.assertNotIn('process_group_cleanup_completed', self.report['steps'][0])

    def test_zero_nine_commands_and_string_argv_refused(self):
        self.add()
        for commands in ([], self.doc['commands'] * 9, [{**self.doc['commands'][0], 'argv': 'echo bad'}]):
            with self.subTest(commands=len(commands)), self.assertRaises(b.StopBatch):
                b.validate({**self.doc, 'commands': commands})

    def test_nonfinite_zero_boolean_and_unbounded_timeouts_refused(self):
        self.add()
        for value in (0, -1, True, float('inf'), float('nan'), 3601):
            with self.subTest(value=value), self.assertRaises(b.StopBatch):
                b.validate({**self.doc, 'campaign_timeout_seconds': value})

    def test_direct_remote_container_or_shell_commands_refused(self):
        self.add()
        for name in ('ssh', 'docker', 'vastai', 'bash'):
            executable = self.root / name; executable.write_text('not executed')
            row = {**self.doc['commands'][0], 'argv': [str(executable), self.doc['commands'][0]['script']]}
            with self.subTest(name=name), self.assertRaisesRegex(b.StopBatch, 'local_commands_only'):
                b.validate({**self.doc, 'commands': [row]})

    def test_gate_path_escape_refused(self):
        self.add(gate={'report': '../outside.json', 'key': 'ok'})
        with self.assertRaisesRegex(b.StopBatch, 'relative_gate_report'):
            b.validate(self.doc)

    def test_old_gate_from_prior_command_refused(self):
        self.add('from pathlib import Path\nPath("gate.json").write_text("{\\"ok\\":true}")\n')
        self.add(gate={'report': 'gate.json', 'key': 'ok'})
        self.assertEqual(self.execute(), 2)
        self.assertEqual(self.summary['reason'], 'gate_report_must_be_new')
        self.assertEqual(len(self.report['steps']), 1)

    def test_batch_report_collision_preserves_command_output(self):
        self.add('from pathlib import Path\nPath("batch-report.json").write_text("{}")\n')
        self.assertEqual(self.execute(), 2)
        self.assertEqual(self.summary['reason'], 'batch_report_write_failed')
        self.assertEqual((self.output / 'batch-report.json').read_text(), '{}')


if __name__ == '__main__':
    unittest.main()
