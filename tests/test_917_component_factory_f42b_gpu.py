"""Tests du lot GPU F42b, sans réseau, secret, USD privé ni runtime NVIDIA."""

from __future__ import annotations

import importlib.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "twins/reference-917-engine"
REMOTE = ENGINE / "remote-simready"
F42B = REMOTE / "f42b"
CONTRACT_PATH = ENGINE / "component-factory-f42b-gpu.json"
SUMMARY_PATH = ENGINE / "evidence/f42a-cpu-usd/repeatability-summary.json"
CONTROLLER = ROOT / "deploy/vast/simready"
PROFILE_DIRECTORY_PATCH = (
    CONTROLLER / "patches/nvidia-simready-profiles-directory.patch"
)

SPEC = importlib.util.spec_from_file_location("f42b_contract", F42B / "_contract.py")
assert SPEC is not None and SPEC.loader is not None
F42B_CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(F42B_CONTRACT)
SUMMARY_SPEC = importlib.util.spec_from_file_location(
    "f42b_retrieval", CONTROLLER / "_summarize_f42b_retrieval.py"
)
assert SUMMARY_SPEC is not None and SUMMARY_SPEC.loader is not None
F42B_SUMMARY = importlib.util.module_from_spec(SUMMARY_SPEC)
SUMMARY_SPEC.loader.exec_module(F42B_SUMMARY)
DESTINATION_SPEC = importlib.util.spec_from_file_location(
    "f42b_private_destination", CONTROLLER / "_private_destination.py"
)
assert DESTINATION_SPEC is not None and DESTINATION_SPEC.loader is not None
F42B_DESTINATION = importlib.util.module_from_spec(DESTINATION_SPEC)
DESTINATION_SPEC.loader.exec_module(F42B_DESTINATION)


