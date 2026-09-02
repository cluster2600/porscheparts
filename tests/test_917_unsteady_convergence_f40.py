from __future__ import annotations

import copy
import importlib.util
import json
import math
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins/reference-917-engine"
CONTRACT = TWIN / "unsteady-convergence-campaign-f40.json"
RUNNER = TWIN / "source/run_unsteady_convergence_f40.py"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_runner():
    spec = importlib.util.spec_from_file_location("run_unsteady_convergence_f40", RUNNER)
    assert spec is not None and spec.loader is not None
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


def fake_boundaries(values: list[float]) -> list[dict]:
    return [
        {
            "cycle_index": index,
            "cycle_window_completed": True,
            "finite_fields": True,
            "positive_state": True,
            "metrics": metric_values(value),
        }
        for index, value in enumerate(values, start=1)
    ]


def completed_case(case_id: str, value: float, runner, contract: dict) -> dict:
    boundaries = fake_boundaries([value, value, value, value])
    return {
        "case_id": case_id,
        "status": "completed",
        "four_cycles_completed": True,
        "all_runtime_fields_finite": True,
        "all_runtime_states_positive": True,
        "cycle_boundaries": boundaries,
        "cycle_convergence": runner.evaluate_cycle_convergence(
            boundaries, contract["convergence_policy"]
        ),
    }


