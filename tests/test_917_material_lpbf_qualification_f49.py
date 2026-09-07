#!/usr/bin/env python3
"""Tests fail-closed du contrat matière et procédé LPBF F49."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "twins/reference-917-engine/source/build_material_lpbf_qualification_f49.py"
CONTRACT = ROOT / "twins/reference-917-engine/material-lpbf-qualification-f49.json"
EVIDENCE = ROOT / "twins/reference-917-engine/evidence/f49-material-lpbf"
CSV_PATH = EVIDENCE / "material-comparison.csv"
MANIFEST = EVIDENCE / "manifest.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module():
    spec = importlib.util.spec_from_file_location("f49_material_lpbf", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MaterialLpbfQualificationF49Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load(CONTRACT)
        cls.manifest = load(MANIFEST)
        cls.module = load_module()

    def test_cli_check_and_generator_are_deterministic(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--project-root", str(ROOT), "--check"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("F49 material/LPBF qualification evidence: OK", result.stdout)
        self.assertEqual(self.contract, self.module.build_contract(ROOT))

    def test_upstream_and_primary_sources_are_hash_bound(self) -> None:
        for binding in self.contract["upstream"].values():
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(binding["sha256"], sha256(path))
        for binding in self.contract["source_bindings"].values():
            path = ROOT / binding["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(binding["sha256"], sha256(path))
            record = load(path)
            self.assertIn(record["source_type"], {"manufacturer", "official"})

    def test_required_material_families_are_compared_without_false_selection(self) -> None:
        materials = {item["id"]: item for item in self.contract["material_comparison"]}
        self.assertEqual(
            set(materials),
            {
                "Aheadd_CP1_400C_4h",
                "A20X_A205_LPBF_T7",
                "EOS_AlSi10Mg_T6",
                "EOS_AlF357_T6_like",
                "2618_T61_wrought_machined_reference",
            },
        )
        self.assertEqual(self.contract["screening_decision"]["primary_coupon_candidate"], "Aheadd_CP1_400C_4h")
        self.assertEqual(self.contract["screening_decision"]["alternate_coupon_candidate"], "A20X_A205_LPBF_T7")
        self.assertIsNone(self.contract["screening_decision"]["qualified_material"])
        self.assertTrue(all(item["complete_hot_card"] is False for item in materials.values()))
        self.assertEqual(materials["Aheadd_CP1_400C_4h"]["room_temperature"]["thermal_conductivity_w_mk"], 187.0)
        self.assertEqual(materials["A20X_A205_LPBF_T7"]["public_hot_tensile_points"][-1]["yield_mpa"], 215.0)
        self.assertFalse(materials["2618_T61_wrought_machined_reference"]["digitized_graph_values_are_design_allowables"])

    def test_sapphire_bare_envelope_math_does_not_claim_final_fit(self) -> None:
        fit = self.contract["selected_machine_route"]["fit_screen"]
        self.assertEqual(fit["screening_input_envelope_mm"], [225.0, 120.0, 98.0])
        self.assertEqual(fit["published_machine_volume"], {"shape": "circular_platform", "diameter_mm": 315.0, "height_mm": 400.0})
        expected_width = 120.0 * math.cos(math.radians(35.0)) + 98.0 * math.sin(math.radians(35.0))
        expected_height = 120.0 * math.sin(math.radians(35.0)) + 98.0 * math.cos(math.radians(35.0))
        expected_diameter = math.hypot(225.0, expected_width)
        self.assertAlmostEqual(fit["axis_aligned_envelope_after_roll_mm"][1], expected_width, places=6)
        self.assertAlmostEqual(fit["axis_aligned_envelope_after_roll_mm"][2], expected_height, places=6)
        self.assertAlmostEqual(fit["required_platform_diameter_from_bounding_box_mm"], expected_diameter, places=6)
        self.assertTrue(fit["bare_envelope_screen_pass"])
        self.assertIsNone(fit["support_extent_mm"])
        self.assertIsNone(fit["supplier_edge_margin_mm"])
        self.assertFalse(fit["recoater_clearance_verified"])
        self.assertFalse(fit["final_build_fit_verified"])

    def test_support_allowance_and_heat_treatment_plan_remain_hypotheses(self) -> None:
        process = self.contract["process_plan"]
        support = process["support_policy"]
        self.assertFalse(support["internal_gas_or_oil_passage_supports_allowed"])
        self.assertFalse(support["support_contact_on_seat_guide_bore_deck_or_bearing_surface_allowed"])
        self.assertFalse(support["support_projection_generated"])
        allowance = process["machining_allowance_hypotheses"]
        self.assertIn("not_released", allowance["classification"])
        self.assertFalse(allowance["supplier_and_machinist_approved"])
        post = process["post_processing"]
        self.assertEqual(post["baseline_route"]["cycle"], "400_degC_4h")
        self.assertFalse(post["baseline_route"]["T6_designation_used"])
        self.assertIsNone(post["HIP_branch"]["pressure_mpa"])
        self.assertIsNone(post["HIP_branch"]["hold_time_h"])
        self.assertFalse(post["HIP_branch"]["selected"])

    def test_coupon_plan_reaches_300C_but_has_no_invented_acceptance_curve(self) -> None:
        plan = self.contract["coupon_qualification_plan"]
        self.assertGreaterEqual(plan["minimum_independent_builds_for_screening"], 3)
        self.assertEqual(plan["orientations"], ["X", "Y", "Z", "45deg"])
        self.assertEqual(plan["temperatures_c"], [20.0, 150.0, 200.0, 250.0, 300.0])
        properties = {item["property"] for item in plan["tests"]}
        self.assertIn("yield_uts_elongation_reduction_of_area", properties)
        self.assertIn("thermal_diffusivity", properties)
        self.assertIn("HCF_LCF_TMF", properties)
        self.assertIn("creep_and_stress_relaxation", properties)
        self.assertIsNone(plan["hot_strength_acceptance_curves"])
        self.assertIsNone(plan["thermal_property_acceptance_curves"])
        self.assertIsNone(plan["fatigue_TMF_creep_acceptance_curves"])
        self.assertIsNone(plan["statistical_lower_tolerance_basis"])
        self.assertFalse(plan["qualification_complete"])

    def test_additivefoam_and_thermomechanical_contracts_fail_closed(self) -> None:
        additive = self.contract["additivefoam_contract"]
        self.assertTrue(all(value is False for value in additive["required_inputs"].values()))
        self.assertEqual(additive["numerical_acceptance"]["temperature_cap_k"], 3300.0)
        self.assertFalse(additive["numerical_acceptance"]["temperature_cap_hit_allowed"])
        self.assertIsNone(additive["numerical_acceptance"]["mass_and_energy_balance_tolerance"])
        self.assertFalse(additive["simulation_executed_for_CP1_route"])
        self.assertFalse(additive["calibrated_to_physical_CP1_coupon"])
        thermal = self.contract["thermomechanical_contract"]
        self.assertTrue(thermal["F47_loads_bound_by_hash"])
        self.assertFalse(thermal["F47_loads_correlated"])
        self.assertIsNone(thermal["qualified_material_card_path"])
        self.assertIsNone(thermal["yield_margin_requirement"])
        self.assertFalse(thermal["analysis_executed"])
        self.assertFalse(thermal["accepted"])

    def test_CT_NDT_and_pressure_acceptance_are_not_invented(self) -> None:
        inspection = self.contract["inspection_and_acceptance_plan"]
        self.assertIsNone(inspection["CT"]["voxel_size_um"])
        self.assertIsNone(inspection["CT"]["probability_of_detection_curve"])
        self.assertIsNone(inspection["CT"]["maximum_accepted_defect_by_zone"])
        self.assertIn("ASTM_E1417", inspection["surface_NDT"]["method"])
        self.assertIsNone(inspection["surface_NDT"]["linear_indication_limit"])
        self.assertIsNone(inspection["pressure_leak_and_cleanliness"]["proof_pressure_pa"])
        self.assertIsNone(inspection["pressure_leak_and_cleanliness"]["leak_rate_limit"])
        self.assertFalse(inspection["acceptance_criteria_frozen_before_build"])

    def test_no_geometry_or_release_claim_and_all_gates_closed(self) -> None:
        scope = self.contract["scope"]
        self.assertFalse(scope["CAD_or_mesh_created"])
        self.assertFalse(scope["external_scan_skin_modified"])
        self.assertFalse(scope["functional_interface_dimension_created"])
        self.assertFalse(scope["geometry_claimed"])
        outer = scope["outer_surface_policy"]
        self.assertEqual(outer["authority"], "F43_scan_contour_outer_skin_via_F47_internal_contract")
        self.assertTrue(outer["same_exact_F43_bytes_required_for_2v_and_4v"])
        self.assertFalse(outer["external_shape_change_allowed"])
        self.assertFalse(outer["uniform_or_directional_scaling_allowed"])
        self.assertFalse(outer["global_envelope_authored_by_F49"])
        self.assertEqual(outer["internal_analytic_scope"], "functional_circular_cylinders_only_per_F47")
        self.assertFalse(outer["historical_proxy_geometry_reusable"])
        self.assertTrue(self.contract["release_gates"])
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))
        self.assertFalse(self.contract["conclusion"]["part_qualified"])
        self.assertFalse(self.contract["conclusion"]["printable_part_claimed"])
        for path in EVIDENCE.rglob("*"):
            if path.is_file():
                self.assertNotIn(path.suffix.lower(), {".step", ".stp", ".stl", ".obj", ".msh", ".inp"})

    def test_csv_and_manifest_are_complete_and_hash_locked(self) -> None:
        rows = list(csv.DictReader(io.StringIO(CSV_PATH.read_text(encoding="utf-8"))))
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["material_id"], "Aheadd_CP1_400C_4h")
        self.assertTrue(all(row["qualified_material"] == "false" for row in rows))
        artifacts = {item["path"]: item for item in self.manifest["artifacts"]}
        self.assertEqual(set(artifacts), {CONTRACT.relative_to(ROOT).as_posix(), CSV_PATH.relative_to(ROOT).as_posix()})
        self.assertEqual(self.manifest["generator"]["sha256"], sha256(SCRIPT))
        for relative, item in artifacts.items():
            path = ROOT / relative
            self.assertEqual(path.stat().st_size, item["bytes"])
            self.assertEqual(sha256(path), item["sha256"])
        self.assertFalse(self.manifest["release_claimed"])


if __name__ == "__main__":
    unittest.main()
