"""Check the CPU variant preserves the frozen data and train/test boundaries."""
import json
import importlib.util
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

PACKAGE=Path(__file__).resolve().parents[1]/'training/qwen-metal-additive-20261002'

class MetalCPUProfileTest(unittest.TestCase):
    def test_packaging_rejects_an_incomplete_training_run(self):
        path=PACKAGE/'package_cpu_run.py'
        spec=importlib.util.spec_from_file_location('metal_cpu_packager',path)
        packager=importlib.util.module_from_spec(spec)
        sys.path.insert(0,str(PACKAGE))
        try:
            spec.loader.exec_module(packager)
        finally:
            sys.path.remove(str(PACKAGE))
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';source.mkdir()
            (source/'run-receipt.json').write_text(json.dumps({'status':'training','test_used_in_training':False}))
            target=Path(tmp)/'package'
            with self.assertRaisesRegex(ValueError,'Run incomplete'):
                packager.package(source,target)
            self.assertFalse(target.exists())

    def test_published_result_integrity_and_corruption_rejection(self):
        path=PACKAGE/'verify_cpu_package.py'
        spec=importlib.util.spec_from_file_location('metal_cpu_verifier',path)
        verifier=importlib.util.module_from_spec(spec)
        sys.path.insert(0,str(PACKAGE))
        try:
            spec.loader.exec_module(verifier)
        finally:
            sys.path.remove(str(PACKAGE))
        package=PACKAGE/'runs/cpu-lora-001'
        self.assertEqual(verifier.verify(package)['status'],'pass')
        with tempfile.TemporaryDirectory() as tmp:
            changed=Path(tmp)/'result'
            shutil.copytree(package,changed)
            weights=changed/'adapter/adapter_model.safetensors'
            with weights.open('r+b') as stream:
                stream.seek(-1,2)
                original=stream.read(1)
                stream.seek(-1,2)
                stream.write(bytes([original[0]^1]))
            with self.assertRaisesRegex(ValueError,'Changed packaged file'):
                verifier.verify(changed)

    def test_default_entrypoint_checks_without_loading_weights(self):
        process=subprocess.run([sys.executable,str(PACKAGE/'run_cpu_pilot.py')],capture_output=True,text=True,check=True)
        result=json.loads(process.stdout)
        self.assertEqual(result['status'],'cpu_preflight_pass_not_trained')
        self.assertEqual(result['audit']['counts']['sft_tokens'],{'train':53,'valid':16,'test':21})

    def test_cpu_variant_is_explicitly_unquantized_and_preserves_source_experiment(self):
        cpu=json.loads((PACKAGE/'cpu-pilot.json').read_text())
        source=json.loads((PACKAGE/cpu['source_config']).read_text())
        self.assertEqual((cpu['device'],cpu['dtype']),('cpu','bfloat16'))
        self.assertIsNone(cpu['quantization'])
        self.assertEqual(source['training_arguments']['num_train_epochs'],1)
        self.assertEqual(source['training_arguments']['seed'],42)
        self.assertEqual(cpu['decoding'],{'do_sample':False,'max_new_tokens':256})

if __name__=='__main__':
    unittest.main()
