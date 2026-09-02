"""Tests statiques de l'image minimale d'auteur CAO F28."""

from __future__ import annotations

import ast
import bz2
import gzip
import hashlib
import io
import json
import lzma
import re
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "containers/cad-author-f28.Dockerfile"
DOCKERIGNORE = ROOT / "containers/cad-author-f28.Dockerfile.dockerignore"
REQUIREMENTS = ROOT / "containers/cad-author-f28-requirements.txt"
SYSTEM_PACKAGES = ROOT / "containers/cad-author-f28-system-packages.sha256"
SMOKE = ROOT / "containers/cad-author-f28-smoke.py"
WORKFLOW = ROOT / ".github/workflows/cad-author-f28-image.yml"
DOC = ROOT / "docs/917_CAD_AUTHOR_IMAGE_F28.md"


class CadAuthorF28ImageTests(unittest.TestCase):
    def test_dockerfile_is_pinned_amd64_non_root_and_minimal(self):
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        for fragment in (
            "docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e",
            "python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef",
            'test "${TARGETARCH}" = "amd64"',
            "libgl1=1.6.0-1",
            "fontconfig-config=2.14.1-4",
            "apt-get download",
            "sha256sum --check /tmp/cad-author-f28-system-packages.sha256",
            'dpkg-deb --extract "${package}" /runtime',
            "--only-binary=:all:",
            "--require-hashes",
            "--no-deps",
            "python -m pip check",
            'CAD_UID=9178',
            'CAD_GID=9178',
            'HOME=/tmp',
            'XDG_CACHE_HOME=/tmp/cad-author-f28-cache',
            "cad-author:x:%s:%s:CAD author:/tmp:/usr/sbin/nologin",
            "USER ${CAD_UID}:${CAD_GID}",
            "RUN --network=none /bin/bash -euo pipefail",
            'if test -s "${stderr}"; then cat "${stderr}" >&2; exit 1; fi',
            'org.opencontainers.image.licenses="NOASSERTION"',
            'CMD ["python", "/opt/cad-author-f28/cad-author-f28-smoke.py"]',
            "Aucun scan, modele vehicule, solveur, poids de modele ou secret",
        ):
            self.assertIn(fragment, dockerfile)
        copy_lines = [line.strip() for line in dockerfile.splitlines() if line.startswith("COPY ")]
        self.assertEqual(
            copy_lines,
            [
                "COPY --from=system-libs /runtime/lib/x86_64-linux-gnu/ /usr/lib/x86_64-linux-gnu/",
                "COPY --from=system-libs /runtime/usr/lib/x86_64-linux-gnu/ /usr/lib/x86_64-linux-gnu/",
                "COPY --from=system-libs /runtime/usr/share/X11/ /usr/share/X11/",
                "COPY --from=system-libs /runtime/etc/fonts/ /etc/fonts/",
                "COPY --from=system-libs /runtime/usr/share/fontconfig/ /usr/share/fontconfig/",
                "COPY --from=system-libs /runtime/usr/share/doc/ /usr/share/doc/",
                "COPY --from=python-cad /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/",
                "COPY containers/cad-author-f28-requirements.txt /opt/cad-author-f28/cad-author-f28-requirements.txt",
                "COPY containers/cad-author-f28-smoke.py /opt/cad-author-f28/cad-author-f28-smoke.py",
                "COPY containers/cad-author-f28-system-packages.sha256 /opt/cad-author-f28/cad-author-f28-system-packages.sha256",
            ],
        )
        for forbidden in (
            "COPY .",
            "raw-scans",
            "COPY work",
            "freecad",
            "openscad",
            "gmsh",
            "openfoam",
            "physicsnemo",
            "omniverse",
            "cuda",
            "nvidia",
            "openssh",
            "EXPOSE",
            "ENTRYPOINT",
            "apt-get install",
        ):
            self.assertNotIn(forbidden.lower(), dockerfile.lower())

    def test_dockerfile_specific_context_is_exact_allow_list(self):
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
                "!containers/cad-author-f28-requirements.txt",
                "!containers/cad-author-f28-smoke.py",
                "!containers/cad-author-f28-system-packages.sha256",
            ],
        )
        self.assertNotIn("!work/", patterns)
        self.assertNotIn("!raw-scans/", patterns)
        self.assertNotIn("!twins/", patterns)

    def test_wheel_lock_is_complete_unique_and_critical_hashes_match(self):
        requirements = REQUIREMENTS.read_text(encoding="ascii")
        entries = re.findall(
            r"^([a-z0-9_.-]+)==([^ \\\n]+) \\\n\s+--hash=sha256:([0-9a-f]{64})$",
            requirements,
            re.MULTILINE,
        )
        self.assertEqual(len(entries), 46)
        self.assertEqual(len({name for name, _, _ in entries}), 46)
        self.assertEqual(len({digest for _, _, digest in entries}), 46)
        locked = {name: (version, digest) for name, version, digest in entries}
        self.assertEqual(
            locked["build123d"],
            (
                "0.11.1",
                "4e95fa7ccbdc83e624313be492e7c4f5f0eb2ea1df36130eb718bb0c25a89e10",
            ),
        )
        self.assertEqual(
            locked["cadquery-ocp-novtk"],
            (
                "7.9.3.1.1",
                "60497cf42419dd2000d323ab772937f61539f2f0a5d3ef1b288611b13254c587",
            ),
        )
        self.assertEqual(
            locked["cadquery-ocp-proxy"],
            (
                "7.9.3.1.1",
                "ca4164ec4b54956d9fc3e68c67d555b5486cb963c2f71e18df005ba16b921c91",
            ),
        )
        self.assertEqual(locked["numpy"][0], "2.5.2")
        self.assertEqual(locked["scipy"][0], "1.18.1")
        self.assertEqual(requirements.count("--hash=sha256:"), 46)
        self.assertNotIn("--extra-index-url", requirements)
        self.assertNotIn("git+", requirements)
        self.assertNotIn("http://", requirements)
        self.assertNotIn("https://", requirements)

    def test_system_library_lock_is_exact_and_avoids_mesa_llvm_payloads(self):
        source = SYSTEM_PACKAGES.read_text(encoding="ascii")
        entries = re.findall(
            r"^([0-9a-f]{64})  ([A-Za-z0-9%+_.:-]+\.deb)$",
            source,
            re.MULTILINE,
        )
        self.assertEqual(len(entries), 11)
        self.assertEqual(len({digest for digest, _ in entries}), 11)
        packages = {name for _, name in entries}
        self.assertIn("fontconfig-config_2.14.1-4_amd64.deb", packages)
        self.assertIn("libgl1_1.6.0-1_amd64.deb", packages)
        self.assertIn("libglvnd0_1.6.0-1_amd64.deb", packages)
        self.assertIn("libx11-6_2%3a1.8.4-2+deb12u2_amd64.deb", packages)
        self.assertNotRegex(source.lower(), r"mesa|llvm|dri")

    def test_size_measurement_accepts_only_valid_gzip_or_raw_tar_layers(self):
        payload = b"cad-author-f28-size-fixture\n"
        layer_stream = io.BytesIO()
        with tarfile.open(fileobj=layer_stream, mode="w") as layer_tar:
            member = tarfile.TarInfo("fixture.txt")
            member.size = len(payload)
            member.mtime = 0
            member.uid = 0
            member.gid = 0
            layer_tar.addfile(member, io.BytesIO(payload))
        raw_layer = layer_stream.getvalue()

        with tempfile.TemporaryDirectory(prefix="cad-author-f28-size-test-") as temporary:
            temporary_path = Path(temporary)

            def run_measurement(
                archive_kind: str, layer_bytes: bytes
            ) -> subprocess.CompletedProcess[str]:
                digest = hashlib.sha256(layer_bytes).hexdigest()
                layer_path = (
                    f"blobs/sha256/{digest}"
                    if archive_kind != "legacy-tar"
                    else f"{digest}/layer.tar"
                )
                manifest = json.dumps([{"Layers": [layer_path]}]).encode("ascii")
                archive_path = temporary_path / f"{archive_kind}.tar"
                with tarfile.open(archive_path, mode="w") as outer_tar:
                    manifest_member = tarfile.TarInfo("manifest.json")
                    manifest_member.size = len(manifest)
                    manifest_member.mtime = 0
                    outer_tar.addfile(manifest_member, io.BytesIO(manifest))
                    layer_member = tarfile.TarInfo(layer_path)
                    layer_member.size = len(layer_bytes)
                    layer_member.mtime = 0
                    outer_tar.addfile(layer_member, io.BytesIO(layer_bytes))
                return subprocess.run(
                    [
                        sys.executable,
                        str(SMOKE),
                        "--measure-image-archive",
                        str(archive_path),
                        "--local-store-bytes",
                        "12345",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )

            for archive_kind, layer_bytes in (
                ("oci-gzip", gzip.compress(raw_layer, mtime=0)),
                ("legacy-tar", raw_layer),
            ):
                completed = run_measurement(archive_kind, layer_bytes)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                report = json.loads(completed.stdout)
                self.assertEqual(report["local_store_reported_bytes"], 12345)
                self.assertEqual(report["uncompressed_layer_tar_bytes"], len(raw_layer))
                self.assertEqual(
                    report["metric_scope"],
                    "docker_local_store_plus_sum_of_uncompressed_layer_tar_streams",
                )
                self.assertEqual(
                    report["local_store_metric_note"],
                    "diagnostic_only_engine_backend_dependent_not_gated",
                )
                self.assertNotIn("local_store_reported_bytes", report["budgets"])
                self.assertEqual(report["budgets"]["uncompressed_layer_tar_bytes"], 1100000000)

            for archive_kind, layer_bytes in (
                ("reject-bzip2", bz2.compress(raw_layer)),
                ("reject-xz", lzma.compress(raw_layer, format=lzma.FORMAT_XZ)),
                ("reject-zstd", b"\x28\xb5\x2f\xfdnot-a-supported-layer"),
                ("reject-gzip-non-tar", gzip.compress(b"not a tar stream", mtime=0)),
            ):
                completed = run_measurement(archive_kind, layer_bytes)
                self.assertNotEqual(completed.returncode, 0, archive_kind)

    def test_smoke_builds_exports_reopens_and_checks_closed_solid(self):
        smoke = SMOKE.read_text(encoding="utf-8")
        ast.parse(smoke)
        for fragment in (
            "from build123d import Align, Box, Cylinder, Pos",
            "from build123d import export_step, import_step",
            "return body - cutter",
            "export_step(source, step_path)",
            "imported = import_step(step_path)",
            'solid.is_valid',
            'solid.is_manifold',
            'len(solid.shells()) == 1',
            'solid.shells()[0].is_manifold',
            '"solid_count": len(solids)',
            '"all_solids_closed"',
            'expected_volume = 20.0 * 12.0 * 8.0 - math.pi * 2.0**2 * 8.0',
            'metrics["bounds_size_mm"] == expected_bounds',
            '"created_geometry_signature_repeatable"',
            '"reopened_geometry_signature_repeatable"',
            '"step_export_sha256_recorded_not_a_reproducibility_claim"',
            '"passed_synthetic_cad_fixture_only"',
            '"canonical_scan_used": False',
            '"vehicle_geometry_used": False',
            'network_isolation_evidence()',
            'runtime_identity_and_cache_audit()',
            'fontconfig_audit()',
            'font_payload_audit()',
            'license_audit()',
            'account.pw_name == "cad-author"',
            'account.pw_dir == str(RUNTIME_HOME)',
            'os.environ.get("XDG_CACHE_HOME") == str(RUNTIME_CACHE)',
            'Path("/etc/fonts/fonts.conf")',
            '"system_font_file_count": len(system_font_files)',
            '"dependency_font_file_count": len(font_files)',
            '8b30ea7ea8a2b17fb9d5c70b5c7c37e6a9285b4f8aced4fbd646bc591dba59b3',
            'CANONICAL_EMPTY_GZIP_LAYER_SHA256',
            'unsupported non-gzip layer encoding',
            'validate_tar_stream_and_count(decoded)',
            '"package_notice_count": len(notice_paths)',
            'len(pins) == 46',
            'len(hashes) == 46',
            'len(system_entries) == 11',
            '"contains_scan_or_engine_geometry": False',
            '"contains_model_weights": False',
        ):
            self.assertIn(fragment, smoke)
        for forbidden in (
            "raw-scans/",
            "917-engine-case",
            "b48f23d64ceab",
            "428c4143d073",
        ):
            self.assertNotIn(forbidden, smoke)

    def test_workflow_gates_supply_chain_runtime_and_anonymous_digest(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for fragment in (
            "workflow_dispatch:",
            "default: false",
            "runs-on: ubuntu-24.04",
            "platforms: linux/amd64",
            "provenance: mode=max",
            "sbom: true",
            "steps.build.outputs.digest",
            "for attempt in 1 2 3 4 5",
            "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
            "docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f",
            "version: v0.36.1",
            "image=moby/buildkit@sha256:28a898719c18a33f4e8000685287fa36fd0dd9560c6440227d3a732d79bb41d8",
            "grep -F 'v0.32.2' cad-author-f28-builder.txt",
            "48af8a397ebd60178778bf63611dbcebe5f5e7a9be90eb9147b24b9587455778",
            "docker ps --filter name=buildx_buildkit",
            "docker container inspect --format '{{.Config.Image}}'",
            "docker/login-action@c94ce9fb468520275223c153574b00df6fe4bcc9",
            "docker/build-push-action@10e90e3645eae34f1e60eeb005ba3a3d33f178e8",
            "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
            ".subject.digest == $subject",
            '.request.root.request.args["vcs:source"] == $source',
            '.request.root.request.args["vcs:revision"] == $revision',
            "SPDX-2.3",
            "CC0-1.0",
            '"build123d" and .versionInfo == "0.11.1"',
            '"cadquery-ocp-novtk" and .versionInfo == "7.9.3.1.1"',
            "docker pull --platform linux/amd64",
            "--network none --read-only",
            "--tmpfs /tmp:rw,noexec,nosuid,size=128m",
            "--pids-limit 64",
            "--cap-drop ALL",
            "--security-opt no-new-privileges",
            "DOCKER_CONFIG=\"${anonymous_config}\"",
            "trap 'rm -rf -- \"${anonymous_config}\"' EXIT",
            "> cad-author-f28-smoke.json",
            "2> cad-author-f28-smoke.stderr; then",
            "cat cad-author-f28-smoke.stderr >&2",
            "test ! -s cad-author-f28-smoke.stderr",
            "test ! -s cad-author-f28-anonymous-smoke.stderr",
            "cad-author-f28-license-audit.json",
            "compressed_layer_max_bytes:275000000",
            'all(.layers[]; .mediaType == "application/vnd.oci.image.layer.v1.tar+gzip")',
            "registry_compressed",
            "local_and_uncompressed",
            "python3 containers/cad-author-f28-smoke.py",
            "--measure-image-archive",
            ".fontconfig_audit.system_font_file_count == 0",
            ".font_payload_audit.dependency_font_file_count == 1",
            "8b30ea7ea8a2b17fb9d5c70b5c7c37e6a9285b4f8aced4fbd646bc591dba59b3",
            ".checks.closed_solid_after_step_roundtrip == true",
            ".checks.canonical_scan_used == false",
            "all(.release_gates[]; . == false)",
        ):
            self.assertIn(fragment, workflow)
        self.assertNotIn(":latest", workflow)
        self.assertNotIn("raw-scans", workflow)
        self.assertNotIn("917-engine-case", workflow)
        self.assertNotIn("vast", workflow.lower())
        self.assertNotIn("cad-author-f28-measure-image-size.sh", workflow)
        uses = re.findall(r"^\s*uses:\s*(\S+)$", workflow, re.MULTILINE)
        self.assertGreaterEqual(len(uses), 6)
        for reference in uses:
            self.assertRegex(reference, r"^[^@]+@[0-9a-f]{40}$")
            self.assertNotRegex(reference, r"@v\d")
        self.assertNotIn("> >(", workflow)
        self.assertEqual(workflow.count("2> cad-author-f28-smoke.stderr; then"), 2)
        self.assertEqual(workflow.count("test ! -s cad-author-f28-smoke.stderr"), 2)
        self.assertEqual(
            workflow.count(".fontconfig_audit.system_font_file_count == 0"), 3
        )
        self.assertEqual(
            workflow.count(".checks.vehicle_geometry_used == false"), 3
        )

    def test_workflow_artifacts_are_evidence_only(self):
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
                r"^cad-author-f28-(?:image-ref\.txt|builder\.txt|index\.json|platform-manifest\.json|attestation-manifest\.json|anonymous-smoke\.json|anonymous-smoke\.stderr|license-audit\.json|provenance\.json|sbom\.json|size\.json|smoke\.json|smoke\.stderr)$",
            )

    def test_documentation_separates_cad_author_from_other_toolchains(self):
        document = DOC.read_text(encoding="utf-8")
        for fragment in (
            "```mermaid",
            "build123d 0.11.1",
            "OCCT 7.9.3",
            "46 roues",
            "onze paquets",
            "fontconfig",
            "8b30ea7ea8a2b17fb9d5c70b5c7c37e6a9285b4f8aced4fbd646bc591dba59b3",
            "bzip2",
            "notices",
            "stderr",
            "BuildKit `v0.32.2`",
            "48af8a397ebd60178778bf63611dbcebe5f5e7a9be90eb9147b24b9587455778",
            "layer.tar",
            "linux/amd64",
            "FreeCAD",
            "OpenSCAD",
            "Gmsh",
            "OpenFOAM",
            "PhysicsNeMo",
            "Omniverse",
            "aucune géométrie du moteur",
            "aucun scan",
            "fixture",
            "unique coque",
            "digest exact",
            "pull et le smoke avec un `DOCKER_CONFIG` anonyme",
            "n'est pas présenté comme une promesse de build byte-identique",
            "aucun digest public F28",
            "tous les gates",
        ):
            self.assertIn(fragment, document)


if __name__ == "__main__":
    unittest.main()
