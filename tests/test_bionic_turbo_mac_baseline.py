"""Checks for the additive Mac runtime baseline; no solver is executed."""
import copy
import importlib.util
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "twins/bionic-turbo-f1/baseline-20261106-mac"
spec = importlib.util.spec_from_file_location("turbo_mac_baseline", BASE / "baseline.py")
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


class MacBaselineTests(unittest.TestCase):
    def test_parent_and_revision_validate_and_both_g01_attestations_match(self):
        self.assertEqual(baseline.check(), [])
        self.assertTrue(all(item["may_open"] for item in baseline.evaluate().values()))

    def test_substituted_binary_or_generator_cannot_open_execution_gate(self):
        parent = baseline.parent
        data = parent.load_baseline(BASE)
        original = parent.load_json(BASE / "G01-execution-contract-attestation.json")
        for changed in ("binary", "config"):
            with self.subTest(changed=changed):
                attestation = copy.deepcopy(original)
                if changed == "binary":
                    attestation["runtime"]["opencfd-v2406-runtime"]["executables"]["checkMesh"] = "0" * 64
                else:
                    key = next(key for key in attestation["config_sha256"] if key.endswith("prepare_case_v2.py"))
                    attestation["config_sha256"][key] = "0" * 64
                accepted, reasons = parent.evaluate_gate(
                    "G01-execution-contract", data["ledger"], data["matrix"], attestation)
                self.assertFalse(accepted)
                self.assertTrue(any("mismatch" in reason for reason in reasons))

    def test_readback_does_not_open_downstream_or_release_gates(self):
        data = baseline.parent.load_baseline(BASE)
        for gate in data["ledger"]["gates"]:
            self.assertNotEqual(gate["state"], "engineering_passed")
        self.assertEqual(
            data["ledger"]["paired_comparison_contract"],
            baseline.parent.load_baseline(baseline.PARENT)["ledger"]["paired_comparison_contract"],
        )


if __name__ == "__main__":
    unittest.main()
