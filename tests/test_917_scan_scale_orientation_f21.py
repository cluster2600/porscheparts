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
    / "twins/reference-917-engine/source/build_scan_scale_orientation_f21.py"
)
CONTRACT = (
    ROOT
    / "twins/reference-917-engine/scan-scale-orientation-acquisition-f21.json"
)
F11_INPUT = ROOT / "twins/reference-917-engine/engineering-inputs-f11.template.json"
F16 = ROOT / "twins/reference-917-engine/kinematic-interface-readiness-f16.json"
F18 = ROOT / "twins/reference-917-engine/boundary-review-execution-evidence-f18.json"
F20 = ROOT / "twins/reference-917-engine/valvetrain-flow-inputs-f20.json"


def load_module():
    spec = importlib.util.spec_from_file_location("scan_scale_orientation_917_f21", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
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


class ScanScaleOrientation917F21Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.f11_input = json.loads(F11_INPUT.read_text(encoding="utf-8"))
        cls.f16 = json.loads(F16.read_text(encoding="utf-8"))
        cls.f18 = json.loads(F18.read_text(encoding="utf-8"))
        cls.f20 = json.loads(F20.read_text(encoding="utf-8"))

    def test_contract_is_deterministic_and_passes_only_fail_closed(self):
        self.assertEqual(self.module.build_contract(ROOT), self.contract)
        report = self.module.evaluate(ROOT, self.contract)
        self.assertEqual(report["report_status"], "passed_fail_closed")
        self.assertEqual(report["contract_errors"], [])
        self.assertTrue(all_false(report["release"]))
        self.assertFalse(report["readiness"]["scale_ready"])
        self.assertFalse(report["readiness"]["orientation_ready"])
        self.assertFalse(report["readiness"]["cad_ready"])
        self.assertTrue(all(value is False for value in report["tracked_sensitive_content"].values()))

    def test_f11_adapter_reuses_exactly_three_generic_control_slots(self):
        adapter = self.contract["f11_compatibility"]
        upstream_scale = self.f11_input["source_identity_and_scale"]
        controls = self.contract["scale_control_slots"]

        self.assertEqual(adapter["adapter_target"], "source_identity_and_scale")
        self.assertEqual(adapter["required_control_count"], 3)
        self.assertEqual(
            adapter["maximum_relative_spread"],
            upstream_scale["maximum_relative_spread"],
        )
        self.assertEqual(len(controls), 3)
        self.assertEqual(
            [item["f11_feature_id"] for item in controls],
            [item["feature_id"] for item in upstream_scale["scale_controls"]],
        )
        self.assertEqual(
            [item["f21_slot_id"] for item in adapter["control_id_mapping"]],
            ["SC-01", "SC-02", "SC-03"],
        )
        self.assertIsNone(adapter["identity_report"])
        self.assertIsNone(adapter["mm_per_obj_unit"])
        self.assertFalse(adapter["ready"])
        identity = self.contract["identity_evidence_slot"]
        self.assertEqual(
            identity["f11_claim_id"],
            "source_identity_and_scale.identity_report",
        )
        self.assertEqual(identity["f11_evidence_kind"], "identity_metrology_report")
        self.assertEqual(identity["status"], "missing")
        self.assertIsNone(identity["physical_asset_or_part_set_id"])
        self.assertIsNone(identity["variant_id"])
        self.assertEqual(identity["provenance"]["review_status"], "missing")

    def test_each_scale_slot_requires_same_observable_feature_provenance_and_uncertainty(self):
        controls = self.contract["scale_control_slots"]
        self.assertEqual(len({item["f11_feature_id"] for item in controls}), 3)
        for control in controls:
            self.assertTrue(control["required"])
            self.assertEqual(control["status"], "missing")
            self.assertEqual(
                control["independence_requirement"],
                "distinct_physical_feature_and_distinct_scan_region",
            )
            self.assertIn("same_feature", control["calibration_basis_required"])
            self.assertIsNone(control["physical_feature_id"])
            self.assertIsNone(control["scan_region_token"])
            self.assertIsNone(control["observable_on_exact_scan"])
            self.assertIsNone(control["same_feature_measured_physically"])
            self.assertIsNone(control["scan_distance_obj_units"])
            self.assertIsNone(control["physical_distance_mm"])
            self.assertIsNone(control["combined_standard_uncertainty_mm"])
            self.assertEqual(control["documentary_source_refs"], [])
            provenance = control["provenance"]
            self.assertIsNone(provenance["evidence_manifest_ref"])
            self.assertIsNone(provenance["evidence_artifact_sha256"])
            self.assertIsNone(provenance["instrument_id"])
            self.assertIsNone(provenance["calibration_certificate_ref"])
            self.assertEqual(provenance["review_status"], "missing")

    def test_orientation_uses_f16_named_datums_without_coordinates(self):
        slots = self.contract["orientation_datum_slots"]
        f16_datums = {
            item["id"]
            for item in self.f16["datum_registry_contract"]["fixed_datums"]
        }
        self.assertEqual(
            [item["f16_datum_ref"] for item in slots],
            [
                "crankshaft_axis",
                "crankcase_split_plane",
                "bank_positive_deck_plane",
            ],
        )
        self.assertTrue(all(item["f16_datum_ref"] in f16_datums for item in slots))
        self.assertEqual(
            {item["role"] for item in slots},
            {"primary_axis", "secondary_plane", "handedness_reference"},
        )
        for item in slots:
            self.assertEqual(item["status"], "missing")
            self.assertIsNone(item["observed_on_exact_scan"])
            self.assertIsNone(item["physical_registration_verified"])
            self.assertIsNone(item["angular_uncertainty_deg"])
            self.assertEqual(item["provenance"]["review_status"], "missing")
        self.assertEqual(self.module._walk_keys(self.contract), [])

    def test_fia_facts_are_documentary_and_cannot_calibrate_scan(self):
        exclusion = self.contract["documentary_dimension_exclusion"]
        self.assertEqual(exclusion["source_id"], "SRC-FIA-917-HOMOLOGATION-250")
        self.assertFalse(exclusion["documentary_source_has_scan_scale_authority"])
        self.assertFalse(exclusion["documentary_source_has_scan_orientation_authority"])
        self.assertFalse(exclusion["exception_without_physical_metrology"])
        prohibited = set(
            exclusion[
                "dimension_refs_without_same_feature_metrology_prohibited_for_scan_calibration"
            ]
        )
        self.assertTrue(
            {
                "FACT-4907-STROKE",
                "FACT-45-PISTON-COMPRESSION-HEIGHT",
                "FACT-45-CRANKPIN-BEARING-DIAMETER",
                "F20-INTAKE-VALVE-OUTER-DIAMETER",
                "F20-INTAKE-VALVE-MAX-LIFT",
                "F20-INTAKE-PORT-DIAMETER",
            }.issubset(prohibited)
        )
        self.assertNotIn("FACT-45-CONNECTING-ROD-BIG-END-DIAMETER", prohibited)
        self.assertIn(
            "FACT-45-CONNECTING-ROD-BIG-END-DIAMETER",
            exclusion["other_documentary_refs_without_scan_calibration_authority"],
        )
        self.assertIn("physical measurement", exclusion["rule"])
        self.assertIn("exact scan", exclusion["rule"])
        self.assertFalse(
            self.f20["authority_boundary"]["cad_dimension_release_authorized"]
        )

    def test_current_f18_state_has_no_scale_units_axis_or_interface_authority(self):
        self.assertEqual(self.f18["inventory"]["confirmed_interface_count"], 0)
        self.assertEqual(
            self.f18["inventory"]["units"], "unconfirmed OBJ coordinate units"
        )
        for gate_id in (
            "scale_confirmed",
            "units_confirmed",
            "axis_semantics_confirmed",
            "semantic_interfaces_confirmed",
            "cad_reconstruction_released",
            "physicsnemo_dataset_released",
            "fabrication_released",
        ):
            self.assertFalse(self.f18["release_gates"][gate_id])
        self.assertEqual(
            self.contract["current_readiness"]["f18_confirmed_interface_count"], 0
        )

    def test_injected_measurement_duplicate_control_or_release_fails_closed(self):
        mutated = copy.deepcopy(self.contract)
        mutated["scale_control_slots"][0]["physical_distance_mm"] = 118.0
        mutated["scale_control_slots"][1]["f11_feature_id"] = "control_A"
        mutated["release_gates"]["scan_scale_verified"] = True

        errors = self.module.validate_contract(ROOT, mutated)
        report = self.module.evaluate(ROOT, mutated)
        self.assertIn("scale_control_template_mismatch", errors)
        self.assertIn("scale_control_independence_contract_mismatch", errors)
        self.assertIn("all_f21_release_gates_must_be_false", errors)
        self.assertEqual(report["report_status"], "failed")
        self.assertTrue(all_false(report["release"]))

    def test_fia_authority_or_empty_sheet_readiness_injection_fails_closed(self):
        mutated = copy.deepcopy(self.contract)
        mutated["documentary_dimension_exclusion"][
            "documentary_source_has_scan_scale_authority"
        ] = True
        mutated["documentary_dimension_exclusion"][
            "dimension_refs_without_same_feature_metrology_prohibited_for_scan_calibration"
        ] = []
        mutated["current_readiness"]["scale_ready"] = True

        errors = self.module.validate_contract(ROOT, mutated)
        self.assertIn("documentary_dimension_exclusion_mismatch", errors)
        self.assertIn("current_readiness_must_remain_empty", errors)
        self.assertTrue(all_false(self.module.evaluate(ROOT, mutated)["release"]))

    def test_unknown_root_or_nested_field_is_rejected_by_canonical_comparison(self):
        root_injection = copy.deepcopy(self.contract)
        root_injection["fabrication_ready"] = True
        root_errors = self.module.validate_contract(ROOT, root_injection)
        self.assertIn("canonical_f21_contract_mismatch", root_errors)
        self.assertTrue(all_false(self.module.evaluate(ROOT, root_injection)["release"]))

        nested_injection = copy.deepcopy(self.contract)
        nested_injection["f11_compatibility"]["invented_authority"] = True
        nested_errors = self.module.validate_contract(ROOT, nested_injection)
        self.assertIn("canonical_f21_contract_mismatch", nested_errors)
        self.assertIn("f11_compatibility_mismatch", nested_errors)
        self.assertTrue(all_false(self.module.evaluate(ROOT, nested_injection)["release"]))

    def test_orientation_coordinate_or_unreviewed_datum_injection_fails_closed(self):
        mutated = copy.deepcopy(self.contract)
        mutated["orientation_datum_slots"][0]["coordinates"] = [0, 0, 0]
        mutated["orientation_datum_slots"][0]["status"] = "verified"
        mutated["orientation_policy"]["orientation_ready"] = True

        errors = self.module.validate_contract(ROOT, mutated)
        self.assertIn("orientation_datum_template_mismatch", errors)
        self.assertIn("orientation_policy_mismatch", errors)
        self.assertTrue(
            any(error.startswith("tracked_coordinate_field_forbidden:") for error in errors)
        )
        self.assertTrue(all_false(self.module.evaluate(ROOT, mutated)["release"]))

    def test_upstream_digest_tampering_and_cli_check_are_rejected_or_passed(self):
        mutated = copy.deepcopy(self.contract)
        mutated["upstream_contracts"][0]["sha256"] = "0" * 64
        errors = self.module.validate_contract(ROOT, mutated)
        self.assertIn("upstream_sha256_mismatch:f11_engineering_input_template", errors)
        self.assertIn("upstream_contract_manifest_mismatch", errors)

        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(ROOT),
                "--contract",
                str(CONTRACT),
                "--check",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["report_status"], "passed_fail_closed")


if __name__ == "__main__":
    unittest.main()
