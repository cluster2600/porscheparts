"""Garde statique de l'image CPU air/huile F34b et de sa publication."""

from __future__ import annotations

import ast
import json
import re
import shlex
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "containers/air-oil-cycle-f34b.Dockerfile"
DOCKERIGNORE = ROOT / "containers/air-oil-cycle-f34b.Dockerfile.dockerignore"
REQUIREMENTS = ROOT / "containers/air-oil-cycle-f34b.requirements.txt"
SMOKE = ROOT / "containers/air-oil-cycle-f34b-smoke.py"
SOLVER = ROOT / "scripts/run_917_air_oil_cycle_f34b.py"
ARCHITECTURE = ROOT / "twins/reference-917-engine/air-oil-core-controls-f34a.json"
DOE_CONTRACT = ROOT / "twins/reference-917-engine/doe-surrogate-f34.json"
SEED_BUNDLE = (
    ROOT
    / "twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json"
)
DOE_MANIFEST = (
    ROOT / "twins/reference-917-engine/evidence/f34/doe-case-manifest.json"
)
WORKFLOW = ROOT / ".github/workflows/air-oil-cycle-f34b-image.yml"

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
EXPECTED_COPY_SOURCES = [
    "containers/air-oil-cycle-f34b.requirements.txt",
    "containers/air-oil-cycle-f34b-smoke.py",
    "scripts/run_917_air_oil_cycle_f34b.py",
    "twins/reference-917-engine/air-oil-core-controls-f34a.json",
    "twins/reference-917-engine/doe-surrogate-f34.json",
    "twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json",
    "twins/reference-917-engine/evidence/f34/doe-case-manifest.json",
]
EXPECTED_DOCKERIGNORE = [
    "**",
    "!containers/",
    "!containers/air-oil-cycle-f34b.requirements.txt",
    "!containers/air-oil-cycle-f34b-smoke.py",
    "!scripts/",
    "!scripts/run_917_air_oil_cycle_f34b.py",
    "!twins/",
    "!twins/reference-917-engine/",
    "!twins/reference-917-engine/air-oil-core-controls-f34a.json",
    "!twins/reference-917-engine/doe-surrogate-f34.json",
    "!twins/reference-917-engine/evidence/",
    "!twins/reference-917-engine/evidence/f34/",
    "!twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json",
    "!twins/reference-917-engine/evidence/f34/doe-case-manifest.json",
]
REQUIRED_FALSE_RELEASE_GATES = {
    "target_definition_complete",
    "target_power_proven",
    "mass_and_energy_balance_validated",
    "thermodynamic_cycle_validated",
    "air_cooling_validated",
    "oil_system_validated",
    "turbo_match_validated",
    "combustion_and_knock_validated",
    "controls_and_overspeed_protection_validated",
    "structural_and_fatigue_validated",
    "doe_execution_complete",
    "physical_correlation_complete",
    "test_bench_start_authorized",
    "porsche_993_packaging_validated",
    "porsche_993_vehicle_installation_authorized",
    "metal_print_authorized",
    "manufacturing_authorized",
}


def _docker_copy_sources(dockerfile: str) -> list[str]:
    """Return local COPY sources while rejecting ambiguous shell forms."""

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


