import hashlib
import importlib.util
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_pet_993_engineering_readiness.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_pet_993_engineering_readiness", MODULE_PATH
)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Pet993EngineeringReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = json.loads(generator.OUTPUT.read_text(encoding="utf-8"))
        cls.tasks = []
        for shard in cls.index["output"]["shards"]:
            path = ROOT / shard["path"]
            with path.open("r", encoding="utf-8") as handle:
                cls.tasks.extend(json.loads(line) for line in handle if line.strip())

    def test_one_task_exists_for_every_part_master(self) -> None:
        scope = self.index["scope"]
        self.assertEqual(scope["part_master_twins"], 6013)
        self.assertEqual(scope["engineering_tasks"], 6013)
        self.assertEqual(len(self.tasks), 6013)
        self.assertEqual(len({item["engineering_task_id"] for item in self.tasks}), 6013)
        self.assertEqual(len({item["part_master_twin_id"] for item in self.tasks}), 6013)

    def test_configuration_and_turbo_partitions_close(self) -> None:
        scope = self.index["scope"]
        self.assertEqual(scope["tasks_with_configuration_evidence"], 684)
        self.assertEqual(scope["tasks_without_configuration_evidence"], 5329)
        self.assertEqual(scope["tasks_with_configuration_candidate_links"], 659)
        self.assertEqual(scope["tasks_with_exception_contract_links"], 12)
        self.assertEqual(scope["tasks_with_turbo_integration_evidence"], 317)
        self.assertEqual(scope["tasks_with_workshop_manual_candidates"], 417)
        self.assertEqual(scope["workshop_manual_candidate_links"], 1569)
        self.assertEqual(scope["promoted_workshop_manual_measurements_or_torques"], 0)
        self.assertEqual(scope["tasks_with_linked_catalog_part_engineering_records"], 8)
        self.assertEqual(scope["linked_catalog_part_engineering_record_links"], 8)
        self.assertEqual(
            scope["promoted_catalog_material_process_geometry_or_validation_claims"],
            0,
        )
        self.assertEqual(scope["tasks_with_linked_simulation_evidence"], 171)
        self.assertEqual(scope["linked_simulation_evidence_record_links"], 178)
        self.assertEqual(scope["tasks_with_virtual_F2_readiness_contract"], 1)
        self.assertEqual(scope["virtual_F2_readiness_contract_links"], 1)
        self.assertEqual(scope["tasks_with_mass_constrained_structural_surrogate"], 1)
        self.assertEqual(
            scope["mass_constrained_structural_surrogate_component_credits"], 0
        )
        self.assertEqual(scope["tasks_with_valve_dimensional_surrogate"], 3)
        self.assertEqual(scope["valve_dimensional_surrogate_links"], 3)
        self.assertEqual(
            scope["valve_dimensional_surrogate_component_CAE_credits"], 0
        )
        self.assertEqual(scope["tasks_with_k16_envelope_flow_surrogate"], 4)
        self.assertEqual(scope["k16_envelope_flow_surrogate_links"], 4)
        self.assertEqual(scope["k16_evaluated_zeroD_operating_points"], 0)
        self.assertEqual(
            scope["k16_envelope_flow_surrogate_component_CAE_credits"], 0
        )
        self.assertEqual(scope["tasks_with_charge_air_chain_surrogate"], 5)
        self.assertEqual(scope["charge_air_chain_surrogate_links"], 5)
        self.assertEqual(scope["charge_air_evaluated_zeroD_operating_points"], 0)
        self.assertEqual(scope["charge_air_chain_surrogate_component_CAE_credits"], 0)
        self.assertEqual(scope["tasks_with_heat_shield_thermal_surrogate"], 1)
        self.assertEqual(scope["heat_shield_thermal_surrogate_links"], 1)
        self.assertEqual(scope["heat_shield_evaluated_thermal_operating_points"], 0)
        self.assertEqual(scope["heat_shield_thermal_surrogate_component_CAE_credits"], 0)
        self.assertEqual(
            scope["tasks_with_turbo_lubrication_control_topology_contract"], 40
        )
        self.assertEqual(scope["turbo_lubrication_control_topology_links"], 40)
        self.assertEqual(scope["turbo_lubrication_control_symbolic_equations"], 10)
        self.assertEqual(scope["turbo_lubrication_control_blocked_load_cases"], 6)
        self.assertEqual(scope["turbo_lubrication_control_component_CAE_credits"], 0)
        self.assertEqual(scope["tasks_with_oil_tank_circuit_topology_contract"], 81)
        self.assertEqual(scope["oil_tank_circuit_topology_links"], 81)
        self.assertEqual(scope["oil_tank_circuit_symbolic_equations"], 11)
        self.assertEqual(scope["oil_tank_circuit_blocked_load_cases"], 7)
        self.assertEqual(scope["oil_tank_circuit_component_CAE_credits"], 0)
        self.assertEqual(scope["tasks_with_oil_cooler_circuit_topology_contract"], 43)
        self.assertEqual(scope["oil_cooler_circuit_topology_links"], 43)
        self.assertEqual(scope["oil_cooler_circuit_symbolic_equations"], 14)
        self.assertEqual(scope["oil_cooler_circuit_blocked_load_cases"], 8)
        self.assertEqual(scope["oil_cooler_circuit_component_CAE_credits"], 0)
        self.assertEqual(scope["tasks_with_exact_oem_F1_envelope_candidates"], 9)
        self.assertEqual(scope["exact_oem_F1_envelope_candidate_links"], 9)
        self.assertEqual(
            scope[
                "promoted_linked_reference_solver_physicsnemo_simready_or_manufacturing_results"
            ],
            0,
        )
        self.assertEqual(
            scope["tasks_with_configuration_evidence"]
            + scope["tasks_without_configuration_evidence"],
            6013,
        )

    def test_priority_and_next_gate_coverage_closes(self) -> None:
        self.assertEqual(
            self.index["coverage"]["tasks_by_priority"],
            {"P0": 317, "P1": 206, "P2": 161, "P3": 2617, "P4": 2712},
        )
        self.assertEqual(
            self.index["coverage"]["tasks_by_next_required_gate"],
            {
                "author_editable_geometry_and_measured_interfaces": 664,
                "infer_and_cross_check_F2_interface_coordinates_with_uncertainty": 1,
                "replace_F1_valve_surrogate_with_F2_interface_geometry": 3,
                "resolve_104_01_configuration_topology_F2_interfaces_and_oil_properties": 12,
                "resolve_104_05_configuration_topology_F2_interfaces_oil_air_properties_and_fan_control": 1,
                "resolve_202_16_configuration_topology_side_assignment_and_F2_interfaces": 3,
                "resolve_configuration_applicability": 5329,
            },
        )
        self.assertEqual(
            self.index["coverage"]["tasks_by_current_fidelity"],
            {
                "F0_reference": 5842,
                "F1_charge_air_chain_guides_unvalidated": 5,
                "F1_heat_shield_envelope_thermal_readiness_unvalidated": 1,
                "F1_k16_envelope_diameter_guides_unvalidated": 4,
                "F1_mass_constrained_structural_surrogate_virtual_F2_readiness": 1,
                "F1_oil_tank_circuit_topology_readiness_unvalidated": 81,
                "F1_oil_cooler_circuit_topology_readiness_unvalidated": 41,
                "F1_turbo_lubrication_control_topology_readiness_unvalidated": 35,
                "F1_valve_dimensional_surrogate_unvalidated": 3,
            },
        )
        self.assertEqual(
            Counter(
                task["risk_and_priority"]["priority"] for task in self.tasks
            ),
            Counter(self.index["coverage"]["tasks_by_priority"]),
        )
        self.assertEqual(
            sum(self.index["coverage"]["tasks_by_engineering_archetype"].values()),
            6013,
        )

    def test_archetype_hypothesis_routing_closes_without_human_review_claim(self) -> None:
        scope = self.index["scope"]
        audit = self.index["classification_audit"]
        self.assertEqual(scope["tasks_with_lexical_archetype_hypothesis"], 5380)
        self.assertEqual(
            scope["tasks_with_system_fallback_archetype_hypothesis"], 633
        )
        self.assertEqual(scope["unclassified_archetype_routes"], 0)
        self.assertEqual(scope["human_reviewed_archetype_classifications"], 0)
        self.assertEqual(audit["part_master_routes"], 6013)
        self.assertEqual(audit["archetype_count"], 42)
        self.assertEqual(audit["description_keyword_routes"], 5380)
        self.assertEqual(audit["primary_pet_system_fallback_routes"], 633)
        self.assertFalse(audit["policy"]["system_fallback_is_part_classification"])
        self.assertFalse(audit["policy"]["simulation_domain_route_is_solver_result"])
        self.assertTrue(audit["policy"]["manual_or_geometry_review_required"])
        self.assertEqual(
            self.index["coverage"]["tasks_by_classification_confidence"],
            {
                "lexical_candidate_not_human_reviewed": 5380,
                "system_context_only_not_part_classification": 633,
            },
        )
        for task in self.tasks:
            route = task["engineering_route"]
            self.assertTrue(route["classification_rule_id"])
            self.assertIn(
                route["classification_evidence_kind"],
                {"description_keyword", "primary_pet_system_context"},
            )
            self.assertFalse(route["human_reviewed_classification"])

    def test_all_engineering_claims_remain_fail_closed(self) -> None:
        verified_models = {
            "GeoTransolver", "Transolver", "MeshGraphNet", "FIGConvUNet", "DoMINO"
        }
        for task in self.tasks:
            self.assertIsNone(task["engineering_route"]["selected_material"])
            self.assertIsNone(task["engineering_route"]["selected_manufacturing_route"])
            self.assertEqual(task["engineering_gates"]["reference_solver"], "not_run")
            self.assertEqual(task["engineering_gates"]["physicsnemo"], "not_run")
            self.assertEqual(task["engineering_gates"]["omniverse_simready"], "not_run")
            self.assertTrue(
                set(task["engineering_route"]["physicsnemo_candidate_models"])
                <= verified_models
            )
            self.assertIsNone(task["engineering_route"]["physicsnemo_selected_model"])
            self.assertFalse(task["engineering_route"]["physicsnemo_execution_enabled"])
            self.assertEqual(
                task["workshop_manual_evidence"]["promoted_measurements_or_torques"],
                0,
            )
            self.assertFalse(task["workshop_manual_evidence"]["manual_review_completed"])
            self.assertEqual(
                task["catalog_part_engineering"]["material_or_process_decisions_promoted"],
                0,
            )
            self.assertEqual(
                task["linked_simulation_evidence"]["reference_solver_results_promoted"],
                0,
            )
            self.assertEqual(
                task["linked_simulation_evidence"]["physicsnemo_results_promoted"],
                0,
            )
            self.assertFalse(any(task["claims"].values()))
        self.assertFalse(self.index["engineering_readiness"]["functioning_vehicle_claim"])
        self.assertTrue(
            all(
                value == 0
                for key, value in self.index["engineering_readiness"].items()
                if key
                not in {
                    "functioning_vehicle_claim",
                    "F1_envelope_identity_linked_unvalidated",
                    "F1_mass_constrained_structural_surrogate",
                    "F1_valve_dimensional_surrogate_unvalidated",
                    "F1_k16_envelope_diameter_guides_unvalidated",
                    "F1_charge_air_chain_guides_unvalidated",
                    "F1_heat_shield_envelope_thermal_readiness_unvalidated",
                    "F1_turbo_lubrication_control_topology_readiness_unvalidated",
                    "F1_oil_tank_circuit_topology_readiness_unvalidated",
                    "F1_oil_cooler_circuit_topology_readiness_unvalidated",
                    "F1_mass_constrained_structural_surrogate_virtual_F2_readiness",
                }
            )
        )
        self.assertEqual(
            self.index["engineering_readiness"][
                "F1_envelope_identity_linked_unvalidated"
            ],
            0,
        )
        self.assertEqual(
            self.index["engineering_readiness"][
                "F1_mass_constrained_structural_surrogate"
            ],
            1,
        )
        self.assertEqual(
            self.index["engineering_readiness"][
                "F1_valve_dimensional_surrogate_unvalidated"
            ],
            3,
        )
        self.assertEqual(
            self.index["engineering_readiness"][
                "F1_k16_envelope_diameter_guides_unvalidated"
            ],
            4,
        )
        self.assertEqual(
            self.index["engineering_readiness"][
                "F1_charge_air_chain_guides_unvalidated"
            ],
            5,
        )
        self.assertEqual(
            self.index["engineering_readiness"][
                "F1_heat_shield_envelope_thermal_readiness_unvalidated"
            ],
            1,
        )
        self.assertEqual(
            self.index["engineering_readiness"][
                "F1_turbo_lubrication_control_topology_readiness_unvalidated"
            ],
            35,
        )
        self.assertEqual(
            self.index["engineering_readiness"][
                "F1_oil_tank_circuit_topology_readiness_unvalidated"
            ],
            81,
        )
        self.assertEqual(
            self.index["engineering_readiness"][
                "F1_oil_cooler_circuit_topology_readiness_unvalidated"
            ],
            41,
        )
        self.assertEqual(
            self.index["engineering_readiness"][
                "F1_mass_constrained_structural_surrogate_virtual_F2_readiness"
            ],
            1,
        )

    def test_valve_surrogates_promote_only_f1_editable_guides(self) -> None:
        valve_tasks = [
            task
            for task in self.tasks
            if any(
                record["valve_dimensional_surrogate_contract"] is not None
                for record in task["linked_simulation_evidence"]["records"]
            )
        ]
        self.assertEqual(len(valve_tasks), 3)
        self.assertEqual(
            {task["subject"]["normalized_oem_reference"] for task in valve_tasks},
            {"99310540902", "99310541901", "99310541952"},
        )
        for task in valve_tasks:
            gates = task["engineering_gates"]
            self.assertEqual(
                gates["current_fidelity"],
                "F1_valve_dimensional_surrogate_unvalidated",
            )
            self.assertEqual(
                gates["editable_geometry"],
                "F1_editable_valve_surrogate_available_not_analysis_or_F2_geometry",
            )
            self.assertEqual(
                gates["next_required_gate"],
                "replace_F1_valve_surrogate_with_F2_interface_geometry",
            )
            self.assertEqual(gates["measured_interfaces_and_tolerances"], "missing")
            self.assertEqual(gates["reference_solver"], "not_run")
            self.assertEqual(gates["physicsnemo"], "not_run")
            self.assertFalse(any(task["claims"].values()))

    def test_declared_inputs_are_observations_not_decisions(self) -> None:
        scope = self.index["scope"]
        self.assertEqual(scope["tasks_with_declared_bounding_box"], 9)
        self.assertEqual(scope["tasks_with_declared_mass"], 9)
        self.assertEqual(scope["tasks_with_non_placeholder_declared_material_label"], 1)
        for task in self.tasks:
            self.assertFalse(task["input_evidence"]["qualified_material_decision"])

    def test_exact_oem_proxy_candidates_promote_only_f1_envelope_state(self) -> None:
        promoted = [
            task
            for task in self.tasks
            if task["catalogue_proxy_geometry"]["record_count"] > 0
        ]
        self.assertEqual(len(promoted), 9)
        self.assertEqual(
            self.index["engineering_readiness"][
                "F1_envelope_identity_linked_unvalidated"
            ],
            0,
        )
        self.assertEqual(
            self.index["engineering_readiness"]["F2_interface_geometry"], 0
        )
        for task in promoted:
            proxy = task["catalogue_proxy_geometry"]
            gates = task["engineering_gates"]
            has_k16 = any(
                record["k16_envelope_flow_surrogate_contract"] is not None
                for record in task["linked_simulation_evidence"]["records"]
            )
            has_charge_air = any(
                record["charge_air_chain_surrogate_contract"] is not None
                for record in task["linked_simulation_evidence"]["records"]
            )
            has_heat_shield = any(
                record.get("heat_shield_thermal_surrogate_contract") is not None
                for record in task["linked_simulation_evidence"]["records"]
            )
            has_virtual_f2 = any(
                record["virtual_F2_readiness_contract"] is not None
                for record in task["linked_simulation_evidence"]["records"]
            )
            if has_k16:
                self.assertEqual(
                    gates["current_fidelity"],
                    "F1_k16_envelope_diameter_guides_unvalidated",
                )
                self.assertIn("F1_editable_K16", gates["editable_geometry"])
            elif has_charge_air:
                self.assertEqual(
                    gates["current_fidelity"],
                    "F1_charge_air_chain_guides_unvalidated",
                )
                self.assertIn("F1_editable_charge_air", gates["editable_geometry"])
            elif has_heat_shield:
                self.assertEqual(
                    gates["current_fidelity"],
                    "F1_heat_shield_envelope_thermal_readiness_unvalidated",
                )
                self.assertIn("F1_editable_heat_shield", gates["editable_geometry"])
            elif has_virtual_f2:
                self.assertEqual(
                    gates["current_fidelity"],
                    "F1_mass_constrained_structural_surrogate_virtual_F2_readiness",
                )
                self.assertIn(
                    "F1_mass_constrained_structural_surrogate",
                    gates["editable_geometry"],
                )
            else:
                self.assertEqual(
                    gates["current_fidelity"],
                    "F1_envelope_identity_linked_unvalidated",
                )
                self.assertIn(
                    "F1_editable_envelope_candidate", gates["editable_geometry"]
                )
            self.assertFalse(proxy["geometry_composed_into_vehicle"])
            self.assertFalse(proxy["vehicle_transform_known"])
            self.assertFalse(proxy["interface_geometry_available"])
            self.assertFalse(proxy["dimensionally_accurate_claim"])
            self.assertFalse(proxy["fitment_validated_claim"])
            for record in proxy["records"]:
                self.assertEqual(record["fidelity"], "F1_envelope")
                self.assertFalse(record["geometry_fit_validated"])

    def test_k16_surrogates_promote_four_pet_tasks_to_guides_only(self) -> None:
        k16_tasks = [
            task
            for task in self.tasks
            if any(
                record["k16_envelope_flow_surrogate_contract"] is not None
                for record in task["linked_simulation_evidence"]["records"]
            )
        ]
        self.assertEqual(len(k16_tasks), 4)
        self.assertEqual(
            {task["subject"]["normalized_oem_reference"] for task in k16_tasks},
            {"99312301351", "99312301352", "99312301451", "99312301452"},
        )
        for task in k16_tasks:
            gates = task["engineering_gates"]
            self.assertEqual(
                gates["current_fidelity"],
                "F1_k16_envelope_diameter_guides_unvalidated",
            )
            self.assertEqual(
                gates["editable_geometry"],
                "F1_editable_K16_envelope_and_diameter_guides_not_F2_or_F3_geometry",
            )
            self.assertEqual(gates["next_required_gate"], "resolve_configuration_applicability")
            self.assertEqual(gates["measured_interfaces_and_tolerances"], "missing")
            self.assertEqual(gates["reference_solver"], "not_run")
            self.assertEqual(gates["physicsnemo"], "not_run")
            self.assertFalse(any(task["claims"].values()))

    def test_charge_air_surrogates_promote_five_pet_tasks_to_guides_only(self) -> None:
        charge_air_tasks = [
            task
            for task in self.tasks
            if any(
                record["charge_air_chain_surrogate_contract"] is not None
                for record in task["linked_simulation_evidence"]["records"]
            )
        ]
        self.assertEqual(len(charge_air_tasks), 5)
        self.assertEqual(
            {task["subject"]["normalized_oem_reference"] for task in charge_air_tasks},
            {
                "99311033053",
                "99311034054",
                "99311063256",
                "99311063356",
                "99360611400",
            },
        )
        for task in charge_air_tasks:
            gates = task["engineering_gates"]
            self.assertEqual(
                gates["current_fidelity"],
                "F1_charge_air_chain_guides_unvalidated",
            )
            self.assertEqual(
                gates["editable_geometry"],
                "F1_editable_charge_air_envelopes_and_unpositioned_diameter_guides_not_F2_or_F3_geometry",
            )
            self.assertEqual(
                gates["next_required_gate"], "resolve_configuration_applicability"
            )
            self.assertEqual(gates["measured_interfaces_and_tolerances"], "missing")
            self.assertEqual(gates["reference_solver"], "not_run")
            self.assertEqual(gates["physicsnemo"], "not_run")
            self.assertFalse(any(task["claims"].values()))

    def test_heat_shield_surrogate_promotes_one_task_to_thermal_readiness_only(self) -> None:
        heat_tasks = [
            task
            for task in self.tasks
            if any(
                record.get("heat_shield_thermal_surrogate_contract") is not None
                for record in task["linked_simulation_evidence"]["records"]
            )
        ]
        self.assertEqual(len(heat_tasks), 1)
        heat = heat_tasks[0]
        self.assertEqual(heat["subject"]["normalized_oem_reference"], "99312311351")
        gates = heat["engineering_gates"]
        self.assertEqual(
            gates["current_fidelity"],
            "F1_heat_shield_envelope_thermal_readiness_unvalidated",
        )
        self.assertEqual(gates["next_required_gate"], "resolve_configuration_applicability")
        contract = heat["linked_simulation_evidence"]["records"][0][
            "heat_shield_thermal_surrogate_contract"
        ]
        self.assertEqual(contract["symbolic_thermal_equation_count"], 7)
        self.assertEqual(contract["evaluated_thermal_operating_points"], 0)
        self.assertFalse(contract["qualified_material_decision"])
        self.assertFalse(contract["component_CAE_credit"])
        self.assertFalse(contract["physicsnemo_execution_enabled"])
        self.assertFalse(any(heat["claims"].values()))

    def test_202_16_topology_promotes_only_the_remaining_thirty_five_tasks(self) -> None:
        topology_tasks = [
            task
            for task in self.tasks
            if any(
                record.get("turbo_lubrication_control_topology_contract") is not None
                for record in task["linked_simulation_evidence"]["records"]
            )
        ]
        self.assertEqual(len(topology_tasks), 40)
        promoted = [
            task
            for task in topology_tasks
            if task["engineering_gates"]["current_fidelity"]
            == "F1_turbo_lubrication_control_topology_readiness_unvalidated"
        ]
        self.assertEqual(len(promoted), 35)
        for task in promoted:
            gates = task["engineering_gates"]
            self.assertEqual(
                gates["editable_geometry"],
                "F1_generated_nonspatial_turbo_lubrication_control_topology_not_part_geometry",
            )
            topology = next(
                record["turbo_lubrication_control_topology_contract"]
                for record in task["linked_simulation_evidence"]["records"]
                if record.get("turbo_lubrication_control_topology_contract")
                is not None
            )
            self.assertEqual(topology["symbolic_equation_count"], 10)
            self.assertEqual(topology["known_interface_coordinate_count"], 0)
            self.assertFalse(topology["component_CAE_credit"])
            self.assertFalse(topology["physicsnemo_execution_enabled"])
            self.assertFalse(any(task["claims"].values()))

    def test_104_01_topology_promotes_eighty_one_tasks_without_geometry_credit(self) -> None:
        topology_tasks = [
            task
            for task in self.tasks
            if any(
                record.get("oil_tank_circuit_topology_contract") is not None
                for record in task["linked_simulation_evidence"]["records"]
            )
        ]
        self.assertEqual(len(topology_tasks), 81)
        self.assertTrue(
            all(
                task["engineering_gates"]["current_fidelity"]
                == "F1_oil_tank_circuit_topology_readiness_unvalidated"
                for task in topology_tasks
            )
        )
        for task in topology_tasks:
            self.assertEqual(
                task["engineering_gates"]["editable_geometry"],
                "F1_generated_nonspatial_oil_tank_circuit_topology_not_part_geometry",
            )
            topology = next(
                record["oil_tank_circuit_topology_contract"]
                for record in task["linked_simulation_evidence"]["records"]
                if record.get("oil_tank_circuit_topology_contract") is not None
            )
            self.assertEqual(topology["symbolic_equation_count"], 11)
            self.assertEqual(topology["known_interface_coordinate_count"], 0)
            self.assertFalse(topology["component_CAE_credit"])
            self.assertFalse(topology["physicsnemo_execution_enabled"])
            self.assertFalse(any(task["claims"].values()))

    def test_104_05_topology_links_forty_three_and_promotes_forty_one_tasks(self) -> None:
        topology_tasks = [
            task
            for task in self.tasks
            if any(
                record.get("oil_cooler_circuit_topology_contract") is not None
                for record in task["linked_simulation_evidence"]["records"]
            )
        ]
        self.assertEqual(len(topology_tasks), 43)
        promoted = [
            task
            for task in topology_tasks
            if task["engineering_gates"]["current_fidelity"]
            == "F1_oil_cooler_circuit_topology_readiness_unvalidated"
        ]
        self.assertEqual(len(promoted), 41)
        for task in promoted:
            self.assertEqual(
                task["engineering_gates"]["editable_geometry"],
                "F1_generated_nonspatial_oil_cooler_circuit_topology_not_part_geometry",
            )
            topology = next(
                record["oil_cooler_circuit_topology_contract"]
                for record in task["linked_simulation_evidence"]["records"]
                if record.get("oil_cooler_circuit_topology_contract") is not None
            )
            self.assertEqual(topology["symbolic_equation_count"], 14)
            self.assertEqual(topology["known_interface_coordinate_count"], 0)
            self.assertFalse(topology["component_CAE_credit"])
            self.assertFalse(topology["physicsnemo_execution_enabled"])
            self.assertFalse(any(task["claims"].values()))

    def test_shards_match_the_versioned_index(self) -> None:
        shards = self.index["output"]["shards"]
        self.assertEqual([item["shard_id"] for item in shards], list("0123456789abcdef"))
        self.assertEqual(sum(item["record_count"] for item in shards), 6013)
        for shard in shards:
            path = ROOT / shard["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(sha256_file(path), shard["sha256"])

    def test_first_batch_is_unique_unreviewed_p0_work(self) -> None:
        batch = self.index["first_engineering_batch"]
        self.assertIn("not_human_reviewed", batch["selection_status"])
        self.assertEqual(batch["batch_size"], 100)
        ids = [item["engineering_task_id"] for item in batch["tasks"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(item["priority"] == "P0" for item in batch["tasks"]))
        self.assertEqual(batch["tasks"][0]["normalized_oem_reference"], "99311502153")
        self.assertTrue(batch["tasks"][0]["declared_bounding_box_available"])
        self.assertTrue(batch["tasks"][0]["declared_mass_available"])
        self.assertTrue(batch["tasks"][0]["declared_material_label_available"])
        self.assertEqual(
            batch["tasks"][0]["linked_catalog_part_engineering_record_count"], 1
        )

    def test_engine_carrier_has_part_specific_domains(self) -> None:
        carrier = next(
            task
            for task in self.tasks
            if task["subject"]["normalized_oem_reference"] == "99311502153"
        )
        route = carrier["engineering_route"]
        self.assertEqual(
            route["engineering_archetype"],
            "load_bearing_bracket_carrier_or_mount",
        )
        self.assertEqual(
            route["simulation_domain_ids"],
            ["multibody", "package_interfaces", "structural"],
        )
        self.assertTrue(
            set(route["simulation_domain_ids"])
            < set(route["system_candidate_simulation_domain_ids"])
        )
        linked = carrier["catalog_part_engineering"]
        self.assertEqual(linked["record_count"], 1)
        self.assertEqual(linked["records"][0]["part_id"], "993-ENG-CARRIER-0001")
        self.assertEqual(linked["records"][0]["validation"]["status"], "concept")
        simulation = carrier["linked_simulation_evidence"]
        self.assertEqual(simulation["record_count"], 1)
        self.assertEqual(len(simulation["records"][0]["load_cases"]), 6)
        self.assertFalse(simulation["records"][0]["analysis_geometry_available"])
        virtual_f2 = simulation["records"][0]["virtual_F2_readiness_contract"]
        self.assertEqual(virtual_f2["interface_hypothesis_count"], 2)
        self.assertEqual(virtual_f2["unknown_parameter_count"], 19)
        self.assertEqual(virtual_f2["blocked_load_case_count"], 8)
        self.assertTrue(virtual_f2["mass_constraint_closed"])
        self.assertAlmostEqual(virtual_f2["equivalent_wall_mm"], 2.175319724, places=9)
        self.assertEqual(virtual_f2["interface_search_domain_count"], 2)
        self.assertEqual(virtual_f2["selected_interface_point_count"], 0)
        self.assertFalse(virtual_f2["mass_constrained_surrogate_component_credit"])
        self.assertFalse(virtual_f2["F2_interface_geometry"])
        self.assertEqual(carrier["catalogue_proxy_geometry"]["record_count"], 1)
        self.assertEqual(
            carrier["engineering_gates"]["next_required_gate"],
            "infer_and_cross_check_F2_interface_coordinates_with_uncertainty",
        )
        self.assertEqual(
            carrier["engineering_gates"]["current_fidelity"],
            "F1_mass_constrained_structural_surrogate_virtual_F2_readiness",
        )
        self.assertIsNone(route["selected_material"])
        self.assertIsNone(route["selected_manufacturing_route"])

    def test_shared_physicsnemo_and_omniverse_policies_are_blocked(self) -> None:
        policies = self.index["shared_execution_policies"]
        self.assertEqual(
            policies["physicsnemo"]["discovered_commit"],
            "4fbfcfd62bf050b48ceec6b438da409b9f4644b3",
        )
        self.assertFalse(policies["physicsnemo"]["execution_enabled"])
        self.assertEqual(policies["omniverse"]["current_status"], "blocked_before_preflight")
        self.assertFalse(policies["omniverse"]["simready_claim"])
        self.assertEqual(
            policies["omniverse"]["required_stage_order"][:3],
            ["source_asset", "preflight_and_content_agents_readiness", "asset_context"],
        )

    def test_checked_in_outputs_are_current(self) -> None:
        self.assertEqual(generator.main(["--check"]), 0)
        self.assertEqual(generator.main(["--check-index"]), 0)


if __name__ == "__main__":
    unittest.main()
