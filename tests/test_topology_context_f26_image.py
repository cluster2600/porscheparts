"""Tests statiques de l'image CPU F26 et de sa chaîne GHCR."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys
import unittest


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "containers/topology-context-f26.Dockerfile"
DOCKERIGNORE = ROOT / "containers/topology-context-f26.Dockerfile.dockerignore"
REQUIREMENTS = ROOT / "containers/topology-context-f26-requirements.txt"
SMOKE = ROOT / "containers/topology-context-f26-smoke.py"
BIND_SMOKE = ROOT / "containers/topology-context-f26-bind-smoke.sh"
PIPELINE = ROOT / "twins/reference-917-engine/source/build_topology_context_f26.py"
F18 = ROOT / "twins/reference-917-engine/source/review_boundary_components_f18.py"
CONTRACT = ROOT / "twins/reference-917-engine/topology-context-contract-f26.json"
WORKFLOW = ROOT / ".github/workflows/topology-context-f26-image.yml"


class TopologyContextF26ImageTests(unittest.TestCase):
    def test_requirements_has_one_exact_amd64_wheel_hash(self):
        lines = [line for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines() if line]
        self.assertEqual(
            lines,
            [
                "numpy==2.2.6 --hash=sha256:fd83c01228a688733f1ded5201c678f0c53ecc1006ffbc404db9f7a899ac6249"
            ],
        )

    def test_dockerfile_is_pinned_minimal_amd64_non_root_and_smoked_offline(self):
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        for fragment in (
            "docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e",
            "python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef",
            'test "${TARGETARCH}" = "amd64"',
            "--only-binary=:all:",
            "--require-hashes",
            "--no-deps",
            "CONTEXT_UID=9174",
            "CONTEXT_GID=9174",
            "USER ${CONTEXT_UID}:${CONTEXT_GID}",
            "RUN --network=none /usr/local/bin/topology-context-f26-smoke",
            'CMD ["/usr/local/bin/topology-context-f26-smoke"]',
            "no scans, datasets or model weights",
        ):
            self.assertIn(fragment, dockerfile)
        copy_lines = [line.strip() for line in dockerfile.splitlines() if line.startswith("COPY ")]
        self.assertEqual(
            copy_lines,
            [
                "COPY containers/topology-context-f26-requirements.txt /tmp/topology-context-f26-requirements.txt",
                "COPY twins/reference-917-engine/topology-context-contract-f26.json /opt/3dprinting993/twins/reference-917-engine/topology-context-contract-f26.json",
                "COPY twins/reference-917-engine/source/review_boundary_components_f18.py /opt/3dprinting993/twins/reference-917-engine/source/review_boundary_components_f18.py",
                "COPY twins/reference-917-engine/source/build_topology_context_f26.py /opt/3dprinting993/twins/reference-917-engine/source/build_topology_context_f26.py",
                "COPY containers/topology-context-f26-smoke.py /usr/local/bin/topology-context-f26-smoke",
            ],
        )
        for forbidden in (
            "apt-get",
            "COPY .",
            "COPY work",
            "COPY raw-scans",
            "trimesh",
            "matplotlib",
            "freecad",
            "blender",
            "cuda",
            "nvidia",
            "physicsnemo",
            "openssh",
            "EXPOSE",
        ):
            self.assertNotIn(forbidden.lower(), dockerfile.lower())

    def test_docker_context_is_an_exact_allow_list_without_geometry(self):
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
                "!containers/topology-context-f26-requirements.txt",
                "!containers/topology-context-f26-smoke.py",
                "!twins/",
                "!twins/reference-917-engine/",
                "!twins/reference-917-engine/topology-context-contract-f26.json",
                "!twins/reference-917-engine/source/",
                "!twins/reference-917-engine/source/review_boundary_components_f18.py",
                "!twins/reference-917-engine/source/build_topology_context_f26.py",
            ],
        )
        self.assertNotIn("!work/", patterns)
        self.assertNotIn("!raw-scans/", patterns)
        self.assertFalse(any(Path(pattern.lstrip("!")).suffix.lower() in {".obj", ".ply", ".stl", ".usd"} for pattern in patterns))

    def test_smoke_uses_only_synthetic_geometry_and_audits_the_bundle(self):
        smoke = SMOKE.read_text(encoding="utf-8")
        ast.parse(smoke)
        for fragment in (
            'PIPELINE = SOURCE_ROOT / "build_topology_context_f26.py"',
            'F18_PIPELINE = SOURCE_ROOT / "review_boundary_components_f18.py"',
            'CONTRACT = APPLICATION_ROOT / "twins/reference-917-engine/topology-context-contract-f26.json"',
            "write_open_cylinder_obj",
            '"--fixture-mode"',
            '"--expected-components", "2"',
            '"--batch-size", "1"',
            "deterministic_tree_byte_identical",
            "all_payload_hashes_verified",
            'text.count(\'class="orthographic-view"\') == 4',
            'text.count(\'class="global-locator"\') == 4',
            '"confirmed_interfaces": 0',
            '"status": "passed_synthetic_fixture_only"',
            "network_isolation_evidence",
            "expected_files",
            "forbidden_asset_files",
            "secret_named_files",
            "sys.dont_write_bytecode = True",
            'parser.add_argument("--export-fixture", type=Path)',
            '"status": "synthetic_bind_fixture_exported"',
        ):
            self.assertIn(fragment, smoke)
        for forbidden in (
            "917-engine-case-with-cylinders.obj",
            "428c4143d073f8330022f2fecbd1ac1ee7784d4f1565f1160020448dbdffa0ae",
            "boundary-components-f18.ply",
            "/workspace/input/engine.obj",
        ):
            self.assertNotIn(forbidden, smoke)

    def test_workflow_is_manual_attested_anonymous_and_runtime_hardened(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for fragment in (
            "workflow_dispatch:",
            "runs-on: ubuntu-24.04",
            "platforms: linux/amd64",
            "provenance: mode=max",
            "sbom: true",
            "steps.build.outputs.digest",
            "for attempt in 1 2 3 4 5",
            "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
            "docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f",
            "docker/login-action@c94ce9fb468520275223c153574b00df6fe4bcc9",
            "docker/build-push-action@10e90e3645eae34f1e60eeb005ba3a3d33f178e8",
            "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
            '.subject.digest == $subject',
            '.request.root.request.args["vcs:source"] == $source',
            '.request.root.request.args["vcs:revision"] == $revision',
            "SPDX-2.3",
            "CC0-1.0",
            'ascii_downcase) == "numpy" and .versionInfo == "2.2.6"',
            "docker pull --platform linux/amd64",
            "--network none --read-only",
            "--tmpfs /tmp:rw,noexec,nosuid,size=128m",
            "--pids-limit 64",
            "--cap-drop ALL",
            "--security-opt no-new-privileges",
            "DOCKER_CONFIG=\"${anonymous_config}\"",
            "DOCKER_CONFIG=\"${anonymous_config}\" docker pull --platform linux/amd64",
            "DOCKER_CONFIG=\"${anonymous_config}\" docker run --rm --platform linux/amd64",
            "topology-context-f26-bind-smoke.sh",
            ".status == \"passed_synthetic_bind_mount_fixture_only\"",
            ".input_mount_read_only == true",
            ".output_mount_read_write == true",
            ".output_owned_by_runtime_uid == true",
            ".checks.topological_ring_count == 2",
            ".checks.orthographic_views_per_component == 4",
            ".checks.global_locators_per_component == 4",
            ".checks.all_payload_hashes_verified == true",
            ".checks.deterministic_tree_byte_identical == true",
            "all(.release_gates[]; . == false)",
        ):
            self.assertIn(fragment, workflow)
        self.assertNotIn(":latest", workflow)
        self.assertNotIn("vast", workflow.lower())
        for forbidden in (
            "raw-scans",
            "boundary-review-f18.json",
            "boundary-components-f18.ply",
            "917-engine-case-with-cylinders.obj",
        ):
            self.assertNotIn(forbidden, workflow)
        uses = re.findall(r"^\s*uses:\s*(\S+)$", workflow, re.MULTILINE)
        self.assertGreaterEqual(len(uses), 6)
        for reference in uses:
            self.assertRegex(reference, r"^[^@]+@[0-9a-f]{40}$")

    def test_workflow_artifacts_are_image_evidence_only(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        artifact_paths: list[str] = []
        in_path = False
        path_indent = 0
        for line in workflow.splitlines():
            if re.match(r"^\s+path:\s*\|\s*$", line):
                in_path = True
                path_indent = len(line) - len(line.lstrip())
                continue
            if in_path:
                indent = len(line) - len(line.lstrip())
                if line.strip() and indent <= path_indent:
                    in_path = False
                elif line.strip():
                    artifact_paths.append(line.strip())
        self.assertTrue(artifact_paths)
        for path in artifact_paths:
            self.assertRegex(
                path,
                r"^topology-context-f26-(?:image-ref\.txt|index\.json|platform-manifest\.json|attestation-manifest\.json|provenance\.json|sbom\.json|smoke\.json|bind-smoke\.json|anonymous-smoke\.json)$",
            )
            self.assertNotRegex(path, r"boundary_[0-9]+|\.svg$|inventory|manifest-f26")

    def test_contract_does_not_pretend_the_image_is_verified(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertIsNone(contract["image"]["immutable_digest"])
        self.assertEqual(contract["image"]["platform"], "linux/amd64")
        self.assertFalse(contract["image"]["root_user_allowed"])
        self.assertFalse(contract["image"]["network_required_at_runtime"])
        self.assertFalse(contract["image"]["gpu_required"])
        self.assertTrue(all(value is False for value in contract["release_gates"].values()))

    def test_host_bind_smoke_proves_read_only_inputs_and_uid_owned_writable_output(self):
        script = BIND_SMOKE.read_text(encoding="utf-8")
        for fragment in (
            "set -euo pipefail",
            "sudo chown 9174:9174",
            "sudo chmod 0700",
            "--user 9174:9174",
            "--network none --read-only",
            "--cap-drop ALL --security-opt no-new-privileges",
            '--mount "type=bind,src=${input_dir},dst=/workspace/input,readonly"',
            '--mount "type=bind,src=${output_dir},dst=/workspace/output"',
            "--export-fixture /workspace/export",
            "mesh_after",
            "report_after",
            "input_hashes_unchanged: true",
            "output_mount_read_write: true",
            "output_owned_by_runtime_uid: true",
            "canonical_scan_used: false",
            "all(.release_gates[]; . == false)",
        ):
            self.assertIn(fragment, script)
        for forbidden in (
            "917-engine-case-with-cylinders.obj",
            "boundary-review-f18.json",
            "raw-scans",
        ):
            self.assertNotIn(forbidden, script)


if __name__ == "__main__":
    unittest.main()
