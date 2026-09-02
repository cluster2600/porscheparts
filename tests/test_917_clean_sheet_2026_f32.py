"""Tests du flat-12 917-inspired clean-sheet 2026 F32."""

from __future__ import annotations

import copy
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "twins/reference-917-engine/clean-sheet-2026-f32.json"
SCRIPT_PATH = ROOT / "twins/reference-917-engine/source/run_clean_sheet_2026_f32.py"
EVIDENCE_PATH = ROOT / "twins/reference-917-engine/evidence/f32/screening-report.json"
DOC_PATH = ROOT / "docs/917_CLEAN_SHEET_2026_F32.md"


def load_module():
    specification = importlib.util.spec_from_file_location("clean_sheet_2026_f32", SCRIPT_PATH)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot import {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


class CleanSheet917Engine2026F32Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.module = load_module()
        cls.report = cls.module.build_report(cls.contract)

    def test_contract_is_new_2026_program_not_historical_replica(self):
        self.assertEqual(self.contract["phase"], "F32")
        self.assertEqual(self.contract["program"]["id"], "917_2026_turbo_1600hp_clean_sheet")
        self.assertFalse(self.contract["program"]["historical_replica"])
        self.assertFalse(self.contract["program"]["historical_geometry_authority"])
        self.assertEqual(self.contract["program"]["target_vehicle"], "porsche_911_type_993_shell")
        self.assertNotIn("917_30_1973_turbo_5374", json.dumps(self.contract))
        upstream_cae = ROOT / self.contract["authority_boundary"]["upstream_head_reference_cae"]
        self.assertTrue(upstream_cae.is_file())

    def test_1600_mechanical_hp_is_exact_and_never_called_proven(self):
        target = self.report["design_point"]["target_power"]
        self.assertAlmostEqual(target["w"], 1_193_119.794531632, places=6)
        self.assertAlmostEqual(target["kw"], 1193.119794532, places=9)
        self.assertTrue(target["power_requirement_identity_closed"])
        self.assertFalse(target["target_power_proven"])
        self.assertFalse(self.report["release_gates"]["target_power_proven"])

        tampered = copy.deepcopy(self.contract)
        tampered["program"]["target_power"]["unit"] = "PS"
        errors = self.module.validate_contract(tampered)
        self.assertTrue(any("1600 mechanical hp" in error for error in errors))

    def test_nominal_geometry_mechanics_air_and_turbo_seed_match_golden_values(self):
        mechanics = self.report["design_point"]["geometry_and_mechanics"]
        self.assertAlmostEqual(mechanics["displacement_l"], 5.374385384, places=9)
        self.assertAlmostEqual(mechanics["specific_power_kw_per_l"], 222.001160915, places=9)
        self.assertAlmostEqual(mechanics["required_torque_nm"], 1265.939420003, places=9)
        self.assertAlmostEqual(mechanics["required_bmep_bar"], 29.600154789, places=9)
        self.assertAlmostEqual(mechanics["mean_piston_speed_m_s"], 21.12, places=9)

        flow = self.report["design_point"]["air_and_fuel"]
        self.assertAlmostEqual(flow["fuel_mass_flow_kg_s"], 0.110878135, places=9)
        self.assertAlmostEqual(flow["air_mass_flow_kg_s"], 1.219659484, places=9)
        self.assertAlmostEqual(flow["air_mass_flow_per_turbo_kg_s"], 0.609829742, places=9)
        self.assertAlmostEqual(
            flow["exhaust_mass_flow_kg_s"],
            flow["air_mass_flow_kg_s"] + flow["fuel_mass_flow_kg_s"],
            places=9,
        )
        self.assertTrue(flow["air_plus_fuel_mass_balance_closed"])
        self.assertAlmostEqual(flow["compressor_pressure_ratio"], 3.200896515, places=9)
        self.assertAlmostEqual(flow["compressor_outlet_temperature_k"], 454.906450542, places=9)
        self.assertAlmostEqual(flow["compressor_power_total_w"], 192145.439004355, places=6)
        self.assertAlmostEqual(flow["intercooler_heat_rejection_w"], 159233.842579224, places=6)
        self.assertFalse(flow["turbo_map_match_verified"])

    def test_fixed_power_mechanics_and_air_system_have_expected_monotonicity(self):
        low_speed = copy.deepcopy(self.contract)
        high_speed = copy.deepcopy(self.contract)
        low_speed["architecture_seed"]["design_speed_rpm"] = 8500.0
        high_speed["architecture_seed"]["design_speed_rpm"] = 9500.0
        low_point = self.module._powertrain_point(low_speed)
        high_point = self.module._powertrain_point(high_speed)
        self.assertGreater(
            low_point["geometry_and_mechanics"]["required_torque_nm"],
            high_point["geometry_and_mechanics"]["required_torque_nm"],
        )
        self.assertGreater(
            low_point["geometry_and_mechanics"]["required_bmep_bar"],
            high_point["geometry_and_mechanics"]["required_bmep_bar"],
        )
        self.assertLess(
            low_point["geometry_and_mechanics"]["mean_piston_speed_m_s"],
            high_point["geometry_and_mechanics"]["mean_piston_speed_m_s"],
        )

        higher_loss = copy.deepcopy(self.contract)
        higher_loss["air_and_fuel_screening"]["charge_path_pressure_loss_pa"] = 50000.0
        higher_loss_point = self.module._powertrain_point(higher_loss)
        nominal_flow = self.report["design_point"]["air_and_fuel"]
        changed_flow = higher_loss_point["air_and_fuel"]
        self.assertGreater(changed_flow["compressor_pressure_ratio"], nominal_flow["compressor_pressure_ratio"])
        self.assertGreater(
            changed_flow["compressor_outlet_temperature_k"],
            nominal_flow["compressor_outlet_temperature_k"],
        )
        self.assertGreater(changed_flow["compressor_power_total_w"], nominal_flow["compressor_power_total_w"])

    def test_declared_residual_energy_partition_closes_arithmetically_only(self):
        energy = self.report["declared_residual_energy_partition"]
        self.assertAlmostEqual(
            sum(energy["declared_outputs_w"].values()),
            energy["input_fuel_power_w"],
            places=5,
        )
        self.assertLess(abs(energy["relative_closure_error"]), 1.0e-12)
        self.assertTrue(energy["partition_is_hypothesis_not_measurement"])
        self.assertEqual(
            energy["closure_kind"],
            "residual_arithmetic_closure_not_turbine_or_exhaust_enthalpy_balance",
        )
        self.assertFalse(energy["turbo_shaft_power_balance_closed"])
        self.assertGreater(energy["declared_outputs_w"]["tailpipe_exhaust_heat"], 0.0)

    def test_hybrid_is_next_study_candidate_with_missing_turbo_load(self):
        variants = {item["id"]: item for item in self.report["cooling_variants"]}
        hybrid = variants["917_2026_hybrid_head_liquid_air_oil_cylinders"]
        air_oil = variants["917_2026_air_oil_engine_air_air_charge"]
        self.assertTrue(hybrid["evaluated_loads_within_declared_screening_limits"])
        self.assertFalse(hybrid["within_all_declared_screening_limits"])
        self.assertFalse(hybrid["screening_complete"])
        self.assertIsNone(hybrid["loads"]["turbo_bearing_housings"]["load_w"])
        self.assertTrue(hybrid["loads"]["turbo_bearing_housings"]["missing_input"])
        self.assertIsNone(hybrid["required_mass_flows_kg_s"]["turbo_bearing_coolant"])
        self.assertFalse(hybrid["thermal_system_validated"])
        self.assertFalse(hybrid["vehicle_packaging_validated"])
        self.assertFalse(air_oil["within_all_declared_screening_limits"])
        self.assertFalse(air_oil["loads"]["oil_loop"]["within_declared_screening_limit"])
        self.assertFalse(
            air_oil["loads"]["cylinder_and_head_fin_air"]["within_declared_screening_limit"]
        )
        self.assertTrue(air_oil["loads"]["air_to_air_charge_cooler"]["within_declared_screening_limit"])
        self.assertEqual(
            self.report["screening_decision"]["candidate_for_next_study"],
            "917_2026_hybrid_head_liquid_air_oil_cylinders",
        )
        self.assertTrue(
            self.report["screening_decision"]["hybrid_evaluated_loads_within_declared_limits"]
        )
        self.assertFalse(self.report["screening_decision"]["hybrid_complete_limit_screen"])
        self.assertTrue(self.report["screening_decision"]["decision_is_design_screen_not_validation"])

    def test_993_historical_and_conversion_cooling_are_never_conflated(self):
        integration = self.contract["porsche_993_integration"]
        self.assertEqual(integration["historical_993_engine_cooling"], "air_and_oil_cooled")
        self.assertIn("dedicated_hybrid", integration["conversion_baseline"])
        self.assertFalse(integration["vehicle_installation_authorized"])
        for variant in self.contract["thermal_screening"]["variants"]:
            self.assertFalse(variant["stock_993_liquid_cooling_claim"])
        self.assertFalse(self.report["screening_decision"]["stock_993_liquid_cooling_claim"])
        self.assertTrue(self.report["screening_decision"]["dedicated_conversion_system_required"])

    def test_vehicle_solver_and_manufacturing_evidence_stay_absent_and_gates_closed(self):
        self.assertTrue(all(value is None for value in self.contract["required_next_solver_evidence"].values()))
        self.assertTrue(
            all(value is None for value in self.contract["porsche_993_integration"]["required_evidence"].values())
        )
        self.assertTrue(self.report["release_gates"])
        self.assertTrue(all(value is False for value in self.report["release_gates"].values()))
        self.assertFalse(self.report["porsche_993_integration"]["vehicle_installation_authorized"])

        missing_solver_evidence = copy.deepcopy(self.contract)
        missing_solver_evidence["required_next_solver_evidence"].pop(
            "digitized_compressor_and_turbine_maps"
        )
        self.assertTrue(
            any(
                "required_next_solver_evidence" in error
                for error in self.module.validate_contract(missing_solver_evidence)
            )
        )

        missing_vehicle_evidence = copy.deepcopy(self.contract)
        missing_vehicle_evidence["porsche_993_integration"]["required_evidence"].pop(
            "radiator_core_and_duct_packaging"
        )
        self.assertTrue(
            any(
                "porsche_993_integration.required_evidence" in error
                for error in self.module.validate_contract(missing_vehicle_evidence)
            )
        )

    def test_contract_rejects_non_numeric_boolean_missing_variant_and_open_gate(self):
        boolean_bore = copy.deepcopy(self.contract)
        boolean_bore["architecture_seed"]["bore_mm"] = True
        self.assertTrue(any("bore_mm" in error for error in self.module.validate_contract(boolean_bore)))

        for invalid in (math.nan, math.inf):
            invalid_speed = copy.deepcopy(self.contract)
            invalid_speed["architecture_seed"]["design_speed_rpm"] = invalid
            self.assertTrue(
                any("design_speed_rpm" in error for error in self.module.validate_contract(invalid_speed))
            )

        missing_variant = copy.deepcopy(self.contract)
        missing_variant["thermal_screening"]["variants"].pop()
        self.assertTrue(any("exact hybrid and air/oil" in error for error in self.module.validate_contract(missing_variant)))

        open_gate = copy.deepcopy(self.contract)
        open_gate["release_gates"]["target_power_proven"] = True
        self.assertTrue(any("literal false" in error for error in self.module.validate_contract(open_gate)))

    def test_contract_rejects_impossible_domains_and_derived_compressor_state(self):
        mutations = (
            ("air_and_fuel_screening", "gas_gamma", 0.5),
            ("air_and_fuel_screening", "volumetric_efficiency", 99.0),
            ("thermal_screening", "coolant_cp_j_kg_k", -1.0),
            ("thermal_screening", "head_coolant_delta_t_k", -1.0),
            ("thermal_screening", "charge_coolant_cp_j_kg_k", math.inf),
            ("thermal_screening", "oil_delta_t_k", math.nan),
            ("thermal_screening", "coolant_cp_j_kg_k", 5.0e-324),
            ("thermal_screening", "charge_coolant_cp_j_kg_k", 1.0e308),
        )
        for section, field, value in mutations:
            with self.subTest(section=section, field=field, value=value):
                tampered = copy.deepcopy(self.contract)
                tampered[section][field] = value
                self.assertTrue(self.module.validate_contract(tampered))

        no_compression = copy.deepcopy(self.contract)
        no_compression["air_and_fuel_screening"]["brake_specific_fuel_consumption_lb_hp_h"] = 0.06
        no_compression["air_and_fuel_screening"]["air_fuel_ratio_mass"] = 1.1
        no_compression["air_and_fuel_screening"]["volumetric_efficiency"] = 2.0
        with self.assertRaisesRegex(ValueError, "pressure ratio must exceed 1"):
            self.module.build_report(no_compression)

    def test_authority_material_and_993_source_boundaries_are_validated(self):
        mutations = (
            ("program", "id", "historical_917_30"),
            ("program", "scan_role", "measured_design_authority"),
            ("authority_boundary", "f29_or_f30_geometry_released_for_engine_operation", True),
            ("authority_boundary", "upstream_layout_contract", "untracked/layout.json"),
            ("authority_boundary", "upstream_head_reference_cae", "untracked/fea.json"),
            ("authority_boundary", "upstream_head_reference_cae_role", "validated_full_head_fea"),
            ("authority_boundary", "f31_head_reference_cae_released_for_engine_operation", True),
            ("authority_boundary", "forbidden_claims", []),
            ("architecture_seed", "classification", "measured_design_lock"),
            ("thermal_screening", "load_allocation_classification", "validated_cht_data"),
            ("material_hypotheses", "manufacturing_released", True),
            ("material_hypotheses", "fatigue_thermal_corrosion_and_process_qualification_complete", True),
            ("porsche_993_integration", "historical_fact_source_ids", ["SRC-3D-DRUCK-SERVICE-FRANKFURT-RE"]),
            ("porsche_993_integration", "conversion_baseline", "stock_993_liquid_cooling_system"),
        )
        for section, field, value in mutations:
            with self.subTest(section=section, field=field):
                tampered = copy.deepcopy(self.contract)
                tampered[section][field] = value
                self.assertTrue(self.module.validate_contract(tampered))

        turbo_load_claim = copy.deepcopy(self.contract)
        turbo_load_claim["thermal_screening"]["variants"][0]["turbo_bearing_housing_heat_load_w"] = 1000.0
        self.assertTrue(self.module.validate_contract(turbo_load_claim))

        cooling_claim = copy.deepcopy(self.contract)
        cooling_claim["thermal_screening"]["variants"][0]["engine_cooling"] = "stock_993_factory_water_cooling"
        self.assertTrue(self.module.validate_contract(cooling_claim))

        charge_claim = copy.deepcopy(self.contract)
        charge_claim["thermal_screening"]["variants"][0]["charge_cooling"] = "validated_water_to_air_system"
        self.assertTrue(self.module.validate_contract(charge_claim))

        target_origin = copy.deepcopy(self.contract)
        target_origin["program"]["target_power"]["origin"] = "measured_dyno"
        self.assertTrue(self.module.validate_contract(target_origin))

    def test_candidate_is_derived_from_evaluated_load_status(self):
        flipped = copy.deepcopy(self.contract)
        for variant in flipped["thermal_screening"]["variants"]:
            replacement = 1.0 if variant["id"].startswith("917_2026_hybrid") else 1.0e9
            variant["screening_limits_w"] = {
                name: replacement for name in variant["screening_limits_w"]
            }
        report = self.module.build_report(flipped)
        decision = report["screening_decision"]
        self.assertFalse(decision["hybrid_evaluated_loads_within_declared_limits"])
        self.assertTrue(decision["air_oil_evaluated_loads_within_declared_limits"])
        self.assertEqual(
            decision["candidate_for_next_study"],
            "917_2026_air_oil_engine_air_air_charge",
        )
        self.assertIn("air_oil_loads_are_inside", decision["candidate_reason"])

    def test_tracked_evidence_is_current_and_deterministic(self):
        self.assertTrue(EVIDENCE_PATH.is_file())
        evidence_text = EVIDENCE_PATH.read_text(encoding="utf-8")
        self.assertEqual(evidence_text, self.module._json_text(self.report))
        tracked = json.loads(evidence_text)
        self.assertEqual(tracked, self.report)
        second = self.module.build_report(copy.deepcopy(self.contract))
        self.assertEqual(second, self.report)
        self.assertRegex(self.report["contract_sha256"], r"^[0-9a-f]{64}$")

    def test_french_documentation_and_make_targets_preserve_evidence_boundary(self):
        document = DOC_PATH.read_text(encoding="utf-8")
        self.assertIn("```mermaid", document)
        self.assertIn("La 993 d'origine", document)
        self.assertIn("1 600 mechanical hp", document)
        self.assertIn("ne prouve", document)
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("917-clean-sheet-2026-f32:", makefile)
        self.assertIn("917-clean-sheet-2026-f32-check:", makefile)
        self.assertIn("check: validate test 917-clean-sheet-2026-f32-check", makefile)


if __name__ == "__main__":
    unittest.main()
