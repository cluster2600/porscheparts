import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "twins/reference-917-engine/source/build_manufacturing_routing_f19.py"
)
CONTRACT = ROOT / "twins/reference-917-engine/manufacturing-routing-f19.json"
F12 = ROOT / "twins/reference-917-engine/whole-engine-reengineering-f12.json"
F16 = ROOT / "twins/reference-917-engine/kinematic-interface-readiness-f16.json"


def load_module():
    spec = importlib.util.spec_from_file_location("manufacturing_routing_f19", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def all_false(value):
    if isinstance(value, bool):
        return value is False
    if isinstance(value, dict):
        return all(all_false(item) for item in value.values())
    if isinstance(value, list):
        return all(all_false(item) for item in value)
    return True


class ManufacturingRouting917F19Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.f12 = json.loads(F12.read_text(encoding="utf-8"))
        cls.f16 = json.loads(F16.read_text(encoding="utf-8"))

    def test_checked_contract_is_deterministically_generated(self):
        self.assertEqual(self.module.build_contract(ROOT), self.contract)
        report = self.module.evaluate(ROOT, self.contract)
        self.assertEqual(report["report_status"], "passed")
        self.assertEqual(report["contract_errors"], [])
        self.assertTrue(all_false(report["release"]))

    def test_every_f12_family_has_a_fail_closed_route_record(self):
        source = {item["id"]: item for item in self.f12["family_registry"]}
        routed = {
            item["id"]: item for item in self.contract["family_route_registry"]
        }
        self.assertEqual(set(routed), set(source))
        self.assertEqual(len(routed), 31)
        for family_id, item in routed.items():
            self.assertEqual(
                item["source_manufacturing_disposition"],
                source[family_id]["manufacturing_route"],
            )
            self.assertEqual(
                item["functional_disposition"]["route_class"],
                self.module.F12_ROUTE_CLASSES[
                    source[family_id]["manufacturing_route"]
                ],
            )
            self.assertIsNone(item["selected_material_grade"])
            self.assertIsNone(item["selected_process"])
            self.assertIsNone(item["selected_tolerance_set"])
            self.assertFalse(
                item["prototype_disposition"]["functional_use"]
            )
            self.assertTrue(all_false(item["release"]))

    def test_route_classes_distinguish_additive_conventional_purchased_and_unknown(self):
        routed = {
            item["id"]: item["functional_disposition"]["route_class"]
            for item in self.contract["family_route_registry"]
        }
        self.assertEqual(routed["individual_head"], "metal_additive_candidate")
        self.assertEqual(routed["crankcase_half"], "conventional_candidate")
        self.assertEqual(routed["crankshaft"], "conventional_candidate")
        self.assertEqual(routed["individual_cylinder"], "conventional_candidate")
        self.assertEqual(routed["main_bearing"], "purchased_non_printable")
        self.assertEqual(routed["piston_ring"], "purchased_non_printable")
        self.assertEqual(routed["valve_spring"], "purchased_non_printable")
        self.assertEqual(routed["injector"], "purchased_non_printable")
        self.assertEqual(routed["spark_plug"], "purchased_non_printable")
        self.assertEqual(routed["piston"], "unresolved")

    def test_every_f16_semantic_instance_is_explicit_and_inherits_only_a_class(self):
        expected_count = sum(
            item["count"] for item in self.f16["component_instance_contract"]
        )
        records = self.contract["instance_route_registry"]
        self.assertEqual(expected_count, 58)
        self.assertEqual(len(records), expected_count)
        self.assertEqual(len({item["id"] for item in records}), expected_count)
        self.assertTrue(all(item["variant_scope"] == "type_912_5_0_na" for item in records))
        for item in records:
            self.assertEqual(
                item["route_status"], "inherited_classification_only_not_selected"
            )
            self.assertEqual(
                item["prototype_disposition"]["route_class"],
                "printable_prototype",
            )
            self.assertFalse(item["prototype_disposition"]["functional_use"])
            self.assertIsInstance(item["hybrid_completion_may_be_required"], bool)
            self.assertIsNone(item["selected_material_grade"])
            self.assertIsNone(item["selected_process"])
            self.assertIsNone(item["selected_tolerance_set"])
            self.assertTrue(all_false(item["release"]))

    def test_f8_routes_cover_connections_seals_ducts_and_boundaries(self):
        registry = self.contract["f8_interface_route_registry"]
        expected = {
            "mechanical_connections": (18, "hybrid_candidate"),
            "sealing_interfaces": (29, "purchased_non_printable"),
            "ducts": (21, "hybrid_candidate"),
            "external_interfaces": (6, "not_a_part"),
        }
        for key, (count, route_class) in expected.items():
            self.assertEqual(len(registry[key]), count)
            self.assertTrue(
                all(item["route_class"] == route_class for item in registry[key])
            )
            self.assertTrue(all(all_false(item["release"]) for item in registry[key]))

    def test_unbounded_bom_keeps_unknown_counts_and_procured_functions(self):
        backlog = {
            item["id"]: item
            for item in self.contract["unbounded_bom_route_registry"]
        }
        self.assertEqual(len(backlog), 13)
        self.assertTrue(all(item["quantity"] is None for item in backlog.values()))
        self.assertTrue(all(item["dimensions"] is None for item in backlog.values()))
        purchased = {
            "fasteners_and_threaded_hardware",
            "gaskets_and_dynamic_seals",
            "retaining_hardware",
            "additional_bearings_bushings_and_thrust_elements",
            "sensors_and_instrumentation",
            "wiring_ignition_and_connectors",
            "filters_screens_and_flow_conditioners",
        }
        self.assertTrue(
            all(
                backlog[item_id]["route_class"] == "purchased_non_printable"
                for item_id in purchased
            )
        )
        self.assertEqual(
            backlog["fluid_lines_and_fittings"]["route_class"],
            "hybrid_candidate",
        )
        self.assertEqual(
            backlog["internal_fluid_passages"]["route_class"], "not_a_part"
        )

    def test_titanium_and_inconel_controls_select_nothing(self):
        policies = self.contract["conditional_material_policies"]
        for policy_id in ("titanium", "inconel_nickel_superalloy"):
            policy = policies[policy_id]
            self.assertEqual(
                policy["required_evidence_topics"],
                list(self.module.SPECIAL_MATERIAL_TOPICS),
            )
            for field in self.module.SPECIAL_MATERIAL_NULL_FIELDS:
                self.assertIsNone(policy[field])
            self.assertFalse(policy["additive_build_authorized"])
            self.assertFalse(policy["functional_use_authorized"])
        topics = set(policies["titanium"]["required_evidence_topics"])
        self.assertTrue(
            {
                "process_and_parameter_qualification",
                "build_orientation_and_anisotropy",
                "heat_treatment_by_exact_grade_and_route",
                "hip_applicability_and_cycle_if_relevant",
                "machining_allowances_from_measured_distortion",
                "ndt_and_ct_detectability_with_acceptance_criteria",
                "hcf_lcf_thermal_fatigue_and_surface_condition",
                "galvanic_isolation_in_real_temperature_and_fluid",
            }.issubset(topics)
        )

    def test_functional_engine_never_means_fully_printed(self):
        policy = self.contract["functional_engine_policy"]
        self.assertFalse(policy["fully_additively_manufactured"])
        self.assertFalse(policy["mixed_route_qualified"])
        self.assertTrue(policy["mixed_route_required_before_functional_claim"])
        mandatory = set(policy["purchased_functions_remain_mandatory"])
        self.assertTrue(
            {
                "bearings_and_bushings",
                "gaskets_and_dynamic_seals",
                "springs",
                "piston_rings",
                "injectors",
                "spark_plugs",
                "sensors_and_instrumentation",
            }.issubset(mandatory)
        )
        self.assertTrue(all_false(self.contract["release_gates"]))

    def test_route_material_tolerance_or_release_injection_fails_closed(self):
        contract = copy.deepcopy(self.contract)
        contract["family_route_registry"][0]["selected_process"] = "lpbf"
        contract["conditional_material_policies"]["titanium"][
            "selected_grade"
        ] = "invented-grade"
        contract["release_gates"]["functional_engine_authorized"] = True
        contract["family_route_registry"][0]["release"]["functional"] = True

        errors = self.module.validate_contract(ROOT, contract)

        self.assertIn(
            "selection_without_evidence:family_route_registry[0].selected_process",
            errors,
        )
        self.assertIn(
            "material_selection_forbidden:titanium:selected_grade", errors
        )
        self.assertIn("all_release_gates_must_be_false", errors)
        self.assertIn("family_release_must_be_false:crankcase_half", errors)
        self.assertTrue(all_false(self.module.evaluate(ROOT, contract)["release"]))

    def test_missing_instance_route_tamper_and_false_completeness_fail(self):
        contract = copy.deepcopy(self.contract)
        contract["instance_route_registry"].pop()
        contract["family_route_registry"][0]["functional_disposition"][
            "route_class"
        ] = "metal_additive_candidate"
        contract["upstream_contracts"][0]["inventory_complete"] = True

        errors = self.module.validate_contract(ROOT, contract)

        self.assertIn("f16_instance_coverage_mismatch", errors)
        self.assertIn("family_route_class_mismatch:crankcase_half", errors)
        self.assertIn(
            "upstream_completeness_claim_forbidden:whole_engine_f12", errors
        )

    def test_upstream_digest_and_fully_printed_claim_tampering_fail(self):
        contract = copy.deepcopy(self.contract)
        contract["upstream_contracts"][0]["sha256"] = "0" * 64
        contract["functional_engine_policy"]["fully_additively_manufactured"] = True
        contract["asset"][
            "functional_100_percent_means_100_percent_printed"
        ] = True

        errors = self.module.validate_contract(ROOT, contract)

        self.assertIn("upstream_sha256_mismatch:whole_engine_f12", errors)
        self.assertIn("functional_engine_must_not_claim_fully_printed", errors)
        self.assertIn("functional_equals_printed_claim_forbidden", errors)

    def test_taxonomy_material_scope_and_functional_policy_tampering_fail(self):
        contract = copy.deepcopy(self.contract)
        contract["routing_taxonomy"]["unresolved"] = "route selected"
        contract["conditional_material_policies"]["titanium"][
            "candidate_scopes"
        ] = []
        contract["functional_engine_policy"][
            "purchased_functions_remain_mandatory"
        ] = []

        errors = self.module.validate_contract(ROOT, contract)

        self.assertIn(
            "immutable_contract_field_mismatch:routing_taxonomy", errors
        )
        self.assertIn(
            "material_policy_field_mismatch:titanium:candidate_scopes", errors
        )
        self.assertIn("functional_engine_policy_mismatch", errors)

    def test_cli_check_valide_sans_recrire_le_contrat(self):
        before = CONTRACT.read_bytes()
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project-root",
                str(ROOT),
                "--contract",
                str(CONTRACT),
                "--check",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn('"report_status": "passed"', completed.stdout)
        self.assertEqual(CONTRACT.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
