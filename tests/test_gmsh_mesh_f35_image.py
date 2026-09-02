#!/usr/bin/env python3
"""Gardes statiques de la recette Gmsh F35."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTAINERS = ROOT / "containers"
DOCKERFILE = CONTAINERS / "gmsh-mesh-f35.Dockerfile"
IGNORE = CONTAINERS / "gmsh-mesh-f35.Dockerfile.dockerignore"
REQUIREMENTS = CONTAINERS / "gmsh-mesh-f35.requirements.txt"
SYSTEM_HASHES = CONTAINERS / "gmsh-mesh-f35-system-packages.sha256"
SMOKE = CONTAINERS / "gmsh-mesh-f35-smoke.py"
WORKFLOW = ROOT / ".github" / "workflows" / "gmsh-mesh-f35-image.yml"


class GmshMeshF35ImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        cls.ignore = IGNORE.read_text(encoding="utf-8")
        cls.requirements = REQUIREMENTS.read_text(encoding="utf-8")
        cls.smoke = SMOKE.read_text(encoding="utf-8")
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_platform_base_and_frontend_are_digest_pinned(self) -> None:
        self.assertIn("docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e", self.dockerfile)
        self.assertIn("python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef", self.dockerfile)
        self.assertGreaterEqual(self.dockerfile.count('test "${TARGETARCH}" = "amd64"'), 3)

    def test_python_and_debian_artifacts_are_exactly_hashed(self) -> None:
        expected = (
            "gmsh==4.15.2 \\\n"
            "    --hash=sha256:4076a948ce22625330d1413d4982e22b5c69fc2f0f7951f5df64c778cf54108c"
        )
        self.assertEqual(self.requirements.strip(), expected)
        self.assertIn("--only-binary=:all:", self.dockerfile)
        self.assertIn("--require-hashes", self.dockerfile)
        self.assertIn("--no-deps", self.dockerfile)
        hash_lines = [
            line
            for line in SYSTEM_HASHES.read_text(encoding="utf-8").splitlines()
            if line
        ]
        self.assertEqual(len(hash_lines), 24)
        for line in hash_lines:
            self.assertRegex(line, r"^[0-9a-f]{64}  [^/ ]+\.deb$")
        self.assertEqual(len({line.split("  ", 1)[1] for line in hash_lines}), 24)

    def test_runtime_is_non_root_offline_and_read_only_by_contract(self) -> None:
        self.assertIn("USER ${GMSH_MESH_UID}:${GMSH_MESH_GID}", self.dockerfile)
        self.assertIn("ARG GMSH_MESH_UID=9135", self.dockerfile)
        self.assertIn("ARG GMSH_MESH_GID=9135", self.dockerfile)
        self.assertIn("RUN --network=none", self.dockerfile)
        user_position = self.dockerfile.index("USER ${GMSH_MESH_UID}:${GMSH_MESH_GID}")
        smoke_position = self.dockerfile.index("RUN --network=none")
        self.assertLess(user_position, smoke_position)
        self.assertIn("PIP_NO_INDEX=1", self.dockerfile)
        self.assertIn("COPY --from=system-libs /runtime/usr/share/doc/ /usr/share/doc/", self.dockerfile)
        self.assertNotIn("ENTRYPOINT", self.dockerfile)

    def test_allow_list_excludes_project_assets(self) -> None:
        self.assertEqual(self.ignore.splitlines()[1], "**")
        allowed = {line for line in self.ignore.splitlines() if line.startswith("!")}
        self.assertEqual(
            allowed,
            {
                "!containers/",
                "!containers/gmsh-mesh-f35.requirements.txt",
                "!containers/gmsh-mesh-f35-system-packages.sha256",
                "!containers/gmsh-mesh-f35-smoke.py",
            },
        )
        self.assertNotRegex(self.ignore.lower(), r"scan|\.obj|\.stl|\.step|\.stp")

    def test_smoke_requires_occ_groups_elements_and_positive_jacobians(self) -> None:
        for token in (
            "gmsh.model.occ.addCylinder",
            "gmsh.model.addPhysicalGroup",
            'gmsh.model.mesh.generate(3)',
            "gmsh.model.mesh.getElementTypes(3)",
            "gmsh.model.mesh.getJacobians",
            'gmsh.model.mesh.getElementQualities(element_tags, "minDetJac")',
            'gmsh.model.mesh.getElementQualities(element_tags, "minSICN")',
            'gmsh.option.setNumber("General.NumThreads", 1)',
            'gmsh.option.setNumber("Mesh.RandomSeed", 1)',
            "9db3090d3b720c57b76bcbfa01d13854823ae2698c91343c20bdd4c2b81f6317",
            "value > 0.0",
            '"porsche_geometry_used": False',
            '"physics_simulation_verified": False',
            '"fabrication_authorized": False',
        ):
            self.assertIn(token, self.smoke)

    def test_workflow_is_digest_authoritative_and_anonymous_pull_gated(self) -> None:
        for token in (
            "workflow_dispatch:",
            "platforms: linux/amd64",
            "provenance: mode=max",
            "sbom: true",
            "confirm_gmsh_source_compliance:",
            'pinned_ref="${IMAGE_REPOSITORY}@${IMAGE_DIGEST}"',
            'DOCKER_CONFIG="${anonymous_config}" docker pull',
            "Promote verified digest to unique tag",
        ):
            self.assertIn(token, self.workflow)
        self.assertNotIn(":latest", self.workflow)
        action_references = [
            line.strip().split("uses: ", 1)[1]
            for line in self.workflow.splitlines()
            if "uses: " in line
        ]
        self.assertGreater(len(action_references), 0)
        for reference in action_references:
            self.assertRegex(reference, r"^[^@]+@[0-9a-f]{40}$")

    def test_recipe_contains_no_remote_runtime_or_secret_interface(self) -> None:
        combined = "\n".join((self.dockerfile, self.smoke))
        self.assertNotRegex(
            combined.lower(), r"(curl|wget|requests\.|urllib|socket\.|openbao|vast\.ai)"
        )
        self.assertNotRegex(
            combined.lower(), r"(password|api[_-]?key|access[_-]?token|private[_-]?key)"
        )


if __name__ == "__main__":
    unittest.main()
