"""Native scalar controls retain gaps in the full turbo arithmetic proof."""

from copy import deepcopy
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "twins/bionic-turbo-f1/fp-contract-20261106"
spec = importlib.util.spec_from_file_location("scalar_reader", HERE / "verify_scalars.py")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


def load(name):
    return json.loads((HERE / name).read_text())


class TurboFPContractTests(unittest.TestCase):
    def test_native_controls_and_independent_receipts(self):
        for cases_name, native_name, independent_name in (
            ("scalar-cases.json", "native-scalar-receipt.json", "independent-scalar-receipt.json"),
            ("supplement-cases.json", "supplement-native-receipt.json", "supplement-independent-receipt.json"),
        ):
            native, independent = load(native_name), load(independent_name)
            result = reader.verify(load(cases_name), native)
            self.assertEqual(result["controls"], independent["controls"])
            self.assertFalse(result["full_conversion_or_arithmetic_qualification"])
            self.assertFalse(native["engineering_gate_passed"])
            self.assertFalse(native["geometry_or_solver_executed"])
            for name, expected in ((cases_name, native["cases_sha256"]),
                                   (native_name, independent["native_receipt_sha256"]),
                                   ("verify_scalars.py", independent["reader_sha256"]),
                                   ("source-bindings.json", native["source_bindings_sha256"])):
                self.assertEqual(hashlib.sha256((HERE / name).read_bytes()).hexdigest(), expected)
        for name, native, field in (("SCALAR-PLAN.md", "native-scalar-receipt.json", "plan_sha256"),
                                    ("SCALAR-RETRY.md", "native-scalar-receipt.json", "retry_plan_sha256"),
                                    ("SUPPLEMENT-PLAN.md", "supplement-native-receipt.json", "plan_sha256")):
            self.assertEqual(hashlib.sha256((HERE / name).read_bytes()).hexdigest(), load(native)[field])

    def test_true_normal_and_exact_binary64_counterexample(self):
        cases = load("supplement-cases.json")
        self.assertGreater(Fraction(cases[0]["input"]), Fraction(1, 2**1022))
        self.assertEqual(Fraction(cases[1]["input"]), 1 + Fraction(1, 2**52))
        runs = load("supplement-native-receipt.json")["runs"]
        self.assertEqual(Fraction(runs[0]["stdout"]), 0)
        self.assertEqual(Fraction(runs[1]["stdout"]), 1)
        self.assertEqual(load("supplement-independent-receipt.json")["precision16_roundtrip_loss"], str(Fraction(1, 2**52)))

    def test_failed_setup_and_corrupted_controls_are_rejected(self):
        cases, native = load("scalar-cases.json"), load("native-scalar-receipt.json")
        with self.assertRaisesRegex(ValueError, "setup diagnostic"):
            reader.verify(cases, load("scalar-first-attempt.json"))
        for mutation in ("missing", "duplicate", "precision", "input", "unexpected-warning", "nonzero-tiny", "accepted-overflow"):
            with self.subTest(mutation=mutation):
                bad = deepcopy(native)
                if mutation == "missing": bad["runs"].pop()
                elif mutation == "duplicate": bad["runs"][1] = bad["runs"][0]
                elif mutation == "precision": bad["precision"] = 17
                elif mutation == "input": bad["runs"][0]["input_sha256"] = "0" * 64
                elif mutation == "unexpected-warning": bad["runs"][0]["stderr"] += "unexpected warning"
                elif mutation == "nonzero-tiny": bad["runs"][2]["stdout"] = "1e-324"
                else: bad["runs"][-1]["exit_code"] = 0
                with self.assertRaises(ValueError): reader.verify(cases, bad)

    def test_source_recovery_and_runtime_logs_remain_bound(self):
        recovered = load("source-recovery.json")
        self.assertEqual(recovered["files"], 26)
        self.assertTrue(recovered["independent_shasum_verified"])
        self.assertFalse(recovered["programs_executed"])
        runtime = load("runtime-preflight.json")
        self.assertIsNone(runtime["actual_compiler_flags"])
        self.assertIsNone(runtime["rounding_mode_observed"])
        self.assertFalse(runtime["engineering_gate_passed"])
        self.assertEqual(len(runtime["resolved_library_sha256"]), 22)
        for log in runtime["logs"]:
            self.assertEqual(hashlib.sha256((HERE / log["name"]).read_bytes()).hexdigest(), log["sha256"])


if __name__ == "__main__":
    unittest.main()
