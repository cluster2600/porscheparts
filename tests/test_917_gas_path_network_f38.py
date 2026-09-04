import copy
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
TWIN = ROOT / "twins/reference-917-engine"
CONTRACT = TWIN / "gas-path-network-f38.json"
RUNNER = TWIN / "source/run_gas_path_network_f38.py"
REPORT_NAME = "gas-path-network-f38-report.json"
EVIDENCE_REPORT = TWIN / "evidence/f38/gas-path-network-f38-report.json"
NA = "917_2026_flat12_na_candidate"
TURBO = "917_2026_flat12_twin_turbo_1600hp_target"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_runner_module():
    spec = importlib.util.spec_from_file_location("run_gas_path_network_f38", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GasPathNetworkF38Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(exist_ok=True)
        cls.contract = load(CONTRACT)
        cls.module = load_runner_module()

    def make_temp(self):
        return tempfile.TemporaryDirectory(prefix="f38-test-", dir=WORK)

    def run_solver(self, project_root, contract_path, output):
        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--project-root",
                str(project_root),
                "--contract",
                str(contract_path),
                "--output",
                str(output),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        report_path = output / REPORT_NAME
        report = load(report_path) if report_path.is_file() else None
        return result, report

    def materialize_project(self, root, contract_mutator=None, source_mutator=None):
        contract = copy.deepcopy(self.contract)
        for source_id, declaration in contract["source_evidence"].items():
            source = ROOT / declaration["path"]
            destination = root / declaration["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
            if source_mutator is not None:
                source_mutator(source_id, destination)
            declaration["expected_sha256"] = digest(destination)
        if contract_mutator is not None:
            contract_mutator(contract)
        contract_path = root / "twins/reference-917-engine/gas-path-network-f38.json"
        write_json(contract_path, contract)
        return contract_path

    def test_contract_is_bivariant_hash_bound_offline_and_fail_closed(self):
        self.assertEqual(self.contract["phase"], "F38")
        self.assertEqual(len(self.contract["source_evidence"]), 7)
        self.assertEqual(
            {item["variant_id"] for item in self.contract["variants"]}, {NA, TURBO}
        )
        variants = {item["variant_id"]: item for item in self.contract["variants"]}
        self.assertEqual(variants[NA]["turbocharger_count"], 0)
        self.assertEqual(variants[TURBO]["turbocharger_count"], 2)
        self.assertFalse(variants[NA]["bench_geometry_identity_match"])
        self.assertFalse(variants[TURBO]["bench_geometry_identity_match"])
        self.assertIn("no_geometry_or_displacement_identity", variants[NA]["bench_binding_scope"])
        self.assertFalse(self.contract["numerical_policy"]["network_access_required"])
        self.assertFalse(self.contract["numerical_policy"]["external_api_required"])
        self.assertFalse(
            self.contract["numerical_policy"][
                "unsteady_one_dimensional_gas_dynamics_executed"
            ]
        )
        self.assertEqual(
            self.contract["numerical_policy"]["report_significant_digits"], 12
        )
        authority = self.contract["authority_boundary"]
        self.assertFalse(
            authority["requested_power_target_used_as_direct_f38_solver_input"]
        )
        self.assertTrue(
            authority["requested_power_target_has_indirect_sampling_ancestry"]
        )
        self.assertTrue(authority["inverse_sizing_seed_ancestry_present"])
        self.assertFalse(authority["full_target_independence_proven"])
        self.assertEqual(self.contract["unit_registry"]["mass_flow_kg_s"], "kg/s")
        self.assertEqual(
            self.contract["unit_registry"]["metric_power_ps"], "metric_PS_or_ch"
        )
        self.assertTrue(
            all(value is False for value in self.contract["release_gates"].values())
        )

    def test_runner_closes_only_numerical_identities_for_two_variants(self):
        with self.make_temp() as temp_name:
            output = Path(temp_name) / "output"
            result, report = self.run_solver(ROOT, CONTRACT, output)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertEqual(report["phase"], "F38")
            self.assertEqual(report["variant_count"], 2)
            self.assertTrue(all(report["technical_gates"].values()))
            self.assertTrue(all(value is False for value in report["release_gates"].values()))
            self.assertFalse(report["runtime"]["network_access_used"])
            self.assertFalse(report["runtime"]["external_api_used"])
            self.assertFalse(
                report["model_scope"]["unsteady_one_dimensional_gas_dynamics_executed"]
            )
            self.assertFalse(report["model_scope"]["moving_valve_or_piston_cfd_executed"])
            self.assertFalse(report["model_scope"]["independent_model_cross_check"])
            target_history = report["target_independence"]
            self.assertFalse(
                target_history[
                    "requested_power_target_used_as_direct_f38_solver_input"
                ]
            )
            self.assertTrue(
                target_history[
                    "requested_power_target_has_indirect_sampling_ancestry"
                ]
            )
            self.assertFalse(target_history["full_target_independence_proven"])
            self.assertEqual(len(report["source_evidence"]), 7)
            self.assertTrue(
                all(item["hash_verified"] for item in report["source_evidence"].values())
            )
            thermal = report["thermal_architecture_authority"]
            self.assertEqual(thermal["engine_core"], "strict_forced_air_and_dry_sump_oil_only")
            self.assertFalse(thermal["engine_core_liquid_coolant_loop_present"])
            self.assertTrue(thermal["auxiliary_liquid_isolated_from_engine_core"])
            self.assertFalse(thermal["forced_air_network_solved"])

    def test_topology_flows_and_turbo_shaft_solution_are_explicit(self):
        with self.make_temp() as temp_name:
            output = Path(temp_name) / "output"
            result, report = self.run_solver(ROOT, CONTRACT, output)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            variants = {item["variant_id"]: item for item in report["variants"]}
            na = variants[NA]
            turbo = variants[TURBO]
            self.assertEqual(len(na["nodes"]), 5)
            self.assertEqual(len(na["edges"]), 5)
            self.assertIsNone(na["turbo_system"])
            self.assertEqual(len(turbo["nodes"]), 15)
            self.assertEqual(len(turbo["edges"]), 10)
            self.assertAlmostEqual(turbo["mass_balance"]["air_mass_flow_kg_s"], 1.226549579345)
            self.assertAlmostEqual(turbo["mass_balance"]["fuel_mass_flow_kg_s"], 0.111018753507)
            self.assertAlmostEqual(turbo["mass_balance"]["exhaust_mass_flow_kg_s"], 1.337568332852)
            shaft = turbo["turbo_system"]["steady_shaft_balance"]
            self.assertTrue(shaft["capacity_available"])
            self.assertTrue(shaft["converged"])
            self.assertLessEqual(shaft["relative_shaft_power_residual"], 1.0e-9)
            self.assertAlmostEqual(shaft["turbine_flow_fraction"], 0.765696655959)
            self.assertAlmostEqual(shaft["wastegate_bypass_fraction"], 0.234303344041)
            self.assertFalse(turbo["turbo_system"]["compressor_map_digitized"])
            self.assertFalse(turbo["turbo_system"]["turbine_map_digitized"])
            self.assertFalse(turbo["turbo_system"]["turbo_match_validated"])
            self.assertFalse(turbo["turbo_system"]["independent_model_cross_check"])
            self.assertAlmostEqual(
                turbo["turbo_system"]["turbo_mechanical_loss_total_w"],
                5924.95,
                places=2,
            )
            self.assertFalse(
                turbo["turbo_system"]["turbo_mechanical_loss_destination_known"]
            )
            self.assertIsNone(
                turbo["turbo_system"]["turbo_mechanical_loss_thermal_destination"]
            )
            self.assertAlmostEqual(
                turbo["turbo_system"]["turbine_gas_power_selected_total_w"]
                - turbo["turbo_system"]["turbine_shaft_power_selected_total_w"],
                turbo["turbo_system"]["turbo_mechanical_loss_total_w"],
                delta=1.0e-6,
            )
            self.assertFalse(turbo["engine_energy_accounting"]["full_engine_energy_balance_validated"])
            self.assertTrue(
                turbo["engine_energy_accounting"][
                    "nonnegative_arithmetic_complement_constructed"
                ]
            )
            duty = turbo["charge_cooler_required_duty"]
            self.assertTrue(duty["required_duty_computed_from_prescribed_states"])
            self.assertFalse(duty["independent_charge_enthalpy_balance_validated"])
            gates = report["technical_gates"]
            self.assertIn(
                "f33_turbo_algebra_subset_recomputed_from_same_inputs", gates
            )
            self.assertNotIn("f33_values_independently_reproduced", gates)
            self.assertNotIn("arithmetic_energy_identities_closed", gates)

    def test_two_offline_runs_are_byte_identical(self):
        with self.make_temp() as temp_name:
            temp = Path(temp_name)
            first_output = temp / "first"
            second_output = temp / "second"
            first, first_report = self.run_solver(ROOT, CONTRACT, first_output)
            second, second_report = self.run_solver(ROOT, CONTRACT, second_output)
            self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
            self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
            self.assertEqual(first_report, second_report)
            self.assertEqual(
                (first_output / REPORT_NAME).read_bytes(),
                (second_output / REPORT_NAME).read_bytes(),
            )

    def test_report_float_canonicalization_is_significant_digit_stable(self):
        self.assertEqual(self.module.REPORT_SIGNIFICANT_DIGITS, 12)
        self.assertEqual(
            self.module.rounded(1303553.5851016245),
            self.module.rounded(1303553.5851016247),
        )
        self.assertEqual(self.module.rounded(1303553.5851016245), 1303553.5851)
        self.assertEqual(self.module.rounded(-0.0), 0.0)

    def test_committed_evidence_matches_a_fresh_offline_run(self):
        with self.make_temp() as temp_name:
            output = Path(temp_name) / "fresh"
            result, report = self.run_solver(ROOT, CONTRACT, output)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertEqual(report, load(EVIDENCE_REPORT))
            self.assertEqual(
                (output / REPORT_NAME).read_bytes(), EVIDENCE_REPORT.read_bytes()
            )

    def test_mutating_requirement_does_not_change_forward_prediction_or_prove_it(self):
        def change_target(contract):
            variant = next(item for item in contract["variants"] if item["variant_id"] == TURBO)
            variant["target_power_mechanical_hp"] = 1700.0

        with self.make_temp() as temp_name:
            root = Path(temp_name) / "project"
            contract_path = self.materialize_project(root, contract_mutator=change_target)
            result, report = self.run_solver(root, contract_path, root / "output")
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            turbo = next(item for item in report["variants"] if item["variant_id"] == TURBO)
            baseline_result, baseline_report = self.run_solver(
                ROOT, CONTRACT, root / "baseline-output"
            )
            self.assertEqual(
                baseline_result.returncode,
                0,
                baseline_result.stderr or baseline_result.stdout,
            )
            baseline_turbo = next(
                item for item in baseline_report["variants"] if item["variant_id"] == TURBO
            )
            comparison = turbo["target_comparison"]
            self.assertEqual(comparison["target_power_mechanical_hp"], 1700.0)
            self.assertAlmostEqual(comparison["forward_predicted_mechanical_hp"], 1601.195944552682)
            self.assertFalse(
                comparison[
                    "requested_power_target_used_as_direct_f38_solver_input"
                ]
            )
            self.assertTrue(
                comparison[
                    "requested_power_target_has_indirect_sampling_ancestry"
                ]
            )
            self.assertTrue(comparison["inverse_sizing_seed_ancestry_present"])
            self.assertFalse(comparison["full_target_independence_proven"])
            self.assertFalse(comparison["target_power_proven"])
            for key in (
                "nodes",
                "edges",
                "mass_balance",
                "charge_cooler_required_duty",
                "engine_energy_accounting",
                "turbo_system",
            ):
                self.assertEqual(turbo[key], baseline_turbo[key])

    def test_tampered_source_hash_is_rejected_before_execution(self):
        with self.make_temp() as temp_name:
            root = Path(temp_name) / "project"
            contract = copy.deepcopy(self.contract)
            contract["source_evidence"]["cycle_thermal_report_f33"][
                "expected_sha256"
            ] = "0" * 64
            contract_path = root / "twins/reference-917-engine/gas-path-network-f38.json"
            write_json(contract_path, contract)
            result, report = self.run_solver(ROOT, contract_path, root / "output")
            self.assertEqual(result.returncode, 2)
            self.assertIsNone(report)
            self.assertIn("source hash mismatch", result.stderr)

    def test_invalid_upstream_compressor_efficiency_is_rejected_even_when_rehashed(self):
        def mutate_source(source_id, path):
            if source_id != "cycle_thermal_contract_f33":
                return
            value = load(path)
            turbo_variant = next(
                item for item in value["engine_variants"] if item["id"] == TURBO
            )
            turbo_variant["forward_solver_input"]["turbo_screening_input"][
                "compressor_isentropic_efficiency"
            ] = 1.1
            write_json(path, value)

        with self.make_temp() as temp_name:
            root = Path(temp_name) / "project"
            contract_path = self.materialize_project(root, source_mutator=mutate_source)
            result, report = self.run_solver(root, contract_path, root / "output")
            self.assertEqual(result.returncode, 2)
            self.assertIsNone(report)
            self.assertIn("invalid compressor gas properties", result.stderr)

    def test_insufficient_turbine_power_cannot_be_reported_as_converged(self):
        policy = self.contract["numerical_policy"]
        result = self.module.solve_fraction_bisection(100000.0, 90000.0, policy)
        self.assertFalse(result["capacity_available"])
        self.assertFalse(result["converged"])
        self.assertIsNone(result["turbine_flow_fraction"])

    def test_nonfinite_or_nonpositive_inputs_are_rejected(self):
        with self.assertRaises(self.module.F38InputError):
            self.module.finite_number(math.nan, "nan", positive=True)
        with self.assertRaises(self.module.F38InputError):
            self.module.finite_number(-1.0, "negative", positive=True)
        with self.assertRaises(self.module.F38InputError):
            self.module.finite_number(True, "boolean")

    def test_fresh_publish_writes_an_owned_hash_bound_output_marker(self):
        with self.make_temp() as temp_name:
            output = Path(temp_name) / "output"
            result, report = self.run_solver(ROOT, CONTRACT, output)
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            marker = load(output / self.module.OUTPUT_MARKER_NAME)
            self.assertEqual(marker["phase"], "F38")
            self.assertEqual(marker["asset_id"], self.module.OUTPUT_OWNER)
            self.assertEqual(marker["report_name"], REPORT_NAME)
            self.assertEqual(marker["report_sha256"], digest(output / REPORT_NAME))
            self.assertEqual(report["asset_id"], self.module.OUTPUT_OWNER)

    def test_existing_non_f38_directory_is_refused_without_deleting_contents(self):
        with self.make_temp() as temp_name:
            output = Path(temp_name) / "output"
            output.mkdir()
            sentinel = output / "keep-me.txt"
            sentinel.write_text("user data\n", encoding="utf-8")
            result, report = self.run_solver(ROOT, CONTRACT, output)
            self.assertEqual(result.returncode, 2)
            self.assertIsNone(report)
            self.assertIn("refusing to replace non-F38 directory", result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "user data\n")

    def test_failed_atomic_install_restores_previous_owned_output(self):
        with self.make_temp() as temp_name:
            output = Path(temp_name) / "output"
            output.mkdir()
            old_report = {
                "phase": "F38",
                "asset_id": self.module.OUTPUT_OWNER,
                "status": "previous-owned-output",
            }
            write_json(output / REPORT_NAME, old_report)
            sentinel = output / "previous.txt"
            sentinel.write_text("previous\n", encoding="utf-8")
            replacement = {
                "phase": "F38",
                "asset_id": self.module.OUTPUT_OWNER,
                "status": "replacement",
            }
            real_replace = self.module.os.replace
            call_count = 0

            def fail_install_once(source, destination):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise OSError("injected installation failure")
                return real_replace(source, destination)

            with mock.patch.object(
                self.module.os, "replace", side_effect=fail_install_once
            ):
                with self.assertRaises(OSError):
                    self.module.publish(output, replacement)
            self.assertEqual(load(output / REPORT_NAME), old_report)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "previous\n")
            self.assertEqual(call_count, 3)


if __name__ == "__main__":
    unittest.main()
