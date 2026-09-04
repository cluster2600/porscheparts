"""Gardes hors ligne de la recette F47; aucune API, aucun secret, aucun Vast."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import py_compile
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
IMAGE = ROOT / "containers/917-f47-cfd-cae"
DOCKERFILE = IMAGE / "Dockerfile"
CONTRACT = IMAGE / "contract.json"
WORKFLOW = ROOT / ".github/workflows/917-f47-cfd-cae-image.yml"
AUTHORITY = ROOT / "twins/reference-917-engine/engine-solver-authority-f46.json"


class F47CfdCaeImageTests(unittest.TestCase):
    def test_contract_is_bound_to_current_solver_authority_and_stays_closed(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["platform"], "linux/amd64")
        self.assertEqual(contract["source_revision"], "3ab2ee4258c26584dd39205190a5174edbc06fbb")
        self.assertEqual(
            contract["solver_authority"]["sha256"],
            hashlib.sha256(AUTHORITY.read_bytes()).hexdigest(),
        )
        self.assertFalse(contract["solver_authority"]["exact_ICEEngineFoam_executable_found"])
        self.assertFalse(contract["solver_authority"]["historical_engineFoam"]["built"])
        self.assertEqual(contract["job_contract"]["planned_case_count"], 26)
        self.assertEqual(contract["job_contract"]["currently_executable_case_count"], 0)
        self.assertTrue(all(value is False for value in contract["current_gates"].values()))
        self.assertFalse(contract["reproducibility"]["bit_reproducible"])

    def test_dockerfile_is_amd64_pinned_and_contains_the_exact_stack(self):
        source = DOCKERFILE.read_text(encoding="utf-8")
        for fragment in (
            "ubuntu:24.04@sha256:33ceb71981b602c1",
            "python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2",
            'test "${TARGETARCH}" = "amd64"',
            "OPENFOAM_PACKAGE_VERSION=20260724",
            "AATE_COMMIT=c0f75f953d67cd325d28d1300672d14288f22934",
            "AATE_ARCHIVE_SHA256=28ee8d96b6943fab11b3d70ea3befe472d06d24741962cdb399b1d54e7ff7d3b",
            "calculix-ccx=2.21-1",
            "gmsh=4.12.1+ds1-1.1build2",
            "openssh-server=1:9.6p1-3ubuntu13.19",
            "f46-vast-onstart",
            "f46-run-manifest",
            "9147:9147",
            "USER 0:0",
        ):
            self.assertIn(fragment, source)
        self.assertNotRegex(source, r"(?im)^\s*(?:ARG|ENV)\s+[^\n]*(?:TOKEN|PASSWORD|SECRET|API_KEY)")
        self.assertNotRegex(source, r"(?i)ln\s+-s[^\n]*(?:iceenginefoam)")
        self.assertNotIn("OpenFOAM-3.0.x", source)

    def test_build_context_is_a_public_allowlist(self):
        patterns = [
            line for line in (IMAGE / "Dockerfile.dockerignore").read_text().splitlines()
            if line and not line.startswith("#")
        ]
        self.assertEqual(patterns[0], "**")
        self.assertIn("!containers/engine-cycle-f33.requirements.txt", patterns)
        self.assertIn("!benchmarks/openfoam-poiseuille-f25/**", patterns)
        self.assertIn("!containers/917-f47-cfd-cae/**", patterns)
        joined = "\n".join(patterns).lower()
        for forbidden in ("raw", "scan", "work/", ".ssh", "openbao"):
            self.assertNotIn(forbidden, joined)

    def test_smokes_are_real_and_release_claims_are_false(self):
        smoke = (IMAGE / "image_smoke.py").read_text(encoding="utf-8")
        openfoam = (IMAGE / "openfoam_smoke.sh").read_text(encoding="utf-8")
        cuda = (IMAGE / "cuda_driver_smoke.c").read_text(encoding="utf-8")
        for fragment in (
            'gas.equilibrate("HP")',
            '["gmsh", "-3"',
            '["ccx", "-i"',
            'shutil.which(name)',
            "job_runner_smoke()",
            '"physical_validation": False',
            '"manufacturing_release": False',
            'payload["minimal_conjugate_fixture_executed"] = True',
        ):
            self.assertIn(fragment, smoke)
        self.assertIn("foamRun -solver incompressibleFluid", openfoam)
        self.assertIn('"${utility}" -help', openfoam)
        cht = (IMAGE / "cht_smoke.sh").read_text(encoding="utf-8")
        self.assertIn("foamMultiRun >foamMultiRun.log", cht)
        self.assertIn("splitMeshRegions -cellZones all -defaultRegion fluid", cht)
        self.assertIn('dlopen("libcuda.so.1"', cuda)
        self.assertIn("cuMemAlloc_v2", cuda)
        self.assertIn("4096", cuda)

    def test_runner_and_watchdog_are_bounded_and_non_root(self):
        runner = (IMAGE / "run_manifest.py").read_text(encoding="utf-8")
        wrapper = (IMAGE / "run_manifest.sh").read_text(encoding="utf-8")
        watchdog = (IMAGE / "watchdog.py").read_text(encoding="utf-8")
        onstart = (IMAGE / "vast_onstart.sh").read_text(encoding="utf-8")
        self.assertIn("command,", runner)
        self.assertNotIn("shell=True", runner)
        self.assertIn("input_manifest_sha256", runner)
        self.assertIn("compute_stop_epoch", runner)
        self.assertIn("forbidden geometry token or legacy alias", runner)
        self.assertIn("setpriv --reuid=9147 --regid=9147 --clear-groups --no-new-privs", wrapper)
        self.assertIn("real_uid == 9147", watchdog)
        self.assertIn("signal.SIGTERM", watchdog)
        self.assertIn("signal.SIGKILL", watchdog)
        self.assertIn("now + 28800", onstart)
        self.assertIn("--require-cuda", onstart)
        self.assertIn('"remote_watchdog_armed": True', onstart)

    def test_workflow_publishes_only_a_candidate_and_keeps_gpu_gate_closed(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("IMAGE_REPOSITORY: ghcr.io/cluster2600/3dprinting993-cfd-cae-f46", workflow)
        self.assertNotIn("github.repository_owner", workflow)
        self.assertIn('test "${GITHUB_REF}" = "refs/heads/main"', workflow)
        self.assertIn("platforms: linux/amd64", workflow)
        self.assertIn("provenance: mode=max", workflow)
        self.assertIn("sbom: true", workflow)
        self.assertIn("f47-index.json", workflow)
        self.assertIn("f47-platform-manifest.json", workflow)
        self.assertIn("f47-provenance.json", workflow)
        self.assertIn("f47-sbom.json", workflow)
        self.assertIn("--user 9147:9147", workflow)
        self.assertIn("--entrypoint /usr/local/bin/f47-image-smoke", workflow)
        self.assertIn(".tools.cht.passed == true", workflow)
        self.assertIn(".tools.gmsh.passed == true", workflow)
        self.assertIn(".tools.cuda.passed == false", workflow)
        self.assertNotIn(":latest", workflow)
        self.assertNotIn("launch-vast", workflow)

    def test_sources_parse_without_executing_external_actions(self):
        for path in IMAGE.glob("*.py"):
            py_compile.compile(str(path), doraise=True)
        for path in IMAGE.glob("*.sh"):
            subprocess.run(["sh", "-n", str(path)], check=True)


if __name__ == "__main__":
    unittest.main()
