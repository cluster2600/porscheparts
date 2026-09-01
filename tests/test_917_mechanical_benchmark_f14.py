import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "twins/reference-917-engine/mechanical-benchmark-f14.json"
REGISTRY = ROOT / "twins/reference-917-engine/classical-solver-cases-f13.json"
RUNNER = ROOT / "twins/reference-917-engine/source/run_mechanical_benchmark_f14.py"


def load_module():
    spec = importlib.util.spec_from_file_location("mechanical_benchmark_917_f14", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class MechanicalBenchmark917F14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.report = cls.module.build_report(
            cls.config,
            cls.registry,
            config_path=CONFIG,
            registry_path=REGISTRY,
            project_root=ROOT,
        )

    def validate(self, payload: dict, registry: dict | None = None) -> list[str]:
        return self.module.validate_contract(payload, registry or self.registry, ROOT)

    def result_case(self, case_id: str) -> dict:
        return next(item for item in self.report["cases"] if item["id"] == case_id)

    def test_current_contract_passes_and_executes_only_two_documentary_anchors(self):
        self.assertEqual(self.validate(self.config), [])
        self.assertEqual(
            self.report["status"],
            "passed_sourced_algebraic_benchmark_not_physics_simulation",
        )
        self.assertEqual(
            {item["id"] for item in self.report["cases"]},
            {
                "CASE-917-F14-001A-5L-NA",
                "CASE-917-F14-001A-5374-TURBO-1973",
            },
        )
        self.assertTrue(self.report["model"]["algebraic_benchmark_executed"])
        self.assertFalse(self.report["model"]["thermodynamic_solver_executed"])
        self.assertFalse(self.report["model"]["generic_engine_defaults_used"])

    def test_five_litre_na_values_are_reproducible(self):
        result = self.result_case("CASE-917-F14-001A-5L-NA")["derived"]

        self.assertAlmostEqual(result["calculated_displacement_cm3"], 4999.001152861556, places=9)
        self.assertAlmostEqual(result["published_displacement_m3"], 0.004999, places=12)
        self.assertAlmostEqual(result["displacement_difference_cm3"], 0.001152861556, places=9)
        self.assertAlmostEqual(result["displacement_relative_difference_percent"], 0.000023061843, places=12)
        self.assertAlmostEqual(result["reported_power_kw"], 463.3642125, places=7)
        self.assertAlmostEqual(result["torque_nm"], 533.108709912711, places=9)
        self.assertAlmostEqual(
            result["four_stroke_bmep_using_published_displacement_bar"],
            13.401163485709,
            places=9,
        )
        self.assertAlmostEqual(result["mean_piston_speed_m_s"], 19.477333333333, places=9)

    def test_5374_turbo_1973_values_are_reproducible(self):
        result = self.result_case("CASE-917-F14-001A-5374-TURBO-1973")["derived"]

        self.assertAlmostEqual(result["calculated_displacement_cm3"], 5374.385384349132, places=9)
        self.assertAlmostEqual(result["published_displacement_m3"], 0.005374, places=12)
        self.assertAlmostEqual(result["displacement_difference_cm3"], 0.385384349132, places=9)
        self.assertAlmostEqual(result["displacement_relative_difference_percent"], 0.00717127557, places=10)
        self.assertAlmostEqual(result["reported_power_kw"], 809.048625, places=7)
        self.assertAlmostEqual(result["torque_nm"], 990.492983618855, places=9)
        self.assertAlmostEqual(
            result["four_stroke_bmep_using_published_displacement_bar"],
            23.161335919384,
            places=9,
        )
        self.assertAlmostEqual(result["mean_piston_speed_m_s"], 18.304, places=9)

    def test_every_input_retains_field_level_fact_and_source_provenance(self):
        for result in self.report["cases"]:
            pair_sources = set(result["power_speed_pair_provenance"]["source_refs"])
            inputs = result["resolved_inputs"]
            self.assertEqual(set(inputs), set(self.module.EXPECTED_FIELDS))
            for field in inputs.values():
                self.assertRegex(field["fact_ref"], r"^FACT-")
                self.assertTrue(field["source_refs"])
                self.assertFalse(field["design_lock"])
            self.assertTrue(
                pair_sources <= set(inputs["reported_power"]["source_refs"])
            )
            self.assertTrue(
                pair_sources <= set(inputs["reported_power_speed"]["source_refs"])
            )

    def test_1600_hp_without_speed_remains_uncomputed_and_unproven(self):
        claim = self.report["documentary_uncomputed_claims"][0]

        self.assertEqual(claim["reported_power"]["value"], 1600.0)
        self.assertEqual(claim["reported_power"]["unit"], "hp")
        self.assertIsNone(claim["reported_power_speed_rpm"])
        self.assertEqual(claim["proof_status"], "not_proven")
        self.assertTrue(claim["status"].startswith("blocked_missing_"))
        self.assertTrue(
            all(value is None for value in claim["derived_mechanical_quantities"].values())
        )
        self.assertFalse(self.report["physicsnemo_dataset_gate"]["dataset_ready"])
        self.assertFalse(self.report["physicsnemo_dataset_gate"]["training_authorized"])

    def test_contract_rejects_a_substituted_power_fact(self):
        mutated = copy.deepcopy(self.config)
        mutated["cases"][0]["fact_refs"]["reported_power"] = "FACT-TURBO-POWER-1200"

        errors = self.validate(mutated)

        self.assertIn(
            "cases[0].fact_refs: must match the approved F13 facts",
            errors,
        )

    def test_contract_rejects_a_pair_source_not_common_to_power_and_speed(self):
        mutated = copy.deepcopy(self.config)
        mutated["cases"][1]["power_speed_pair_source_refs"] = [
            "SRC-PORSCHE-NEWSROOM-91730-TURBO"
        ]

        errors = self.validate(mutated)

        self.assertIn(
            "cases[1].power_speed_pair_source_refs: unexpected pair provenance",
            errors,
        )

    def test_contract_rejects_a_generic_or_interpolated_third_case(self):
        mutated = copy.deepcopy(self.config)
        generic = copy.deepcopy(mutated["cases"][0])
        generic["id"] = "CASE-917-F14-001A-GENERIC"
        generic["variant"] = "generic_interpolated_engine"
        mutated["cases"].append(generic)

        errors = self.validate(mutated)

        self.assertIn(
            "cases: expected exactly the sourced 5.0L NA and 5.374L turbo 1973 cases",
            errors,
        )
        self.assertIn("cases[2].id: unauthorized case CASE-917-F14-001A-GENERIC", errors)

    def test_contract_rejects_fabricated_speed_or_1600_hp_proof(self):
        mutated = copy.deepcopy(self.config)
        claim = mutated["documentary_uncomputed_claims"][0]
        claim["reported_power_speed_rpm"] = 8000
        claim["derived_mechanical_quantities"] = {"torque_nm": 1424.0}
        claim["proof_status"] = "proven"
        mutated["authority_boundary"]["performance_claim_authorized"] = True

        errors = self.validate(mutated)

        self.assertIn(
            "documentary_uncomputed_claims[0].reported_power_speed_rpm: must remain null",
            errors,
        )
        self.assertIn(
            "documentary_uncomputed_claims[0].derived_mechanical_quantities: must remain null",
            errors,
        )
        self.assertIn(
            "documentary_uncomputed_claims[0].proof_status: must remain not_proven",
            errors,
        )
        self.assertIn(
            "authority_boundary.performance_claim_authorized: must remain false",
            errors,
        )

    def test_runner_has_no_cantera_or_hidden_engine_default_dependency(self):
        source = RUNNER.read_text(encoding="utf-8").lower()

        self.assertNotIn("import cantera", source)
        self.assertNotIn("import numpy", source)
        self.assertNotIn("volumetric_efficiency", source)
        self.assertNotIn("boost_pressure", source)

    def test_cli_writes_the_same_report_to_an_explicit_work_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "work" / "mechanical-benchmark-results.json"
            completed = subprocess.run(
                [
                    "python3",
                    str(RUNNER),
                    "--project-root",
                    str(ROOT),
                    "--config",
                    str(CONFIG),
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
        self.assertIn("1600 hp remains uncomputed", completed.stdout)


if __name__ == "__main__":
    unittest.main()
