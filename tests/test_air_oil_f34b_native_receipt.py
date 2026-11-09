"""Preserve the independently read native English-generation receipts."""

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "containers/air-oil-cycle-f34b-en-20261106"


class NativeF34bReceiptTests(unittest.TestCase):
    def test_source_and_receipt_bytes_match_the_native_lock(self):
        lock = json.loads((BASE / "native-validation-20261107.lock.json").read_text())
        for relative, digest in lock["sources_sha256"].items():
            with self.subTest(source=relative):
                self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)
        for relative, expected in lock["receipts"].items():
            with self.subTest(receipt=relative):
                data = (BASE / relative).read_bytes()
                self.assertEqual(len(data), expected["size_bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected["sha256"])

    def test_native_readback_preserves_outputs_and_closed_authority(self):
        lock = json.loads((BASE / "native-validation-20261107.lock.json").read_text())
        original = json.loads((BASE / "generation.lock.json").read_text())
        directory = BASE / "native-validation-20261107"
        generation = json.loads((directory / "generation.json").read_text())
        smoke = json.loads((directory / "smoke.json").read_text())
        self.assertEqual(generation["outputs"], original["outputs"])
        self.assertEqual(generation["inputs_lock_sha256"], original["inputs_lock_sha256"])
        self.assertTrue(generation["numerical_inputs_and_authority_unchanged"])
        self.assertEqual(generation["canonical_doe_cases_executed"], 0)
        self.assertFalse(generation["physical_qualification"])
        self.assertEqual((directory / "image-identity.txt").read_text().split(),
                         [lock["image"]["config_id"], "linux/amd64", "9133:9133"])
        self.assertEqual(smoke["status"], "passed_embedded_f34b_preflight_and_generic_cantera_fixture_only")
        self.assertTrue(smoke["offline"])
        self.assertTrue(smoke["non_root"])
        self.assertTrue(smoke["network_isolation_evidence"]["verified"])
        self.assertFalse(any(smoke["physical_release_gates"].values()))
        solver = "scripts/run_917_air_oil_cycle_f34b.py"
        self.assertEqual(smoke["bundled_content_audit"]["files_sha256"][solver],
                         hashlib.sha256((ROOT / solver).read_bytes()).hexdigest())
        self.assertFalse(lock["image"]["published"])
        self.assertIsNone(lock["image"]["registry_digest"])
        self.assertFalse(lock["image"]["anonymous_registry_access_verified"])
        self.assertFalse(lock["verification"]["physical_qualification"])


if __name__ == "__main__":
    unittest.main()
