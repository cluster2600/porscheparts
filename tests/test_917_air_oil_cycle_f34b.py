"""Adversarial tests for the fail-closed F34b air/oil CPU solver."""

from __future__ import annotations

import copy
import hashlib
import importlib
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_917_air_oil_cycle_f34b.py"
DOE = ROOT / "twins/reference-917-engine/doe-surrogate-f34.json"
ARCHITECTURE = ROOT / "twins/reference-917-engine/air-oil-core-controls-f34a.json"
SEEDS = (
    ROOT / "twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json"
)
MANIFEST = ROOT / "twins/reference-917-engine/evidence/f34/doe-case-manifest.json"


def _load_runner():
    spec = importlib.util.spec_from_file_location("air_oil_cycle_917_f34b", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _canonical_sha256(value: Any) -> str:
    payload = (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _rehash_bundle(bundle: dict[str, Any]) -> None:
    payload = copy.deepcopy(bundle)
    payload.pop("bundle_payload_sha256", None)
    bundle["bundle_payload_sha256"] = _canonical_sha256(payload)


def _numeric_leaves(value: Any):
    if isinstance(value, dict):
        for child in value.values():
            yield from _numeric_leaves(child)
    elif isinstance(value, list):
        for child in value:
            yield from _numeric_leaves(child)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield float(value)


def _fake_cycle(forward: dict[str, Any]) -> dict[str, Any]:
    retained = 3_500_000.0
    friction = 200_000.0
    pumping = 50_000.0
    accessory = float(forward["accessory_power_w"])
    brake = retained - friction - pumping - accessory
    return {
        "geometry": {
            "displacement_m3": 0.005375,
            "mean_piston_speed_m_s": 21.12,
            "cycles_per_second": 75.0,
        },
        "states": {
            "ivc": {"temperature_k": 325.0, "pressure_pa_abs": 250_000.0},
            "compression_end": {
                "temperature_k": 700.0,
                "pressure_pa_abs": 2_500_000.0,
            },
            "equilibrium_end": {
                "temperature_k": 2_500.0,
                "pressure_pa_abs": 8_000_000.0,
            },
            "expansion_end": {
                "temperature_k": 1_200.0,
                "pressure_pa_abs": 400_000.0,
            },
        },
        "charge": {
            "mixture_mass_per_cylinder_kg": 0.001,
            "air_mass_flow_kg_s": 1.0,
            "fuel_mass_flow_kg_s": 0.05,
            "exhaust_mass_flow_kg_s": 1.05,
        },
        "power": {
            "compression_work_per_cylinder_j": 1_000.0,
            "expansion_work_per_cylinder_j": 6_000.0,
            "gross_work_per_cylinder_j": 5_000.0,
            "gross_indicated_power_w": 4_000_000.0,
            "retained_indicated_power_w": retained,
            "friction_power_w": friction,
            "pumping_power_w": pumping,
            "accessory_power_w": accessory,
            "brake_power_w": brake,
            "fuel_power_w": 5_000_000.0,
        },
    }


class _CanteraStub:
    __version__ = "3.2.0"


class AirOilCycle917F34bTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_runner()
        cls.doe = json.loads(DOE.read_text(encoding="utf-8"))
        cls.architecture = json.loads(ARCHITECTURE.read_text(encoding="utf-8"))
        cls.bundle = json.loads(SEEDS.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.seeds = {
            seed["configuration"]: seed for seed in cls.bundle["seeds"]
        }

    def preflight(
        self,
        *,
        doe: dict[str, Any] | None = None,
        architecture: dict[str, Any] | None = None,
        bundle: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.module.build_preflight_report(
            self.doe if doe is None else doe,
            self.architecture if architecture is None else architecture,
            self.bundle if bundle is None else bundle,
        )

    def forward(self, configuration: str) -> dict[str, Any]:
        return copy.deepcopy(self.seeds[configuration]["forward_input"])

    def test_source_has_two_modes_and_no_legacy_runtime_contract_or_solver_import(self):
        source = RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("clean-sheet-cycle-thermal-f33.json", source)
        self.assertNotIn("run_917_cycle_thermal_f33", source)
        self.assertNotIn("from run_917_cycle", source)
        self.assertNotIn("import cantera", source)
        parser = self.module._parser()
        mode_action = next(action for action in parser._actions if action.dest == "mode")
        self.assertEqual(set(mode_action.choices), {"preflight", "synthetic-smoke"})

    def test_json_reader_rejects_duplicate_keys_and_nonfinite_constants(self):
        with tempfile.TemporaryDirectory(prefix="917-f34b-json-") as temporary:
            duplicate = Path(temporary) / "duplicate.json"
            duplicate.write_text('{"phase":"F34b","phase":"F34"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                self.module._read_json(duplicate)
            nonfinite = Path(temporary) / "nonfinite.json"
            nonfinite.write_text('{"value":NaN}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-finite JSON constant"):
                self.module._read_json(nonfinite)

    def test_preflight_is_stdlib_only_deterministic_and_executes_no_case(self):
        with mock.patch.object(
            self.module.importlib,
            "import_module",
            side_effect=AssertionError("runtime dependency import attempted"),
        ):
            first = self.preflight()
            second = self.preflight()
        self.assertEqual(first, second)
        self.assertEqual(first["mode"], "preflight")
        self.assertEqual(first["canonical_doe_cases_executed"], 0)
        self.assertFalse(first["predicted_engine_power"])
        boundary = first["execution_boundary"]
        self.assertTrue(boundary["standard_library_only"])
        self.assertFalse(boundary["cantera_import_attempted"])
        self.assertEqual(boundary["canonical_doe_cases_executed"], 0)
        self.assertEqual(boundary["synthetic_smoke_cases_executed"], 0)
        self.assertEqual(len(first["validated_f34_air_oil_seed_inputs"]), 2)

    def test_seed_bundle_is_self_contained_hash_bound_and_has_no_power_target_input(self):
        indexed = self.module._seeds_by_configuration(self.bundle)
        self.assertEqual(set(indexed), {"naturally_aspirated", "twin_turbo"})
        for configuration, seed in indexed.items():
            self.assertEqual(
                seed["forward_input_sha256"],
                _canonical_sha256(seed["forward_input"]),
            )
            serialized = json.dumps(seed["forward_input"], sort_keys=True).lower()
            self.assertNotIn("requested_power", serialized)
            self.assertNotIn("target_power", serialized)
            self.assertFalse(
                seed["forward_input"]["selected_architecture"]
                ["engine_core_liquid_coolant_present"]
            )
            self.assertEqual(
                seed["forward_input"]["engine_management"]
                ["electronic_wastegate_control_required"],
                configuration == "twin_turbo",
            )

    def test_bundle_hash_or_forward_hash_mutation_fails_closed(self):
        bundle = copy.deepcopy(self.bundle)
        bundle["bundle_payload_sha256"] = "0" * 64
        with self.assertRaisesRegex(self.module.F34bInputError, "payload SHA-256 mismatch"):
            self.preflight(bundle=bundle)

        bundle = copy.deepcopy(self.bundle)
        bundle["seeds"][0]["forward_input_sha256"] = "0" * 64
        _rehash_bundle(bundle)
        with self.assertRaisesRegex(self.module.F34bInputError, "forward input SHA-256 mismatch"):
            self.preflight(bundle=bundle)

    def test_bundle_execution_or_release_gate_mutation_fails_closed(self):
        mutations = (
            ("canonical_doe_cases_executed",),
            ("execution_ledger", "solver_executed"),
            ("release_gates", "training_authorized"),
            ("physical_gates", "target_power_proven"),
        )
        for path in mutations:
            with self.subTest(path=path):
                bundle = copy.deepcopy(self.bundle)
                parent = bundle
                for key in path[:-1]:
                    parent = parent[key]
                parent[path[-1]] = 1 if path == ("canonical_doe_cases_executed",) else True
                _rehash_bundle(bundle)
                with self.assertRaises(self.module.F34bInputError):
                    self.preflight(bundle=bundle)

    def test_every_gate_group_requires_its_exact_key_set(self):
        bundle_groups = (
            ("physical_gates", "target_power_proven"),
            ("release_gates", "training_authorized"),
        )
        for group, removed in bundle_groups:
            for mutation in ("missing", "extra"):
                with self.subTest(owner="bundle", group=group, mutation=mutation):
                    bundle = copy.deepcopy(self.bundle)
                    if mutation == "missing":
                        del bundle[group][removed]
                    else:
                        bundle[group]["unexpected_gate"] = False
                    _rehash_bundle(bundle)
                    with self.assertRaisesRegex(
                        self.module.F34bInputError, "keys mismatch"
                    ):
                        self.preflight(bundle=bundle)

        architecture_groups = (
            ("technical_gates", "core_geometry_defined"),
            ("release_gates", "target_power_proven"),
        )
        for group, removed in architecture_groups:
            for mutation in ("missing", "extra"):
                with self.subTest(
                    owner="architecture", group=group, mutation=mutation
                ):
                    architecture = copy.deepcopy(self.architecture)
                    if mutation == "missing":
                        del architecture[group][removed]
                    else:
                        architecture[group]["unexpected_gate"] = False
                    with self.assertRaisesRegex(
                        self.module.F34bInputError, "keys mismatch"
                    ):
                        self.preflight(architecture=architecture)

        for mutation in ("missing", "extra"):
            with self.subTest(owner="doe", mutation=mutation):
                doe = copy.deepcopy(self.doe)
                if mutation == "missing":
                    del doe["release_gates"]["training_authorized"]
                else:
                    doe["release_gates"]["unexpected_gate"] = False
                with self.assertRaisesRegex(
                    self.module.F34bInputError, "keys mismatch"
                ):
                    self.preflight(doe=doe)

        for mutation in ("missing", "extra"):
            with self.subTest(owner="manifest", mutation=mutation):
                manifest = copy.deepcopy(self.manifest)
                if mutation == "missing":
                    del manifest["release_gates"]["training_authorized"]
                else:
                    manifest["release_gates"]["unexpected_gate"] = False
                with self.assertRaisesRegex(
                    self.module.F34bInputError, "keys mismatch"
                ):
                    self.module._canonical_case_hashes(
                        manifest,
                        doe_contract_sha256=self.module._sha256(DOE),
                    )

    def test_bundle_parent_binding_rejects_embedded_contract_or_manifest_drift(self):
        bundle = copy.deepcopy(self.bundle)
        bundle["parents"][0]["sha256"] = "0" * 64
        _rehash_bundle(bundle)
        with self.assertRaisesRegex(self.module.F34bInputError, "parent SHA-256 mismatch"):
            self.preflight(bundle=bundle)

        with tempfile.TemporaryDirectory(prefix="917-f34b-parent-") as temporary:
            fake_manifest = Path(temporary) / "doe-case-manifest.json"
            fake_manifest.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(self.module.F34bInputError, "parent SHA-256 mismatch"):
                self.module.build_preflight_report(
                    self.doe,
                    self.architecture,
                    self.bundle,
                    doe_manifest_path=fake_manifest,
                )

    def test_architecture_and_doe_runtime_gates_fail_closed(self):
        architecture = copy.deepcopy(self.architecture)
        architecture["engine_core_boundary"]["core_liquid_coolant_loop_present"] = True
        with self.assertRaisesRegex(self.module.F34bInputError, "liquid loop"):
            self.preflight(architecture=architecture)

        doe = copy.deepcopy(self.doe)
        doe["runtime"]["future_solver"]["execution_authorized"] = True
        with self.assertRaisesRegex(self.module.F34bInputError, "execution"):
            self.preflight(doe=doe)

    def test_forward_schema_rejects_bool_nan_extra_target_and_wrong_units(self):
        mutations = []
        value = self.forward("naturally_aspirated")
        value["speed_rpm"] = True
        mutations.append(value)
        value = self.forward("naturally_aspirated")
        value["speed_rpm"] = float("nan")
        mutations.append(value)
        value = self.forward("naturally_aspirated")
        value["requested_power_target"] = 1600.0
        mutations.append(value)
        value = self.forward("naturally_aspirated")
        value["unit_registry"]["speed_rpm"] = "rad/s"
        mutations.append(value)
        for index, forward in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(self.module.F34bInputError):
                    self.module.validate_f34_forward_input(
                        forward, "naturally_aspirated"
                    )

    def test_forward_rejects_any_engine_core_liquid_or_legacy_thermal_field(self):
        forward = self.forward("naturally_aspirated")
        forward["selected_architecture"]["engine_core_liquid_coolant_present"] = True
        with self.assertRaisesRegex(self.module.F34bInputError, "architecture"):
            self.module.validate_f34_forward_input(forward, "naturally_aspirated")

        forward = self.forward("naturally_aspirated")
        forward["thermal_hypotheses"]["head_coolant_delta_t_k"] = 15.0
        with self.assertRaises(self.module.F34bInputError):
            self.module.validate_f34_forward_input(forward, "naturally_aspirated")

    def test_variant_specific_charge_and_turbo_fields_are_strict(self):
        na = self.forward("naturally_aspirated")
        na["thermal_hypotheses"]["charge_coolant_delta_t_k"] = 10.0
        with self.assertRaises(self.module.F34bInputError):
            self.module.validate_f34_forward_input(na, "naturally_aspirated")

        tt = self.forward("twin_turbo")
        del tt["thermal_hypotheses"]["charge_coolant_delta_t_k"]
        with self.assertRaises(self.module.F34bInputError):
            self.module.validate_f34_forward_input(tt, "twin_turbo")

        tt = self.forward("twin_turbo")
        tt["turbo_screening_input"] = None
        with self.assertRaises(self.module.F34bInputError):
            self.module.validate_f34_forward_input(tt, "twin_turbo")

    def test_thermal_fraction_and_delta_t_domains_fail_closed(self):
        forward = self.forward("naturally_aspirated")
        forward["thermal_hypotheses"]["head_heat_fraction_of_fuel_power"] = 0.75
        with self.assertRaisesRegex(self.module.F34bInputError, "sum"):
            self.module.validate_f34_forward_input(forward, "naturally_aspirated")

        forward = self.forward("naturally_aspirated")
        forward["thermal_hypotheses"]["cooling_air_delta_t_k"] = 0.0
        with self.assertRaisesRegex(self.module.F34bInputError, "positive"):
            self.module.validate_f34_forward_input(forward, "naturally_aspirated")

    def test_air_oil_network_splits_head_and_adds_head_share_to_oil(self):
        forward = self.forward("naturally_aspirated")
        network = self.module._build_air_oil_thermal_network(
            forward,
            fuel_power_w=5_000_000.0,
            friction_power_w=200_000.0,
            brake_power_w=3_000_000.0,
            charge_heat_w=None,
            configuration="naturally_aspirated",
        )
        loads = network["loads_w"]
        self.assertAlmostEqual(loads["head_total"], 700_000.0)
        self.assertAlmostEqual(loads["head_to_oil"], 245_000.0)
        self.assertAlmostEqual(loads["head_to_air"], 455_000.0)
        self.assertAlmostEqual(loads["engine_core_air"], 655_000.0)
        self.assertAlmostEqual(loads["oil_loop"], 600_000.0)
        self.assertFalse(network["engine_core_liquid_coolant_present"])
        self.assertNotIn("charge_lt_coolant", loads)
        self.assertNotIn("charge_coolant", network["required_mass_flows_kg_s"])
        self.assertTrue(network["algebraic_balances"]["numerically_closed"])
        self.assertFalse(
            network["algebraic_balances"]["physical_energy_balance_validated"]
        )

    def test_twin_turbo_network_has_isolated_lt_charge_loop_only(self):
        forward = self.forward("twin_turbo")
        network = self.module._build_air_oil_thermal_network(
            forward,
            fuel_power_w=5_000_000.0,
            friction_power_w=200_000.0,
            brake_power_w=3_000_000.0,
            charge_heat_w=432_000.0,
            configuration="twin_turbo",
        )
        self.assertEqual(network["loads_w"]["charge_lt_coolant"], 432_000.0)
        self.assertEqual(network["required_mass_flows_kg_s"]["charge_coolant"], 10.0)
        auxiliary = network["algebraic_balances"]["auxiliary_charge"]
        self.assertEqual(auxiliary["charge_lt_flow_identity_residual_w"], 0.0)
        self.assertTrue(
            auxiliary["hydraulically_isolated_from_engine_core_assumed_not_validated"]
        )

    def test_air_oil_network_rejects_wrong_variant_charge_and_negative_remainder(self):
        na = self.forward("naturally_aspirated")
        with self.assertRaisesRegex(RuntimeError, "forbids"):
            self.module._build_air_oil_thermal_network(
                na,
                fuel_power_w=5_000_000.0,
                friction_power_w=200_000.0,
                brake_power_w=3_000_000.0,
                charge_heat_w=1.0,
                configuration="naturally_aspirated",
            )
        with self.assertRaisesRegex(RuntimeError, "negative"):
            self.module._build_air_oil_thermal_network(
                na,
                fuel_power_w=5_000_000.0,
                friction_power_w=200_000.0,
                brake_power_w=4_900_000.0,
                charge_heat_w=None,
                configuration="naturally_aspirated",
            )

    def test_synthetic_forward_is_deterministic_finite_and_all_claims_closed(self):
        for configuration in ("naturally_aspirated", "twin_turbo"):
            with self.subTest(configuration=configuration), mock.patch.object(
                self.module,
                "_solve_closed_cycle_cantera",
                side_effect=lambda forward, _: _fake_cycle(forward),
            ):
                forward = self.forward(configuration)
                first = self.module.solve_f34_forward(
                    forward, configuration, cantera_module=_CanteraStub()
                )
                second = self.module.solve_f34_forward(
                    forward, configuration, cantera_module=_CanteraStub()
                )
                self.assertEqual(first, second)
                self.assertTrue(all(math.isfinite(value) for value in _numeric_leaves(first)))
                self.assertEqual(first["trapped_charge"]["mass_identity_residual_kg_s"], 0.0)
                self.assertTrue(first["trapped_charge"]["numerical_mass_identity_closed"])
                self.assertTrue(
                    first["work_and_power"]["numerical_work_identities_closed"]
                )
                self.assertTrue(all(value is False for value in first["claims"].values()))
                serialized = json.dumps(first, sort_keys=True)
                self.assertNotIn("head_ht_coolant", serialized)
                self.assertNotIn("head_coolant", serialized)

    def test_synthetic_report_runs_exactly_two_noncanonical_fixtures(self):
        def fake_solve(forward, configuration, *, cantera_module):
            return {
                "configuration": configuration,
                "finite_marker": 1.0,
                "claims": {"target_power_proven": False},
            }

        with mock.patch.object(self.module, "solve_f34_forward", side_effect=fake_solve):
            first = self.module.build_synthetic_smoke_report(
                self.doe,
                self.architecture,
                self.bundle,
                self.manifest,
                cantera_module=_CanteraStub(),
            )
            second = self.module.build_synthetic_smoke_report(
                self.doe,
                self.architecture,
                self.bundle,
                self.manifest,
                cantera_module=_CanteraStub(),
            )
        self.assertEqual(first, second)
        self.assertEqual(first["canonical_doe_cases_executed"], 0)
        self.assertEqual(
            first["execution_boundary"]["synthetic_noncanonical_fixture_cases_executed"],
            2,
        )
        self.assertTrue(
            first["execution_boundary"]
            ["all_fixture_hashes_absent_from_canonical_manifest"]
        )
        self.assertEqual(first["execution_boundary"]["source_seed_cases_executed"], 0)
        self.assertEqual(len(first["synthetic_predictions"]), 2)
        canonical = {
            case["forward_input_sha256"] for case in self.manifest["cases"]
        }
        for prediction in first["synthetic_predictions"]:
            self.assertEqual(
                prediction["source_seed_is_canonical_doe_case"],
                prediction["source_seed_forward_input_sha256"] in canonical,
            )
            self.assertNotIn(
                prediction["synthetic_fixture_forward_input_sha256"], canonical
            )
            self.assertTrue(
                prediction["synthetic_fixture_absent_from_all_canonical_cases"]
            )
            self.assertGreaterEqual(
                abs(prediction["synthetic_fixture_speed_delta_rpm"]), 100.0
            )
            self.assertNotEqual(
                prediction["source_seed_speed_rpm"],
                prediction["synthetic_fixture_speed_rpm"],
            )
        self.assertTrue(
            any(
                prediction["source_seed_is_canonical_doe_case"]
                for prediction in first["synthetic_predictions"]
            )
        )
        self.assertTrue(first["synthetic_numerical_power_screen_executed"])
        self.assertFalse(
            first["authoritative_engine_power_prediction_available"]
        )
        self.assertFalse(first["validated_1600_hp"])
        self.assertFalse(first["physical_correlation"])
        self.assertTrue(all(value is False for value in first["claims"].values()))

    def test_synthetic_manifest_exclusion_is_checked_before_backend_load(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["case_counts"]["executed"] = 1
        backend = mock.Mock(side_effect=AssertionError("backend must not load"))
        with mock.patch.object(self.module, "_load_cantera_320", backend):
            with self.assertRaisesRegex(self.module.F34bInputError, "result count"):
                self.module.build_synthetic_smoke_report(
                    self.doe,
                    self.architecture,
                    self.bundle,
                    manifest,
                )
        backend.assert_not_called()

        canonical = {
            case["forward_input_sha256"] for case in self.manifest["cases"]
        }
        seed = self.seeds["naturally_aspirated"]
        fixture, fixture_hash, _ = self.module._build_noncanonical_synthetic_fixture(
            seed, "naturally_aspirated", canonical
        )
        self.assertNotEqual(fixture, seed["forward_input"])
        with self.assertRaisesRegex(self.module.F34bInputError, "collides"):
            self.module._build_noncanonical_synthetic_fixture(
                seed,
                "naturally_aspirated",
                canonical | {fixture_hash},
            )

    def test_synthetic_smoke_dependency_failure_is_fail_closed_and_writes_no_output(self):
        with tempfile.TemporaryDirectory(prefix="917-f34b-") as temporary:
            output = Path(temporary) / "must-not-exist.json"
            stderr = io.StringIO()
            with mock.patch.object(
                self.module,
                "_load_cantera_320",
                side_effect=RuntimeError("Cantera unavailable"),
            ), mock.patch("sys.stderr", stderr):
                code = self.module.main(
                    [
                        "synthetic-smoke",
                        "--doe-contract",
                        str(DOE),
                        "--architecture-contract",
                        str(ARCHITECTURE),
                        "--seed-bundle",
                        str(SEEDS),
                        "--doe-manifest",
                        str(MANIFEST),
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(code, 2)
            self.assertFalse(output.exists())
            self.assertIn("Cantera unavailable", stderr.getvalue())

    def test_cli_preflight_writes_canonical_json_and_rejects_hidden_doe_mode(self):
        with tempfile.TemporaryDirectory(prefix="917-f34b-cli-") as temporary:
            output = Path(temporary) / "preflight.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "preflight",
                    "--doe-contract",
                    str(DOE),
                    "--architecture-contract",
                    str(ARCHITECTURE),
                    "--seed-bundle",
                    str(SEEDS),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout, "")
            self.assertEqual(completed.stderr, "")
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["mode"], "preflight")
            self.assertEqual(report["canonical_doe_cases_executed"], 0)

        rejected = subprocess.run(
            [sys.executable, str(RUNNER), "doe"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("invalid choice", rejected.stderr)

    @unittest.skipUnless(
        importlib.util.find_spec("cantera") is not None,
        "Cantera is exercised by the immutable linux/amd64 F34b image",
    )
    def test_actual_cantera_noncanonical_fixture_smoke_when_dependency_is_available(self):
        cantera = importlib.import_module("cantera")
        if getattr(cantera, "__version__", None) != "3.2.0":
            self.skipTest("exact Cantera 3.2.0 is required")
        report = self.module.build_synthetic_smoke_report(
            self.doe,
            self.architecture,
            self.bundle,
            self.manifest,
            cantera_module=cantera,
        )
        self.assertEqual(report["canonical_doe_cases_executed"], 0)
        self.assertEqual(len(report["synthetic_predictions"]), 2)


if __name__ == "__main__":
    unittest.main()
