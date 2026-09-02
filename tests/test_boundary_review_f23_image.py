"""Tests statiques de l'image CPU F23 du workpack de revue humaine."""

from __future__ import annotations

import ast
import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "containers/boundary-review-f23.Dockerfile"
DOCKERIGNORE = ROOT / "containers/boundary-review-f23.Dockerfile.dockerignore"
SMOKE = ROOT / "containers/boundary-review-f23-smoke.py"
PIPELINE = ROOT / "twins/reference-917-engine/source/build_boundary_review_workpack_f23.py"
WORKFLOW = ROOT / ".github/workflows/boundary-review-f23-image.yml"
DOC = ROOT / "docs/917_BOUNDARY_REVIEW_WORKPACK_F23.md"


class BoundaryReviewF23ImageTests(unittest.TestCase):
    def test_dockerfile_is_pinned_amd64_non_root_and_stdlib_only(self):
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        for fragment in (
            "docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e",
            "python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef",
            'test "${TARGETARCH}" = "amd64"',
            "REVIEW_UID=9173",
            "REVIEW_GID=9173",
            "USER ${REVIEW_UID}:${REVIEW_GID}",
            "RUN --network=none /usr/local/bin/boundary-review-f23-smoke",
            'CMD ["/usr/local/bin/boundary-review-f23-smoke"]',
            "no scans, geometry, datasets or model weights",
        ):
            self.assertIn(fragment, dockerfile)
        copy_lines = [line.strip() for line in dockerfile.splitlines() if line.startswith("COPY ")]
        self.assertEqual(
            copy_lines,
            [
                "COPY twins/reference-917-engine/source/build_boundary_review_workpack_f23.py /opt/3dprinting993/twins/reference-917-engine/source/build_boundary_review_workpack_f23.py",
                "COPY containers/boundary-review-f23-smoke.py /usr/local/bin/boundary-review-f23-smoke",
            ],
        )
        for forbidden in (
            "apt-get",
            "pip install",
            "COPY .",
            "COPY raw-scans",
            "COPY work",
            "boundary-components-f18.ply",
            "boundary-review-f18.json",
            "cuda",
            "nvidia",
            "physicsnemo",
            "numpy",
            "pandas",
            "matplotlib",
            "blender",
            "openssh",
            "EXPOSE",
        ):
            self.assertNotIn(forbidden.lower(), dockerfile.lower())

    def test_dockerfile_specific_context_is_an_exact_allow_list(self):
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
                "!containers/boundary-review-f23-smoke.py",
                "!twins/",
                "!twins/reference-917-engine/",
                "!twins/reference-917-engine/source/",
                "!twins/reference-917-engine/source/build_boundary_review_workpack_f23.py",
            ],
        )
        self.assertNotIn("!work/", patterns)
        self.assertNotIn("!raw-scans/", patterns)

    def test_pipeline_imports_only_python_standard_library(self):
        tree = ast.parse(PIPELINE.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
        self.assertEqual(
            imports,
            {
                "__future__",
                "argparse",
                "csv",
                "datetime",
                "hashlib",
                "html",
                "io",
                "json",
                "math",
                "os",
                "pathlib",
                "re",
                "stat",
                "struct",
                "typing",
            },
        )

    def test_smoke_compiles_and_exercises_real_pipeline_with_synthetic_assets(self):
        smoke = SMOKE.read_text(encoding="utf-8")
        ast.parse(smoke)
        for fragment in (
            'PIPELINE = PIPELINE_ROOT / "build_boundary_review_workpack_f23.py"',
            'ply = directory / "synthetic-boundaries.ply"',
            'report_path = directory / "synthetic-f18.json"',
            '"--expected-component-count", "9"',
            '"--expected-candidate-count", "3"',
            '"--secondary-count", "3"',
            "ElementTree.fromstring",
            "csv.DictReader",
            "workpack_path.read_bytes() == (second / workpack_path.name).read_bytes()",
            '"--validate-review-file"',
            '"report SHA-256 mismatch"',
            '"output already exists"',
            '"status": "passed_synthetic_fixture_only"',
            '"network_isolation_evidence"',
            '"python_standard_library_only_no_packages_installed_by_f23"',
            '"confirmed_interfaces": 0',
        ):
            self.assertIn(fragment, smoke)
        for forbidden in (
            "/workspace/input/boundary-review-f18.json",
            "8208c2fec6561261904c48bb449a1bd50d679e370ee7b4a19a86d78ba265450e",
            "822e7d8ea54fa69f44658bd0b7b29dfb1fb4e4e15b3f1c73d4f45cedc03e2451",
        ):
            self.assertNotIn(forbidden, smoke)

    def test_workflow_pins_supply_chain_and_hardens_runtime(self):
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
            ".subject.digest == $subject",
            '.request.root.request.args["vcs:source"] == $source',
            '.request.root.request.args["vcs:revision"] == $revision',
            "SPDX-2.3",
            "CC0-1.0",
            "docker pull --platform linux/amd64",
            "--network none --read-only",
            "--tmpfs /tmp:rw,noexec,nosuid,size=64m",
            "--pids-limit 64",
            "--cap-drop ALL",
            "--security-opt no-new-privileges",
            'test "$(docker image inspect --format \'{{.Config.User}}\'',
            "DOCKER_CONFIG=\"${anonymous_config}\"",
            "test -s boundary-review-f23-attestation-manifest.json",
            "test -s boundary-review-f23-sbom.json",
            ".checks.deterministic_outputs.csv_byte_identical == true",
            ".checks.deterministic_outputs.svg_byte_identical == true",
            ".checks.deterministic_outputs.json_byte_identical == true",
            "all(.release_gates[]; . == false)",
        ):
            self.assertIn(fragment, workflow)
        self.assertNotIn(":latest", workflow)
        self.assertNotIn("vast", workflow.lower())
        self.assertNotIn("raw-scans", workflow)
        self.assertNotIn("boundary-components-f18.ply", workflow)
        self.assertNotIn("boundary-review-f18.json", workflow)
        uses = re.findall(r"^\s*uses:\s*(\S+)$", workflow, re.MULTILINE)
        self.assertGreaterEqual(len(uses), 6)
        for reference in uses:
            self.assertRegex(reference, r"^[^@]+@[0-9a-f]{40}$")
            self.assertNotRegex(reference, r"@v\d")

    def test_workflow_artifacts_cannot_include_real_workpack_outputs(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        artifact_paths = []
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
                r"^boundary-review-f23-(?:image-ref\.txt|index\.json|platform-manifest\.json|attestation-manifest\.json|provenance\.json|sbom\.json|smoke\.json)$",
            )

    def test_documentation_separates_container_from_physical_authority(self):
        document = DOC.read_text(encoding="utf-8")
        for fragment in (
            "Image Docker F23",
            "python:3.12.14-slim-bookworm",
            "linux/amd64",
            "bibliothèque standard",
            "--network none",
            "--read-only",
            "entrée en lecture seule",
            "sortie en lecture-écriture",
            "digest immuable",
            "GHCR",
            "aucun scan",
            "fixture synthétique",
            "SBOM",
            "ne prouve pas",
        ):
            self.assertIn(fragment.lower(), document.lower())


if __name__ == "__main__":
    unittest.main()
