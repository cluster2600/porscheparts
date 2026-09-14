import hashlib
import importlib.util
import json
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'twins/m64-cylinder-head/targets'
SCRIPT = DIRECTORY / '700ps_garrett_reference.py'
spec = importlib.util.spec_from_file_location('m64_turbo_reference', SCRIPT)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


class TurboReferenceTests(unittest.TestCase):
    def test_published_reference_gives_identity(self):
        self.assertAlmostEqual(model.corrected_flow(40, (85 - 32) * 5 / 9 + 273.15, 13.95 * model.PSI_PA), 40)

    def test_reversing_published_equation_recovers_actual_flow(self):
        flow = model.corrected_flow(38.76529529393317, 298.15, 98325)
        recovered = flow * (98325 / model.PSI_PA / 13.95) / math.sqrt(537 / 545)
        self.assertAlmostEqual(recovered, 38.76529529393317)
        self.assertAlmostEqual(flow, 37.64100615142089)

    def test_absolute_pressure_doubling_halves_corrected_flow(self):
        self.assertAlmostEqual(model.corrected_flow(40, 300, 100000), 2 * model.corrected_flow(40, 300, 200000))

    def test_invalid_inputs_refused(self):
        for i in range(3):
            for bad in (0, -1, True, float('nan'), float('inf'), '300'):
                args = [40, 300, 100000]
                args[i] = bad
                with self.subTest(i=i, value=bad), self.assertRaises(ValueError):
                    model.corrected_flow(*args)

    def test_changed_balance_refused(self):
        with self.assertRaises(ValueError):
            model.report(b'{}')

    def test_published_result_and_nonqualification(self):
        saved = json.loads((DIRECTORY / '700ps-garrett-reference-20260908.json').read_text())
        self.assertEqual(saved.pop('script_sha256'), hashlib.sha256(SCRIPT.read_bytes()).hexdigest())
        self.assertEqual(saved, model.report((DIRECTORY / '700ps-balance-20260907.json').read_bytes()))
        self.assertFalse(saved['performance_validated'])
        self.assertFalse(saved['manufacturing_authorized'])
        self.assertIsNone(saved['efficiency_read_from_map'])
        self.assertIsNone(saved['shaft_speed_read_from_map'])


if __name__ == '__main__':
    unittest.main()
