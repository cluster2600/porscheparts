import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_vehicle_993_program.py"
SPEC = importlib.util.spec_from_file_location("generate_vehicle_993_program", MODULE_PATH)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


class Vehicle993ProgramTests(unittest.TestCase):
    def setUp(self) -> None:
        self.program = generator.build_program()

    def test_catalogue_scope_closes_without_claiming_a_vehicle_bom(self) -> None:
        scope = self.program["catalogue_scope"]
        self.assertEqual(scope["system_count"], 10)
        self.assertEqual(scope["illustration_work_package_count"], 239)
        self.assertEqual(scope["reference_count_aggregate"], 12864)
        self.assertEqual(scope["configured_vehicle_bom_count"], 0)
        self.assertIn("ne sont pas les pieces", scope["warning"])
        self.assertEqual(self.program["inventory"]["pet_documentary_twins"], 12879)
        self.assertEqual(self.program["inventory"]["catalogue_part_proxy_twins"], 18)
        self.assertEqual(self.program["inventory"]["pet_unique_oem_references"], 6013)
        self.assertEqual(self.program["inventory"]["pet_part_master_twins"], 6013)
        self.assertEqual(self.program["inventory"]["pet_records_with_proven_variants"], 13)
        self.assertEqual(self.program["inventory"]["documented_variant_configuration_contracts"], 8)
        self.assertEqual(self.program["inventory"]["complete_variant_boms"], 0)
        self.assertEqual(self.program["inventory"]["variant_assignment_links"], 28)
        self.assertEqual(self.program["inventory"]["pet_machine_bom_candidate_occurrences"], 173)
        self.assertEqual(self.program["inventory"]["pet_machine_bom_candidate_vehicle_links"], 178)
        self.assertEqual(self.program["inventory"]["provisional_configuration_axis_contracts"], 4)
        self.assertEqual(self.program["inventory"]["pet_summary_type_records"], 69)
        self.assertEqual(self.program["inventory"]["pet_summary_configuration_candidates"], 149)
        self.assertEqual(self.program["inventory"]["pet_summary_configuration_gaps"], 2)
        self.assertEqual(
            self.program["inventory"]["single_dimension_part_constraint_occurrences"], 694
        )
        self.assertEqual(
            self.program["inventory"]["resolved_configuration_part_constraint_occurrences"],
            682,
        )
        self.assertEqual(self.program["inventory"]["configuration_part_candidate_links"], 24063)
        self.assertEqual(self.program["inventory"]["configuration_exception_contracts"], 4)
        self.assertEqual(
            self.program["inventory"]["mapped_configuration_exception_occurrences"], 12
        )
        self.assertEqual(
            self.program["inventory"]["fully_resolved_configuration_exceptions"], 0
        )
        self.assertEqual(self.program["inventory"]["pet_part_master_engineering_tasks"], 6013)
        self.assertEqual(
            self.program["inventory"]["pet_tasks_with_configuration_evidence"], 684
        )
        self.assertEqual(
            self.program["inventory"]["pet_tasks_without_configuration_evidence"], 5329
        )
        self.assertEqual(
            self.program["inventory"]["pet_tasks_with_turbo_integration_evidence"], 317
        )
        self.assertEqual(
            self.program["inventory"]["pet_tasks_ready_for_editable_geometry_authoring"],
            664,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_F1_envelope_identity_linked_unvalidated"
            ],
            0,
        )
        self.assertEqual(
            self.program["inventory"]["pet_tasks_with_exact_oem_F1_envelope_candidates"],
            9,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_F1_valve_dimensional_surrogate_unvalidated"
            ],
            3,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_F1_k16_envelope_diameter_guides_unvalidated"
            ],
            4,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_F1_charge_air_chain_guides_unvalidated"
            ],
            5,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_F1_heat_shield_envelope_thermal_readiness_unvalidated"
            ],
            1,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_F1_turbo_lubrication_control_topology_readiness_unvalidated"
            ],
            35,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_F1_oil_tank_circuit_topology_readiness_unvalidated"
            ],
            81,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_F1_oil_cooler_circuit_topology_readiness_unvalidated"
            ],
            41,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_F1_mass_constrained_structural_surrogate_virtual_F2_readiness"
            ],
            1,
        )
        self.assertEqual(
            self.program["inventory"]["pet_tasks_ready_for_F2_interface_geometry"],
            0,
        )
        self.assertEqual(
            self.program["inventory"]["pet_tasks_ready_for_virtual_F2_interface_inference"],
            1,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_valve_tasks_ready_for_F2_interface_geometry"
            ],
            3,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_ready_for_202_16_topology_and_F2_interfaces"
            ],
            3,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_ready_for_104_01_topology_F2_interfaces_and_oil_properties"
            ],
            12,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_ready_for_104_05_topology_F2_interfaces_oil_air_properties_and_fan_control"
            ],
            1,
        )
        self.assertEqual(
            self.program["inventory"]["pet_tasks_with_F2_interface_geometry"],
            0,
        )
        self.assertEqual(
            self.program["inventory"]["pet_tasks_with_workshop_manual_candidates"],
            417,
        )
        self.assertEqual(self.program["inventory"]["workshop_manual_candidate_links"], 1569)
        self.assertEqual(self.program["inventory"]["workshop_manual_records"], 2496)
        self.assertEqual(
            self.program["inventory"]["workshop_manual_system_routed_records"],
            2442,
        )
        self.assertEqual(
            self.program["inventory"]["workshop_manual_unresolved_system_records"],
            54,
        )
        self.assertEqual(
            self.program["inventory"]["workshop_manual_part_review_candidate_records"],
            158,
        )
        self.assertEqual(
            self.program["inventory"]["promoted_workshop_manual_measurements_or_torques"],
            0,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_linked_catalog_part_engineering_records"
            ],
            8,
        )
        self.assertEqual(
            self.program["inventory"]["linked_catalog_part_engineering_record_links"],
            8,
        )
        self.assertEqual(
            self.program["inventory"]["pet_tasks_with_linked_simulation_evidence"],
            171,
        )
        self.assertEqual(
            self.program["inventory"]["linked_simulation_evidence_record_links"],
            178,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_virtual_F2_readiness_contract"
            ],
            1,
        )
        self.assertEqual(
            self.program["inventory"]["virtual_F2_readiness_contract_links"],
            1,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_mass_constrained_structural_surrogate"
            ],
            1,
        )
        self.assertEqual(
            self.program["inventory"][
                "mass_constrained_structural_surrogate_component_credits"
            ],
            0,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_valve_dimensional_surrogate"
            ],
            3,
        )
        self.assertEqual(
            self.program["inventory"][
                "valve_dimensional_surrogate_component_CAE_credits"
            ],
            0,
        )
        self.assertEqual(
            self.program["inventory"]["pet_tasks_with_k16_envelope_flow_surrogate"],
            4,
        )
        self.assertEqual(
            self.program["inventory"]["k16_envelope_flow_surrogate_links"], 4
        )
        self.assertEqual(
            self.program["inventory"]["k16_evaluated_zeroD_operating_points"], 0
        )
        self.assertEqual(
            self.program["inventory"][
                "k16_envelope_flow_surrogate_component_CAE_credits"
            ],
            0,
        )
        self.assertEqual(
            self.program["inventory"]["pet_tasks_with_charge_air_chain_surrogate"],
            5,
        )
        self.assertEqual(
            self.program["inventory"]["charge_air_chain_surrogate_links"], 5
        )
        self.assertEqual(
            self.program["inventory"]["charge_air_evaluated_zeroD_operating_points"],
            0,
        )
        self.assertEqual(
            self.program["inventory"][
                "charge_air_chain_surrogate_component_CAE_credits"
            ],
            0,
        )
        self.assertEqual(
            self.program["inventory"]["pet_tasks_with_heat_shield_thermal_surrogate"],
            1,
        )
        self.assertEqual(
            self.program["inventory"]["heat_shield_thermal_surrogate_links"], 1
        )
        self.assertEqual(
            self.program["inventory"]["heat_shield_evaluated_thermal_operating_points"],
            0,
        )
        self.assertEqual(
            self.program["inventory"][
                "heat_shield_thermal_surrogate_component_CAE_credits"
            ],
            0,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_turbo_lubrication_control_topology_contract"
            ],
            40,
        )
        self.assertEqual(
            self.program["inventory"]["turbo_lubrication_control_topology_links"],
            40,
        )
        self.assertEqual(
            self.program["inventory"]["turbo_lubrication_control_symbolic_equations"],
            10,
        )
        self.assertEqual(
            self.program["inventory"]["turbo_lubrication_control_blocked_load_cases"],
            6,
        )
        self.assertEqual(
            self.program["inventory"]["turbo_lubrication_control_component_CAE_credits"],
            0,
        )
        self.assertEqual(
            self.program["inventory"][
                "promoted_linked_reference_solver_physicsnemo_simready_or_manufacturing_results"
            ],
            0,
        )
        self.assertEqual(
            self.program["inventory"]["turbo_integration_seed_candidate_occurrences"],
            325,
        )
        self.assertEqual(
            self.program["inventory"]["turbo_integration_seed_candidate_part_masters"],
            316,
        )
        self.assertEqual(
            self.program["inventory"]["turbo_integration_seed_human_read_occurrences"],
            10,
        )
        self.assertEqual(
            self.program["inventory"]["turbo_integration_seed_configured_bom_entries"],
            0,
        )
        seed = self.program["first_vehicle_integration_seed"]
        self.assertEqual(
            seed["integration_target"]["configuration_candidate"]["model_year"],
            1998,
        )
        self.assertEqual(
            seed["integration_target"]["configuration_candidate"]["market_group"],
            "rest_of_world_unmarked",
        )
        self.assertFalse(seed["assembly_gates"]["functional_vehicle"])
        self.assertEqual(self.program["inventory"]["functional_flow_types"], 10)
        self.assertEqual(self.program["inventory"]["functional_flow_edges"], 29)
        self.assertEqual(
            self.program["inventory"]["functional_flow_work_package_bindings"],
            239,
        )
        self.assertEqual(
            self.program["inventory"]["functional_flow_openusd_f0_stages"], 1
        )
        self.assertEqual(
            self.program["inventory"]["functional_flow_openusd_system_markers"], 10
        )
        self.assertEqual(
            self.program["inventory"]["functional_flow_openusd_curves"], 29
        )
        self.assertEqual(
            self.program["inventory"]["functional_flow_simready_preflight_passes"],
            0,
        )
        self.assertEqual(
            self.program["inventory"]["pet_openusd_part_master_prims"], 6013
        )
        self.assertEqual(self.program["inventory"]["pet_openusd_shard_layers"], 16)
        self.assertEqual(
            self.program["inventory"]["pet_openusd_system_membership_links"], 6325
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_openusd_masters_with_exact_oem_proxy_candidate"
            ],
            9,
        )
        self.assertEqual(
            self.program["inventory"]["pet_openusd_exact_oem_proxy_candidate_links"],
            9,
        )
        self.assertEqual(self.program["inventory"]["pet_openusd_geometry_prims"], 0)
        self.assertEqual(
            self.program["inventory"]["pet_openusd_simready_validated_prims"], 0
        )
        self.assertEqual(
            self.program["inventory"]["pet_visual_proxy_instances"], 6013
        )
        self.assertEqual(
            self.program["inventory"]["pet_visual_proxy_catalogue_coverage_ratio"],
            1.0,
        )
        self.assertEqual(
            self.program["inventory"]["pet_visual_proxy_archetype_prototypes"],
            42,
        )
        self.assertEqual(
            self.program["inventory"]["pet_visual_proxy_system_groups"], 10
        )
        self.assertEqual(
            self.program["inventory"]["pet_visual_proxy_shard_layers"], 16
        )
        self.assertEqual(
            self.program["inventory"]["pet_visual_proxy_engineering_geometry"],
            0,
        )
        self.assertEqual(
            self.program["inventory"]["pet_visual_proxy_positioned_vehicle_parts"],
            0,
        )
        self.assertEqual(
            self.program["inventory"]["pet_catalogue_digital_twin_composed_stages"],
            1,
        )
        self.assertEqual(
            self.program["inventory"]["pet_visual_proxy_simready_validated"], 0
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_catalogue_openusd_strict_validated_root_stages"
            ],
            3,
        )
        self.assertEqual(
            self.program["inventory"]["pet_catalogue_openusd_validation_passes"],
            1,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_catalogue_openusd_composition_resolution_passes"
            ],
            1,
        )
        self.assertEqual(
            self.program["inventory"]["pet_engineering_archetype_count"], 42
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_lexical_archetype_hypothesis"
            ],
            5380,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_tasks_with_system_fallback_archetype_hypothesis"
            ],
            633,
        )
        self.assertEqual(
            self.program["inventory"]["pet_unclassified_archetype_routes"], 0
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_human_reviewed_archetype_classifications"
            ],
            0,
        )
        classification = self.program["pet_archetype_classification"]
        self.assertEqual(classification["scope"]["part_master_routes"], 6013)
        self.assertEqual(classification["scope"]["lexical_hypothesis_routes"], 5380)
        self.assertEqual(
            classification["scope"]["system_context_only_fallback_routes"], 633
        )
        self.assertEqual(classification["scope"]["unclassified_routes"], 0)
        self.assertEqual(classification["scope"]["human_reviewed_routes"], 0)
        self.assertFalse(
            classification["audit"]["policy"][
                "system_fallback_is_part_classification"
            ]
        )
        self.assertEqual(
            self.program["inventory"]["pet_material_process_routing_tasks"],
            6013,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_porschefanatics_exact_replacement_links"
            ],
            6,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_part_masters_with_porschefanatics_exact_replacement_links"
            ],
            2,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_porschefanatics_qualified_material_basis_links"
            ],
            0,
        )
        self.assertEqual(
            self.program["inventory"][
                "pet_material_process_archetype_profiles"
            ],
            42,
        )
        self.assertEqual(
            self.program["inventory"]["pet_tasks_with_additive_route_candidate"],
            5405,
        )
        self.assertEqual(
            self.program["inventory"]["pet_tasks_with_titanium_family_candidate"],
            450,
        )
        self.assertEqual(self.program["inventory"]["pet_selected_materials"], 0)
        self.assertEqual(
            self.program["inventory"]["pet_selected_manufacturing_routes"], 0
        )
        self.assertEqual(
            self.program["inventory"][
                "vehicle_reference_frame_sourced_dimensions"
            ],
            7,
        )
        self.assertEqual(
            self.program["inventory"][
                "vehicle_reference_frame_sourced_mass_constraints"
            ],
            4,
        )
        self.assertEqual(
            self.program["inventory"]["vehicle_reference_frame_curve_prims"],
            5,
        )
        self.assertEqual(
            self.program["inventory"]["vehicle_reference_frame_positioned_parts"],
            0,
        )
        material_process = self.program["pet_material_process_routing"]
        self.assertEqual(material_process["scope"]["part_master_routing_tasks"], 6013)
        self.assertEqual(material_process["scope"]["archetype_profiles"], 42)
        self.assertEqual(material_process["scope"]["selected_materials"], 0)
        self.assertEqual(
            material_process["scope"]["selected_manufacturing_routes"], 0
        )
        self.assertTrue(
            all(value is False for value in material_process["claim_boundary"].values())
        )
        commercial = self.program["pet_porschefanatics_crosswalk"]
        self.assertEqual(commercial["scope"]["exact_pet_replacement_links"], 6)
        self.assertEqual(commercial["scope"]["linked_pet_part_masters"], 2)
        self.assertEqual(
            commercial["scope"]["links_with_qualified_material_basis"], 0
        )
        self.assertTrue(
            all(value is False for value in commercial["claim_boundary"].values())
        )
        reference_frame = self.program["vehicle_reference_frame"]
        self.assertEqual(reference_frame["scope"]["sourced_dimensions"], 7)
        self.assertEqual(reference_frame["scope"]["sourced_mass_constraints"], 4)
        self.assertEqual(reference_frame["scope"]["positioned_vehicle_parts"], 0)
        self.assertEqual(
            reference_frame["validation"]["minimum_usd_validation"],
            "not_run_preflight_blocked",
        )
        self.assertIsNone(
            reference_frame["uncertainty_boundary"][
                "body_to_axle_longitudinal_transform"
            ]
        )
        self.assertTrue(
            all(
                value is False
                for value in reference_frame["claim_boundary"].values()
            )
        )
        self.assertEqual(self.program["inventory"]["virtual_mission_contracts"], 7)
        self.assertEqual(
            self.program["inventory"]["closed_multiphysics_balance_equations"],
            0,
        )
        self.assertEqual(
            self.program["inventory"]["passed_virtual_vehicle_missions"], 0
        )
        flow = self.program["functional_flow_integration"]
        self.assertEqual(flow["scope"]["covered_integration_interface_pairs"], 20)
        self.assertFalse(flow["assembly_readiness"]["functioning_vehicle"])
        self.assertEqual(flow["openusd_f0"]["stage"]["system_marker_count"], 10)
        self.assertEqual(flow["openusd_f0"]["stage"]["flow_curve_count"], 29)
        self.assertFalse(flow["openusd_f0"]["claim_boundary"]["is_vehicle_geometry"])
        self.assertEqual(flow["simready_preflight"]["status"], "blocked")
        self.assertEqual(len(flow["simready_preflight"]["blockers"]), 7)
        self.assertFalse(
            flow["simready_preflight"]["result_boundary"]["simready_validated"]
        )
        pet_openusd = self.program["pet_openusd_federation"]
        self.assertEqual(pet_openusd["scope"]["part_master_prims"], 6013)
        self.assertEqual(pet_openusd["scope"]["documentary_occurrences"], 12879)
        self.assertEqual(pet_openusd["scope"]["geometry_prim_count"], 0)
        self.assertFalse(pet_openusd["validation"]["simready_validated"])
        self.assertEqual(len(pet_openusd["proxy_linkage"]["links"]), 9)
        self.assertFalse(
            pet_openusd["proxy_linkage"]["geometry_composed_into_federation"]
        )
        self.assertTrue(
            all(value is False for value in pet_openusd["claim_boundary"].values())
        )
        visual_twin = self.program["pet_catalogue_visual_twin"]
        self.assertEqual(visual_twin["atlas"]["part_master_proxy_instances"], 6013)
        self.assertEqual(visual_twin["atlas"]["catalogue_master_coverage_ratio"], 1.0)
        self.assertEqual(visual_twin["atlas"]["engineering_geometry_count"], 0)
        self.assertEqual(visual_twin["atlas"]["positioned_vehicle_part_count"], 0)
        self.assertFalse(
            visual_twin["physicsnemo_dataset_boundary"][
                "atlas_is_training_or_validation_data"
            ]
        )
        self.assertFalse(visual_twin["validation"]["simready_validated"])
        self.assertEqual(
            visual_twin["openusd_validation"]["status"],
            "passed_openusd_strict_not_simready",
        )
        self.assertEqual(
            visual_twin["openusd_validation"]["results"][
                "composition_resolution"
            ],
            "passed",
        )
        self.assertFalse(
            visual_twin["openusd_validation"]["results"]["simready_validated"]
        )
        self.assertTrue(
            all(value is False for value in visual_twin["claim_boundary"].values())
        )
        self.assertTrue(
            all(
                value is False
                for value in visual_twin["openusd_validation"][
                    "claim_boundary"
                ].values()
            )
        )
        self.assertEqual(
            self.program["variant_configuration"]["strategy"]["first_integration_target"],
            "993-turbo",
        )
        self.assertFalse(
            self.program["variant_configuration"]["strategy"]["universal_993_bom_allowed"]
        )
        self.assertFalse(
            self.program["variant_configuration"]["scope"]["complete_configuration_universe"]
        )
        self.assertEqual(
            set(
                self.program["variant_configuration"]["catalogue_configuration_universe"][
                    "missing_body_style_contracts"
                ]
            ),
            {"CABRIO", "TARGA"},
        )
        self.assertEqual(
            sum(system["catalogue_reference_count_aggregate"] for system in self.program["systems"]),
            scope["reference_count_aggregate"],
        )

    def test_every_catalogue_illustration_is_a_fail_closed_work_package(self) -> None:
        packages = [package for system in self.program["systems"] for package in system["work_packages"]]
        self.assertEqual(len(packages), 239)
        self.assertEqual(len({package["work_package_id"] for package in packages}), 239)
        for package in packages:
            self.assertEqual(package["current_fidelity"], "F0_reference")
            self.assertEqual(package["current_status"], "inventory_only")
            self.assertEqual(package["catalogue_semantics"], "aggregate_reference_rows_not_mounted_part_instances")
            self.assertIsNone(package["decisions"]["material"])
            self.assertIsNone(package["decisions"]["manufacturing_route"])
            self.assertFalse(package["decisions"]["functional_release"])
            self.assertEqual(package["evidence_state"]["reference_solver_result"], "not_run")

    def test_llm_physicsnemo_and_omniverse_cannot_overclaim(self) -> None:
        claims = self.program["claim_policy"]
        self.assertTrue(claims["virtual_only"])
        self.assertFalse(claims["functioning_vehicle_claim"])
        self.assertFalse(claims["roadworthy_claim"])
        self.assertFalse(claims["manufacturing_release_claim"])
        self.assertIn("solveur_physique_de_reference", self.program["llm_policy"]["forbidden_roles"])
        self.assertFalse(self.program["physicsnemo_policy"]["execution_enabled"])
        self.assertIn("GeoTransolver", self.program["physicsnemo_policy"]["verified_model_families"])
        self.assertEqual(self.program["physicsnemo_policy"]["role"], "surrogate_only_after_converged_reference_solver_dataset")
        self.assertEqual(self.program["omniverse_policy"]["current_status"], "blocked_before_preflight")
        proxy_preflight = self.program["omniverse_policy"]["latest_local_proxy_validation_preflight"]
        self.assertEqual(proxy_preflight["status"], "blocked")
        self.assertIn("openusd_python_unavailable", proxy_preflight["blockers"])
        self.assertFalse(self.program["omniverse_policy"]["simready_claim"])

    def test_all_systems_are_routed_and_workstreams_are_ordered(self) -> None:
        domain_ids = set(self.program["simulation_domains"])
        for system in self.program["systems"]:
            self.assertTrue(system["simulation_domain_ids"])
            self.assertTrue(set(system["simulation_domain_ids"]).issubset(domain_ids))
        workstreams = self.program["engineering_workstreams"]
        self.assertEqual([item["workstream_id"] for item in workstreams], [
            "VEH-00", "VEH-10", "VEH-20", "VEH-30", "VEH-40", "VEH-50", "VEH-60", "VEH-90"
        ])
        self.assertIn("VEH-20", workstreams[-1]["depends_on"])
        self.assertIn("VEH-60", workstreams[-1]["depends_on"])

    def test_only_documentary_gate_is_currently_passed(self) -> None:
        self.assertEqual(self.program["readiness"]["documentary_gates_passed"], 1)
        self.assertEqual(self.program["readiness"]["integration_gate_count"], 11)
        self.assertEqual(self.program["readiness"]["F2_work_packages"], 0)
        self.assertEqual(self.program["readiness"]["F3_work_packages"], 0)
        self.assertEqual(self.program["readiness"]["integrated_vehicle_systems"], 0)

    def test_checked_in_program_is_current(self) -> None:
        self.assertEqual(generator.run(write=False), 0)
        payload = json.loads(generator.OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(payload, self.program)


if __name__ == "__main__":
    unittest.main()
