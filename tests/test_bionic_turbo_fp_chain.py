"""Checks for the G04 conversion chain of issue #397; no solver, mesher or container runs.

They cover the prescription (stages, bounds, branches), the static readback of
the pinned linux/arm64 runtime, the primary and independent readers, the
retained boxes and undecided determinants, and the G04 ledger revision
evaluated by the unchanged baseline evaluator.
"""
import ast
import contextlib
import copy
import importlib.util
import io
import json
import math
import random
import struct
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins/bionic-turbo-f1"
HERE = TWIN / "fp-chain-20261118"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fp = _load("turbo_fp_chain", HERE / "fpchain.py")
reader = _load("turbo_fp_reader", HERE / "independent_reader.py")

GATE = "G04-native-fp-execution"
BLOCKERS = ["pinned-binary-not-executed", "no-admissible-native-input",
            "criterion-sensitivity-and-conditioning-not-certified", "compiler-and-options-not-pinned"]


class GateTests(unittest.TestCase):
    def test_committed_revision_validates(self):
        self.assertEqual(fp.check_all(), [])

    def test_prerequisites_pass_by_the_unchanged_evaluator(self):
        recorded = fp.load("prerequisites")
        for gate in ("G01-baseline-frozen", "G01-execution-contract", "G02-evidence-recoverable"):
            self.assertEqual(recorded["gate_states"][gate], "engineering_passed")
            self.assertEqual(recorded["evaluations"][gate], {"may_open": True, "reasons": []})
        self.assertFalse(recorded["downstream_geometry_solver_and_release_authorized"])

    def test_only_g04_changes_and_it_keeps_its_blockers(self):
        parent = json.loads((ROOT / fp.PARENT_LEDGER).read_text())
        ledger = fp.load("ledger")
        self.assertEqual(fp.check_gate_ledger(ledger), [])
        for old, new in zip(parent["gates"], ledger["gates"], strict=True):
            if old["id"] != GATE:
                self.assertEqual(old, new)
        gate = next(g for g in ledger["gates"] if g["id"] == GATE)
        self.assertEqual(gate["state"], "investigated")
        self.assertEqual([b["id"] for b in gate["blockers"]], BLOCKERS)
        self.assertEqual([b["id"] for b in gate["resolved_blockers"]], ["conversion-chain-not-prescribed"])
        dropped = copy.deepcopy(ledger)
        target = next(g for g in dropped["gates"] if g["id"] == GATE)
        target["blockers"] = target["blockers"][1:]
        self.assertTrue(any("lost blockers" in e for e in fp.check_gate_ledger(dropped)))
        forced = copy.deepcopy(ledger)
        target = next(g for g in forced["gates"] if g["id"] == GATE)
        target["state"], target["blockers"] = "engineering_passed", []
        self.assertTrue(fp.check_gate_ledger(forced))

    def test_unchanged_evaluator_refuses_g04_for_its_blockers_only(self):
        verdict = fp.evaluate_gate()
        self.assertFalse(verdict["may_open"])
        self.assertEqual(verdict["reasons"], [f"open blocker: {b}" for b in BLOCKERS])
        self.assertEqual(verdict, fp.load("evaluation"))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(fp.main(["gate"]), 1)
        self.assertIn("stays closed", out.getvalue())

    def test_substituted_runtime_is_refused_even_without_blockers(self):
        ledger, matrix = fp.load("ledger"), json.loads((ROOT / fp.MATRIX).read_text())
        gate = next(g for g in ledger["gates"] if g["id"] == GATE)
        gate["blockers"] = []
        attestation = fp.load("attestation")
        accepted, reasons = fp.parent().evaluate_gate(GATE, ledger, matrix, attestation, ROOT)
        self.assertTrue(accepted, reasons)
        amd64 = copy.deepcopy(attestation)
        row = amd64["runtime"][fp.ROW]
        row["platform"] = "linux/amd64"
        row["identity"]["image"] = ("docker.io/opencfd/openfoam-run@sha256:"
                                    "32c0541bc3577916a6ddae618ad12d5082a40702249e101358a3f078bcc7f722")
        accepted, reasons = fp.parent().evaluate_gate(GATE, ledger, matrix, amd64, ROOT)
        self.assertFalse(accepted)
        self.assertTrue(any("platform substituted" in r for r in reasons))
        self.assertTrue(any("identity.image mismatch" in r for r in reasons))

    def test_dependent_gate_g05_stays_closed(self):
        ledger, matrix = fp.load("ledger"), json.loads((ROOT / fp.MATRIX).read_text())
        accepted, reasons = fp.parent().evaluate_gate(
            "G05-full-geometry", ledger, matrix, {"gate": "G05-full-geometry", "receipts": []}, ROOT)
        self.assertFalse(accepted)
        self.assertIn(f"prerequisite {GATE} is investigated, not engineering_passed", reasons)

    def test_attestation_claims_no_execution_and_matches_the_readback(self):
        attestation, readback, ledger = fp.load("attestation"), fp.load("readback"), fp.load("ledger")
        self.assertEqual(fp.check_attestation(attestation, readback, ledger), [])
        executed = copy.deepcopy(attestation)
        executed["execution_host"] = "Mac arm64; checkMesh executed"
        self.assertTrue(fp.check_attestation(executed, readback, ledger))