class UnsteadyConvergenceF40Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = load_runner()
        cls.contract = load(CONTRACT)

    def test_contract_hash_binds_exact_f39_and_immutable_image(self) -> None:
        self.runner.validate_contract(self.contract)
        bindings = self.runner.verify_source_bindings(ROOT, self.contract)
        self.assertEqual(
            bindings["f39_contract"]["actual_sha256"],
            "c62d1dffcd57a13dce569eb1af05e61c84b893b27613f77c01b0878831743432",
        )
        self.assertEqual(
            bindings["f39_runner"]["actual_sha256"],
            "4a2f7b905cd512a77b5c9719f79423c5c3eff1b606bd9390b7de47539188d174",
        )
        self.assertEqual(
            self.contract["runtime_image"]["digest"],
            "sha256:742569a45becdd00b9f8d32b057156e68d0bb0489cef1fa97d2e6543fce096a3",
        )
        self.assertEqual(
            self.contract["repository_snapshot"]["commit"],
            "ddc7703d4ad949b2712bdf178a28dbaaf0ae3cda",
        )
        self.assertIs(self.contract["repository_snapshot"]["enforce_current_head"], False)

    def test_hash_binding_tamper_is_rejected(self) -> None:
        bad = copy.deepcopy(self.contract)
        bad["source_bindings"]["f39_runner"]["expected_sha256"] = "0" * 64
        with self.assertRaisesRegex(self.runner.F40InputError, "hash binding mismatch"):
            self.runner.validate_contract(bad)

    def test_six_case_matrix_is_exact_and_deduplicated(self) -> None:
        cases = self.runner.validate_matrix(self.contract)
        self.assertEqual(len(cases), 6)
        self.assertEqual([item["case_id"] for item in cases], sorted(self.runner.EXPECTED_CASES))
        self.assertEqual(
            {(item["mesh_scale"], item["cfl"], item["initial_pressure_factor"]) for item in cases},
            set(self.runner.EXPECTED_CASES.values()),
        )

    def test_duplicate_case_signature_is_rejected(self) -> None:
        bad = copy.deepcopy(self.contract)
        bad["campaign"]["cases"][-1]["mesh_scale"] = 0.5
        bad["campaign"]["cases"][-1]["cfl"] = 0.2
        bad["campaign"]["cases"][-1]["initial_pressure_factor"] = 1.0
        with self.assertRaisesRegex(self.runner.F40InputError, "duplicate numerical case"):
            self.runner.validate_matrix(bad)

    def test_contract_gates_cannot_predeclare_results(self) -> None:
        for gate_family, gate_name in (
            ("numerical_gates", "cyclic_convergence_all_cases_demonstrated"),
            ("physical_release_gates", "power_or_torque_prediction_authorized"),
        ):
            bad = copy.deepcopy(self.contract)
            bad[gate_family][gate_name] = True
            with self.assertRaises(self.runner.F40InputError):
                self.runner.validate_contract(bad)

    def test_manifest_executes_nothing_and_only_promotes_documentary_gates(self) -> None:
        report = self.runner.build_report(
            self.contract, ROOT, execute=False, workers=None
        )
        self.assertEqual(report["mode"], "manifest")
        self.assertEqual(report["campaign"]["case_reports"], [])
        self.assertEqual(len(report["campaign"]["case_matrix"]), 6)
        self.assertIs(report["numerical_gates"]["source_hashes_verified"], True)
        self.assertIs(report["numerical_gates"]["matrix_validated"], True)
        for gate, value in report["numerical_gates"].items():
            if gate not in {"source_hashes_verified", "matrix_validated"}:
                self.assertIs(value, False, gate)
        self.assertTrue(all(value is False for value in report["physical_release_gates"].values()))
        serialized = json.dumps(report, sort_keys=True, allow_nan=False)
        self.assertNotIn("timestamp", serialized.lower())
        self.assertNotIn("wall_clock", serialized.lower())

    def test_manifest_rejects_workers(self) -> None:
        with self.assertRaisesRegex(self.runner.F40InputError, "only valid"):
            self.runner.build_report(self.contract, ROOT, execute=False, workers=1)

    def test_execute_requires_explicit_workers_before_dispatch(self) -> None:
        with self.assertRaisesRegex(self.runner.F40InputError, "explicit --workers"):
            self.runner.build_report(self.contract, ROOT, execute=True, workers=None)

    def test_mesh_rounding_is_deterministic_half_up(self) -> None:
        self.assertEqual(self.runner.half_up_scaled_cells(9, 0.5, 4), 5)
        self.assertEqual(self.runner.half_up_scaled_cells(4, 0.5, 4), 4)
        self.assertEqual(self.runner.half_up_scaled_cells(18, 2.0, 4), 36)

    def test_initial_factor_scales_internal_specs_but_not_boundaries(self) -> None:
        def items(count, pressure):
            return [SimpleNamespace(init=SimpleNamespace(p=pressure)) for _ in range(count)]

        bcs = [SimpleNamespace(p0=100000.0), SimpleNamespace(p_back=108000.0)]
        case = SimpleNamespace(
            pipes=items(27, 100000.0),
            junctions=items(3, 100000.0),
            cylinders=items(12, 100000.0),
            bcs=bcs,
        )
        counts = self.runner.apply_initial_pressure_factor(case, 0.95)
        self.assertEqual(counts, {"pipe_specs": 27, "junction_specs": 3, "cylinder_specs": 12})
        self.assertTrue(all(item.init.p == 95000.0 for item in case.pipes + case.junctions + case.cylinders))
        self.assertEqual(bcs[0].p0, 100000.0)
        self.assertEqual(bcs[1].p_back, 108000.0)

    def test_four_cycles_reuse_one_network_and_cumulative_t_start(self) -> None:
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

        def dispatch(_case, pipes, components, _bcs, **kwargs):
            calls.append(
                (
                    kwargs["t_start"],
                    _case.case.t_end,
                    id(pipes),
                    id(components),
                )
            )
            return _case.case.t_end

        def boundary(_pipes, _components):
            return {
                "finite_fields": True,
                "positive_state": True,
                "metrics": metric_values(1.0),
            }

        result = self.runner.advance_four_cycles(
            case=case,
            network=network,
            clock=SimpleNamespace(t=0.0),
            dispatch_fn=dispatch,
            boundary_builder=boundary,
            cycle_duration_s=1.0,
            cycles=4,
            maximum_steps_per_cycle=100,
            completion_relative_tolerance=1e-9,
        )
        self.assertEqual([item[0] for item in calls], [0.0, 1.0, 2.0, 3.0])
        self.assertEqual([item[1] for item in calls], [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(len({item[2] for item in calls}), 1)
        self.assertEqual(len({item[3] for item in calls}), 1)
        self.assertEqual(len(result), 4)
        self.assertTrue(all(item["cycle_window_completed"] for item in result))
        self.assertEqual([item["crank_degrees_target"] for item in result], [720.0, 1440.0, 2160.0, 2880.0])

    def test_cycle_convergence_requires_exactly_three_deltas(self) -> None:
        stable = fake_boundaries([1.0, 1.0001, 1.00015, 1.00016])
        result = self.runner.evaluate_cycle_convergence(
            stable, self.contract["convergence_policy"]
        )
        self.assertIs(result["evaluated"], True)
        self.assertEqual(result["observed_consecutive_deltas"], 3)
        self.assertIs(result["passed"], True)
        short = self.runner.evaluate_cycle_convergence(
            stable[:3], self.contract["convergence_policy"]
        )
        self.assertIs(short["evaluated"], False)
        self.assertIs(short["passed"], False)

    def test_unstable_cycles_are_reported_but_do_not_pass(self) -> None:
        result = self.runner.evaluate_cycle_convergence(
            fake_boundaries([1.0, 1.1, 1.2, 1.3]),
            self.contract["convergence_policy"],
        )
        self.assertIs(result["evaluated"], True)
        self.assertEqual(len(result["relative_deltas"]), 3)
        self.assertIs(result["passed"], False)

    def test_sensitivity_uses_cycle_four_and_typed_tolerances(self) -> None:
        reports = [
            completed_case(case_id, 1.0, self.runner, self.contract)
            for case_id in sorted(self.runner.EXPECTED_CASES)
        ]
        by_id = {item["case_id"]: item for item in reports}
        by_id["mesh_0p5_cfl_0p2_init_1p00"]["cycle_boundaries"][-1]["metrics"] = metric_values(1.03)
        sensitivity = self.runner.evaluate_sensitivity(reports, self.contract)
        self.assertIs(sensitivity["mesh"]["evaluated"], True)
        self.assertIs(sensitivity["mesh"]["within_tolerance"], False)
        self.assertIs(sensitivity["temporal"]["within_tolerance"], True)
        self.assertIs(sensitivity["initial_state"]["within_tolerance"], True)

    def test_missing_case_falsifies_sensitivity_and_campaign_gates(self) -> None:
        reports = [
            completed_case(case_id, 1.0, self.runner, self.contract)
            for case_id in sorted(self.runner.EXPECTED_CASES)[:-1]
        ]
        sensitivity = self.runner.evaluate_sensitivity(reports, self.contract)
        gates = self.runner.derive_numerical_gates(
            source_hashes_verified=True,
            matrix_validated=True,
            case_reports=reports,
            sensitivity=sensitivity,
        )
        self.assertIs(gates["all_cases_executed_four_cycles"], False)
        self.assertIs(gates["cyclic_convergence_all_cases_demonstrated"], False)
        self.assertIs(sensitivity["temporal"]["evaluated"], False)
        self.assertIs(gates["temporal_sensitivity_within_tolerance"], False)

    def test_duplicate_case_report_cannot_satisfy_execution_gate(self) -> None:
        reports = [
            completed_case(case_id, 1.0, self.runner, self.contract)
            for case_id in sorted(self.runner.EXPECTED_CASES)
        ]
        reports[-1] = copy.deepcopy(reports[0])
        sensitivity = self.runner.evaluate_sensitivity(reports, self.contract)
        gates = self.runner.derive_numerical_gates(
            source_hashes_verified=True,
            matrix_validated=True,
            case_reports=reports,
            sensitivity=sensitivity,
        )
        self.assertIs(gates["all_cases_executed_four_cycles"], False)

    def test_positive_fake_campaign_can_promote_only_numerical_gates(self) -> None:
        reports = [
            completed_case(case_id, 1.0, self.runner, self.contract)
            for case_id in sorted(self.runner.EXPECTED_CASES)
        ]
        sensitivity = self.runner.evaluate_sensitivity(reports, self.contract)
        gates = self.runner.derive_numerical_gates(
            source_hashes_verified=True,
            matrix_validated=True,
            case_reports=reports,
            sensitivity=sensitivity,
        )
        self.assertTrue(all(gates.values()))
        self.assertTrue(all(value is False for value in self.contract["physical_release_gates"].values()))

    @unittest.skipUnless(
        importlib.util.find_spec("aeolus1d") is not None,
        "Aeolus1D 0.3.3 not installed in this interpreter",
    )
    def test_image_builds_each_case_with_expected_runtime_topology(self) -> None:
        from aeolus1d.bc.transient import Clock
        from aeolus1d.io.build import build_network

        for case_spec in self.runner.validate_matrix(self.contract):
            case, _f39, summary = self.runner.build_case_for_campaign(
                ROOT, case_spec, self.contract
            )
            network = build_network(case, clock=Clock())
            crank = self.runner.validate_runtime_crank_on_network(case, network)
            state = self.runner.collect_boundary_state(_f39, network.pipes, network.junctions)
            self.assertEqual(len(network.pipes), 27)
            self.assertEqual(len(network.junctions), 15)
            self.assertEqual(summary["initial_pressure_scaling_counts"], {
                "pipe_specs": 27,
                "junction_specs": 3,
                "cylinder_specs": 12,
            })
            self.assertIs(crank["global_crank_inheritance_verified"], True)
            self.assertIs(state["finite_fields"], True)
            self.assertIs(state["positive_state"], True)
            self.assertGreater(state["metrics"]["total_gas_mass_kg"], 0.0)


if __name__ == "__main__":
    unittest.main()
