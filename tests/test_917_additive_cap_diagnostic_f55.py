import json
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'twins/reference-917-engine/source/prepare_additive_cap_diagnostic_f55.py'


class CapDiagnosticTests(unittest.TestCase):
    def test_peak_is_not_confused_with_final_temperature(self):
        path = SCRIPT.with_name('postprocess_additive_diagnostic_f55.py')
        spec = importlib.util.spec_from_file_location('cap_post', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            case = Path(folder)
            bounds = case / 'postProcessing/diagnosticTemperatureBounds/0/volFieldValue.dat'
            bounds.parent.mkdir(parents=True)
            bounds.write_text('# time max(T)\n0.00004 4700\n0.00012 4200\n')
            (case / 'diagnostic-run.log').write_text('Time = 0.00012\nabsorbed power: 290\n')
            result = module.evaluate(case)
            self.assertEqual(result['temperature_max_k'], 4700)
            self.assertEqual(result['temperature_final_k'], 4200)
            self.assertTrue(result['final_time_reached'])
            self.assertFalse(result['process_qualified'])
            bounds.write_text('0.00012 nan\n')
            with self.assertRaises(ValueError):
                module.evaluate(case)

    def test_only_intended_inputs_differ_and_output_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, output = root / 'source', root / 'output'
            for name in ('0', 'constant', 'system'):
                (source / name).mkdir(parents=True)
            (source / '0/T').write_text('internalField uniform 293.15;\n')
            (source / 'constant/heatSourceDict').write_text('sources { beam { absorption { model Kelly; eta0 0.28; etaMin 0.35; } } }\n')
            (source / 'system/fvSolution').write_text('PIMPLE {\n Tmax 3300.0;\n}\n')
            (source / 'system/controlDict').write_text('endTime 0.015;\nwriteInterval 0.0025;\nwriteFormat binary;\nfunctions\n{\n}\n')
            before = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()}
            command = [sys.executable, str(SCRIPT), '--source', str(source), '--output', str(output), '--include-constant-absorption']
            subprocess.run(command, check=True, capture_output=True)
            manifest = json.loads((output / 'manifest.json').read_text())
            hashes = {k: v['files_sha256'] for k, v in manifest['cases'].items()}
            self.assertEqual([k for k in hashes['capped'] if hashes['capped'][k] != hashes['uncapped'][k]], ['system/fvSolution'])
            self.assertEqual([k for k in hashes['uncapped'] if hashes['uncapped'][k] != hashes['uncapped_constant_absorption'][k]], ['constant/heatSourceDict'])
            self.assertFalse(manifest['manufacturing_authorized'])
            self.assertEqual(before, {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()})
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
