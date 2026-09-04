"""Garde statique de l'image CPU F38 et de sa publication GHCR."""

from __future__ import annotations

import ast
import importlib.util
import json
import shlex
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "containers/gas-path-f38.Dockerfile"
DOCKERIGNORE = ROOT / "containers/gas-path-f38.Dockerfile.dockerignore"
SMOKE = ROOT / "containers/gas-path-f38-smoke.py"
WORKFLOW = ROOT / ".github/workflows/gas-path-f38-image.yml"
CONTRACT = ROOT / "twins/reference-917-engine/gas-path-network-f38.json"
REPORT = ROOT / "twins/reference-917-engine/evidence/f38/gas-path-network-f38-report.json"
BASE_IMAGE = (
    "python:3.12.14-slim-bookworm@sha256:"
    "9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef"
)
EXPECTED_COPY_SOURCES = [
    "containers/gas-path-f38-smoke.py",
    "twins/reference-917-engine/source/run_gas_path_network_f38.py",
    "twins/reference-917-engine/gas-path-network-f38.json",
    "twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json",
    "twins/reference-917-engine/doe-surrogate-f34.json",
    "twins/reference-917-engine/air-oil-core-controls-f34a.json",
    "twins/reference-917-engine/integrated-bench-assembly-f37.json",
    "twins/reference-917-engine/evidence/f33/cycle-thermal-report.json",
    "twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json",
    "twins/reference-917-engine/evidence/f34/report.json",
    "twins/reference-917-engine/evidence/f38/gas-path-network-f38-report.json",
]
EXPECTED_DOCKERIGNORE = [
    "**",
    "!containers/",
    "!containers/gas-path-f38-smoke.py",
    "!twins/",
    "!twins/reference-917-engine/",
    "!twins/reference-917-engine/source/",
    "!twins/reference-917-engine/source/run_gas_path_network_f38.py",
    "!twins/reference-917-engine/gas-path-network-f38.json",
    "!twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json",
    "!twins/reference-917-engine/doe-surrogate-f34.json",
    "!twins/reference-917-engine/air-oil-core-controls-f34a.json",
    "!twins/reference-917-engine/integrated-bench-assembly-f37.json",
    "!twins/reference-917-engine/evidence/",
    "!twins/reference-917-engine/evidence/f33/",
    "!twins/reference-917-engine/evidence/f33/cycle-thermal-report.json",
    "!twins/reference-917-engine/evidence/f34/",
    "!twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json",
    "!twins/reference-917-engine/evidence/f34/report.json",
    "!twins/reference-917-engine/evidence/f38/",
    "!twins/reference-917-engine/evidence/f38/gas-path-network-f38-report.json",
]


def docker_copy_sources(source: str) -> list[str]:
    result: list[str] = []
    for raw in source.splitlines():
        line = raw.strip()
        if not line.startswith("COPY "):
            continue
        tokens = shlex.split(line)
        positional = [token for token in tokens[1:] if not token.startswith("--")]
        result.extend(positional[:-1])
    return result


