import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "twins/m64-cylinder-head/cp1-hot-points-supplement-20260907.json").read_text())


class CP1HotPointsSupplementTests(unittest.TestCase):
    def setUp(self):
        self.points = DATA["elevated_temperature_tensile_points"]
        self.expansion = DATA["thermal_expansion_interval_coefficients"]
        self.constraints = DATA["interpretation_constraints"]
        self.sources = {source["id"]: source for source in DATA["sources"]}

    def test_single_published_hot_point_and_exact_values(self):
        self.assertEqual(len(self.points), 1)
        point = self.points[0]
        self.assertEqual(point["test_temperature_C"], 200)
        self.assertEqual(point["yield_strength_MPa"], 126)
        self.assertEqual(point["ultimate_tensile_strength_MPa"], 149)
        self.assertEqual(point["elongation_percent"], 17.0)

    def test_treatment_and_test_temperatures_remain_distinct(self):
        point = self.points[0]
        self.assertEqual(point["heat_treatment_temperature_C"], 400)
        self.assertEqual(point["heat_treatment_duration_h"], 1)
        self.assertNotEqual(point["test_temperature_C"], point["heat_treatment_temperature_C"])
        self.assertIs(self.constraints["heat_treatment_temperature_not_test_temperature"], True)
        self.assertIs(self.constraints["thermal_stability_not_tensile_strength_at_temperature"], True)

    def test_no_transfer_to_four_hour_treatment(self):
        self.assertIs(self.points[0]["transfer_to_4h_heat_treatment_permitted"], False)

    def test_hot_point_keeps_process_and_orientation(self):
        point = self.points[0]
        self.assertEqual(point["machine"], "EOS_M290")
        self.assertEqual(point["process"], "LPBF")
        self.assertEqual(point["layer_thickness_um"], 60)
        self.assertEqual(point["orientation"], "vertical")
        self.assertEqual(point["source_id"], "constellium_formnext_2021_p9")

    def test_YS_not_promoted_to_Rp02_or_design_allowable(self):
        point = self.points[0]
        self.assertEqual(point["yield_strength_source_notation"], "YS")
        self.assertIsNone(point["yield_offset_percent"])
        self.assertEqual(point["statistical_basis"], "typical_properties")
        self.assertIs(point["is_design_allowable"], False)

    def test_unknown_hot_test_conditions_remain_null(self):
        for key in ("sample_count", "uncertainty_MPa", "test_standard",
                    "strain_rate_per_second", "test_temperature_dwell_time_h", "surface_finish"):
            with self.subTest(key=key):
                self.assertIsNone(self.points[0][key])

    def test_expansion_values_remain_source_separated_intervals(self):
        actual = [(row["source_id"], row["temperature_interval_C"], row["coefficient_per_K"])
                  for row in self.expansion]
        self.assertEqual(actual, [
            ("constellium_formnext_2021_p9", [20, 200], 0.00002519),
            ("eos_cp1_m290_60um_20260904", [25, 100], 0.000019),
            ("eos_cp1_m290_60um_20260904", [25, 200], 0.000021),
            ("eos_cp1_m290_60um_20260904", [25, 300], 0.000022),
        ])
        self.assertIs(self.constraints["do_not_merge_2021_and_EOS_values"], True)

    def test_interval_coefficients_not_instantaneous_alpha_curve(self):
        self.assertIs(self.constraints["expansion_coefficients_are_reported_over_intervals"], True)
        self.assertIs(self.constraints["do_not_treat_interval_coefficients_as_instantaneous_alpha_T"], True)
        self.assertIs(self.constraints["no_interpolation_or_extrapolation_created"], True)
        for row in self.expansion:
            with self.subTest(interval=row["temperature_interval_C"]):
                self.assertEqual(len(row["temperature_interval_C"]), 2)
                self.assertLess(*row["temperature_interval_C"])
                self.assertNotIn("test_temperature_C", row)

    def test_unknown_expansion_states_are_not_filled_from_tensile_recipe(self):
        for row in self.expansion:
            for key in ("heat_treatment", "orientation", "test_standard", "uncertainty_per_K"):
                with self.subTest(source=row["source_id"], key=key):
                    self.assertIsNone(row[key])

    def test_no_new_thermal_laws_or_solver_release(self):
        for key in ("new_k_T_points_verified", "new_Cp_T_points_verified",
                    "solver_material_assignment_allowed", "manufacturing_authorized"):
            with self.subTest(key=key):
                self.assertIs(self.constraints[key], False)
        self.assertEqual(DATA["material"], "Constellium_Aheadd_CP1")
        self.assertEqual(DATA["status"], "manufacturer_documentary_points_not_a_qualified_material_card")

    def test_all_points_reference_unique_known_sources(self):
        self.assertEqual(len(self.sources), len(DATA["sources"]))
        for row in self.points + self.expansion:
            with self.subTest(source=row["source_id"]):
                self.assertIn(row["source_id"], self.sources)

    def test_formnext_source_bound_to_visually_reviewed_page(self):
        source = self.sources["constellium_formnext_2021_p9"]
        self.assertEqual(source["sha256"], "fb545cdaa3bbbbcf69768c334158cce2f67de4012738134659058b13be60f45f")
        self.assertEqual(source["page_one_based"], 9)
        self.assertIs(source["page_visually_verified"], True)

    def test_EOS_status_date_and_HTML_not_presented_as_PDF_verification(self):
        source = self.sources["eos_cp1_m290_60um_20260904"]
        self.assertEqual(source["document_displayed_status_date"], "2026-09-04")
        self.assertIs(source["publication_date_inferred_from_status_date"], False)
        self.assertEqual(source["source_type"], "manufacturer_process_data_sheet_HTML")
        self.assertEqual(source["PDF_generation_attempt"], "HTTP_500")
        self.assertIs(source["PDF_visual_verification_claimed"], False)


if __name__ == "__main__":
    unittest.main()
