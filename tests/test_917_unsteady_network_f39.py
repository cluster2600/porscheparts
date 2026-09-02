from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace


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


class FakePipe:
    def __init__(
        self,
        *,
        density: tuple[float, ...] = (1.0, 1.1),
        velocity: tuple[float, ...] = (-2.0, 3.0),
        pressure: tuple[float, ...] = (100000.0, 101000.0),
    ) -> None:
        self.N = len(density)
        self.R_gas = 287.05
        self._primitives = density, velocity, pressure

    def primitives(self):
        return self._primitives


class FakeComponent:
    def __init__(self, component_id: str, *, mass_kg: float = 0.001) -> None:
        self.id = component_id
        self.volume = SimpleNamespace(
            p=100000.0,
            T=303.0,
            V=0.001,
            m=mass_kg,
            E_internal=100.0,
        )
        if component_id.startswith("c"):
            self.last_theta_deg = 0.0
            self.last_xb = 0.0
            self.combustion = None
            self.m_fuel_per_cycle = 0.0


def valid_fake_runtime(runner):
    pipes = {f"pipe_{index:02d}": FakePipe() for index in range(27)}
    components = [FakeComponent(component_id) for component_id in sorted(runner.expected_runtime_component_ids())]
    return pipes, components


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

    def test_motored_and_physical_release_gates_fail_closed(self) -> None:
        authority = self.contract["authority_boundary"]
        self.assertIs(authority["motored_only"], True)
        self.assertIs(authority["combustion_enabled"], False)
        self.assertIs(authority["fuel_injection_enabled"], False)
        self.assertIs(authority["requested_power_target_used_as_solver_input"], False)
        self.assertTrue(self.contract["physical_release_gates"])
        self.assertTrue(all(value is False for value in self.contract["physical_release_gates"].values()))
        self.assertTrue(self.contract["numerical_gates"])
        self.assertTrue(all(value is False for value in self.contract["numerical_gates"].values()))
        topology = self.runner.build_topology(self.contract)
        self.assertTrue(all(item["combustion"] is None for item in topology["cylinders"]))
        self.assertTrue(all(item["fuel_mass_per_cycle_kg"] == 0.0 for item in topology["cylinders"]))

    def test_structured_manifest_does_not_promote_execution(self) -> None:
        report = self.runner.build_report(self.contract, ROOT, validate_aeolus=False, execute=False)
        self.assertEqual(report["phase"], "F39")
        self.assertEqual(report["status"], "motored_unsteady_720_manifest")
        self.assertIs(report["execution"]["executed"], False)
        self.assertIs(report["numerical_gates"]["source_hashes_verified"], True)
        self.assertIs(report["numerical_gates"]["topology_contract_valid"], True)
        self.assertIs(report["numerical_gates"]["aeolus_case_constructed"], False)
        self.assertIs(report["numerical_gates"]["full_720_time_march_executed"], False)
        self.assertIs(report["numerical_gates"]["runtime_fields_finite"], False)
        self.assertIs(report["numerical_gates"]["runtime_state_positive"], False)
        self.assertTrue(all(value is False for value in report["physical_release_gates"].values()))
        self.assertEqual(report["execution"]["component_diagnostics"], {})
        self.assertIsNone(report["execution"]["state_minima"]["component_mass_kg"])

    def test_duplicate_pipe_and_duplicate_phase_are_rejected(self) -> None:
        topology = self.runner.build_topology(self.contract)
        topology["pipes"][1]["id"] = topology["pipes"][0]["id"]
        with self.assertRaisesRegex(self.runner.F39InputError, "duplicate pipe id"):
            self.runner.validate_topology(topology, self.contract)
        bad_contract = copy.deepcopy(self.contract)
        bad_contract["phase_policy"]["firing_order_candidate"][-1] = 1
        with self.assertRaisesRegex(self.runner.F39InputError, "cylinders 1..12"):
            self.runner.validate_phase_policy(bad_contract)

    def test_physical_power_or_manufacturing_gate_cannot_be_promoted(self) -> None:
        bad_contract = copy.deepcopy(self.contract)
        bad_contract["physical_release_gates"]["target_power_proven"] = True
        with self.assertRaisesRegex(self.runner.F39InputError, "physical release gates must remain false"):
            self.runner.validate_contract(bad_contract)

    def test_contract_cannot_predeclare_a_numerical_result(self) -> None:
        bad_contract = copy.deepcopy(self.contract)
        bad_contract["numerical_gates"]["full_720_time_march_executed"] = True
        with self.assertRaisesRegex(self.runner.F39InputError, "numerical gates must start false"):
            self.runner.validate_contract(bad_contract)

    def test_all_27_pipes_and_15_components_have_positive_finite_diagnostics(self) -> None:
        pipes, components = valid_fake_runtime(self.runner)
        diagnostics = self.runner.collect_runtime_diagnostics(pipes, components)
        self.assertIs(diagnostics["finite_fields"], True)
        self.assertIs(diagnostics["positive_state"], True)
        self.assertIs(diagnostics["exact_runtime_coverage"], True)
        self.assertEqual(diagnostics["pipe_diagnostic_count"], 27)
        self.assertEqual(diagnostics["component_diagnostic_count"], 15)
        self.assertEqual(len(diagnostics["component_diagnostics"]), 15)
        self.assertEqual(
            sum(item["kind"] == "cylinder" for item in diagnostics["component_diagnostics"].values()),
            12,
        )
        self.assertEqual(
            sum(item["kind"] == "plenum" for item in diagnostics["component_diagnostics"].values()),
            3,
        )
        self.assertGreater(diagnostics["state_minima"]["pipe_density_kg_m3"], 0.0)
        self.assertGreater(diagnostics["state_minima"]["component_mass_kg"], 0.0)

    def test_negative_plenum_mass_falsifies_positive_state(self) -> None:
        pipes, components = valid_fake_runtime(self.runner)
        plenum = next(item for item in components if item.id == "intake_plenum")
        plenum.volume.m = -1.0e-6
        diagnostics = self.runner.collect_runtime_diagnostics(pipes, components)
        self.assertIs(diagnostics["finite_fields"], True)
        self.assertIs(diagnostics["positive_state"], False)
        self.assertIs(diagnostics["component_diagnostics"]["intake_plenum"]["state_positive"], False)
        self.assertEqual(diagnostics["state_minima"]["component_mass_kg"], -1.0e-6)

    def test_negative_pipe_pressure_falsifies_positive_state(self) -> None:
        pipes, components = valid_fake_runtime(self.runner)
        pipes["pipe_00"] = FakePipe(pressure=(-1.0, 101000.0))
        diagnostics = self.runner.collect_runtime_diagnostics(pipes, components)
        self.assertIs(diagnostics["finite_fields"], True)
        self.assertIs(diagnostics["positive_state"], False)
        self.assertIs(diagnostics["pipe_diagnostics"]["pipe_00"]["state_positive"], False)
        self.assertEqual(diagnostics["state_minima"]["pipe_pressure_pa_abs"], -1.0)

    def test_nonfinite_pipe_and_missing_component_fail_closed(self) -> None:
        pipes, components = valid_fake_runtime(self.runner)
        pipes["pipe_00"] = FakePipe(pressure=(float("nan"), 101000.0))
        components.pop()
        diagnostics = self.runner.collect_runtime_diagnostics(pipes, components)
        self.assertIs(diagnostics["finite_fields"], False)
        self.assertIs(diagnostics["positive_state"], False)
        self.assertIs(diagnostics["exact_runtime_coverage"], False)
        self.assertEqual(diagnostics["component_diagnostic_count"], 14)
        self.assertIsNone(diagnostics["pipe_diagnostics"]["pipe_00"]["pressure_pa_abs_min"])
        self.assertIsNone(diagnostics["state_minima"]["pipe_pressure_pa_abs"])
        json.dumps(diagnostics, allow_nan=False)

    def test_numerical_gates_reflect_completed_finite_positive_execution_only(self) -> None:
        execution = {
            "executed": True,
            "requested_720_window_completed": True,
            "finite_fields": True,
            "positive_state": True,
        }
        gates = self.runner.derive_numerical_gates(
            source_hashes_verified=True,
            topology_contract_valid=True,
            aeolus_case_constructed=True,
            execution=execution,
        )
        self.assertTrue(all(gates.values()))
        execution["positive_state"] = False
        gates = self.runner.derive_numerical_gates(
            source_hashes_verified=True,
            topology_contract_valid=True,
            aeolus_case_constructed=True,
            execution=execution,
        )
        self.assertIs(gates["full_720_time_march_executed"], True)
        self.assertIs(gates["runtime_fields_finite"], True)
        self.assertIs(gates["runtime_state_positive"], False)


if __name__ == "__main__":
    unittest.main()
