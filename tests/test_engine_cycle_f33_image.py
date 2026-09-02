"""Garde statique de l'image CPU de thermochimie moteur F33."""

from __future__ import annotations

import ast
import re
import shlex
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "containers/engine-cycle-f33.Dockerfile"
DOCKERIGNORE = ROOT / "containers/engine-cycle-f33.Dockerfile.dockerignore"
REQUIREMENTS = ROOT / "containers/engine-cycle-f33.requirements.txt"
SMOKE = ROOT / "scripts/smoke_engine_cycle_f33.py"
WORKFLOW = ROOT / ".github/workflows/engine-cycle-f33-image.yml"

BASE_IMAGE = (
    "python:3.12.14-slim-bookworm@sha256:"
    "9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef"
)
EXPECTED_REQUIREMENTS = {
    "cantera": (
        "3.2.0",
        "d7232fd69dda04b350b3d095dd5be234e4f627b8368421f8d1f976956feb3441",
    ),
    "numpy": (
        "2.5.2",
        "3cdec01fa790a186d430433fdd4d4ffb70eed6f0eeb4bf05c8dbe2dce0a9bcb8",
    ),
    "ruamel.yaml": (
        "0.19.1",
        "27592957fedf6e0b62f281e96effd28043345e0e66001f97683aa9a40c667c93",
    ),
    "typing-extensions": (
        "4.16.0",
        "481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8",
    ),
}
REQUIRED_FALSE_RELEASE_GATES = {
    "target_definition_complete",
    "target_power_proven",
    "mass_and_energy_balance_validated",
    "thermodynamic_cycle_validated",
    "turbo_match_validated",
    "combustion_and_knock_validated",
    "cooling_system_validated",
    "oil_system_validated",
    "structural_and_fatigue_validated",
    "controls_and_overspeed_protection_validated",
    "test_bench_start_authorized",
    "porsche_993_packaging_validated",
    "porsche_993_vehicle_installation_authorized",
    "held_out_physical_correlation_complete",
    "metal_print_authorized",
    "manufacturing_authorized",
}


def _docker_copy_sources(dockerfile: str) -> list[str]:
    """Return local COPY sources while refusing shell-form ambiguity in the recipe."""

    sources: list[str] = []
    for raw_line in dockerfile.splitlines():
        line = raw_line.strip()
        if not line.startswith("COPY "):
            continue
        tokens = shlex.split(line)
        if any(token.startswith("--from=") for token in tokens[1:]):
            continue
        positional = [token for token in tokens[1:] if not token.startswith("--")]
        if len(positional) < 2:
            raise AssertionError(f"COPY invalide: {raw_line}")
        sources.extend(positional[:-1])
    return sources


