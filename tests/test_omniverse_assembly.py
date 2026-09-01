import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/omniverse-engine-assembly/source/build_usd_assemblies.py"
CONFIG = ROOT / "twins/omniverse-engine-assembly/assembly-f0.json"
SPEC = importlib.util.spec_from_file_location("build_usd_assemblies", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class OmniverseAssemblyTests(unittest.TestCase):
    def test_contract_keeps_917_and_935_separate(self):
        data = json.loads(CONFIG.read_text())
        self.assertEqual(data["assets"]["engine_917"]["fitment"], "no_993_or_935_fitment_claim")
        self.assertEqual(data["assets"]["head_935"]["fitment"], "comparison_rig_only")
        self.assertNotEqual(
            data["overview_offsets_mm"]["engine_917"],
            data["overview_offsets_mm"]["valvetrain_rig"],
        )

    def test_exhaust_defaults_to_inconel_study(self):
        data = json.loads(CONFIG.read_text())
        exhaust = [v for v in data["valves"] if "Exhaust" in v["id"]]
        self.assertTrue(exhaust)
        self.assertTrue(all(v["default_material"] == "Inconel751Study" for v in exhaust))

    def test_relative_asset_path_is_portable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layer = root / "stages" / "assembly.usda"
            asset = root / "assets" / "part.usdc"
            self.assertEqual(MODULE.relative_asset_path(layer, asset), "../assets/part.usdc")


if __name__ == "__main__":
    unittest.main()
