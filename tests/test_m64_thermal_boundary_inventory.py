import importlib.util
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "twins/m64-cylinder-head/inventory_thermal_boundaries.py"
SPEC = importlib.util.spec_from_file_location("m64_boundaries", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ThermalBoundaryTests(unittest.TestCase):
    def mapping(self, ids=None):
        return {"source_sha256": "abc", "ocp_version": "7.9.3.1", "assignments": [{"role": "cooling_air", "evidence": "Reviewed labelled CAD, case X", "face_ids": ids or [1]}]}

    def test_no_automatic_adiabatic_fallback(self):
        self.assertEqual(MODULE.validate_assignments(None, "abc", 2), {})

    def test_source_hash_required(self):
        with self.assertRaisesRegex(ValueError, "hash_mismatch"):
            MODULE.validate_assignments(self.mapping(), "other", 2)

    def test_duplicate_face_rejected(self):
        with self.assertRaisesRegex(ValueError, "overlapping"):
            MODULE.validate_assignments(self.mapping([1, 1]), "abc", 2)

    def test_import_version_must_match(self):
        with self.assertRaisesRegex(ValueError, "import_version_mismatch"):
            MODULE.validate_assignments(self.mapping(), "abc", 2, "other")

    def test_unknown_face_rejected(self):
        with self.assertRaisesRegex(ValueError, "out_of_range"):
            MODULE.validate_assignments(self.mapping([3]), "abc", 2)

    def test_boolean_face_rejected(self):
        with self.assertRaisesRegex(ValueError, "out_of_range"):
            MODULE.validate_assignments(self.mapping([True]), "abc", 2)

    def test_evidence_required(self):
        mapping = self.mapping()
        mapping["assignments"][0]["evidence"] = " "
        with self.assertRaisesRegex(ValueError, "evidence_required"):
            MODULE.validate_assignments(mapping, "abc", 2)

    def test_roles_are_not_free_form_conditions(self):
        mapping = self.mapping()
        mapping["assignments"][0]["role"] = "allWallsFixed900K"
        with self.assertRaisesRegex(ValueError, "unknown_thermal"):
            MODULE.validate_assignments(mapping, "abc", 2)

    def rows(self):
        return [{"face_id": 1, "surface_type": "Plane", "area_scan_units_squared": 2.0, "thermal_role": "cooling_air"},
                {"face_id": 2, "surface_type": "Cylinder", "area_scan_units_squared": 3.0, "thermal_role": None}]

    def test_partial_coverage_is_reported_not_passed(self):
        summary = MODULE.summarize(self.rows(), 5.0, "abc")
        self.assertFalse(summary["boundary_partition_complete"])
        self.assertEqual(summary["assigned_surface_area_fraction"], .4)
        self.assertFalse(summary["cht_solved"])

    def test_surface_sum_must_close(self):
        with self.assertRaisesRegex(ValueError, "does_not_match"):
            MODULE.summarize(self.rows(), 6.0, "abc")

    def test_nonfinite_area_rejected(self):
        rows = self.rows()
        rows[0]["area_scan_units_squared"] = float("nan")
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            MODULE.summarize(rows, 5.0, "abc")

    def test_complete_partition_still_not_a_solver(self):
        rows = self.rows()
        rows[1]["thermal_role"] = "exhaust_gas"
        summary = MODULE.summarize(rows, 5.0, "abc")
        self.assertTrue(summary["boundary_partition_complete"])
        self.assertFalse(summary["cht_case_generated"])
        self.assertFalse(summary["manufacturing_authorized"])


if __name__ == "__main__":
    unittest.main()
