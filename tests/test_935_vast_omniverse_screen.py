import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import base64

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "twins/935-horizontal-cooling-system-f0/vast-omniverse-screen"
SOURCE = SCREEN / "source/run_campaign.py"
TRANSFER = ROOT / "deploy/vast/simready/transfer-935-screen.sh"
spec = importlib.util.spec_from_file_location("screen_campaign", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ScreenContractTests(unittest.TestCase):
    def test_material_cards_cover_ten_distinct_families_and_preserve_we43_unknown(self):
        cards, scenario = module.load_inputs(SCREEN)
        self.assertEqual(len(cards["materials"]), 10)
        self.assertEqual(len({item["id"] for item in cards["materials"]}), 10)
        self.assertIsNone(next(item for item in cards["materials"] if item["id"] == "we43")["yield_comparator_MPa"])
        self.assertFalse(scenario["geometry"]["interfaces_verified"])

    def test_input_contract_keeps_unreviewed_935_values_out_of_the_proxy(self):
        contract = module.load_input_contract(SCREEN)
        self.assertEqual(contract["matrix_rows"], 50)
        self.assertEqual(contract["separate_variants"], 6)
        self.assertEqual(contract["accepted_935_numeric_physical_claims"], 0)
        self.assertFalse(contract["physical_claims_consumed"])

    def test_transfer_includes_the_input_contract_needed_by_the_runner(self):
        transfer = TRANSFER.read_text(encoding="utf-8")
        self.assertIn('INPUT_CONTRACT="twins/935-horizontal-cooling-system"', transfer)
        self.assertIn('"$INPUT_CONTRACT/data/input-matrix.json"', transfer)
        self.assertIn('"$INPUT_CONTRACT/research/coverage.json"', transfer)

    def test_ovrtx_renderer_is_limited_to_the_local_service(self):
        self.assertEqual(module.require_ovrtx_endpoint("http://127.0.0.1:8001"), "http://127.0.0.1:8001")
        with self.assertRaisesRegex(ValueError, "local loopback"):
            module.require_ovrtx_endpoint("https://renderer.example/preview")

    def test_ovrtx_renderer_saves_a_hashed_preview(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return json.dumps({"status": "success", "images": {"0": {
                    "/FanAlloyScreen/Camera": {"rgb": base64.b64encode(b"x" * 1025).decode("ascii")}
                }}}).encode("utf-8")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = root / "screen.usda"
            stage.write_text("#usda 1.0\n", encoding="utf-8")
            with mock.patch.object(module.urllib.request, "urlopen", return_value=Response()):
                render = module.render_ovrtx(stage, root, "http://127.0.0.1:8001")
            self.assertEqual(render["status"], "passed")
            self.assertEqual(render["image"]["bytes"], 1025)
            self.assertRegex(render["image"]["sha256"], r"^[0-9a-f]{64}$")

    def test_invalid_duplicate_material_is_rejected_before_solver(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cards = json.loads((SCREEN / "materials.json").read_text())
            cards["materials"][1]["id"] = cards["materials"][0]["id"]
            (root / "materials.json").write_text(json.dumps(cards))
            (root / "scenario.json").write_text((SCREEN / "scenario.json").read_text())
            with self.assertRaises(ValueError):
                module.load_inputs(root)

    def test_readme_has_no_fabrication_or_fitment_claim(self):
        text = (SCREEN / "README.md").read_text().lower()
        self.assertIn("pas le scan privé", text)
        self.assertIn("aucun résultat ne prouve", text)
        self.assertIn("aptitude à fabriquer", text)

if __name__ == "__main__":
    unittest.main()
