"""Tests adversariaux du bundle de seeds air/huile F34b."""

from __future__ import annotations

import copy
import hashlib
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
RUNNER = ROOT / "scripts/export_917_air_oil_seeds_f34b.py"
TRACKED = (
    ROOT
    / "twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json"
)


def _load_runner():
    spec = importlib.util.spec_from_file_location("f34b_seed_export", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _canonical_json(value: Any) -> str:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AirOilSeedsF34bTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_runner()
        cls.tracked_text = TRACKED.read_text(encoding="utf-8")
        cls.tracked = cls.module._read_json(TRACKED)
        cls.built = cls.module.build_bundle(project_root=ROOT)
        cls.parent_hashes = {
            path: _sha256(ROOT / path)
            for _, path, _ in cls.module.PARENT_SPECS
        }

    def assert_invalid(self, bundle: dict[str, Any], expected: str) -> None:
        errors = self.module.validate_bundle(
            bundle,
            expected_parent_hashes=self.parent_hashes,
        )
        self.assertTrue(errors, "la mutation doit être rejetée en fail-closed")
        self.assertTrue(
            any(expected in error for error in errors),
            f"erreur attendue {expected!r}; erreurs reçues: {errors}",
        )

    def test_build_is_deterministic_canonical_and_matches_tracked_bundle(self):
        second = self.module.build_bundle(project_root=ROOT)
        self.assertEqual(self.built, second)
        self.assertEqual(self.built, self.tracked)
        self.assertEqual(self.tracked_text, _canonical_json(self.built))
        self.assertEqual(
            self.module.validate_bundle(
                self.built,
                expected_parent_hashes=self.parent_hashes,
            ),
            [],
        )
        payload = copy.deepcopy(self.built)
        claimed = payload.pop("bundle_payload_sha256")
        self.assertEqual(claimed, self.module._canonical_payload_sha256(payload))

    def test_exact_parent_paths_and_file_hashes_are_pinned(self):
        expected_paths = [path for _, path, _ in self.module.PARENT_SPECS]
        self.assertEqual(
            [parent["path"] for parent in self.built["parents"]],
            expected_paths,
        )
        self.assertNotIn(self.module.F33_CONTRACT_PATH, expected_paths)
        for parent in self.built["parents"]:
            self.assertEqual(parent["sha256"], _sha256(ROOT / parent["path"]))

    def test_two_forward_inputs_have_canonical_hashes_and_no_results(self):
        self.assertEqual(
            [seed["configuration"] for seed in self.built["seeds"]],
            ["naturally_aspirated", "twin_turbo"],
        )
        self.assertEqual(
            [seed["variant_id"] for seed in self.built["seeds"]],
            [
                "917_2026_flat12_na_air_oil_f34b",
                "917_2026_flat12_twin_turbo_air_oil_f34b",
            ],
        )
        self.assertEqual(self.built["canonical_doe_cases_executed"], 0)
        for seed in self.built["seeds"]:
            self.assertEqual(
                seed["forward_input_sha256"],
                self.module._canonical_payload_sha256(seed["forward_input"]),
            )
            self.assertIsNone(
                self.module._forward_power_target_leak(seed["forward_input"])
            )
        self.assertEqual(
            self.built["execution_ledger"],
            {
                "seed_count": 2,
                "solver_case_count": 0,
                "solver_executed": False,
                "labels_present": False,
                "calibration_executed": False,
                "training_executed": False,
                "physical_test_executed": False,
            },
        )

    def test_air_oil_core_and_auxiliary_liquid_boundary_are_exact(self):
        for seed in self.built["seeds"]:
            configuration = seed["configuration"]
            forward = seed["forward_input"]
            architecture = forward["selected_architecture"]
            self.assertIs(
                architecture["engine_core_liquid_coolant_present"], False
            )
            self.assertEqual(
                architecture["engine_core_heat_rejection"],
                ["forced_air", "dry_sump_oil"],
            )
            thermal_coolant = {
                key
                for key in forward["thermal_hypotheses"]
                if "coolant" in key.lower()
            }
            if configuration == "naturally_aspirated":
                self.assertEqual(thermal_coolant, set())
                self.assertEqual(architecture["auxiliary_liquid_scope"], [])
            else:
                self.assertEqual(
                    thermal_coolant,
                    {
                        "charge_coolant_cp_j_kg_k",
                        "charge_coolant_delta_t_k",
                    },
                )
                self.assertEqual(
                    architecture["auxiliary_liquid_scope"],
                    ["charge_cooling", "turbo_chra_optional_unresolved"],
                )

    def test_modern_control_requirements_are_present_but_unvalidated(self):
        for seed in self.built["seeds"]:
            configuration = seed["configuration"]
            management = seed["forward_input"]["engine_management"]
            expected = dict(self.module.EXPECTED_ENGINE_MANAGEMENT_COMMON)
            expected["electronic_wastegate_control_required"] = (
                configuration == "twin_turbo"
            )
            self.assertEqual(management, expected)
            self.assertIs(management["electronic_fuel_injection_required"], True)
            self.assertIs(management["dual_electronic_ignition_required"], True)
            self.assertEqual(management["independent_ignition_channels_required"], 24)
            self.assertIs(management["drive_by_wire_required"], True)
            self.assertIs(management["variable_cam_timing_candidate"], True)
            self.assertIs(management["variable_valve_lift_candidate"], True)
            self.assertIs(management["closed_loop_lambda_required"], True)
            self.assertIs(
                management["cylinder_attributed_knock_control_candidate"], True
            )
            self.assertIs(management["can_fd_required"], True)
            self.assertIs(management["hardware_maps_thresholds_validated"], False)

    def test_target_is_neither_input_feature_nor_calibration(self):
        authority = self.built["authority_boundary"]
        self.assertIs(
            authority["requested_power_target_present_in_forward_inputs"], False
        )
        self.assertIs(authority["requested_power_target_used_as_feature"], False)
        self.assertIs(
            authority["requested_power_target_used_for_calibration"], False
        )
        self.assertIs(authority["inverse_sizing_seed_ancestry_present"], True)
        self.assertIs(authority["full_target_independence_proven"], False)

    def test_all_physical_and_release_gates_remain_false(self):
        self.assertEqual(
            set(self.built["physical_gates"]), self.module.PHYSICAL_GATE_IDS
        )
        self.assertTrue(
            all(value is False for value in self.built["physical_gates"].values())
        )
        self.assertEqual(
            set(self.built["release_gates"]), self.module.RELEASE_GATE_IDS
        )
        self.assertTrue(
            all(value is False for value in self.built["release_gates"].values())
        )

    def test_image_runtime_is_self_contained_and_fail_closed(self):
        runtime = self.built["image_runtime_contract"]
        self.assertIs(runtime["bundle_is_self_contained_for_two_forward_inputs"], True)
        self.assertIs(runtime["f33_forward_solver_source_required_in_image"], False)
        self.assertIs(runtime["f33_contract_required_in_image"], False)
        self.assertIs(runtime["f34_generator_source_required_in_image"], False)
        self.assertIs(runtime["network_required_to_load_bundle"], False)
        self.assertIs(runtime["solver_execution_authorized"], False)

    def test_parent_path_and_hash_mutations_are_rejected(self):
        mutated = copy.deepcopy(self.built)
        mutated["parents"][0]["path"] = "../air-oil-core-controls-f34a.json"
        self.assert_invalid(mutated, "parent_path_invalid")

        mutated = copy.deepcopy(self.built)
        mutated["parents"][2]["sha256"] = "0" * 64
        self.assert_invalid(mutated, "parent_sha_mismatch")

        mutated = copy.deepcopy(self.built)
        mutated["parents"].reverse()
        self.assert_invalid(mutated, "parent_id_invalid")

    def test_requested_power_target_leaks_are_rejected(self):
        mutations = (
            ("requested_power_target_w", 1_193_120.0),
            ("calibration_note", "distance_to_1600"),
            ("power_target_mechanical_hp", 1600.0),
        )
        for key, value in mutations:
            with self.subTest(key=key):
                mutated = copy.deepcopy(self.built)
                mutated["seeds"][1]["forward_input"][key] = value
                self.assert_invalid(mutated, "requested_power_target_leak")

    def test_core_liquid_and_auxiliary_scope_mutations_are_rejected(self):
        mutated = copy.deepcopy(self.built)
        mutated["seeds"][0]["forward_input"]["thermal_hypotheses"][
            "head_coolant_delta_t_k"
        ] = 20.0
        self.assert_invalid(mutated, "engine_core_liquid_thermal_field_present")

        mutated = copy.deepcopy(self.built)
        mutated["seeds"][1]["forward_input"]["selected_architecture"][
            "engine_core_liquid_coolant_present"
        ] = True
        self.assert_invalid(mutated, "selected_air_oil_architecture_invalid")

        mutated = copy.deepcopy(self.built)
        mutated["seeds"][0]["forward_input"]["thermal_hypotheses"][
            "charge_coolant_delta_t_k"
        ] = 10.0
        self.assert_invalid(mutated, "auxiliary_coolant_scope_invalid")

    def test_each_modern_control_family_is_fail_closed(self):
        fields = (
            "electronic_fuel_injection_required",
            "dual_electronic_ignition_required",
            "drive_by_wire_required",
            "variable_cam_timing_candidate",
            "variable_valve_lift_candidate",
            "closed_loop_lambda_required",
            "cylinder_attributed_knock_control_candidate",
            "can_fd_required",
        )
        for field in fields:
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.built)
                mutated["seeds"][0]["forward_input"]["engine_management"][
                    field
                ] = False
                self.assert_invalid(mutated, "modern_engine_management_invalid")

    def test_hash_execution_and_gate_escalations_are_rejected(self):
        mutated = copy.deepcopy(self.built)
        mutated["seeds"][0]["forward_input_sha256"] = "0" * 64
        self.assert_invalid(mutated, "forward_input_sha_mismatch")

        mutated = copy.deepcopy(self.built)
        mutated["execution_ledger"]["solver_executed"] = True
        mutated["execution_ledger"]["solver_case_count"] = 1
        self.assert_invalid(mutated, "execution_ledger_invalid")

        mutated = copy.deepcopy(self.built)
        mutated["physical_gates"]["target_power_proven"] = True
        self.assert_invalid(mutated, "physical_gates_must_all_be_false")

        mutated = copy.deepcopy(self.built)
        mutated["release_gates"]["manufacturing_authorized"] = True
        self.assert_invalid(mutated, "release_gates_must_all_be_false")

    def test_non_finite_and_non_json_values_are_rejected(self):
        mutated = copy.deepcopy(self.built)
        mutated["seeds"][0]["forward_input"]["speed_rpm"] = math.inf
        self.assert_invalid(mutated, "non_finite")

        mutated = copy.deepcopy(self.built)
        mutated["seeds"][0]["forward_input"]["speed_rpm"] = {1, 2}
        self.assert_invalid(mutated, "non_json_type")

    def test_duplicate_json_keys_are_rejected_by_reader(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"phase":"F34b","phase":"F34c"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                self.module._read_json(path)

    def test_cli_check_and_safe_output_path(self):
        checked = subprocess.run(
            [sys.executable, str(RUNNER), "--check", str(TRACKED)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "bundle.json"
            generated = subprocess.run(
                [sys.executable, str(RUNNER), "--output", str(output)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(generated.returncode, 0, generated.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), self.tracked_text)

    def test_cli_rejects_escape_and_parent_overwrite(self):
        outside = ROOT.parent / "f34b-escape.json"
        escaped = subprocess.run(
            [sys.executable, str(RUNNER), "--output", str(outside)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(escaped.returncode, 2)
        self.assertIn("escapes project root", escaped.stderr)
        self.assertFalse(outside.exists())

        protected = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--output",
                str(ROOT / self.module.F34_CONTRACT_PATH),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(protected.returncode, 2)
        self.assertIn("refusing to overwrite source parent", protected.stderr)


if __name__ == "__main__":
    unittest.main()
