import copy
import hashlib
import importlib.util
import json
import math
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/reference-917-engine/source/build_scan_metrology_f13.py"
CONTRACT = ROOT / "twins/reference-917-engine/scan-metrology-f13.json"
LOCAL_INTERFACES = ROOT / "work/917-engine/vast-output/reports/interfaces.json"


def load_module():
    spec = importlib.util.spec_from_file_location("scan_metrology_917_f13", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synthetic_interfaces() -> dict:
    longitudinal = [-354.5, -236.5, -118.5, 54.5, 172.5, 290.5]
    banks = {}
    for bank_id, sign in (("positive", 1.0), ("negative", -1.0)):
        banks[bank_id] = []
        for index, position in enumerate(longitudinal):
            diameter = 86.8 + (index - 2.5) * 0.08 + (0.03 if sign < 0 else 0.0)
            banks[bank_id].append(
                {
                    "hough_score": 0.60,
                    "center_longitudinal_vertical": [position, sign * index * 0.2],
                    "diameter_obj_units": diameter,
                    "circle_fit_p95_obj_units": 0.25,
                    "rim_outward_depth_mode_obj_units": 180.0,
                    "ring_inliers": 1200 + index,
                    "center_scan_coordinates": [position, sign * 180.0, index * 0.2],
                    "axis_scan_coordinates": [0.0, sign, 0.0],
                }
            )
    return {
        "status": "F1_detected_exterior_interfaces",
        "units": "synthetic OBJ units; scale unconfirmed",
        "banks": banks,
    }


class ScanMetrology917F13Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def evaluate(self, interfaces: dict, contract: dict | None = None) -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            contract_path = temp / "contract.json"
            fixture_source = temp / "fixture-source.json"
            fixture_copy = temp / "input" / "interfaces.json"
            write_json(contract_path, contract or self.contract)
            write_json(fixture_source, interfaces)
            fixture_copy.parent.mkdir(parents=True)
            shutil.copy2(fixture_source, fixture_copy)
            return self.module.evaluate(contract_path, fixture_copy)

    def test_synthetic_two_by_six_register_is_hypothesis_only(self):
        report = self.evaluate(synthetic_interfaces())

        self.assertEqual(report["report_status"], "passed_hypothesis_only")
        self.assertEqual(report["observations"]["interface_count"], 12)
        self.assertEqual(len(report["interface_registry"]), 12)
        self.assertAlmostEqual(
            report["derived"]["conditional_scale_mm_per_obj_unit"], 1.0, places=9
        )
        self.assertEqual(
            report["hypotheses"]["variant"]["closest_numerical_candidate_id"],
            "917_5_0_na",
        )
        self.assertIsNone(report["hypotheses"]["variant"]["selected_variant_id"])
        self.assertEqual(
            report["hypotheses"]["variant"]["status"], "ambiguous_not_selected"
        )
        closest = report["hypotheses"]["variant"]["candidate_comparison"][0]
        self.assertAlmostEqual(
            closest["conditional_scale_if_visible_opening_is_bore_mm_per_obj_unit"],
            86.8 / 86.815,
        )
        self.assertAlmostEqual(
            closest["implied_regular_pitch_mm_using_observed_mean"],
            118.0 * (86.8 / 86.815),
        )
        self.assertFalse(report["release"]["identity_confirmed"])
        self.assertFalse(report["release"]["scale_confirmed"])
        self.assertFalse(report["release"]["variant_confirmed"])
        self.assertFalse(report["release"]["functional_release_authorized"])
        self.assertFalse(report["release"]["fabrication_release_authorized"])

    def test_register_has_pitch_diameter_residuals_and_non_traceable_envelope(self):
        report = self.evaluate(synthetic_interfaces())
        first_after_regular_gap = report["interface_registry"][1]
        after_central_split = report["interface_registry"][3]

        self.assertEqual(first_after_regular_gap["gap_classification"], "regular_pitch")
        self.assertAlmostEqual(
            first_after_regular_gap["regular_pitch_residual_conditional_mm"], 0.0
        )
        self.assertEqual(after_central_split["gap_classification"], "central_split")
        self.assertIsNone(after_central_split["regular_pitch_residual_conditional_mm"])
        self.assertIn(
            "917_30_turbo_5374", first_after_regular_gap["candidate_bore_residuals_mm"]
        )
        self.assertGreater(first_after_regular_gap["screening_envelope_conditional_mm"], 0)
        self.assertFalse(
            first_after_regular_gap["screening_envelope_is_traceable_uncertainty"]
        )

    def test_three_physical_controls_are_explicitly_missing(self):
        report = self.evaluate(synthetic_interfaces())

        self.assertEqual(
            [item["id"] for item in report["required_physical_controls"]],
            ["PC-01", "PC-02", "PC-03"],
        )
        self.assertTrue(
            all(item["status"] == "missing" for item in report["required_physical_controls"])
        )
        self.assertEqual(report["release"]["physical_controls_required"], 3)
        self.assertEqual(report["release"]["physical_controls_verified"], 0)

    def test_forged_release_authority_cannot_promote_scan(self):
        contract = copy.deepcopy(self.contract)
        for key in list(contract["release_authority"]):
            if key.endswith("_enabled") or key.endswith("_implemented"):
                contract["release_authority"][key] = True

        report = self.evaluate(synthetic_interfaces(), contract)

        self.assertEqual(report["report_status"], "failed")
        self.assertTrue(report["contract_integrity_errors"])
        self.assertTrue(all(report["release"][key] is False for key in self.module.RELEASE_KEYS))

    def test_declared_physical_controls_cannot_self_validate(self):
        contract = copy.deepcopy(self.contract)
        for control in contract["required_physical_controls"]:
            control["status"] = "passed"
            control["measurement_report"] = "self-declared.json"

        report = self.evaluate(synthetic_interfaces(), contract)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "contract_physical_controls_must_start_missing",
            report["contract_integrity_errors"],
        )
        self.assertFalse(report["release"]["scale_confirmed"])
        self.assertFalse(report["release"]["fabrication_release_authorized"])

    def test_missing_opening_or_non_unit_axis_fails_closed(self):
        missing = synthetic_interfaces()
        missing["banks"]["negative"].pop()
        missing_report = self.evaluate(missing)

        invalid_axis = synthetic_interfaces()
        invalid_axis["banks"]["positive"][0]["axis_scan_coordinates"] = [0, 2, 0]
        axis_report = self.evaluate(invalid_axis)

        self.assertEqual(missing_report["report_status"], "failed")
        self.assertEqual(axis_report["report_status"], "failed")
        self.assertFalse(missing_report["release"]["functional_release_authorized"])
        self.assertFalse(axis_report["release"]["fabrication_release_authorized"])

    def test_public_fact_grade_or_source_cannot_be_silently_upgraded(self):
        contract = copy.deepcopy(self.contract)
        contract["public_facts"]["candidate_regular_pitch"]["evidence_grade"] = "A"

        report = self.evaluate(synthetic_interfaces(), contract)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "contract_pitch_must_remain_grade_d_candidate_118_mm",
            report["contract_integrity_errors"],
        )
        self.assertFalse(report["release"]["scale_confirmed"])

    def test_input_hash_is_recomputed_from_temporary_copy(self):
        fixture = synthetic_interfaces()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "fixture-source.json"
            copied = temp / "copied" / "interfaces.json"
            contract_path = temp / "contract.json"
            write_json(source, fixture)
            copied.parent.mkdir()
            shutil.copy2(source, copied)
            write_json(contract_path, self.contract)

            report = self.module.evaluate(contract_path, copied)

            self.assertEqual(report["input_custody"]["interfaces_report_sha256"], sha256(copied))
            self.assertFalse(
                report["input_custody"]["raw_mesh_vertices_or_faces_copied_into_report"]
            )
            self.assertTrue(
                report["input_custody"]["derived_interface_measurements_may_be_included"]
            )

    @unittest.skipUnless(LOCAL_INTERFACES.exists(), "local scan report is intentionally outside Git")
    def test_current_local_report_keeps_all_release_gates_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            copied = Path(temp_dir) / "interfaces.json"
            shutil.copy2(LOCAL_INTERFACES, copied)
            report = self.module.evaluate(CONTRACT, copied)

        self.assertEqual(report["report_status"], "passed_hypothesis_only")
        self.assertEqual(len(report["interface_registry"]), 12)
        self.assertTrue(math.isfinite(report["derived"]["conditional_scale_mm_per_obj_unit"]))
        self.assertFalse(report["release"]["scale_confirmed"])
        self.assertFalse(report["release"]["fabrication_release_authorized"])


if __name__ == "__main__":
    unittest.main()
