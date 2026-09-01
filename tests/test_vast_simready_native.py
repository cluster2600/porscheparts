"""Tests des phases natives Vast/SimReady, sans accès réseau ni secret."""

from __future__ import annotations

import json
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
REMOTE = ROOT / "twins/reference-917-engine/remote-simready"
CONTROLLER = ROOT / "deploy/vast/simready"
DIGEST = "sha256:" + "a" * 64
IMAGE = f"ghcr.io/cluster2600/3dprinting993-simready-local-ai@{DIGEST}"
SUMMARY_SPEC = importlib.util.spec_from_file_location(
    "vast_simready_retrieval", CONTROLLER / "_summarize_retrieval.py"
)
assert SUMMARY_SPEC is not None and SUMMARY_SPEC.loader is not None
SUMMARY = importlib.util.module_from_spec(SUMMARY_SPEC)
SUMMARY_SPEC.loader.exec_module(SUMMARY)
BUNDLE_SPEC = importlib.util.spec_from_file_location(
    "vast_simready_bundle", REMOTE / "_bundle_manifest.py"
)
assert BUNDLE_SPEC is not None and BUNDLE_SPEC.loader is not None
BUNDLE = importlib.util.module_from_spec(BUNDLE_SPEC)
BUNDLE_SPEC.loader.exec_module(BUNDLE)


