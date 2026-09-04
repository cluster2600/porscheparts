#!/usr/bin/env python3
"""Tests de la porte fail-closed PhysicsNeMo F52."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "twins/reference-917-engine/physicsnemo-readiness-f52.json"
EVIDENCE_DIR = ROOT / "twins/reference-917-engine/evidence/f52-physicsnemo-readiness"
EVIDENCE_PATH = EVIDENCE_DIR / "physicsnemo-readiness-f52.json"
VALIDATOR_PATH = ROOT / "twins/reference-917-engine/source/validate_physicsnemo_readiness_f52.py"
LOCK_PATH = ROOT / "containers/physicsnemo-cae-cu12.lock.json"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_f52", VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PhysicsNeMoReadinessF52Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        cls.validator = _load_validator()

    def test_validator_passes_while_releases_stay_closed(self) -> None:
        report = self.validator.validate(ROOT, CONTRACT_PATH, EVIDENCE_PATH)
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertTrue(report["fail_closed"])
        self.assertEqual(report["accepted_training_samples"], 0)
        self.assertFalse(report["training_authorized"])
        self.assertFalse(report["manufacturing_authorized"])
        self.assertFalse(report["engine_start_authorized"])

    def test_image_is_pinned_but_smoke_is_import_only(self) -> None:
        runtime = self.contract["runtime_pin"]
        self.assertEqual(runtime["physicsnemo_version"], "2.2.1")
        self.assertEqual(runtime["immutable_reference"], self.lock["image"]["immutable_reference"])
        self.assertTrue(runtime["image_build_and_public_pull_verified"])
        self.assertTrue(runtime["offline_import_smoke_verified"])
        self.assertFalse(runtime["gpu_runtime_verified_for_this_image"])
        execution = self.contract["execution_status"]
        self.assertTrue(execution["physicsnemo_imports_executed"])
        self.assertFalse(execution["physicsnemo_model_forward_executed"])
        self.assertFalse(execution["physicsnemo_model_executed"])
        self.assertFalse(execution["physicsnemo_training_executed"])
        self.assertFalse(execution["physicsnemo_inference_evaluation_executed"])
        self.assertEqual(execution["interpretation"], "IMPORT_SMOKE_ONLY_NOT_MODEL_EXECUTION")

    def test_lanes_are_separated_and_not_ready(self) -> None:
        lanes = self.contract["model_lanes"]
        self.assertEqual(lanes["DoMINO_CFD_CHT"]["model"], "DoMINO")
        self.assertEqual(lanes["GeoTransolver_thermomechanical"]["model"], "GeoTransolver")
        for lane in lanes.values():
            self.assertFalse(lane["dataset_ready"])
            self.assertFalse(lane["training_authorized"])
        domino = lanes["DoMINO_CFD_CHT"]
        self.assertEqual(domino["current_reference_case_count"], 12)
        self.assertTrue(domino["current_cases_are_steady_incompressible"])
        self.assertFalse(domino["current_energy_equation_available"])
        self.assertFalse(domino["current_all_cases_passed"])
        geot = lanes["GeoTransolver_thermomechanical"]
        self.assertFalse(geot["current_full_head_fields_available"])
        self.assertFalse(geot["current_hot_material_card_available"])
        self.assertFalse(geot["current_fatigue_life_available"])

    def test_artifacts_are_hashed_and_none_is_a_training_sample(self) -> None:
        inputs = self.contract["audited_inputs"]
        self.assertEqual(len(inputs), 8)
        self.assertEqual(sum(item["availability"] == "present_hash_verified" for item in inputs), 7)
        self.assertEqual(sum(item["sha256"] is None for item in inputs), 1)
        self.assertTrue(all(item["eligible_training_sample"] is False for item in inputs))
        for item in inputs:
            if item["availability"] != "present_hash_verified":
                continue
            path = ROOT / item["path"]
            self.assertTrue(path.is_file(), item["id"])
            self.assertEqual(self.validator._sha256(path), item["sha256"], item["id"])

    def test_grouped_split_prevents_leakage(self) -> None:
        split = self.contract["split_policy"]
        self.assertAlmostEqual(sum(split["fractions_after_readiness"].values()), 1.0)
        self.assertEqual(
            set(split["group_keys"]),
            {
                "geometry_family_id",
                "operating_regime_family_id",
                "solver_campaign_id",
                "physical_test_campaign_id",
            },
        )
        self.assertFalse(split["same_geometry_across_splits_allowed"])
        self.assertFalse(split["same_operating_regime_family_across_splits_allowed"])
        self.assertFalse(split["same_physical_test_campaign_across_splits_allowed"])
        self.assertTrue(split["normalization_fit_on_train_only"])
        self.assertFalse(split["model_selection_uses_test_split"])

    def test_UQ_OOD_and_runtime_abstention_are_strict(self) -> None:
        policies = self.contract["evaluation_and_guardrails"]
        metrics = policies["metric_gates"]
        self.assertLessEqual(metrics["field_relative_L2_max"], 0.05)
        self.assertGreaterEqual(policies["uncertainty_quantification"]["deep_ensemble_members_min"], 5)
        ood = policies["out_of_distribution"]
        self.assertGreaterEqual(ood["OOD_detection_AUROC_min"], 0.95)
        self.assertGreaterEqual(ood["hard_OOD_abstention_recall_min"], 0.95)
        self.assertLessEqual(ood["in_distribution_false_abstention_max"], 0.05)
        guards = set(policies["runtime_guardrails"])
        self.assertIn("abstain_on_unknown_geometry_hash", guards)
        self.assertIn("reject_mass_or_energy_conservation_violation", guards)
        self.assertIn("never_issue_manufacturing_or_engine_start_release", guards)

    def test_every_release_gate_is_false(self) -> None:
        self.assertTrue(self.contract["release_gates"])
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))
        self.assertTrue(all(value is False for value in self.evidence["release"].values()))

    def test_public_evidence_has_no_geometry_dataset_or_weights(self) -> None:
        forbidden_suffixes = (
            "*.brep",
            "*.step",
            "*.stl",
            "*.obj",
            "*.ply",
            "*.3mf",
            "*.usd",
            "*.usda",
            "*.usdc",
            "*.pt",
            "*.pth",
            "*.ckpt",
            "*.npz",
        )
        for suffix in forbidden_suffixes:
            self.assertEqual(list(EVIDENCE_DIR.glob(suffix)), [], suffix)
        self.assertFalse(self.evidence["geometry_modified"])
        self.assertFalse(self.evidence["private_geometry_published"])
        self.assertEqual(self.evidence["input_audit"]["eligible_training_samples"], 0)

    def test_validator_detects_false_training_claim(self) -> None:
        mutated = json.loads(json.dumps(self.contract))
        mutated["execution_status"]["physicsnemo_training_executed"] = True
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "contract.json"
            path.write_text(json.dumps(mutated), encoding="utf-8")
            report = self.validator.validate(ROOT, path, EVIDENCE_PATH)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("execution_claim_invalid:physicsnemo_training_executed", report["errors"])


if __name__ == "__main__":
    unittest.main()
