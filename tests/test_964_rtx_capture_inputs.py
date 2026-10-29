"""RTX execution must reject incomplete, altered or escaping bundle inputs."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("capture_964", ROOT / "twins/964-chassis/monocoque/omniverse/capture_rtx.py")
CAPTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAPTURE)


class RTXInputsTests(unittest.TestCase):
    def test_missing_manifest_members_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = {"status": "passed_portable_usd_review_only", "manufacturing_authorized": False, "outputs_sha256": {}}
            (root / "validation.json").write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                CAPTURE.verify_inputs(root)

    def test_intact_bundle_accepted_and_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            names = ("monocoque.usda", "interior.usda", "geometry.usdc", "display.usda", "results.usda", "presentation.usda")
            for name in names:
                (root / name).write_bytes(name.encode())
            report = {"status": "passed_portable_usd_review_only", "manufacturing_authorized": False,
                      "outputs_sha256": {name: hashlib.sha256(name.encode()).hexdigest() for name in names}}
            (root / "validation.json").write_text(json.dumps(report))
            self.assertEqual(CAPTURE.verify_inputs(root), report)
            (root / names[0]).write_text("altered")
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                CAPTURE.verify_inputs(root)


if __name__ == "__main__":
    unittest.main()
