#!/usr/bin/env python3
"""Tests for the F41 flat-12 four-valve component factory contract."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "twins/reference-917-engine/component-factory-f41.json"
RUNNER_PATH = ROOT / "twins/reference-917-engine/source/build_component_factory_f41.py"
EXECUTOR_PATH = ROOT / "twins/reference-917-engine/source/execute_component_factory_f41.py"
BUNDLE_PATH = ROOT / "twins/reference-917-engine/source/build_component_factory_bundle_f41.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("component_factory_f41", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load F41 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ComponentFactoryF41ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.runner = load_runner()
        cls.executor = load_module("component_factory_f41_executor", EXECUTOR_PATH)
        cls.bundle = load_module("component_factory_f41_bundle", BUNDLE_PATH)
        cls.by_id = {item["id"]: item for item in cls.contract["families"]}

    def make_bundle_repository(self, parent: Path, *, publish: bool = True) -> Path:
        repository = parent / "repository"
        repository.mkdir()
        for relative_path in self.bundle.ALLOWLIST:
            source = ROOT / relative_path
            destination = repository / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        def git(*arguments: str, cwd: Path = repository) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                ["git", *arguments],
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True,
            )

        git("init", "--initial-branch=f41-test")
        git("config", "user.name", "F41 Test")
        git("config", "user.email", "f41-test@example.invalid")
        git("add", "--all")
        git("commit", "-m", "F41 bundle fixture")
        if publish:
            remote = parent / "remote.git"
            remote.mkdir()
            git("init", "--bare", cwd=remote)
            git("remote", "add", "origin", str(remote))
            git("push", "--set-upstream", "origin", "HEAD:refs/heads/f41-test")
        return repository

    def test_exact_flat_12_four_valve_architecture(self):
        engine = self.contract["engine"]
        self.assertEqual(engine["cylinder_count"], 12)
        self.assertEqual(engine["bank_count"], 2)
        self.assertEqual(engine["cylinders_per_bank"], 6)
        self.assertEqual(engine["valves_per_cylinder"], 4)
        self.assertEqual(engine["total_valve_count"], 48)
        self.assertIn("twenty_four_cylinder_engine", self.contract["prohibited_claims"])

    def test_mandatory_occurrence_quantities(self):
        expected = {
            "individual_cylinder": 12,
            "cylinder_head": 12,
            "connecting_rod": 12,
            "piston": 12,
            "intake_valve": 24,
            "exhaust_valve": 24,
            "spark_plug": 24,
            "camshaft": 4,
            "turbine_wheel": 2,
            "compressor_wheel": 2,
        }
        self.assertEqual({key: self.by_id[key]["quantity"] for key in expected}, expected)

    def test_families_cover_required_systems(self):
        systems = {item["system"] for item in self.contract["families"]}
        self.assertTrue({
            "structure",
            "rotating",
            "cylinder_module",
            "four_valve_head",
            "valvetrain",
            "timing",
            "lubrication",
            "air_cooling",
            "intake",
            "fuel",
            "exhaust",
            "turbocharger",
            "ignition",
            "controls",
            "electrical",
            "sealing",
            "fasteners",
            "accessory",
            "mounting",
        }.issubset(systems))

    def test_unknown_counts_remain_unexpanded(self):
        unknown = [item for item in self.contract["families"] if item["quantity"] is None]
        self.assertGreater(len(unknown), 0)
        for family in unknown:
            self.assertEqual(family["knowledge_classification"], "unknown")
            self.assertEqual(family["route"], "interface_definition_required")
            self.assertEqual(
                self.runner.expand_occurrence_ids(family, self.contract["engine"]),
                [],
            )

    def test_source_contracts_are_hash_bound(self):
        validated = self.runner.validate_contract(ROOT, self.contract)
        self.assertEqual(validated["family_count"], 138)
        self.assertEqual(validated["known_occurrence_count"], 1265)
        self.assertEqual(len(validated["source_evidence"]), 6)

    def test_four_valve_head_seed_is_planning_reference_only(self):
        seeds = self.contract["prototype_seeds"]
        self.assertEqual(seeds["f34_four_valve_head"]["families"], ["cylinder_head"])
        self.assertIsNone(seeds["f34_four_valve_head"]["execution_command"])
        self.assertIn("not_F41_generateable_or_executable", seeds["f34_four_valve_head"]["status"])
        self.assertEqual(seeds["f1_legacy_two_valve"]["families"], [])
        self.assertIn("execution_forbidden", seeds["f1_legacy_two_valve"]["status"])

    def test_outputs_cover_editable_step_3mf_stl_and_usd(self):
        output = self.contract["output_contract"]
        self.assertTrue(output["editable_master"].endswith(".py"))
        self.assertTrue(output["editable_master_alternative"].endswith(".FCStd"))
        self.assertTrue(output["neutral_cad"].endswith(".step"))
        self.assertTrue(output["prototype_mesh"].endswith(".3mf"))
        self.assertTrue(output["display_mesh"].endswith(".stl"))
        self.assertTrue(output["usd_asset"].endswith(".usd"))
        self.assertFalse(output["purchased_parts_three_mf_allowed"])

    def test_executable_factory_has_exactly_six_hash_bound_F35_seed_families(self):
        factory = self.contract["executable_factory"]
        expected = {
            "crankshaft",
            "main_bearing_pair",
            "connecting_rod",
            "piston",
            "piston_pin",
            "piston_ring",
        }
        self.assertEqual(factory["generateable_family_count"], 6)
        self.assertEqual(factory["blocked_family_count_before_new_sources"], 132)
        self.assertEqual(factory["generated_occurrence_coverage_if_successful"], 81)
        self.assertEqual(set(factory["cad_runtime"]["families"]), expected)
        self.assertEqual(set(factory["usd_runtime"]["families"]), expected)
        self.assertIn("@sha256:", factory["cad_runtime"]["image_ref"])
        self.assertIn("@sha256:", factory["usd_runtime"]["image_ref"])
        self.assertNotIn("f34_step_seed", factory)
        bound = self.contract["prototype_seeds"]["f35_rotating"]["hash_bound_inputs"]
        self.assertEqual({item["role"] for item in bound}, {"contract", "generator", "math_module"})
        for item in bound:
            source = ROOT / item["path"]
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), item["sha256"])
        self.assertFalse(factory["raw_scan_in_bundle_allowed"])

    def test_simready_order_respects_content_agents_workflow(self):
        self.assertEqual(
            self.contract["output_contract"]["simready_stage_order"],
            [
                "preflight",
                "content_agents_readiness",
                "convert_to_usd",
                "validate_usd_minimum",
                "material_assignment",
                "physics_assignment",
                "simready_conformance",
                "asset_geometry_physics_profile_validation",
            ],
        )

    def test_all_release_gates_are_false(self):
        self.assertTrue(self.contract["release_gates"])
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))

    def test_mutated_cylinder_count_fails_closed(self):
        mutated = copy.deepcopy(self.contract)
        mutated["engine"]["cylinder_count"] = 24
        with self.assertRaisesRegex(self.runner.ContractError, "exactly_12_cylinders_required"):
            self.runner.validate_contract(ROOT, mutated)

    def test_mutated_source_hash_fails_closed(self):
        mutated = copy.deepcopy(self.contract)
        mutated["source_contracts"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(self.runner.ContractError, "source_hash_mismatch"):
            self.runner.validate_contract(ROOT, mutated)

    def test_mutated_F35_generator_hash_fails_before_execution(self):
        mutated = copy.deepcopy(self.contract)
        by_role = {
            item["role"]: item
            for item in mutated["prototype_seeds"]["f35_rotating"]["hash_bound_inputs"]
        }
        by_role["generator"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(self.runner.ContractError, "F35_hash_bound_input_hash_mismatch:generator"):
            self.runner.validate_contract(ROOT, mutated)
        with self.assertRaisesRegex(self.executor.FactoryError, "F35_hash_bound_input_hash_mismatch:generator"):
            self.executor.verify_f35_hash_bound_inputs(ROOT, mutated)

    def test_mutated_release_gate_fails_closed(self):
        mutated = copy.deepcopy(self.contract)
        mutated["release_gates"]["engine_start_authorized"] = True
        with self.assertRaisesRegex(self.runner.ContractError, "all_release_gates_must_be_false"):
            self.runner.validate_contract(ROOT, mutated)

    def test_materialization_writes_plans_not_fake_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "f41"
            report = self.runner.materialize(ROOT, CONTRACT_PATH, output)
            self.assertEqual(report["status"], "passed_plan_generation_geometry_not_generated")
            self.assertEqual(report["family_count"], 138)
            self.assertEqual(report["known_occurrence_count"], 1265)
            self.assertEqual(report["family_plan_count"], 138)
            self.assertEqual(report["generated_geometry_family_count"], 0)
            self.assertEqual(report["generated_step_count"], 0)
            self.assertEqual(report["generated_3mf_count"], 0)
            self.assertEqual(report["generated_stl_count"], 0)
            self.assertEqual(report["generated_usd_count"], 0)
            bom = json.loads((output / "bom-occurrences.json").read_text(encoding="utf-8"))
            self.assertEqual(len(bom["occurrences"]), 1265)
            self.assertEqual(bom["cylinder_count"], 12)
            self.assertEqual(bom["total_valve_count"], 48)
            self.assertEqual(bom["manufacturing_released_occurrence_count"], 0)
            jobs = json.loads((output / "vast-jobs.json").read_text(encoding="utf-8"))
            self.assertFalse(jobs["large_gpu_needed_now"])
            self.assertTrue(all(job["paid_instance_launched"] is False for job in jobs["jobs"]))
            self.assertEqual(len(list((output / "family-plans").glob("*.json"))), 138)
            self.assertFalse(any(output.rglob("*.step")))
            self.assertFalse(any(output.rglob("*.3mf")))
            self.assertFalse(any(output.rglob("*.stl")))
            self.assertFalse(any(output.rglob("*.usd")))

    def test_runtime_preflight_fails_closed_without_exact_image_identity(self):
        cad = self.executor.preflight(ROOT, CONTRACT_PATH, "cad")
        usd = self.executor.preflight(ROOT, CONTRACT_PATH, "usd")
        self.assertEqual(cad["status"], "blocked")
        self.assertEqual(usd["status"], "blocked")
        self.assertIn("exact_immutable_runtime_image_ref_not_reported", cad["errors"])
        self.assertIn("exact_immutable_runtime_image_ref_not_reported", usd["errors"])
        self.assertFalse(cad["geometry_generated"])
        self.assertFalse(usd["geometry_generated"])

    def test_finalize_separates_planned_generateable_generated_and_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            cad_families = []
            usd_families = []
            for family_id in self.executor.GENERATEABLE_FAMILIES:
                family_root = output / "artifacts" / family_id
                outputs = {}
                for key, relative in (
                    ("STEP", f"step/{family_id}.step"),
                    ("STL", f"stl/{family_id}-display-only.stl"),
                    ("3MF", f"3mf/{family_id}-prototype-only.3mf"),
                ):
                    path = family_root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(f"F41-{family_id}-{key}\n".encode())
                    outputs[key] = self.executor.file_evidence(path, output)
                usd_path = family_root / "usd" / f"{family_id}.usd"
                usd_path.parent.mkdir(parents=True, exist_ok=True)
                usd_path.write_bytes(f"F41-{family_id}-USD\n".encode())
                cad_families.append({"family_id": family_id, "outputs": outputs})
                usd_families.append({
                    "family_id": family_id,
                    "outputs": {"USD": self.executor.file_evidence(usd_path, output)},
                })
            self.executor.write_json(output / "cad-execution-report.json", {
                "generated_family_count": 6,
                "family_reports": cad_families,
            })
            self.executor.write_json(output / "usd-execution-report.json", {
                "generated_family_count": 6,
                "family_reports": usd_families,
            })
            report = self.executor.finalize(ROOT, CONTRACT_PATH, output)
            self.assertEqual(report["planned_family_count"], 138)
            self.assertEqual(report["generateable_family_count"], 6)
            self.assertEqual(report["generated_family_count"], 6)
            self.assertEqual(report["blocked_family_count"], 132)
            self.assertEqual(report["generated_occurrence_coverage"], 81)
            self.assertEqual(report["generated_format_counts"], {"STEP": 6, "STL": 6, "3MF": 6, "USD": 6})
            self.assertFalse(report["engine_complete"])
            blocked = [item for item in report["family_states"] if not item["generateable"]]
            self.assertEqual(len(blocked), 132)
            self.assertTrue(all(item["state"] == "blocked_missing_measurements_or_source" for item in blocked))
            self.assertEqual(next(item for item in blocked if item["family_id"] == "cylinder_head")["outputs"], {})

    def test_public_bundle_is_deterministic_and_contains_no_raw_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            repository = self.make_bundle_repository(parent)
            first_dir = parent / "first"
            second_dir = parent / "second"
            first = self.bundle.build_bundle(repository, first_dir)
            second = self.bundle.build_bundle(repository, second_dir)
            self.assertEqual(first["archive"]["sha256"], second["archive"]["sha256"])
            self.assertFalse(first["raw_scan_included"])
            self.assertFalse(first["private_absolute_path_included"])
            self.assertFalse(first["secret_included"])
            self.assertFalse(first["binary_payload_included"])
            self.assertTrue(first["all_payload_files_utf8_text"])
            self.assertRegex(first["source_revision"], r"^[0-9a-f]{40}$")
            self.assertEqual(first["public_remote_refs"], ["refs/remotes/origin/f41-test"])
            archive = Path(first_dir) / first["archive"]["path"]
            with tarfile.open(archive, "r:gz") as bundle:
                names = bundle.getnames()
                self.assertIn("917-component-factory-f41/REMOTE_JOB.md", names)
                self.assertIn("917-component-factory-f41/BUNDLE-MANIFEST.json", names)
                self.assertFalse(any("raw-scans" in name or "/Users/" in name or ".ssh" in name for name in names))
                self.assertFalse(any(name.lower().endswith((".step", ".stl", ".3mf", ".usd", ".obj")) for name in names))
                manifest = json.load(bundle.extractfile("917-component-factory-f41/BUNDLE-MANIFEST.json"))
                self.assertEqual(manifest["schema_version"], "1.1.0")
                self.assertEqual(manifest["source_revision"], first["source_revision"])
                self.assertEqual(manifest["archive_member_count"], len(names))
                self.assertTrue(manifest["all_payload_files_utf8_text"])
                self.assertFalse(manifest["binary_payload_included"])

    def test_bundle_rejects_clean_but_unpublished_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            repository = self.make_bundle_repository(parent, publish=False)
            with self.assertRaisesRegex(self.bundle.BundleError, "git_remote_required"):
                self.bundle.build_bundle(repository, parent / "output")

    def test_bundle_rejects_dirty_or_untracked_worktree(self):
        for dirty_kind in ("tracked", "untracked"):
            with self.subTest(dirty_kind=dirty_kind), tempfile.TemporaryDirectory() as directory:
                parent = Path(directory)
                repository = self.make_bundle_repository(parent)
                if dirty_kind == "tracked":
                    path = repository / "docs/917_COMPONENT_FACTORY_F41.md"
                    path.write_text(path.read_text(encoding="utf-8") + "\nnon committed\n", encoding="utf-8")
                else:
                    (repository / "untracked.txt").write_text("not committed\n", encoding="utf-8")
                with self.assertRaisesRegex(self.bundle.BundleError, "git_worktree_must_be_clean"):
                    self.bundle.build_bundle(repository, parent / "output")

    def test_makefile_exposes_test_plan_preflight_execute_and_bundle_targets(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        for target in (
            "917-component-factory-f41-test:",
            "917-component-factory-f41-plan:",
            "917-component-factory-f41-preflight:",
            "917-component-factory-f41:",
            "917-component-factory-f41-bundle:",
        ):
            self.assertIn(target, makefile)
        orchestrator = (ROOT / "twins/reference-917-engine/source/run_component_factory_f41.sh").read_text(encoding="utf-8")
        self.assertIn("--pull never", orchestrator)
        self.assertIn("--network none", orchestrator)
        self.assertNotIn("rm -rf", orchestrator)


if __name__ == "__main__":
    unittest.main()