class RuntimeReadbackTests(unittest.TestCase):
    def test_static_readback_matches_the_pinned_row(self):
        readback, contract = fp.load("readback"), fp.load("contract")
        self.assertEqual(fp.check_readback(readback, contract), [])
        self.assertTrue(all(readback["checks"].values()))
        self.assertEqual(readback["config"]["architecture"], "arm64")
        lib = readback["libOpenFOAM"]
        self.assertLessEqual({"strtold", "__trunctfdf2"}, set(lib["imports_of_interest"]))
        self.assertEqual(lib["fe_environment_imports"], ["fedisableexcept", "feenableexcept"])
        self.assertTrue(all(c["equal"] for c in lib["exported_constants"]))
        self.assertGreater(sum(f["fused_total"] for f in lib["geometry_functions"]), 0)
        self.assertEqual(readback["checkMesh"]["comment"], [])

    def test_a_tampered_executable_hash_is_refused(self):
        readback, contract = fp.load("readback"), fp.load("contract")
        bad = copy.deepcopy(readback)
        bad["pinned_executables"]["checkMesh"]["observed"] = "0" * 64
        bad["checkMesh"]["sha256"] = "0" * 64
        self.assertTrue(any("checkMesh" in e for e in fp.check_readback(bad, contract)))

    def test_fused_instruction_classifier(self):
        readback_module = _load("turbo_fp_readback", HERE / "readback_image.py")
        self.assertEqual(readback_module.classify(0x1F420C20), "fmadd.double")   # fmadd d0, d1, d2, d3
        self.assertEqual(readback_module.classify(0x1F628C20), "fnmsub.double")  # fnmsub d0, d1, d2, d3
        self.assertEqual(readback_module.classify(0x4E62CC20), "fmla.vector.double")
        self.assertIsNone(readback_module.classify(0x1E622820))                  # fadd d0, d1, d2


class ConversionTests(unittest.TestCase):
    def test_native_reader_double_rounds_through_binary128(self):
        read = fp.s2_read("1.000000000000000111022302462515654043")
        self.assertEqual(read["branch"], "scalar")
        self.assertEqual(read["x"], 1.0)
        self.assertTrue(read["double_rounding_discrepancy"])
        self.assertEqual(float("1.000000000000000111022302462515654043"), 1.0000000000000002)

    def test_vsmall_is_lost_in_a_writeprecision_16_cycle(self):
        vsmall = float(fp.VSMALL64)
        self.assertEqual(fp.s3_write(vsmall), "1e-300")
        self.assertEqual("%.17g" % vsmall, "1e-300")
        self.assertEqual(fp.s2_read("1e-300")["branch"], "zero")
        self.assertEqual(fp.s2_read("1.000000000000001e-300")["branch"], "scalar")
        self.assertEqual(fp.s2_read("-0.0")["x_bits"], fp.bits(0.0))
        self.assertEqual(fp.s2_read("1.000000000000001e+300")["branch"], "range-refusal")
        self.assertEqual(fp.s2_read("1" * 128)["branch"], "length-refusal")

    def test_sixteen_digits_do_not_round_trip(self):
        x = 0.1 + 0.2
        self.assertNotEqual(fp.s2_read(fp.s3_write(x))["x"], x)
        text = "9007199254740993"
        self.assertNotEqual(fp.s3_write(fp.s2_read(text)["x"]), text)

    def test_formatters_agree_with_cpython_on_sampled_binary64(self):
        rng = random.Random(397)
        for _ in range(3000):
            x = struct.unpack("<d", struct.pack("<Q", rng.getrandbits(64) & 0x7FEFFFFFFFFFFFFF))[0]
            if x == 0 or not math.isfinite(x):
                continue
            x = -x if rng.random() < 0.5 else x
            self.assertEqual(fp.dec16(Fraction(x))[0], "%.16g" % x)
            self.assertEqual(reader.decimal16(Fraction(x))[0], "%.16g" % x)

    def test_double_rounding_lemma_holds_on_sampled_sixteen_digit_texts(self):
        rng = random.Random(1997)
        for _ in range(1500):
            digits = rng.randrange(10 ** 15, 10 ** 16)
            exponent = rng.randrange(-10, 19)
            text = f"{digits // 10 ** 15}.{digits % 10 ** 15:015d}e{exponent}"
            read = fp.s2_read(text)
            self.assertTrue(read["lemma"], text)
            self.assertFalse(read["double_rounding_discrepancy"], text)

    def test_independent_emulation_matches_hardware(self):
        rng = random.Random(2406)
        for _ in range(400):
            a, b, c = (rng.uniform(-1, 1) * 10 ** rng.randint(-8, 8) for _ in range(3))
            fa, fb, fc = (reader.F.exact(Fraction(v)) for v in (a, b, c))
            self.assertEqual(reader.mul(fa, fb).bits(), fp.bits(a * b))
            self.assertEqual(reader.sub(fa, fb).bits(), fp.bits(a - b))
            self.assertEqual(reader.div(fa, fb).bits(), fp.bits(a / b))
            self.assertEqual(reader.sqrt(reader.F.exact(Fraction(abs(a)))).bits(), fp.bits(math.sqrt(abs(a))))
            self.assertEqual(reader.fma(fa, fb, fc).bits(), fp.bits(fp.fma(a, b, c)))
        zero = reader.F(0, Fraction(0))
        self.assertEqual(reader.sub(zero, zero).bits(), fp.bits(0.0 - 0.0))
        self.assertEqual(reader.mul(reader.F.exact(Fraction(-1)), zero).bits(), fp.bits(-1.0 * 0.0))


