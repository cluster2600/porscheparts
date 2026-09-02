"""Tests adversariaux du contrat et du manifeste DOE F34 du moteur 917."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/doe-surrogate-f34.json"
F33_CONTRACT = ROOT / "twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json"
RUNNER = ROOT / "scripts/run_917_doe_f34.py"
TRACKED_MANIFEST = (
    ROOT / "twins/reference-917-engine/evidence/f34/doe-case-manifest.json"
)

EXPECTED_CONFIG_COUNTS = {
    "naturally_aspirated": 857,
    "twin_turbo": 1713,
}
EXPECTED_BLOCK_COUNTS = {
    "anchor": 2,
    "morris": 648,
    "lhs": 1536,
    "ood": 384,
}
EXPECTED_SPLIT_COUNTS = {
    "naturally_aspirated": {
        "train": 320,
        "validation": 64,
        "conformal_calibration": 64,
        "locked_digital_holdout": 64,
    },
    "twin_turbo": {
        "train": 640,
        "validation": 128,
        "conformal_calibration": 128,
        "locked_digital_holdout": 128,
    },
}
EXPECTED_RELEASE_GATES = {
    "doe_execution_complete",
    "dataset_ready",
    "training_authorized",
    "surrogate_trained",
    "surrogate_validated_against_0d_solver",
    "ood_policy_calibrated",
    "one_dimensional_model_validated",
    "hydraulic_network_validated",
    "cfd_validated",
    "cht_validated",
    "physical_correlation_complete",
    "target_power_proven",
    "cooling_system_validated",
    "test_bench_start_authorized",
    "porsche_993_vehicle_installation_authorized",
    "metal_print_authorized",
    "manufacturing_authorized",
    "ecu_hardware_selected",
    "ecu_io_complete",
    "crank_cam_sync_validated",
    "injector_characterization_validated",
    "ignition_validated",
    "closed_loop_controls_validated",
    "vvt_vvl_validated",
    "lambda_control_validated",
    "knock_control_validated",
    "boost_failsafe_validated",
    "can_fd_architecture_validated",
    "sil_complete",
    "hil_complete",
}
EXPECTED_TECHNICAL_GATES = {
    "contract_valid",
    "doe_plan_valid",
    "case_manifest_generated",
    "selected_air_oil_architecture_locked",
    "modern_controls_contract_valid",
    "future_solver_image_available",
    "requested_target_scalar_excluded_from_fields",
    "full_target_independence_proven",
    "split_plan_generated",
}
EXPECTED_CASE_ORDER = [
    ("naturally_aspirated", "anchor"),
    ("naturally_aspirated", "morris"),
    ("naturally_aspirated", "lhs"),
    ("naturally_aspirated", "ood"),
    ("twin_turbo", "anchor"),
    ("twin_turbo", "morris"),
    ("twin_turbo", "lhs"),
    ("twin_turbo", "ood"),
]
FORBIDDEN_TARGET_TOKENS = (
    "requested_power",
    "target_power",
    "delta_to_target",
    "distance_to_1600",
    "meets_1600",
    "inverse_sizing_seed",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _load_runner():
    spec = importlib.util.spec_from_file_location("doe_917_f34", RUNNER)
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _case_group_order(cases: list[dict[str, Any]]) -> list[tuple[str, str]]:
    groups: list[tuple[str, str]] = []
    for case in cases:
        current = (case["configuration"], case["design_block"])
        if not groups or groups[-1] != current:
            groups.append(current)
    return groups


def _mapping_key_paths(value: Any, prefix: str = ""):
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else key
            yield child
            yield from _mapping_key_paths(item, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _mapping_key_paths(item, f"{prefix}[{index}]")


class Doe917F34Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_runner()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.f33_contract = json.loads(F33_CONTRACT.read_text(encoding="utf-8"))
        cls.tracked_manifest = json.loads(
            TRACKED_MANIFEST.read_text(encoding="utf-8")
        )
        cls.manifest = cls.module.build_manifest(
            cls.contract,
            contract_path=CONTRACT,
            project_root=ROOT,
        )

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
        with self.assertRaises(ValueError):
            self.module.build_manifest(
                contract,
                contract_path=CONTRACT,
                project_root=ROOT,
            )

    def test_baseline_validates_and_matches_tracked_manifest_byte_for_byte(self):
        self.assertEqual(self.validate(), [])
        self.assertEqual(self.manifest, self.tracked_manifest)
        self.assertEqual(
            TRACKED_MANIFEST.read_text(encoding="utf-8"),
            _canonical_json(self.manifest),
        )
        self.assertEqual(
            self.manifest["contract_sha256"],
            _canonical_payload_sha256(self.contract),
        )
        self.assertEqual(self.manifest["contract_file_sha256"], _sha256(CONTRACT))
        self.assertEqual(self.manifest["phase"], "F34")
        self.assertEqual(set(self.manifest["technical_gates"]), EXPECTED_TECHNICAL_GATES)
        self.assertEqual(
            self.manifest["technical_gates"],
            {
                "contract_valid": True,
                "doe_plan_valid": True,
                "case_manifest_generated": True,
                "selected_air_oil_architecture_locked": True,
                "modern_controls_contract_valid": True,
                "future_solver_image_available": False,
                "requested_target_scalar_excluded_from_fields": True,
                "full_target_independence_proven": False,
                "split_plan_generated": True,
            },
        )
        self.assertEqual(set(self.manifest["release_gates"]), EXPECTED_RELEASE_GATES)
        self.assertTrue(
            all(value is False for value in self.manifest["release_gates"].values())
        )

    def test_target_scalar_is_directly_excluded_but_inverse_seed_ancestry_remains(self):
        mutated_f33 = copy.deepcopy(self.f33_contract)
        self.assertEqual(mutated_f33["requested_power_target"]["value"], 1600.0)
        mutated_f33["requested_power_target"]["value"] = 1400.0
        _, baseline_cases = self.module._build_cases_from_f33(
            self.contract, self.f33_contract
        )
        _, scalar_only_cases = self.module._build_cases_from_f33(
            self.contract, mutated_f33
        )
        self.assertEqual(scalar_only_cases, baseline_cases)

        inverse_rebuilt = copy.deepcopy(mutated_f33)
        turbo = next(
            item
            for item in inverse_rebuilt["engine_variants"]
            if item["configuration"] == "twin_turbo"
        )
        turbo["forward_solver_input"]["manifold_pressure_pa_abs"] *= 1400.0 / 1600.0
        _, inverse_rebuilt_cases = self.module._build_cases_from_f33(
            self.contract, inverse_rebuilt
        )
        self.assertNotEqual(inverse_rebuilt_cases, baseline_cases)
        self.assertIs(
            self.manifest["technical_gates"]["full_target_independence_proven"],
            False,
        )
        self.assertIs(
            self.manifest["authority_boundary"]["inverse_sizing_seed_ancestry_present"],
            True,
        )

    def test_f34_seed_strips_head_coolant_and_locks_modern_air_oil_architecture(self):
        for variant in self.f33_contract["engine_variants"]:
            configuration = variant["configuration"]
            legacy = variant["forward_solver_input"]
            seed = self.module._f34_base_forward_input(legacy, configuration)
            thermal = seed["thermal_hypotheses"]
            self.assertNotIn("coolant_cp_j_kg_k", thermal)
            self.assertNotIn("head_coolant_delta_t_k", thermal)
            self.assertNotIn("cylinder_air_heat_fraction_of_fuel_power", thermal)
            self.assertIn("cylinder_heat_fraction_of_fuel_power", thermal)
            self.assertIn("head_heat_to_oil_fraction", thermal)
            self.assertIn("cooling_air_delta_t_k", thermal)
            architecture = seed["selected_architecture"]
            self.assertEqual(
                architecture["id"],
                "F34A-AIR-OIL-CORE-2026-CONTROLS",
            )
            self.assertIs(
                architecture["engine_core_liquid_coolant_present"], False
            )
            self.assertEqual(
                architecture["engine_core_heat_rejection"],
                ["forced_air", "dry_sump_oil"],
            )
            management = seed["engine_management"]
            self.assertTrue(management["electronic_fuel_injection_required"])
            self.assertTrue(management["sequential_port_injection_required"])
            self.assertTrue(management["staged_port_injection_candidate"])
            self.assertEqual(management["independent_injection_channels_target"], 24)
            self.assertTrue(management["dual_electronic_ignition_required"])
            self.assertEqual(
                management["independent_ignition_channels_required"], 24
            )
            self.assertTrue(management["drive_by_wire_required"])
            self.assertEqual(management["drive_by_wire_actuators_minimum"], 2)
            self.assertTrue(management["variable_cam_timing_candidate"])
            self.assertTrue(management["variable_valve_lift_candidate"])
            self.assertTrue(management["closed_loop_lambda_required"])
            self.assertTrue(
                management["cylinder_attributed_knock_control_candidate"]
            )
            self.assertIs(
                management["electronic_wastegate_control_required"],
                configuration == "twin_turbo",
            )
            self.assertTrue(management["can_fd_required"])
            self.assertFalse(management["hardware_maps_thresholds_validated"])
            self.assertFalse(management["response_model_present_in_l0"])

            self.assertIn("coolant_cp_j_kg_k", legacy["thermal_hypotheses"])
            self.assertIn("head_coolant_delta_t_k", legacy["thermal_hypotheses"])

    def test_contract_sections_reject_extra_keys(self):
        mutations: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
            ("contract", lambda value: value.__setitem__("extra", None)),
            ("parent", lambda value: value["parents"][0].__setitem__("extra", None)),
            ("authority", lambda value: value["authority_boundary"].__setitem__("extra", None)),
            ("runtime", lambda value: value["runtime"].__setitem__("extra", None)),
            ("variant", lambda value: value["variant_registry"][0].__setitem__("extra", None)),
            ("axis", lambda value: value["axis_registry"][0].__setitem__("extra", None)),
            ("constraint", lambda value: value["constraints"][0].__setitem__("extra", None)),
            ("sampling", lambda value: value["sampling_plan"].__setitem__("extra", None)),
            ("seeds", lambda value: value["sampling_plan"]["seeds"].__setitem__("extra", 1)),
            ("partition", lambda value: value["dataset_partition"].__setitem__("extra", None)),
            ("feature", lambda value: value["feature_schema"].__setitem__("extra", None)),
            ("label", lambda value: value["label_schema"][0].__setitem__("extra", None)),
            ("physicsnemo", lambda value: value["physicsnemo_discovery"].__setitem__("extra", None)),
            ("physical", lambda value: value["physical_evidence_boundary"].__setitem__("extra", None)),
            ("unknown", lambda value: value["unknown_registry"][0].__setitem__("extra", None)),
            ("technical_gates", lambda value: value["technical_gates"].__setitem__("extra", False)),
            ("release_gates", lambda value: value["release_gates"].__setitem__("extra", False)),
        ]
        for label, mutate in mutations:
            with self.subTest(section=label):
                changed = copy.deepcopy(self.contract)
                mutate(changed)
                self.assert_rejected(changed)

    def test_non_finite_numbers_are_rejected_in_memory_and_by_json_parser(self):
        for invalid in (math.nan, math.inf, -math.inf):
            with self.subTest(invalid=invalid):
                changed = copy.deepcopy(self.contract)
                changed["axis_registry"][0]["bounds"]["naturally_aspirated"][0] = invalid
                self.assert_rejected(changed, "axis_bounds_invalid")

        with tempfile.TemporaryDirectory(prefix="917-f34-non-finite-") as temporary:
            temporary_path = Path(temporary)
            for token, invalid in (("NaN", math.nan), ("Infinity", math.inf)):
                with self.subTest(token=token):
                    changed = copy.deepcopy(self.contract)
                    changed["axis_registry"][0]["bounds"]["naturally_aspirated"][0] = invalid
                    invalid_contract = temporary_path / f"contract-{token}.json"
                    invalid_contract.write_text(
                        json.dumps(changed, allow_nan=True),
                        encoding="utf-8",
                    )
                    output = temporary_path / f"manifest-{token}.json"
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(RUNNER),
                            "--contract",
                            str(invalid_contract),
                            "--output",
                            str(output),
                        ],
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("non-finite JSON constant rejected", result.stderr)
                    self.assertFalse(output.exists())

    def test_bool_wrong_type_negative_and_out_of_range_seeds_are_rejected(self):
        for invalid in (True, "9173401", 9173401.0, 0, -1, 2**63, None):
            with self.subTest(seed=invalid):
                changed = copy.deepcopy(self.contract)
                changed["sampling_plan"]["seeds"]["morris"] = invalid
                self.assert_rejected(changed, "invalid_seed:morris")

    def test_pressure_temperature_speed_and_power_units_are_closed(self):
        axis_mutations = (
            ("manifold_pressure_pa_abs", "bar"),
            ("manifold_temperature_k", "degC"),
            ("speed_rpm", "rad/s"),
        )
        for axis_id, invalid_unit in axis_mutations:
            with self.subTest(axis=axis_id, unit=invalid_unit):
                changed = copy.deepcopy(self.contract)
                axis = next(item for item in changed["axis_registry"] if item["id"] == axis_id)
                axis["unit"] = invalid_unit
                self.assert_rejected(changed, f"unit_registry_mismatch:{axis_id}")

        changed = copy.deepcopy(self.contract)
        label = next(
            item
            for item in changed["label_schema"]
            if item["id"] == "forward_predicted_mechanical_hp"
        )
        label["unit"] = "PS"
        self.assert_rejected(
            changed,
            "label_schema_mismatch:forward_predicted_mechanical_hp",
        )

    def test_axis_paths_and_transforms_are_pinned_to_f34_air_oil_schema(self):
        changed = copy.deepcopy(self.contract)
        changed["axis_registry"][0]["target_path"] = "volumetric_efficiency"
        self.assert_rejected(changed, "axis_target_path_mismatch:compression_ratio")

        changed = copy.deepcopy(self.contract)
        axis = next(
            item
            for item in changed["axis_registry"]
            if item["id"] == "fmep_coefficient_scale"
        )
        axis["transform"] = "multiply_some_other_coefficients"
        self.assert_rejected(changed, "axis_transform_mismatch:fmep_coefficient_scale")

    def test_morris_levels_and_directions_are_balanced_per_axis(self):
        expected_levels = {0.0, 0.2, 0.4, 0.6, 0.8, 1.0}
        for configuration, trajectory_count in (
            ("naturally_aspirated", 12),
            ("twin_turbo", 16),
        ):
            with self.subTest(configuration=configuration):
                axes = [
                    axis
                    for axis in self.contract["axis_registry"]
                    if configuration in axis["applies_to"]
                ]
                cases = [
                    case
                    for case in self.manifest["cases"]
                    if case["configuration"] == configuration
                    and case["design_block"] == "morris"
                ]
                groups: dict[str, list[dict[str, Any]]] = {}
                for case in cases:
                    groups.setdefault(case["design_block_id"], []).append(case)
                self.assertEqual(len(groups), trajectory_count)
                levels = [set() for _ in axes]
                positive = [0 for _ in axes]
                negative = [0 for _ in axes]
                for group in groups.values():
                    group.sort(key=lambda item: item["design_index"])
                    normalized_rows: list[list[float]] = []
                    for case in group:
                        row: list[float] = []
                        for axis, value in zip(axes, case["feature_values"], strict=True):
                            low, high = axis["bounds"][configuration]
                            normalized = round((value - low) / (high - low), 10)
                            row.append(normalized)
                        normalized_rows.append(row)
                    for row in normalized_rows:
                        for axis_index, value in enumerate(row):
                            levels[axis_index].add(value)
                    for before, after in zip(normalized_rows, normalized_rows[1:]):
                        changed_axes = [
                            index
                            for index, (left, right) in enumerate(
                                zip(before, after, strict=True)
                            )
                            if not math.isclose(left, right, abs_tol=1e-12)
                        ]
                        self.assertEqual(len(changed_axes), 1)
                        axis_index = changed_axes[0]
                        if after[axis_index] > before[axis_index]:
                            positive[axis_index] += 1
                        else:
                            negative[axis_index] += 1
                self.assertTrue(all(values == expected_levels for values in levels))
                self.assertTrue(all(count == trajectory_count // 2 for count in positive))
                self.assertTrue(all(count == trajectory_count // 2 for count in negative))

    def test_preflight_constraints_block_all_in_domain_violations(self):
        cases = self.manifest["cases"]
        in_domain = [case for case in cases if case["design_block"] != "ood"]
        self.assertTrue(
            all(not case["preflight_input_constraint_flags"] for case in in_domain)
        )
        summary = self.manifest["preflight_input_constraints"]
        self.assertEqual(summary["in_domain_violation_count"], 0)
        ood_flag_count = sum(
            len(case["preflight_input_constraint_flags"])
            for case in cases
            if case["design_block"] == "ood"
        )
        self.assertEqual(summary["ood_challenge_violation_count"], ood_flag_count)

    def test_manifest_generation_is_byte_deterministic_and_case_order_is_stable(self):
        first = self.module.build_manifest(
            self.contract,
            contract_path=CONTRACT,
            project_root=ROOT,
        )
        second = self.module.build_manifest(
            self.contract,
            contract_path=CONTRACT,
            project_root=ROOT,
        )
        self.assertEqual(_canonical_json(first), _canonical_json(second))
        self.assertEqual(first["cases"], second["cases"])
        self.assertEqual(_case_group_order(first["cases"]), EXPECTED_CASE_ORDER)

        for configuration, design_block in EXPECTED_CASE_ORDER:
            cases = [
                case
                for case in first["cases"]
                if case["configuration"] == configuration
                and case["design_block"] == design_block
            ]
            self.assertEqual(
                [case["design_index"] for case in cases],
                list(range(1, len(cases) + 1)),
                (configuration, design_block),
            )

    def test_case_counts_are_exact_for_variants_and_design_blocks(self):
        counts = self.manifest["case_counts"]
        self.assertEqual(counts["planned"], 2570)
        self.assertEqual(counts["executed"], 0)
        self.assertEqual(counts["accepted"], 0)
        self.assertEqual(counts["rejected"], 0)
        self.assertEqual(counts["by_configuration"], EXPECTED_CONFIG_COUNTS)
        self.assertEqual(counts["by_design_block"], EXPECTED_BLOCK_COUNTS)
        self.assertEqual(len(self.manifest["cases"]), 2570)
        self.assertEqual(self.manifest["execution_ledger"]["planned_not_executed"], 2570)
        self.assertEqual(self.manifest["execution_ledger"]["silent_drop_count"], 0)

    def test_case_ids_and_forward_input_hashes_are_globally_unique(self):
        cases = self.manifest["cases"]
        case_ids = [case["case_id"] for case in cases]
        input_hashes = [case["forward_input_sha256"] for case in cases]
        self.assertEqual(len(case_ids), len(set(case_ids)))
        self.assertEqual(len(input_hashes), len(set(input_hashes)))
        self.assertTrue(all(SHA256_RE.fullmatch(value) for value in input_hashes))
        self.assertTrue(all(case["training_eligible"] is False for case in cases))

    def test_lhs_splits_are_exact_disjoint_and_group_closed(self):
        lhs_cases = [
            case for case in self.manifest["cases"] if case["design_block"] == "lhs"
        ]
        self.assertEqual(len(lhs_cases), 1536)
        split_manifest = self.manifest["split_manifest"]
        self.assertEqual(split_manifest["counts"], EXPECTED_SPLIT_COUNTS)
        self.assertTrue(split_manifest["assignment_precedes_solver_execution"])
        self.assertTrue(split_manifest["applies_only_to_lhs"])
        self.assertTrue(split_manifest["group_closed"])
        self.assertEqual(split_manifest["group_count"], 96)

        for configuration, expected in EXPECTED_SPLIT_COUNTS.items():
            configuration_cases = [
                case for case in lhs_cases if case["configuration"] == configuration
            ]
            memberships = {
                role: {
                    case["case_id"]
                    for case in configuration_cases
                    if case["future_dataset_role"] == role
                }
                for role in expected
            }
            for role, count in expected.items():
                self.assertEqual(len(memberships[role]), count, (configuration, role))
            roles = list(memberships)
            for left_index, left in enumerate(roles):
                for right in roles[left_index + 1 :]:
                    self.assertTrue(
                        memberships[left].isdisjoint(memberships[right]),
                        (configuration, left, right),
                    )
            self.assertEqual(
                set().union(*memberships.values()),
                {case["case_id"] for case in configuration_cases},
            )

        group_roles: dict[tuple[str, str, str], set[str]] = {}
        group_sizes: dict[tuple[str, str, str], int] = {}
        for case in lhs_cases:
            key = (
                case["variant_id"],
                case["design_block_id"],
                case["solver_campaign_id"],
            )
            group_roles.setdefault(key, set()).add(case["future_dataset_role"])
            group_sizes[key] = group_sizes.get(key, 0) + 1
        self.assertEqual(len(group_roles), 96)
        self.assertTrue(all(len(roles) == 1 for roles in group_roles.values()))
        self.assertTrue(all(size == 16 for size in group_sizes.values()))

        membership = [
            {
                "case_id": case["case_id"],
                "future_dataset_role": case["future_dataset_role"],
            }
            for case in lhs_cases
        ]
        self.assertEqual(
            split_manifest["membership_sha256"],
            _canonical_payload_sha256(membership),
        )

    def test_ood_cases_never_gain_training_membership_or_authority(self):
        ood_cases = [
            case for case in self.manifest["cases"] if case["design_block"] == "ood"
        ]
        self.assertEqual(len(ood_cases), 384)
        self.assertTrue(
            all(case["future_dataset_role"] == "ood_challenge_only" for case in ood_cases)
        )
        self.assertTrue(all(case["training_eligible"] is False for case in ood_cases))
        self.assertTrue(all(isinstance(case.get("ood_axis_id"), str) for case in ood_cases))
        self.assertIs(self.contract["sampling_plan"]["ood_challenge"]["used_for_training"], False)
        self.assertIs(self.contract["dataset_partition"]["ood_in_training"], False)
        self.assertIs(self.manifest["authority_boundary"]["training_authorized"], False)
        self.assertIs(self.manifest["release_gates"]["training_authorized"], False)

    def test_features_and_labels_exclude_target_data_and_target_mutations_fail(self):
        for schemas in self.manifest["feature_schema"].values():
            for feature in schemas:
                serialized = f"{feature['id']} {feature['unit']}".lower()
                self.assertFalse(any(token in serialized for token in FORBIDDEN_TARGET_TOKENS))
        for label in self.manifest["label_schema"]:
            serialized = f"{label['id']} {label['path']} {label['unit']}".lower()
            self.assertFalse(any(token in serialized for token in FORBIDDEN_TARGET_TOKENS))
        for case in self.manifest["cases"]:
            paths = list(_mapping_key_paths(case))
            self.assertFalse(
                any(
                    token in path.lower()
                    for path in paths
                    for token in FORBIDDEN_TARGET_TOKENS
                ),
                case["case_id"],
            )

        changed = copy.deepcopy(self.contract)
        changed["axis_registry"][0]["target_path"] = "requested_power_target.value"
        self.assert_rejected(changed, "target_leakage_forbidden")

        changed = copy.deepcopy(self.contract)
        changed["label_schema"][0]["path"] = "target_power.value"
        self.assert_rejected(changed, "target_leakage_forbidden")

    def test_missing_duplicate_bad_hash_and_unsafe_parents_are_rejected(self):
        changed = copy.deepcopy(self.contract)
        changed["parents"].pop()
        self.assert_rejected(changed, "parents_count_invalid")

        changed = copy.deepcopy(self.contract)
        changed["parents"][-1] = copy.deepcopy(changed["parents"][0])
        self.assert_rejected(changed, "parent_id_invalid_or_duplicate")
        self.assertTrue(
            any("parent_path_invalid_or_duplicate" in error for error in self.validate(changed))
        )

        changed = copy.deepcopy(self.contract)
        changed["parents"][0]["sha256"] = "0" * 64
        self.assert_rejected(changed, "parent_sha_invalid")

        changed = copy.deepcopy(self.contract)
        changed["parents"][0]["id"] = "f34a_claimed_physical_truth"
        self.assert_rejected(changed, "parent_id_invalid")

        changed = copy.deepcopy(self.contract)
        changed["parents"][0]["role"] = "validated_physical_truth_1600_hp_proven"
        self.assert_rejected(changed, "parent_role_invalid")

        for unsafe in ("../clean-sheet-cycle-thermal-f33.json", str(F33_CONTRACT)):
            with self.subTest(unsafe=unsafe):
                changed = copy.deepcopy(self.contract)
                changed["parents"][0]["path"] = unsafe
                self.assert_rejected(changed, "parent_unexpected")
                self.assertIsNone(self.module._safe_file(ROOT, unsafe))

    def test_f34a_parent_semantics_fail_closed_independently_of_file_hash(self):
        parent = json.loads(
            (ROOT / "twins/reference-917-engine/air-oil-core-controls-f34a.json")
            .read_text(encoding="utf-8")
        )

        mutations = (
            (
                "liquid_core",
                lambda value: value["engine_core_boundary"].__setitem__(
                    "core_liquid_coolant_loop_present", True
                ),
                "f34a_parent_core_liquid_boundary_invalid",
            ),
            (
                "non_sequential_injection",
                lambda value: value["controls_architecture"]["fuel_injection"].__setitem__(
                    "mode_requirement", "batch_electronic_port_injection"
                ),
                "f34a_parent_injection_invalid",
            ),
            (
                "single_ignition",
                lambda value: value["controls_architecture"]["ignition"].__setitem__(
                    "independent_channels_required", 12
                ),
                "f34a_parent_ignition_invalid",
            ),
            (
                "validated_dbw_without_evidence",
                lambda value: value["controls_architecture"]["drive_by_wire"].__setitem__(
                    "validated", True
                ),
                "f34a_parent_dbw_invalid",
            ),
            (
                "removed_vvt_candidate",
                lambda value: value["controls_architecture"]["valvetrain_control"].__setitem__(
                    "variable_cam_timing_candidate", False
                ),
                "f34a_parent_valvetrain_invalid",
            ),
            (
                "open_loop_lambda",
                lambda value: value["controls_architecture"]["lambda_control"].__setitem__(
                    "closed_loop_required", False
                ),
                "f34a_parent_lambda_control_invalid",
            ),
            (
                "removed_knock_control",
                lambda value: value["controls_architecture"].pop("knock_control"),
                "f34a_parent_knock_control_invalid",
            ),
            (
                "unsafe_wastegate_state",
                lambda value: value["controls_architecture"]["wastegates"].__setitem__(
                    "deenergized_safe_open_state_required", False
                ),
                "f34a_parent_wastegate_invalid",
            ),
            (
                "removed_can_fd",
                lambda value: value["controls_architecture"]["communications"].__setitem__(
                    "can_fd_required", False
                ),
                "f34a_parent_communications_invalid",
            ),
            (
                "coarse_cht_scope",
                lambda value: next(
                    item
                    for item in value["sensor_registry"]
                    if item["id"] == "core_metal_temperature"
                ).__setitem__("scope", "each_bank"),
                "f34a_parent_sensor_invalid:core_metal_temperature",
            ),
            (
                "opened_gate",
                lambda value: value["release_gates"].__setitem__(
                    next(iter(value["release_gates"])), True
                ),
                "f34a_parent_gates_not_fail_closed:release_gates",
            ),
        )

        for name, mutate, expected in mutations:
            with self.subTest(name=name):
                changed = copy.deepcopy(parent)
                mutate(changed)
                errors = []
                self.module._validate_f34a_decision_parent(changed, errors)
                self.assertIn(expected, errors)

    def test_all_release_technical_and_training_gates_fail_closed(self):
        for gate in sorted(EXPECTED_RELEASE_GATES):
            with self.subTest(kind="release", gate=gate):
                changed = copy.deepcopy(self.contract)
                changed["release_gates"][gate] = True
                self.assert_rejected(changed, "release_gates_must_all_be_false")

        for gate in sorted(EXPECTED_TECHNICAL_GATES):
            with self.subTest(kind="technical", gate=gate):
                changed = copy.deepcopy(self.contract)
                changed["technical_gates"][gate] = True
                self.assert_rejected(changed, "technical_gates_must_be_false_in_contract")

        training_mutations = (
            ("authority_boundary", "doe_executed"),
            ("authority_boundary", "surrogate_trained"),
            ("authority_boundary", "physicsnemo_training_authorized"),
            ("physicsnemo_discovery", "runtime_compatibility_verified"),
            ("physicsnemo_discovery", "training_executed"),
            ("physicsnemo_discovery", "training_authorized"),
        )
        for section, gate in training_mutations:
            with self.subTest(kind="training", section=section, gate=gate):
                changed = copy.deepcopy(self.contract)
                changed[section][gate] = True
                self.assert_rejected(changed)

    def test_cli_output_check_and_stale_manifest_exit_codes(self):
        with tempfile.TemporaryDirectory(prefix="917-f34-cli-") as temporary:
            temporary_path = Path(temporary)
            output = temporary_path / "generated-manifest.json"
            generated = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--contract",
                    str(CONTRACT),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(generated.returncode, 0, generated.stderr)
            self.assertEqual(output.read_bytes(), TRACKED_MANIFEST.read_bytes())

            checked = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--contract",
                    str(CONTRACT),
                    "--check",
                    str(TRACKED_MANIFEST),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)

            stale = temporary_path / "stale-manifest.json"
            stale.write_text("{}\n", encoding="utf-8")
            rejected = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--contract",
                    str(CONTRACT),
                    "--check",
                    str(stale),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("stale F34 manifest", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
