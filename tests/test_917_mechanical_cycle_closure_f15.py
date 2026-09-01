import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/mechanical-cycle-closure-f15.json"
BENCHMARK = ROOT / "twins/reference-917-engine/mechanical-benchmark-f14.json"
REGISTRY = ROOT / "twins/reference-917-engine/classical-solver-cases-f13.json"
RUNNER = ROOT / "twins/reference-917-engine/source/run_mechanical_cycle_closure_f15.py"


def load_module():
    spec = importlib.util.spec_from_file_location("mechanical_cycle_closure_917_f15", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class MechanicalCycleClosure917F15Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.benchmark = json.loads(BENCHMARK.read_text(encoding="utf-8"))
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.report = cls.module.build_report(
            cls.contract,
            cls.benchmark,
            cls.registry,
            contract_path=CONTRACT,
            benchmark_path=BENCHMARK,
            registry_path=REGISTRY,
            project_root=ROOT,
        )

    def validate(
        self,
        contract: dict | None = None,
        benchmark: dict | None = None,
        registry: dict | None = None,
    ) -> list[str]:
        return self.module.validate_contract(
            contract or self.contract,
            benchmark or self.benchmark,
            registry or self.registry,
            ROOT,
        )

    def result_case(self, case_id: str) -> dict:
        return next(item for item in self.report["cases"] if item["id"] == case_id)

    def test_current_contract_passes_and_executes_only_mechanical_closure(self):
        self.assertEqual(self.validate(), [])
        self.assertEqual(
            self.report["status"],
            "passed_sourced_mechanical_cycle_closure_thermodynamic_blocked",
        )
        self.assertEqual(
            {item["id"] for item in self.report["cases"]},
            {
                "CASE-917-F15-001-5L-NA",
                "CASE-917-F15-001-5374-TURBO-1973",
            },
        )
        self.assertTrue(self.report["model"]["mechanical_cycle_closure_executed"])
        self.assertFalse(self.report["model"]["thermodynamic_solver_executed"])
        self.assertFalse(self.report["model"]["cantera_executed"])
        self.assertFalse(self.report["model"]["generic_engine_defaults_used"])

    def test_five_litre_cycle_energy_values_are_reproducible(self):
        result = self.result_case("CASE-917-F15-001-5L-NA")["derived"]

        self.assertAlmostEqual(result["engine_cycles_per_second"], 69.166666666667, places=11)
        self.assertAlmostEqual(result["firing_events_per_second"], 830.0, places=9)
        self.assertAlmostEqual(result["brake_work_per_engine_cycle_j"], 6699.241626506023, places=9)
        self.assertAlmostEqual(result["brake_work_per_cylinder_firing_j"], 558.270135542169, places=9)
        self.assertAlmostEqual(result["torque_reconstructed_nm"], 533.108709912711, places=9)
        self.assertAlmostEqual(result["bmep_reconstructed_bar"], 13.401163485709, places=9)

    def test_turbo_cycle_energy_values_are_reproducible(self):
        result = self.result_case("CASE-917-F15-001-5374-TURBO-1973")["derived"]

        self.assertAlmostEqual(result["engine_cycles_per_second"], 65.0, places=9)
        self.assertAlmostEqual(result["firing_events_per_second"], 780.0, places=9)
        self.assertAlmostEqual(result["brake_work_per_engine_cycle_j"], 12446.901923076923, places=9)
        self.assertAlmostEqual(result["brake_work_per_cylinder_firing_j"], 1037.241826923077, places=9)
        self.assertAlmostEqual(result["torque_reconstructed_nm"], 990.492983618855, places=9)
        self.assertAlmostEqual(result["bmep_reconstructed_bar"], 23.161335919384, places=9)

    def test_each_identity_closes_but_is_not_physical_validation(self):
        for result in self.report["cases"]:
            closure = result["numerical_closure"]
            self.assertTrue(closure["power_identity_passed"])
            self.assertTrue(closure["torque_identity_passed"])
            self.assertTrue(closure["bmep_identity_passed"])
            self.assertEqual(
                closure["role"],
                "algebraic_regression_oracle_not_physical_validation",
            )
            self.assertTrue(
                result["claim_limits"]["reported_power_is_input_not_prediction"]
            )
            self.assertFalse(
                result["claim_limits"]["instantaneous_component_loads_computed"]
            )

    def test_thermodynamic_case_and_1600_hp_remain_fail_closed(self):
        readiness = self.report["thermodynamic_readiness"]
        claim = self.report["documentary_uncomputed_claims"][0]

        self.assertFalse(readiness["ready"])
        self.assertFalse(readiness["execution_authorized"])
        self.assertIsNone(readiness["backend_selected"])
        self.assertEqual(
            set(readiness["all_blockers"]),
            self.module.EXPECTED_THERMODYNAMIC_BLOCKERS,
        )
        self.assertEqual(
            set(readiness["missing_required_inputs"]),
            self.module.EXPECTED_REQUIRED_UNKNOWN_INPUTS,
        )
        self.assertEqual(claim["reported_power"]["value"], 1600.0)
        self.assertIsNone(claim["reported_power_speed_rpm"])
        self.assertEqual(claim["proof_status"], "not_proven")
        self.assertFalse(self.report["physicsnemo_dataset_gate"]["dataset_ready"])
        self.assertEqual(self.report["physicsnemo_dataset_gate"]["sample_count_added"], 0)

    def test_contract_rejects_thermodynamic_or_cantera_authorization(self):
        mutated = copy.deepcopy(self.contract)
        mutated["authority_boundary"]["thermodynamic_solver_execution_authorized"] = True
        mutated["authority_boundary"]["cantera_execution_authorized"] = True

        errors = self.validate(contract=mutated)

        self.assertIn(
            "authority_boundary.thermodynamic_solver_execution_authorized: must remain false",
            errors,
        )
        self.assertIn(
            "authority_boundary.cantera_execution_authorized: must remain false",
            errors,
        )

    def test_contract_rejects_training_fabrication_or_start_authorization(self):
        mutated = copy.deepcopy(self.contract)
        mutated["authority_boundary"]["physicsnemo_training_authorized"] = True
        mutated["authority_boundary"]["fabrication_authorized"] = True
        mutated["authority_boundary"]["metal_print_authorized"] = True
        mutated["authority_boundary"]["engine_start_authorized"] = True

        errors = self.validate(contract=mutated)

        for flag in (
            "physicsnemo_training_authorized",
            "fabrication_authorized",
            "metal_print_authorized",
            "engine_start_authorized",
        ):
            self.assertIn(f"authority_boundary.{flag}: must remain false", errors)

    def test_contract_rejects_missing_blocker_or_unblocked_f13_execution(self):
        mutated_contract = copy.deepcopy(self.contract)
        mutated_contract["thermodynamic_blockers_required"].remove("friction_model")
        mutated_registry = copy.deepcopy(self.registry)
        case = next(
            item
            for item in mutated_registry["solver_cases"]
            if item["id"] == "CASE-917-F13-001"
        )
        case["execution"]["authorized"] = True
        case["execution"]["results_present"] = True

        errors = self.validate(
            contract=mutated_contract,
            registry=mutated_registry,
        )

        self.assertIn(
            "thermodynamic_blockers_required: expected the seven F13 blockers",
            errors,
        )
        self.assertIn("CASE-917-F13-001.execution.authorized: must remain false", errors)
        self.assertIn("CASE-917-F13-001.execution.results_present: must remain false", errors)

    def test_parent_f14_provenance_cannot_be_replaced_or_extended(self):
        mutated = copy.deepcopy(self.benchmark)
        mutated["cases"][0]["fact_refs"]["reported_power"] = "FACT-TURBO-POWER-1200"
        generic = copy.deepcopy(mutated["cases"][1])
        generic["id"] = "CASE-917-F14-001A-GENERIC"
        mutated["cases"].append(generic)

        errors = self.validate(benchmark=mutated)

        self.assertIn("parent_benchmark.cases: exact F14 anchor set required", errors)
        self.assertTrue(
            any(error.startswith("parent_f14.cases") for error in errors),
            errors,
        )

    def test_runner_has_no_cantera_numpy_or_hidden_engine_calibration(self):
        source = RUNNER.read_text(encoding="utf-8").lower()

        self.assertNotIn("import cantera", source)
        self.assertNotIn("import numpy", source)
        self.assertNotIn("wiebe", source)
        self.assertNotIn("isentropic_efficiency", source)

    def test_cli_writes_the_same_report_to_an_explicit_work_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "work" / "mechanical-cycle-closure-results.json"
            completed = subprocess.run(
                [
                    "python3",
                    str(RUNNER),
                    "--project-root",
                    str(ROOT),
                    "--contract",
                    str(CONTRACT),
                    "--benchmark",
                    str(BENCHMARK),
                    "--registry",
                    str(REGISTRY),
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            generated = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(generated, self.report)
        self.assertIn("thermodynamic/Cantera execution remains blocked", completed.stdout)


if __name__ == "__main__":
    unittest.main()
