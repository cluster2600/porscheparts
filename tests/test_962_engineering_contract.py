"""Manufacturer points and research assumptions never become qualified head data."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "twins/962-cylinder-head-f0/engineering"
spec = importlib.util.spec_from_file_location("head_engineering_contract", FOLDER / "validate_contract.py")
engineering = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engineering)


class EngineeringContractTests(unittest.TestCase):
    def setUp(self):
        self.materials = json.loads((FOLDER / "materials.json").read_text())
        self.contract = json.loads((FOLDER / "input-contract.json").read_text())

    def research_fixture(self):
        # Synthetic validator fixture only; these numbers are never solver inputs.
        values = (1, .25, 1e-6, 20, 21, 1, 1)
        self.contract["material_recipe_id"] = self.materials["recipes"][0]["id"]
        for entry, value in zip(self.contract["research_inputs"].values(), values):
            entry.update(value=value, basis="research_assumption",
                         source={"reference": "unit-test-only", "locator": "research_fixture"},
                         reason="Synthetic input-validation fixture, not an engineering scenario")
        self.contract["fixture_definition"] = dict(reference="unit-test-only", locator="fixture",
            basis="research_assumption", reason="No actual restraint or attachment is asserted")

    def test_current_contract_binds_four_native_geometries_and_stays_incomplete(self):
        result = engineering.validate(self.contract, self.materials)
        self.assertEqual(result["geometry_variants"], 4)
        self.assertEqual(result["material_recipes"], 7)
        self.assertFalse(result["research_inputs_ready"])
        self.assertIn("material_recipe_id", result["missing_research_inputs"])
        self.assertIn("evidence:professional_engineering_review", result["missing_qualification_inputs"])
        self.assertFalse(any(result["qualification"].values()))
        self.assertTrue(all(value is None for value in self.materials["missing_laws"].values()))

    def test_manufacturer_rows_preserve_machine_treatment_and_orientation(self):
        recipes = engineering.validate_materials(self.materials)
        cp1 = recipes["cp1-400c-4h-vertical-machine-unspecified"]
        self.assertIsNone(cp1["machine_model"])
        self.assertIsNone(cp1["layer_thickness_um"])
        self.assertEqual(cp1["thermal_conductivity_W_mK"]["value"], 187)
        self.assertEqual(cp1["tensile_points"][0]["yield_MPa"], 323)
        ht1 = recipes["ht1-treatment-1-m290-60um-vertical"]
        ht2 = recipes["ht1-treatment-2-m290-60um-vertical"]
        self.assertEqual([p["yield_MPa"] for p in ht1["tensile_points"]], [425, 238, 188])
        self.assertEqual([p["yield_MPa"] for p in ht2["tensile_points"]], [285, 270, 216])
        self.assertEqual(ht2["alloy"], ht1["alloy"])
        for recipe in (ht1, ht2):
            self.assertEqual((recipe["machine_model"], recipe["layer_thickness_um"]), ("EOS M290", 60))
            self.assertIsNone(recipe["heat_treatment"]["hold_h"])
        conductivity = recipes["cucrzr-m400-1-80um-conductivity-vertical_z"]
        tensile = recipes["cucrzr-m400-1-80um-tensile-vertical_z"]
        self.assertEqual((conductivity["tensile_points"][0]["yield_MPa"], conductivity["electrical_conductivity_IACS_pct"]), (230, 88))
        self.assertEqual((tensile["tensile_points"][0]["yield_MPa"], tensile["electrical_conductivity_IACS_pct"]), (495, 76))
        self.assertIsNone(tensile["thermal_conductivity_W_mK"])
        self.assertIsNone(tensile["tensile_points"][0]["test_temperature_C"])

    def test_explicit_research_assumptions_can_prepare_a_case_without_qualification(self):
        self.research_fixture()
        result = engineering.validate(self.contract, self.materials, require_ready=True)
        self.assertTrue(result["research_inputs_ready"])
        self.assertEqual(len(result["explicit_research_assumptions"]), 8)
        self.assertFalse(any(result["qualification"].values()))
        with self.assertRaisesRegex(ValueError, "Qualification inputs incomplete"):
            engineering.validate(self.contract, self.materials, require_qualification=True)

    def test_units_invalid_numbers_and_missing_provenance_are_rejected(self):
        self.research_fixture()
        original = copy.deepcopy(self.contract)
        for key, value in (("young_modulus_GPa", 0), ("poisson_ratio", .5),
                           ("metal_temperature_C", -273.15), ("chamber_pressure_bar", -1),
                           ("coolant_pressure_bar", True), ("young_modulus_GPa", float("nan")),
                           ("young_modulus_GPa", float("inf"))):
            candidate = copy.deepcopy(original)
            candidate["research_inputs"][key]["value"] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                engineering.validate(candidate, self.materials)
        for field, value in (("unit", "Pa"), ("source", None), ("reason", "")):
            candidate = copy.deepcopy(original)
            candidate["research_inputs"]["young_modulus_GPa"][field] = value
            with self.assertRaises(ValueError):
                engineering.validate(candidate, self.materials)

    def test_geometry_drift_and_recipe_or_qualification_promotion_are_rejected(self):
        candidate = copy.deepcopy(self.contract)
        candidate["geometry_variants"][0]["config_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Geometry evidence changed"):
            engineering.validate(candidate, self.materials)
        candidate = copy.deepcopy(self.materials)
        candidate["recipes"].append(copy.deepcopy(candidate["recipes"][0]))
        with self.assertRaisesRegex(ValueError, "distinct"):
            engineering.validate(self.contract, candidate)
        self.materials["recipes"][0]["qualified_for_962_head"] = True
        with self.assertRaisesRegex(ValueError, "cannot qualify"):
            engineering.validate(self.contract, self.materials)

    def test_required_nulls_cannot_be_removed_to_bypass_qualification(self):
        for field in ("lpbf_inputs", "qualification_evidence"):
            candidate = copy.deepcopy(self.contract)
            candidate[field] = {}
            with self.assertRaisesRegex(ValueError, "Required engineering input names"):
                engineering.validate(candidate, self.materials, require_qualification=True)
        self.materials["missing_laws"] = {}
        with self.assertRaisesRegex(ValueError, "required law names"):
            engineering.validate(self.contract, self.materials)

    def test_measured_input_needs_evidence_hash_and_manufacturing_stays_false(self):
        self.research_fixture()
        self.contract["research_inputs"]["young_modulus_GPa"]["basis"] = "measured"
        with self.assertRaisesRegex(ValueError, "immutable evidence digest"):
            engineering.validate(self.contract, self.materials)
        self.contract["qualification"]["manufacturing_authorized"] = True
        with self.assertRaisesRegex(ValueError, "cannot grant"):
            engineering.validate(self.contract, self.materials)

    def test_material_units_and_primary_source_attribution_are_required(self):
        self.materials["units"]["modulus_GPa"] = "MPa"
        with self.assertRaisesRegex(ValueError, "Material units"):
            engineering.validate(self.contract, self.materials)
        self.setUp()
        self.materials["sources"][0]["url"] = "https://unattributed.example/material"
        with self.assertRaisesRegex(ValueError, "primary-manufacturer provenance"):
            engineering.validate(self.contract, self.materials)

    def test_cli_reports_missing_inputs_and_refuses_qualification(self):
        script = str(FOLDER / "validate_contract.py")
        result = subprocess.run([sys.executable, script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["research_inputs_ready"])
        result = subprocess.run([sys.executable, script, "--require-qualification"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Qualification inputs incomplete", result.stderr)


if __name__ == "__main__":
    unittest.main()
