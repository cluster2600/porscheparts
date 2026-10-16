"""Discrete source points cannot supply missing head-material properties."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/962-cylinder-head-f0/source/compare_materials.py"
spec = importlib.util.spec_from_file_location("head_material_comparison", SOURCE)
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


class MaterialComparisonTests(unittest.TestCase):
    def setUp(self):
        self.materials = json.loads(comparison.MATERIALS.read_text())
        self.geometry = [dict(bore_mm=bore, metal_volume_cm3=1000)
                         for bore in (95, 98, 100, 102)]

    def rows(self, materials=None):
        return {row["recipe_id"]: row for row in comparison.compare(
            self.materials if materials is None else materials, self.geometry)}

    def test_each_ht1_treatment_uses_its_own_room_temperature_reference(self):
        rows = self.rows()
        first = rows["ht1-treatment-1-m290-60um-vertical"]["ht1_yield_retention"]
        second = rows["ht1-treatment-2-m290-60um-vertical"]["ht1_yield_retention"]
        for points, reference, yields in ((first, 425, (238, 188)), (second, 285, (270, 216))):
            self.assertEqual([p["test_temperature_C"] for p in points], [200, 250])
            for point, value in zip(points, yields):
                self.assertEqual(point["same_recipe_reference_yield_MPa"], reference)
                self.assertAlmostEqual(point["yield_retention_percent"], value / reference * 100)
        changed = copy.deepcopy(self.materials)
        changed["recipes"][1]["tensile_points"][0]["yield_MPa"] = 400
        changed_rows = self.rows(changed)
        self.assertEqual(changed_rows["ht1-treatment-2-m290-60um-vertical"],
                         rows["ht1-treatment-2-m290-60um-vertical"])

    def test_unknown_density_and_eos_test_temperature_stay_unknown(self):
        rows = self.rows()
        for recipe in self.materials["recipes"]:
            row = rows[recipe["id"]]
            self.assertEqual(row["tensile_points"], recipe["tensile_points"])
            if recipe["density_kg_m3"] is None:
                self.assertTrue(all(p["conditional_head_mass_kg"] is None for p in row["conditional_head_masses"]))
            if recipe["source_id"] == "eos-cucrzr-2025":
                self.assertIsNone(row["tensile_points"][0]["test_temperature_C"])
                self.assertIsNone(row["ht1_yield_retention"])
                self.assertIsNone(row["thermal_conductivity_W_mK"])
                for mass in row["conditional_head_masses"]:
                    self.assertAlmostEqual(mass["conditional_head_mass_kg"], 8.84)
                    self.assertEqual(mass["bound_for_fixed_study_volume"], "minimum")

    def test_missing_ht1_temperature_is_rejected_without_interpolation(self):
        self.materials["recipes"][1]["tensile_points"][1]["test_temperature_C"] = None
        with self.assertRaisesRegex(ValueError, "separate 25/200/250"):
            self.rows()

    def test_bound_file_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "materials.json"
            path.write_text("original input")
            result = dict(inputs=[dict(path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())])
            comparison.verify_bound_inputs(result, root)
            path.write_text("changed input")
            with self.assertRaisesRegex(ValueError, "input changed"):
                comparison.verify_bound_inputs(result, root)

    def test_actual_report_is_bound_to_inspected_volumes_and_remains_unqualified(self):
        result = comparison.report()
        comparison.verify_bound_inputs(result)
        delivery = json.loads(comparison.DELIVERY.read_text())
        self.assertEqual([g["metal_volume_cm3"] for g in result["geometry"]],
                         [m["metal_volume_cm3"] for m in delivery["models"]])
        self.assertEqual(len(result["recipes"]), 7)
        self.assertIsNone(result["selected_material_recipe_id"])
        self.assertIsNone(result["selected_service_temperature_C"])
        self.assertFalse(any(result["qualification"].values()))
        self.assertTrue(all(value is None for value in result["missing_laws"].values()))

    def test_cli_refuses_to_overwrite_a_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "report.json"
            path.write_text("previous evidence")
            result = subprocess.run([sys.executable, str(SOURCE), "--output", str(path)],
                                    text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(path.read_text(), "previous evidence")


if __name__ == "__main__":
    unittest.main()
