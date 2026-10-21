"""Independent normalization/enthalpy invariants; no synthetic fixture is native proof."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "twins/962-cylinder-head-f0/source/physics_witness/thermal_birth"
SPEC = importlib.util.spec_from_file_location("thermal_birth", SOURCE / "assess.py")
WITNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WITNESS)
REFINEMENT_SPEC = importlib.util.spec_from_file_location("thermal_refinement", SOURCE / "assess_refinement.py")
REFINEMENT = importlib.util.module_from_spec(REFINEMENT_SPEC)
REFINEMENT_SPEC.loader.exec_module(REFINEMENT)


class ThermalBirthTest(unittest.TestCase):
    def setUp(self):
        self.card = json.loads((SOURCE / "card.json").read_text())

    def test_full_space_and_half_space_power_normalization(self):
        card = copy.deepcopy(self.card)
        card["bounds_m"] = [[-10, -10, -10], [10, 10, 10]]
        card["source_start_m"] = [0, 0, 0]
        self.assertEqual(WITNESS.box_power(card, 0, 10), 40.0)
        card["bounds_m"][0][0] = 0
        self.assertEqual(WITNESS.box_power(card, 0, 10), 20.0)

    def test_nonlinear_enthalpy_uses_integrated_capacity(self):
        self.assertEqual(WITNESS.enthalpy_density(self.card, 350), 112.5)
        self.assertEqual(WITNESS.enthalpy_density(self.card, 400), 250.0)
        self.assertEqual(WITNESS.enthalpy_density(self.card, 410) - 250, 30.5)
        # Endpoint cp(410)*10 = 31; backward Euler's capacity correction is 0.5.
        self.assertEqual(3.1 * 10 - 0.5 * 0.01 * 10**2, 30.5)

    def test_shared_interface_birth_energy_is_not_uniform_block_energy(self):
        field = {}
        for lo, h, corners in WITNESS.grid(self.card, 2):
            for point in corners:
                field[point] = 400.0 if point[0] <= 1 else 350.0
        initial = {point: value for point, value in field.items() if point[0] <= 1}
        birth = WITNESS.integrals(self.card, field, 2) - WITNESS.integrals(self.card, initial, 1)
        self.assertAlmostEqual(birth, 112.5 + 25.0/3.0, places=10)

    def test_moving_source_tracks_declared_center(self):
        first = WITNESS.source_value(self.card, [0.4, 0.5, 0.5], 0)
        moved = WITNESS.source_value(self.card, [1.6, 0.5, 0.5], 0.4)
        self.assertAlmostEqual(first, moved, places=12)
        self.assertLess(WITNESS.source_value(self.card, [0.4, 0.5, 0.5], 0.4), first/100)

    def test_temperature_increment_quadrature_is_exact(self):
        field = {}
        for lo, h, corners in WITNESS.grid(self.card, 1):
            for point in corners:
                field[point] = 400.0
        after = {point: value + 10 for point, value in field.items()}
        self.assertAlmostEqual(WITNESS.integrals(self.card, after, 1, field), 100, places=11)

    def test_nonfinite_native_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "field.csv"
            path.write_text("x,y,z,id,temperature\n0,0,0,0,nan\n")
            with self.assertRaises(ValueError):
                WITNESS.csv_rows(path)

    def test_existing_assessment_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing.json"
            output.write_text("immutable\n")
            result = subprocess.run([sys.executable, "-B", str(SOURCE / "assess.py"), "missing",
                                     "--contract", "missing", "--output", str(output)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), "immutable\n")

    def refinement_fixture(self, errors, wrong_assessor=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = root / "contract.json"
            contract.write_text(json.dumps({"card": self.card, "assessor_sha256": "frozen"}))
            paths = []
            for level, error in enumerate(errors):
                path = root / f"level-{level}.json"
                path.write_text(json.dumps({"passed": True, "level": level,
                    "dt_s": self.card["time_steps_s"][level], "frozen_contract_sha256": WITNESS.sha(contract),
                    "assessor_sha256": "changed" if wrong_assessor else "frozen",
                    "max_continuous_relative_energy_error": error, "checks_count": 1,
                    "max_error_by_check": {}, "native_receipt_sha256": "unit_fixture_only", "traces": [{}]}))
                paths.append(path)
            return REFINEMENT.assess(contract, paths)

    def test_refinement_gate_passes_decreasing_fixture(self):
        self.assertTrue(self.refinement_fixture([0.02, 0.01, 0.005])["passed"])

    def test_refinement_gate_rejects_weak_convergence(self):
        self.assertFalse(self.refinement_fixture([0.006, 0.005, 0.004])["passed"])

    def test_missing_refinement_level_is_rejected(self):
        with self.assertRaises(ValueError):
            self.refinement_fixture([0.02, 0.01])

    def test_changed_frozen_assessor_is_rejected(self):
        with self.assertRaises(ValueError):
            self.refinement_fixture([0.02, 0.01, 0.005], wrong_assessor=True)

    def test_invalid_refinement_errors_cannot_pass_the_ratio_gate(self):
        for invalid in (float('inf'),float('-inf'),float('nan'),-0.02,True,None,'0.02',10**400):
            with self.subTest(error=invalid), self.assertRaisesRegex(ValueError,'finite nonnegative'):
                self.refinement_fixture([invalid,0.01,0.005])

    def test_zero_denominator_and_ratio_overflow_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'zero denominator'):
            self.refinement_fixture([0.02,0.01,0])
        with self.assertRaisesRegex(ValueError,'ratios must remain finite'):
            self.refinement_fixture([1e308,1e-308,1e-309])
        self.assertFalse(self.refinement_fixture([0,0.01,0.005])['passed'])


if __name__ == "__main__":
    unittest.main()
