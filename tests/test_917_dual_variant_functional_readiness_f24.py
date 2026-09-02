import copy
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "twins/reference-917-engine/source/build_dual_variant_functional_readiness_f24.py"
)
CONTRACT = (
    ROOT
    / "twins/reference-917-engine/dual-variant-functional-readiness-f24.json"
)


def load_module():
    specification = importlib.util.spec_from_file_location(
        "build_dual_variant_functional_readiness_f24", SCRIPT
    )
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module


def all_false(value):
    if isinstance(value, bool):
        return value is False
    if isinstance(value, dict):
        return all(all_false(item) for item in value.values())
    if isinstance(value, list):
        return all(all_false(item) for item in value)
    return True


class DualVariantFunctionalReadinessF24Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_tracked_contract_is_deterministic_and_fail_closed(self):
        self.assertEqual(self.module.build_contract(ROOT), self.contract)

        report = self.module.evaluate(ROOT, self.contract)

        self.assertEqual(report["report_status"], "passed", report["contract_errors"])
        self.assertEqual(report["variant_count"], 3)
        self.assertEqual(report["solver_input_template_count"], 24)
        self.assertTrue(all_false(report["release"]))
        self.assertTrue(all_false(self.contract["release_gates"]))

    def test_all_upstreams_are_tracked_and_digest_bound(self):
        records = {item["id"]: item for item in self.contract["upstream_contracts"]}

        self.assertEqual(set(records), set(self.module.UPSTREAMS))
        for source_id, specification in self.module.UPSTREAMS.items():
            record = records[source_id]
            self.assertEqual(record["path"], specification["path"])
            self.assertEqual(record["sha256"], specification["sha256"])
            self.assertEqual(
                self.module.sha256(ROOT / record["path"]), record["sha256"]
            )
            self.assertFalse(record["geometry_authority"])
            self.assertFalse(record["solver_execution_authority"])
            self.assertFalse(record["manufacturing_authority"])

    def test_case_008_and_011_applicability_is_exact(self):
        matrix = {item["case_id"]: item for item in self.contract["case_matrix"]}

        self.assertEqual(
            matrix["CASE-917-F13-008"]["applicability"],
            {
                "type_912_5_0_na": "required",
                "917_30_1973_turbo_5374": "blocked_variant_scope_missing",
                "917_30_1975_record_turbo_5374": "not_in_record_documentary_scope",
            },
        )
        self.assertEqual(
            matrix["CASE-917-F13-011"]["applicability"],
            {
                "type_912_5_0_na": "not_applicable_turbo_only",
                "917_30_1973_turbo_5374": "required",
                "917_30_1975_record_turbo_5374": "required",
            },
        )

    def test_null_templates_cover_two_engineering_branches_and_1975_record(self):
        templates = self.contract["solver_input_templates"]
        by_variant = {
            variant_id: [
                item for item in templates if item["variant_id"] == variant_id
            ]
            for variant_id in self.module.TARGET_VARIANTS
        }

        self.assertEqual(len(templates), 24)
        self.assertEqual(len(by_variant["type_912_5_0_na"]), 11)
        self.assertEqual(len(by_variant["917_30_1973_turbo_5374"]), 11)
        self.assertEqual(len(by_variant["917_30_1975_record_turbo_5374"]), 2)
        self.assertEqual(
            tuple(item["case_id"] for item in by_variant["type_912_5_0_na"]),
            self.module.EXPECTED_CASE_REFS["type_912_5_0_na"],
        )
        self.assertEqual(
            tuple(
                item["case_id"]
                for item in by_variant["917_30_1973_turbo_5374"]
            ),
            self.module.EXPECTED_CASE_REFS["917_30_1973_turbo_5374"],
        )
        self.assertEqual(
            tuple(
                item["case_id"]
                for item in by_variant["917_30_1975_record_turbo_5374"]
            ),
            self.module.EXPECTED_CASE_REFS["917_30_1975_record_turbo_5374"],
        )
        for template in templates:
            for item in template["inputs"]:
                self.assertIsNone(item["value"])
                self.assertIsNone(item["uncertainty"])
                self.assertIsNone(item["evidence_manifest_ref"])
                self.assertIsNone(item["review_status"])
                self.assertFalse(item["candidate_adopted"])
            for item in template["expected_outputs"]:
                self.assertIsNone(item["value"])
                self.assertIsNone(item["artifact_ref"])
            self.assertTrue(all_false(template["geometry_state"]))
            self.assertTrue(all_false(template["execution"]))
            self.assertFalse(template["physicsnemo_export"]["authorized"])
            self.assertIsNone(template["physicsnemo_export"]["sample_manifest"])

    def test_variant_templates_do_not_transfer_cylinder_or_intercooler_facts(self):
        templates = {
            (item["variant_id"], item["case_id"]): item
            for item in self.contract["solver_input_templates"]
        }
        for variant_id, (input_id, fact_id) in (
            self.module.CYLINDER_COUNT_INPUT_BY_VARIANT.items()
        ):
            inputs = templates[(variant_id, "CASE-917-F13-001")]["inputs"]
            counts = [item for item in inputs if item["quantity"] == "cylinder_count"]
            self.assertEqual(len(counts), 1)
            self.assertEqual((counts[0]["id"], counts[0]["candidate_ref"]), (input_id, fact_id))

        turbo_inputs = {
            item["id"]
            for item in templates[
                ("917_30_1973_turbo_5374", "CASE-917-F13-011")
            ]["inputs"]
        }
        record_inputs = {
            item["id"]
            for item in templates[
                ("917_30_1975_record_turbo_5374", "CASE-917-F13-011")
            ]["inputs"]
        }
        self.assertIn("turbo_count", turbo_inputs)
        self.assertIn("intercooler_1973_status", turbo_inputs)
        self.assertNotIn("intercooler_1975_status", turbo_inputs)
        self.assertNotIn("turbocharger_count_1975_record", turbo_inputs)
        self.assertIn("turbocharger_count_1975_record", record_inputs)
        self.assertIn("intercooler_1975_status", record_inputs)
        self.assertIn("intercooler_maps_1975_record", record_inputs)
        self.assertNotIn("turbo_count", record_inputs)
        self.assertNotIn("intercooler_1973_status", record_inputs)
        self.assertNotIn("boost_claim", record_inputs)
        self.assertNotIn("spool_claim", record_inputs)
        self.assertFalse(
            any(
                "intercooler" in item
                for item in templates[
                    ("917_30_1973_turbo_5374", "CASE-917-F13-011")
                ]["blocking_unknowns"]
            )
        )
        self.assertIn(
            "intercooler_maps_1975_record",
            templates[
                ("917_30_1975_record_turbo_5374", "CASE-917-F13-011")
            ]["blocking_unknowns"],
        )

    def test_input_applicability_never_relabels_evidence_variant_scope(self):
        templates = {
            (item["variant_id"], item["case_id"]): item
            for item in self.contract["solver_input_templates"]
        }
        duct = templates[("type_912_5_0_na", "CASE-917-F13-004")]
        intake = next(
            item for item in duct["inputs"] if item["id"] == "intake_valve_diameter"
        )
        self.assertEqual(intake["input_variant_scope"], ["type_912_5_0_na"])
        self.assertEqual(intake["source_variant_scope"], [])
        self.assertIsNone(intake["candidate_ref"])

        structural = templates[("type_912_5_0_na", "CASE-917-F13-006")]
        bearing_count = next(
            item for item in structural["inputs"] if item["id"] == "main_bearing_count"
        )
        self.assertEqual(bearing_count["input_variant_scope"], ["type_912_5_0_na"])
        self.assertEqual(bearing_count["source_variant_scope"], ["917_unspecified"])

        for template in self.contract["solver_input_templates"]:
            for item in template["inputs"]:
                if item["candidate_ref"] is None:
                    self.assertEqual(
                        item["source_variant_scope"],
                        [],
                        f"{template['template_id']}:{item['id']}",
                    )

    def test_relabelled_evidence_variant_scope_is_rejected(self):
        contract = copy.deepcopy(self.contract)
        template = next(
            item
            for item in contract["solver_input_templates"]
            if item["variant_id"] == "917_30_1975_record_turbo_5374"
            and item["case_id"] == "CASE-917-F13-011"
        )
        intercooler = next(
            item for item in template["inputs"] if item["id"] == "intercooler_1975_status"
        )
        intercooler["source_variant_scope"] = ["917_30_1973_turbo_5374"]

        report = self.module.evaluate(ROOT, contract)

        self.assertEqual(report["report_status"], "failed")
        self.assertTrue(
            any(
                error.startswith("template_source_variant_scope_mismatch:")
                for error in report["contract_errors"]
            )
        )

    def test_scan_remains_unbound_and_numerical_proximity_is_not_selection(self):
        scan = self.contract["scan_evidence_boundary"]
        na = self.contract["variant_crosswalk"][0]

        self.assertEqual(scan["closest_numerical_candidate_id"], "917_5_0_na")
        self.assertIsNone(scan["selected_variant_id"])
        self.assertFalse(scan["scan_binding_authorized"])
        self.assertFalse(scan["identity_verified"])
        self.assertFalse(scan["scale_verified"])
        self.assertFalse(scan["dimensional_fit_verified"])
        self.assertFalse(scan["local_report_required_for_contract_validation"])
        self.assertEqual(na["canonical_variant_id"], "type_912_5_0_na")
        self.assertIn("scan_numerical_proximity", na["selection_basis_excludes"])

    def test_f10_is_display_only_and_f22_is_schema_only(self):
        crosswalk = {
            item["canonical_variant_id"]: item
            for item in self.contract["variant_crosswalk"]
        }
        turbo = crosswalk["917_30_1973_turbo_5374"]
        na = crosswalk["type_912_5_0_na"]

        self.assertEqual(turbo["f10_visual_variant_id"], "917_30_turbo_5374")
        self.assertEqual(turbo["f10_mapping_scope"], "display_only_visual_lineage")
        self.assertFalse(turbo["f10_identity_equivalent"])
        self.assertIsNone(turbo["f22_cad_variant_id"])
        self.assertIsNone(na["f22_cad_variant_id"])
        self.assertEqual(
            na["nontransferable_contract_refs"],
            [
                {
                    "contract_id": "parametric_cad_f22",
                    "variant_id": "type_912_4_5_na",
                    "reuse_scope": "schema_and_null_policy_only",
                }
            ],
        )

    def test_1975_record_crosswalk_stays_documentary_and_unknown(self):
        crosswalk = {
            item["canonical_variant_id"]: item
            for item in self.contract["variant_crosswalk"]
        }
        record = crosswalk["917_30_1975_record_turbo_5374"]
        self.assertEqual(record["parent_1973_variant_ref"], "917_30_1973_turbo_5374")
        self.assertFalse(record["hardware_identity_equivalent_to_1973"])
        self.assertEqual(
            record["intercooler_status_fact_ref"],
            "FACT-INTERCOOLER-1975-STATUS",
        )
        for key in (
            "intercooler_count",
            "intercooler_geometry",
            "intercooler_maps",
            "turbocharger_count",
        ):
            self.assertIsNone(record[key])
        self.assertFalse(record["geometry_ready"])
        self.assertFalse(record["solver_ready"])

    def test_1975_record_hardware_inference_is_rejected(self):
        contract = copy.deepcopy(self.contract)
        record = next(
            item
            for item in contract["variant_crosswalk"]
            if item["canonical_variant_id"] == "917_30_1975_record_turbo_5374"
        )
        record["hardware_identity_equivalent_to_1973"] = True
        record["turbocharger_count"] = 2

        report = self.module.evaluate(ROOT, contract)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn("record_1975_scope_mismatch", report["contract_errors"])

    def test_reported_1600_hp_and_physicsnemo_remain_non_authoritative(self):
        turbo = self.contract["variant_crosswalk"][1]
        physicsnemo = self.contract["physicsnemo_boundary"]

        self.assertEqual(
            turbo["reported_1600_hp_role"],
            "documentary_only_not_boundary_condition",
        )
        self.assertEqual(physicsnemo["accepted_samples"], 0)
        self.assertEqual(physicsnemo["classical_cases_passed"], 0)
        self.assertTrue(physicsnemo["variant_case_pair_validation_required"])
        for key in (
            "dataset_ready",
            "model_selected",
            "training_authorized",
            "inference_authorized",
            "raw_scan_or_f10_proxy_allowed",
        ):
            self.assertFalse(physicsnemo[key])

    def test_a_populated_input_value_is_rejected(self):
        contract = copy.deepcopy(self.contract)
        contract["solver_input_templates"][0]["inputs"][0]["value"] = 12

        report = self.module.evaluate(ROOT, contract)

        self.assertEqual(report["report_status"], "failed")
        self.assertTrue(
            any(
                error.startswith("template_input_value_must_be_null:")
                for error in report["contract_errors"]
            )
        )
        self.assertTrue(all_false(report["release"]))

    def test_an_open_gate_is_rejected_without_opening_report_release(self):
        contract = copy.deepcopy(self.contract)
        contract["release_gates"]["na_solver_execution_authorized"] = True
        contract["solver_input_templates"][0]["execution"]["authorized"] = True

        report = self.module.evaluate(ROOT, contract)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn("release_gates_must_remain_false", report["contract_errors"])
        self.assertTrue(
            any(
                error.startswith("template_execution_gate_open:")
                for error in report["contract_errors"]
            )
        )
        self.assertTrue(all_false(report["release"]))

    def test_a_wrong_variant_case_pair_is_rejected(self):
        contract = copy.deepcopy(self.contract)
        contract["solver_input_templates"][7]["variant_id"] = (
            "917_30_1973_turbo_5374"
        )

        report = self.module.evaluate(ROOT, contract)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "solver_input_template_pairs_mismatch", report["contract_errors"]
        )

    def test_check_mode_is_read_only_and_rejects_tampering(self):
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        with tempfile.TemporaryDirectory() as temp_dir:
            contract_path = Path(temp_dir) / "f24.json"
            contract_path.write_text(
                json.dumps(self.contract, indent=2) + "\n", encoding="utf-8"
            )
            before = contract_path.read_bytes()
            passed = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--root",
                    str(ROOT),
                    "--output",
                    str(contract_path),
                    "--check",
                ],
                capture_output=True,
                check=False,
                env=environment,
                text=True,
            )
            self.assertEqual(passed.returncode, 0, passed.stderr)
            self.assertEqual(contract_path.read_bytes(), before)

            tampered = copy.deepcopy(self.contract)
            tampered["release_gates"]["functional_variants_authorized"] = True
            contract_path.write_text(json.dumps(tampered), encoding="utf-8")
            failed = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--root",
                    str(ROOT),
                    "--output",
                    str(contract_path),
                    "--check",
                ],
                capture_output=True,
                check=False,
                env=environment,
                text=True,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("release_gates_must_remain_false", failed.stdout)


if __name__ == "__main__":
    unittest.main()
