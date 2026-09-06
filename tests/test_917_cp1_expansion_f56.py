import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'twins/reference-917-engine'
spec = importlib.util.spec_from_file_location('cp1_expansion', ROOT / 'source/cp1_reference_expansion_f56.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CP1ReferenceExpansionTests(unittest.TestCase):
    def setUp(self):
        self.card = json.loads((ROOT / 'cp1-process-reference-f56.json').read_text())

    def test_endpoint_strains_use_interval_means_not_incremental_means(self):
        for temperature, expected in ((25, 0), (100, .001425), (200, .003675), (300, .00605)):
            self.assertAlmostEqual(module.reference_strain(self.card, temperature), expected)

    def test_interpolation_preserves_endpoint_strains(self):
        self.assertAlmostEqual(module.reference_strain(self.card, 150), .00255)

    def test_no_extrapolation_or_nonfinite_input(self):
        for temperature in (20, 350, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                module.reference_strain(self.card, temperature)

    def test_processes_and_qualification_remain_distinct(self):
        self.assertEqual([p['platform_temperature_c'] for p in self.card['processes']], [125, 150])
        self.assertFalse(self.card['existing_AlSi10Mg_Sapphire_results_transferred'])
        self.assertFalse(self.card['manufacturing_authorized'])


if __name__ == '__main__':
    unittest.main()
