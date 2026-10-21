"""Prepared stdlib mock checks only; no VTK, worker process or monitor execution."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
PREP = ROOT / 'work/962-engineering/atomic-cavity-openings-prep-001'


def launcher():
    spec = importlib.util.spec_from_file_location('opening_launcher_test', PREP / 'run_openings.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LauncherBoundaries(unittest.TestCase):
    def test_child_drift_refuses_before_worker_import_output_or_spawn(self):
        module = launcher()
        with tempfile.TemporaryDirectory() as tmp:
            child = Path(tmp) / 'child.json'
            child.write_text('{}\n')
            output = Path(tmp) / 'output'
            with patch.object(module, 'load') as load, patch.object(module.subprocess, 'Popen') as spawn:
                with self.assertRaisesRegex(ValueError, 'before worker import'):
                    module.run(child, '0' * 64, output)
                load.assert_not_called()
                spawn.assert_not_called()
                self.assertFalse(output.exists())

    def test_interruption_at_monitor_entry_delegates_immediate_owned_cleanup(self):
        module = launcher()
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'
            source_pins = {str(p.relative_to(ROOT)): digest(p)
                           for p in [PREP / 'run_openings.py', PREP / 'audit_openings.py']}
            child = Path(tmp) / 'child.json'
            child.write_text(json.dumps({'input_hashes': source_pins}))
            resources = dict(rss_stop_bytes=4294967296, rss_poll_seconds=.1,
                             process_group_deadline_seconds=120, thread_environment_limit=2,
                             hard_address_space_quota=False, OS_CPU_quota=False)
            def save(path, value):
                with path.open('x') as stream:
                    json.dump(value, stream)
            worker = SimpleNamespace(OUTPUT=output, ROOT=ROOT, SOURCE=ROOT / 'twins/962-cylinder-head-f0/source',
                RESOURCES=resources, QUALIFICATION={}, digest=digest, save=save,
                load_contract=lambda *_: {'input_hashes': source_pins, 'interpreter': '/unlaunched-mock-interpreter'})
            observation = dict(stopped_by_watchdog='process_group_wall_deadline', monitor_error=None,
                cleanup_error=None, worker_reaped=True, worker_running_after_monitor=False)
            monitor = SimpleNamespace(monitor=Mock(side_effect=[KeyboardInterrupt('entry gap'), observation]))
            process = SimpleNamespace(returncode=-9)
            with patch.object(module, 'load', side_effect=[worker, monitor]), \
                    patch.object(module.subprocess, 'Popen', return_value=process) as spawn:
                self.assertEqual(module.run(child, digest(child), output), 2)
            self.assertTrue(spawn.call_args.kwargs['start_new_session'])
            self.assertEqual(monitor.monitor.call_count, 2)
            self.assertIs(monitor.monitor.call_args_list[1].args[0], process)
            self.assertEqual(monitor.monitor.call_args_list[1].args[2]['process_group_deadline_seconds'], 0)
            receipt = json.loads((output / 'receipt.json').read_text())
            self.assertIn('KeyboardInterrupt: entry gap', receipt['error'])
            self.assertEqual(receipt['status'], 'failed_or_rejected_outputs_preserved')
            self.assertTrue(receipt['monitor_observation']['worker_reaped'])


if __name__ == '__main__':
    unittest.main()
