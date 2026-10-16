"""Reference and rejection tests; synthetic CSV fixtures are not native evidence."""
import copy
import base64
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "twins/962-cylinder-head-f0/source/physics_witness"
SPEC = importlib.util.spec_from_file_location("physics_witness", SOURCE / "assess.py")
WITNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WITNESS)


class PhysicsWitnessTest(unittest.TestCase):
    def setUp(self):
        self.card = json.loads((SOURCE / "hypothetical-material.json").read_text())
        self.rows = [{"time": r["time"], **r["fields"]} for r in WITNESS.reference(self.card)]
        self.contract = {"frozen_before_native_run": True, "classification": self.card["classification"],
            "source_sha256": {name: WITNESS.sha256(SOURCE / name) for name in
                ("variable-thermoelastic.i", "variable-yield.i", "hypothetical-material.json", "assess.py")},
            "predeclared_absolute_tolerances": copy.deepcopy(self.card["predeclared_absolute_tolerances"]),
            "elastic_reference": WITNESS.reference(self.card),
            "plastic_reference": WITNESS.reference(self.card, plastic=True)}

    def assess_rows(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.csv"
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=self.rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            return WITNESS.assess(path, self.card, self.contract)

    def test_mean_cte_length_reference_is_distinct_from_stress_free_reference(self):
        hot = WITNESS.reference(self.card)[3]
        # L(600)/L(250)=1.0056 and L(300)/L(250)=1.0005.
        self.assertAlmostEqual(hot["thermal_strain"], 0.0051 / 1.0005, places=15)
        self.assertAlmostEqual(hot["fields"]["stress_zz_max"], -764.6176911544229, places=9)
        self.assertAlmostEqual(hot["fields"]["disp_y_max"], 0.0131514242878561, places=14)

    def test_perfect_j2_cooling_keeps_history_and_reverses_yield(self):
        rows = WITNESS.reference(self.card, plastic=True)
        self.assertEqual(rows[2]["fields"]["stress_zz_min"], -250.0)
        self.assertEqual(rows[3]["fields"]["stress_zz_min"], -225.0)
        self.assertEqual(rows[5]["fields"]["stress_zz_min"], 275.0)
        self.assertEqual(rows[6]["fields"]["stress_zz_min"], 300.0)
        self.assertAlmostEqual(rows[6]["fields"]["plastic_zz_min"], -1.0 / 700.0, places=15)

    def test_complete_fixture_passes_field_checker(self):
        result = self.assess_rows(self.rows)
        self.assertTrue(result["passed"])
        self.assertEqual(result["checks_count"], 140)

    def test_corrupted_transverse_field_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[3]["stress_xx_max"] = 0.001
        self.assertFalse(self.assess_rows(rows)["passed"])

    def test_nonfinite_displacement_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[3]["disp_y_max"] = float("nan")
        self.assertFalse(self.assess_rows(rows)["passed"])

    def test_missing_time_is_rejected(self):
        with self.assertRaises(ValueError):
            self.assess_rows(self.rows[:-1])

    def test_duplicate_time_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[3]["time"] = 2.0
        with self.assertRaises(ValueError):
            self.assess_rows(rows)

    def test_physical_material_label_is_rejected(self):
        self.card["classification"] = "PHYSICAL_MATERIAL"
        with self.assertRaises(ValueError):
            self.assess_rows(self.rows)

    def proof_fixture(self, mutate=None, plastic=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mode = "plastic" if plastic else "elastic"
            path = root / (mode + "-fixture")
            path.mkdir()
            inputs = {name: (SOURCE / name).read_bytes() for name in
                      ("variable-thermoelastic.i", "hypothetical-material.json")}
            if plastic:
                inputs["variable-yield.i"] = (SOURCE / "variable-yield.i").read_bytes()
            for name, content in inputs.items():
                (path / name).write_bytes(content)
            log = b"Solve Converged!\n" * 6
            (path / "native.log").write_bytes(log)
            receipt = {"returncode": 0, "binary_sha256": self.card["native_binary_sha256"],
                       "binary_unchanged": True, "inputs_unchanged": True,
                       "wall_seconds": 1.0, "deadline_seconds": 100,
                       "input_sha256": {name: hashlib.sha256(content).hexdigest()
                                        for name, content in inputs.items()},
                       "log_sha256": hashlib.sha256(log).hexdigest()}
            (path / "native-execution.json").write_text(json.dumps(receipt))
            csv_name = ("variable-yield" if plastic else "variable-thermoelastic") + "_out.csv"
            (path / csv_name).write_text("synthetic CSV capture fixture, not native evidence\n")
            (path / (csv_name[:-4] + ".e")).write_bytes(b"synthetic Exodus capture fixture")
            names = list(inputs) + ["native.log", "native-execution.json", csv_name, csv_name[:-4] + ".e"]
            captured = {**receipt, "artifacts_base64": {name: base64.b64encode(
                (path / name).read_bytes()).decode() for name in names}}
            stdout_sha = hashlib.sha256((json.dumps(captured) + "\n").encode()).hexdigest()
            (path / "ssh-execution.json").write_text(json.dumps(dict(returncode=0, stdout_sha256=stdout_sha)))
            contract_path = root / "predeclared-contract.json"
            contract_path.write_text(json.dumps(self.contract))
            manifest = {"classification": self.card["classification"],
                "predeclared_contract_sha256": WITNESS.sha256(contract_path), "runs": {mode: {
                    "directory": path.name, "artifact_order": names,
                    "artifacts_sha256": {name: WITNESS.sha256(path / name) for name in names},
                    "native_execution_sha256": WITNESS.sha256(path / "native-execution.json"),
                    "ssh_execution_sha256": WITNESS.sha256(path / "ssh-execution.json"),
                    "ssh_stdout_sha256": stdout_sha}}}
            if mutate:
                mutate(path, receipt)
                (path / "native-execution.json").write_text(json.dumps(receipt))
            return WITNESS.native_proof(path / csv_name, self.card, self.contract,
                                        manifest, contract_path, plastic)

    def test_complete_execution_fixture_passes_receipt_checker(self):
        self.assertTrue(self.proof_fixture()["passed"])
        self.assertTrue(self.proof_fixture(plastic=True)["passed"])

    def test_wrong_runtime_is_rejected(self):
        self.assertFalse(self.proof_fixture(lambda path, r: r.update(binary_sha256="wrong"))["passed"])

    def test_changed_input_is_rejected(self):
        self.assertFalse(self.proof_fixture(
            lambda path, r: (path / "variable-thermoelastic.i").write_text("changed"))["passed"])

    def test_missing_equilibrium_step_is_rejected(self):
        def remove_step(path, receipt):
            content = b"Solve Converged!\n" * 5
            (path / "native.log").write_bytes(content)
            receipt["log_sha256"] = hashlib.sha256(content).hexdigest()
        self.assertFalse(self.proof_fixture(remove_step)["passed"])

    def test_changed_native_csv_is_rejected_by_original_capture(self):
        result = self.proof_fixture(lambda path, receipt:
            (path / "variable-thermoelastic_out.csv").write_text("different fields"))
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["capture_artifact_hashes"])
        self.assertFalse(result["checks"]["original_ssh_capture"])

    def test_changed_frozen_reference_and_loosened_tolerances_are_rejected(self):
        self.contract["elastic_reference"][3]["fields"]["stress_zz_min"] += 1
        with self.assertRaisesRegex(ValueError, "predeclared"):
            self.assess_rows(self.rows)
        self.setUp()
        self.card["predeclared_absolute_tolerances"]["stress_MPa"] = 1
        with self.assertRaisesRegex(ValueError, "tolerances changed"):
            self.assess_rows(self.rows)

    def test_changed_law_or_units_cannot_redefine_the_frozen_witness(self):
        self.card["youngs_modulus_slope_MPa_per_K"] = -199
        with self.assertRaisesRegex(ValueError, "predeclared"):
            self.assess_rows(self.rows)
        self.setUp()
        self.card["units"]["temperature"] = "degC"
        with self.assertRaisesRegex(ValueError, "unchanged units"):
            self.assess_rows(self.rows)

    def test_native_inputs_must_match_the_predeclared_input_hashes(self):
        self.contract["source_sha256"]["variable-thermoelastic.i"] = "0" * 64
        result = self.proof_fixture()
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["native_inputs_frozen_before_run"])

    def test_cli_refuses_to_overwrite_previous_assessment(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "assessment.json"
            output.write_text("previous evidence")
            result = subprocess.run([sys.executable, str(SOURCE / "assess.py"),
                str(Path(directory) / "missing.csv"), "--output", str(output)],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), "previous evidence")
            self.assertIn("output must be new", result.stderr)


if __name__ == "__main__":
    unittest.main()
