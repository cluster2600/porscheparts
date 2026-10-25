"""Actual quota discovery covers both common Linux layouts and unbounded sentinels."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/inspect_linux_limits.py'
spec=importlib.util.spec_from_file_location('carrier_linux_limits',SOURCE);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class LinuxLimitTests(unittest.TestCase):
    def test_v2_reads_both_actual_limits(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);(root/'memory.max').write_text('183500800000\n');(root/'cpu.max').write_text('1536000 100000\n')
            result=module.inspect_limits(root,'')
            self.assertEqual(result['memory_limit_bytes'],183500800000);self.assertEqual(result['cpu_limit_cores'],15.36);self.assertEqual(result['memory_controller'],'v2')

    def test_v1_supports_both_cpu_mount_names(self):
        for name in ['cpu','cpu,cpuacct']:
            with self.subTest(name=name),tempfile.TemporaryDirectory()as directory:
                root=Path(directory);(root/'memory').mkdir();(root/name).mkdir();(root/'memory/memory.limit_in_bytes').write_text('367233335296\n');(root/name/'cpu.cfs_quota_us').write_text('3071999\n');(root/name/'cpu.cfs_period_us').write_text('100000\n')
                result=module.inspect_limits(root,'')
                self.assertEqual(result['memory_limit_bytes'],367233335296);self.assertEqual(result['cpu_limit_cores'],30.71999);self.assertEqual(result['cpu_controller'],'v1')

    def test_nested_membership_keeps_the_tighter_visible_parent_quota(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory)
            for group,memory,cpu in [('',10000,'1600000 100000'),('docker/case',20000,'800000 100000')]:
                path=root/group;path.mkdir(parents=True,exist_ok=True);(path/'memory.max').write_text(str(memory));(path/'cpu.max').write_text(cpu)
            result=module.inspect_limits(root,'0::/docker/case')
            self.assertEqual(result['memory_limit_bytes'],10000);self.assertEqual(result['cpu_limit_cores'],8)
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory)
            for controller in ['memory','cpu,cpuacct']:
                for group in ['', 'docker/case']:
                    path=root/controller/group;path.mkdir(parents=True,exist_ok=True)
                    if controller=='memory':(path/'memory.limit_in_bytes').write_text('9000'if group else'5000')
                    else:(path/'cpu.cfs_quota_us').write_text('1600000'if group else'800000');(path/'cpu.cfs_period_us').write_text('100000')
            result=module.inspect_limits(root,'2:memory:/docker/case\n3:cpu,cpuacct:/docker/case')
            self.assertEqual(result['memory_limit_bytes'],5000);self.assertEqual(result['cpu_limit_cores'],8)

    def test_membership_traversal_is_refused(self):
        with tempfile.TemporaryDirectory()as directory:
            with self.assertRaisesRegex(ValueError,'Invalid cgroup membership'):module.inspect_limits(directory,'0::/../../outside')

    def test_unbounded_sentinels_never_become_a_fake_allocation(self):
        for value in ['max','-1','9223372036854771712']:
            self.assertIsNone(module.memory_limit(value))
        for value in ['max','-1']:self.assertIsNone(module.cpu_limit(value,100000))

    def test_unknown_layout_and_invalid_limits_are_refused(self):
        with tempfile.TemporaryDirectory()as directory:
            with self.assertRaisesRegex(ValueError,'Unsupported cgroup memory layout'):module.inspect_limits(directory,'')
        for value in ['0','-2','nan']:
            with self.assertRaises(ValueError):module.memory_limit(value)
        for quota,period in [('0',100000),('-2',100000),('100',0)]:
            with self.assertRaises(ValueError):module.cpu_limit(quota,period)

if __name__=='__main__':unittest.main()
