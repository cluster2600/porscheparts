import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016/chart_progress.py'
spec=importlib.util.spec_from_file_location('chart_progress_test',SOURCE)
progress=importlib.util.module_from_spec(spec);spec.loader.exec_module(progress)

class ChartProgressTests(unittest.TestCase):
    def test_capture_precedes_call_and_preserves_exact_return_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'progress';domain=SimpleNamespace(wkb=b'domain',wkb_hex=b'domain'.hex())
            material=SimpleNamespace(wkb=b'result',wkb_hex=b'result'.hex());receipt={'unchanged':True};interfaces={'upper':[],'lower':[]}
            block=SimpleNamespace(supportTeethUpperPenetration=.2,generateTrussGrid=False)
            def original(b,d,defer,diagnostic,source):
                self.assertTrue((folder/'chart-0000-input.json').is_file())
                self.assertIs(b,block);self.assertIs(d,domain);self.assertIs(source,interfaces)
                self.assertTrue(defer);self.assertFalse(diagnostic)
                return material,receipt
            module=SimpleNamespace(native_infill=original);manifest=progress.install(module,folder)
            a,b=module.native_infill(block,domain,True,False,interfaces)
            self.assertIs(a,material);self.assertIs(b,receipt)
            self.assertEqual(manifest()['calls'],1);self.assertEqual(len(manifest()['files_sha256']),2)
            self.assertEqual(json.loads((folder/'chart-0000-input.json').read_text())['attested_source_interfaces'],interfaces)
            with self.assertRaisesRegex(ValueError,'already installed'):progress.install(module,Path(tmp)/'another')

    def test_completed_capture_roundtrips_full_material_and_native_infill(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'progress';material_bytes=b'full material representation'
            material=SimpleNamespace(wkb=material_bytes,wkb_hex=material_bytes.hex())
            receipt={'native_infill':{'regions':[{'coordinates':[[1.0,-0.0],[2.0,3.5]],'passed':True}]},'optional':None}
            receipt_before=json.dumps(receipt,allow_nan=False)
            module=SimpleNamespace(native_infill=lambda *args:(material,receipt));manifest=progress.install(module,folder)
            result,native=module.native_infill(SimpleNamespace(supportTeethUpperPenetration=.2,generateTrussGrid=False),SimpleNamespace(wkb=b'D',wkb_hex='44'))
            captured=json.loads((folder/'chart-0000-completed.json').read_text())
            self.assertEqual(bytes.fromhex(captured['generated_material_geometry_wkb_hex']),material_bytes)
            self.assertEqual(captured['native_infill'],receipt)
            self.assertEqual(json.dumps(receipt,allow_nan=False),receipt_before)
            self.assertIs(result,material);self.assertIs(native,receipt)
            self.assertEqual(manifest()['calls'],1)

    def test_capture_changed_during_call_cannot_be_reported_as_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'progress'
            def original(*args):
                (folder/'chart-0000-input.json').write_text('{}')
                return SimpleNamespace(wkb=b'result'),{}
            module=SimpleNamespace(native_infill=original);progress.install(module,folder)
            with self.assertRaisesRegex(ValueError,'Captured chart input changed'):
                module.native_infill(SimpleNamespace(supportTeethUpperPenetration=.2,generateTrussGrid=False),SimpleNamespace(wkb=b'D',wkb_hex='44'))
            receipt=json.loads((folder/'chart-0000-error.json').read_text())
            self.assertFalse(receipt['captured_input_unchanged'])
            self.assertFalse((folder/'chart-0000-completed.json').exists())

    def test_failed_call_keeps_capture_and_reraises_original_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'progress';error=ValueError('retained failure')
            def original(*args):raise error
            module=SimpleNamespace(native_infill=original);manifest=progress.install(module,folder)
            with self.assertRaises(ValueError) as caught:
                module.native_infill(SimpleNamespace(supportTeethUpperPenetration=.2,generateTrussGrid=False),SimpleNamespace(wkb=b'D',wkb_hex='44'),interfaces={'upper':[],'lower':[]})
            self.assertIs(caught.exception,error)
            self.assertTrue((folder/'chart-0000-input.json').exists())
            self.assertEqual(json.loads((folder/'chart-0000-error.json').read_text())['status'],'call_failed_no_admission')
            self.assertFalse((folder/'chart-0000-completed.json').exists())
            self.assertEqual(len(manifest()['files_sha256']),2)

if __name__=='__main__':unittest.main()
