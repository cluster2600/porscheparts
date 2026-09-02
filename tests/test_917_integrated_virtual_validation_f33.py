"""Tests des preuves integrees virtuelles F33 de la culasse 917."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/integrated-virtual-validation-f33.json"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f33"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class IntegratedVirtualValidationF33Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_json(CONTRACT)
        cls.report = load_json(EVIDENCE / "report.json")
        cls.publication = load_json(EVIDENCE / "publication.json")

    def test_scan_only_measurement_boundary_is_explicit(self):
        policy = self.contract["program"]["measurement_policy"]
        self.assertEqual(self.contract["phase"], "F33")
        self.assertEqual(policy["sole_geometry_measurement_source"], "existing_3d_scan")
        self.assertFalse(policy["future_physical_measurements_expected"])
        self.assertFalse(policy["scan_contains_cylinder_heads"])
        self.assertFalse(policy["scan_absolute_scale_confirmed"])
        self.assertIn("not_dimensionally_certified", policy["maximum_claim"])

    def test_functional_solver_cad_is_generated_but_not_manufacturing_cad(self):
        cad = self.report["functional_solver_cad"]
        self.assertTrue(cad["step_or_mesh_generated"])
        self.assertFalse(cad["manufacturing_cad_complete"])
        self.assertEqual({item["architecture"] for item in cad["variants"]}, {"2v", "4v"})
        for variant in cad["variants"]:
            self.assertGreater(variant["surface_element_count"], 10_000)
            self.assertEqual(len(variant["step"]["sha256"]), 64)
            self.assertEqual(len(variant["stl"]["sha256"]), 64)

    def test_six_openfoam_runs_and_mesh_convergence_pass(self):
        cfd = self.report["equivalent_port_cfd"]
        self.assertTrue(cfd["all_runs_returned_zero"])
        self.assertTrue(cfd["all_convergence_passed"])
        self.assertEqual(sum(len(items) for items in cfd["architectures"].values()), 6)
        for rows in cfd["architectures"].values():
            self.assertEqual({item["mesh_id"] for item in rows}, {"coarse", "medium", "fine"})
            self.assertTrue(all(item["solver_returncode"] == 0 for item in rows))
        self.assertFalse(cfd["full_runner_and_moving_valve_geometry_used"])

    def test_four_valve_virtual_performance_advantage_is_not_a_proof(self):
        flow = self.report["virtual_flowbench"]
        dyno = self.report["zero_dimensional_engine_dyno"]
        cht = self.report["cht_reduced_order"]
        self.assertGreater(flow["four_valve_peak_flow_gain_percent"], 0.0)
        self.assertGreater(
            dyno["curves"]["4v"][-1]["brake_power_mechanical_hp"],
            dyno["curves"]["2v"][-1]["brake_power_mechanical_hp"],
        )
        self.assertFalse(dyno["target_power_proven"])
        self.assertLess(
            cht["4v"]["combustion_side_wall_temperature_c"],
            cht["2v"]["combustion_side_wall_temperature_c"],
        )
        self.assertFalse(cht["4v"]["full_3d_cht_executed"])

    def test_material_and_fatigue_remain_failed_closed(self):
        self.assertFalse(self.report["material_screen"]["hot_curve_qualified"])
        tmf = self.report["fatigue_tmf_screen"]["architectures"]
        for architecture in ("2v", "4v"):
            self.assertFalse(tmf[architecture]["screening_passed"])
            self.assertGreater(tmf[architecture]["miner_total_damage"], 1.0)
            self.assertLess(tmf[architecture]["hot_yield_margin_on_combined_p95"], 1.0)
        selection = self.report["valvetrain_selection"]
        self.assertFalse(selection["intake_valve"]["additive_manufacturing_allowed"])
        self.assertFalse(selection["exhaust_valve"]["additive_manufacturing_allowed"])
        self.assertFalse(selection["spring"]["additive_manufacturing_allowed"])

    def test_synthetic_ct_defines_resolution_without_claiming_real_ndt(self):
        ndt = self.report["virtual_ct_ndt"]
        outcomes = {item["voxel_size_mm"]: item["critical_pod_screen_passed"] for item in ndt["ct_cases"]}
        self.assertEqual(outcomes, {0.06: True, 0.1: False, 0.2: False})
        self.assertFalse(ndt["physical_part_scanned"])
        self.assertFalse(ndt["real_probability_of_detection_demonstrated"])

    def test_physicsnemo_and_omniverse_are_not_overclaimed(self):
        physicsnemo = self.report["physicsnemo"]
        self.assertLess(
            physicsnemo["dataset_cases_available_after_f33"],
            physicsnemo["minimum_classical_solver_cases_before_training"],
        )
        self.assertFalse(physicsnemo["training_executed"])
        preflight_path = EVIDENCE / "omniverse/preflight.json"
        preflight = load_json(preflight_path)
        self.assertEqual(preflight["status"], "blocked")
        serialized = preflight_path.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", serialized)
        self.assertNotIn("/private/tmp/", serialized)

    def test_representative_case_matches_arm64_and_x86(self):
        check = self.report["cross_architecture_check"]
        self.assertEqual(check["remote_architecture"], "x86_64")
        self.assertEqual(check["local_architecture"], "arm64")
        self.assertEqual(check["relative_difference"], 0.0)
        self.assertEqual(check["openfoam_version"], "13")
        self.assertTrue(check["remote_temporary_case_removed"])

    def test_all_release_gates_are_closed_and_publication_is_hashed(self):
        self.assertEqual(
            self.report["status"],
            "integrated_virtual_campaign_complete_not_physical_validation",
        )
        self.assertTrue(all(value is False for value in self.report["release_gates"].values()))
        self.assertFalse(self.report["claims"]["manufacturing_or_engine_start_authorized"])
        for relative_path, expected in self.publication["files"].items():
            path = EVIDENCE / relative_path
            self.assertTrue(path.is_file())
            self.assertEqual(sha256(path), expected)
        for name in (
            "integrated-2v-4v.png",
            "virtual-ndt-pod.png",
            "product-4v-functional-cad.png",
        ):
            path = EVIDENCE / "figures" / name
            self.assertGreater(path.stat().st_size, 20_000)
            self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
