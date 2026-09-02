"""Tests adversariaux du contrat cycle/thermique clean-sheet F33."""

from __future__ import annotations

import copy
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json"
RUNNER = ROOT / "scripts/run_917_cycle_thermal_f33.py"
EVIDENCE = (
    ROOT
    / "twins/reference-917-engine/evidence/f33/cycle-thermal-report.json"
)
IMAGE_PUBLICATION = (
    ROOT
    / "twins/reference-917-engine/evidence/f33/engine-cycle-image-publication.json"
)

EXPECTED_CONFIGURATIONS = {"naturally_aspirated", "twin_turbo"}
EXPECTED_RELEASE_GATES = {
    "target_definition_complete",
    "target_power_proven",
    "mass_and_energy_balance_validated",
    "thermodynamic_cycle_validated",
    "turbo_match_validated",
    "combustion_and_knock_validated",
    "cooling_system_validated",
    "oil_system_validated",
    "structural_and_fatigue_validated",
    "controls_and_overspeed_protection_validated",
    "test_bench_start_authorized",
    "porsche_993_packaging_validated",
    "porsche_993_vehicle_installation_authorized",
    "held_out_physical_correlation_complete",
    "metal_print_authorized",
    "manufacturing_authorized",
}


def _load_runner():
    spec = importlib.util.spec_from_file_location("cycle_thermal_917_f33", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"


def _canonical_payload_sha256(value: Any) -> str:
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


def _cantera_320_available() -> bool:
    if importlib.util.find_spec("cantera") is None:
        return False
    cantera = importlib.import_module("cantera")
    return getattr(cantera, "__version__", None) == "3.2.0"


CANTERA_320_AVAILABLE = _cantera_320_available()


def _indexed(values: Any, field: str) -> dict[str, dict[str, Any]]:
    if not isinstance(values, list):
        return {}
    return {
        item[field]: item
        for item in values
        if isinstance(item, dict) and isinstance(item.get(field), str)
    }


def _numeric_leaves(value: Any, prefix: str = ""):
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else key
            yield from _numeric_leaves(item, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _numeric_leaves(item, f"{prefix}[{index}]")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield prefix, float(value)


def _mapping_keys(value: Any, prefix: str = ""):
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else key
            yield child
            yield from _mapping_keys(item, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _mapping_keys(item, f"{prefix}[{index}]")


def _set_dotted(mapping: dict[str, Any], dotted_path: str, value: Any) -> None:
    keys = dotted_path.split(".")
    parent = mapping
    for key in keys[:-1]:
        child = parent[key]
        if not isinstance(child, dict):
            raise AssertionError(f"{dotted_path} does not address a mapping leaf")
        parent = child
    parent[keys[-1]] = value


def _image_parent(contract: dict[str, Any]) -> dict[str, Any]:
    expected = "twins/reference-917-engine/evidence/f33/engine-cycle-image-publication.json"
    matches = [
        parent
        for parent in contract["upstream_manifest"]
        if parent.get("path") == expected
    ]
    if len(matches) != 1:
        raise AssertionError("F33 must reference exactly one image-publication parent")
    return matches[0]


class CycleThermal917F33Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_runner()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.tracked_report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        cls.report = cls.tracked_report

    def validate(self, contract: dict[str, Any] | None = None) -> list[str]:
        return self.module.validate_contract(
            self.contract if contract is None else contract,
            project_root=ROOT,
        )

    def variants(self, contract: dict[str, Any] | None = None):
        payload = self.contract if contract is None else contract
        return _indexed(payload["engine_variants"], "configuration")

    def predictions(self, report: dict[str, Any] | None = None):
        payload = self.report if report is None else report
        return _indexed(payload["forward_predictions"], "configuration")

    def test_contract_has_exact_na_and_twin_turbo_variants_with_separate_target(self):
        self.assertEqual(self.validate(), [])
        self.assertEqual(self.contract["phase"], "F33")
        self.assertEqual(set(self.variants()), EXPECTED_CONFIGURATIONS)
        self.assertEqual(len(self.contract["engine_variants"]), 2)

        target = self.contract["requested_power_target"]
        self.assertEqual(target["value"], 1600.0)
        self.assertEqual(target["unit"], "mechanical_hp")
        self.assertEqual(target["configuration"], "twin_turbo")
        for flag in ("measured", "simulated", "proven"):
            self.assertIs(target[flag], False)

        variants = self.variants()
        self.assertIsNone(variants["naturally_aspirated"]["requested_power_ref"])
        self.assertEqual(
            variants["twin_turbo"]["requested_power_ref"],
            "requested_power_target",
        )
        for variant in variants.values():
            forward = variant["forward_solver_input"]
            self.assertTrue(forward)
            for path in _mapping_keys(forward):
                self.assertNotIn("requested_power", path.lower())
                self.assertNotIn("target_power", path.lower())
        self.assertEqual(set(self.predictions()), EXPECTED_CONFIGURATIONS)
        for configuration, prediction in self.predictions().items():
            self.assertEqual(
                set(prediction),
                {"variant_id", "configuration", "forward_prediction"},
            )
            predicted_hp = prediction["forward_prediction"]["work_and_power"][
                "forward_predicted_mechanical_hp"
            ]
            self.assertTrue(math.isfinite(predicted_hp), configuration)
            self.assertGreater(predicted_hp, 0.0, configuration)

    @unittest.skipUnless(
        CANTERA_320_AVAILABLE,
        "Cantera 3.2.0 is only required for the full F33 image path",
    )
    def test_requested_target_mutation_does_not_change_any_forward_prediction(self):
        mutated = copy.deepcopy(self.contract)
        mutated["requested_power_target"]["value"] = 1400.0
        self.assertEqual(self.validate(mutated), [])

        with tempfile.TemporaryDirectory(prefix="917-f33-target-") as temporary:
            mutated_contract = Path(temporary) / "mutated-contract.json"
            mutated_contract.write_text(_canonical_json(mutated), encoding="utf-8")
            changed_report = self.module.build_report(
                mutated,
                contract_path=mutated_contract,
                project_root=ROOT,
            )
            self.assertEqual(
                changed_report["forward_predictions"],
                self.report["forward_predictions"],
            )
            self.assertEqual(
                changed_report["requested_power_target"]["value"],
                1400.0,
            )
            self.assertNotEqual(
                changed_report["target_comparison"],
                self.report["target_comparison"],
            )
            self.assertEqual(
                changed_report["contract_sha256"],
                _canonical_payload_sha256(mutated),
            )
            self.assertEqual(
                changed_report["contract_file_sha256"],
                _sha256(mutated_contract),
            )

    def test_forward_input_rejects_bool_nan_infinity_negative_and_wrong_units(self):
        turbo = self.variants()["twin_turbo"]
        unit_registry = turbo["forward_solver_input"]["unit_registry"]
        pressure_fields = [field for field, unit in unit_registry.items() if unit == "Pa_abs"]
        temperature_fields = [field for field, unit in unit_registry.items() if unit == "K"]
        self.assertTrue(pressure_fields, "F33 requires at least one absolute-pressure input")
        self.assertTrue(temperature_fields, "F33 requires at least one Kelvin input")
        pressure_field = pressure_fields[0]

        for invalid in (True, math.nan, math.inf, -1.0):
            with self.subTest(invalid=invalid):
                mutated = copy.deepcopy(self.contract)
                variant = self.variants(mutated)["twin_turbo"]
                _set_dotted(variant["forward_solver_input"], pressure_field, invalid)
                self.assertTrue(self.validate(mutated))

        for field, invalid_unit in (
            (pressure_fields[0], "bar"),
            (temperature_fields[0], "degC"),
        ):
            with self.subTest(field=field, invalid_unit=invalid_unit):
                mutated = copy.deepcopy(self.contract)
                variant = self.variants(mutated)["twin_turbo"]
                variant["forward_solver_input"]["unit_registry"][field] = invalid_unit
                self.assertTrue(self.validate(mutated))

    def test_unit_registry_exactly_covers_every_numeric_forward_input(self):
        for configuration, variant in self.variants().items():
            forward = variant["forward_solver_input"]
            registry = forward["unit_registry"]
            numeric_fields = {
                path
                for path, _value in _numeric_leaves(
                    {key: value for key, value in forward.items() if key != "unit_registry"}
                )
            }
            self.assertEqual(set(registry), numeric_fields, configuration)
            self.assertTrue(all(isinstance(unit, str) and unit for unit in registry.values()))

    def test_parent_image_publication_path_sha_and_proof_boundary_are_verified(self):
        parent = _image_parent(self.contract)
        self.assertEqual(
            parent["path"],
            "twins/reference-917-engine/evidence/f33/engine-cycle-image-publication.json",
        )
        self.assertEqual(parent["sha256"], _sha256(IMAGE_PUBLICATION))
        publication = json.loads(IMAGE_PUBLICATION.read_text(encoding="utf-8"))
        self.assertEqual(publication["workflow"]["conclusion"], "success")
        self.assertEqual(publication["image"]["platform"], "linux/amd64")
        self.assertTrue(publication["image"]["anonymous_exact_digest_access_verified"])
        self.assertTrue(all(publication["supply_chain"].values()))
        self.assertEqual(
            publication["runtime_smoke"]["status"],
            "passed_synthetic_thermochemistry_fixture_only",
        )
        self.assertFalse(publication["proof_boundary"]["engine_cycle_solver_executed"])
        self.assertFalse(publication["proof_boundary"]["target_1600_hp_proven"])

        verified = self.report["parent_image_publication"]
        self.assertEqual(verified["path"], parent["path"])
        self.assertEqual(verified["sha256"], parent["sha256"])
        self.assertTrue(verified["anonymous_exact_digest_access_verified"])
        self.assertTrue(verified["verified"])
        self.assertFalse(verified["engine_solver_in_image"])

        mutated = copy.deepcopy(self.contract)
        _image_parent(mutated)["sha256"] = "0" * 64
        self.assertTrue(self.validate(mutated))

    def test_unknown_claim_open_gate_missing_or_duplicate_variant_fail_closed(self):
        for scope in ("top_level", "authority", "variant", "turbo_data"):
            with self.subTest(scope=scope):
                extra_claim = copy.deepcopy(self.contract)
                if scope == "top_level":
                    extra_claim["validated_digital_twin"] = True
                elif scope == "authority":
                    extra_claim["authority_boundary"]["validated_digital_twin"] = True
                elif scope == "variant":
                    self.variants(extra_claim)["twin_turbo"][
                        "validated_digital_twin"
                    ] = True
                else:
                    self.variants(extra_claim)["twin_turbo"]["turbo_data"][
                        "turbo_match_claim"
                    ] = True
                self.assertTrue(self.validate(extra_claim))

        open_gate = copy.deepcopy(self.contract)
        open_gate["release_gates"]["target_power_proven"] = True
        self.assertTrue(self.validate(open_gate))
        with self.assertRaises(ValueError):
            self.module.build_report(
                open_gate,
                contract_path=CONTRACT,
                project_root=ROOT,
            )

        missing = copy.deepcopy(self.contract)
        missing["engine_variants"].pop()
        self.assertTrue(self.validate(missing))

        duplicate = copy.deepcopy(self.contract)
        duplicate["engine_variants"].append(copy.deepcopy(duplicate["engine_variants"][0]))
        self.assertTrue(self.validate(duplicate))

        wrong_configuration = copy.deepcopy(self.contract)
        self.variants(wrong_configuration)["twin_turbo"][
            "configuration"
        ] = "naturally_aspirated"
        self.assertTrue(self.validate(wrong_configuration))

    def test_na_has_no_turbo_and_twin_turbo_remains_unmatched(self):
        variants = self.variants()
        na = variants["naturally_aspirated"]
        turbo = variants["twin_turbo"]

        self.assertEqual(na["turbocharger_count"], 0)
        self.assertIsNone(na["turbo_data"])
        self.assertEqual(na["forward_solver_input"]["turbocharger_count"], 0)
        self.assertIsNone(na["forward_solver_input"]["turbo_screening_input"])

        self.assertEqual(turbo["turbocharger_count"], 2)
        self.assertIsInstance(turbo["turbo_data"], dict)
        self.assertIs(turbo["turbo_data"]["turbine_map_digitized"], False)
        self.assertIs(turbo["turbo_data"]["turbo_match_validated"], False)
        turbo_screen = self.predictions()["twin_turbo"]["forward_prediction"][
            "turbo_screen"
        ]
        self.assertIs(turbo_screen["turbine_map_digitized"], False)
        self.assertIs(turbo_screen["map_interpolation_executed"], False)
        self.assertIs(turbo_screen["turbo_match_validated"], False)
        self.assertIs(self.report["release_gates"]["turbo_match_validated"], False)

    def test_tracked_report_outputs_are_finite_and_match_contract(self):
        numeric_values = list(_numeric_leaves(self.report))
        self.assertTrue(numeric_values)
        for path, value in numeric_values:
            self.assertTrue(math.isfinite(value), path)
        _canonical_json(self.report)

        self.assertEqual(EVIDENCE.read_text(encoding="utf-8"), _canonical_json(self.report))
        self.assertEqual(
            self.report["contract_sha256"],
            _canonical_payload_sha256(self.contract),
        )
        self.assertEqual(self.report["contract_file_sha256"], _sha256(CONTRACT))

    @unittest.skipUnless(
        CANTERA_320_AVAILABLE,
        "Cantera 3.2.0 is only required for the full F33 image path",
    )
    def test_solver_report_is_deterministic_and_tracked_exactly(self):
        second = self.module.build_report(
            copy.deepcopy(self.contract),
            contract_path=CONTRACT,
            project_root=ROOT,
        )
        self.assertEqual(second, self.report)
        self.assertEqual(self.tracked_report, self.report)

    def test_semantics_can_close_without_solver_or_physical_release(self):
        topology = self.report["semantic_topology"]
        self.assertTrue(topology["semantic_topology_closed"])
        self.assertFalse(topology["physical_bom_complete"])
        self.assertFalse(topology["solver_ready"])

        scope = self.report["model_scope"]
        self.assertEqual(scope["maximum_model_dimension"], "0D")
        self.assertEqual(
            scope["cantera_role"],
            "zero_dimensional_thermochemistry_only_not_engine_cycle_proof",
        )
        self.assertEqual(scope["cantera_version"], "3.2.0")
        self.assertIs(scope["forward_closed_cycle_0d_executed"], True)
        for flag in (
            "twelve_open_cylinders_executed",
            "one_dimensional_gas_dynamics_executed",
            "turbo_map_interpolation_executed",
            "hydraulic_network_executed",
            "cfd_executed",
            "cht_executed",
            "physicsnemo_executed",
            "omniverse_executed",
            "dyno_measurement_available",
            "physical_correlation_complete",
        ):
            self.assertIs(scope[flag], False, flag)

        for prediction in self.report["forward_predictions"]:
            numerical_scope = prediction["forward_prediction"]["numerical_scope"]
            self.assertIs(numerical_scope["cantera_equilibrium_uv_executed"], True)
            self.assertIs(numerical_scope["closed_cycle_four_state_only"], True)
            for flag in (
                "crank_angle_time_marching_executed",
                "cyclic_convergence_executed",
                "one_dimensional_gas_dynamics_executed",
                "cfd_or_cht_executed",
                "combustion_calibrated",
                "knock_model_executed",
                "physical_correlation_complete",
            ):
                self.assertIs(numerical_scope[flag], False, flag)

        self.assertEqual(set(self.contract["release_gates"]), EXPECTED_RELEASE_GATES)
        self.assertEqual(set(self.report["release_gates"]), EXPECTED_RELEASE_GATES)
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))
        self.assertTrue(all(value is False for value in self.report["release_gates"].values()))

    @unittest.skipUnless(
        CANTERA_320_AVAILABLE,
        "Cantera 3.2.0 is only required for the full F33 image path",
    )
    def test_cli_output_check_and_stale_evidence_paths(self):
        with tempfile.TemporaryDirectory(prefix="917-f33-test-") as temporary:
            output = Path(temporary) / "cycle-thermal-report.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--contract",
                    str(CONTRACT),
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), self.report)

            current = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--contract",
                    str(CONTRACT),
                    "--check",
                    str(EVIDENCE),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(current.returncode, 0, current.stderr)

            output.write_text("{}\n", encoding="utf-8")
            stale = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--contract",
                    str(CONTRACT),
                    "--check",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("stale", (stale.stdout + stale.stderr).lower())


if __name__ == "__main__":
    unittest.main()
