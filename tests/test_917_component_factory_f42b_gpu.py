"""Tests du lot GPU F42b, sans réseau, secret, USD privé ni runtime NVIDIA."""

from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import shutil
import stat
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "twins/reference-917-engine"
REMOTE = ENGINE / "remote-simready"
F42B = REMOTE / "f42b"
CONTRACT_PATH = ENGINE / "component-factory-f42b-gpu.json"
SUMMARY_PATH = ENGINE / "evidence/f42a-cpu-usd/repeatability-summary.json"
CONTROLLER = ROOT / "deploy/vast/simready"

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

    def test_runtime_reste_bloque_avant_digest_local_ai_qualifie(self):
        runtime = self.contract["runtime"]
        self.assertEqual(
            runtime["image_repository"],
            "ghcr.io/cluster2600/3dprinting993-simready-local-ai",
        )
        self.assertEqual(
            runtime["qualification_status"],
            "pending_public_linux_amd64_digest_qualification",
        )
        self.assertIsNone(runtime["qualified_image_ref"])
        with self.assertRaises(F42B_CONTRACT.ContractError):
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
        self.assertTrue(all(value is False for value in self.contract["release_gates"].values()))
        render = self.contract["render"]
        self.assertEqual(render["backend"], "OVRTX")
        self.assertEqual(render["photos_from_frame_indices"], [0, 6, 12, 18])
        self.assertEqual(render["turntable"]["frames"], 24)
        self.assertFalse(render["source_asset_mutation_allowed"])


if __name__ == "__main__":
    unittest.main()