class ComponentFactoryF42bGpuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        cls.f7 = json.loads((ENGINE / "motion-video-f7.json").read_text(encoding="utf-8"))

    def test_contrat_lie_exactement_les_six_usd_canoniques_f42a(self):
        F42B_CONTRACT.validate_contract(CONTRACT_PATH)
        source = self.contract["source_usd"]
        self.assertEqual(
            source["minimum_material_binding_policy"],
            "preserve_exact_f42a_all_purpose_mesh_bindings_then_rebind_canonical_visual_material",
        )
        expected = [
            {
                "family_id": item["family_id"],
                "filename": f"{item['family_id']}.usd",
                "sha256": item["USD_sha256"],
                "size_bytes": item["USD_size_bytes"],
                "default_prim_path": item["default_prim_path"],
            }
            for item in self.summary["repeatability"]["families"]
        ]
        self.assertEqual(source["families"], expected)
        self.assertEqual(source["exact_file_count"], 6)
        self.assertEqual(source["total_size_bytes"], 166766)
        self.assertFalse(source["private_artifacts_committed"])
        self.assertEqual(self.summary["repeatability"]["run_count"], 2)
        self.assertTrue(self.summary["repeatability"]["canonical_namespace"])
        self.assertTrue(self.summary["repeatability"]["all_six_USD_bitwise_identical"])

    def test_runtime_est_epingle_mais_exige_un_recu_live(self):
        runtime = self.contract["runtime"]
        self.assertEqual(
            runtime["image_repository"],
            "ghcr.io/cluster2600/3dprinting993-simready-local-ai",
        )
        self.assertEqual(
            runtime["qualification_status"],
            "qualified_public_linux_amd64_digest",
        )
        self.assertEqual(
            runtime["qualified_image_ref"],
            "ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:"
            "5a69a6805a275ef708e264600cb933663159a2846b069eafe0459c28e5f69699",
        )
        self.assertTrue(self.contract["release_gates"]["runtime_digest_qualified"])
        F42B_CONTRACT.validate_contract(CONTRACT_PATH, permit_pending=True)
        with self.assertRaisesRegex(
            F42B_CONTRACT.ContractError, "runtime-attestation live requise"
        ):
            F42B_CONTRACT.validate_contract(CONTRACT_PATH, permit_pending=False)

    def test_pin_runtime_ouvre_uniquement_son_gate_dedie(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract_path = root / "twins/reference-917-engine/component-factory-f42b-gpu.json"
            contract_path.parent.mkdir(parents=True)
            for relative in (
                "twins/reference-917-engine/evidence/f42a-cpu-usd/repeatability-summary.json",
                "twins/reference-917-engine/motion-video-f7.json",
                "twins/reference-917-engine/mechanical-connections-f8.json",
            ):
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, destination)
            pinned = json.loads(json.dumps(self.contract))
            pinned["runtime"]["qualified_image_ref"] = (
                "ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:"
                + "a" * 64
            )
            pinned["runtime"]["qualification_status"] = (
                "qualified_public_linux_amd64_digest"
            )
            pinned["release_gates"]["runtime_digest_qualified"] = True
            contract_path.write_text(json.dumps(pinned) + "\n", encoding="utf-8")
            with self.assertRaises(F42B_CONTRACT.ContractError):
                F42B_CONTRACT.validate_contract(contract_path, permit_pending=False)

            evidence_path = root / F42B_CONTRACT.QUALIFICATION_EVIDENCE_PATH
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            digest = "sha256:" + "a" * 64
            evidence = {
                "schema_version": "1.0.0",
                "status": "qualified_public_linux_amd64_digest",
                "image_ref": pinned["runtime"]["qualified_image_ref"],
                "image_repository": pinned["runtime"]["image_repository"],
                "manifest_digest": digest,
                "platform": "linux/amd64",
                "github_run_id": 123456,
                "github_run_url": "https://github.com/cluster2600/3dprinting993/actions/runs/123456",
                "source_revision": "b" * 40,
                "source_branch": "codex/917-f42-simready-runtime",
                "run_attempt": 1,
                "workflow_path": ".github/workflows/containers.yml",
                "workflow_git_blob": "d" * 40,
                "checks": {
                    "workflow_conclusion_success": True,
                    "public_package_visible": True,
                    "linux_amd64_manifest_verified": True,
                    "anonymous_exact_digest_pull_verified": True,
                    "runtime_smoke_verified": True,
                },
            }
            evidence_path.write_text(json.dumps(evidence) + "\n", encoding="utf-8")
            pinned["runtime"]["qualification_evidence"] = {
                "path": F42B_CONTRACT.QUALIFICATION_EVIDENCE_PATH,
                "sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
            }
            wrapper = root / F42B_CONTRACT.LAUNCHER_PIN_PATH
            wrapper.parent.mkdir(parents=True)
            wrapper.write_text(
                'SIMREADY_REVOKED_IMAGE_OLD = "ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:'
                + "c" * 64
                + '"\nSIMREADY_IMAGE = "'
                + pinned["runtime"]["qualified_image_ref"]
                + '"\n',
                encoding="utf-8",
            )
            contract_path.write_text(json.dumps(pinned) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(
                F42B_CONTRACT.ContractError, "runtime-attestation live requise"
            ):
                F42B_CONTRACT.validate_contract(contract_path, permit_pending=False)
            F42B_CONTRACT.validate_contract(contract_path, permit_pending=True)

            ghcr_wrapper = root / F42B_CONTRACT.RUNTIME_ATTESTOR_PATH
            ghcr_bytes = (ROOT / F42B_CONTRACT.RUNTIME_ATTESTOR_PATH).read_bytes()
            ghcr_wrapper.write_bytes(ghcr_bytes)
            ghcr_wrapper.chmod(0o700)
            ghcr_blob = hashlib.sha1(
                f"blob {len(ghcr_bytes)}\0".encode("ascii") + ghcr_bytes,
                usedforsecurity=False,
            ).hexdigest()
            runtime_job_id = "f42b-test"
            runtime_nonce = "e" * 32
            runtime_receipt = root / "runtime-receipt.json"
            runtime_receipt.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "status": "verified_public_runtime",
                        "image_ref": evidence["image_ref"],
                        "manifest_digest": evidence["manifest_digest"],
                        "platform": "linux/amd64",
                        "source_revision": evidence["source_revision"],
                        "source_branch": evidence["source_branch"],
                        "run_attempt": evidence["run_attempt"],
                        "workflow_path": evidence["workflow_path"],
                        "workflow_git_blob": evidence["workflow_git_blob"],
                        "github_run_id": evidence["github_run_id"],
                        "github_run_url": evidence["github_run_url"],
                        "github_job_id": 789012,
                        "github_job_url": (
                            "https://github.com/cluster2600/3dprinting993/actions/"
                            "runs/123456/job/789012"
                        ),
                        "qualification_evidence_sha256": hashlib.sha256(
                            evidence_path.read_bytes()
                        ).hexdigest(),
                        "verified_steps": {
                            "Build large local AI image from Docker store": "success",
                            "Resolve published immutable digest": "success",
                            "Verify published local AI manifest limits": "success",
                            "Verify anonymous digest pull": "success",
                            "Promote verified image": "success",
                        },
                        "attestor": {
                            "path": F42B_CONTRACT.RUNTIME_ATTESTOR_PATH,
                            "command": F42B_CONTRACT.RUNTIME_ATTESTOR_COMMAND,
                            "git_blob": ghcr_blob,
                        },
                        "invocation": {
                            "job_id": runtime_job_id,
                            "nonce": runtime_nonce,
                            "authenticity_scope": (
                                "local_live_procedural_receipt_not_cryptographic_signature"
                            ),
                        },
                        "verified_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            runtime_receipt.chmod(0o600)
            F42B_CONTRACT.validate_contract(
                contract_path,
                permit_pending=False,
                runtime_attestation_path=runtime_receipt,
                runtime_job_id=runtime_job_id,
                runtime_nonce=runtime_nonce,
            )
            with self.assertRaisesRegex(F42B_CONTRACT.ContractError, "nonce attendu"):
                F42B_CONTRACT.validate_contract(
                    contract_path,
                    permit_pending=False,
                    runtime_attestation_path=runtime_receipt,
                    runtime_job_id=runtime_job_id,
                    runtime_nonce="wrong",
                )

            pinned["release_gates"]["runtime_digest_qualified"] = False
            contract_path.write_text(json.dumps(pinned) + "\n", encoding="utf-8")
            with self.assertRaises(F42B_CONTRACT.ContractError):
                F42B_CONTRACT.validate_contract(contract_path, permit_pending=True)

            pinned["release_gates"]["runtime_digest_qualified"] = True
            pinned["release_gates"]["manufacturing_authorized"] = True
            contract_path.write_text(json.dumps(pinned) + "\n", encoding="utf-8")
            with self.assertRaises(F42B_CONTRACT.ContractError):
                F42B_CONTRACT.validate_contract(contract_path, permit_pending=True)

            pinned["release_gates"]["manufacturing_authorized"] = False
            del pinned["release_gates"]["fea_validated"]
            contract_path.write_text(json.dumps(pinned) + "\n", encoding="utf-8")
            with self.assertRaises(F42B_CONTRACT.ContractError):
                F42B_CONTRACT.validate_contract(contract_path, permit_pending=True)

    def test_materiaux_visuels_et_historiques_sont_separes(self):
        materials = self.contract["materials"]
        self.assertEqual(
            materials["visual_claim_scope"],
            "visual_hypotheses_only_not_historical_material_identification",
        )
        expected_visual = {
            "connecting_rod": "titanium",
            "crankshaft": "steel",
            "main_bearing_pair": "steel",
            "piston": "light_alloy",
            "piston_pin": "steel",
            "piston_ring": "steel",
        }
        assignments = {
            item["family_id"]: item for item in materials["assignments"]
        }
        self.assertEqual(
            {family: item["visual_material"] for family, item in assignments.items()},
            expected_visual,
        )
        for item in assignments.values():
            self.assertTrue(item["visual_source_assignment"].startswith("motion-video-f7:"))
            self.assertTrue(item["historical_material_status"])
            self.assertEqual(
                item["physics_properties"],
                {
                    "density": None,
                    "dynamic_friction": None,
                    "restitution": None,
                    "static_friction": None,
                },
            )
            self.assertEqual(len(item["physics_properties"]), 4)
            self.assertEqual(
                F42B_CONTRACT.VISUAL_PALETTE[item["visual_material"]],
                {
                    "diffuse_color": self.f7["visual_materials"]["palette"][item["visual_material"]]["color"],
                    "metallic": self.f7["visual_materials"]["palette"][item["visual_material"]]["metallic"],
                    "roughness": self.f7["visual_materials"]["palette"][item["visual_material"]]["roughness"],
                },
            )
        for family in ("main_bearing_pair", "piston_pin", "piston_ring"):
            self.assertEqual(assignments[family]["historical_material_family"], "unknown")
            self.assertEqual(assignments[family]["historical_evidence"], [])

    def test_physique_est_strictement_un_diagnostic_de_colliders_statiques(self):
        physics = self.contract["physics"]
        self.assertEqual(physics["mode"], "static_collision_diagnostics_only")
        self.assertEqual(physics["required_mesh_api"], "UsdPhysics.CollisionAPI")
        self.assertIsNone(physics["optional_mesh_api"])
        self.assertEqual(
            physics["allowed_operations"],
            ["author_static_collision_api_on_existing_mesh_prims"],
        )
        self.assertTrue(physics["geometry_must_remain_identical"])
        self.assertEqual(physics["joint_count"], 0)
        self.assertEqual(physics["rigid_body_count"], 0)
        self.assertEqual(physics["mass_property_count"], 0)
        self.assertFalse(physics["simulation_validated"])
        self.assertFalse(physics["fea_validated"])
        forbidden = set(physics["forbidden_operations"])
        for operation in (
            "author_joint_or_drive",
            "author_rigid_body_or_articulation",
            "author_mass_density_or_inertia",
            "author_force_torque_velocity_or_initial_conditions",
            "run_fea_cfd_thermal_fatigue_or_physicsnemo_simulation",
            "change_geometry_or_create_proxy_geometry",
        ):
            self.assertIn(operation, forbidden)

    def test_allowlist_physx_refuse_schemas_et_proprietes_hors_collision_statique(self):
        for schema in ("PhysicsCollisionAPI", "PhysicsMeshCollisionAPI"):
            self.assertFalse(F42B_CONTRACT.physics_schema_forbidden(schema))
        for schema in (
            "PhysxTriggerAPI",
            "PhysxContactReportAPI",
            "PhysxCollisionAPI",
            "PhysicsRigidBodyAPI",
            "MassAPI",
        ):
            self.assertTrue(F42B_CONTRACT.physics_schema_forbidden(schema))
        for name in ("physics:collisionEnabled", "physics:approximation"):
            self.assertFalse(F42B_CONTRACT.physics_property_forbidden(name))
        for name in (
            "physics:simulationOwner",
            "physxCollision:contactOffset",
            "physxCollision:restOffset",
            "physics:mass",
        ):
            self.assertTrue(F42B_CONTRACT.physics_property_forbidden(name))
        self.assertEqual(
            F42B_CONTRACT.collision_schema_flags(["PhysicsMeshCollisionAPI"]),
            (False, True),
        )
        self.assertEqual(
            F42B_CONTRACT.collision_schema_flags(
                ["PhysicsCollisionAPI", "PhysicsMeshCollisionAPI"]
            ),
            (True, True),
        )
        self.assertFalse(
            F42B_CONTRACT.physics_schema_allowed_on_prim(
                "PhysicsCollisionAPI", "Xform"
            )
        )
        self.assertFalse(
            F42B_CONTRACT.physics_property_context_valid(
                "physics:collisionEnabled",
                "Xform",
                ["PhysicsCollisionAPI"],
                "physics",
                True,
                False,
                False,
            )
        )
        self.assertFalse(
            F42B_CONTRACT.physics_property_context_valid(
                "physics:collisionEnabled", "Mesh", [], "physics", True, False, False
            )
        )
        self.assertFalse(
            F42B_CONTRACT.physics_property_context_valid(
                "physics:collisionEnabled",
                "Mesh",
                ["PhysicsCollisionAPI"],
                "physics",
                False,
                False,
                False,
            )
        )
        self.assertFalse(
            F42B_CONTRACT.physics_property_context_valid(
                "physics:approximation",
                "Mesh",
                ["PhysicsMeshCollisionAPI"],
                "physics",
                "convexHull",
                False,
                False,
            )
        )
        self.assertFalse(
            F42B_CONTRACT.physics_property_context_valid(
                "physics:collisionEnabled",
                "Mesh",
                ["PhysicsCollisionAPI"],
                "material",
                True,
                False,
                False,
            )
        )

    def test_binding_material_rejette_purpose_collection_et_prim_non_mesh(self):
        self.assertTrue(
            F42B_CONTRACT.material_binding_properties_valid(
                ["material:binding"], "Mesh", "minimum"
            )
        )
        self.assertTrue(
            F42B_CONTRACT.material_binding_properties_valid(
                ["material:binding"], "Mesh", "material"
            )
        )
        for names in (
            ["material:binding", "material:binding:preview"],
            ["material:binding:full"],
            ["material:binding:collection:look"],
        ):
            self.assertFalse(
                F42B_CONTRACT.material_binding_properties_valid(
                    names, "Mesh", "final"
                )
            )
        self.assertFalse(
            F42B_CONTRACT.material_binding_properties_valid(
                ["material:binding"], "Xform", "final"
            )
        )
        helper_source = (F42B / "_contract.py").read_text(encoding="utf-8")
        self.assertIn(
            "direct_all_purpose_material_binding_signatures(\n        source, UsdShade",
            helper_source,
        )
        self.assertIn(
            "direct_all_purpose_material_binding_signatures(\n        target, UsdShade",
            helper_source,
        )
        self.assertIn(
            "target_material_signatures == source_material_signatures", helper_source
        )
        self.assertIn("replaced_source_material_bindings", helper_source)
        self.assertEqual(helper_source.count("root_layer_authored_meshes(stage, meshes)"), 2)
        summary_source = (CONTROLLER / "_summarize_f42b_retrieval.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("bindings != source_bindings", summary_source)
        self.assertIn("source_material_binding_signatures", summary_source)
        self.assertIn("material_binding_signatures", summary_source)
        self.assertIn(
            "bindings != {path: material_path for path in meshes}", summary_source
        )
        self.assertIn(
            'material_authoring.get("replaced_source_material_binding_signatures")',
            summary_source,
        )
        self.assertEqual(
            summary_source.count("baseline de bindings différente du gate minimum"), 3
        )
        self.assertIn("all(isinstance(path, str) and path for path in meshes)", summary_source)
        self.assertNotIn('stage == "minimum" and (\n        bindings\n', summary_source)

    def test_validation_bloquee_ne_devient_jamais_needs_rerun(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            asset = root / "asset.usd"
            asset.write_bytes(b"usd")
            report_path = root / "validation.json"
            base = {
                "asset_path": str(asset.resolve()),
                "validator_skill": "simready-validate",
                "passed": False,
                "status": "BLOCKED",
                "issue_counts": {"ERROR": 0, "FAILURE": 0},
                "issues": [],
                "errors": ["CLI absente"],
            }
            report_path.write_text(json.dumps(base) + "\n", encoding="utf-8")
            with self.assertRaises(F42B_CONTRACT.ContractError):
                F42B_CONTRACT.classify_nvidia_validation(
                    report_path, asset, "simready-validate", 1
                )
            self.assertIsNone(
                F42B_SUMMARY.nvidia_validation_outcome(
                    base, str(asset.resolve()), "simready-validate"
                )
            )

            findings = {
                **base,
                "status": "FAIL",
                "issue_counts": {"ERROR": 0, "FAILURE": 1},
                "issues": [{"severity": "FAILURE", "requirement_id": "FET004"}],
                "errors": ["FET004 failed"],
            }
            report_path.write_text(json.dumps(findings) + "\n", encoding="utf-8")
            self.assertEqual(
                F42B_CONTRACT.classify_nvidia_validation(
                    report_path, asset, "simready-validate", 1
                ),
                "needs_rerun",
            )
            self.assertEqual(
                F42B_SUMMARY.nvidia_validation_outcome(
                    findings, str(asset.resolve()), "simready-validate"
                ),
                "needs_rerun",
            )
            with self.assertRaises(F42B_CONTRACT.ContractError):
                F42B_CONTRACT.classify_nvidia_validation(
                    report_path, asset, "simready-validate", 124
                )

            contradictory_pass = {
                **base,
                "passed": True,
                "status": "PASS",
                "errors": [],
                "issue_counts": {"ERROR": 1, "FAILURE": 0},
                "issues": [{"severity": "ERROR", "requirement_id": "FET004"}],
            }
            report_path.write_text(
                json.dumps(contradictory_pass) + "\n", encoding="utf-8"
            )
            with self.assertRaises(F42B_CONTRACT.ContractError):
                F42B_CONTRACT.classify_nvidia_validation(
                    report_path, asset, "simready-validate", 0
                )
            self.assertIsNone(
                F42B_SUMMARY.nvidia_validation_outcome(
                    contradictory_pass, str(asset.resolve()), "simready-validate"
                )
            )

    def test_quatre_phases_f42b_sont_isolees_et_executables(self):
        expected = {
            "phase-minimum-usd.sh",
            "phase-material.sh",
            "phase-physics.sh",
            "phase-render-preview.sh",
        }
        self.assertEqual({path.name for path in F42B.glob("phase-*.sh")}, expected)
        for path in F42B.glob("phase-*.sh"):
            text = path.read_text(encoding="utf-8")
            self.assertTrue(path.stat().st_mode & stat.S_IXUSR)
            self.assertIn("_contract.py", text)
            self.assertNotIn("docker run", text)
            self.assertNotIn("docker compose", text)

        minimum = (F42B / "phase-minimum-usd.sh").read_text(encoding="utf-8")
        material = (F42B / "phase-material.sh").read_text(encoding="utf-8")
        physics = (F42B / "phase-physics.sh").read_text(encoding="utf-8")
        render = (F42B / "phase-render-preview.sh").read_text(encoding="utf-8")
        validate_one = (REMOTE / "_validate-one.sh").read_text(encoding="utf-8")
        self.assertIn("validate-usd-minimum", minimum)
        self.assertIn("f42b-input-audit.json", minimum)
        self.assertIn("material-agent-client", material)
        self.assertIn("--no-optimize-usd", material)
        self.assertIn("physics-agent-client", physics)
        self.assertIn("f42b-physics-audit.json", physics)
        self.assertIn("simready-validate/scripts/run.py", render)
        self.assertIn("Prop-Robotics-Physx", render)
        self.assertNotIn("--validation-report", render)
        self.assertNotIn("repair-loop", render)
        self.assertNotIn("ATTEMPT_2", render)
        self.assertNotIn("phase-validate-simready.sh", render)
        self.assertIn("--fail-on-uniform", render)
        self.assertIn("turntable.py", render)
        self.assertIn("--frames 24", render)
        self.assertIn("ffmpeg", render)
        self.assertIn("drawbox=x=0:y=ih-54:w=iw:h=54", render)
        self.assertNotIn("drawbox=x=0:y=h-54:w=w:h=54", render)
        self.assertIn("source_asset_mutated_by_render", render)
        self.assertIn("classify-nvidia-validation", validate_one)
        self.assertIn("classify-nvidia-validation", render)
        self.assertIn("clone-stage", material)
        self.assertIn("agent-output", material)
        self.assertIn("author-static-collisions", physics)
        self.assertIn("agent-output", physics)

    def test_helper_refuse_un_repertoire_prive_incomplet(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "connecting_rod.usd").write_bytes(b"not-canonical")
            with self.assertRaises(F42B_CONTRACT.ContractError):
                F42B_CONTRACT.verify_input_root(self.contract, root)

    def test_validation_nvidia_est_ordonee_sans_auto_reparation(self):
        validation = self.contract["validation"]
        self.assertEqual(
            validation["order"],
            [
                "minimum-usd",
                "material-agent",
                "physics-agent",
                "conform",
                "validate-asset",
                "validate-geometry",
                "validate-physics",
                "validate-simready",
                "ovrtx-render",
            ],
        )
        self.assertEqual(
            validation["simready_validation_location"],
            "render-preview-child-validation-only",
        )
        self.assertFalse(validation["simready_auto_repair"])
        self.assertFalse(validation["fet004_rb_mb_001_auto_repair"])
        self.assertFalse(validation["fet005_gsp_001_auto_repair"])

    def test_patch_nvidia_charge_exactement_le_repertoire_des_profils(self):
        patch = PROFILE_DIRECTORY_PATCH.read_text(encoding="utf-8")
        self.assertIn(
            "--- a/references/simready-validate/scripts/run.py\n"
            "+++ b/references/simready-validate/scripts/run.py\n",
            patch,
        )
        changed_lines = [
            line
            for line in patch.splitlines()
            if line.startswith(("+", "-"))
            and not line.startswith(("+++", "---"))
        ]
        self.assertEqual(
            changed_lines,
            [
                '-        profiles = foundation_spec_root / "profiles" / "profiles.toml"',
                '+        profiles = foundation_spec_root / "profiles"',
            ],
        )
        self.assertEqual(
            sum(line.startswith("@@") for line in patch.splitlines()), 1
        )

        documentation = (ROOT / "docs/917_COMPONENT_FACTORY_F42B_GPU.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("f42b-917-20260903d", documentation)
        self.assertIn("Ne jamais modifier le skill installé", documentation)
        self.assertIn(
            'PATCHED_SKILL_ROOT="${PATCHED_SKILL_PARENT}/omniverse-cad-to-simready"',
            documentation,
        )
        self.assertIn(
            '/usr/bin/patch -N -s -p1 -d "${PATCHED_SKILL_ROOT}"',
            documentation,
        )
        self.assertIn('SKILL_ROOT="${PATCHED_SKILL_ROOT}"', documentation)

    def test_equivalence_fet001_pxr_conserve_affines_et_bounds_monde_en_metres(self):
        try:
            from pxr import Gf, Usd, UsdGeom
        except ImportError:
            self.skipTest("pxr requis pour le test comportemental FET001")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source.usda"
            target_path = root / "target.usda"
            source_stage = Usd.Stage.CreateNew(str(source_path))
            UsdGeom.SetStageMetersPerUnit(source_stage, 0.001)
            UsdGeom.SetStageUpAxis(source_stage, UsdGeom.Tokens.z)
            default = UsdGeom.Xform.Define(source_stage, "/part")
            source_stage.SetDefaultPrim(default.GetPrim())
            mesh = UsdGeom.Mesh.Define(source_stage, "/part/mesh")
            mesh.CreatePointsAttr(
                [(-20.0, -10.0, 0.0), (20.0, -10.0, 0.0), (0.0, 30.0, 5.0)]
            )
            mesh.CreateFaceVertexCountsAttr([3])
            mesh.CreateFaceVertexIndicesAttr([0, 1, 2])
            UsdGeom.Xformable(mesh).AddTranslateOp().Set(Gf.Vec3d(120.0, -30.0, 5.0))
            self.assertTrue(source_stage.GetRootLayer().Save())
            shutil.copyfile(source_path, target_path)

            target_stage = Usd.Stage.Open(str(target_path))
            target_default = UsdGeom.Xformable(target_stage.GetDefaultPrim())
            target_default.AddScaleOp(
                UsdGeom.XformOp.PrecisionDouble, "meter_normalization"
            ).Set(Gf.Vec3d(0.001, 0.001, 0.001))
            UsdGeom.SetStageMetersPerUnit(target_stage, 1.0)
            self.assertTrue(target_stage.GetRootLayer().Save())

            source_signature = F42B_CONTRACT._geometry_signature(
                Usd.Stage.Open(str(source_path))
            )
            target_signature = F42B_CONTRACT._geometry_signature(
                Usd.Stage.Open(str(target_path))
            )
            evidence = F42B_CONTRACT._geometry_equivalence(
                source_signature, target_signature
            )
            self.assertLessEqual(evidence["max_world_delta_m"], 1e-12)
            accepted = F42B_CONTRACT._validate_fet001_transform_delta(
                Usd.Stage.Open(str(source_path)),
                Usd.Stage.Open(str(target_path)),
                "/part",
                UsdGeom,
            )
            self.assertEqual(accepted["normalization_scale"], [0.001] * 3)

            target_stage = Usd.Stage.Open(str(target_path))
            UsdGeom.Xformable(target_stage.GetDefaultPrim()).SetResetXformStack(True)
            self.assertTrue(target_stage.GetRootLayer().Save())
            with self.assertRaisesRegex(
                F42B_CONTRACT.ContractError, "resetXformStack"
            ):
                F42B_CONTRACT._validate_fet001_transform_delta(
                    Usd.Stage.Open(str(source_path)),
                    Usd.Stage.Open(str(target_path)),
                    "/part",
                    UsdGeom,
                )

            target_stage = Usd.Stage.Open(str(target_path))
            UsdGeom.Xformable(target_stage.GetDefaultPrim()).SetResetXformStack(False)
            target_stage.GetDefaultPrim().GetAttribute("xformOpOrder").Set(
                [], Usd.TimeCode(1.0)
            )
            self.assertTrue(target_stage.GetRootLayer().Save())
            with self.assertRaisesRegex(
                F42B_CONTRACT.ContractError, "xformOpOrder animée"
            ):
                F42B_CONTRACT._validate_fet001_transform_delta(
                    Usd.Stage.Open(str(source_path)),
                    Usd.Stage.Open(str(target_path)),
                    "/part",
                    UsdGeom,
                )

            target_stage = Usd.Stage.Open(str(target_path))
            target_stage.GetDefaultPrim().GetAttribute("xformOpOrder").ClearAtTime(
                Usd.TimeCode(1.0)
            )
            target_stage.GetPrimAtPath("/part/mesh").GetAttribute("xformOp:translate").Set(
                Gf.Vec3d(121.0, -30.0, 5.0)
            )
            self.assertTrue(target_stage.GetRootLayer().Save())
            moved = F42B_CONTRACT._geometry_signature(target_stage)
            with self.assertRaisesRegex(F42B_CONTRACT.ContractError, "monde en mètres modifiés"):
                F42B_CONTRACT._geometry_equivalence(source_signature, moved)

    def test_pilote_chronometre_bloque_les_cinq_autres_si_projection_depassee(self):
        execution = self.contract["execution"]
        self.assertEqual(execution["pilot_family"], "connecting_rod")
        self.assertEqual(
            execution["remaining_family_order"],
            ["crankshaft", "main_bearing_pair", "piston", "piston_pin", "piston_ring"],
        )
        self.assertTrue(execution["pilot_must_include_ovrtx_render"])
        self.assertEqual(execution["max_projected_total_seconds"], 10800)
        self.assertTrue(execution["remaining_families_blocked_until_projection_passes"])

        with tempfile.TemporaryDirectory() as temporary:
            job_id = "f42b-test"
            output_root = Path(temporary) / job_id
            pilot_run = f"{job_id}-connecting_rod"

            def write_phase(
                phase: str,
                run_id: str,
                seconds: int,
                status: str = "passed",
                exit_code: int | None = None,
            ) -> Path:
                path = output_root / phase / run_id / f"phase-{phase}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                if exit_code is None:
                    exit_code = 0 if status == "passed" else 3
                path.write_text(
                    json.dumps(
                        {
                            "schema_version": "1.0.0",
                            "phase": phase,
                            "status": status,
                            "passed": status == "passed",
                            "exit_code": exit_code,
                            "started_at": "2026-09-03T00:00:00+00:00",
                            "finished_at": f"2026-09-03T00:{seconds // 60:02d}:{seconds % 60:02d}+00:00",
                            "control": {"job_id": job_id},
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                return path

            write_phase("readiness", job_id, 10)
            write_phase("preflight", job_id, 10)
            for phase in F42B_CONTRACT.TOP_LEVEL_PHASES:
                write_phase(phase, pilot_run, 60)
            passed = F42B_CONTRACT.project_runtime(CONTRACT_PATH, output_root, job_id)
            self.assertTrue(passed["passed"])
            self.assertEqual(passed["projected_total_seconds"], 20 + 6 * 8 * 60)

            write_phase("render-preview", pilot_run, 60, exit_code=1)
            with self.assertRaisesRegex(F42B_CONTRACT.ContractError, "code de sortie incoherent"):
                F42B_CONTRACT.project_runtime(CONTRACT_PATH, output_root, job_id)

            write_phase("validate-asset", pilot_run, 60, status="needs_rerun", exit_code=1)
            write_phase("render-preview", pilot_run, 60)
            with self.assertRaisesRegex(F42B_CONTRACT.ContractError, "code de sortie incoherent"):
                F42B_CONTRACT.project_runtime(CONTRACT_PATH, output_root, job_id)

            write_phase("validate-asset", pilot_run, 60, status="needs_rerun")

            write_phase("render-preview", pilot_run, 30 * 60)
            blocked = F42B_CONTRACT.project_runtime(CONTRACT_PATH, output_root, job_id)
            self.assertFalse(blocked["passed"])
            self.assertGreater(blocked["projected_total_seconds"], 10800)

    def test_transfert_et_collecte_emploient_un_profil_ferme(self):
        transfer_path = CONTROLLER / "transfer-f42b-job.sh"
        self.assertTrue(transfer_path.stat().st_mode & stat.S_IXUSR)
        transfer = transfer_path.read_text(encoding="utf-8")
        self.assertIn('WORKFLOW_PROFILE="f42b-six-usd-v1"', transfer)
        self.assertIn("--f42a-output-root", transfer)
        self.assertIn("O_NOFOLLOW", transfer)
        self.assertIn("exact path, size and SHA-256", transfer)
        self.assertIn("qualified_public_linux_amd64_digest", transfer)
        self.assertIn("runtime F42b non qualifié", transfer)
        self.assertNotIn("--runtime-attestation)", transfer)
        self.assertIn('python3 "${STAGED_GHCR_WRAPPER}" attest-simready-runtime', transfer)
        self.assertIn('"${JOB_ID}" "${RUNTIME_ATTESTATION_NONCE}"', transfer)
        self.assertIn('--runtime-job-id "${JOB_ID}" --runtime-nonce "${RUNTIME_ATTESTATION_NONCE}"', transfer)
        self.assertIn('"runtime_attestation_nonce": sys.argv[17]', transfer)
        self.assertIn("_materialize_git_snapshot.py", transfer)
        self.assertIn('cd "${STAGED_PROJECT_ROOT}"', transfer)
        self.assertNotIn('cd "${REPOSITORY_ROOT}"\n    COPYFILE_DISABLE=1 tar', transfer)
        self.assertIn("exact commit blobs", transfer)
        self.assertEqual(transfer.count("tar --no-same-owner -xf -"), 4)
        self.assertIn("wrapper GHCR approuvé différent de la source suivie", transfer)
        self.assertIn("wrapper GHCR de travail différent du blob Git", transfer)
        self.assertIn("GIT_*) unset", transfer)
        self.assertIn("compgen -v", transfer)
        self.assertIn("--runtime-attestation", transfer)
        self.assertIn("runtime-attestation.json", transfer)
        self.assertIn("deploy/openbao/openbao-ghcr", transfer)
        self.assertNotIn("raw-scans", transfer)
        for relative in (
            "f42b/_contract.py",
            "f42b/phase-minimum-usd.sh",
            "f42b/phase-material.sh",
            "f42b/phase-physics.sh",
            "f42b/phase-render-preview.sh",
        ):
            self.assertIn(relative, transfer)

        collect = (CONTROLLER / "collect-artifacts.sh").read_text(encoding="utf-8")
        destroy = (CONTROLLER / "destroy-instance.sh").read_text(encoding="utf-8")
        for text in (collect, destroy):
            self.assertIn("legacy-f10", text)
            self.assertIn("f42b-six-usd-v1", text)
        self.assertIn("_summarize_f42b_retrieval.py", collect)
        self.assertIn("--destination-root absolu hors de toute worktree Git", collect)
        self.assertIn("copy-stdin-exclusive", collect)
        self.assertIn("extract-archive", collect)
        self.assertEqual(F42B_DESTINATION.MAX_ARCHIVE_BYTES, 4 * 1024**3)
        self.assertEqual(F42B_DESTINATION.MAX_ARCHIVE_MEMBERS, 4096)
        self.assertEqual(F42B_DESTINATION.MAX_ARCHIVE_CONTENT_BYTES, 12 * 1024**3)
        self.assertEqual(F42B_DESTINATION.MAX_ARCHIVE_FILE_BYTES, 2 * 1024**3)
        expected, run_ids = F42B_SUMMARY.expected_contract("job-f42b")
        self.assertEqual(len(expected), 50)
        self.assertEqual(
            run_ids,
            {
                family: f"job-f42b-{family}"
                for family in F42B_CONTRACT.FAMILY_ORDER
            },
        )

    def test_destination_privee_refuse_worktree_et_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            private_parent = Path(temporary)
            destination = private_parent / "results"
            prepared = F42B_DESTINATION.prepare_destination(destination, ROOT)
            self.assertEqual(prepared, destination.resolve())
            self.assertEqual(stat.S_IMODE(prepared.stat().st_mode), 0o700)

            symlink = private_parent / "linked-results"
            symlink.symlink_to(prepared, target_is_directory=True)
            with self.assertRaises(F42B_DESTINATION.DestinationError):
                F42B_DESTINATION.prepare_destination(symlink, ROOT)

        with self.assertRaises(F42B_DESTINATION.DestinationError):
            F42B_DESTINATION.prepare_destination(ROOT / "work", ROOT)

        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "job.tar.gz"
            archive.write_bytes(b"not-a-tar")
            with self.assertRaisesRegex(RuntimeError, "destination privée exacte"):
                F42B_SUMMARY.summarize(ROOT, archive, "job", 1, "repo@sha256:" + "a" * 64)

    def test_destination_privee_isole_la_decouverte_git_de_l_environnement(self):
        clean_environment = {
            name: value
            for name, value in os.environ.items()
            if not name.startswith("GIT_")
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            foreign_repository = root / "foreign-repository"
            external_parent = root / "external"
            foreign_repository.mkdir()
            external_parent.mkdir()
            subprocess.run(
                ["git", "init", "--quiet", str(foreign_repository)],
                check=True,
                env=clean_environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            with mock.patch.dict(
                os.environ,
                {
                    "GIT_DIR": str(foreign_repository / ".git"),
                    "GIT_WORK_TREE": str(external_parent),
                },
            ):
                prepared = F42B_DESTINATION.prepare_destination(
                    external_parent / "results", ROOT
                )
            self.assertEqual(prepared, (external_parent / "results").resolve())

            with mock.patch.dict(
                os.environ,
                {
                    "GIT_DIR": str(root / "missing.git"),
                    "GIT_WORK_TREE": str(external_parent),
                    "GIT_CEILING_DIRECTORIES": str(foreign_repository),
                },
            ):
                with self.assertRaises(F42B_DESTINATION.DestinationError):
                    F42B_DESTINATION.prepare_destination(
                        foreign_repository / "results", ROOT
                    )

    def test_sonde_worktree_supprime_toutes_les_surcharges_git(self):
        overrides = {
            "GIT_DIR": "/tmp/untrusted.git",
            "GIT_WORK_TREE": "/tmp/untrusted-worktree",
            "GIT_COMMON_DIR": "/tmp/untrusted-common.git",
            "GIT_CEILING_DIRECTORIES": "/tmp",
            "GIT_DISCOVERY_ACROSS_FILESYSTEM": "1",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.bare",
            "GIT_CONFIG_VALUE_0": "true",
            "F42B_GIT_PROBE_TEST": "preserved",
        }
        completed = mock.Mock(returncode=0, stdout="true\n")
        with mock.patch.dict(os.environ, overrides):
            with mock.patch.object(
                F42B_DESTINATION.subprocess, "run", return_value=completed
            ) as run:
                self.assertTrue(F42B_DESTINATION._inside_git_worktree(ROOT))

        environment = run.call_args.kwargs["env"]
        self.assertFalse(any(name.startswith("GIT_") for name in environment))
        self.assertEqual(environment["F42B_GIT_PROBE_TEST"], "preserved")

    def test_audit_sdf_precede_toute_ouverture_composee(self):
        source = (F42B / "_contract.py").read_text(encoding="utf-8")
        audit_start = source.index("def _stage_audit")
        audit = source[audit_start:]
        self.assertLess(
            audit.index("_static_layer_audit(source_path"),
            audit.index("Usd.Stage.Open(str(source_path), load=Usd.Stage.LoadAll)"),
        )
        self.assertIn("asset path externe interdit", source)
        self.assertIn("arc de composition ou variant interdit", source)
        self.assertIn('"customData Material hors contrat"', source)

    def test_conformance_f42b_refuse_neutral_ou_mauvaise_version(self):
        asset = "/workspace/results/job/conform/run/output.usd"
        base = {
            "passed": True,
            "status": "PASS",
            "output_usd_path": asset,
            "profile": "Prop-Robotics-Physx",
            "profile_version": "1.0.0",
        }
        self.assertTrue(F42B_SUMMARY.conform_reference_valid(base, asset))
        for profile, version in (
            ("Prop-Robotics-Neutral", "1.0.0"),
            ("Prop-Robotics-Physx", "2.0.0"),
        ):
            candidate = {**base, "profile": profile, "profile_version": version}
            self.assertFalse(F42B_SUMMARY.conform_reference_valid(candidate, asset))

    def test_release_et_resultats_ne_survendent_rien(self):
        self.assertTrue(self.contract["release_gates"])
        self.assertTrue(self.contract["release_gates"]["runtime_digest_qualified"])
        self.assertTrue(
            all(
                value is False
                for key, value in self.contract["release_gates"].items()
                if key != "runtime_digest_qualified"
            )
        )
        render = self.contract["render"]
        self.assertEqual(render["backend"], "OVRTX")
        self.assertEqual(render["photos_from_frame_indices"], [0, 6, 12, 18])
        self.assertEqual(render["turntable"]["frames"], 24)
        self.assertFalse(render["source_asset_mutation_allowed"])


if __name__ == "__main__":
    unittest.main()
