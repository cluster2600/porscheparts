"""Tests statiques de l'image CPU F23 du workpack de revue humaine."""

from __future__ import annotations

import ast
import hashlib
import json
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
LOCK = ROOT / "containers/boundary-review-f23.lock.json"


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
            "boundary-review-f23.lock.json",
            "sha256:860fb1c481a8a4b72cf14d9f1d15d65b9adf327cf268ebbcc26da127427126c9",
            "33580635075",
        ):
            self.assertIn(fragment.lower(), document.lower())

    def test_lock_pins_exact_public_image_run_and_attestations(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        image = lock["image"]
        verification = lock["verification"]
        self.assertEqual(lock["phase"], "F23")
        self.assertEqual(
            image["digest"],
            "sha256:860fb1c481a8a4b72cf14d9f1d15d65b9adf327cf268ebbcc26da127427126c9",
        )
        self.assertEqual(
            image["immutable_reference"],
            f"{image['repository']}@{image['digest']}",
        )
        self.assertEqual(image["index"]["size_bytes"], 857)
        self.assertEqual(image["index"]["platform_manifest_count"], 1)
        self.assertEqual(image["index"]["attestation_manifest_count"], 1)
        self.assertEqual(image["platform"]["architecture"], "amd64")
        self.assertEqual(image["platform"]["user"], "9173:9173")
        self.assertFalse(image["platform"]["gpu_required"])
        self.assertEqual(
            image["attestation_manifest"]["subject_manifest_digest"],
            image["manifest"]["digest"],
        )
        predicates = {
            item["predicate_type"]: item
            for item in image["attestation_manifest"]["predicate_layers"]
        }
        self.assertEqual(set(predicates), {"https://spdx.dev/Document", "https://slsa.dev/provenance/v1"})
        self.assertEqual(
            predicates["https://slsa.dev/provenance/v1"]["digest"],
            verification["provenance"]["layer_digest"],
        )
        self.assertEqual(
            predicates["https://spdx.dev/Document"]["digest"],
            verification["sbom"]["layer_digest"],
        )
        workflow = verification["workflow"]
        self.assertEqual(workflow["run_id"], 33580635075)
        self.assertEqual(workflow["job_id"], 100093974333)
        self.assertEqual(workflow["head_sha"], "1ae15656080df2a1042db15fdc2dff2881c474a2")
        self.assertEqual(workflow["conclusion"], "success")
        self.assertTrue(verification["anonymous_exact_digest_access"])
        self.assertTrue(verification["published_digest_pulled"])
        self.assertFalse(verification["cryptographic_signature_verified"])

    def test_lock_recomputes_manifest_counts_sizes_and_evidence_metadata(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        manifest = lock["image"]["manifest"]
        layers = manifest["layers"]
        self.assertEqual(manifest["layer_count"], len(layers))
        self.assertEqual(manifest["compressed_size_bytes"], sum(item["size_bytes"] for item in layers))
        largest = max(layers, key=lambda item: item["size_bytes"])
        self.assertEqual(manifest["largest_layer_digest"], largest["digest"])
        self.assertEqual(manifest["largest_layer_bytes"], largest["size_bytes"])
        expected_evidence = {
            "boundary-review-f23-index.json": (
                "860fb1c481a8a4b72cf14d9f1d15d65b9adf327cf268ebbcc26da127427126c9",
                857,
            ),
            "boundary-review-f23-platform-manifest.json": (
                "293add3960b56029cef05be34d0b3c3d437ce659d77a57c96a7e318e300d498b",
                2185,
            ),
            "boundary-review-f23-attestation-manifest.json": (
                "2252a5eca14ae74549d4e519e705d4674c05c3172e846294cc39c39421c543b2",
                1112,
            ),
            "boundary-review-f23-provenance.json": (
                "7c7f119a169f928551627268aede70e852412a89a833702f4ada7558e77670ee",
                32877,
            ),
            "boundary-review-f23-sbom.json": (
                "a3ddad59b7f9a31048262fdf84303a17e8ba6cb0ef25948a2452b46066e82622",
                3271510,
            ),
            "boundary-review-f23-smoke.json": (
                "739670b7aeace8db7cb9d126c8653275ad356adf774db061e245cf738be93eb4",
                2508,
            ),
            "boundary-review-f23-image-ref.txt": (
                "4889f74944ac5c69f2f6be1b5a85c9a32ca6c1b575163939f50f5cfe5161c245",
                126,
            ),
        }
        actual_evidence = {
            item["name"]: (item["sha256"], item["size_bytes"])
            for item in lock["verification"]["evidence_files"]
        }
        self.assertEqual(actual_evidence, expected_evidence)
        self.assertEqual(
            actual_evidence["boundary-review-f23-index.json"][0],
            lock["image"]["digest"].removeprefix("sha256:"),
        )
        artifact = lock["verification"]["evidence_artifact"]
        self.assertEqual(artifact["id"], 9828265818)
        self.assertEqual(artifact["digest"], "sha256:6fc0cb96de6d44415be0553b3d9e068ee8a61b8ef1fa101552546e4b69d9daa3")
        self.assertEqual(artifact["size_bytes"], 304319)
        self.assertFalse(artifact["expired"])
        self.assertEqual(lock["verification"]["sbom"]["package_count"], 114)
        self.assertEqual(lock["verification"]["sbom"]["file_count"], 3235)
        self.assertEqual(lock["verification"]["sbom"]["relationship_count"], 3807)

    def test_lock_rereads_exact_recipe_inputs(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        inputs = lock["recipe"]["inputs"]
        self.assertEqual(len(inputs), 5)
        self.assertEqual(len({item["path"] for item in inputs}), len(inputs))
        for item in inputs:
            path = ROOT / item["path"]
            self.assertTrue(path.is_file(), item["path"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                item["sha256"],
                item["path"],
            )
        self.assertEqual(
            lock["recipe"]["workflow_head_sha"],
            lock["verification"]["workflow"]["head_sha"],
        )
        self.assertTrue(lock["verification"]["provenance"]["frontend_digest_present"])
        self.assertTrue(lock["verification"]["provenance"]["base_image_digest_present"])

    def test_lock_opens_only_image_and_smoke_gates_and_contains_no_private_assets(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(
            {name for name, value in lock["release_gates"].items() if value},
            {"immutable_public_image_verified", "linux_amd64_offline_smoke_verified"},
        )
        smoke = lock["verification"]["offline_smoke"]
        self.assertEqual(smoke["status"], "passed_synthetic_fixture_only")
        self.assertEqual(smoke["confirmed_interface_count"], 0)
        self.assertTrue(smoke["json_byte_identical"])
        self.assertTrue(smoke["csv_byte_identical"])
        self.assertTrue(smoke["svg_byte_identical"])
        bundled = lock["bundled_assets"]
        for field in (
            "raw_scans",
            "derived_scan_geometry",
            "f18_reports",
            "ply_files",
            "real_workpacks",
            "datasets",
            "model_weights",
            "secrets",
            "synthetic_fixtures_persisted_in_image",
        ):
            self.assertFalse(bundled[field], field)
        serialized = LOCK.read_text(encoding="utf-8")
        for forbidden in (
            "boundary-review-f18",
            "boundary-components-f18",
            "8208c2fec6561261904c48bb449a1bd50d679e370ee7b4a19a86d78ba265450e",
            "822e7d8ea54fa69f44658bd0b7b29dfb1fb4e4e15b3f1c73d4f45cedc03e2451",
            "raw-scans/",
            "work/917-engine/",
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
