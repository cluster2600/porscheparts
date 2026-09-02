from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins/reference-917-engine"
CONTRACT = TWIN / "unsteady-network-f39.json"
RUNNER = TWIN / "source/run_unsteady_network_f39.py"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_runner():
    spec = importlib.util.spec_from_file_location("run_unsteady_network_f39", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UnsteadyNetworkF39Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = load_runner()
        cls.contract = load(CONTRACT)

    def test_contract_schema_and_hash_bound_sources(self) -> None:
        self.runner.validate_contract(self.contract)
        evidence = self.runner.verify_sources(ROOT, self.contract)
        self.assertEqual(self.contract["schema_version"], "1.0.0")
        self.assertEqual(self.contract["phase"], "F39")
        self.assertEqual(self.contract["asset_id"], "porsche-917-unsteady-network-f39")
        self.assertEqual(len(evidence), 6)
        self.assertTrue(all(item["hash_verified"] for item in evidence.values()))
        self.assertIn("clean_sheet_head_contract_f29", evidence)
        self.assertIn("clean_sheet_head_design_study_f29", evidence)

    def test_topology_is_exact_connected_flat12(self) -> None:
        topology = self.runner.build_topology(self.contract)
        self.runner.validate_topology(topology, self.contract)
        self.assertEqual(len(topology["pipes"]), 27)
        self.assertEqual(len(topology["junctions"]), 15)
        self.assertEqual(len(topology["cylinders"]), 12)
        self.assertEqual(len(topology["valves"]), 24)
        self.assertEqual(sum(item["physical_valve_count"] for item in topology["valves"]), 48)
        family_counts: dict[str, int] = {}
        for pipe in topology["pipes"]:
            family_counts[pipe["family"]] = family_counts.get(pipe["family"], 0) + 1
        self.assertEqual(
            family_counts,
            {"intake_trunk": 1, "intake_runner": 12, "exhaust_primary": 12, "exhaust_outlet": 2},
        )
        self.assertEqual(sum(item["aeolus_component"] == "JunctionSpec" for item in topology["junctions"]), 3)
        self.assertEqual(sum(item["aeolus_component"] == "CylinderSpec" for item in topology["junctions"]), 12)

    def test_f29_four_valve_head_and_equivalent_ports_are_explicit(self) -> None:
        phases = self.contract["phase_policy"]
        intake = phases["intake_valve_group"]
        exhaust = phases["exhaust_valve_group"]
        self.assertEqual(intake["physical_valve_count_per_cylinder"], 2)
        self.assertEqual(exhaust["physical_valve_count_per_cylinder"], 2)
        self.assertEqual((intake["open_deg"], intake["center_deg"], intake["close_deg"]), (690.0, 110.0, 250.0))
        self.assertEqual((exhaust["open_deg"], exhaust["center_deg"], exhaust["close_deg"]), (470.0, 610.0, 30.0))
        self.assertAlmostEqual(intake["valve_diameter_mm_each"], 32.4)
        self.assertAlmostEqual(exhaust["valve_diameter_mm_each"], 27.0)
        self.assertAlmostEqual(intake["maximum_lift_mm_each"], 10.368)
        self.assertAlmostEqual(exhaust["maximum_lift_mm_each"], 8.64)
        self.assertAlmostEqual(intake["total_geometric_port_area_m2"], 0.00121957)
        self.assertAlmostEqual(exhaust["total_geometric_port_area_m2"], 0.00084692)
        self.assertAlmostEqual(intake["discharge_coefficient"], 0.72)
        self.assertAlmostEqual(exhaust["discharge_coefficient"], 0.68)

    def test_candidate_phases_cover_720_without_claiming_absolute_zero(self) -> None:
        by_number = self.runner.validate_phase_policy(self.contract)
        self.assertEqual(self.contract["phase_policy"]["firing_order_candidate"], [1, 9, 5, 12, 3, 8, 6, 10, 2, 7, 4, 11])
        self.assertEqual(sorted(by_number.values()), [float(value) for value in range(0, 720, 60)])
        self.assertEqual(by_number[1], 0.0)
        self.assertEqual(by_number[9], 60.0)
        self.assertIs(self.contract["phase_policy"]["absolute_zero_validated"], False)

    def test_event_phase_is_converted_to_negative_aeolus_offset(self) -> None:
        topology = self.runner.build_topology(self.contract)
        by_number = {item["number"]: item for item in topology["cylinders"]}
        self.assertEqual(by_number[1]["event_phase_deg"], 0.0)
        self.assertEqual(by_number[1]["theta_init_deg"], 0.0)
        self.assertEqual(by_number[9]["event_phase_deg"], 60.0)
        self.assertEqual(by_number[9]["theta_init_deg"], 660.0)
        for cylinder in topology["cylinders"]:
            self.assertEqual(cylinder["theta_init_deg"], (-cylinder["event_phase_deg"]) % 720.0)

    def test_topology_rejects_positive_event_phase_used_as_theta_offset(self) -> None:
        topology = self.runner.build_topology(self.contract)
        cylinder = next(item for item in topology["cylinders"] if item["number"] == 9)
        cylinder["theta_init_deg"] = cylinder["event_phase_deg"]
        with self.assertRaisesRegex(self.runner.F39InputError, "negative modulo 720"):
            self.runner.validate_topology(topology, self.contract)

    @unittest.skipUnless(importlib.util.find_spec("aeolus1d") is not None, "Aeolus1D 0.3.3 not installed in this interpreter")
    def test_aeolus_global_crank_inheritance_is_effectively_nonzero(self) -> None:
        topology = self.runner.build_topology(self.contract)
        case = self.runner.build_aeolus_case(self.contract, topology)
        summary = self.runner.case_summary(case)
        self.assertEqual(summary["legacy_zero_omega_inheritance_sentinel_count"], 12)
        effective = self.runner.validate_effective_crank(case)
        self.assertEqual(effective["runtime_cylinder_count"], 12)
        self.assertTrue(effective["global_crank_inheritance_verified"])
        self.assertGreater(effective["minimum_runtime_omega_rad_s"], 0.0)

    def test_motored_and_release_gates_fail_closed(self) -> None:
        authority = self.contract["authority_boundary"]
        self.assertIs(authority["motored_only"], True)
        self.assertIs(authority["combustion_enabled"], False)
        self.assertIs(authority["fuel_injection_enabled"], False)
        self.assertIs(authority["requested_power_target_used_as_solver_input"], False)
        self.assertTrue(self.contract["release_gates"])
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))
        topology = self.runner.build_topology(self.contract)
        self.assertTrue(all(item["combustion"] is None for item in topology["cylinders"]))
        self.assertTrue(all(item["fuel_mass_per_cycle_kg"] == 0.0 for item in topology["cylinders"]))

    def test_structured_manifest_does_not_promote_execution(self) -> None:
        report = self.runner.build_report(self.contract, ROOT, validate_aeolus=False, execute=False)
        self.assertEqual(report["phase"], "F39")
        self.assertEqual(report["status"], "motored_unsteady_720_manifest")
        self.assertIs(report["execution"]["executed"], False)
        self.assertIs(report["technical_checks"]["topology_27_pipes_15_junctions_valid"], True)
        self.assertIs(report["technical_checks"]["aeolus_case_constructed"], False)
        self.assertIs(report["technical_checks"]["time_march_completed"], False)
        self.assertIs(report["technical_checks"]["cycle_convergence_evaluated"], False)
        self.assertTrue(all(value is False for value in report["release_gates"].values()))

    def test_duplicate_pipe_and_duplicate_phase_are_rejected(self) -> None:
        topology = self.runner.build_topology(self.contract)
        topology["pipes"][1]["id"] = topology["pipes"][0]["id"]
        with self.assertRaisesRegex(self.runner.F39InputError, "duplicate pipe id"):
            self.runner.validate_topology(topology, self.contract)
        bad_contract = copy.deepcopy(self.contract)
        bad_contract["phase_policy"]["firing_order_candidate"][-1] = 1
        with self.assertRaisesRegex(self.runner.F39InputError, "cylinders 1..12"):
            self.runner.validate_phase_policy(bad_contract)

    def test_power_or_manufacturing_gate_cannot_be_promoted(self) -> None:
        bad_contract = copy.deepcopy(self.contract)
        bad_contract["release_gates"]["target_power_proven"] = True
        with self.assertRaisesRegex(self.runner.F39InputError, "all contract release gates must be false"):
            self.runner.validate_contract(bad_contract)


if __name__ == "__main__":
    unittest.main()