class EngineCycleF33ImageTests(unittest.TestCase):
    def test_dockerfile_is_exact_amd64_non_root_offline_and_minimal(self):
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        lower = dockerfile.lower()

        self.assertIn(
            f"ARG PYTHON_BASE_IMAGE={BASE_IMAGE}",
            dockerfile,
        )
        self.assertEqual(dockerfile.count("FROM ${PYTHON_BASE_IMAGE}"), 2)
        for fragment in (
            "docker/dockerfile:1.7@sha256:",
            "ARG TARGETARCH",
            'test "${TARGETARCH}" = "amd64"',
            "ENGINE_CYCLE_UID=9133",
            "ENGINE_CYCLE_GID=9133",
            "engine-cycle",
            "USER ${ENGINE_CYCLE_UID}:${ENGINE_CYCLE_GID}",
            "--require-hashes",
            "--no-deps",
            "--only-binary=:all:",
            "python -m pip check",
            "engine-cycle-f33.requirements.txt",
            "smoke_engine_cycle_f33.py",
            "RUN --network=none",
        ):
            self.assertIn(fragment, dockerfile)

        self.assertEqual(
            _docker_copy_sources(dockerfile),
            [
                "containers/engine-cycle-f33.requirements.txt",
                "scripts/smoke_engine_cycle_f33.py",
            ],
        )
        for forbidden in (
            "copy .",
            "raw-scans",
            "copy work",
            "copy twins",
            "openbao",
            "id_vastai",
            "openssh",
            "curl ",
            "wget ",
            "cuda",
            "nvidia",
            "physicsnemo",
            "omniverse",
            "openfoam",
            "gmsh",
            "expose ",
        ):
            self.assertNotIn(forbidden, lower)
        self.assertNotRegex(
            dockerfile,
            r"(?im)^\s*(?:ARG|ENV)\s+[^\n]*(?:TOKEN|PASSWORD|SECRET|API_KEY)",
        )

    def test_requirements_are_the_exact_hashed_wheel_lock(self):
        requirements = REQUIREMENTS.read_text(encoding="ascii")
        entries = re.findall(
            r"^([A-Za-z0-9_.-]+)==([^ \\\n]+)\s*\\\n\s+--hash=sha256:([0-9a-f]{64})$",
            requirements,
            re.MULTILINE,
        )
        locked = {name.lower(): (version, digest) for name, version, digest in entries}

        self.assertEqual(locked, EXPECTED_REQUIREMENTS)
        self.assertEqual(len(entries), len(EXPECTED_REQUIREMENTS))
        self.assertEqual(len({name.lower() for name, _, _ in entries}), len(entries))
        self.assertEqual(len({digest for _, _, digest in entries}), len(entries))
        self.assertEqual(
            requirements.count("--hash=sha256:"), len(EXPECTED_REQUIREMENTS)
        )
        for forbidden in (
            "--extra-index-url",
            "--find-links",
            "git+",
            "http://",
            "https://",
            "-e ",
        ):
            self.assertNotIn(forbidden, requirements)

    def test_docker_context_is_an_exact_two_file_allow_list(self):
        patterns = [
            line
            for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")
        ]
        self.assertEqual(
            patterns,
            [
                "**",
                "!containers/",
                "!containers/engine-cycle-f33.requirements.txt",
                "!scripts/",
                "!scripts/smoke_engine_cycle_f33.py",
            ],
        )
        for forbidden in ("!raw-scans/", "!twins/", "!work/", "!catalog/"):
            self.assertNotIn(forbidden, patterns)

    def test_smoke_exercises_only_synthetic_cantera_thermochemistry(self):
        source = SMOKE.read_text(encoding="utf-8")
        ast.parse(source)

        for fragment in (
            "import cantera as ct",
            '"cantera": "3.2.0"',
            "metadata.distributions()",
            'ct.Solution("gri30.yaml")',
            'equilibrate("HP")',
            "ct.IdealGasReactor(",
            "ct.ReactorNet(",
            "advance(",
            "math.isclose",
            "network.solver_stats",
            "runtime_identity_audit()",
            "network_isolation_evidence()",
            '"status": "passed_synthetic_thermochemistry_fixture_only"',
            '"synthetic_fixture": True',
            '"engine_cycle_solver_executed": False',
            '"engine_cycle_model": False',
            '"predicted_engine_power": False',
            '"validated_1600_hp": False',
            '"physical_correlation": False',
            '"physical_release_gates": PHYSICAL_RELEASE_GATES',
            "allow_nan=False",
        ):
            self.assertIn(fragment, source)
        for gate in REQUIRED_FALSE_RELEASE_GATES:
            self.assertRegex(
                source,
                rf'["\']{re.escape(gate)}["\']\s*:\s*False',
                gate,
            )
        for forbidden in (
            "raw-scans",
            "917-engine-case",
            "clean-sheet-2026-f32.json",
            "openfoam",
            "physicsnemo import",
            "omni.",
            "requests.",
            "urllib.request",
        ):
            self.assertNotIn(forbidden, source.lower())

    def test_workflow_publishes_attested_digest_and_runs_hardened_smoke(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        lower = workflow.lower()

        for fragment in (
            "workflow_dispatch:",
            "runs-on: ubuntu-24.04",
            "contents: read",
            "packages: write",
            "platforms: linux/amd64",
            "push: true",
            "provenance: mode=max",
            "sbom: true",
            "steps.build.outputs.digest",
            "docker buildx imagetools inspect --raw",
            "application/vnd.oci.image.manifest.v1+json",
            "https://slsa.dev/provenance/v1",
            "https://spdx.dev/Document",
            ".subject.digest == $subject",
            "docker pull --platform linux/amd64",
            "--network none",
            "--read-only",
            "--user 9133:9133",
            "--pids-limit",
            "--cap-drop ALL",
            "--security-opt no-new-privileges",
            "smoke_engine_cycle_f33.py",
            "engine-cycle-f33-smoke.json",
        ):
            self.assertIn(fragment, workflow)

        self.assertRegex(workflow, r"ghcr\.io/[^\s\"']+/[^\s\"']*engine-cycle-f33")
        self.assertRegex(workflow, r"@\$\{[^}]*digest[^}]*\}")
        self.assertNotIn(":latest", workflow)
        self.assertNotIn("vast", lower)
        self.assertNotIn("physicsnemo", lower)

        smoke_source = SMOKE.read_text(encoding="utf-8")
        for workflow_assertion, smoke_literal in (
            (".proof_boundary.synthetic_fixture == true", '"synthetic_fixture": True'),
            (
                ".proof_boundary.engine_cycle_solver_executed == false",
                '"engine_cycle_solver_executed": False',
            ),
            (".proof_boundary.predicted_engine_power == false", '"predicted_engine_power": False'),
        ):
            self.assertIn(workflow_assertion, workflow)
            self.assertIn(smoke_literal, smoke_source)

        action_references = re.findall(r"^\s*uses:\s*(\S+)$", workflow, re.MULTILINE)
        self.assertGreaterEqual(len(action_references), 5)
        for reference in action_references:
            self.assertRegex(reference, r"^[^@]+@[0-9a-f]{40}$")
            self.assertNotRegex(reference, r"@v\d")

    def test_workflow_scope_includes_every_image_input(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for relative_path in (
            "containers/engine-cycle-f33.Dockerfile",
            "containers/engine-cycle-f33.Dockerfile.dockerignore",
            "containers/engine-cycle-f33.requirements.txt",
            "scripts/smoke_engine_cycle_f33.py",
            "tests/test_engine_cycle_f33_image.py",
        ):
            self.assertIn(relative_path, workflow)


if __name__ == "__main__":
    unittest.main()
