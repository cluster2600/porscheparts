#!/usr/bin/env python3
"""Tests fail-closed de la recherche de periodicite F40b."""

from __future__ import annotations

import copy
import importlib.util
import json
import math
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "twins/reference-917-engine/source/run_extended_periodic_state_f40b.py"
CONTRACT = ROOT / "twins/reference-917-engine/extended-periodic-state-f40b.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_runner():
    spec = importlib.util.spec_from_file_location("test_f40b_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load F40b runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metric_values(value: float) -> dict[str, float]:
    return {
        "total_pipe_mass_kg": value,
        "total_component_mass_kg": value,
        "total_gas_mass_kg": value,
        "pipe_pressure_volume_mean_pa_abs": value,
        "pipe_temperature_mass_mean_k": value,
        "component_pressure_volume_mean_pa_abs": value,
        "component_temperature_mass_mean_k": value,
    }


def boundary(index: int, value: float) -> dict:
    return {
        "cycle_index": index,
        "cycle_window_completed": True,
        "finite_fields": True,
        "positive_state": True,
        "exact_runtime_coverage": True,
        "metrics": metric_values(value),
    }


def boundaries(values: list[float]) -> list[dict]:
    return [boundary(index, value) for index, value in enumerate(values, start=1)]


def fake_runtime(values: list[float]):
    case = SimpleNamespace(
        case=SimpleNamespace(t_end=0.0),
        crankshaft=SimpleNamespace(rpm=120.0),
    )
    network = SimpleNamespace(
        pipes={"same": object()},
        junctions=[object()],
        bcs=[object()],
        coolant_couplings=[],
        wall_thermal_pairs=[],
    )
    calls: list[tuple[float, float, int, int]] = []
    cursor = {"value": 0}

    def dispatch(_case, pipes, components, _bcs, **kwargs):
        calls.append((kwargs["t_start"], _case.case.t_end, id(pipes), id(components)))
        return _case.case.t_end

    def build_boundary(_pipes, _components):
        value = values[cursor["value"]]
        cursor["value"] += 1
        return {
            "finite_fields": True,
            "positive_state": True,
            "exact_runtime_coverage": True,
            "metrics": metric_values(value),
        }

    return case, network, calls, dispatch, build_boundary


def execution_from_values(runner, contract: dict, values: list[float]) -> dict:
    observed = boundaries(values)
    convergence = runner.evaluate_periodicity(
        observed,
        contract["convergence_policy"],
        minimum_cycles=contract["campaign"]["minimum_cycles"],
    )
    periodic = convergence["passed"]
    maximum = contract["campaign"]["maximum_cycles"]
    return {
        "case_id": runner.NOMINAL_CASE["case_id"],
        "status": "periodic_state_demonstrated" if periodic else "cycle_budget_exhausted_without_periodicity",
        "runtime_network_build_count": 1,
        "cycles_attempted": len(observed),
        "cycles_completed": len(observed),
        "cycle_boundaries": observed,
        "all_cycle_windows_completed": True,
        "all_runtime_fields_finite": True,
        "all_runtime_states_positive": True,
        "exact_runtime_coverage_all_boundaries": True,
        "cycle_budget_exhausted": len(observed) == maximum and not periodic,
        "stopped_early": periodic and len(observed) < maximum,
        "convergence": convergence,
    }


class ExtendedPeriodicStateF40bTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = load_runner()
        cls.contract = load(CONTRACT)

    def test_contract_binds_exact_f40_sources_and_image(self) -> None:
        self.runner.validate_contract(self.contract)
        bindings = self.runner.verify_source_bindings(ROOT, self.contract)
        self.assertEqual(
            bindings["f40_contract"]["actual_sha256"],
            "6fff578fe167b8563b48271b9234f36c05b9bb1b2003a5ddee594acd6de9178c",
        )
        self.assertEqual(
            bindings["f40_runner"]["actual_sha256"],
            "fa2e529389c6a493789fb4528e973e7c987100f941f83ab744ea45822ff925d3",
        )
        self.assertEqual(
            self.contract["runtime_image"]["digest"],
            "sha256:742569a45becdd00b9f8d32b057156e68d0bb0489cef1fa97d2e6543fce096a3",
        )

    def test_upstream_f40_chain_and_nominal_case_are_validated(self) -> None:
        f40, upstream = self.runner.validate_upstream_f40(ROOT, self.contract)
        cases = {item["case_id"]: item for item in f40.validate_matrix(upstream)}
        self.assertEqual(cases[self.runner.NOMINAL_CASE["case_id"]], self.runner.NOMINAL_CASE)
        self.assertEqual(self.runner.NOMINAL_CASE["case_id"], "mesh_2p0_cfl_0p2_init_1p00")

    def test_hash_binding_tamper_is_rejected(self) -> None:
        bad = copy.deepcopy(self.contract)
        bad["source_bindings"]["f40_runner"]["expected_sha256"] = "0" * 64
        with self.assertRaisesRegex(self.runner.F40bInputError, "hash binding mismatch"):
            self.runner.validate_contract(bad)

    def test_cycle_budget_and_tolerance_are_immutable(self) -> None:
        mutations = (
            ("campaign", "minimum_cycles", 3),
            ("campaign", "maximum_cycles", 25),
            ("convergence_policy", "required_consecutive_deltas", 2),
            ("convergence_policy", "cyclic_max_relative_delta", 0.01),
        )
        for section, field, value in mutations:
            bad = copy.deepcopy(self.contract)
            bad[section][field] = value
            with self.subTest(field=field), self.assertRaises(self.runner.F40bInputError):
                self.runner.validate_contract(bad)

    def test_physical_and_phase_resolved_gates_start_false(self) -> None:
        self.assertTrue(all(value is False for value in self.contract["physical_release_gates"].values()))
        self.assertEqual(self.contract["phase_resolved_sampling"]["status"], "not_implemented_fail_closed")
        for key in ("sampling_evaluated", "l2_norm_evaluated", "linf_norm_evaluated"):
            self.assertIs(self.contract["phase_resolved_sampling"][key], False)
        bad = copy.deepcopy(self.contract)
        bad["physical_release_gates"]["target_power_proven"] = True
        with self.assertRaises(self.runner.F40bInputError):
            self.runner.validate_contract(bad)

    def test_manifest_executes_nothing_and_promotes_only_documentary_gates(self) -> None:
        report = self.runner.build_report(self.contract, ROOT, execute=False)
        self.assertEqual(report["mode"], "manifest")
        self.assertIsNone(report["campaign"]["execution"])
        self.assertIs(report["numerical_gates"]["source_hashes_verified"], True)
        self.assertIs(report["numerical_gates"]["nominal_case_validated"], True)
        for name, value in report["numerical_gates"].items():
            if name not in {"source_hashes_verified", "nominal_case_validated"}:
                self.assertIs(value, False, name)
        self.assertTrue(all(value is False for value in report["physical_release_gates"].values()))
        serialized = json.dumps(report, sort_keys=True, allow_nan=False)
        self.assertNotIn("timestamp", serialized.lower())
        self.assertNotIn('"wall_clock_s"', serialized.lower())
        self.assertNotIn('"elapsed_s"', serialized.lower())

    def test_stable_runtime_stops_at_first_permitted_cycle(self) -> None:
        values = [1.0, 1.0001, 1.00015, 1.00016] + [2.0] * 20
        case, network, calls, dispatch, build_boundary = fake_runtime(values)
        observed, convergence = self.runner.advance_until_periodic(
            case=case,
            network=network,
            clock=SimpleNamespace(t=0.0),
            dispatch_fn=dispatch,
            boundary_builder=build_boundary,
            cycle_duration_s=1.0,
            minimum_cycles=4,
            maximum_cycles=24,
            maximum_steps_per_cycle=100,
            completion_relative_tolerance=1.0e-9,
            convergence_policy=self.contract["convergence_policy"],
        )
        self.assertEqual(len(observed), 4)
        self.assertEqual(len(calls), 4)
        self.assertEqual(convergence["first_satisfied_at_cycle"], 4)
        self.assertIs(convergence["passed"], True)
        self.assertEqual([item[0] for item in calls], [0.0, 1.0, 2.0, 3.0])
        self.assertEqual([item[1] for item in calls], [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(len({item[2] for item in calls}), 1)
        self.assertEqual(len({item[3] for item in calls}), 1)

    def test_convergence_window_can_be_reached_after_cycle_four(self) -> None:
        values = [1.0, 1.1, 1.2, 1.2005, 1.2008, 1.2009] + [2.0] * 18
        case, network, calls, dispatch, build_boundary = fake_runtime(values)
        observed, convergence = self.runner.advance_until_periodic(
            case=case,
            network=network,
            clock=SimpleNamespace(t=0.0),
            dispatch_fn=dispatch,
            boundary_builder=build_boundary,
            cycle_duration_s=1.0,
            minimum_cycles=4,
            maximum_cycles=24,
            maximum_steps_per_cycle=100,
            completion_relative_tolerance=1.0e-9,
            convergence_policy=self.contract["convergence_policy"],
        )
        self.assertEqual(len(observed), 6)
        self.assertEqual(len(calls), 6)
        self.assertEqual(convergence["first_satisfied_at_cycle"], 6)
        self.assertEqual([item["to_cycle"] for item in convergence["satisfied_window"]], [4, 5, 6])

    def test_unstable_runtime_records_all_24_boundaries(self) -> None:
        values = [1.0 + 0.01 * index for index in range(24)]
        case, network, calls, dispatch, build_boundary = fake_runtime(values)
        observed, convergence = self.runner.advance_until_periodic(
            case=case,
            network=network,
            clock=SimpleNamespace(t=0.0),
            dispatch_fn=dispatch,
            boundary_builder=build_boundary,
            cycle_duration_s=1.0,
            minimum_cycles=4,
            maximum_cycles=24,
            maximum_steps_per_cycle=100,
            completion_relative_tolerance=1.0e-9,
            convergence_policy=self.contract["convergence_policy"],
        )
        self.assertEqual(len(observed), 24)
        self.assertEqual(len(calls), 24)
        self.assertEqual(len(convergence["relative_deltas"]), 23)
        self.assertIs(convergence["passed"], False)

    def test_all_metrics_must_pass_each_of_three_deltas(self) -> None:
        observed = boundaries([1.0, 1.0001, 1.00015, 1.00016])
        observed[3]["metrics"]["total_gas_mass_kg"] = 1.01
        convergence = self.runner.evaluate_periodicity(
            observed,
            self.contract["convergence_policy"],
            minimum_cycles=4,
        )
        self.assertIs(convergence["evaluated"], True)
        self.assertIs(convergence["passed"], False)
        self.assertGreater(
            convergence["relative_deltas"][-1]["metric_relative_deltas"]["total_gas_mass_kg"],
            0.001,
        )

    def test_nonfinite_boundary_never_passes(self) -> None:
        observed = boundaries([1.0, 1.0, 1.0, 1.0])
        observed[-1]["metrics"]["total_gas_mass_kg"] = math.nan
        convergence = self.runner.evaluate_periodicity(
            observed,
            self.contract["convergence_policy"],
            minimum_cycles=4,
        )
        self.assertIs(convergence["metrics_valid_at_all_boundaries"], False)
        self.assertIs(convergence["evaluated"], False)
        self.assertIs(convergence["passed"], False)

    def test_periodic_execution_promotes_only_aggregate_numerical_gate(self) -> None:
        execution = execution_from_values(self.runner, self.contract, [1.0, 1.0001, 1.00015, 1.00016])
        gates = self.runner.derive_numerical_gates(
            source_hashes_verified=True,
            nominal_case_validated=True,
            execution=execution,
            contract=self.contract,
        )
        self.assertIs(gates["aggregate_periodic_state_demonstrated"], True)
        self.assertIs(gates["early_stop_rule_respected"], True)
        self.assertIs(gates["phase_resolved_convergence_evaluated"], False)

    def test_budget_exhaustion_is_integrity_complete_but_not_periodic(self) -> None:
        values = [1.0 + 0.01 * index for index in range(24)]
        execution = execution_from_values(self.runner, self.contract, values)
        gates = self.runner.derive_numerical_gates(
            source_hashes_verified=True,
            nominal_case_validated=True,
            execution=execution,
            contract=self.contract,
        )
        self.assertIs(gates["minimum_cycles_completed"], True)
        self.assertIs(gates["early_stop_rule_respected"], True)
        self.assertIs(gates["aggregate_periodic_state_demonstrated"], False)

    def test_missing_boundary_index_fails_recording_gate(self) -> None:
        execution = execution_from_values(self.runner, self.contract, [1.0, 1.0001, 1.00015, 1.00016])
        execution["cycle_boundaries"][-1]["cycle_index"] = 5
        gates = self.runner.derive_numerical_gates(
            source_hashes_verified=True,
            nominal_case_validated=True,
            execution=execution,
            contract=self.contract,
        )
        self.assertIs(gates["all_cycle_boundaries_recorded"], False)

    def test_report_preserves_all_physical_gates_false(self) -> None:
        execution = execution_from_values(self.runner, self.contract, [1.0, 1.0001, 1.00015, 1.00016])

        def executor(_root, _contract):
            return execution

        report = self.runner.build_report(self.contract, ROOT, execute=True, executor=executor)
        self.assertEqual(report["status"], "aggregate_periodic_state_demonstrated")
        self.assertTrue(all(value is False for value in report["physical_release_gates"].values()))
        self.assertEqual(report["campaign"]["execution"]["cycles_attempted"], 4)

    def test_make_targets_use_immutable_image_and_absolute_output(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("917-extended-periodic-state-f40b-test:", makefile)
        self.assertIn("917-extended-periodic-state-f40b-image-smoke:", makefile)
        target = makefile.split("917-extended-periodic-state-f40b:", 1)[1].split(
            "917-wave-action-f39-image-test:", 1
        )[0]
        self.assertIn('mkdir -p "$(abspath $(F40B_OUTPUT))"', target)
        self.assertIn('-v "$(abspath $(F40B_OUTPUT)):/output:rw"', target)
        self.assertIn("$(F40B_WAVE_RELEASE_IMAGE)", target)

    @unittest.skipUnless(importlib.util.find_spec("aeolus1d"), "Aeolus1D absent de l'hote")
    def test_aeolus_image_builds_exact_flat_12_nominal_network(self) -> None:
        f40, upstream = self.runner.validate_upstream_f40(ROOT, self.contract)
        case, _f39, summary = f40.build_case_for_campaign(
            ROOT,
            copy.deepcopy(self.runner.NOMINAL_CASE),
            upstream,
        )
        from aeolus1d.bc.transient import Clock
        from aeolus1d.io.build import build_network

        network = build_network(case, clock=Clock())
        crank = f40.validate_runtime_crank_on_network(case, network)
        self.assertEqual(len(case.pipes), 27)
        self.assertEqual(len(case.cylinders), 12)
        self.assertEqual(len(network.junctions), 15)
        self.assertEqual(crank["runtime_cylinder_count"], 12)
        self.assertEqual(summary["case_id"], self.runner.NOMINAL_CASE["case_id"])


if __name__ == "__main__":
    unittest.main()
