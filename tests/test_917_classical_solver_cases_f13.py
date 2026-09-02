import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "twins/reference-917-engine/classical-solver-cases-f13.json"
VALIDATOR = (
    ROOT
    / "twins/reference-917-engine/source/validate_classical_solver_cases_f13.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("solver_cases_917_f13", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ClassicalSolverCases917F13Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def evaluate(self, registry: dict) -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "solver-cases-f13.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            return self.module.evaluate(ROOT, path)

    def case(self, registry: dict, case_id: str) -> dict:
        return next(item for item in registry["solver_cases"] if item["id"] == case_id)

    def fact(self, registry: dict, fact_id: str) -> dict:
        return next(item for item in registry["fact_registry"] if item["id"] == fact_id)

    def test_current_registry_passes_without_authorizing_any_action(self):
        report = self.module.evaluate(ROOT, REGISTRY)

        self.assertEqual(report["report_status"], "passed", report["errors"])
        self.assertEqual(
            self.registry["asset_id"], "porsche-917-classical-solver-cases-f13"
        )
        self.assertEqual(
            self.registry["parent_asset_id"],
            "porsche-917-whole-engine-reengineering-f12",
        )
        self.assertEqual(report["solver_case_count"], 12)
        self.assertGreaterEqual(report["fact_count"], 30)
        self.assertGreaterEqual(report["contradiction_count"], 10)
        self.assertFalse(report["solver_execution_authorized"])
        self.assertFalse(report["results_present"])
        self.assertFalse(report["physicsnemo_training_authorized"])
        self.assertFalse(report["fabrication_authorized"])

    def test_required_solver_domains_are_explicit_and_separate(self):
        actual = {
            item["id"]: item["domain"] for item in self.registry["solver_cases"]
        }

        self.assertEqual(actual, self.module.EXPECTED_CASES)
        self.assertIn("structural_thermomechanical_fea_crankcase", actual.values())
        self.assertIn("structural_fatigue_fea_connecting_rods", actual.values())
        self.assertIn("structural_thermomechanical_fea_head_studs", actual.values())
        self.assertIn("multibody_valvetrain_dynamics", actual.values())
        self.assertIn("crankshaft_gear_rotordynamics", actual.values())
        self.assertIn("electrical_ignition_and_safety_network", actual.values())

    def test_five_litre_na_is_a_separate_blocked_baseline(self):
        scenario = next(
            item
            for item in self.registry["solver_scenarios"]
            if item["id"] == "SCENARIO-917-5L-NA"
        )
        facts = {
            item["id"]: item["candidate"]
            for item in self.registry["fact_registry"]
        }

        self.assertEqual(scenario["variant"], "type_912_5_0_na")
        self.assertEqual(facts["FACT-50-DISPLACEMENT"]["value"], 4999.0)
        self.assertEqual(facts["FACT-50-BORE"]["value"], 86.8)
        self.assertEqual(facts["FACT-50-STROKE"]["value"], 70.4)
        self.assertEqual(facts["FACT-50-COMPRESSION"]["value"], 10.5)
        self.assertEqual(facts["FACT-NA-POWER"]["value"], 630.0)
        self.assertEqual(facts["FACT-50-RATED-SPEED"]["value"], 8300.0)
        self.assertEqual(
            scenario["scan_relationship"]["assessment"],
            "provisionally_more_coherent_with_scan_envelope",
        )
        self.assertFalse(scenario["scan_relationship"]["identity_verified"])
        self.assertFalse(scenario["scan_relationship"]["scale_verified"])
        self.assertFalse(scenario["execution_authorized"])

    def test_public_power_claims_remain_separate_documentary_points(self):
        facts = {item["id"]: item for item in self.registry["fact_registry"]}

        self.assertEqual(facts["FACT-TURBO-POWER-1100"]["candidate"]["unit"], "PS")
        self.assertEqual(facts["FACT-TURBO-POWER-1200"]["candidate"]["value"], 1200.0)
        self.assertEqual(facts["FACT-TURBO-POWER-1230"]["variant"], "917_30_1975_record_turbo_5374")
        self.assertEqual(
            facts["FACT-TURBO-POWER-1600-REPORTED"]["usage"],
            "documentary_claim_not_calibration_target",
        )
        self.assertNotEqual(
            facts["FACT-TURBO-POWER-1600-REPORTED"]["candidate"]["unit"],
            facts["FACT-TURBO-POWER-1100"]["candidate"]["unit"],
        )

    def test_ams_evidence_level_divergence_is_explicit_and_conservative(self):
        source = next(
            item
            for item in self.registry["source_registry"]
            if item["source_id"] == "SRC-AMS-917-ENGINE-TECHNICAL-ANALYSIS"
        )

        self.assertEqual(source["research_matrix_evidence_level"], "B")
        self.assertEqual(source["catalog_declared_evidence_level"], "C")
        self.assertEqual(source["effective_evidence_level"], "C_until_reconciled")
        self.assertEqual(
            source["contradiction_ref"],
            "CONTRADICTION-AMS-EVIDENCE-LEVEL",
        )

    def test_fia_homologation_facts_are_primary_but_variant_scoped(self):
        source = next(
            item
            for item in self.registry["source_registry"]
            if item["source_id"] == "SRC-FIA-917-HOMOLOGATION-250"
        )
        facts = {item["id"]: item for item in self.registry["fact_registry"]}

        self.assertEqual(source["rights"], "reference_only")
        self.assertEqual(source["catalog_declared_evidence_level"], "A")
        self.assertEqual(
            source["catalog_path"],
            "catalog/sources/src-fia-917-homologation-250.json",
        )
        self.assertEqual(facts["FACT-4907-BORE"]["candidate"]["value"], 86.0)
        self.assertEqual(facts["FACT-4907-STROKE"]["candidate"]["value"], 70.4)
        self.assertEqual(
            facts["FACT-4907-DISPLACEMENT"]["candidate"]["value"], 4907.28
        )
        self.assertEqual(
            facts["FACT-45-PISTON-COMPRESSION-HEIGHT"]["candidate"]["value"],
            43.0,
        )
        self.assertEqual(
            facts["FACT-45-CRANKPIN-BEARING-DIAMETER"]["candidate"]["value"],
            52.0,
        )
        self.assertEqual(
            facts["FACT-45-CONNECTING-ROD-BIG-END-DIAMETER"]["candidate"]["value"],
            56.0,
        )
        self.assertEqual(
            facts["FACT-4907-CRANKSHAFT-CONSTRUCTION"]["candidate"]["part_number"],
            "912.102.031.00",
        )
        for fact_id in (
            "FACT-4907-BORE",
            "FACT-4907-STROKE",
            "FACT-4907-DISPLACEMENT",
            "FACT-45-PISTON-COMPRESSION-HEIGHT",
            "FACT-45-CRANKPIN-BEARING-DIAMETER",
            "FACT-45-CONNECTING-ROD-BIG-END-DIAMETER",
            "FACT-45-CRANKSHAFT-MASS",
            "FACT-45-CONNECTING-ROD-MASS",
            "FACT-45-PISTON-GROUP-MASS",
            "FACT-45-CRANKSHAFT-CONSTRUCTION",
            "FACT-4907-CRANKSHAFT-CONSTRUCTION",
        ):
            fact = facts[fact_id]
            self.assertFalse(fact["design_lock"], fact_id)
            self.assertEqual(
                fact["source_refs"], ["SRC-FIA-917-HOMOLOGATION-250"], fact_id
            )
            self.assertIn(
                "CONTRADICTION-FIA-VARIANT-TRANSFER",
                fact["contradiction_refs"],
                fact_id,
            )

    def test_fia_catalogue_record_tracks_pdf_without_redistributing_it(self):
        source_path = ROOT / "catalog/sources/src-fia-917-homologation-250.json"
        source = json.loads(source_path.read_text(encoding="utf-8"))

        self.assertEqual(source["source_type"], "official")
        self.assertEqual(source["quality"]["evidence_level"], "A")
        self.assertEqual(source["rights"]["redistribution"], "prohibited")
        self.assertIn(
            "92a03ecef96a68cd227d0ef9f5f7413a7519a04ef24796330fbee4874b2226cd",
            source["notes"],
        )
        self.assertFalse(
            (ROOT / "catalog/sources/homologation_form_number_250_group_4.pdf").exists()
        )

    def test_candidate_ranges_are_only_derived_variant_envelopes(self):
        report = self.module.evaluate(ROOT, REGISTRY)

        self.assertEqual(report["report_status"], "passed")
        for item in self.registry["candidate_ranges"]:
            self.assertEqual(
                item["derivation"], "min_max_of_published_variant_points"
            )
            self.assertIn("not_continuous", item["semantics"])
            self.assertFalse(item["design_lock"])

    def test_invented_candidate_range_is_rejected(self):
        registry = copy.deepcopy(self.registry)
        registry["candidate_ranges"][0]["maximum"] += 1.0

        report = self.evaluate(registry)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "range_maximum_not_derived:RANGE-DOCUMENTED-BORE", report["errors"]
        )

    def test_unsourced_public_fact_is_rejected(self):
        registry = copy.deepcopy(self.registry)
        self.fact(registry, "FACT-50-BORE")["source_refs"] = []

        report = self.evaluate(registry)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn("fact_source_refs_missing:FACT-50-BORE", report["errors"])

    def test_required_unknown_must_block_case_execution(self):
        registry = copy.deepcopy(self.registry)
        case = self.case(registry, "CASE-917-F13-004")
        case["blocking_unknowns"].remove("port_geometry")

        report = self.evaluate(registry)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "solver_required_unknown_not_blocking:CASE-917-F13-004:port_geometry",
            report["errors"],
        )

    def test_candidate_units_must_match_sourced_fact(self):
        registry = copy.deepcopy(self.registry)
        case = self.case(registry, "CASE-917-F13-008")
        stud_length = next(
            item for item in case["inputs"] if item["id"] == "stud_length"
        )
        stud_length["unit"] = "inch"

        report = self.evaluate(registry)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "solver_candidate_unit_mismatch:CASE-917-F13-008:stud_length",
            report["errors"],
        )

    def test_no_output_may_claim_a_simulation_result(self):
        registry = copy.deepcopy(self.registry)
        case = self.case(registry, "CASE-917-F13-005")
        case["expected_outputs"][0]["status"] = "computed"
        case["execution"]["results_present"] = True

        report = self.evaluate(registry)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn("solver_output_claims_result:CASE-917-F13-005:0", report["errors"])
        self.assertIn(
            "solver_results_present_must_be_false:CASE-917-F13-005",
            report["errors"],
        )

    def test_unsourced_numeric_acceptance_threshold_is_rejected(self):
        registry = copy.deepcopy(self.registry)
        registry["gate_profiles"]["GP-FEA"]["acceptance"][
            "numeric_threshold"
        ] = 1.25

        report = self.evaluate(registry)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "gate_unsourced_numeric_threshold:GP-FEA:acceptance", report["errors"]
        )

    def test_open_contradictions_cannot_be_silently_resolved(self):
        registry = copy.deepcopy(self.registry)
        contradiction = next(
            item
            for item in registry["contradictions"]
            if item["id"] == "CONTRADICTION-ARCHITECTURE"
        )
        contradiction["resolution_status"] = "resolved"

        report = self.evaluate(registry)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "contradiction_must_remain_open:CONTRADICTION-ARCHITECTURE",
            report["errors"],
        )

    def test_scan_visual_coherence_cannot_confirm_identity_or_scale(self):
        registry = copy.deepcopy(self.registry)
        scenario = next(
            item
            for item in registry["solver_scenarios"]
            if item["id"] == "SCENARIO-917-5L-NA"
        )
        scenario["scan_relationship"]["identity_verified"] = True

        report = self.evaluate(registry)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "scenario_scan_claim_must_be_false:SCENARIO-917-5L-NA:identity_verified",
            report["errors"],
        )

    def test_physicsnemo_training_cannot_be_enabled_by_configuration(self):
        registry = copy.deepcopy(self.registry)
        registry["authority_boundary"]["physicsnemo_training_authorized"] = True
        registry["physicsnemo_transition"]["training_authorized"] = True
        registry["physicsnemo_transition"]["dataset_ready"] = True
        registry["physicsnemo_transition"]["classical_cases_passed"] = 12

        report = self.evaluate(registry)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "authority_must_be_false:physicsnemo_training_authorized",
            report["errors"],
        )
        self.assertIn("physicsnemo_training_must_be_false", report["errors"])
        self.assertIn("physicsnemo_dataset_ready_must_be_false", report["errors"])
        self.assertIn(
            "physicsnemo_classical_cases_passed_must_be_zero", report["errors"]
        )

    def test_physicsnemo_discovery_links_are_pinned_to_image_version(self):
        for family in self.registry["physicsnemo_transition"]["candidate_model_families"]:
            self.assertIn("/tree/v2.2.1/physicsnemo/models/", family["official_repo_path"])

    def test_every_case_has_blocked_mesh_convergence_correlation_and_acceptance(self):
        profiles = self.registry["gate_profiles"]

        for case in self.registry["solver_cases"]:
            refs = [case["gate_profile_ref"], *case.get("secondary_gate_profile_refs", [])]
            for ref in refs:
                profile = profiles[ref]
                for section in self.module.REQUIRED_GATE_SECTIONS:
                    self.assertEqual(profile[section]["status"], "blocked")
                    self.assertTrue(profile[section]["requirements"])
            self.assertFalse(case["execution"]["authorized"])
            self.assertFalse(case["execution"]["results_present"])


if __name__ == "__main__":
    unittest.main()
