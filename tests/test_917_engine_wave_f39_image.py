"""Garde statique de l'image CPU F39 et de sa publication GHCR."""

from __future__ import annotations

import ast
import re
import shlex
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
IMAGE_ROOT = ROOT / "containers/917-engine-wave-f39"
DOCKERFILE = IMAGE_ROOT / "Dockerfile"
DOCKERIGNORE = IMAGE_ROOT / "Dockerfile.dockerignore"
REQUIREMENTS = IMAGE_ROOT / "requirements.txt"
SMOKE = IMAGE_ROOT / "smoke.py"
ENTRYPOINT = IMAGE_ROOT / "entrypoint.sh"
WORKFLOW = ROOT / ".github/workflows/917-engine-wave-f39-image.yml"

BASE_IMAGE = (
    "python:3.12.14-slim-bookworm@sha256:"
    "9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef"
)
EXPECTED_REQUIREMENTS = {
    "aeolus1d": (
        "0.3.3",
        "a62b8cc321588c092a1fa3481ea0023ccc685822018212fb8e1b35f346803c0e",
    ),
    "h5py": (
        "3.14.0",
        "0cbd41f4e3761f150aa5b662df991868ca533872c95467216f2bec5fcad84882",
    ),
    "llvmlite": (
        "0.49.0",
        "6acba646d88abbc87d5c113a3d62c1fbf8b8fee11c6493f516803e30f21ae870",
    ),
    "numba": (
        "0.67.0",
        "f63d43db06b4756424d6d2484737c902e0ae944a0eec3e8b0b4de2c695b15caa",
    ),
    "numpy": (
        "2.2.6",
        "fd83c01228a688733f1ded5201c678f0c53ecc1006ffbc404db9f7a899ac6249",
    ),
    "scipy": (
        "1.16.3",
        "72d1717fd3b5e6ec747327ce9bda32d5463f472c9dce9f54499e81fbd50245a1",
    ),
}
EXPECTED_COPY_SOURCES = [
    "containers/917-engine-wave-f39/requirements.txt",
    "containers/917-engine-wave-f39/smoke.py",
    "containers/917-engine-wave-f39/entrypoint.sh",
]
EXPECTED_DOCKERIGNORE = [
    "**",
    "!containers/",
    "!containers/917-engine-wave-f39/",
    "!containers/917-engine-wave-f39/requirements.txt",
    "!containers/917-engine-wave-f39/smoke.py",
    "!containers/917-engine-wave-f39/entrypoint.sh",
]


def docker_copy_sources(source: str) -> list[str]:
    result: list[str] = []
    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line.startswith("COPY "):
            continue
        tokens = shlex.split(line)
        if any(token.startswith("--from=") for token in tokens[1:]):
            continue
        positional = [token for token in tokens[1:] if not token.startswith("--")]
        result.extend(positional[:-1])
    return result


class EngineWaveF39ImageTests(unittest.TestCase):
    def test_dockerfile_is_pinned_amd64_non_root_and_minimal(self):
        source = DOCKERFILE.read_text(encoding="utf-8")
        lower = source.lower()
        self.assertIn(f"ARG PYTHON_BASE_IMAGE={BASE_IMAGE}", source)
        self.assertEqual(source.count("FROM ${PYTHON_BASE_IMAGE}"), 2)
        for fragment in (
            "docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e",
            'test "${TARGETARCH}" = "amd64"',
            "--only-binary=:all:",
            "--require-hashes",
            "--no-deps",
            "python -m pip check",
            "ENGINE_WAVE_UID=9139",
            "ENGINE_WAVE_GID=9139",
            "USER ${ENGINE_WAVE_UID}:${ENGINE_WAVE_GID}",
            "RUN --network=none",
            "ENTRYPOINT [\"/opt/917-engine-wave-f39/entrypoint.sh\"]",
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
            "cuda",
            "physicsnemo",
            "omniverse",
            "openfoam",
            "expose ",
        ):
            self.assertNotIn(forbidden, lower)
        self.assertNotRegex(
            source,
            r"(?im)^\s*(?:ARG|ENV)\s+[^\n]*(?:TOKEN|PASSWORD|SECRET|API_KEY)",
        )

    def test_requirements_are_exact_hashed_linux_wheels(self):
        source = REQUIREMENTS.read_text(encoding="ascii")
        entries = re.findall(
            r"^([A-Za-z0-9_.-]+)==([^ \\\n]+)\s*\\\n\s+--hash=sha256:([0-9a-f]{64})$",
            source,
            re.MULTILINE,
        )
        locked = {name.lower(): (version, digest) for name, version, digest in entries}
        self.assertEqual(locked, EXPECTED_REQUIREMENTS)
        self.assertEqual(source.count("--hash=sha256:"), len(EXPECTED_REQUIREMENTS))
        for forbidden in ("--extra-index-url", "--find-links", "git+", "http://", "https://", "-e "):
            self.assertNotIn(forbidden, source)

    def test_context_is_an_exact_public_allowlist(self):
        patterns = [
            line
            for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")
        ]
        self.assertEqual(patterns, EXPECTED_DOCKERIGNORE)
        self.assertEqual(
            set(docker_copy_sources(DOCKERFILE.read_text(encoding="utf-8"))),
            set(EXPECTED_COPY_SOURCES),
        )

    def test_smoke_is_generic_and_keeps_engine_claims_closed(self):
        source = SMOKE.read_text(encoding="utf-8")
        ast.parse(source)
        for fragment in (
            "run_sod(N=64, cfl=0.4)",
            '"generic_sod_benchmark_executed": True',
            '"flat_12_model_executed": False',
            '"turbo_maps_validated": False',
            '"engine_model_physically_correlated": False',
            '"target_1600_mechanical_hp_proven": False',
            '"engine_start_authorized": False',
            '"manufacturing_authorized": False',
        ):
            self.assertIn(fragment, source)

    def test_entrypoint_and_workflow_are_bounded(self):
        entrypoint = ENTRYPOINT.read_text(encoding="utf-8")
        self.assertIn("set -eu", entrypoint)
        self.assertIn('exec "$@"', entrypoint)
        ast.parse(SMOKE.read_text(encoding="utf-8"))

        workflow = WORKFLOW.read_text(encoding="utf-8")
        for fragment in (
            "ghcr.io/${{ github.repository_owner }}/3dprinting993-wave-action-f39",
            "platforms: linux/amd64",
            "provenance: mode=max",
            "sbom: true",
            "--network none",
            "--read-only",
            "--cap-drop ALL",
            "target_1600_mechanical_hp_proven == false",
        ):
            self.assertIn(fragment, workflow)
        self.assertNotIn("pull_request_target", workflow)
        self.assertNotRegex(
            workflow,
            r"(?im)^\s*(?:env:|[A-Za-z0-9_]+:)\s*[^\n]*(?:NVIDIA_API_KEY|VAST_API_KEY)",
        )


if __name__ == "__main__":
    unittest.main()