class GasPathF38ImageTest(unittest.TestCase):
    def test_dockerfile_is_pinned_minimal_amd64_non_root_and_offline(self):
        source = DOCKERFILE.read_text(encoding="utf-8")
        lower = source.lower()
        self.assertIn(f"ARG PYTHON_BASE_IMAGE={BASE_IMAGE}", source)
        self.assertEqual(source.count("FROM ${PYTHON_BASE_IMAGE}"), 1)
        for fragment in (
            "docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e",
            'test "${TARGETARCH}" = "amd64"',
            "GAS_PATH_UID=9138",
            "GAS_PATH_GID=9138",
            "USER ${GAS_PATH_UID}:${GAS_PATH_GID}",
            "RUN --network=none",
            "gas-path-f38-smoke.py",
            "run_gas_path_network_f38.py",
        ):
            self.assertIn(fragment, source)
        self.assertEqual(docker_copy_sources(source), EXPECTED_COPY_SOURCES)
        for forbidden in (
            "copy .",
            "raw-scans",
            "copy work",
            "copy catalog",
            "openbao",
            "id_vastai",
            "curl ",
            "wget ",
            "apt-get",
            "pip install",
            "cuda",
            "nvidia",
            "physicsnemo",
            "omniverse",
            "openfoam",
            "gmsh",
            "expose ",
        ):
            self.assertNotIn(forbidden, lower)
        self.assertNotRegex(source, r"(?im)^\s*(?:ARG|ENV)\s+[^\n]*(?:TOKEN|PASSWORD|SECRET|API_KEY)")

    def test_context_is_an_exact_public_allowlist(self):
        patterns = [
            line
            for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")
        ]
        self.assertEqual(patterns, EXPECTED_DOCKERIGNORE)
        self.assertNotIn("!raw-scans/", patterns)
        self.assertNotIn("!work/", patterns)
        self.assertNotIn("!catalog/", patterns)
        self.assertEqual(set(docker_copy_sources(DOCKERFILE.read_text(encoding="utf-8"))), set(EXPECTED_COPY_SOURCES))

    def test_smoke_reexecutes_exact_report_and_keeps_proof_gates_closed(self):
        source = SMOKE.read_text(encoding="utf-8")
        ast.parse(source)
        for fragment in (
            "EXPECTED_REPORT_SHA256",
            "f433c3a7e0dbfee9139bcd72b244dedfa28bf781101c0bd38ccb47bb9b565e10",
            '"byte_identical": True',
            '"target_power_proven": False',
            '"unsteady_1d_executed": False',
            '"maps_digitized": False',
            '"physical_correlation_complete": False',
            '"full_target_independence_proven": False',
            '"independent_model_cross_check": False',
            '"target_unit": "mechanical_hp_not_metric_PS_or_ch"',
            'require(not ipv4_routes',
            'require(\n        not ipv6_routed_interfaces',
            '"external_api_required": False',
            '"gpu_required": False',
            "EXPECTED_APPLICATION_FILES",
            "EXPECTED_TECHNICAL_GATES",
            "EXPECTED_RELEASE_GATES",
            "all(value is False for value in release.values())",
            "standard_library_audit()",
            "source_hash_audit(contract)",
        ):
            self.assertIn(fragment, source)
        self.assertNotIn("requests", source)
        self.assertNotIn("urllib", source)

    def test_contract_and_canonical_report_remain_consistent(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        self.assertEqual(contract["phase"], "F38")
        self.assertEqual(report["phase"], "F38")
        self.assertEqual(len(contract["source_evidence"]), 7)
        self.assertTrue(all(report["technical_gates"].values()))
        self.assertTrue(all(value is False for value in contract["release_gates"].values()))
        self.assertTrue(all(value is False for value in report["release_gates"].values()))
        self.assertFalse(report["runtime"]["external_api_used"])
        self.assertFalse(report["runtime"]["gpu_used"])

    def test_smoke_boundary_audit_accepts_the_current_canonical_report(self):
        spec = importlib.util.spec_from_file_location("gas_path_f38_smoke", SMOKE)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        module.CONTRACT = CONTRACT
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        boundary = module.report_boundary_audit(contract, report)
        self.assertFalse(boundary["target_power_proven"])
        self.assertFalse(boundary["full_target_independence_proven"])
        self.assertFalse(boundary["independent_model_cross_check"])
        self.assertTrue(
            boundary["requested_power_target_has_indirect_sampling_ancestry"]
        )

    def test_workflow_is_manual_pinned_hardened_and_publishes_by_digest(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        for fragment in (
            "workflow_dispatch:",
            "permissions:",
            "contents: read",
            "packages: write",
            "refs/heads/main",
            "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
            "docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f",
            "docker/login-action@c94ce9fb468520275223c153574b00df6fe4bcc9",
            "docker/build-push-action@10e90e3645eae34f1e60eeb005ba3a3d33f178e8",
            "provenance: mode=max",
            "sbom: true",
            "platforms: linux/amd64",
            "--network none",
            "--read-only",
            "--cap-drop ALL",
            "--security-opt no-new-privileges",
            "@${IMAGE_DIGEST}",
            "docker logout ghcr.io",
            'anonymous_config="$(mktemp -d)"',
            'printf \'{"auths":{}}\\n\'',
            'DOCKER_CONFIG="${anonymous_config}" docker pull',
            '"anonymous_pull_verified": True',
            "gas-path-f38-provenance.json",
            "gas-path-f38-sbom.json",
            'args["vcs:source"]',
            'args["vcs:revision"]',
            'internal["github_repository"]',
            'internal["github_workflow_sha"]',
            "a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e",
            "9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef",
            "target_power_proven",
            "unsteady_1d_executed",
        ):
            self.assertIn(fragment, source)
        self.assertNotIn("pull_request:", source)
        self.assertNotIn("push:\n", source)
        self.assertNotRegex(source, r"uses:\s+[^\n]+@(v\d+|main|master)\s*$")


if __name__ == "__main__":
    unittest.main()
