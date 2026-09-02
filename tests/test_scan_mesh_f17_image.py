"""Tests statiques de l'image CPU de traitement de maillage F17."""

from __future__ import annotations

import ast
import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "containers/scan-mesh-f17.Dockerfile"
REQUIREMENTS = ROOT / "containers/scan-mesh-f17-requirements.txt"
SMOKE = ROOT / "containers/scan-mesh-f17-smoke.py"
SEGMENT = ROOT / "twins/reference-917-engine/source/segment_engine.py"
WORKFLOW = ROOT / ".github/workflows/scan-mesh-f17-image.yml"
DOC = ROOT / "docs/917_SCAN_MESH_CONTAINER_F17.md"


class ScanMeshF17ImageTests(unittest.TestCase):
    def test_dockerfile_est_epingle_amd64_non_root_et_a_portee_minimale(self):
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        for fragment in (
            "docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e",
            "python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2",
            'test "${TARGETARCH}" = "amd64"',
            "libgl1=1.6.0-1",
            "libopengl0=1.6.0-1",
            "--no-deps",
            "--only-binary=:all:",
            "--require-hashes",
            "MESH_UID=9177",
            "MESH_GID=9177",
            "USER ${MESH_UID}:${MESH_GID}",
            "scan-mesh-f17-smoke",
            "RUN --network=none /usr/local/bin/scan-mesh-f17-smoke",
        ):
            self.assertIn(fragment, dockerfile)
        copy_lines = [line.strip() for line in dockerfile.splitlines() if line.startswith("COPY ")]
        self.assertEqual(
            copy_lines,
            [
                "COPY twins/reference-917-engine/source/prepare_scan.py /opt/3dprinting993/twins/reference-917-engine/source/prepare_scan.py",
                "COPY twins/reference-917-engine/source/analyze_boundaries.py /opt/3dprinting993/twins/reference-917-engine/source/analyze_boundaries.py",
                "COPY twins/reference-917-engine/source/segment_engine.py /opt/3dprinting993/twins/reference-917-engine/source/segment_engine.py",
                "COPY containers/scan-mesh-f17-smoke.py /usr/local/bin/scan-mesh-f17-smoke",
            ],
        )
        for forbidden in (
            "COPY .",
            "COPY raw-scans",
            "COPY work",
            "cuda",
            "nvidia",
            "physicsnemo",
            "blender",
            "openfoam",
            "gmsh",
            "openssh",
            "EXPOSE",
        ):
            self.assertNotIn(forbidden.lower(), dockerfile.lower())

    def test_dependances_et_hashes_sont_exacts(self):
        requirements = REQUIREMENTS.read_text(encoding="utf-8")
        expected = {
            "numpy": (
                "2.5.2",
                "3cdec01fa790a186d430433fdd4d4ffb70eed6f0eeb4bf05c8dbe2dce0a9bcb8",
            ),
            "scipy": (
                "1.18.1",
                "f55fa87b6c612ecd6b058f167c53231b1d14e412efe361d3d6e38b3631c73218",
            ),
            "trimesh": (
                "5.1.0",
                "0fa85d1d131e321b683c00747c20090200b92071298b905ea588f609eb204c89",
            ),
            "pymeshlab": (
                "2025.7.post1",
                "bc453d89b114671affc747991a939b257d2320b71885b31213190c64081f5c35",
            ),
            "rtree": (
                "1.4.1",
                "12de4578f1b3381a93a655846900be4e3d5f4cd5e306b8b00aa77c1121dc7e8c",
            ),
        }
        pins = dict(re.findall(r"^([a-z0-9_-]+)==([^ \\\n]+)", requirements, re.MULTILINE))
        hashes = re.findall(r"--hash=sha256:([0-9a-f]{64})", requirements)
        self.assertEqual(pins, {name: version for name, (version, _) in expected.items()})
        self.assertEqual(hashes, [digest for _, digest in expected.values()])
        self.assertEqual(requirements.count("--hash=sha256:"), 5)

    def test_smoke_compile_et_exerce_les_chemins_geometriques_reels(self):
        source = SMOKE.read_text(encoding="utf-8")
        ast.parse(source)
        for fragment in (
            "prepare.component_labels(compound)",
            "prepare.topology(compound)",
            "prepare.simplify(decimation_source, decimation_output, 160)",
            "prepare.deviation(compound, decimated)",
            "import rtree",
            "boundary_components",
            "expected two boundary loops",
            "signatures.isdisjoint(other)",
            "set().union(*part_signatures) == input_signatures",
            "network_isolation_evidence()",
            '"external_routed_interfaces"',
            '"scope": str(scope)',
            '"secret_named_files"',
            '"rejected_invalid_interface_contracts": 4',
            '"status": "passed_synthetic_fixture_only"',
            '"semantic_segmentation": False',
            '"watertight_geometry": False',
            '"manufacturing_ready": False',
            '"cryptographic_signature_verified": False',
            '"vast_launch_authorized": False',
        ):
            self.assertIn(fragment, source)

    def test_segmentateur_refuse_interfaces_non_provenancees_ou_invalides(self):
        source = SEGMENT.read_text(encoding="utf-8")
        ast.parse(source)
        for fragment in (
            'SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")',
            "np.all(np.isfinite(array))",
            "frame @ frame.T",
            "np.linalg.det(frame)",
            "must be direct (determinant +1)",
            "must contain exactly six centres in canonical mode",
            'parser.add_argument("--input-sha256")',
            'parser.add_argument("--interfaces-sha256")',
            '"--synthetic-fixture-mode"',
            '"provenance_hashes_matched_external_expectations": not args.synthetic_fixture_mode',
        ):
            self.assertIn(fragment, source)

    def test_workflow_garde_digest_slsa_sbom_anonyme_et_runtime_durci(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for fragment in (
            "workflow_dispatch:",
            "runs-on: ubuntu-24.04",
            "platforms: linux/amd64",
            "provenance: mode=max",
            "sbom: true",
            "steps.build.outputs.digest",
            "tag_digest",
            "for attempt in 1 2 3 4 5",
            'uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262',
            'uses: docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f',
            'uses: docker/login-action@c94ce9fb468520275223c153574b00df6fe4bcc9',
            'uses: docker/build-push-action@10e90e3645eae34f1e60eeb005ba3a3d33f178e8',
            'uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02',
            ".subject.digest == $subject",
            '.request.root.request.args["vcs:source"] == $source',
            '.request.root.request.args["vcs:revision"] == $revision',
            ".SLSA.buildDefinition.buildType",
            ".SLSA.runDetails.builder.id",
            ".SLSA.buildDefinition.resolvedDependencies",
            "SPDX-2.3",
            "CC0-1.0",
            "docker pull --platform linux/amd64",
            "--network none --read-only",
            "--pids-limit 256",
            "--cap-drop ALL",
            "--security-opt no-new-privileges",
            "DOCKER_CONFIG=\"${anonymous_config}\"",
            "test -s scan-mesh-f17-attestation-manifest.json",
            "test -s scan-mesh-f17-sbom.json",
            "all(.release_gates[]; . == false)",
        ):
            self.assertIn(fragment, workflow)
        self.assertNotIn(":latest", workflow)
        self.assertNotIn("vast", workflow.lower())
        self.assertNotIn("verify_anonymous", workflow)
        uses = re.findall(r"^\s*uses:\s*(\S+)$", workflow, re.MULTILINE)
        self.assertGreaterEqual(len(uses), 6)
        for reference in uses:
            self.assertRegex(reference, r"^[^@]+@[0-9a-f]{40}$")
            self.assertNotRegex(reference, r"@v\d")

    def test_documentation_separe_cpu_gpu_et_reste_fail_closed(self):
        document = DOC.read_text(encoding="utf-8")
        for fragment in (
            "```mermaid",
            "linux/amd64",
            "sans GPU",
            "prepare_scan.py",
            "analyze_boundaries.py",
            "segment_engine.py",
            "deux boucles",
            "aucun scan",
            "entrée brute en lecture seule",
            "sortie en lecture-écriture",
            "PhysicsNeMo",
            "Vast.ai",
            "ne prouve pas",
            "digest immuable",
            "n'est pas une promesse de build bit à bit reproductible",
            "matrice 3 x 3 orthonormale",
            "exactement six centres par banc",
            "cryptographic_signature_verified",
            "n'est pas un scanner",
            "32 Gio",
        ):
            self.assertIn(fragment, document)
        self.assertNotIn("image `linux/amd64` reproductible", document)


if __name__ == "__main__":
    unittest.main()