class PhasesNativesSimReadyTests(unittest.TestCase):
    def test_les_phases_sont_atomiques_et_sans_docker(self):
        attendues = {
            "phase-readiness.sh",
            "phase-preflight.sh",
            "phase-f1.sh",
            "phase-f2.sh",
            "phase-f3.sh",
            "phase-f10.sh",
            "phase-minimum-usd.sh",
            "phase-material.sh",
            "phase-physics.sh",
            "phase-conform.sh",
            "phase-validate-asset.sh",
            "phase-validate-geometry.sh",
            "phase-validate-physics.sh",
            "phase-validate-simready.sh",
            "phase-render-preview.sh",
        }
        presentes = {path.name for path in REMOTE.glob("phase-*.sh")}
        self.assertEqual(presentes, attendues)
        for path in REMOTE.glob("*.sh"):
            texte = path.read_text(encoding="utf-8")
            self.assertNotIn("docker run", texte)
            self.assertNotIn("docker compose", texte)
            self.assertTrue(path.stat().st_mode & stat.S_IXUSR)

    def test_l_ordre_nvidia_est_encode_dans_les_gates(self):
        material = (REMOTE / "phase-material.sh").read_text(encoding="utf-8")
        physics = (REMOTE / "phase-physics.sh").read_text(encoding="utf-8")
        conform = (REMOTE / "phase-conform.sh").read_text(encoding="utf-8")
        validation = (REMOTE / "_validate-one.sh").read_text(encoding="utf-8")
        self.assertIn("--minimum-report", material)
        self.assertIn("--asset-context-report", material)
        self.assertIn("material-agent-client", material)
        self.assertIn("propertyAssignmentIntent", material)
        self.assertIn("--material-report", physics)
        self.assertIn("--asset-context-report", physics)
        self.assertIn("require_report_input", physics)
        self.assertIn("physics-agent-client", physics)
        self.assertIn("--physics-report", conform)
        self.assertIn("simready-conform-profile", conform)
        self.assertNotIn("--pipeline-step usd-convert-cad", conform)
        self.assertIn("--previous-validation-report", validation)
        self.assertNotIn("--token", material + physics)
        self.assertIn("--preflight-report", (REMOTE / "phase-f3.sh").read_text(encoding="utf-8"))
        f2 = (REMOTE / "phase-f2.sh").read_text(encoding="utf-8")
        self.assertIn("--input-f1-report", f2)
        self.assertIn("author_kinematics_f2.py", f2)
        f10 = (REMOTE / "phase-f10.sh").read_text(encoding="utf-8")
        self.assertIn("--variant", f10)
        self.assertIn("type_912_4_5_na", f10)
        self.assertIn("917_30_turbo_5374", f10)
        self.assertIn('phase_init "f10-${SLUG}"', f10)
        self.assertIn("identify-asset-context", f10)
        self.assertIn("_asset_context.py", f10)
        repair = (REMOTE / "phase-validate-simready.sh").read_text(encoding="utf-8")
        self.assertIn("repair-loop.json", repair)
        self.assertIn("--validation-report", repair)
        self.assertIn('"max_attempts": 2', repair)
        self.assertNotIn("--pipeline-step usd-convert-cad", repair)
        self.assertIn("GSP.001 exige des points de préhension", repair)
        render = (REMOTE / "phase-render-preview.sh").read_text(encoding="utf-8")
        self.assertIn('report.get("phase") != "validate-simready"', render)
        self.assertIn("--fail-on-uniform", render)
        self.assertIn("render-media.sha256", render)
        self.assertIn("omniverse_visual_diagnostic_only", render)
        self.assertIn('"simulation_validated": False', render)
        self.assertIn("video-f7-status.json", render)
        self.assertIn("turntable.py", render)
        self.assertIn("917-engine-simready-turntable.mp4", render)
        self.assertIn("ffmpeg", render)
        self.assertNotIn("run_logged ffprobe", render)
        self.assertIn('>"${FFPROBE_REPORT}" 2>>"${PHASE_LOG}"', render)
        self.assertIn("_final_workflow_report.py", render)
        self.assertIn("omniverse-cad-to-simready-report.json", render)

    def test_readiness_prouve_cuda_sans_revendiquer_une_simulation(self):
        readiness = (REMOTE / "phase-readiness.sh").read_text(encoding="utf-8")
        for fragment in (
            "NVIDIA_SMI_BIN",
            "physicsnemo.__version__",
            'version == "2.2.0"',
            "torch.cuda.is_available()",
            "get_device_properties",
            'device="cuda"',
            "aucune simulation moteur",
        ):
            self.assertIn(fragment, readiness)
        self.assertNotIn("SIMREADY_SERVICES_BIN", readiness)
        self.assertNotIn("CURL_BIN", readiness)
        preflight = (REMOTE / "phase-preflight.sh").read_text(encoding="utf-8")
        self.assertIn("--targets validation,content-agents", preflight)
        self.assertIn("--skip-deploy", preflight)

    def test_skill_root_est_explicite_et_fail_closed(self):
        common = (REMOTE / "_common.sh").read_text(encoding="utf-8")
        self.assertIn("SIMREADY_SKILL_ROOT doit être défini explicitement", common)
        self.assertIn('SIMREADY_SKILL_ROOT}/SKILL.md', common)
        self.assertIn("SIMREADY_SKILL_ROOT différent du skill transféré et attesté", common)
        transfer = (CONTROLLER / "transfer-job.sh").read_text(encoding="utf-8")
        self.assertIn("--skill-root", transfer)
        self.assertIn('${SKILL_ROOT}/SKILL.md', transfer)

    def test_transfert_est_sur_liste_blanche_et_exclut_f8_f9(self):
        transfer = (CONTROLLER / "transfer-job.sh").read_text(encoding="utf-8")
        self.assertIn("SOURCE_FILES=(", transfer)
        self.assertIn("git -C \"${REPOSITORY_ROOT}\" ls-files --error-unmatch", transfer)
        self.assertIn("git -C \"${REPOSITORY_ROOT}\" diff --quiet", transfer)
        self.assertIn("git -C \"${REPOSITORY_ROOT}\" diff --cached --quiet", transfer)
        self.assertIn('f"{revision}:{relative}"', transfer)
        self.assertIn("working_blob", transfer)
        self.assertNotIn("find twins/reference-917-engine/remote-simready", transfer)
        self.assertNotIn("raw-scans", transfer)
        self.assertNotIn("interfaces_f8", transfer)
        self.assertNotIn("performance_envelope_0d_f9", transfer)
        self.assertNotIn("${F2_ASSET,,}", transfer)
        self.assertNotIn("${F2_SUFFIX,,}", transfer)
        self.assertNotIn("--f2-asset", transfer)
        self.assertIn("author_kinematics_f2.py", transfer)
        self.assertIn("kinematics_f2_math.py", transfer)
        self.assertIn("phase-f2.sh", transfer)
        self.assertIn("phase-f10.sh", transfer)
        self.assertIn("variant-configurations-f10.json", transfer)
        self.assertIn("_bundle_manifest.py", transfer)
        self.assertIn("src-local-917-engine-case-cylinders-scan.json", transfer)
        self.assertIn("src-porsche-newsroom-91730-1600-qualifying.json", transfer)
        self.assertIn("_asset_context.py", transfer)
        self.assertIn("_final_workflow_report.py", transfer)

    def test_collecte_separe_recuperation_et_validation(self):
        collecte = (CONTROLLER / "collect-artifacts.sh").read_text(encoding="utf-8")
        self.assertIn("_summarize_retrieval.py", collecte)
        summarize = (CONTROLLER / "_summarize_retrieval.py").read_text(encoding="utf-8")
        self.assertIn('"retrieval_complete": retrieval_complete', summarize)
        self.assertIn('"simready_validated": simready_validated', summarize)
        self.assertIn('"simulation_validated": simulation_validated', summarize)
        self.assertIn("simulation_validated = False", summarize)
        self.assertIn('"duplicate_reports":', summarize)
        self.assertIn('run_ids = {name: f"{job_id}-{name}"', summarize)

    def test_f10_fournit_deux_stages_et_les_phases_aval_sont_parametriques(self):
        manifest = json.loads(
            (ROOT / "twins/reference-917-engine/variant-configurations-f10.json").read_text(
                encoding="utf-8"
            )
        )
        detail_stages = [item["outputs"]["detail_stage"] for item in manifest["variants"]]
        self.assertEqual(len(detail_stages), 2)
        self.assertEqual(len(set(detail_stages)), 2)
        self.assertTrue(all(path.endswith("-detail-f10.usda") for path in detail_stages))
        minimum = (REMOTE / "phase-minimum-usd.sh").read_text(encoding="utf-8")
        common = (REMOTE / "_common.sh").read_text(encoding="utf-8")
        self.assertIn("--asset", minimum)
        self.assertIn("--producer-report", minimum)
        self.assertIn("--run-id", common)

    def test_ssh_du_controleur_est_borne(self):
        common = (CONTROLLER / "_controller_common.sh").read_text(encoding="utf-8")
        for option in ("ConnectTimeout=20", "ServerAliveInterval=15", "ServerAliveCountMax=4"):
            self.assertIn(option, common)
        self.assertIn('-i "${VAST_SSH_IDENTITY_FILE}"', common)
        self.assertIn("IdentitiesOnly=yes", common)
        self.assertIn("stat.S_IMODE(info.st_mode) == 0o600", common)
        check = (CONTROLLER / "check-instance.sh").read_text(encoding="utf-8")
        self.assertIn('controller_ssh "test -f /workspace/READY"', check)
        self.assertIn('"ssh_authenticated"] = passed', check)
        self.assertIn('"remote_ready"] = passed', check)
        self.assertIn("--allowed-status loading", check)
        self.assertIn('READY_TIMEOUT_SECONDS}" -le 3600', check)
        self.assertIn('[ -n "${KNOWN_HOSTS}" ]', check)
        self.assertTrue((CONTROLLER / "check-instance.sh").stat().st_mode & stat.S_IXUSR)

    def test_runbook_lance_via_le_wrapper_ghcr(self):
        runbook = (ROOT / "docs/917_VAST_SIMREADY_NATIVE.md").read_text(encoding="utf-8")
        self.assertIn('"${OPENBAO_GHCR_BIN}" launch-vast-simready-heavy "${OFFER_ID}"', runbook)
        self.assertNotIn('"${OPENBAO_VASTAI_BIN}" launch-simready-heavy', runbook)
        self.assertIn('--known-hosts "${CONTROL_ROOT}/known_hosts"', runbook)
        self.assertIn('"${OPENBAO_VASTAI_BIN}" instances | tee', runbook)
        self.assertIn('"${OPENBAO_VASTAI_BIN}" heavy-offers | tee', runbook)
        self.assertIn('offer.get("gpu") == "RTX PRO 6000 WS"', runbook)
        self.assertIn(".artifact_archive_verified == true and .retrieval_complete == true", runbook)
        self.assertIn('cmp -s deploy/openbao/openbao-vastai "${OPENBAO_VASTAI_BIN}"', runbook)
        self.assertIn("asset-context.json", runbook)
        self.assertIn("repair-loop.json", runbook)
        self.assertIn("omniverse-cad-to-simready-report.json", runbook)
        self.assertIn("trap cleanup_instance_on_exit EXIT", runbook)
        self.assertIn("collect-artifacts.sh", runbook)
        self.assertIn("NO-RETRIEVAL:${JOB_ID}:${INSTANCE_ID}:${EXPECTED_IMAGE}", runbook)
        self.assertIn("CLEANUP_ARMED=0\ntrap - EXIT INT TERM", runbook)
        self.assertLess(
            runbook.index("trap cleanup_instance_on_exit EXIT"),
            runbook.index('payload.get("singleton_verified") is not True'),
        )

    def test_prompts_obligatoires_et_attestes_avant_finalisation(self):
        transfer = (CONTROLLER / "transfer-job.sh").read_text(encoding="utf-8")
        self.assertIn("les prompts Material et Physics sont obligatoires", transfer)
        self.assertIn('"input_prompts": json.loads', transfer)
        self.assertIn('"skill_manifest_sha256"', transfer)
        self.assertIn('"skill_tree_sha256"', transfer)
        self.assertIn("REMOTE_BUNDLE_TOOL=", transfer)
        self.assertIn("verify --job-root", transfer)
        self.assertIn(
            'require_attested_prompt material "${PROMPT_FILE}"',
            (REMOTE / "phase-material.sh").read_text(encoding="utf-8"),
        )
        self.assertIn(
            'require_attested_prompt physics "${PROMPT_FILE}"',
            (REMOTE / "phase-physics.sh").read_text(encoding="utf-8"),
        )