class ReceiptTests(unittest.TestCase):
    def test_every_witness_class_is_exhibited_and_bounds_hold(self):
        receipt, contract = fp.load("conversions"), fp.load("contract")
        self.assertEqual(receipt["status"], "passed")
        for name in contract["witness_classes"]:
            self.assertTrue(receipt["coverage"][name], name)
        self.assertTrue(all(receipt["acceptance"].values()))
        self.assertFalse(receipt["findings"]["vsmall64_survives_native_cycle"])

    def test_exact_cancellation_is_not_a_floating_point_cancellation(self):
        summary = fp.load("conversions")["reference_summary"]
        self.assertTrue(summary["cell_closures_exact_zero"])
        self.assertGreater(summary["cell_closures_floating_nonzero"], 0)
        self.assertGreater(summary["boundary_floating_nonzero"], 0)
        self.assertTrue(summary["cell_closures_within_bound"] and summary["boundary_within_bound"])
        self.assertGreater(summary["fused_differs_from_unfused"], 0)
        self.assertTrue(summary["all_within_bound"])

    def test_undecided_branches_are_kept(self):
        summary = fp.load("conversions")["reference_summary"]
        self.assertEqual(summary["guard_decisions"],
                         {"GF-below": ["active"], "GF-near": ["undecided"], "GF-above": ["inactive"]})
        margins = fp.load("conversions")["certificates"]["margins"]
        self.assertTrue(all(m["native_decision"].startswith("undecided") for m in margins))
        self.assertTrue(all(m["certified_side"] for m in margins))

    def test_boxes_endpoints_and_undecided_determinants_are_retained(self):
        retained = fp.load("conversions")["certificates"]["retained"]
        self.assertEqual((retained["boxes"], retained["first_leaf"], retained["last_leaf"]), (153, 1778, 1930))
        self.assertTrue(retained["all_kept"])
        self.assertEqual(retained["undecided_determinant_leaves"], [1929, 1930])
        self.assertFalse(retained["point_selected"])
        contract = fp.load("contract")
        shrunk = copy.deepcopy(contract)
        shrunk["retained"]["boxes"] = 151
        thr = fp.load("conversions")["thresholds"]["non_orthogonality_cosine"]["bracket"]
        self.assertFalse(fp.certificates(shrunk, thr)["retained"]["all_kept"])

    def test_a_stale_certificate_is_refused(self):
        contract = copy.deepcopy(fp.load("contract"))
        contract["certificates"][0]["sha256"] = "0" * 64
        with self.assertRaises(fp.ChainError):
            fp.certificate(contract, contract["certificates"][0]["id"])

    def test_independent_reader_confirms_and_detects_tampering(self):
        tree = ast.parse((HERE / "independent_reader.py").read_text())
        imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imported |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertFalse({name for name in imported if name and "fpchain" in name})
        self.assertNotIn("importlib", imported)
        result = reader.run()
        self.assertEqual(result["status"], "passed")
        self.assertGreater(result["comparisons"], 1000)
        receipt = fp.load("conversions")
        bad = copy.deepcopy(receipt)
        bad["references"]["cells"][1]["faces"][0]["patterns"]["F1"]["A_bits"][0] = "0x0000000000000001"
        bad["witnesses"]["texts"][0]["S2"]["branch"] = "scalar"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "conversion-receipt.json"
            path.write_text(json.dumps(bad))
            with patch.object(reader, "PRIMARY", path):
                tampered = reader.run()
        self.assertEqual(tampered["status"], "failed")
        self.assertTrue(any("RC2-rotated-cube.face0.F1.bits" in m for m in tampered["mismatches"]))
        self.assertTrue(any("text-1e-300.S2.branch" in m for m in tampered["mismatches"]))


if __name__ == "__main__":
    unittest.main()
