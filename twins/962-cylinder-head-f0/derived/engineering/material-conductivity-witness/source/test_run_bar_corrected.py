"""Prepared mocked guards only; no native execution, runtime import or network."""
import importlib.util
import json
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch


class FixedBarLauncher(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('isolated_bar_launcher',Path(__file__).with_name('run_bar.py'))
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.source=self.base/'source';self.source.mkdir()
        self.runtime=self.base/'runtime';(self.runtime/'opt/moose/bin').mkdir(parents=True)
        binary=self.runtime/'opt/moose/bin/moose-opt';binary.write_bytes(b'fake-runtime-never-executed')
        self.output=self.base/'fresh-output';m=self.module;m.SOURCE=self.source
        (self.source/'run_bar.py').write_bytes(Path(m.__file__).read_bytes())
        for name in ['conductivity-z.i','conductivity-xy.i']:(self.source/name).write_text('fixed synthetic bytes')
        pins={'opt/moose/bin/moose-opt':m.sha(binary)}
        old={'required_rootfs':str(self.runtime),'runtime_sha256s':pins}
        (self.source/'old-runtime-contract.json').write_text(json.dumps(old))
        card=dict(native_launch_authorized=True,case_inputs=m.CASE_INPUTS,resources=m.RESOURCES,
            required_rootfs=str(self.runtime),reserved_remote_output=str(self.output),runtime_sha256s=pins,
            source_sha256s={p.name:m.sha(p) for p in self.source.iterdir()})
        self.contract=self.base/'contract.json';self.contract.write_text(json.dumps(card));self.digest=m.sha(self.contract)

    def test_changed_source_refused_before_output_or_executor(self):
        (self.source/'conductivity-z.i').write_text('changed')
        with patch.object(self.module.subprocess,'Popen') as spawn:
            with self.assertRaises(ValueError):self.module.run(self.runtime,self.output,self.contract,self.digest)
            spawn.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_existing_output_refused_preserving_bytes(self):
        self.output.mkdir();sentinel=self.output/'retained';sentinel.write_bytes(b'preserve')
        with patch.object(self.module.subprocess,'Popen') as spawn:
            with self.assertRaises(ValueError):self.module.run(self.runtime,self.output,self.contract,self.digest)
            spawn.assert_not_called()
        self.assertEqual(sentinel.read_bytes(),b'preserve')

    def test_interruption_kills_and_reaps_without_next_case(self):
        class Interrupted:
            pid=12345
            returncode=None
            calls=0
            def poll(self):return self.returncode
            def wait(self,timeout=None):
                self.calls+=1
                if self.calls==1:raise KeyboardInterrupt('mock interrupt')
                self.returncode=-9
                return self.returncode
        process=Interrupted()
        with patch.object(self.module.subprocess,'Popen',return_value=process) as spawn,patch.object(self.module.os,'killpg') as kill:
            with self.assertRaises(KeyboardInterrupt):self.module.run(self.runtime,self.output,self.contract,self.digest)
            spawn.assert_called_once();kill.assert_called_once_with(process.pid,signal.SIGKILL)
        self.assertGreaterEqual(process.calls,2)
        self.assertFalse((self.output/'XY').exists())
        receipt=json.loads((self.output/'Z/native-execution.json').read_text())
        self.assertTrue(receipt['process_reaped']);self.assertFalse(receipt['native_execution_completed'])
        self.assertFalse(json.loads((self.output/'execution-summary.json').read_text())['native_invocations_completed'])


if __name__=='__main__':unittest.main()