class ManifesteBundleTests(unittest.TestCase):
    def _bundle(self, directory: Path) -> tuple[Path, Path, Path]:
        skill = directory / "omniverse-cad-to-simready"
        skill.mkdir()
        (skill / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
        (skill / "references").mkdir()
        (skill / "references/workflow.md").write_text("workflow\n", encoding="utf-8")
        job = directory / "job"
        (job / "control").mkdir(parents=True)
        (job / "vendor").mkdir()
        (job / "inputs").mkdir()
        remote_skill = job / "vendor/omniverse-cad-to-simready"
        import shutil
        shutil.copytree(skill, remote_skill)
        manifest_path = job / "control/skill-manifest.json"
        manifest = BUNDLE.create_skill_manifest(skill, manifest_path)
        material = job / "inputs/material-prompt.txt"
        physics = job / "inputs/physics-prompt.txt"
        material.write_text("matériau sourcé", encoding="utf-8")
        physics.write_text("physique sourcée", encoding="utf-8")
        prompts = {}
        for name, path in (("material", material), ("physics", physics)):
            data = path.read_bytes()
            prompts[name] = {
                "filename": path.name,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        control = job / "control/job-control.json"
        control.write_text(
            json.dumps(
                {
                    "skill_manifest_report": "skill-manifest.json",
                    "skill_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                    "skill_tree_sha256": manifest["tree_sha256"],
                    "input_prompts": prompts,
                }
            ),
            encoding="utf-8",
        )
        return skill, job, control

    def test_manifeste_deterministe_et_bundle_distant_verifie(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            skill, job, control = self._bundle(directory)
            BUNDLE.verify_bundle(job, control)
            second = directory / "second.json"
            first_payload = BUNDLE.create_skill_manifest(skill, second)
            first = json.loads((job / "control/skill-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(first_payload, first)

            (job / "inputs/material-prompt.txt").write_text("altéré", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "prompt material différent"):
                BUNDLE.verify_bundle(job, control)

    def test_skill_refuse_liens_symboliques_et_fichiers_speciaux(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            skill = directory / "omniverse-cad-to-simready"
            skill.mkdir()
            (skill / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
            (skill / "link").symlink_to(skill / "SKILL.md")
            with self.assertRaisesRegex(RuntimeError, "lien symbolique interdit"):
                BUNDLE.create_skill_manifest(skill, directory / "symlink.json")
            (skill / "link").unlink()
            os.mkfifo(skill / "fifo")
            with self.assertRaisesRegex(RuntimeError, "fichier spécial interdit"):
                BUNDLE.create_skill_manifest(skill, directory / "fifo.json")

    def test_phase_refuse_prompt_ou_skill_non_atteste(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            _skill, job, control = self._bundle(directory)
            expected_skill = job / "vendor/omniverse-cad-to-simready"
            reference = expected_skill / "references/test.py"
            reference.write_text("# référence\n", encoding="utf-8")
            other_prompt = job / "inputs/autre-prompt.txt"
            other_prompt.write_text("matériau sourcé", encoding="utf-8")
            other_skill = job / "vendor/autre-skill"
            other_skill.mkdir()
            (other_skill / "SKILL.md").write_text("# autre\n", encoding="utf-8")
            (other_skill / "references").mkdir()
            (other_skill / "references/test.py").write_text("# autre\n", encoding="utf-8")

            def bash_call(fragment: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [
                        "/bin/bash", "-c",
                        "set -euo pipefail; "
                        f". '{REMOTE / '_common.sh'}'; "
                        f"PHASE_CONTROL='{control}'; SYSTEM_PYTHON='{sys.executable}'; "
                        + fragment,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )

            accepted_prompt = bash_call(
                f"require_attested_prompt material '{job / 'inputs/material-prompt.txt'}'"
            )
            self.assertEqual(accepted_prompt.returncode, 0, accepted_prompt.stderr)
            rejected_prompt = bash_call(f"require_attested_prompt material '{other_prompt}'")
            self.assertNotEqual(rejected_prompt.returncode, 0)
            accepted_skill = bash_call(
                f"SIMREADY_SKILL_ROOT='{expected_skill}'; require_skill_reference references/test.py"
            )
            self.assertEqual(accepted_skill.returncode, 0, accepted_skill.stderr)
            rejected_skill = bash_call(
                f"SIMREADY_SKILL_ROOT='{other_skill}'; require_skill_reference references/test.py"
            )
            self.assertNotEqual(rejected_skill.returncode, 0)


class ResumeRecuperationVariantAwareTests(unittest.TestCase):
    def _write_phase(
        self,
        root: Path,
        phase_directory: str,
        run_id: str,
        phase: str,
        *,
        status: str = "passed",
        inputs: list[str] | None = None,
        outputs: list[str] | None = None,
        child_reports: list[str] | None = None,
        filename: str | None = None,
        schema_version: str = "1.0.0",
        passed: bool | None = None,
        exit_code: int | None = None,
        control: dict | None = None,
    ) -> Path:
        directory = root / phase_directory / run_id
        directory.mkdir(parents=True, exist_ok=True)
        default_filename = "phase-f10.json" if phase.startswith("f10-") else f"phase-{phase}.json"
        path = directory / (filename or default_filename)
        job_id = root.name
        for output in outputs or []:
            remote = Path(output)
            prefix = Path("/workspace/results") / job_id
            relative = remote.relative_to(prefix)
            local = root / relative
            local.parent.mkdir(parents=True, exist_ok=True)
            if not local.exists():
                local.write_bytes(f"artefact:{output}".encode("utf-8"))
        for child in child_reports or []:
            remote = Path(child)
            prefix = Path("/workspace/results") / job_id
            relative = remote.relative_to(prefix)
            local = root / relative
            local.parent.mkdir(parents=True, exist_ok=True)
            if not local.exists():
                if local.suffix == ".json":
                    local.write_text(
                        json.dumps({"schema_version": "1.0.0", "status": "passed", "passed": True}),
                        encoding="utf-8",
                    )
                else:
                    local.write_text("attestation\n", encoding="utf-8")
        expected_passed = status == "passed" if passed is None else passed
        expected_exit_code = (0 if status == "passed" else 3) if exit_code is None else exit_code
        path.write_text(
            json.dumps(
                {
                    "schema_version": schema_version,
                    "phase": phase,
                    "status": status,
                    "passed": expected_passed,
                    "exit_code": expected_exit_code,
                    "input_paths": inputs or [],
                    "output_paths": outputs or [],
                    "child_reports": child_reports or [],
                    "control": control or {
                        "job_id": job_id,
                        "instance_id": 12345,
                        "expected_image": IMAGE,
                    },
                }
            ),
            encoding="utf-8",
        )
        return path

    def _complete_tree(self, root: Path, job_id: str) -> None:
        remote_root = f"/workspace/results/{job_id}"

        def write_remote(remote_path: str, payload: dict | str | bytes) -> None:
            local = root / Path(remote_path).relative_to(Path("/workspace/results") / job_id)
            local.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(payload, dict):
                local.write_text(json.dumps(payload), encoding="utf-8")
            elif isinstance(payload, bytes):
                local.write_bytes(payload)
            else:
                local.write_text(payload, encoding="utf-8")

        readiness_report = SUMMARY.remote_report_path(job_id, job_id, "readiness")
        preflight_report = SUMMARY.remote_report_path(job_id, job_id, "preflight")
        f1_report = SUMMARY.remote_report_path(job_id, job_id, "f1")
        f2_report = SUMMARY.remote_report_path(job_id, job_id, "f2")
        readiness_output = f"{remote_root}/readiness/{job_id}/gpu-runtime.json"
        preflight_outputs = [
            f"{remote_root}/preflight/{job_id}/cad-to-simready-preflight.json",
            f"{remote_root}/preflight/{job_id}/cad-to-simready-preflight.env",
            f"{remote_root}/preflight/{job_id}/cad-to-simready-preflight.md",
        ]
        f1_output = f"{remote_root}/f1/{job_id}/stages/917-complete-engine-f1.usda"
        f2_output = f"{remote_root}/f2/{job_id}/stages/917-engine-kinematic-f2.usda"
        f3_output = f"{remote_root}/f3/{job_id}/stages/917-engine-detail-f3.usda"
        self._write_phase(
            root, "readiness", job_id, "readiness", outputs=[readiness_output],
            child_reports=[readiness_output],
        )
        self._write_phase(
            root, "preflight", job_id, "preflight",
            inputs=[readiness_report], outputs=preflight_outputs,
            child_reports=[preflight_outputs[0]],
        )
        f1_child = f"{remote_root}/f1/{job_id}/validate-complete-engine-f1.json"
        f2_child = f"{remote_root}/f2/{job_id}/validate-kinematics-f2.json"
        f3_child = f"{remote_root}/f3/{job_id}/validate-detail-expansion-f3.json"
        self._write_phase(
            root, "f1", job_id, "f1", inputs=[preflight_report], outputs=[f1_output],
            child_reports=[f1_child],
        )
        self._write_phase(
            root, "f2", job_id, "f2", inputs=[f1_output, f1_report], outputs=[f2_output],
            child_reports=[f2_child],
        )
        self._write_phase(
            root, "f3", job_id, "f3",
            inputs=[f2_output, f2_report, preflight_report], outputs=[f3_output],
            child_reports=[f3_child],
        )
        definitions = {
            "na": (
                "f10-type-912-4-5-na", "type_912_4_5_na", "type-912-4-5-na",
                "/type-912-4-5-na/stages/type-912-4-5-na-detail-f10.usda",
            ),
            "turbo": (
                "f10-917-30-turbo-5374", "917_30_turbo_5374", "917-30-turbo-5374",
                "/917-30-turbo-5374/stages/917-30-turbo-5374-detail-f10.usda",
            ),
        }
        for suffix, (f10_phase, variant_id, slug, stage_suffix) in definitions.items():
            run_id = f"{job_id}-{suffix}"
            f10_report = SUMMARY.remote_report_path(job_id, run_id, f10_phase)
            stage = f"{remote_root}/f10/{run_id}/generated{stage_suffix}"
            context_root = f"{remote_root}/f10/{run_id}/generated/{slug}/reports"
            context_report = f"{context_root}/asset-context.json"
            context_markdown = f"{context_root}/asset-context.md"
            self._write_phase(
                root,
                "f10",
                run_id,
                f10_phase,
                inputs=[preflight_report],
                outputs=[stage],
                child_reports=[context_report, context_markdown],
            )
            write_remote(
                context_report,
                {
                    "schema_version": "1.0.0", "status": "passed", "passed": True,
                    "source_asset_path": stage, "variant_id": variant_id,
                    "documented_geometry": {
                        field: {"value": 1, "source_ids": ["src-test"]}
                        for field in (
                            "cylinder_count", "bore_mm", "stroke_mm",
                            "documented_displacement_cm3",
                        )
                    },
                    "evidence": [{"source_id": "src-test"}],
                    "release_gates": {key: False for key in SUMMARY.RELEASE_GATES},
                    "material_physics_prompt": "Contexte sourcé, aucune revendication physique.",
                },
            )
            write_remote(context_markdown, "# Contexte\n")
            minimum_report = SUMMARY.remote_report_path(job_id, run_id, "minimum-usd")
            material_report = SUMMARY.remote_report_path(job_id, run_id, "material")
            physics_report = SUMMARY.remote_report_path(job_id, run_id, "physics")
            conform_report = SUMMARY.remote_report_path(job_id, run_id, "conform")
            material_output = f"{remote_root}/material/{run_id}/output/material.usda"
            physics_output = f"{remote_root}/physics/{run_id}/output/physics.usda"
            conform_output = f"{remote_root}/conform/{run_id}/output/conformed.usda"
            material_prompt = f"/workspace/jobs/{job_id}/inputs/material-prompt.txt"
            physics_prompt = f"/workspace/jobs/{job_id}/inputs/physics-prompt.txt"
            self._write_phase(
                root, "minimum-usd", run_id, "minimum-usd",
                inputs=[stage, f10_report], outputs=[stage],
                child_reports=[f"{remote_root}/minimum-usd/{run_id}/minimum-usd.json"],
            )
            self._write_phase(
                root, "material", run_id, "material",
                inputs=[stage, minimum_report, material_prompt, context_report],
                outputs=[material_output],
                child_reports=[f"{remote_root}/material/{run_id}/material-agent.json"],
            )
            self._write_phase(
                root, "physics", run_id, "physics",
                inputs=[material_report, physics_prompt, context_report, material_output],
                outputs=[physics_output],
                child_reports=[f"{remote_root}/physics/{run_id}/physics-agent.json"],
            )
            self._write_phase(
                root, "conform", run_id, "conform",
                inputs=[physics_report, physics_output], outputs=[conform_output],
                child_reports=[f"{remote_root}/conform/{run_id}/simready-conform-profile.json"],
            )
            previous = None
            validation_reports = {}
            for phase in SUMMARY.VALIDATION_PHASES[:-1]:
                inputs = [conform_report, conform_output]
                if previous:
                    inputs.append(previous)
                child = f"{remote_root}/{phase}/{run_id}/{phase}.json"
                self._write_phase(
                    root, phase, run_id, phase, inputs=inputs, outputs=[conform_output],
                    child_reports=[child],
                )
                previous = SUMMARY.remote_report_path(job_id, run_id, phase)
                validation_reports[phase.removeprefix("validate-")] = previous
            simready_report = SUMMARY.remote_report_path(job_id, run_id, "validate-simready")
            simready_root = f"{remote_root}/validate-simready/{run_id}"
            initial_simready = f"{simready_root}/attempt-1/simready-validate.json"
            initial_simready_markdown = f"{simready_root}/attempt-1/simready-validate.md"
            repair_report = f"{simready_root}/repair-loop.json"
            repair_markdown = f"{simready_root}/repair-loop.md"
            validation_reports["simready"] = initial_simready
            self._write_phase(
                root, "validate-simready", run_id, "validate-simready",
                inputs=[conform_report, conform_output, previous], outputs=[conform_output],
                child_reports=[
                    initial_simready, initial_simready_markdown, repair_report, repair_markdown,
                ],
            )
            write_remote(
                initial_simready,
                {"schema_version": "1.0.0", "status": "passed", "passed": True,
                 "asset_path": conform_output},
            )
            write_remote(initial_simready_markdown, "# SimReady\n")
            write_remote(
                repair_report,
                {
                    "schema_version": "1.0.0", "status": "passed", "passed": True,
                    "profile": "Prop-Robotics-Neutral", "profile_version": "1.0.0",
                    "source_conform_report": conform_report,
                    "initial_usd_path": conform_output, "final_usd_path": conform_output,
                    "repair_attempted": False, "max_attempts": 2, "attempt_count": 1,
                    "failed_requirement_ids": [], "repaired_requirement_ids": [],
                    "blocked_requirement_ids": [], "unresolved_requirement_ids": [],
                    "attempts": [{"attempt": 1}],
                    "final_validation_reports": validation_reports,
                },
            )
            write_remote(repair_markdown, "# Boucle de réparation\n")
            render_root = f"{remote_root}/render-preview/{run_id}"
            render_png = f"{render_root}/917-engine-simready-preview.png"
            photos = [
                f"{render_root}/photos/{name}"
                for name in (
                    "917-engine-front.png",
                    "917-engine-right.png",
                    "917-engine-rear.png",
                    "917-engine-left.png",
                )
            ]
            movie = f"{render_root}/917-engine-simready-turntable.mp4"
            checksum = f"{render_root}/render-media.sha256"
            render_reference = f"{render_root}/ovrtx-render-service.json"
            render_reference_markdown = f"{render_root}/ovrtx-render-service.md"
            turntable_report = f"{render_root}/ovrtx-turntable.json"
            turntable_markdown = f"{render_root}/ovrtx-turntable.md"
            ffprobe_report = f"{render_root}/turntable-video-ffprobe.json"
            render_attestation = f"{render_root}/render-media-attestation.json"
            video_status = f"{render_root}/video-f7-status.json"
            final_report = f"{render_root}/omniverse-cad-to-simready-report.json"
            final_markdown = f"{render_root}/omniverse-cad-to-simready-report.md"
            frame_paths = [
                f"{render_root}/turntable-frames/frame_{index:03d}.png"
                for index in range(24)
            ]
            self._write_phase(
                root, "render-preview", run_id, "render-preview",
                inputs=[conform_report, simready_report, conform_output],
                outputs=[render_png, *photos, movie, checksum],
                child_reports=[
                    render_reference, render_reference_markdown,
                    turntable_report, turntable_markdown, ffprobe_report,
                    render_attestation, video_status, final_report, final_markdown,
                ],
            )
            write_remote(render_png, b"preview-ovrtx")
            for index, frame_path in enumerate(frame_paths):
                write_remote(frame_path, f"frame-ovrtx-{index:03d}".encode("ascii"))
            for photo, source_index in zip(photos, (0, 6, 12, 18), strict=True):
                write_remote(photo, f"frame-ovrtx-{source_index:03d}".encode("ascii"))
            write_remote(movie, b"mp4-h264-yuv420p")
            write_remote(
                render_reference,
                {
                    "asset_path": conform_output,
                    "output_image_path": render_png,
                    "generated_files": [render_png],
                    "passed": True,
                },
            )
            write_remote(render_reference_markdown, "# Rendu OVRTX\n")
            write_remote(
                turntable_report,
                {
                    "asset_path": conform_output,
                    "frames_requested": 24,
                    "frames_rendered": 24,
                    "generated_files": frame_paths,
                    "frame_reports": [
                        {
                            "frame": index,
                            "passed": True,
                            "output_image_path": frame_path,
                            "pixel_inspection": {"uniform": False},
                        }
                        for index, frame_path in enumerate(frame_paths)
                    ],
                    "passed": True,
                },
            )
            write_remote(turntable_markdown, "# Turntable OVRTX\n")
            write_remote(
                ffprobe_report,
                {
                    "streams": [{
                        "codec_name": "h264", "pix_fmt": "yuv420p",
                        "width": 1280, "height": 720, "nb_frames": "24",
                    }],
                    "format": {"duration": "3.000000"},
                },
            )
            media_paths = [render_png, *photos, movie]
            media_sha = {
                path: hashlib.sha256(
                    (root / Path(path).relative_to(Path("/workspace/results") / job_id)).read_bytes()
                ).hexdigest()
                for path in media_paths
            }
            write_remote(
                checksum,
                "".join(f"{media_sha[path]}  {Path(path).name}\n" for path in media_paths),
            )
            write_remote(
                render_attestation,
                {
                    "schema_version": "1.0.0", "status": "passed", "passed": True,
                    "claim_scope": "omniverse_visual_diagnostic_only",
                    "source_asset_path": conform_output,
                    "preview_path": render_png,
                    "photo_paths": photos,
                    "diagnostic_video_path": movie,
                    "turntable_frame_paths": frame_paths,
                    "media_sha256": media_sha,
                    "checksum_manifest_path": checksum,
                    "ovrtx_render_report": render_reference,
                    "ovrtx_turntable_report": turntable_report,
                    "ffprobe_report": ffprobe_report,
                    "upstream_simready_validation_status": "passed",
                    "simulation_validated": False,
                    "physical_simulation_validated": False,
                    "dyno_validated": False,
                    "performance_1600hp_validated": False,
                },
            )
            write_remote(
                video_status,
                {
                    "schema_version": "1.0.0", "status": "passed", "passed": True,
                    "phase": "turntable-diagnostic-film",
                    "output_video_path": movie,
                    "source_asset_path": conform_output,
                    "disclosure_embedded": True,
                    "kinematic_f7_engine_motion_status":
                        "blocked_not_part_of_this_simready_run",
                    "physical_simulation_claim_authorized": False,
                },
            )
            stage_names = [
                "readiness", "preflight", "f1", "f2", "f3", "f10",
                "minimum-usd", "material", "physics", "conform",
                "validate-asset", "validate-geometry", "validate-physics",
                "validate-simready", "render-ovrtx",
            ]
            ordered_stages = [{"stage": name, "status": "passed"} for name in stage_names]
            ordered_stages[-1].update({
                "report_path": render_reference,
                "input_artifacts": [conform_output],
                "output_artifacts": media_paths,
            })
            write_remote(
                final_report,
                {
                    "schema_version": "1.0.0", "overall_status": "passed", "passed": True,
                    "request_summary": {
                        "job_id": job_id, "run_id": run_id, "variant_id": variant_id,
                        "simready_profile": "Prop-Robotics-Neutral", "profile_version": "1.0.0",
                    },
                    "ordered_stage_results": ordered_stages,
                    "content_agents": {
                        "credentials": "redacted",
                        "render_report": render_reference,
                        "turntable_report": turntable_report,
                    },
                    "conformance_and_validation": {"repair_loop_report": repair_report},
                    "validation_scope": {
                        "simready_validated": True,
                        "physical_simulation_validated": False,
                        "dyno_validated": False,
                        "performance_1600hp_validated": False,
                    },
                    "final_artifacts": {
                        "final_usd_path": conform_output, "render_preview_path": render_png,
                        "render_photo_paths": photos,
                        "diagnostic_video_path": movie,
                        "render_checksum_manifest_path": checksum,
                        "render_reference_report": render_reference,
                        "render_turntable_report": turntable_report,
                        "render_attestation_report": render_attestation,
                        "json_report_path": final_report, "markdown_report_path": final_markdown,
                    },
                    "claim_boundaries": ["SimReady seulement", "pas de dyno", "pas de 1600 ch"],
                },
            )
            write_remote(final_markdown, "# Rapport consolidé\n")

    def _set_branch_needs_rerun(self, root: Path, job_id: str, suffix: str) -> None:
        run_id = f"{job_id}-{suffix}"
        phase_path = root / f"validate-simready/{run_id}/phase-validate-simready.json"
        phase = json.loads(phase_path.read_text(encoding="utf-8"))
        phase.update({"status": "needs_rerun", "passed": False, "exit_code": 3})
        phase_path.write_text(json.dumps(phase), encoding="utf-8")

        initial_path = root / f"validate-simready/{run_id}/attempt-1/simready-validate.json"
        initial = json.loads(initial_path.read_text(encoding="utf-8"))
        initial.update({
            "status": "needs_rerun", "passed": False,
            "issues": [{"requirement_id": "GSP.001"}],
        })
        initial_path.write_text(json.dumps(initial), encoding="utf-8")

        repair_path = root / f"validate-simready/{run_id}/repair-loop.json"
        repair = json.loads(repair_path.read_text(encoding="utf-8"))
        repair.update({
            "status": "needs_rerun", "passed": False,
            "failed_requirement_ids": ["GSP.001"],
            "blocked_requirement_ids": ["GSP.001"],
            "unresolved_requirement_ids": ["GSP.001"],
        })
        repair_path.write_text(json.dumps(repair), encoding="utf-8")

        final_path = root / f"render-preview/{run_id}/omniverse-cad-to-simready-report.json"
        final = json.loads(final_path.read_text(encoding="utf-8"))
        final.update({"overall_status": "needs_rerun", "passed": False})
        final["validation_scope"]["simready_validated"] = False
        for stage in final["ordered_stage_results"]:
            if stage.get("stage") == "validate-simready":
                stage["status"] = "needs_rerun"
        final_path.write_text(json.dumps(final), encoding="utf-8")

        attestation_path = root / f"render-preview/{run_id}/render-media-attestation.json"
        attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
        attestation["upstream_simready_validation_status"] = "needs_rerun"
        attestation_path.write_text(json.dumps(attestation), encoding="utf-8")

    def _summarize(self, directory: Path, job_id: str = "job-test") -> dict:
        archive = directory / "results.tar.gz"
        archive.write_bytes(b"archive-verifiee")
        return SUMMARY.summarize(directory / job_id, archive, job_id, 12345, IMAGE)

    def test_deux_chaines_completes_sont_requises_pour_valider(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            root = directory / "job-test"
            self._complete_tree(root, "job-test")
            payload = self._summarize(directory)
            self.assertTrue(payload["retrieval_complete"])
            self.assertTrue(payload["simready_validated"])
            self.assertFalse(payload["simulation_validated"])
            self.assertFalse(payload["physical_simulation_validated"])
            self.assertFalse(payload["dyno_validated"])
            self.assertFalse(payload["performance_1600hp_validated"])
            self.assertEqual(payload["expected_pipelines"]["required_report_count"], 25)
            self.assertEqual(len(payload["f10_detail_stages"]), 2)

    def test_missing_turbo_ou_needs_rerun_ne_valide_jamais(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            root = directory / "job-test"
            self._complete_tree(root, "job-test")
            (root / "render-preview/job-test-turbo/phase-render-preview.json").unlink()
            missing = self._summarize(directory)
            self.assertFalse(missing["retrieval_complete"])
            self.assertFalse(missing["simulation_validated"])

            self._complete_tree(root, "job-test")
            self._set_branch_needs_rerun(root, "job-test", "na")
            rerun = self._summarize(directory)
            self.assertTrue(rerun["retrieval_complete"])
            self.assertFalse(rerun["simready_validated"])
            self.assertFalse(rerun["simulation_validated"])

    def test_doublon_ou_stage_f10_incorrect_est_refuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            root = directory / "job-test"
            self._complete_tree(root, "job-test")
            self._write_phase(
                root,
                "validate-asset",
                "job-test-na",
                "validate-asset",
                filename="phase-duplicate.json",
            )
            duplicate = self._summarize(directory)
            self.assertFalse(duplicate["retrieval_complete"])
            self.assertTrue(duplicate["duplicate_reports"])

            (root / "validate-asset/job-test-na/phase-duplicate.json").unlink()
            f10 = root / "f10/job-test-turbo/phase-f10.json"
            report = json.loads(f10.read_text(encoding="utf-8"))
            report["output_paths"] = ["/workspace/results/job-test/shared-detail-f10.usda"]
            f10.write_text(json.dumps(report), encoding="utf-8")
            wrong_stage = self._summarize(directory)
            self.assertFalse(wrong_stage["retrieval_complete"])
            self.assertTrue(wrong_stage["f10_stage_errors"])

    def test_identite_schema_et_statut_incoherents_sont_malformed(self):
        mutations = (
            ("control_job", {"job_id": "autre-job", "instance_id": 12345, "expected_image": IMAGE}),
            ("control_instance", {"job_id": "job-test", "instance_id": 54321, "expected_image": IMAGE}),
            ("control_image", {"job_id": "job-test", "instance_id": 12345, "expected_image": IMAGE.replace("a", "b")}),
            ("schema_version", "2.0.0"),
            ("status", "failed"),
            ("passed", False),
            ("exit_code", 7),
            ("exit_code_float", 0.0),
        )
        for field, value in mutations:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                root = directory / "job-test"
                self._complete_tree(root, "job-test")
                path = root / "material/job-test-na/phase-material.json"
                report = json.loads(path.read_text(encoding="utf-8"))
                target_field = "control" if field.startswith("control_") else field.removesuffix("_float")
                report[target_field] = value
                path.write_text(json.dumps(report), encoding="utf-8")
                payload = self._summarize(directory)
                self.assertFalse(payload["retrieval_complete"])
                self.assertFalse(payload["simulation_validated"])
                self.assertTrue(payload["report_contract_errors"])
                self.assertIn("job-test-na/material", payload["incomplete_phases"])

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            root = directory / "job-test"
            self._complete_tree(root, "job-test")
            path = root / "validate-geometry/job-test-na/phase-validate-geometry.json"
            report = json.loads(path.read_text(encoding="utf-8"))
            report["status"] = "needs_rerun"
            report["passed"] = True
            report["exit_code"] = 0
            path.write_text(json.dumps(report), encoding="utf-8")
            payload = self._summarize(directory)
            self.assertFalse(payload["retrieval_complete"])
            self.assertTrue(payload["report_contract_errors"])

    def test_sortie_absente_ou_continuite_brulee_est_refusee(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            root = directory / "job-test"
            self._complete_tree(root, "job-test")
            material = root / "material/job-test-na/phase-material.json"
            report = json.loads(material.read_text(encoding="utf-8"))
            missing = "/workspace/results/job-test/material/job-test-na/output/absent.usda"
            report["output_paths"] = [missing]
            material.write_text(json.dumps(report), encoding="utf-8")
            absent = self._summarize(directory)
            self.assertFalse(absent["retrieval_complete"])
            self.assertTrue(absent["report_contract_errors"])

            self._complete_tree(root, "job-test")
            minimum = root / "minimum-usd/job-test-turbo/phase-minimum-usd.json"
            report = json.loads(minimum.read_text(encoding="utf-8"))
            report["input_paths"] = [report["input_paths"][0]]
            minimum.write_text(json.dumps(report), encoding="utf-8")
            discontinu = self._summarize(directory)
            self.assertFalse(discontinu["retrieval_complete"])
            self.assertTrue(discontinu["continuity_errors"])

            self._complete_tree(root, "job-test")
            material = root / "material/job-test-na/phase-material.json"
            report = json.loads(material.read_text(encoding="utf-8"))
            report["input_paths"] = [
                "/workspace/jobs/job-test/inputs/prompt-non-atteste.txt"
                if value.endswith("material-prompt.txt") else value
                for value in report["input_paths"]
            ]
            material.write_text(json.dumps(report), encoding="utf-8")
            wrong_prompt = self._summarize(directory)
            self.assertFalse(wrong_prompt["retrieval_complete"])
            self.assertTrue(wrong_prompt["continuity_errors"])

    def test_rapport_attendu_hors_emplacement_exact_est_refuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            root = directory / "job-test"
            self._complete_tree(root, "job-test")
            original = root / "material/job-test-na/phase-material.json"
            shadow = root / "shadow/material/job-test-na/phase-material.json"
            shadow.parent.mkdir(parents=True)
            original.replace(shadow)
            payload = self._summarize(directory)
            self.assertFalse(payload["retrieval_complete"])
            self.assertFalse(payload["simulation_validated"])
            self.assertTrue(
                any("emplacement exact" in error for error in payload["report_contract_errors"])
            )

    def test_rapport_inattendu_refuse_le_contrat_de_recuperation(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            root = directory / "job-test"
            self._complete_tree(root, "job-test")
            self._write_phase(
                root,
                "surprise",
                "job-test",
                "surprise",
                outputs=["/workspace/results/job-test/surprise/job-test/unexpected.json"],
            )
            payload = self._summarize(directory)
            self.assertFalse(payload["retrieval_complete"])
            self.assertFalse(payload["simulation_validated"])
            self.assertEqual(payload["unexpected_reports"], ["job-test/surprise"])

    def test_contexte_reparation_et_rapport_final_sont_attestes(self):
        mutations = (
            (
                "context",
                "f10/job-test-na/generated/type-912-4-5-na/reports/asset-context.json",
                lambda payload: payload.update({"source_asset_path": "/workspace/results/job-test/autre.usda"}),
            ),
            (
                "repair",
                "validate-simready/job-test-na/repair-loop.json",
                lambda payload: payload.update({"final_usd_path": "/workspace/results/job-test/autre.usda"}),
            ),
            (
                "final",
                "render-preview/job-test-na/omniverse-cad-to-simready-report.json",
                lambda payload: payload["validation_scope"].update(
                    {"physical_simulation_validated": True}
                ),
            ),
        )
        for label, relative, mutate in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                root = directory / "job-test"
                self._complete_tree(root, "job-test")
                path = root / relative
                payload = json.loads(path.read_text(encoding="utf-8"))
                mutate(payload)
                path.write_text(json.dumps(payload), encoding="utf-8")
                summary = self._summarize(directory)
                self.assertFalse(summary["retrieval_complete"])
                self.assertFalse(summary["simready_validated"])
                self.assertTrue(summary["provenance_errors"])

    def test_rendu_ovrtx_photos_film_et_checksums_sont_attestes(self):
        mutations = (
            (
                "ovrtx_asset",
                "render-preview/job-test-na/ovrtx-render-service.json",
                lambda payload: payload.update({
                    "asset_path": "/workspace/results/job-test/autre.usda"
                }),
            ),
            (
                "turntable_status",
                "render-preview/job-test-na/ovrtx-turntable.json",
                lambda payload: payload.update({"status": "failed", "passed": True}),
            ),
            (
                "attestation_digest",
                "render-preview/job-test-na/render-media-attestation.json",
                lambda payload: payload["media_sha256"].update({
                    next(iter(payload["media_sha256"])): "0" * 64
                }),
            ),
            (
                "ordered_render",
                "render-preview/job-test-na/omniverse-cad-to-simready-report.json",
                lambda payload: payload["ordered_stage_results"].pop(),
            ),
        )
        for label, relative, mutate in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                root = directory / "job-test"
                self._complete_tree(root, "job-test")
                path = root / relative
                payload = json.loads(path.read_text(encoding="utf-8"))
                mutate(payload)
                path.write_text(json.dumps(payload), encoding="utf-8")
                summary = self._summarize(directory)
                self.assertFalse(summary["retrieval_complete"])
                self.assertFalse(summary["simready_validated"])
                self.assertTrue(summary["provenance_errors"])

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            root = directory / "job-test"
            self._complete_tree(root, "job-test")
            checksum = root / "render-preview/job-test-na/render-media.sha256"
            checksum.write_text("0" * 64 + "  falsifie.png\n", encoding="utf-8")
            summary = self._summarize(directory)
            self.assertFalse(summary["retrieval_complete"])
            self.assertTrue(summary["provenance_errors"])


class GardeInstanceTests(unittest.TestCase):
    def _wrapper(
        self,
        directory: Path,
        *,
        dph: float = 2.4,
        image: str = IMAGE,
        destroy_marker: Path | None = None,
        overrides: dict | None = None,
    ) -> Path:
        wrapper = directory / "openbao-vastai-factice"
        payload = {
            "id": 12345,
            "label": "3dprinting993-simready-local-ai",
            "status": "running",
            "gpu": "RTX PRO 6000 WS",
            "gpu_ram_mb": 98304,
            "num_gpus": 1,
            "gpu_fraction": 1,
            "machine_verification": "verified",
            "cpu_cores_effective": 32,
            "cpu_ram_mb": 196608,
            "disk_space_gb": 500,
            "dph_total": dph,
            "ssh_host": "ssh1.vast.ai",
            "ssh_port": 22022,
            "image": image,
        }
        payload.update(overrides or {})
        marker_command = f"printf destroyed >'{destroy_marker}'\n" if destroy_marker else ""
        wrapper.write_text(
            "#!/bin/sh\n"
            "if test \"$1\" = show && test \"$2\" = 12345; then\n"
            f"  printf '%s\\n' '{json.dumps(payload)}'\n"
            "  exit 0\n"
            "fi\n"
            "if test \"$1\" = destroy && test \"$2\" = 12345 && test \"$3\" = --confirm; then\n"
            f"  {marker_command}"
            "  printf '%s\\n' '{\"instance_id\": 12345, \"destroyed\": true, \"verified_absent\": true}'\n"
            "  exit 0\n"
            "fi\n"
            "exit 2\n",
            encoding="utf-8",
        )
        wrapper.chmod(0o700)
        return wrapper

    def _run(
        self,
        wrapper: Path,
        report: Path,
        image: str = IMAGE,
        *extra: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(CONTROLLER / "_instance_guard.py"),
                "--wrapper",
                str(wrapper),
                "--instance-id",
                "12345",
                "--expected-image",
                image,
                "--max-actual-dph",
                "2.50",
                "--require-ssh",
                "--report",
                str(report),
                *extra,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_garde_accepte_le_cout_contractuel_sous_2_50(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            report = directory / "guard.json"
            result = self._run(self._wrapper(directory), report)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "passed")
            self.assertEqual(payload["criteria"]["max_actual_dph"], "2.50")
            self.assertIn("disque contractuel inclus", payload["criteria"]["cost_basis"])

    def test_garde_refuse_un_cout_reel_superieur(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            report = directory / "guard.json"
            result = self._run(self._wrapper(directory, dph=3.161111), report)
            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "blocked")
            self.assertTrue(any("dph_total" in error for error in payload["errors"]))

    def test_garde_refuse_une_machine_sous_dimensionnee(self):
        mutations = (
            ("gpu", "RTX PRO 6000 S", "exactement RTX PRO 6000 WS"),
            ("gpu_fraction", 0.5, "GPU complet"),
            ("machine_verification", "unverified", "n'est pas vérifiée"),
            ("gpu_ram_mb", 48000, "VRAM"),
            ("cpu_cores_effective", 12, "CPU"),
            ("cpu_ram_mb", 64000, "RAM CPU"),
            ("disk_space_gb", 400, "disque"),
        )
        for field, value, expected_error in mutations:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                report = directory / "guard.json"
                wrapper = self._wrapper(directory, overrides={field: value})
                result = self._run(wrapper, report)
                self.assertNotEqual(result.returncode, 0)
                payload = json.loads(report.read_text(encoding="utf-8"))
                self.assertTrue(any(expected_error in error for error in payload["errors"]), payload)

    def test_garde_refuse_une_cible_ssh_non_vast_ou_privee(self):
        for host in ("ssh.example.test", "127.0.0.1", "10.0.0.7", "169.254.1.2"):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                report = directory / "guard.json"
                result = self._run(self._wrapper(directory, overrides={"ssh_host": host}), report)
                self.assertNotEqual(result.returncode, 0)
                payload = json.loads(report.read_text(encoding="utf-8"))
                self.assertIn("hôte SSH invalide", payload["errors"])

    def test_garde_refuse_tag_ou_digest_different(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            report = directory / "guard.json"
            tag = "ghcr.io/cluster2600/3dprinting993-simready-local-ai:latest"
            result = self._run(self._wrapper(directory), report, image=tag)
            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "blocked")

    def test_mode_cleanup_ignore_seulement_le_plafond(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            report = directory / "cleanup-guard.json"
            result = self._run(self._wrapper(directory, dph=99.0), report, IMAGE, "--skip-cost-cap")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertFalse(payload["criteria"]["cost_cap_enforced"])

            wrong_image = f"ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:{'b' * 64}"
            rejected = self._run(self._wrapper(directory, dph=99.0), directory / "wrong.json", wrong_image, "--skip-cost-cap")
            self.assertNotEqual(rejected.returncode, 0)

    def test_destruction_partielle_exige_derogation_meme_si_cout_et_capacite_degrades(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            marker = directory / "destroyed.marker"
            wrapper = self._wrapper(
                directory,
                dph=99.0,
                destroy_marker=marker,
                overrides={"gpu_ram_mb": 1, "cpu_cores_effective": 1, "cpu_ram_mb": 1, "disk_space_gb": 1},
            )
            archive = directory / "partial.tar.gz"
            archive.write_bytes(b"artefacts-partiels")
            retrieval = directory / "retrieval.json"
            retrieval.write_text(
                json.dumps(
                    {
                        "job_id": "job-test",
                        "instance_id": 12345,
                        "expected_image": IMAGE,
                        "retrieval_attempted": True,
                        "artifact_archive_verified": True,
                        "retrieval_complete": False,
                        "simulation_validated": False,
                        "archive_path": str(archive),
                        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                    }
                ),
                encoding="utf-8",
            )
            control = directory / "control"
            env = os.environ.copy()
            env["OPENBAO_VASTAI_BIN"] = str(wrapper)
            result = subprocess.run(
                [
                    "bash", str(CONTROLLER / "destroy-instance.sh"),
                    "--instance-id", "12345",
                    "--expected-image", IMAGE,
                    "--job-id", "job-test",
                    "--confirm-job-id", "job-test",
                    "--confirm-instance-id", "12345",
                    "--confirm-digest", IMAGE,
                    "--retrieval-report", str(retrieval),
                    "--control-root", str(control),
                ],
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("récupération partielle", result.stderr)
            self.assertFalse(marker.exists())

            waiver = f"NO-RETRIEVAL:job-test:12345:{IMAGE}"
            waived = subprocess.run(
                [
                    "bash", str(CONTROLLER / "destroy-instance.sh"),
                    "--instance-id", "12345",
                    "--expected-image", IMAGE,
                    "--job-id", "job-test",
                    "--confirm-job-id", "job-test",
                    "--confirm-instance-id", "12345",
                    "--confirm-digest", IMAGE,
                    "--confirm-no-retrieval", waiver,
                    "--control-root", str(control),
                ],
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(waived.returncode, 0, waived.stderr)
            self.assertTrue(marker.is_file())
            destroyed = json.loads((control / "destroy-report.json").read_text(encoding="utf-8"))
            self.assertTrue(destroyed["retrieval_waived"])
            self.assertFalse(destroyed["retrieval_complete"])
            self.assertFalse(destroyed["simready_validated"])
            self.assertFalse(destroyed["simulation_validated"])
            guard = json.loads((control / "instance-guard-destroy.json").read_text(encoding="utf-8"))
            self.assertFalse(guard["criteria"]["cost_cap_enforced"])
            self.assertFalse(guard["criteria"]["capability_floor_enforced"])

    def test_destruction_refuse_confirmation_digest_differente(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            marker = directory / "destroyed.marker"
            wrapper = self._wrapper(directory, dph=99.0, destroy_marker=marker)
            env = os.environ.copy()
            env["OPENBAO_VASTAI_BIN"] = str(wrapper)
            result = subprocess.run(
                [
                    "bash", str(CONTROLLER / "destroy-instance.sh"),
                    "--instance-id", "12345",
                    "--expected-image", IMAGE,
                    "--job-id", "job-test",
                    "--confirm-job-id", "job-test",
                    "--confirm-instance-id", "12345",
                    "--confirm-digest", "digest-different",
                    "--confirm-no-retrieval", f"NO-RETRIEVAL:job-test:12345:{IMAGE}",
                    "--control-root", str(directory / "control"),
                ],
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())

    def test_destruction_refuse_archives_traversee_et_lien_symbolique(self):
        cases = (
            ("traversal", "job-test/../escape.txt", False),
            ("symlink", "job-test/link", True),
        )
        for label, member_name, is_symlink in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                marker = directory / "destroyed.marker"
                wrapper = self._wrapper(directory, destroy_marker=marker)
                archive = directory / f"{label}.tar.gz"
                with tarfile.open(archive, "w:gz") as handle:
                    member = tarfile.TarInfo(member_name)
                    if is_symlink:
                        member.type = tarfile.SYMTYPE
                        member.linkname = "/tmp/escape"
                        handle.addfile(member)
                    else:
                        payload = b"interdit"
                        member.size = len(payload)
                        handle.addfile(member, io.BytesIO(payload))
                retrieval = directory / "retrieval.json"
                retrieval.write_text(
                    json.dumps(
                        {
                            "job_id": "job-test",
                            "instance_id": 12345,
                            "expected_image": IMAGE,
                            "retrieval_attempted": True,
                            "artifact_archive_verified": True,
                            "retrieval_complete": True,
                            "simulation_validated": False,
                            "archive_path": str(archive),
                            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                        }
                    ),
                    encoding="utf-8",
                )
                env = os.environ.copy()
                env["OPENBAO_VASTAI_BIN"] = str(wrapper)
                result = subprocess.run(
                    [
                        "bash", str(CONTROLLER / "destroy-instance.sh"),
                        "--instance-id", "12345", "--expected-image", IMAGE,
                        "--job-id", "job-test", "--confirm-job-id", "job-test",
                        "--confirm-instance-id", "12345", "--confirm-digest", IMAGE,
                        "--retrieval-report", str(retrieval),
                        "--control-root", str(directory / "control"),
                    ],
                    env=env,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(marker.exists())
                self.assertFalse((directory / "escape.txt").exists())

    def test_cleanup_rabat_une_fausse_validation_sans_bloquer_destruction(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            marker = directory / "destroyed.marker"
            wrapper = self._wrapper(directory, destroy_marker=marker)
            root = directory / "job-test"
            fixture = ResumeRecuperationVariantAwareTests()
            fixture._complete_tree(root, "job-test")
            fixture._set_branch_needs_rerun(root, "job-test", "na")
            archive = directory / "results.tar.gz"
            with tarfile.open(archive, "w:gz") as handle:
                handle.add(root, arcname="job-test", recursive=True)
            retrieval_payload = SUMMARY.summarize(root, archive, "job-test", 12345, IMAGE)
            self.assertTrue(retrieval_payload["retrieval_complete"])
            self.assertFalse(retrieval_payload["simulation_validated"])
            retrieval_payload["simulation_validated"] = True
            retrieval = directory / "retrieval.json"
            retrieval.write_text(json.dumps(retrieval_payload), encoding="utf-8")
            env = os.environ.copy()
            env["OPENBAO_VASTAI_BIN"] = str(wrapper)
            result = subprocess.run(
                [
                    "bash", str(CONTROLLER / "destroy-instance.sh"),
                    "--instance-id", "12345", "--expected-image", IMAGE,
                    "--job-id", "job-test", "--confirm-job-id", "job-test",
                    "--confirm-instance-id", "12345", "--confirm-digest", IMAGE,
                    "--retrieval-report", str(retrieval),
                    "--control-root", str(directory / "control"),
                ],
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(marker.exists())
            destroyed = json.loads(
                (directory / "control/destroy-report.json").read_text(encoding="utf-8")
            )
            self.assertFalse(destroyed["simulation_validated"])
            self.assertFalse(destroyed["simready_validated"])


if __name__ == "__main__":
    unittest.main()
