#!/usr/bin/env python3
"""Contrôles autonomes des preuves publiques F49."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/f49-cfd-cht-contract.json"
BUILDER = ROOT / "twins/reference-917-engine/source/build_cfd_cases_f49.py"
RUNNER = ROOT / "twins/reference-917-engine/source/run_cfd_cases_f49.py"
PUBLISHER = ROOT / "twins/reference-917-engine/source/publish_cfd_results_f49.py"
FAILED_RERUN_SUMMARIZER = ROOT / "twins/reference-917-engine/source/summarize_failed_reruns_f49.py"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f49-cfd-cht"
REPORT = EVIDENCE / "f49-cfd-cht-report.json"
PUBLICATION = EVIDENCE / "publication.json"
VAST_BUDGET = ROOT / "twins/reference-917-engine/f49-vast-execution-budget.json"
CORRECTION = ROOT / "twins/reference-917-engine/f49-cfd-cht-corrective-coarse.json"
RUNTIME_POLICY = ROOT / "twins/reference-917-engine/f49-cfd-cht-runtime-policy.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F49CFDCHTTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.publication = json.loads(PUBLICATION.read_text(encoding="utf-8"))

    def test_authority_hashes_are_current(self) -> None:
        for record in self.contract["authority"].values():
            if not isinstance(record, dict):
                continue
            path = ROOT / record["path"]
            self.assertTrue(path.is_file(), record["path"])
            self.assertEqual(sha256(path), record["sha256"], record["path"])

    def test_same_BC_and_three_prepared_grids_for_2V_4V(self) -> None:
        self.assertEqual(self.contract["geometry_policy"]["variants"], ["2V", "4V"])
        self.assertEqual(self.contract["mesh_matrix"]["levels"], ["coarse", "medium", "fine"])
        self.assertEqual(set(self.contract["openfoam"]["screens"]), {"intake", "exhaust"})
        for screen in self.contract["openfoam"]["screens"].values():
            self.assertEqual(screen["imposed_pressure_difference_pa"], 10000.0)
            self.assertIn(screen["source_patch"], self.contract["geometry_policy"]["patches"])
            self.assertIn(screen["sink_patch"], self.contract["geometry_policy"]["patches"])

    def test_corrective_runner_fails_if_openfoam_environment_is_not_sourced(self) -> None:
        spec = importlib.util.spec_from_file_location("run_cfd_cases_f49", RUNNER)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with mock.patch.dict(module.os.environ, {}, clear=True), mock.patch.object(module.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "openfoam_environment_not_sourced"):
                module.assert_openfoam_environment()

    def test_corrective_contract_keeps_physics_and_geometry_unchanged(self) -> None:
        correction = json.loads(CORRECTION.read_text(encoding="utf-8"))
        self.assertEqual(correction["base_contract"]["sha256"], sha256(CONTRACT))
        self.assertFalse(correction["scope"]["physical_boundary_conditions_changed"])
        self.assertFalse(correction["scope"]["geometry_changed"])
        self.assertLessEqual(correction["numerical_controls"]["maximum_Courant_number"], 0.1)
        self.assertTrue(correction["patch_audit"]["omegaWallFunction_allowed_only_where_U_is_noSlip"])
        self.assertFalse(correction["claims"]["performance_claim_allowed"])

    def test_runtime_policy_disables_residual_only_early_stop(self) -> None:
        policy = json.loads(RUNTIME_POLICY.read_text(encoding="utf-8"))
        self.assertEqual(policy["bound_inputs"]["base_contract_sha256"], sha256(CONTRACT))
        self.assertEqual(policy["bound_inputs"]["executed_corrective_profile_sha256"], sha256(CORRECTION))
        builder_record = policy["bound_inputs"]["builder_without_residualControl"]
        self.assertEqual(builder_record["path"], str(BUILDER.relative_to(ROOT)))
        self.assertEqual(builder_record["sha256"], sha256(BUILDER))
        runner_record = policy["bound_inputs"]["runner"]
        self.assertEqual(runner_record["path"], str(RUNNER.relative_to(ROOT)))
        self.assertEqual(runner_record["sha256"], sha256(RUNNER))
        summarizer_record = policy["bound_inputs"]["failed_rerun_summarizer"]
        self.assertEqual(summarizer_record["path"], str(FAILED_RERUN_SUMMARIZER.relative_to(ROOT)))
        self.assertEqual(summarizer_record["sha256"], sha256(FAILED_RERUN_SUMMARIZER))
        self.assertFalse(policy["PIMPLE_residualControl_early_stop_enabled"])
        self.assertTrue(policy["residuals_remain_recorded_metrics"])
        self.assertEqual(policy["minimum_physical_time_before_positive_stop_s"], 0.005)
        self.assertEqual(policy["maximum_authorized_future_horizon_s"], 0.02)
        self.assertFalse(policy["threshold_relaxation_allowed"])
        self.assertNotIn("residualControl", BUILDER.read_text(encoding="utf-8"))

    def test_no_geometry_or_external_skin_mutation(self) -> None:
        policy = self.contract["geometry_policy"]
        self.assertFalse(policy["external_F43_skin_imported_or_modified"])
        self.assertFalse(policy["solid_head_present"])
        self.assertFalse(policy["ellipse_or_oval_primitive_or_envelope_allowed"])
        for source in (BUILDER, RUNNER, PUBLISHER):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            calls = {
                node.func.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            }
            self.assertTrue(calls.isdisjoint({"addEllipse", "addDisk", "addBox", "importShapes"}), source.name)

    def test_openfoam_execution_is_real_but_fail_closed(self) -> None:
        self.assertEqual(self.report["case_count"], 8)
        expected = {f"{variant}-{level}-{screen}" for variant in ("2v", "4v") for level in ("coarse", "medium") for screen in ("intake", "exhaust")}
        self.assertEqual(set(self.report["case_index"]), expected)
        self.assertEqual(self.report["gates"]["solver_attempt_count"], 14)
        self.assertEqual(self.report["gates"]["selected_case_count"], 8)
        self.assertFalse(self.report["gates"]["all_eight_solvers_return_code_zero"])
        for case in self.report["case_index"].values():
            self.assertTrue(case["solver_executed"])
            self.assertIn(case["status"], {"EXECUTED_FAIL_CLOSED", "SOLVER_FAILED"})
            self.assertEqual(set(case["mesh"]["patch_names_seen_in_log"]), set(self.contract["geometry_policy"]["patches"]))
            self.assertLess(case["mesh"]["volume_relative_difference_from_F48"], 0.02)
        self.assertTrue(all(self.report["case_index"][f"{variant}-{level}-intake"]["solver_return_code_zero"] for variant in ("2v", "4v") for level in ("coarse", "medium")))
        self.assertTrue(any(not case["solver_return_code_zero"] for case in self.report["case_index"].values()))
        self.assertFalse(self.report["validation_claim"])

    def test_corrective_coarse_audits_wall_functions_and_energy_signs(self) -> None:
        self.assertEqual(len(self.report["corrective_execution_inputs"]), 5)
        courant_guard = self.report["corrective_Courant_guard"]
        self.assertEqual(courant_guard["configured_target"], 0.1)
        self.assertEqual(courant_guard["control_tolerance_fraction"], 0.005)
        self.assertAlmostEqual(courant_guard["maximum_accepted_observed"], 0.1005)
        self.assertEqual(self.report["corrective_openfoam_environment"]["configDict"], "/opt/openfoam14/etc/configDict")
        for variant in ("2v", "4v"):
            for screen in ("intake", "exhaust"):
                case = self.report["case_index"][f"{variant}-coarse-{screen}"]
                self.assertTrue(case["patch_type_audit"]["pass"])
                self.assertTrue(case["patch_type_audit"]["checks"]["flow_patches_have_no_omega_wall_function"])
                self.assertIn("outward_advective_total_enthalpy", case["values"]["energy_balance_sign_convention"])
                self.assertIn("finite_difference_storage_rate_w", case["values"]["unsteady_total_energy_storage"])
                self.assertIn("absolute_total_energy_storage_rate_w", case["values"]["unsteady_total_energy_storage"])
                self.assertEqual(case["convergence_assessment"]["minimum_physical_horizon_s"], 0.005)
        self.assertEqual(
            set(self.report["superseded_corrective_exhaust_early_stops"]),
            {"2v-coarse-exhaust", "4v-coarse-exhaust"},
        )
        self.assertEqual(
            set(self.report["failed_full_horizon_exhaust_reruns"]),
            {"2v-coarse-exhaust", "4v-coarse-exhaust"},
        )
        for failed in self.report["failed_full_horizon_exhaust_reruns"].values():
            self.assertEqual(failed["status"], "TIME_STEP_COLLAPSE_FAIL")
            self.assertFalse(failed["minimum_horizon_reached"])
            self.assertFalse(failed["PIMPLE_residualControl_present"])
            self.assertLessEqual(failed["minimum_time_step_s"], failed["time_step_collapse_threshold_s"])
        plan = self.report["bounded_corrective_plan"]
        self.assertFalse(plan["physical_cause_established"])
        self.assertFalse(plan["Vast_expected_to_fix_numerical_instability_automatically"])
        self.assertTrue(plan["Vast_remains_forbidden_until_local_5ms_smoke_reaches_horizon"])
        self.assertTrue(self.report["gates"]["combined_positive_stop_gate_implemented_in_post_processing"])
        self.assertFalse(self.report["gates"]["all_combined_positive_stop_gates_pass"])
        self.assertTrue(self.report["gates"]["PIMPLE_residualControl_early_stop_disabled_for_future_runs"])
        self.assertTrue(
            all(not case["convergence_assessment"]["positive_stop_gate_pass"] for case in self.report["case_index"].values())
        )
        for screen in ("intake", "exhaust"):
            for variant in ("2V", "4V"):
                self.assertEqual(
                    self.report["comparisons"][screen]["coarse_to_medium"][variant]["status"],
                    "unavailable_mixed_numerical_controls" if screen == "intake" else "unavailable_solver_failure",
                )

    def test_4V_coarse_volume_difference_is_explained_not_repaired(self) -> None:
        case = self.report["case_index"]["4v-coarse-intake"]
        self.assertGreater(case["mesh"]["volume_relative_difference_from_F48"], 0.01)
        self.assertLess(case["mesh"]["volume_relative_difference_from_F48"], 0.02)
        explanation = " ".join(self.report["limitations"])
        self.assertIn("exact OCC mass", explanation)
        self.assertIn("not a geometry repair", explanation)

    def test_AATE_CHT_and_release_claims_remain_closed(self) -> None:
        self.assertFalse(self.contract["aate_icengines"]["exact_ICEEngineFoam_executable_found"])
        self.assertFalse(self.contract["aate_icengines"]["engine_case_execution_ready"])
        self.assertFalse(self.report["AATE_binary_smoke"]["engine_case_executed"])
        self.assertTrue(all(item["help_return_code"] == 0 for item in self.report["AATE_binary_smoke"]["binaries"].values()))
        for gate in (
            "three_grid_solution_available",
            "three_grid_convergence_pass",
            "AATE_dynamic_engine_case_executed",
            "cross_method_agreement_pass",
            "conjugate_CHT_executed",
            "thermal_CHT_validated",
            "fitment_validated",
            "manufacturing_authorized",
            "engine_start_authorized",
        ):
            self.assertFalse(self.report["gates"][gate], gate)

    def test_independent_analytic_method_is_only_an_upper_bound(self) -> None:
        for variant in ("2V", "4V"):
            for screen in ("intake", "exhaust"):
                record = self.report["independent_analytic_method"][variant][screen]
                self.assertEqual(record["Cd_assumed"], 1.0)
                self.assertGreater(record["ideal_upper_bound_mass_flow_kg_s"], 0.0)
                self.assertIn("upper_bound", record["role"])

    def test_optional_Vast_budget_is_bounded_and_not_launched(self) -> None:
        vast = json.loads(VAST_BUDGET.read_text(encoding="utf-8"))
        self.assertLess(vast["total_cost_bound_usd"], vast["budget_ceiling_usd"])
        self.assertEqual(vast["transfer_bounds_gb"]["total"], 5.1)
        self.assertEqual(vast["planned_cases_if_authorized"]["expected_job_count"], 12)
        self.assertEqual(len(vast["planned_cases_if_authorized"]["OpenFOAM_case_ids"]), 12)
        self.assertFalse(vast["planned_cases_if_authorized"]["AATE_dynamic_engine_case"])
        self.assertFalse(vast["planned_cases_if_authorized"]["conjugate_CHT_case"])
        self.assertEqual(vast["planned_solver_horizon_if_authorized"]["maximum_physical_time_s"], 0.02)
        self.assertTrue(vast["planned_solver_horizon_if_authorized"]["final_averaging_window_required"])
        self.assertFalse(vast["planned_solver_horizon_if_authorized"]["threshold_relaxation_allowed"])
        self.assertFalse(vast["registry_digest_verified"])
        self.assertFalse(vast["launch_ready"])
        self.assertFalse(vast["launched"])

    def test_publication_hashes_and_no_raw_solver_artifacts(self) -> None:
        for record in self.publication["files"].values():
            path = ROOT / record["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(sha256(path), record["sha256"])
        forbidden = {".msh", ".brep", ".step", ".stp", ".stl", ".obj", ".foam"}
        leaked = [path for path in EVIDENCE.rglob("*") if path.is_file() and path.suffix.lower() in forbidden]
        self.assertEqual(leaked, [])
        self.assertFalse(self.publication["raw_mesh_or_field_committed"])


if __name__ == "__main__":
    unittest.main()
