"""Tests adversariaux du contrat de décision F34a air/huile et contrôles."""

from __future__ import annotations

import copy
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
CONTRACT = ROOT / "twins/reference-917-engine/air-oil-core-controls-f34a.json"
VALIDATOR = ROOT / "scripts/validate_917_air_oil_core_controls_f34a.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("f34a_validator", VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AirOilCoreControlsF34aTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_validator()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def validate(self, contract: dict[str, Any] | None = None) -> list[str]:
        return self.module.validate_contract(
            self.contract if contract is None else contract,
            project_root=ROOT,
        )

    def assert_rejected(
        self,
        contract: dict[str, Any],
        expected_error: str | None = None,
    ) -> None:
        errors = self.validate(contract)
        self.assertTrue(errors, "la mutation doit etre rejetee en fail-closed")
        if expected_error is not None:
            self.assertTrue(
                any(expected_error in error for error in errors),
                f"erreur attendue {expected_error!r}, erreurs recues: {errors}",
            )

    def test_baseline_validates_and_cli_succeeds(self):
        self.assertEqual(self.validate(), [])
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "--contract", str(CONTRACT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("decision contract valid", result.stdout)
        self.assertEqual(
            self.contract["decision"]["id"],
            "F34A-AIR-OIL-CORE-2026-CONTROLS",
        )

    def test_top_level_and_nested_schema_are_closed(self):
        changed = copy.deepcopy(self.contract)
        changed["extra"] = None
        self.assert_rejected(changed, "unexpected_key:contract.extra")

        mutations = (
            ("decision", lambda value: value["decision"].__setitem__("extra", None)),
            (
                "core",
                lambda value: value["engine_core_boundary"].__setitem__("extra", None),
            ),
            (
                "forced_air",
                lambda value: value["forced_air_architecture"].__setitem__("extra", None),
            ),
            (
                "controls",
                lambda value: value["controls_architecture"]["ecu"].__setitem__(
                    "extra", None
                ),
            ),
            (
                "sensor",
                lambda value: value["sensor_registry"][0].__setitem__("extra", None),
            ),
            (
                "interlock",
                lambda value: value["hardwired_interlocks"][0].__setitem__(
                    "extra", None
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(section=label):
                changed = copy.deepcopy(self.contract)
                mutate(changed)
                self.assert_rejected(changed, "unexpected_key")

    def test_parent_paths_hashes_and_roles_are_fail_closed(self):
        changed = copy.deepcopy(self.contract)
        changed["parents"][0]["sha256"] = "0" * 64
        self.assert_rejected(changed, "value_invalid:parents[0].sha256")

        changed = copy.deepcopy(self.contract)
        changed["parents"][0]["path"] = "../reengineering-contract-f11.json"
        self.assert_rejected(changed, "value_invalid:parents[0].path")
        self.assertIsNone(
            self.module._safe_file(ROOT, "../reengineering-contract-f11.json")
        )

        changed = copy.deepcopy(self.contract)
        changed["parents"][2]["head_liquid_loop_selection_transferred"] = True
        self.assert_rejected(
            changed,
            "value_invalid:parents[2].head_liquid_loop_selection_transferred",
        )

    def test_core_rejects_every_liquid_jacket_cavity_or_cross_connection(self):
        for index in range(3):
            for key in (
                "liquid_coolant_jacket_allowed",
                "liquid_coolant_cavity_allowed",
                "liquid_coolant_passage_geometry_authorized",
            ):
                with self.subTest(component=index, key=key):
                    changed = copy.deepcopy(self.contract)
                    changed["engine_core_boundary"]["included_components"][index][key] = True
                    self.assert_rejected(changed, "core_liquid_prohibition_invalid")

        for key in (
            "core_liquid_coolant_loop_present",
            "core_to_auxiliary_liquid_cross_connection_allowed",
            "oil_to_auxiliary_liquid_heat_exchanger_allowed",
        ):
            with self.subTest(boundary=key):
                changed = copy.deepcopy(self.contract)
                changed["engine_core_boundary"][key] = True
                self.assert_rejected(changed, "core_boundary_value_invalid")

        changed = copy.deepcopy(self.contract)
        changed["engine_core_boundary"]["included_components"][2][
            "permitted_heat_transfer_media"
        ] = ["forced_air", "dry_sump_oil", "head_ht_coolant"]
        self.assert_rejected(changed, "core_media_invalid")

    def test_forced_air_fan_plenums_and_fins_are_mandatory(self):
        for key in (
            "required",
            "fan_required",
            "bank_plenums_required",
            "head_fins_required",
            "cylinder_fins_required",
            "baffles_and_seals_required",
        ):
            with self.subTest(requirement=key):
                changed = copy.deepcopy(self.contract)
                changed["forced_air_architecture"][key] = False
                self.assert_rejected(changed, "forced_air_requirement_invalid")

        changed = copy.deepcopy(self.contract)
        changed["forced_air_architecture"]["topology"].remove("bank_plenums")
        self.assert_rejected(changed, "forced_air_topology_invalid")

    def test_dry_sump_scavenge_piston_jets_and_air_oil_cooler_are_mandatory(self):
        for key in (
            "pressure_stage_required",
            "scavenge_stages_required",
            "deairation_required",
            "filtration_required",
            "piston_underside_oil_jets_required",
            "air_to_oil_heat_rejection_required",
        ):
            with self.subTest(requirement=key):
                changed = copy.deepcopy(self.contract)
                changed["dry_sump_oil_architecture"][key] = False
                self.assert_rejected(changed, "dry_sump_requirement_invalid")

        changed = copy.deepcopy(self.contract)
        changed["dry_sump_oil_architecture"][
            "liquid_to_oil_heat_rejection_allowed"
        ] = True
        self.assert_rejected(
            changed,
            "dry_sump_liquid_heat_rejection_must_be_false",
        )

    def test_auxiliary_liquid_is_isolated_and_limited_to_charge_and_optional_chra(self):
        auxiliary = self.contract["auxiliary_liquid_boundary"]
        self.assertEqual(
            [item["id"] for item in auxiliary["allowed_consumers"]],
            ["charge_cooling", "turbo_chra"],
        )
        self.assertIs(auxiliary["allowed_consumers"][0]["optional"], False)
        self.assertIs(auxiliary["allowed_consumers"][1]["optional"], True)

        changed = copy.deepcopy(self.contract)
        changed["auxiliary_liquid_boundary"]["allowed_consumers"].append(
            copy.deepcopy(changed["auxiliary_liquid_boundary"]["allowed_consumers"][0])
        )
        changed["auxiliary_liquid_boundary"]["allowed_consumers"][-1]["id"] = (
            "cylinder_heads"
        )
        self.assert_rejected(changed, "auxiliary_consumers_invalid")

        for key, invalid in (
            ("hydraulically_isolated_from_engine_core_required", False),
            ("shared_core_cavity_allowed", True),
            ("shared_core_manifold_allowed", True),
            ("core_cross_connection_allowed", True),
            ("all_other_liquid_consumers_forbidden", False),
        ):
            with self.subTest(boundary=key):
                changed = copy.deepcopy(self.contract)
                changed["auxiliary_liquid_boundary"][key] = invalid
                self.assert_rejected(changed, "auxiliary_liquid_value_invalid")

    def test_injection_and_dual_ignition_channel_contract_is_exact(self):
        injection = self.contract["controls_architecture"]["fuel_injection"]
        self.assertEqual(injection["minimum_independent_channels"], 12)
        self.assertEqual(injection["target_independent_channels"], 24)
        self.assertIs(injection["staged_port_injection_candidate"], True)
        ignition = self.contract["controls_architecture"]["ignition"]
        self.assertEqual(ignition["spark_plugs_per_cylinder"], 2)
        self.assertEqual(ignition["independent_channels_required"], 24)

        mutations = (
            ("fuel_injection", "minimum_independent_channels", 11),
            ("fuel_injection", "target_independent_channels", 12),
            ("fuel_injection", "staged_port_injection_candidate", False),
            ("fuel_injection", "minimum_independent_channels", True),
            ("ignition", "spark_plugs_per_cylinder", 1),
            ("ignition", "independent_channels_required", 12),
        )
        for section, key, invalid in mutations:
            with self.subTest(section=section, key=key, invalid=invalid):
                changed = copy.deepcopy(self.contract)
                changed["controls_architecture"][section][key] = invalid
                self.assert_rejected(changed, f"value_invalid:controls_architecture.{section}.{key}")

    def test_ecu_redundant_dbw_and_electronic_wastegates_stay_unselected(self):
        mutations = (
            ("ecu", "selected", True),
            ("ecu", "validated", True),
            ("drive_by_wire", "actuator_count_minimum", 1),
            ("drive_by_wire", "one_actuator_per_bank_required", False),
            ("drive_by_wire", "pedal_position_channels_minimum", 1),
            ("drive_by_wire", "throttle_position_channels_minimum", 1),
            ("drive_by_wire", "independent_plausibility_monitor_required", False),
            ("drive_by_wire", "deenergized_safe_state_required", False),
            ("wastegates", "mode_requirement", "pneumatic_only"),
            ("wastegates", "position_feedback_required", False),
            ("wastegates", "deenergized_safe_open_state_required", False),
            (
                "wastegates",
                "sensor_or_actuator_fault_action_requirement",
                "hold_last_command",
            ),
            ("wastegates", "selected", True),
        )
        for section, key, invalid in mutations:
            with self.subTest(section=section, key=key):
                changed = copy.deepcopy(self.contract)
                changed["controls_architecture"][section][key] = invalid
                self.assert_rejected(
                    changed,
                    f"value_invalid:controls_architecture.{section}.{key}",
                )

    def test_vvt_vvl_lambda_knock_and_can_fd_are_fail_closed_requirements(self):
        controls = self.contract["controls_architecture"]
        self.assertIs(
            controls["valvetrain_control"]["variable_cam_timing_candidate"], True
        )
        self.assertIs(
            controls["valvetrain_control"]["variable_valve_lift_candidate"], True
        )
        self.assertIs(controls["lambda_control"]["closed_loop_required"], True)
        self.assertEqual(
            controls["knock_control"]["mode_requirement"],
            "crank_angle_windowed_cylinder_attributed_knock_control",
        )
        self.assertIs(controls["communications"]["can_fd_required"], True)

        mutations = (
            ("valvetrain_control", "variable_cam_timing_candidate", False),
            ("valvetrain_control", "variable_valve_lift_candidate", False),
            ("valvetrain_control", "selected", True),
            ("valvetrain_control", "validated", True),
            ("lambda_control", "closed_loop_required", False),
            ("lambda_control", "selected", True),
            ("lambda_control", "validated", True),
            ("knock_control", "closed_loop_ignition_retard_candidate", False),
            ("knock_control", "selected", True),
            ("knock_control", "validated", True),
            ("communications", "can_fd_required", False),
            ("communications", "selected", True),
            ("communications", "validated", True),
        )
        for section, key, invalid in mutations:
            with self.subTest(section=section, key=key):
                changed = copy.deepcopy(self.contract)
                changed["controls_architecture"][section][key] = invalid
                self.assert_rejected(
                    changed,
                    f"value_invalid:controls_architecture.{section}.{key}",
                )

    def test_sensor_hardware_ranges_and_calibrations_remain_null_and_blocked(self):
        sensors = {item["id"]: item for item in self.contract["sensor_registry"]}
        self.assertEqual(sensors["cam_phase"]["scope"], "each_actuated_camshaft")
        self.assertEqual(sensors["valve_lift_state"]["scope"], "each_variable_lift_actuator")
        self.assertEqual(sensors["exhaust_gas_temperature"]["scope"], "each_cylinder")
        self.assertEqual(sensors["core_metal_temperature"]["scope"], "each_cylinder_head")
        self.assertIn("knock", sensors)
        self.assertIn("fuel_differential_pressure", sensors)
        self.assertNotIn("fuel_pressure", sensors)

        mutations = (
            ("hardware_ref", "sensor-model-x"),
            ("operating_range", [0, 100]),
            ("calibration_ref", "evidence/calibration.json"),
            ("status", "selected"),
        )
        for key, invalid in mutations:
            with self.subTest(field=key):
                changed = copy.deepcopy(self.contract)
                changed["sensor_registry"][0][key] = invalid
                self.assert_rejected(changed, "sensor_")

        changed = copy.deepcopy(self.contract)
        changed["sensor_registry"].pop()
        self.assert_rejected(changed, "sensor_registry_invalid")

    def test_logging_evidence_remains_null_and_blocked(self):
        for key, invalid in (
            ("logger_hardware_ref", "logger-x"),
            ("schema_ref", "logging-schema.json"),
            ("sample_rate_plan", {"hz": 1000}),
            ("retention_plan", {"seconds": 60}),
            ("time_sync_evidence_ref", "evidence/time-sync.json"),
            ("status", "ready"),
        ):
            with self.subTest(field=key):
                changed = copy.deepcopy(self.contract)
                changed["logging_architecture"][key] = invalid
                self.assert_rejected(
                    changed,
                    f"value_invalid:logging_architecture.{key}",
                )

    def test_hardwired_interlocks_cannot_be_overridden_or_falsely_defined(self):
        self.assertEqual(
            self.contract["hardwired_interlocks"][-1]["id"],
            "turbo_overspeed",
        )
        for key, invalid in (
            ("ecu_override_allowed", True),
            ("hardware_ref", "safety-plc-x"),
            ("threshold", 1.0),
            ("logic_ref", "interlock-logic.json"),
            ("verification_ref", "evidence/trip-test.json"),
            ("status", "verified"),
        ):
            with self.subTest(field=key):
                changed = copy.deepcopy(self.contract)
                changed["hardwired_interlocks"][0][key] = invalid
                self.assert_rejected(changed, "hardwired_interlock")

        changed = copy.deepcopy(self.contract)
        changed["hardwired_interlocks"].pop()
        self.assert_rejected(changed, "hardwired_interlocks_invalid")

    def test_all_hardware_range_map_and_threshold_slots_are_null_and_blocked(self):
        for key, invalid in (
            ("value", {"model": "invented"}),
            ("evidence_ref", "evidence/invented.json"),
            ("status", "selected"),
            ("kind", "result"),
        ):
            with self.subTest(field=key):
                changed = copy.deepcopy(self.contract)
                changed["unresolved_registry"][0][key] = invalid
                self.assert_rejected(changed, "unresolved_")

        changed = copy.deepcopy(self.contract)
        changed["controls_architecture"]["ecu"]["hardware_slot_ref"] = (
            "U-F34A-FAN-MAP"
        )
        self.assert_rejected(changed, "value_invalid:controls_architecture.ecu.hardware_slot_ref")

    def test_all_technical_release_and_authority_gates_fail_closed(self):
        for section in ("technical_gates", "release_gates"):
            for gate in self.contract[section]:
                with self.subTest(section=section, gate=gate):
                    changed = copy.deepcopy(self.contract)
                    changed[section][gate] = True
                    self.assert_rejected(changed, f"{section[:-1]}s_must_all_be_false")

        for key in (
            "hardware_selected",
            "target_power_proven",
            "ruf_compatibility_evaluated",
            "porsche_993_fitment_evaluated",
            "engine_operation_authorized",
            "manufacturing_authorized",
        ):
            with self.subTest(authority=key):
                changed = copy.deepcopy(self.contract)
                changed["authority_boundary"][key] = True
                self.assert_rejected(changed, f"value_invalid:authority_boundary.{key}")

        changed = copy.deepcopy(self.contract)
        changed["prohibited_claims"].remove("ruf_compatibility_or_validation")
        self.assert_rejected(changed, "prohibited_claims_invalid")

    def test_non_finite_json_and_malformed_contract_fail_via_cli(self):
        with tempfile.TemporaryDirectory(prefix="917-f34a-") as temporary:
            temporary_path = Path(temporary)
            for token, invalid in (("NaN", math.nan), ("Infinity", math.inf)):
                with self.subTest(token=token):
                    changed = copy.deepcopy(self.contract)
                    changed["sensor_registry"][0]["operating_range"] = invalid
                    path = temporary_path / f"contract-{token}.json"
                    path.write_text(
                        json.dumps(changed, allow_nan=True),
                        encoding="utf-8",
                    )
                    result = subprocess.run(
                        [sys.executable, str(VALIDATOR), "--contract", str(path)],
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("non-finite JSON constant rejected", result.stderr)

            malformed = temporary_path / "malformed.json"
            malformed.write_text("[]\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--contract", str(malformed)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("contract_not_object", result.stderr)


if __name__ == "__main__":
    unittest.main()
