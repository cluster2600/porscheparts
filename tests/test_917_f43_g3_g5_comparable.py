import copy
import importlib.util
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "twins/reference-917-engine/f43-g3-g5-comparable-execution.json"
REPORT_PATH = ROOT / "twins/reference-917-engine/evidence/f43-g3-g5-comparable/audit-report.json"
FIXTURE_PATH = ROOT / "tests/fixtures/917-g3-g5-synthetic-case-results.json"
SCRIPT_PATH = ROOT / "twins/reference-917-engine/source/audit_g3_g5_comparable_execution_f43.py"

SPEC = importlib.util.spec_from_file_location("f43_audit", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class F43G3G5ComparableExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text())
        cls.report = json.loads(REPORT_PATH.read_text())

    def test_tracked_audit_is_deterministic_and_hash_bound(self):
        generated = MODULE.build_report(CONTRACT_PATH)
        self.assertEqual(MODULE.canonical_bytes(generated), REPORT_PATH.read_bytes())
        self.assertTrue(self.report["contract"]["all_upstream_hashes_verified"])
        self.assertEqual(
            self.report["contract"]["sha256"], MODULE.sha256(CONTRACT_PATH)
        )

    def test_comparison_pair_is_one_revision_but_unavailable_for_execution(self):
        geometry = self.contract["comparison_geometry"]
        self.assertEqual(
            [row["architecture"] for row in geometry["paired_variants"]],
            ["2v", "4v"],
        )
        self.assertTrue(geometry["same_generation_revision_verified"])
        self.assertFalse(geometry["same_external_envelope_verified"])
        self.assertFalse(geometry["execution_authorized"])
        for row in geometry["paired_variants"]:
            self.assertFalse(row["geometry_file_available_in_repository"])
            self.assertFalse(row["sealed_intake_exhaust_fluid_domain_available"])
            self.assertFalse(row["moving_piston_valve_domain_available"])

    def test_turbo_boundary_is_shared_but_not_validated(self):
        boundary = self.contract["shared_turbo_boundary"]
        self.assertEqual(boundary["applies_identically_to"], ["2v", "4v"])
        self.assertEqual(boundary["source_variant_id"], "917_2026_flat12_twin_turbo_1600hp_target")
        self.assertFalse(boundary["combustion_calibration_available"])
        self.assertFalse(boundary["cam_and_valve_laws_available"])
        self.assertFalse(boundary["validated"])

    def test_G3_G4_G5_matrix_requires_two_methods_three_meshes_and_balances(self):
        execution = self.contract["three_mesh_execution"]
        self.assertEqual(execution["mesh_ids"], ["coarse", "medium", "fine"])
        self.assertEqual(execution["planned_case_count"], 18)
        self.assertEqual(execution["executed_case_count"], 0)
        self.assertEqual(
            [row["id"] for row in execution["domains"]],
            ["G3_steady_port_flow", "G4_moving_engine_cycle", "G5_external_air_cooling"],
        )
        for row in execution["domains"]:
            self.assertEqual(row["architectures"], ["2v", "4v"])
            self.assertNotEqual(row["method_a"], row["method_b"])
            self.assertFalse(row["geometry_ready"])
            self.assertFalse(row["execution_authorized"])
        acceptance = self.contract["numerical_acceptance"]
        self.assertEqual(acceptance["cross_method_relative_difference_maximum"], 0.20)
        self.assertLessEqual(acceptance["mass_balance_relative_maximum"], 0.005)
        self.assertLessEqual(acceptance["energy_balance_relative_maximum"], 0.05)

    def test_existing_solver_evidence_is_audited_without_promotion(self):
        g3 = self.report["existing_G3_OpenFOAM_audit"]
        self.assertEqual(g3["executed_case_count"], 6)
        self.assertFalse(g3["full_runner_or_moving_valve_geometry_used"])
        self.assertFalse(g3["boundary_mass_balance_fields_present"])
        self.assertFalse(g3["energy_balance_fields_present"])
        self.assertFalse(g3["independent_second_method_present"])
        self.assertFalse(g3["accepted_for_F43_comparison"])
        self.assertFalse(g3["architectures"]["2v"]["passes_F43_five_percent_mesh_rule"])
        self.assertFalse(g3["architectures"]["4v"]["passes_F43_five_percent_mesh_rule"])

        cantera = self.report["existing_Cantera_audit"]
        self.assertTrue(cantera["cantera_equilibrium_uv_executed"])
        self.assertFalse(cantera["crank_angle_time_marching_executed"])
        self.assertFalse(cantera["same_2v_4v_turbo_case_executed"])
        self.assertFalse(cantera["accepted_for_G4_cross_method"])

        ice = self.report["existing_ICEEngineFoam_audit"]
        self.assertFalse(ice["exact_iceEngineFoam_executable_present"])
        self.assertEqual(ice["executed_valve_count"], 2)
        self.assertFalse(ice["porsche_917_geometry_used"])
        self.assertFalse(ice["four_valve_case_executed"])

        cooling = self.report["existing_G5_air_cooling_audit"]
        self.assertEqual(cooling["F34_OpenFOAM"]["architecture"], "4v_only")
        self.assertFalse(cooling["F36_cross_solver"]["cooling_closed"])
        self.assertFalse(cooling["F42_cross_method"]["exact_F41_OpenFOAM_case_accepted"])
        self.assertFalse(cooling["paired_2v_4v_same_geometry_revision_exists"])

    def test_LPBF_air_DOE_is_bounded_open_and_unexecuted(self):
        doe = self.contract["f43_air_cooling_LPBF_DOE"]
        self.assertEqual(len(doe["designs"]), 7)
        self.assertEqual(doe["planned_case_count"], 21)
        self.assertEqual(doe["executed_case_count"], 0)
        self.assertTrue(all(value is None for value in doe["dimension_parameters_mm"].values()))
        self.assertIsNone(doe["external_envelope_control"]["maximum_allowed_deviation_mm"])
        self.assertFalse(doe["external_envelope_control"]["quasi_identical_verified"])
        prohibited = set(doe["prohibited_features"])
        self.assertIn("liquid_cooling_jacket", prohibited)
        self.assertIn("closed_internal_cavity", prohibited)
        self.assertIn("microchannel_without_demonstrated_powder_removal", prohibited)
        self.assertIsNone(doe["selected_design"])
        self.assertFalse(doe["simulation_authorized"])

    def test_secondary_oil_DOE_keeps_air_primary_and_all_design_values_null(self):
        oil = self.contract["f43_secondary_oil_cooling_DOE"]
        self.assertIn("air_forced_remains_primary", oil["role"])
        self.assertTrue(all(value is None for value in oil["design_lock_values"].values()))
        self.assertIn("through_or_open_ended_only", oil["printed_passage_policy"])
        self.assertIn("CT_inspectable_with_probability_of_detection_study", oil["printed_passage_policy"])
        self.assertIn("no_liquid_jacket_around_combustion_chamber", oil["printed_passage_policy"])
        self.assertIsNone(oil["planned_case_count"])
        self.assertEqual(oil["executed_case_count"], 0)
        self.assertFalse(oil["existing_F37_values_are_design_lock"])
        self.assertFalse(oil["simulation_authorized"])
        audit = self.report["existing_secondary_oil_audit"]
        self.assertFalse(audit["methods_are_independent_for_laminar_flow"])
        self.assertFalse(audit["jet_impingement_CFD_executed"])
        self.assertFalse(audit["multiphase_aeration_and_drainback_executed"])

    def test_synthetic_fixture_exercises_math_but_never_evidence_gates(self):
        fixture = json.loads(FIXTURE_PATH.read_text())
        result = MODULE.evaluate_synthetic_fixture(fixture, self.contract)
        self.assertTrue(result["validator_math_passed"])
        self.assertTrue(result["excluded_from_engine_evidence"])
        self.assertFalse(result["physical_or_release_gate_opened"])
        self.assertTrue(all(value is False for value in fixture["release_gates"].values()))

    def test_adversarial_mutations_fail_closed(self):
        mutations = []

        changed_hash = copy.deepcopy(self.contract)
        changed_hash["upstream_evidence"][0]["sha256"] = "0" * 64
        mutations.append(changed_hash)

        changed_bc = copy.deepcopy(self.contract)
        changed_bc["shared_turbo_boundary"]["manifold_pressure_pa_abs"] += 1.0
        mutations.append(changed_bc)

        opened_execution = copy.deepcopy(self.contract)
        opened_execution["three_mesh_execution"]["domains"][0]["execution_authorized"] = True
        mutations.append(opened_execution)

        invented_fin = copy.deepcopy(self.contract)
        invented_fin["f43_air_cooling_LPBF_DOE"]["dimension_parameters_mm"]["fin_pitch"] = 4.0
        mutations.append(invented_fin)

        invented_jet = copy.deepcopy(self.contract)
        invented_jet["f43_secondary_oil_cooling_DOE"]["design_lock_values"]["jet_diameters_mm"] = [1.0]
        mutations.append(invented_jet)

        opened_release = copy.deepcopy(self.contract)
        opened_release["release_gates"]["metal_print_authorized"] = True
        mutations.append(opened_release)

        for mutated in mutations:
            with self.subTest(mutation=mutated):
                with self.assertRaises(MODULE.ContractError):
                    MODULE.validate_contract(mutated)

    def test_every_release_gate_and_decision_remains_closed(self):
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))
        decision = self.report["decision"]
        self.assertFalse(decision["comparable_2v_4v_execution_complete"])
        self.assertFalse(decision["F43_LPBF_cooling_improvement_quantified"])
        self.assertFalse(decision["new_long_solver_run_started"])
        self.assertFalse(decision["metal_print_authorized"])
        self.assertFalse(decision["engine_start_authorized"])


if __name__ == "__main__":
    unittest.main()
