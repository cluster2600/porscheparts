import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "twins/reference-917-engine/physicsnemo-dataset-f14.json"
VALIDATOR = (
    ROOT
    / "twins/reference-917-engine/source/validate_physicsnemo_dataset_f14.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("physicsnemo_dataset_917_f14", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PhysicsNeMoDataset917F14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def evaluate_contract(self, contract: dict, samples_root: Path | None = None) -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            contract_path = Path(temp_dir) / "physicsnemo-dataset-f14.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            return self.module.evaluate(ROOT, contract_path, samples_root)

    def write_sample(self, root: Path) -> tuple[Path, dict]:
        sample_root = root / "sample-001"
        sample_root.mkdir(parents=True)
        filenames = {
            "geometry": "geometry.step",
            "mesh": "mesh.vtu",
            "solver_config": "solver.json",
            "boundary_conditions": "boundaries.json",
            "fields": "fields.vtu",
            "convergence_report": "convergence.json",
            "mesh_independence_report": "mesh-independence.json",
            "correlation_report": "correlation.json",
        }
        artifacts = []
        for role, filename in filenames.items():
            path = sample_root / filename
            payload = f"F14 fixture for {role}\n".encode()
            path.write_bytes(payload)
            artifact = {
                "role": role,
                "path": filename,
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            if role == "mesh":
                artifact["format"] = "vtu"
            artifacts.append(artifact)
        sample = {
            "schema_version": "1.0.0",
            "sample_id": "SAMPLE-917-F14-001",
            "case_id": "CASE-917-F13-004",
            "variant_id": "type_912_5_0_na",
            "geometry_family_id": "geometry-measured-a",
            "operating_point_family_id": "operating-point-a",
            "physical_test_campaign_id": "campaign-a",
            "producer": {
                "solver_name": "reference-cfd",
                "solver_version": "test-only",
                "container_digest": "sha256:" + "a" * 64,
                "source_commit": "b" * 40,
            },
            "geometry_state": copy.deepcopy(
                self.contract["sample_contract"]["required_geometry_state"]
            ),
            "verification": {
                key: True
                for key in self.contract["sample_contract"][
                    "required_verification_flags"
                ]
            },
            "rights": {"training_allowed": True},
            "authority_boundary": {
                "training_authorized": False,
                "engine_simulation_proven": False,
                "reported_1600_hp_proven": False,
                "fabrication_authorized": False,
            },
            "artifacts": artifacts,
        }
        manifest = sample_root / "sample.json"
        manifest.write_text(json.dumps(sample), encoding="utf-8")
        return manifest, sample

    def test_current_contract_passes_with_zero_samples_and_closed_gates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = self.module.evaluate(ROOT, CONTRACT, Path(temp_dir) / "absent")

        self.assertEqual(report["report_status"], "passed", report["errors"])
        self.assertEqual(report["reference_case_count"], 12)
        self.assertEqual(report["sample_files_seen"], 0)
        self.assertEqual(report["accepted_samples"], 0)
        self.assertFalse(report["dataset_ready"])
        self.assertFalse(report["training_authorized"])
        self.assertFalse(report["engine_simulation_proven"])
        self.assertFalse(report["reported_1600_hp_proven"])
        self.assertFalse(report["fabrication_authorized"])

    def test_model_and_datapipe_axes_remain_explicit_and_unselected(self):
        discovery = self.contract["live_discovery"]
        models = {item["name"]: item for item in discovery["candidate_models"]}
        datapipes = {
            item["name"]: item for item in discovery["candidate_datapipes"]
        }

        self.assertEqual(set(models), self.module.EXPECTED_MODELS)
        self.assertEqual(set(datapipes), self.module.EXPECTED_DATAPIPES)
        self.assertTrue(all(item["selection_status"] == "candidate_not_selected" for item in models.values()))
        self.assertTrue(all(item["selection_status"] == "candidate_not_selected" for item in datapipes.values()))

    def test_live_paths_are_pinned_but_runtime_compatibility_is_open(self):
        discovery = self.contract["live_discovery"]

        self.assertRegex(discovery["commit"], r"^[0-9a-f]{40}$")
        self.assertFalse(discovery["runtime_pin_compatibility_verified"])
        runtime_imports = {
            item["name"]: item["runtime_import_verified"]
            for item in discovery["candidate_models"]
        }
        self.assertEqual(
            {name for name, passed in runtime_imports.items() if passed},
            self.module.RUNTIME_VERIFIED_MODELS,
        )
        self.assertFalse(runtime_imports["Transolver"])

    def test_changed_immutable_image_reference_is_rejected(self):
        contract = copy.deepcopy(self.contract)
        contract["runtime"]["immutable_reference"] = (
            "ghcr.io/cluster2600/3dprinting993-physicsnemo-cae-cu12@sha256:"
            + "0" * 64
        )

        report = self.evaluate_contract(contract)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn("runtime_immutable_reference_mismatch", report["errors"])

    def test_training_cannot_be_authorized_by_the_contract(self):
        contract = copy.deepcopy(self.contract)
        contract["authority_boundary"]["training_authorized"] = True

        report = self.evaluate_contract(contract)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn(
            "authority_must_be_false:training_authorized", report["errors"]
        )

    def test_all_f13_cases_are_required(self):
        contract = copy.deepcopy(self.contract)
        contract["reference_cases"]["required_case_ids"].pop()

        report = self.evaluate_contract(contract)

        self.assertEqual(report["report_status"], "failed")
        self.assertIn("reference_case_ids_mismatch", report["errors"])

    def test_complete_sample_is_structurally_accepted_but_cannot_release_training(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            samples_root = Path(temp_dir) / "cases"
            self.write_sample(samples_root)

            report = self.module.evaluate(ROOT, CONTRACT, samples_root)

        self.assertEqual(report["report_status"], "passed", report["errors"])
        self.assertEqual(report["sample_files_seen"], 1)
        self.assertEqual(report["accepted_samples"], 1)
        self.assertEqual(report["rejected_samples"], 0)
        self.assertFalse(report["dataset_ready"])
        self.assertFalse(report["training_authorized"])

    def test_bad_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            samples_root = Path(temp_dir) / "cases"
            manifest, sample = self.write_sample(samples_root)
            sample["artifacts"][0]["sha256"] = "0" * 64
            manifest.write_text(json.dumps(sample), encoding="utf-8")

            report = self.module.evaluate(ROOT, CONTRACT, samples_root)

        self.assertEqual(report["report_status"], "failed")
        self.assertEqual(report["rejected_samples"], 1)
        self.assertTrue(
            any(error.startswith("sample_artifact_sha256_mismatch") for error in report["errors"])
        )

    def test_symlinked_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            samples_root = temp / "cases"
            manifest, sample = self.write_sample(samples_root)
            geometry = manifest.parent / "geometry.step"
            target = temp / "external.step"
            target.write_text("external", encoding="utf-8")
            geometry.unlink()
            geometry.symlink_to(target)
            sample["artifacts"][0]["sha256"] = hashlib.sha256(b"external").hexdigest()
            manifest.write_text(json.dumps(sample), encoding="utf-8")

            report = self.module.evaluate(ROOT, CONTRACT, samples_root)

        self.assertEqual(report["report_status"], "failed")
        self.assertTrue(
            any(error.startswith("sample_artifact_missing_or_unsafe") for error in report["errors"])
        )

    def test_raw_scan_cannot_be_solver_geometry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            samples_root = Path(temp_dir) / "cases"
            manifest, sample = self.write_sample(samples_root)
            sample["geometry_state"]["source_kind"] = "raw_scan"
            sample["geometry_state"]["raw_scan_used_as_solver_geometry"] = True
            manifest.write_text(json.dumps(sample), encoding="utf-8")

            report = self.module.evaluate(ROOT, CONTRACT, samples_root)

        self.assertEqual(report["report_status"], "failed")
        self.assertTrue(
            any(error.startswith("sample_geometry_state_invalid") for error in report["errors"])
        )

    def test_split_fractions_remain_unset_until_release_design(self):
        split = self.contract["split_policy"]

        self.assertIsNone(split["train_fraction"])
        self.assertIsNone(split["validation_fraction"])
        self.assertIsNone(split["test_fraction"])
        self.assertFalse(split["cross_split_group_leakage_allowed"])
        self.assertTrue(split["held_out_geometry_required"])
        self.assertTrue(split["held_out_operating_region_required"])
        self.assertTrue(split["out_of_distribution_suite_required"])


if __name__ == "__main__":
    unittest.main()
