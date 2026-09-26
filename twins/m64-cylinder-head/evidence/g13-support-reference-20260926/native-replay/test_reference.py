"""Private branch checks; mocked numerical execution is never evidence."""
import argparse
from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('native_reference',Path(__file__).with_name('reference.py'))
pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)


class Guards(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        for name in ('ccx','build.json','x.inp','minus_z.inp'):
            (self.root/name).write_text('fixture')
        (self.root/'build-inventory.json').write_text(json.dumps({'binary':{'sha256':'binary'},'dynamic_libraries':{}}))
        self.args=argparse.Namespace(binary=self.root/'ccx',binary_sha256='binary',build_receipt=self.root/'build.json',
            build_receipt_sha256='build',input=self.root,output=self.root/'new',deadline=time.time()+2700)

    def mocks(self,stack):
        stack.enter_context(patch.object(pilot.sys,'platform','darwin'))
        stack.enter_context(patch.object(pilot.platform,'machine',return_value='arm64'))
        stack.enter_context(patch.object(pilot.platform,'platform',return_value='mocked-test-only'))
        hashes={str(Path(pilot.reference.__file__)):pilot.HELPER_SHA,str(self.args.binary):'binary',
            str(self.args.build_receipt):'build',str(self.root/'build-inventory.json'):pilot.INVENTORY_SHA}
        stack.enter_context(patch.object(pilot.reference,'sha',side_effect=lambda p:hashes.get(str(p),'test-sha')))
        stack.enter_context(patch.object(pilot.subprocess,'run',return_value=argparse.Namespace(stdout='Mach-O arm64')))
        stack.enter_context(patch.object(pilot.reference,'inputs',return_value={'x':'fixture','minus_z':'fixture'}))
        stack.enter_context(patch.object(pilot.reference,'INPUTS',{'x.inp':'fixture','minus_z.inp':'fixture'}))
        stack.enter_context(patch.dict(pilot.os.environ,{},clear=False))
        stack.enter_context(patch.object(pilot.signal,'setitimer'))

    def test_hash_rejected_before_output(self):
        with ExitStack() as stack:
            self.mocks(stack);self.args.binary_sha256='wrong'
            with self.assertRaisesRegex(ValueError,'fingerprint mismatch'):
                pilot.run(self.args)
        self.assertFalse(self.args.output.exists())

    def test_output_never_reused(self):
        self.args.output.mkdir()
        with ExitStack() as stack:
            self.mocks(stack)
            with self.assertRaises(FileExistsError):pilot.run(self.args)
        self.assertEqual(list(self.args.output.iterdir()),[])

    def test_failed_solve_keeps_explicit_failure_schema(self):
        with ExitStack() as stack:
            self.mocks(stack)
            stack.enter_context(patch.object(pilot.reference,'ccx',side_effect=TimeoutError('fixture timeout')))
            self.assertEqual(pilot.run(self.args),2)
        value=json.loads((self.args.output/'summary-0001.json').read_text())
        self.assertFalse(value['complete']);self.assertFalse(value['CUDA_executed'])
        self.assertFalse(value['G13_Linux_reference_promoted']);self.assertFalse(value['manufacturing_authorized'])
        self.assertTrue(value['original_failure_preserved']);self.assertIn('fixture timeout',value['error'])


if __name__=='__main__':unittest.main()