class AirOilCycleF34bImageTests(unittest.TestCase):
    def test_dockerfile_is_pinned_amd64_non_root_offline_and_exact(self):
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        lower = dockerfile.lower()

        self.assertIn(f"ARG PYTHON_BASE_IMAGE={BASE_IMAGE}", dockerfile)
        self.assertEqual(dockerfile.count("FROM ${PYTHON_BASE_IMAGE}"), 2)
        for fragment in (
            "docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e",
            "ARG TARGETARCH",
            'test "${TARGETARCH}" = "amd64"',
            "AIR_OIL_CYCLE_UID=9133",
            "AIR_OIL_CYCLE_GID=9133",
            "air-oil-cycle",
            "USER ${AIR_OIL_CYCLE_UID}:${AIR_OIL_CYCLE_GID}",
            "--require-hashes",
            "--no-deps",
            "--only-binary=:all:",
            "python -m pip check",
            "RUN --network=none",
            "air-oil-cycle-f34b-smoke.py",
            "run_917_air_oil_cycle_f34b.py",
            "air-oil-core-controls-f34a.json",
            "doe-surrogate-f34.json",
            "air-oil-forward-seeds-f34b.json",
            "doe-case-manifest.json",
        ):
            self.assertIn(fragment, dockerfile)
        self.assertEqual(_docker_copy_sources(dockerfile), EXPECTED_COPY_SOURCES)

        for forbidden in (
            "copy .",
            "raw-scans",
            "clean-sheet-cycle-thermal-f33",
            "run_917_cycle_thermal_f33",
            "copy work",
            "copy catalog",
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

    def test_requirements_are_the_exact_hashed_binary_wheel_lock(self):
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
        self.assertEqual(requirements.count("--hash=sha256:"), 4)
        for forbidden in (
            "--extra-index-url",
            "--find-links",
            "git+",
            "http://",
            "https://",
            "-e ",
        ):
            self.assertNotIn(forbidden, requirements)

    def test_docker_context_is_the_exact_public_allow_list(self):
        patterns = [
            line
            for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")
        ]
        self.assertEqual(patterns, EXPECTED_DOCKERIGNORE)
        for forbidden in (
            "!raw-scans/",
            "!work/",
            "!catalog/",
            "!docs/",
            "clean-sheet-cycle-thermal-f33",
            "cycle-thermal-report",
        ):
            self.assertNotIn(forbidden, "\n".join(patterns))

    def test_smoke_allows_only_preflight_and_generic_cantera_fixture(self):
        source = SMOKE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for fragment in (
            'ALLOWED_SOLVER_MODES = ("preflight",)',
            'execute_solver_mode("preflight")',
            '"--seed-bundle"',
            "air-oil-forward-seeds-f34b.json",
            'ct.Solution("gri30.yaml")',
            'equilibrate("HP")',
            'ct.IdealGasReactor(',
            'ct.ReactorNet([reactor])',
            'network.advance(final_time_s)',
            '"uses_engine_forward_input": False',
            '"uses_engine_geometry": False',
            '"uses_engine_calibration": False',
            '"canonical_doe_case": False',
            '"canonical_doe_cases_executed": 0',
            '"engine_forward_solver_executed": False',
            '"solver_synthetic_smoke_executed": False',
            '"canonical_doe_solver_campaign_executed": False',
            '"dataset_generated": False',
            '"surrogate_trained": False',
            '"predicted_engine_power": False',
            '"validated_1600_hp": False',
            '"physical_correlation": False',
            '"physicsnemo_executed": False',
            '"omniverse_executed": False',
            '"remote_compute_used": False',
            '"engine_core_liquid_coolant_present": False',
            '"canonical_doe_planned_cases": counts["planned"]',
            'case.get("execution_status") == "planned_not_executed"',
            'case.get("training_eligible") is False',
            "F34A_TECHNICAL_GATE_IDS",
            "F34A_RELEASE_GATE_IDS",
            "F34_RELEASE_GATE_IDS",
            "F34B_SEED_PHYSICAL_GATE_IDS",
            "require_closed_gate_set(",
            "set(value) == expected",
            'network_isolation_evidence()',
            'runtime_identity_and_filesystem_audit()',
            'bundled_content_audit()',
            'allow_nan=False',
        ):
            self.assertIn(fragment, source)
        for gate in REQUIRED_FALSE_RELEASE_GATES:
            self.assertRegex(
                source,
                rf'["\']{re.escape(gate)}["\']\s*:\s*False',
                gate,
            )

        invoked_modes = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id == "execute_solver_mode":
                self.assertEqual(len(node.args), 1)
                self.assertIsInstance(node.args[0], ast.Constant)
                invoked_modes.append(node.args[0].value)
        self.assertEqual(invoked_modes, ["preflight"])
        self.assertNotIn('execute_solver_mode("synthetic-smoke")', source)

        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        self.assertTrue(imported_roots.isdisjoint({"requests", "urllib"}))

        lower = source.lower()
        for forbidden in (
            "raw-scans",
            "clean-sheet-cycle-thermal-f33",
            "run_917_cycle_thermal_f33",
            "run_917_doe_f34",
            "--case-id",
            "--execute-doe",
            "openbao",
            "id_vastai",
        ):
            self.assertNotIn(forbidden, lower)

    def test_embedded_contracts_and_manifest_remain_fail_closed(self):
        architecture = json.loads(ARCHITECTURE.read_text(encoding="utf-8"))
        doe = json.loads(DOE_CONTRACT.read_text(encoding="utf-8"))
        seeds = json.loads(SEED_BUNDLE.read_text(encoding="utf-8"))
        manifest = json.loads(DOE_MANIFEST.read_text(encoding="utf-8"))

        self.assertEqual(
            architecture["decision"]["selected_core_thermal_architecture"],
            "strict_forced_air_and_dry_sump_oil_only",
        )
        self.assertFalse(
            architecture["engine_core_boundary"]["core_liquid_coolant_loop_present"]
        )
        self.assertFalse(doe["authority_boundary"]["doe_executed"])
        self.assertFalse(doe["runtime"]["future_solver"]["execution_authorized"])
        self.assertFalse(
            seeds["authority_boundary"]["engine_core_liquid_coolant_present"]
        )
        self.assertEqual(seeds["canonical_doe_cases_executed"], 0)
        self.assertEqual(seeds["execution_ledger"]["seed_count"], 2)
        self.assertEqual(seeds["execution_ledger"]["solver_case_count"], 0)
        self.assertEqual(manifest["case_counts"]["planned"], 2570)
        self.assertEqual(manifest["case_counts"]["executed"], 0)
        self.assertEqual(manifest["execution_ledger"]["planned_not_executed"], 2570)
        self.assertTrue(
            all(case["execution_status"] == "planned_not_executed" for case in manifest["cases"])
        )
        self.assertEqual(len(architecture["technical_gates"]), 15)
        self.assertEqual(len(architecture["release_gates"]), 17)
        self.assertEqual(len(doe["release_gates"]), 30)
        self.assertEqual(set(doe["release_gates"]), set(manifest["release_gates"]))
        self.assertEqual(set(doe["release_gates"]), set(seeds["release_gates"]))
        self.assertTrue(all(value is False for value in architecture["release_gates"].values()))
        self.assertTrue(all(value is False for value in doe["release_gates"].values()))
        self.assertTrue(all(value is False for value in manifest["release_gates"].values()))

    def test_workflow_is_manual_attested_exact_digest_and_anonymous(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        lower = workflow.lower()
        for fragment in (
            "workflow_dispatch:",
            "runs-on: ubuntu-24.04",
            "contents: read",
            "packages: write",
            "python3 tests/test_air_oil_cycle_f34b_image.py",
            "set -o pipefail",
            "scripts/export_917_air_oil_seeds_f34b.py",
            "--check twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json",
            "python3 tests/test_917_air_oil_seeds_f34b.py -v",
            "python3 tests/test_917_air_oil_cycle_f34b.py -v",
            "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
            "docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f",
            "version: v0.36.1",
            "image=moby/buildkit@sha256:28a898719c18a33f4e8000685287fa36fd0dd9560c6440227d3a732d79bb41d8",
            "48af8a397ebd60178778bf63611dbcebe5f5e7a9be90eb9147b24b9587455778",
            "docker/login-action@c94ce9fb468520275223c153574b00df6fe4bcc9",
            "docker/build-push-action@10e90e3645eae34f1e60eeb005ba3a3d33f178e8",
            "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
            "platforms: linux/amd64",
            "push: true",
            "provenance: mode=max",
            "sbom: true",
            "OCI_SOURCE=https://github.com/${{ github.repository }}",
            "candidate-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}",
            "group: air-oil-cycle-f34b-${{ github.sha }}",
            "cancel-in-progress: false",
            'test "${GITHUB_REF}" = "refs/heads/main"',
            'test "${GITHUB_SHA}" = "$(git rev-parse HEAD)"',
            "steps.build.outputs.digest",
            "for attempt in 1 2 3 4 5",
            "docker buildx imagetools inspect --raw",
            "application/vnd.oci.image.manifest.v1+json",
            "https://slsa.dev/provenance/v1",
            "https://spdx.dev/Document",
            ".subject.digest == $subject",
            "SPDX-2.3",
            "CC0-1.0",
            '"cantera" and .versionInfo == "3.2.0"',
            '"numpy" and .versionInfo == "2.5.2"',
            "docker pull --platform linux/amd64 \"${pinned_ref}\"",
            "--network none --read-only",
            "--tmpfs /tmp:rw,noexec,nosuid,size=64m",
            "--user 9133:9133",
            "--pids-limit 64",
            "--cap-drop ALL",
            "--security-opt no-new-privileges",
            "docker logout ghcr.io",
            'printf \'{"auths":{}}\\n\'',
            'DOCKER_CONFIG="${anonymous_config}" docker pull',
            "air-oil-cycle-f34b-anonymous-pull.txt",
            "air-oil-cycle-f34b-anonymous-audit.json",
            "docker buildx imagetools create --tag",
            "air-oil-cycle-f34b-candidate-tag.txt",
            "air-oil-cycle-f34b-release-tag.txt",
            "name: air-oil-cycle-f34b-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}",
            "if: always()",
            "test ! -s air-oil-cycle-f34b-smoke.stderr",
            "test ! -s air-oil-cycle-f34b-anonymous-smoke.stderr",
            "air-oil-cycle-f34b-derived-fixtures.json",
            "test ! -s air-oil-cycle-f34b-derived-fixtures.stderr",
            'synthetic-smoke',
            '"two_noncanonical_fixture_smokes_complete_all_physical_gates_blocked"',
            ".execution_boundary.synthetic_noncanonical_fixture_cases_executed == 2",
            ".execution_boundary.source_seed_cases_executed == 0",
            ".authoritative_engine_power_prediction_available == false",
            ".embedded_authority_audit.canonical_doe_executed_cases == 0",
            ".proof_boundary.engine_forward_solver_executed == false",
            ".proof_boundary.solver_synthetic_smoke_executed == false",
            ".proof_boundary.canonical_doe_cases_executed == 0",
            ".proof_boundary.predicted_engine_power == false",
            ".proof_boundary.validated_1600_hp == false",
            "(.physical_release_gates | keys | length) == 17",
            "(.physical_release_gates | keys | sort) == $expected_physical_release_gate_keys",
            "all(.physical_release_gates[]; . == false)",
            "verified-${GITHUB_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}",
        ):
            self.assertIn(fragment, workflow)

        self.assertNotRegex(workflow, r"(?m)^  (?:push|pull_request|schedule):\s*$")
        self.assertNotIn(":latest", workflow)
        for forbidden in (
            "raw-scans",
            "clean-sheet-cycle-thermal-f33",
            "run_917_cycle_thermal_f33",
            "vast",
            "openssh",
            "id_vastai",
            "cuda",
            "api.github",
        ):
            self.assertNotIn(forbidden, lower)
        self.assertNotIn("pip install physicsnemo", lower)
        self.assertNotIn("python3 scripts/run_917_doe_f34.py", workflow)

        uses = re.findall(r"^\s*uses:\s*(\S+)$", workflow, re.MULTILINE)
        self.assertEqual(len(uses), 6)
        self.assertEqual(
            uses.count(
                "docker/login-action@c94ce9fb468520275223c153574b00df6fe4bcc9"
            ),
            2,
        )
        self.assertEqual(
            workflow.count("(.physical_release_gates | keys | length) == 17"),
            2,
        )
        self.assertEqual(
            workflow.count(
                "(.physical_release_gates | keys | sort) == "
                "$expected_physical_release_gate_keys"
            ),
            2,
        )
        self.assertEqual(
            workflow.count(
                '--argjson expected_physical_release_gate_keys '
                '"${EXPECTED_PHYSICAL_RELEASE_GATE_KEYS}"'
            ),
            2,
        )
        expected_physical_release_gate_keys = sorted(REQUIRED_FALSE_RELEASE_GATES)
        encoded_expected_keys = json.dumps(
            expected_physical_release_gate_keys,
            separators=(",", ":"),
        )
        self.assertIn(encoded_expected_keys, workflow)
        for reference in uses:
            self.assertRegex(reference, r"^[^@]+@[0-9a-f]{40}$")
            self.assertNotRegex(reference, r"@v\d")

        logout_index = workflow.index("docker logout ghcr.io")
        anonymous_pull_index = workflow.index('DOCKER_CONFIG="${anonymous_config}" docker pull')
        promotion_index = workflow.index("docker buildx imagetools create --tag")
        self.assertLess(logout_index, anonymous_pull_index)
        self.assertLess(anonymous_pull_index, promotion_index)
        self.assertEqual(workflow.count("2> air-oil-cycle-f34b-smoke.stderr; then"), 1)
        self.assertEqual(workflow.count("test ! -s air-oil-cycle-f34b-smoke.stderr"), 1)
        self.assertEqual(
            workflow.count("2> air-oil-cycle-f34b-anonymous-smoke.stderr; then"),
            1,
        )
        self.assertEqual(
            workflow.count("test ! -s air-oil-cycle-f34b-anonymous-smoke.stderr"),
            1,
        )
        self.assertEqual(
            workflow.count("test ! -s air-oil-cycle-f34b-derived-fixtures.stderr"),
            1,
        )

    def test_workflow_records_every_input_but_uploads_evidence_only(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for relative in (
            ".github/workflows/air-oil-cycle-f34b-image.yml",
            "containers/air-oil-cycle-f34b.Dockerfile",
            "containers/air-oil-cycle-f34b.Dockerfile.dockerignore",
            "containers/air-oil-cycle-f34b.requirements.txt",
            "containers/air-oil-cycle-f34b-smoke.py",
            "scripts/export_917_air_oil_seeds_f34b.py",
            "scripts/run_917_air_oil_cycle_f34b.py",
            "scripts/run_917_doe_f34.py",
            "tests/test_917_air_oil_seeds_f34b.py",
            "tests/test_917_air_oil_cycle_f34b.py",
            "twins/reference-917-engine/air-oil-core-controls-f34a.json",
            "twins/reference-917-engine/doe-surrogate-f34.json",
            "twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json",
            "twins/reference-917-engine/evidence/f34/doe-case-manifest.json",
            "tests/test_air_oil_cycle_f34b_image.py",
        ):
            self.assertIn(relative, workflow)

        artifact_block = workflow.split("path: |", maxsplit=1)[1]
        for forbidden in (
            "air-oil-core-controls-f34a.json",
            "doe-surrogate-f34.json",
            "air-oil-forward-seeds-f34b.json",
            "doe-case-manifest.json",
            "run_917_air_oil_cycle_f34b.py",
        ):
            self.assertNotIn(forbidden, artifact_block)


if __name__ == "__main__":
    unittest.main()
