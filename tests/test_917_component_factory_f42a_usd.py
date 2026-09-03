#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import tempfile
import textwrap
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "twins/reference-917-engine/component-factory-f42a-usd.json"
EXECUTOR_PATH = ROOT / "twins/reference-917-engine/source/execute_component_factory_f42a_usd.py"
WRAPPER_PATH = ROOT / "twins/reference-917-engine/source/run_component_factory_f42a_usd.sh"
IMAGE = "ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:" + "2" * 64
FAMILIES = (
    "connecting_rod",
    "crankshaft",
    "main_bearing_pair",
    "piston",
    "piston_pin",
    "piston_ring",
)


def load_executor():
    spec = importlib.util.spec_from_file_location("component_factory_f42a_usd", EXECUTOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def encoded(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class F42aFixture:
    def __init__(self, root: Path):
        self.root = root
        self.archive_root = "synthetic-f41"
        self.payloads: dict[str, bytes] = {}
        family_reports = []
        for family in FAMILIES:
            step_path = f"artifacts/{family}/step/{family}.step"
            step = f"ISO-10303-21;\nF42A-{family}\nEND-ISO-10303-21;\n".encode()
            self.payloads[step_path] = step
            report = {
                "checks": {
                    "3mf_roundtrip_shape_count": 1,
                    "3mf_roundtrip_solid_count": 1,
                    "step_roundtrip": {
                        "all_solids_positive_volume": True,
                        "bounds_size_mm": [10.0, 20.0, 30.0],
                        "manifold": True,
                        "solid_count": 1,
                        "valid": True,
                        "volume_mm3": 100.0,
                    },
                },
                "family_id": family,
                "manufacturing_released": False,
                "outputs": {
                    "STEP": {
                        "path": step_path,
                        "sha256": digest(step),
                        "size_bytes": len(step),
                    }
                },
                "runtime_image_ref": "cad-image@sha256:" + "1" * 64,
                "simulation_validated": False,
                "source_contract_sha256": "a" * 64,
                "source_generator_sha256": "b" * 64,
                "source_math_sha256": "c" * 64,
                "source_seed": "F35_rotating_917_30_turbo_5374",
                "state": "generated_research_seed_not_released",
            }
            family_reports.append(report)
            self.payloads[f"artifacts/{family}/cad-family-report.json"] = encoded(report)
        gates = {
            "all_family_counts_closed": False,
            "all_interface_dimensions_measured": False,
            "all_materials_qualified": False,
            "all_tolerances_and_clearances_released": False,
            "all_editable_cad_generated": False,
            "all_step_roundtrips_validated": False,
            "all_3mf_meshes_validated": False,
            "all_usd_assets_minimum_valid": False,
            "simready_property_assignment_complete": False,
            "assembly_interference_check_passed": False,
            "lubrication_and_cooling_validated": False,
            "combustion_and_boost_validated": False,
            "fatigue_and_rotordynamics_validated": False,
            "physical_flowbench_correlated": False,
            "physical_dyno_correlated": False,
            "professional_engineering_review_approved": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
            "installation_in_993_authorized": False,
            "performance_1600_hp_claim_authorized": False,
        }
        cad = {
            "schema_version": "1.0.0",
            "phase": "F41",
            "runtime_phase": "cad",
            "status": "passed_six_hash_bound_F35_seed_families_generated_not_released",
            "target_variant": "917_30_turbo_5374",
            "generated_family_count": 6,
            "blocked_family_count": 132,
            "generated_format_counts": {"3MF": 6, "STEP": 6, "STL": 6, "USD": 0},
            "paid_instance_launched": False,
            "release_gates": gates,
            "family_reports": family_reports,
        }
        self.payloads["cad-execution-report.json"] = encoded(cad)
        self.payloads["preflight/cad.json"] = encoded({
            "status": "passed",
            "geometry_generated": False,
            "paid_instance_launched": False,
        })
        self.payloads["logs/f35-cad-seed.log"] = encoded({
            "contract_sha256": "a" * 64,
            "physical_kinematics_ready": False,
            "manufacturing_geometry_ready": False,
            "engine_power_proven": False,
        })
        self.payloads["raw-scans/must-not-be-imported.obj"] = b"private scan sentinel\n"
        self.archive = root / "synthetic-f41.tar.gz"
        self._write_archive(self.archive)
        allowlist = []
        for path, payload in sorted(self.payloads.items()):
            if path.startswith("raw-scans/"):
                continue
            role = "step" if path.endswith(".step") else "family_report" if path.endswith("cad-family-report.json") else {
                "cad-execution-report.json": "cad_execution_report",
                "preflight/cad.json": "cad_preflight_report",
                "logs/f35-cad-seed.log": "generation_log",
            }[path]
            item = {"path": path, "role": role, "sha256": digest(payload), "size_bytes": len(payload)}
            if role in {"step", "family_report"}:
                item["family_id"] = path.split("/")[1]
            allowlist.append(item)
        self.contract = {
            "schema_version": "1.0.0",
            "phase": "F42a",
            "status": "hash_bound_f41_archive_to_minimum_usd_conversion_only",
            "source": {
                "phase": "F41",
                "run_id": self.archive_root,
                "archive_filename": f"{self.archive_root}.tar.gz",
                "archive_root": self.archive_root,
                "archive_sha256": self._file_digest(self.archive),
                "archive_size_bytes": self.archive.stat().st_size,
                "source_revision": "d" * 40,
                "imported_file_count": len(allowlist),
                "imported_size_bytes": sum(item["size_bytes"] for item in allowlist),
            },
            "runtime": {
                "image_repository": "ghcr.io/cluster2600/3dprinting993-simready-workflow",
                "image_ref": IMAGE,
                "qualification_status": "qualified_public_linux_amd64_digest",
                "platform": "linux/amd64",
                "network_required_during_job": False,
                "gpu_required": False,
                "skill_name": "omniverse-cad-to-simready",
                "preflight_targets": ["conversion", "validation"],
                "content_agents": "skipped",
                "conversion_route": "usd-convert-cad",
                "minimum_validator": "validate-usd-minimum",
            },
            "families": list(FAMILIES),
            "input_allowlist": allowlist,
            "usd_audit": {
                "expected_up_axis": "Z",
                "expected_meters_per_unit": 0.001,
                "bounds_relative_tolerance": 0.01,
                "bounds_absolute_tolerance_m": 0.0001,
                "physics_schema_count": 0,
                "material_assignment_required": False,
            },
            "output_contract": {
                "converted_family_count": 6,
                "maximum_usd_size_bytes_per_family": 268435456,
                "maximum_total_usd_size_bytes": 1073741824,
                "property_assignment_intent": "skip",
                "preview_status": "not_run_until_conversion_and_minimum_validation_pass",
                "claim": "conversion_only_minimum_openable_usd_not_simready",
            },
            "release_gates": gates,
        }
        self.contract_path = root / "contract.json"
        self.skill_root = root / "skill"
        self._write_skill()
        self.converter = root / "converter.py"
        self._executable(
            self.converter,
            r'''
            import argparse, hashlib, json
            from pathlib import Path
            p=argparse.ArgumentParser(); p.add_argument("source"); p.add_argument("output"); p.add_argument("--report"); p.add_argument("--log"); p.add_argument("--up-axis"); p.add_argument("--quiet", action="store_true"); a=p.parse_args()
            source=Path(a.source); output=Path(a.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_bytes(b"PXR-USDC synthetic")
            sha=lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            Path(a.log).write_text("synthetic conversion\n")
            Path(a.report).write_text(json.dumps({"status":"passed","errors":[],"requested_up_axis":a.up_axis.upper(),"source_stable_during_conversion":True,"atomic_output_commit":True,"output_usd":str(output),"output_sha256":sha(output),"converter":"usd-convert-cad"}))
            ''',
        )
        self.refresh_runtime_bindings()

    @staticmethod
    def _file_digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _write_archive(self, path: Path, duplicate: str | None = None) -> None:
        with tarfile.open(path, "w:gz") as archive:
            for relative, payload in sorted(self.payloads.items()):
                info = tarfile.TarInfo(f"{self.archive_root}/{relative}")
                info.size = len(payload)
                with tempfile.SpooledTemporaryFile() as stream:
                    stream.write(payload); stream.seek(0); archive.addfile(info, stream)
            if duplicate is not None:
                payload = self.payloads[duplicate]
                info = tarfile.TarInfo(f"{self.archive_root}/{duplicate}")
                info.size = len(payload)
                with tempfile.SpooledTemporaryFile() as stream:
                    stream.write(payload); stream.seek(0); archive.addfile(info, stream)

    def _executable(self, path: Path, source: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
        path.chmod(0o755)

    def _write_skill(self) -> None:
        (self.skill_root / "SKILL.md").parent.mkdir(parents=True)
        (self.skill_root / "SKILL.md").write_text("# synthetic\n")
        self._executable(
            self.skill_root / "references/preflight/scripts/preflight.py",
            r'''
            import argparse, json
            from pathlib import Path
            p=argparse.ArgumentParser(); p.add_argument("--targets"); p.add_argument("--source-asset"); p.add_argument("--output-root"); p.add_argument("--report"); p.add_argument("--markdown-report"); p.add_argument("--check-only",action="store_true"); p.add_argument("--skip-content-agents",action="store_true"); p.add_argument("--skip-deploy",action="store_true"); p.add_argument("--no-update",action="store_true"); a=p.parse_args()
            Path(a.report).write_text(json.dumps({"status":"ready","targets":a.targets.split(","),"content_agents":"skipped"})); Path(a.markdown_report).write_text("# ready\n")
            ''',
        )
        self._executable(
            self.skill_root / "references/validate-usd-minimum/scripts/run.py",
            r'''
            import argparse, json, os
            from pathlib import Path
            p=argparse.ArgumentParser(); p.add_argument("asset"); p.add_argument("--next-step"); p.add_argument("--report"); p.add_argument("--markdown-report"); a=p.parse_args()
            physics = 0
            payload={"asset_path":str(Path(a.asset).resolve()),"passed":True,"metadata":{"default_prim_path":"/Asset","up_axis":"Z","meters_per_unit":0.001,"prim_count":2,"mesh_count":1,"used_layers":[str(Path(a.asset).resolve())],"rigid_body_count":physics,"collider_count":0,"joint_count":0,"bounds":{"meters":{"size":[0.01,0.02,0.03]}}}}
            Path(a.report).write_text(json.dumps(payload)); Path(a.markdown_report).write_text("# minimum\n")
            ''',
        )
        (self.skill_root / "shared").mkdir(parents=True)
        (self.skill_root / "shared/script_utils.py").write_text("# synthetic script utils\n")
        (self.skill_root / "shared/usd_convert_cad_diagnostics.py").write_text("# synthetic diagnostics\n")

    def refresh_runtime_bindings(self) -> None:
        adapter = self.contract["runtime"]
        adapter["converter_adapter"] = {
            "path": "/opt/usd-convert-cad-preflight/convert.py",
            "sha256": self._file_digest(self.converter),
            "size_bytes": self.converter.stat().st_size,
        }
        skill_paths = (
            "SKILL.md",
            "references/preflight/scripts/preflight.py",
            "references/validate-usd-minimum/scripts/run.py",
            "shared/script_utils.py",
            "shared/usd_convert_cad_diagnostics.py",
        )
        adapter["skill_file_allowlist"] = [
            {
                "path": relative,
                "sha256": self._file_digest(self.skill_root / relative),
                "size_bytes": (self.skill_root / relative).stat().st_size,
            }
            for relative in skill_paths
        ]
        self.contract_path.write_bytes(encoded(self.contract))


class ComponentFactoryF42aUsdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.executor = load_executor()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.fixture = F42aFixture(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def test_production_contract_binds_exact_validated_archive_and_15_files(self):
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.executor.validate_contract(contract)
        self.assertEqual(contract["source"]["archive_sha256"], "59ef86584e9dfb16481b76ce79bf5739b129ddf2d3a3869f700b2dd614bd86b5")
        self.assertEqual(contract["source"]["archive_size_bytes"], 772358)
        self.assertEqual(len(contract["input_allowlist"]), 15)
        self.assertEqual(sum(item["size_bytes"] for item in contract["input_allowlist"]), 724745)
        self.assertEqual(sum(item["role"] == "step" for item in contract["input_allowlist"]), 6)
        self.assertEqual(contract["output_contract"]["maximum_usd_size_bytes_per_family"], 268435456)
        self.assertEqual(contract["runtime"]["qualification_status"], "qualified_public_linux_amd64_digest")
        self.assertEqual(
            contract["runtime"]["image_ref"],
            "ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:3d841cc578ca2da04f021e92bfbffabe53052aa49ba9c12ae2971526cd692e84",
        )
        self.assertEqual(contract["usd_audit"]["bounds_relative_tolerance"], 0.01)
        self.assertEqual(contract["usd_audit"]["bounds_absolute_tolerance_m"], 0.0001)
        self.assertFalse(any("raw-scan" in item["path"] or item["path"].endswith((".stl", ".3mf")) for item in contract["input_allowlist"]))
        self.assertTrue(all(value is False for value in contract["release_gates"].values()))

    def test_bounds_tolerances_are_finite_and_exactly_pinned(self):
        mutations = (
            ("bounds_relative_tolerance", 1.0, "bounds_relative_tolerance_must_equal_0_01"),
            ("bounds_relative_tolerance", float("nan"), "bounds_relative_tolerance_must_equal_0_01"),
            ("bounds_absolute_tolerance_m", 1.0, "bounds_absolute_tolerance_must_equal_0_0001_m"),
            ("bounds_absolute_tolerance_m", float("inf"), "bounds_absolute_tolerance_must_equal_0_0001_m"),
        )
        for field, value, message in mutations:
            with self.subTest(field=field, value=value):
                contract = json.loads(json.dumps(self.fixture.contract))
                contract["usd_audit"][field] = value
                with self.assertRaisesRegex(self.executor.F42aError, message):
                    self.executor.validate_contract(contract)

    def test_archive_inspection_ignores_non_allowlisted_scan(self):
        report = self.executor.inspect_archive(self.fixture.archive, self.executor.validate_contract(self.fixture.contract))
        self.assertEqual(report["imported_file_count"], 15)
        self.assertFalse(report["raw_scan_imported"])
        self.assertFalse(report["STL_imported"])
        self.assertTrue(all(value is False for value in report["release_gates"].values()))

    def test_production_runtime_pending_blocks_execution_before_output(self):
        output = self.root / "must-not-exist"
        pending = json.loads(json.dumps(self.fixture.contract))
        pending["runtime"]["image_ref"] = None
        pending["runtime"]["qualification_status"] = "pending_new_simready_workflow_digest"
        pending_path = self.root / "pending-contract.json"
        pending_path.write_bytes(encoded(pending))
        with self.assertRaisesRegex(self.executor.F42aError, "runtime_digest_qualification_pending"):
            self.executor.execute(
                self.fixture.archive,
                pending_path,
                self.fixture.skill_root,
                self.fixture.converter,
                output,
            )
        self.assertFalse(output.exists())

    def test_archive_byte_change_fails_closed(self):
        changed = self.root / "changed.tar.gz"
        changed.write_bytes(self.fixture.archive.read_bytes() + b"x")
        with self.assertRaisesRegex(self.executor.F42aError, "archive_size_mismatch"):
            self.executor.inspect_archive(changed, self.executor.validate_contract(self.fixture.contract))

    def test_duplicate_allowlisted_archive_member_fails_closed(self):
        duplicate = self.root / "duplicate.tar.gz"
        path = f"artifacts/{FAMILIES[0]}/step/{FAMILIES[0]}.step"
        self.fixture._write_archive(duplicate, duplicate=path)
        contract = json.loads(json.dumps(self.fixture.contract))
        contract["source"]["archive_size_bytes"] = duplicate.stat().st_size
        contract["source"]["archive_sha256"] = hashlib.sha256(duplicate.read_bytes()).hexdigest()
        with self.assertRaisesRegex(self.executor.F42aError, "duplicate_archive_member"):
            self.executor.inspect_archive(duplicate, self.executor.validate_contract(contract))

    def test_complete_conversion_only_run_produces_six_minimum_valid_usd(self):
        output = self.root / "output"
        with mock.patch.dict(
            os.environ,
            {
                "F42A_RUNTIME_IMAGE_REF": IMAGE,
                "NVIDIA_VISIBLE_DEVICES": "void",
                "CUDA_VISIBLE_DEVICES": "-1",
            },
            clear=False,
        ):
            report = self.executor.execute(
                self.fixture.archive,
                self.fixture.contract_path,
                self.fixture.skill_root,
                self.fixture.converter,
                output,
            )
        self.assertEqual(report["generated_family_count"], 6)
        self.assertEqual(report["contract_sha256"], self.fixture._file_digest(self.fixture.contract_path))
        self.assertTrue(report["six_imported_assets_minimum_valid"])
        self.assertFalse(report["all_138_families_minimum_valid"])
        self.assertEqual(report["preview_status"], "not_run_until_separate_RTX_batch")
        self.assertFalse(report["simulation_validated"])
        self.assertFalse(report["manufacturing_authorized"])
        self.assertTrue(all(value is False for value in report["release_gates"].values()))
        self.assertEqual(len(list((output / "pipeline/01_conversion").glob("*/*.usd"))), 6)
        self.assertEqual(len(list((output / "pipeline/02_minimum").glob("*/validate-usd-minimum.json"))), 6)
        self.assertEqual(len(list((output / "pipeline/03_audit").glob("*/f42a-usd-family-audit.json"))), 6)
        imported_scan = output / "input" / self.fixture.archive_root / "raw-scans/must-not-be-imported.obj"
        self.assertFalse(imported_scan.exists())
        imported_step = output / "input" / self.fixture.archive_root / f"artifacts/{FAMILIES[0]}/step/{FAMILIES[0]}.step"
        self.assertEqual(stat.S_IMODE(imported_step.stat().st_mode), 0o444)
        conversion_report = json.loads(
            (output / "pipeline/01_conversion" / FAMILIES[0] / "conversion.json").read_text()
        )
        self.assertEqual(conversion_report["converter_execution"], "image_packaged_compatibility_adapter")
        self.assertEqual(conversion_report["converter_adapter_sha256"], self.fixture._file_digest(self.fixture.converter))
        self.assertNotIn("converter_skill", conversion_report)

    def test_runtime_image_identity_is_mandatory(self):
        with mock.patch.dict(
            os.environ,
            {
                "F42A_RUNTIME_IMAGE_REF": "wrong",
                "NVIDIA_VISIBLE_DEVICES": "void",
                "CUDA_VISIBLE_DEVICES": "-1",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(self.executor.F42aError, "exact_immutable"):
                self.executor.execute(
                    self.fixture.archive,
                    self.fixture.contract_path,
                    self.fixture.skill_root,
                    self.fixture.converter,
                    self.root / "output",
                )

    def test_CPU_only_device_mask_is_mandatory_before_output(self):
        masks = (
            ({"NVIDIA_VISIBLE_DEVICES": "all", "CUDA_VISIBLE_DEVICES": "-1"}),
            ({"NVIDIA_VISIBLE_DEVICES": "void", "CUDA_VISIBLE_DEVICES": "0"}),
            ({"NVIDIA_VISIBLE_DEVICES": "", "CUDA_VISIBLE_DEVICES": ""}),
        )
        for index, mask in enumerate(masks):
            with self.subTest(mask=mask):
                output = self.root / f"masked-output-{index}"
                environment = {"F42A_RUNTIME_IMAGE_REF": IMAGE, **mask}
                with mock.patch.dict(os.environ, environment, clear=True):
                    with self.assertRaisesRegex(
                        self.executor.F42aError,
                        "F42a_CPU_only_device_mask_not_enforced",
                    ):
                        self.executor.execute(
                            self.fixture.archive,
                            self.fixture.contract_path,
                            self.fixture.skill_root,
                            self.fixture.converter,
                            output,
                        )
                self.assertFalse(output.exists())

    def test_physics_found_by_minimum_validator_blocks_F42a(self):
        validator = self.fixture.skill_root / "references/validate-usd-minimum/scripts/run.py"
        validator.write_text(validator.read_text().replace("physics = 0", "physics = 1"))
        self.fixture.refresh_runtime_bindings()
        with mock.patch.dict(
            os.environ,
            {
                "F42A_RUNTIME_IMAGE_REF": IMAGE,
                "NVIDIA_VISIBLE_DEVICES": "void",
                "CUDA_VISIBLE_DEVICES": "-1",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(self.executor.F42aError, "no_rigid_bodies"):
                self.executor.execute(
                    self.fixture.archive,
                    self.fixture.contract_path,
                    self.fixture.skill_root,
                    self.fixture.converter,
                    self.root / "output",
                )

    def test_unbound_skill_change_fails_closed(self):
        skill_file = self.fixture.skill_root / "shared/script_utils.py"
        skill_file.write_text(skill_file.read_text() + "# changed\n")
        with mock.patch.dict(
            os.environ,
            {
                "F42A_RUNTIME_IMAGE_REF": IMAGE,
                "NVIDIA_VISIBLE_DEVICES": "void",
                "CUDA_VISIBLE_DEVICES": "-1",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(self.executor.F42aError, "skill_file_(size|sha256)_mismatch"):
                self.executor.execute(
                    self.fixture.archive,
                    self.fixture.contract_path,
                    self.fixture.skill_root,
                    self.fixture.converter,
                    self.root / "output",
                )

    def test_nonempty_output_is_never_overwritten(self):
        output = self.root / "output"
        output.mkdir(); (output / "sentinel").write_text("keep")
        with mock.patch.dict(
            os.environ,
            {
                "F42A_RUNTIME_IMAGE_REF": IMAGE,
                "NVIDIA_VISIBLE_DEVICES": "void",
                "CUDA_VISIBLE_DEVICES": "-1",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(self.executor.F42aError, "output_root_must_be_empty"):
                self.executor.execute(
                    self.fixture.archive,
                    self.fixture.contract_path,
                    self.fixture.skill_root,
                    self.fixture.converter,
                    output,
                )
        self.assertEqual((output / "sentinel").read_text(), "keep")

    def test_cli_failure_never_adds_error_report_to_existing_output(self):
        output = self.root / "output"
        output.mkdir()
        sentinel = output / "sentinel"
        sentinel.write_text("keep")
        result = self.executor.main([
            "run",
            "--archive",
            str(self.fixture.archive),
            "--contract",
            str(CONTRACT_PATH),
            "--skill-root",
            str(self.fixture.skill_root),
            "--converter-adapter",
            str(self.fixture.converter),
            "--output",
            str(output),
        ])
        self.assertEqual(result, 2)
        self.assertEqual(sentinel.read_text(), "keep")
        self.assertFalse((output / "f42a-error.json").exists())

    def test_wrapper_is_CPU_only_offline_and_digest_pinned(self):
        source = WRAPPER_PATH.read_text(encoding="utf-8")
        self.assertIn("--network none --read-only", source)
        self.assertIn("--cap-drop ALL", source)
        self.assertIn("--pull never", source)
        self.assertIn("requested immutable reference absent from RepoDigests", source)
        self.assertIn("F42A_RUNTIME_IMAGE_REF", source)
        self.assertIn("NVIDIA_VISIBLE_DEVICES=void", source)
        self.assertIn("CUDA_VISIBLE_DEVICES=-1", source)
        self.assertIn("digest simready-workflow F42a encore en attente de qualification", source)
        self.assertNotIn("--gpus", source)
        self.assertNotIn("raw-scans", source)
        syntax = subprocess.run(["bash", "-n", str(WRAPPER_PATH)], check=False)
        self.assertEqual(syntax.returncode, 0)

    def test_wrapper_pending_contract_stops_before_docker(self):
        output = self.root / "must-not-exist"
        source_root = self.root / "pending-repo/twins/reference-917-engine/source"
        source_root.mkdir(parents=True)
        staged_wrapper = source_root / WRAPPER_PATH.name
        staged_wrapper.write_bytes(WRAPPER_PATH.read_bytes())
        staged_wrapper.chmod(0o755)
        staged_executor = source_root / EXECUTOR_PATH.name
        staged_executor.write_bytes(EXECUTOR_PATH.read_bytes())
        pending = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        pending["runtime"]["image_ref"] = None
        pending["runtime"]["qualification_status"] = "pending_new_simready_workflow_digest"
        staged_contract = source_root.parent / CONTRACT_PATH.name
        staged_contract.write_bytes(encoded(pending))
        completed = subprocess.run(
            [
                "bash",
                str(staged_wrapper),
                "--archive",
                str(self.fixture.archive),
                "--skill-root",
                str(self.fixture.skill_root),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("encore en attente de qualification", completed.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
