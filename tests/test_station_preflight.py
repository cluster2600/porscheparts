import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('station_preflight', Path(__file__).resolve().parents[1] / 'deploy/vast/station/preflight.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StationPreflightTests(unittest.TestCase):
    def test_cgroup_v1_and_v2_limit_host_resources(self):
        for files in ({'cpu.max': '3200000 100000', 'memory.max': str(256*10**9), 'memory.current': str(10*10**9)},
                      {'cpu,cpuacct/cpu.cfs_quota_us': '3200000', 'cpu,cpuacct/cpu.cfs_period_us': '100000',
                       'memory/memory.limit_in_bytes': str(256*10**9), 'memory/memory.usage_in_bytes': str(10*10**9)}):
            with self.subTest(files=files), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for name, value in files.items():
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(value)
                memory, cpu, _, observed = module.cgroup_allocation({'MemTotal': 774*10**9, 'MemAvailable': 700*10**9}, 128, root)
                self.assertTrue(observed)
                self.assertEqual(cpu, 32)
                self.assertEqual(memory['MemTotal'], 256*10**9)
                self.assertEqual(memory['MemAvailable'], 246*10**9)

    def test_missing_quota_metadata_does_not_qualify_host_totals(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, _, observed = module.cgroup_allocation({'MemTotal': 774*10**9, 'MemAvailable': 700*10**9}, 128, Path(directory))
            self.assertFalse(observed)


if __name__ == '__main__':
    unittest.main()
