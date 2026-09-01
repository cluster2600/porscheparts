import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/reference-935-cylinder-head/source/build_valve_variants.py"
CONFIG = ROOT / "twins/reference-935-cylinder-head/source/valve_variants_f1.json"
SPEC = importlib.util.spec_from_file_location("build_valve_variants", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ValveVariantTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(CONFIG.read_text())

    def test_every_proxy_has_positive_volume(self):
        for variant in self.data["variants"]:
            self.assertGreater(
                MODULE.proxy_volume_mm3(variant, self.data["geometry_defaults"]), 0
            )

    def test_titanium_proxy_is_lighter_than_baseline_steel(self):
        volume = MODULE.proxy_volume_mm3(
            self.data["variants"][0], self.data["geometry_defaults"]
        )
        materials = self.data["materials"]
        self.assertLess(
            MODULE.mass_g(volume, materials["ti64_grade5_lpbf"]["density_g_cm3"]),
            MODULE.mass_g(volume, materials["steel_reference"]["density_g_cm3"]),
        )

    def test_exhaust_variants_include_inconel_reference(self):
        exhaust = [v for v in self.data["variants"] if v["service"] == "exhaust"]
        self.assertTrue(exhaust)
        self.assertTrue(all("inconel_751_bar" in v["material_variants"] for v in exhaust))


if __name__ == "__main__":
    unittest.main()
