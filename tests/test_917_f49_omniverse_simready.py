#!/usr/bin/env python3
"""Tests hors reseau du handoff Omniverse/SimReady F49."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "twins/reference-917-engine"
CONTRACT_PATH = ENGINE / "simready-head-pair-f49.json"
COMMANDS_PATH = ENGINE / "remote-simready/f49/commands.json"
TEMPLATE_PATH = ENGINE / "remote-simready/f49/input-manifest.template.json"
VALIDATOR_PATH = ENGINE / "remote-simready/f49/validate_inputs.py"
RUNTIME_AUDIT_PATH = ENGINE / "evidence/f49-simready-runtime/public-runtime-audit.json"

SPEC = importlib.util.spec_from_file_location("f49_simready_gate", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OmniverseSimreadyF49Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.commands = json.loads(COMMANDS_PATH.read_text(encoding="utf-8"))
        cls.template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        cls.audit = json.loads(RUNTIME_AUDIT_PATH.read_text(encoding="utf-8"))

    def test_contract_is_fail_closed_and_binds_future_pair(self) -> None:
        self.assertTrue(self.contract["status"].startswith("blocked_"))
        future = self.contract["geometry_authority"]["future_step_pair"]
        self.assertEqual([item["variant"] for item in future], ["2V", "4V"])
        self.assertEqual(
            [item["expected_private_path"] for item in future],
            [
                "work/917-f49-solid/917-head-2v-f49-private.step",
                "work/917-f49-solid/917-head-4v-f49-private.step",
            ],
        )
        self.assertTrue(all(item["accepted"] is False for item in future))
        self.assertTrue(all(item["accepted_sha256"] is None for item in future))
        self.assertFalse(
            self.contract["geometry_authority"]["currently_accepted_public_report_present"]
        )
        self.assertTrue(
            all(value is False for value in self.contract["current_gates"].values())
        )

    def test_f43_skin_and_current_gallery_are_byte_locked(self) -> None:
        external = self.contract["geometry_authority"]["external_skin"]
        self.assertEqual(
            external["private_step_sha256"],
            "38f8ed3071005e5f64156d8670b5a755c98599d8702ef030ff132b7a034f0f24",
        )
        self.assertTrue(external["same_exact_source_bytes_required_for_2v_and_4v"])
        self.assertFalse(external["anisotropic_scale_allowed"])
        self.assertFalse(external["synthetic_external_envelope_allowed"])
        for record in (external["public_report"], external["visible_policy"]):
            path = ROOT / record["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(file_sha256(path), record["sha256"])
        policy = json.loads((ROOT / external["visible_policy"]["path"]).read_text())
        self.assertEqual(
            policy["historical_lineages_forbidden_from_current_product_gallery"],
            ["f39", "f42"],
        )
        for image in policy["current_product_visuals"]:
            self.assertIn("/f43-scan-contour-patch/", image["path"])
            self.assertNotIn("/f39", image["path"])
            self.assertNotIn("/f42", image["path"])

    def test_public_runtime_scope_is_exact_and_does_not_claim_gpu(self) -> None:
        runtime = self.contract["runtime"]
        self.assertEqual(runtime["image_ref"], self.audit["image"]["pinned_ref"])
        self.assertEqual(self.audit["image"]["os"], "linux")
        self.assertEqual(self.audit["image"]["architecture"], "amd64")
        self.assertTrue(
            self.audit["public_registry_audit"]["exact_digest_manifest_get_succeeded"]
        )
        self.assertEqual(self.audit["github_workflow"]["conclusion"], "success")
        self.assertTrue(all(self.audit["github_workflow"]["smokes"].values()))
        self.assertFalse(self.audit["unproven"]["nvidia_gpu_visible"])
        self.assertFalse(self.audit["unproven"]["content_agents_services_healthy"])
        self.assertFalse(runtime["current_live_gpu_and_service_readiness"])
        audit_record = runtime["public_audit"]
        self.assertEqual(file_sha256(ROOT / audit_record["path"]), audit_record["sha256"])

    def test_prompts_are_hash_locked_and_forbid_geometry_or_physics_invention(self) -> None:
        assignment = self.contract["assignment"]
        for key in ("material_prompt", "physics_prompt", "material_candidate_authority"):
            record = assignment[key]
            self.assertEqual(file_sha256(ROOT / record["path"]), record["sha256"])
        material = (ROOT / assignment["material_prompt"]["path"]).read_text().lower()
        physics = (ROOT / assignment["physics_prompt"]["path"]).read_text().lower()
        self.assertIn("n'ajoute, ne deforme et ne remplace aucune geometrie", material)
        self.assertIn("n'invente aucune propriete", material)
        self.assertIn("collisions statiques", physics)
        for forbidden in ("rigid body", "masse", "inertie", "joint", "mouvement"):
            self.assertIn(forbidden, physics)
        self.assertFalse(assignment["geometry_mutation_allowed"])
        self.assertFalse(assignment["physical_properties_may_be_invented"])

    def test_atomic_stage_order_matches_nvidia_skill(self) -> None:
        command_record = self.contract["atomic_workflow"]["command_contract"]
        self.assertEqual(ROOT / command_record["path"], COMMANDS_PATH)
        self.assertEqual(file_sha256(COMMANDS_PATH), command_record["sha256"])
        stage_ids = [item["id"] for item in self.commands["stages"]]
        self.assertEqual(
            stage_ids,
            [
                "preflight",
                "content-agents-readiness",
                "identify-asset-context",
                "convert-to-usd",
                "validate-usd-minimum",
                "material-agent",
                "physics-agent",
                "simready-conform-profile",
                "omni-asset-validate",
                "omni-asset-validate-geometry",
                "omni-asset-validate-physics",
                "simready-validate",
                "conditional-fet-repair-and-rerun",
                "ovrtx-render-service",
                "consolidated-report",
            ],
        )
        self.assertLess(stage_ids.index("material-agent"), stage_ids.index("physics-agent"))
        self.assertLess(
            stage_ids.index("physics-agent"), stage_ids.index("simready-conform-profile")
        )
        self.assertLess(
            stage_ids.index("preflight"), stage_ids.index("content-agents-readiness")
        )
        self.assertLess(
            stage_ids.index("content-agents-readiness"),
            stage_ids.index("identify-asset-context"),
        )
        self.assertLess(
            stage_ids.index("simready-validate"), stage_ids.index("ovrtx-render-service")
        )
        self.assertEqual(stage_ids[-1], "consolidated-report")
        self.assertFalse(self.contract["atomic_workflow"]["single_monolithic_runner_allowed"])
        for stage in self.commands["stages"]:
            if "argv" not in stage:
                continue
            command = " ".join(stage["argv"])
            self.assertIn("${SIMREADY_SKILL_ROOT}/references/", command)
            self.assertIn("/scripts/", command)
            self.assertNotIn("f39", command.lower())
            self.assertNotIn("f42", command.lower())

    def test_template_is_rejected_before_any_nvidia_stage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="f49-simready-blocked-") as temporary:
            report = Path(temporary) / "input-gate.json"
            completed = subprocess.run(
                [
                    "python3",
                    str(VALIDATOR_PATH),
                    "--manifest",
                    str(TEMPLATE_PATH),
                    "--report",
                    str(report),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 2)
            result = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "blocked")
            self.assertFalse(result["passed"])
            self.assertTrue(result["blockers"])
            self.assertIn("do not inspect or convert", result["next_step"])

    def test_gate_can_pass_only_with_complete_pair_and_receipts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="f49-simready-ready-") as temporary:
            temp = Path(temporary)
            private_audit = temp / "private-audit.json"
            public_report = temp / "public-report.json"
            private_audit.write_text('{"status":"accepted"}\n', encoding="utf-8")
            public_report.write_text('{"status":"accepted"}\n', encoding="utf-8")
            manifest = json.loads(json.dumps(self.template))
            manifest["status"] = "ready_for_simready_input_gate"
            manifest["private_audit"] = {
                "path": str(private_audit),
                "sha256": file_sha256(private_audit),
            }
            manifest["public_report"] = {
                "path": str(public_report),
                "sha256": file_sha256(public_report),
            }
            for item in manifest["variants"]:
                expected = item["step_path"]
                step = temp / expected
                step.parent.mkdir(parents=True, exist_ok=True)
                step.write_bytes(b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n")
                item.update(
                    {
                        "step_path": str(step),
                        "step_sha256": file_sha256(step),
                        "step_bytes": step.stat().st_size,
                        "solid_candidate_accepted": True,
                        "brepcheck_exact_valid": True,
                        "bopalgo_fault_count_after_step_roundtrip": 0,
                        "solid_count": 1,
                        "shell_count": 1,
                        "free_edge_count": 0,
                        "nonmanifold_edge_count": 0,
                        "gmsh_volume_mesh_completed": True,
                        "external_face_signatures_locked_outside_openings": True,
                        "no_global_scale_transform": True,
                        "no_anisotropic_scale": True,
                        "no_synthetic_external_envelope": True,
                        "no_forbidden_lineage": True,
                    }
                )
            manifest_path = temp / "input-manifest.json"
            manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
            result = GATE.validate(CONTRACT_PATH, manifest_path)
            self.assertTrue(result["passed"], result["blockers"])
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["source_variants"], ["2V", "4V"])


if __name__ == "__main__":
    unittest.main()
