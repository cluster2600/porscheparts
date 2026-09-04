"""Garde-fous de la reconstruction F36 contrainte par le scan."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/scan-conforming-4v-f36.json"
SOURCE = ROOT / "twins/reference-917-engine/source/build_scan_conforming_4v_f36.py"
OPENFOAM_SOURCE = ROOT / "twins/reference-917-engine/source/prepare_scan_conforming_openfoam_f36.py"
CALCULIX_SOURCE = ROOT / "twins/reference-917-engine/source/run_scan_conforming_calculix_f36.py"
SUMMARY_SOURCE = ROOT / "twins/reference-917-engine/source/summarize_scan_conforming_cae_f36.py"
VALVETRAIN_SOURCE = ROOT / "twins/reference-917-engine/source/analyze_f36_valvetrain_assembly.py"
PRINTABILITY_SOURCE = ROOT / "twins/reference-917-engine/source/analyze_f36_lpbf_printability.py"
LPBF_LOCKED_PLATE_SOURCE = ROOT / "twins/reference-917-engine/source/run_f36_lpbf_locked_plate.py"
IMPROVEMENT_SOURCE = ROOT / "twins/reference-917-engine/source/screen_f36_improvements.py"
VALVETRAIN_CONTRACT = ROOT / "twins/reference-917-engine/f36-valvetrain-assembly.json"
IMPROVEMENT_CONTRACT = ROOT / "twins/reference-917-engine/f36-improvement-campaign.json"
FLUIDX3D_SOURCE = ROOT / "twins/reference-917-engine/fluidx3d/setup.cpp"
F34_DOC = ROOT / "docs/917_AIRCOOLED_4V_F34.md"


class ScanConformingFourValveF36Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_f34_product_geometry_is_superseded(self):
        supersedes = self.contract["supersedes"]
        self.assertEqual(supersedes["phase"], "F34")
        self.assertEqual(supersedes["scope"], "product_geometry_only")
        self.assertEqual(supersedes["retained_use"], "numerical_method_regression_only")
        self.assertIn("RETIRÉ", F34_DOC.read_text(encoding="utf-8")[:800])

    def test_exact_scan_is_fail_closed_and_not_published(self):
        source = self.contract["source"]
        self.assertEqual(
            source["sha256"],
            "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486",
        )
        self.assertGreater(source["open_edges"], 90_000)
        self.assertEqual(source["raw_and_derived_geometry_policy"], "local_only_not_committed")
        self.assertFalse(source["porsche_917_dimensional_identity"])
        self.assertFalse(self.contract["reconstruction"]["derived_mesh_committed"])

    def test_four_valve_twin_ignition_architecture_is_explicit(self):
        architecture = self.contract["four_valve_architecture"]
        self.assertEqual(architecture["intake"]["count"], 2)
        self.assertEqual(architecture["exhaust"]["count"], 2)
        self.assertEqual(architecture["intake"]["guide_outer_diameter_obj_units"], 15.0)
        self.assertEqual(architecture["exhaust"]["guide_outer_diameter_obj_units"], 15.0)
        self.assertLess(architecture["intake"]["guide_bore_diameter_obj_units"], 15.0)
        self.assertEqual(architecture["ignition"]["count"], 2)
        self.assertFalse(architecture["spring_package"]["rate_and_installed_load_released"])

    def test_scan_conformance_and_wall_screen_are_quantified(self):
        reconstruction = self.contract["reconstruction"]
        self.assertTrue(reconstruction["watertight"])
        self.assertEqual(reconstruction["body_count"], 1)
        self.assertLess(reconstruction["scan_to_reconstruction_p95_obj_units"], 0.5)
        wall = self.contract["internal_wall_screen"]
        self.assertGreater(wall["minimum_obj_units"], 6.0)
        self.assertFalse(wall["ct_or_metrology_validation"])
        self.assertLessEqual(reconstruction["candidate_mass_kg_if_obj_unit_is_mm_and_density_2670"], 2.83)
        self.assertEqual(reconstruction["selected_valvetrain_bay_radius_obj_units"], 50.85)
        self.assertEqual(reconstruction["selected_valvetrain_bay_floor_obj_units"], 49.15)
        self.assertEqual(
            reconstruction["valvetrain_bay_parameter_selection"],
            "mass_target_adjustment_not_optimized_or_locally_validated",
        )
        self.assertFalse(self.contract["engineering_gates"]["valvetrain_bay_local_ligament_validated"])

    def test_new_geometry_builder_verifies_source_and_keeps_scale_qualified(self):
        source_text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("EXPECTED_SCAN_SHA256", source_text)
        self.assertIn("screened_poisson", source_text)
        self.assertIn("echelle physique non confirmee", source_text)
        self.assertIn('"human_morphology_review": False', source_text)

    def test_f34_cfd_is_not_reused_and_all_release_gates_are_closed(self):
        cooling = self.contract["cooling_model_next_gate"]
        self.assertEqual(cooling["method_a"], "OpenFOAM_finite_volume_RANS_CHT")
        self.assertIn("FluidX3D", cooling["method_b"])
        self.assertFalse(cooling["f34_results_reusable_as_f36_performance_evidence"])
        gates = self.contract["engineering_gates"]
        self.assertFalse(gates["human_morphology_review"])
        self.assertTrue(all(value is False for key, value in gates.items() if key != "automated_surface_conformance"))

    def test_f36_numerical_boundaries_fail_closed(self):
        openfoam = OPENFOAM_SOURCE.read_text(encoding="utf-8")
        self.assertIn("flowRateInletVelocity", openfoam)
        self.assertIn("massFlowRate", openfoam)
        self.assertIn('header("decomposeParDict")', openfoam)
        self.assertIn("method scotch", openfoam)
        calculix = CALCULIX_SOURCE.read_text(encoding="utf-8")
        self.assertIn("GUIDE,1,1", calculix)
        fluidx3d = FLUIDX3D_SOURCE.read_text(encoding="utf-8")
        self.assertIn("hot_wall", fluidx3d)
        self.assertNotIn("TYPE_S|TYPE_T|TYPE_X", fluidx3d)
        summary = SUMMARY_SOURCE.read_text(encoding="utf-8")
        self.assertIn('"external_air_cross_solver_comparison"', summary)
        self.assertIn('"openfoam_fluidx3d_heat_agreement_within_10_percent"', summary)
        self.assertIn('"metal_print_authorized": False', summary)
        self.assertIn('"engine_start_authorized": False', summary)

    def test_complete_valvetrain_bom_and_virtual_print_are_explicit(self):
        assembly = json.loads(VALVETRAIN_CONTRACT.read_text(encoding="utf-8"))
        quantities = {item["id"]: item["quantity"] for item in assembly["bom"]}
        self.assertEqual(quantities["intake_valve"], 2)
        self.assertEqual(quantities["exhaust_valve"], 2)
        self.assertEqual(quantities["valve_guide"], 4)
        self.assertEqual(quantities["dual_valve_spring"], 4)
        self.assertEqual(quantities["split_valve_keeper"], 8)
        self.assertFalse(assembly["release_gates"]["metal_print_authorized"])
        valvetrain = VALVETRAIN_SOURCE.read_text(encoding="utf-8")
        self.assertIn("k=G*d^4/(8*D^3*N_active)", valvetrain)
        self.assertIn("dynamic_force_margin_at_least_1_2", valvetrain)
        printability = PRINTABILITY_SOURCE.read_text(encoding="utf-8")
        self.assertIn("trapped_void_voxels", printability)
        self.assertIn("calibrated_thermomechanical_build_simulation", printability)
        self.assertIn('"metal_print_authorized": False', printability)

    def test_improvement_doe_and_locked_plate_print_screen_are_fail_closed(self):
        campaign = json.loads(IMPROVEMENT_CONTRACT.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(campaign["head_material_candidates"]), 3)
        self.assertGreaterEqual(len(campaign["valve_material_candidates"]), 4)
        inconel = [
            item for item in campaign["valve_material_candidates"]
            if item["id"] == "INCONEL_751_wrought_exhaust"
        ][0]
        self.assertEqual(inconel["mechanical_properties_temperature_c"], 816.0)
        self.assertEqual(inconel["lead_oxide_screening_temperature_c_not_service_rating"], 913.0)
        self.assertNotIn("not_service_rating", inconel["temperature_evidence_classification"])
        source = IMPROVEMENT_SOURCE.read_text(encoding="utf-8")
        self.assertIn('candidate.get("mechanical_properties_temperature_c")', source)
        self.assertGreaterEqual(len(campaign["spring_candidates"]), 3)
        self.assertFalse(campaign["manufacturing_or_engine_release"])
        improvement = IMPROVEMENT_SOURCE.read_text(encoding="utf-8")
        self.assertIn("traceable_virtual_screen_not_exhaustive", improvement)
        self.assertIn('"metal_print_authorized": False', improvement)
        locked_plate = LPBF_LOCKED_PLATE_SOURCE.read_text(encoding="utf-8")
        self.assertIn("BUILD_PLATE,1,3", locked_plate)
        self.assertIn("plasticity_and_stress_relaxation_included", locked_plate)
        self.assertIn('"metal_print_authorized": False', locked_plate)


if __name__ == "__main__":
    unittest.main()
