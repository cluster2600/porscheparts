import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_pet_993_engineering_evidence_links.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_pet_993_engineering_evidence_links", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class Pet993EngineeringEvidenceLinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = generator.build()
        generator.validate(self.contract)

    def test_crosswalk_closes_on_four_records_and_eight_masters(self) -> None:
        summary = self.contract["summary"]
        self.assertEqual(summary["linked_catalog_part_records"], 4)
        self.assertEqual(summary["linked_pet_part_masters"], 8)
        self.assertEqual(summary["linked_catalogue_twin_contracts"], 3)
        self.assertEqual(summary["linked_engine_component_contracts"], 4)
        self.assertEqual(summary["unique_load_case_contracts"], 10)
        self.assertEqual(summary["part_to_load_case_links"], 13)
        self.assertEqual(summary["linked_virtual_F2_readiness_contracts"], 1)
        self.assertEqual(summary["linked_mass_constrained_structural_surrogates"], 1)
        self.assertEqual(summary["mass_constrained_surrogate_component_credits"], 0)
        self.assertEqual(summary["linked_valve_dimensional_surrogate_contracts"], 2)
        self.assertEqual(summary["linked_valve_dimensional_surrogate_variants"], 3)
        self.assertEqual(
            summary["linked_pet_masters_with_valve_dimensional_surrogates"], 3
        )
        self.assertEqual(
            summary["valve_dimensional_surrogate_component_CAE_credits"], 0
        )
        self.assertEqual(summary["linked_k16_envelope_flow_surrogate_contracts"], 1)
        self.assertEqual(summary["linked_k16_envelope_flow_surrogate_variants"], 2)
        self.assertEqual(
            summary["linked_pet_masters_with_k16_envelope_flow_surrogates"], 4
        )
        self.assertEqual(summary["k16_evaluated_zeroD_operating_points"], 0)
        self.assertEqual(
            summary["k16_envelope_flow_surrogate_component_CAE_credits"], 0
        )
        self.assertEqual(
            summary["strict_openusd_validated_engineering_guide_stages"], 8
        )
        self.assertEqual(summary["nvidia_asset_validator_passes"], 0)
        self.assertEqual(summary["linked_charge_air_chain_surrogate_contracts"], 5)
        self.assertEqual(summary["linked_charge_air_chain_surrogate_variants"], 5)
        self.assertEqual(
            summary["linked_pet_masters_with_charge_air_chain_surrogates"], 5
        )
        self.assertEqual(summary["charge_air_evaluated_zeroD_operating_points"], 0)
        self.assertEqual(summary["charge_air_chain_surrogate_component_CAE_credits"], 0)
        self.assertEqual(summary["linked_heat_shield_thermal_surrogate_contracts"], 1)
        self.assertEqual(summary["linked_pet_masters_with_heat_shield_thermal_surrogate"], 1)
        self.assertEqual(summary["heat_shield_evaluated_thermal_operating_points"], 0)
        self.assertEqual(summary["heat_shield_thermal_surrogate_component_CAE_credits"], 0)
        self.assertEqual(
            summary["linked_turbo_lubrication_control_topology_contracts"], 40
        )
        self.assertEqual(
            summary["linked_pet_masters_with_turbo_lubrication_control_topology"],
            40,
        )
        self.assertEqual(summary["turbo_lubrication_control_symbolic_equations"], 10)
        self.assertEqual(summary["turbo_lubrication_control_blocked_load_cases"], 6)
        self.assertEqual(summary["turbo_lubrication_control_component_CAE_credits"], 0)
        self.assertEqual(summary["linked_oil_tank_circuit_topology_contracts"], 81)
        self.assertEqual(
            summary["linked_pet_masters_with_oil_tank_circuit_topology"], 81
        )
        self.assertEqual(summary["oil_tank_circuit_symbolic_equations"], 11)
        self.assertEqual(summary["oil_tank_circuit_blocked_load_cases"], 7)
        self.assertEqual(summary["oil_tank_circuit_component_CAE_credits"], 0)
        self.assertEqual(summary["linked_oil_cooler_circuit_topology_contracts"], 43)
        self.assertEqual(
            summary["linked_pet_masters_with_oil_cooler_circuit_topology"], 43
        )
        self.assertEqual(summary["oil_cooler_circuit_symbolic_equations"], 14)
        self.assertEqual(summary["oil_cooler_circuit_blocked_load_cases"], 8)
        self.assertEqual(summary["oil_cooler_circuit_component_CAE_credits"], 0)

    def test_valves_and_k16_receive_their_blocked_domain_cases(self) -> None:
        by_part = {item["part_id"]: item for item in self.contract["links"]}
        intake_ids = {
            case["load_case_id"]
            for case in by_part["993-ENG-INTAKE-VALVE-F1-0001"][
                "engine_load_case_contracts"
            ]
        }
        self.assertEqual(
            intake_ids,
            {
                "LC-993-VALVE-THERMAL-STEADY",
                "LC-993-VALVE-DYNAMIC-CYCLE",
                "LC-993-CAMSHAFT-VALVETRAIN",
            },
        )
        k16 = by_part["993-TURBOCHARGER-K16-PAIR-0001"]
        self.assertEqual(
            {item["component_id"] for item in k16["engine_component_contracts"]},
            {"CMP-993-K16-LEFT-PROXY", "CMP-993-K16-RIGHT-PROXY"},
        )
        self.assertEqual(
            [item["load_case_id"] for item in k16["engine_load_case_contracts"]],
            ["LC-993-K16-COMPRESSOR-TURBINE"],
        )

    def test_all_evidence_links_remain_fail_closed(self) -> None:
        self.assertFalse(self.contract["physicsnemo_policy"]["execution_enabled"])
        for field in (
            "analysis_geometry_available",
            "qualified_material_decisions",
            "reference_solver_results",
            "physicsnemo_results",
            "simready_assets",
            "manufacturing_releases",
        ):
            self.assertEqual(self.contract["summary"][field], 0)
        for link in self.contract["links"]:
            self.assertFalse(any(link["claims"].values()))
        for link in self.contract["declared_reference_links"]:
            self.assertFalse(any(link["claims"].values()))

    def test_carrier_receives_only_a_virtual_F2_readiness_contract(self) -> None:
        carrier = next(
            item
            for item in self.contract["links"]
            if item["part_id"] == "993-ENG-CARRIER-0001"
        )
        readiness = carrier["virtual_F2_readiness_contract"]
        self.assertEqual(readiness["interface_hypothesis_count"], 2)
        self.assertEqual(readiness["unknown_parameter_count"], 19)
        self.assertEqual(readiness["blocked_load_case_count"], 8)
        self.assertEqual(
            readiness["mass_constrained_surrogate_status"],
            "F1_mass_constrained_structural_surrogate_no_component_credit",
        )
        self.assertTrue(readiness["mass_constraint_closed"])
        self.assertAlmostEqual(readiness["equivalent_wall_mm"], 2.175319724, places=9)
        self.assertEqual(readiness["interface_search_domain_count"], 2)
        self.assertEqual(readiness["selected_interface_point_count"], 0)
        self.assertFalse(readiness["mass_constrained_surrogate_component_credit"])
        self.assertFalse(readiness["F2_interface_geometry"])
        self.assertFalse(readiness["reference_CAE_passed"])
        self.assertFalse(readiness["physicsnemo_validated"])
        self.assertFalse(readiness["simready_validated"])
        self.assertEqual(readiness["openusd_strict_validation"], "passed")
        self.assertEqual(
            readiness["nvidia_asset_validator"], "not_run_preflight_blocked"
        )

    def test_three_pet_valve_masters_receive_only_f1_dimensional_surrogates(self) -> None:
        valve_links = [
            item
            for item in self.contract["links"]
            if item["valve_dimensional_surrogate_contract"] is not None
        ]
        self.assertEqual(
            {item["part_id"] for item in valve_links},
            {
                "993-ENG-INTAKE-VALVE-F1-0001",
                "993-ENG-EXHAUST-VALVE-F1-0001",
            },
        )
        self.assertEqual(
            sum(
                item["valve_dimensional_surrogate_contract"]["variant_count"]
                for item in valve_links
            ),
            3,
        )
        for item in valve_links:
            surrogate = item["valve_dimensional_surrogate_contract"]
            self.assertTrue(surrogate["F1_dimensional_surrogate"])
            self.assertFalse(surrogate["F2_interface_geometry"])
            self.assertFalse(surrogate["analysis_geometry_available"])
            self.assertFalse(surrogate["qualified_material_decision"])
            self.assertFalse(surrogate["component_CAE_credit"])
            self.assertEqual(surrogate["openusd_strict_validation"], "passed")
            self.assertEqual(
                surrogate["nvidia_asset_validator"], "not_run_preflight_blocked"
            )

    def test_four_pet_k16_masters_receive_guides_and_symbolic_equations_only(self) -> None:
        k16_link = next(
            item
            for item in self.contract["links"]
            if item["part_id"] == "993-TURBOCHARGER-K16-PAIR-0001"
        )
        surrogate = k16_link["k16_envelope_flow_surrogate_contract"]
        self.assertEqual(surrogate["variant_count"], 2)
        self.assertEqual(len(surrogate["linked_pet_part_master_twin_ids"]), 4)
        self.assertEqual(surrogate["right_side_wheel_diameter_guide_count"], 4)
        self.assertEqual(surrogate["symbolic_zeroD_equation_count"], 6)
        self.assertEqual(surrogate["evaluated_zeroD_operating_points"], 0)
        self.assertEqual(surrogate["selected_interface_coordinate_count"], 0)
        self.assertTrue(surrogate["F1_envelope_and_diameter_guides"])
        self.assertFalse(surrogate["F2_interface_geometry"])
        self.assertFalse(surrogate["F3_analysis_geometry"])
        self.assertFalse(surrogate["qualified_material_decision"])
        self.assertFalse(surrogate["component_CAE_credit"])
        self.assertFalse(surrogate["physicsnemo_execution_enabled"])
        self.assertEqual(surrogate["openusd_strict_validation"], "passed")
        self.assertEqual(
            surrogate["nvidia_asset_validator"], "not_run_preflight_blocked"
        )

    def test_five_charge_air_masters_receive_guides_and_symbolic_equations_only(self) -> None:
        links = [
            item
            for item in self.contract["declared_reference_links"]
            if item.get("charge_air_chain_surrogate_contract") is not None
        ]
        self.assertEqual(len(links), 5)
        self.assertEqual(
            {item["normalized_oem_reference"] for item in links},
            {
                "99311033053",
                "99311034054",
                "99311063256",
                "99311063356",
                "99360611400",
            },
        )
        for item in links:
            surrogate = item["charge_air_chain_surrogate_contract"]
            self.assertEqual(surrogate["symbolic_zeroD_equation_count"], 8)
            self.assertEqual(surrogate["evaluated_zeroD_operating_points"], 0)
            self.assertEqual(surrogate["selected_interface_coordinate_count"], 0)
            self.assertTrue(surrogate["F1_envelope_guide"])
            self.assertFalse(surrogate["F2_interface_geometry"])
            self.assertFalse(surrogate["F3_analysis_geometry"])
            self.assertFalse(surrogate["qualified_material_decision"])
            self.assertFalse(surrogate["component_CAE_credit"])
            self.assertFalse(surrogate["physicsnemo_execution_enabled"])
            self.assertEqual(surrogate["openusd_strict_validation"], "passed")

    def test_heat_shield_master_receives_thermal_contract_without_solver_credit(self) -> None:
        links = [
            item
            for item in self.contract["declared_reference_links"]
            if item.get("heat_shield_thermal_surrogate_contract") is not None
        ]
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["normalized_oem_reference"], "99312311351")
        surrogate = links[0]["heat_shield_thermal_surrogate_contract"]
        self.assertEqual(surrogate["symbolic_thermal_equation_count"], 7)
        self.assertEqual(surrogate["blocked_reference_load_case_count"], 4)
        self.assertEqual(surrogate["unknown_engineering_parameter_count"], 25)
        self.assertEqual(surrogate["evaluated_thermal_operating_points"], 0)
        self.assertTrue(surrogate["F1_envelope_thermal_readiness"])
        self.assertFalse(surrogate["F2_interface_geometry"])
        self.assertFalse(surrogate["F3_analysis_geometry"])
        self.assertFalse(surrogate["qualified_material_decision"])
        self.assertFalse(surrogate["component_CAE_credit"])
        self.assertFalse(surrogate["physicsnemo_execution_enabled"])
        self.assertEqual(surrogate["openusd_strict_validation"], "passed")

    def test_forty_202_16_masters_receive_nonspatial_topology_only(self) -> None:
        links = [
            item
            for item in self.contract["declared_reference_links"]
            if item.get("turbo_lubrication_control_topology_contract") is not None
        ]
        self.assertEqual(len(links), 40)
        self.assertEqual(
            len(
                {
                    master_id
                    for item in links
                    for master_id in item["pet_part_master_twin_ids"]
                }
            ),
            40,
        )
        for item in links:
            topology = item["turbo_lubrication_control_topology_contract"]
            self.assertEqual(topology["symbolic_equation_count"], 10)
            self.assertEqual(topology["blocked_reference_load_case_count"], 6)
            self.assertEqual(topology["unknown_engineering_parameter_count"], 36)
            self.assertEqual(topology["known_interface_coordinate_count"], 0)
            self.assertTrue(topology["F1_nonspatial_topology_readiness"])
            self.assertFalse(topology["F2_interface_geometry"])
            self.assertFalse(topology["F3_analysis_geometry"])
            self.assertFalse(topology["component_CAE_credit"])
            self.assertFalse(topology["physicsnemo_execution_enabled"])
            self.assertEqual(topology["openusd_strict_validation"], "passed")

    def test_eighty_one_104_01_masters_receive_nonspatial_topology_only(self) -> None:
        links = [
            item
            for item in self.contract["declared_reference_links"]
            if item.get("oil_tank_circuit_topology_contract") is not None
        ]
        self.assertEqual(len(links), 81)
        self.assertEqual(
            len(
                {
                    master_id
                    for item in links
                    for master_id in item["pet_part_master_twin_ids"]
                }
            ),
            81,
        )
        for item in links:
            topology = item["oil_tank_circuit_topology_contract"]
            self.assertEqual(topology["symbolic_equation_count"], 11)
            self.assertEqual(topology["blocked_reference_load_case_count"], 7)
            self.assertEqual(topology["unknown_engineering_parameter_count"], 40)
            self.assertEqual(topology["known_interface_coordinate_count"], 0)
            self.assertTrue(topology["F1_nonspatial_topology_readiness"])
            self.assertFalse(topology["F2_interface_geometry"])
            self.assertFalse(topology["F3_analysis_geometry"])
            self.assertFalse(topology["component_CAE_credit"])
            self.assertFalse(topology["physicsnemo_execution_enabled"])
            self.assertEqual(topology["openusd_strict_validation"], "passed")

    def test_forty_three_104_05_masters_receive_nonspatial_topology_only(self) -> None:
        links = [
            item
            for item in self.contract["declared_reference_links"]
            if item.get("oil_cooler_circuit_topology_contract") is not None
        ]
        self.assertEqual(len(links), 43)
        self.assertEqual(
            len(
                {
                    master_id
                    for item in links
                    for master_id in item["pet_part_master_twin_ids"]
                }
            ),
            43,
        )
        for item in links:
            topology = item["oil_cooler_circuit_topology_contract"]
            self.assertEqual(topology["symbolic_equation_count"], 14)
            self.assertEqual(topology["blocked_reference_load_case_count"], 8)
            self.assertEqual(topology["unknown_engineering_parameter_count"], 44)
            self.assertEqual(topology["known_interface_coordinate_count"], 0)
            self.assertTrue(topology["F1_nonspatial_topology_readiness"])
            self.assertFalse(topology["F2_interface_geometry"])
            self.assertFalse(topology["F3_analysis_geometry"])
            self.assertFalse(topology["component_CAE_credit"])
            self.assertFalse(topology["physicsnemo_execution_enabled"])
            self.assertEqual(topology["openusd_strict_validation"], "passed")

    def test_checked_in_contract_is_current(self) -> None:
        self.assertEqual(generator.main(["--check"]), 0)
        self.assertEqual(
            json.loads(generator.OUTPUT.read_text(encoding="utf-8")),
            self.contract,
        )


if __name__ == "__main__":
    unittest.main()
