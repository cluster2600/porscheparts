"""Fixed SSH arguments and real detached-worker journal logic without SSH/GPU."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('station_tools', ROOT / 'deploy/vast/station/openclaw-tools.py')
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


class StationToolsTest(unittest.TestCase):
    def test_task_and_endpoint_boundaries(self):
        self.assertEqual(tools.validate_job('coupon-001'), 'coupon-001')
        for value in ('../escape', '-oProxyCommand=sh', 'a;id', 'a/b', 'A', 'a' * 49):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                tools.validate_job(value)
        for value in ('nan', 'inf', '0', '100'):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                tools.bounded_number(20, 80)(value)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'endpoint.json'
            path.write_text(json.dumps({'host': 'ssh1.vast.ai', 'port': 22001}))
            self.assertEqual(tools.endpoint(path), ('ssh1.vast.ai', 22001))
            for host, port in [('host;id', 22), ('-oProxyCommand=sh', 22), ('999.0.0.1', 22),
                               ('bad..host', 22), ('host', True), ('host', 65536)]:
                path.write_text(json.dumps({'host': host, 'port': port}))
                with self.subTest(host=host, port=port), self.assertRaises(ValueError):
                    tools.endpoint(path)
        options = tools.ssh_options(22001)
        for required in ('IdentitiesOnly=yes', 'BatchMode=yes', 'StrictHostKeyChecking=yes', 'ForwardAgent=no'):
            self.assertIn(required, options)
        self.assertTrue(any(value.endswith('/.ssh/id_picogk_station_worker') for value in options))
        compile(tools.REMOTE, '<remote-station-command>', 'exec')

    def test_worker_records_actual_success_and_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            for action, code in [('demo', 0), ('render', 7)]:
                work = Path(directory) / action
                work.mkdir()
                command = [sys.executable, '-c', f'print("witness"); raise SystemExit({code})']
                result = subprocess.run([sys.executable, '-c', tools.WORKER, str(work), action, json.dumps(command)],
                                        capture_output=True, text=True, timeout=10, check=True)
                self.assertIn('witness', result.stdout)
                state = json.loads((work / (action + '.json')).read_text())
                self.assertEqual(state['returncode'], code)
                self.assertEqual(state['status'], 'complete' if code == 0 else 'failed')
                self.assertFalse((work / (action + '.tmp')).exists())


if __name__ == '__main__':
    unittest.main()
