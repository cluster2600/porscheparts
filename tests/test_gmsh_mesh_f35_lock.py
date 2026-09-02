#!/usr/bin/env python3
"""Validation fail-closed du contrat de publication Gmsh F35."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "containers" / "gmsh-mesh-f35.lock.json"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "gmsh-mesh-f35-image.yml"


class GmshMeshF35LockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = LOCK_PATH.read_text(encoding="utf-8")
        cls.lock = json.loads(cls.raw)
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_identity_and_recipe_are_exact(self) -> None:
        self.assertEqual(self.lock["schema_version"], "1.0.0")
        self.assertEqual(self.lock["phase"], "F35")
        self.assertEqual(self.lock["lot"], "gmsh-mesh-f35")
        recipe = self.lock["recipe"]
        self.assertEqual(recipe["platform"], "linux/amd64")
        self.assertEqual(recipe["gmsh_version"], "4.15.2")
        self.assertRegex(recipe["gmsh_wheel_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            recipe["libgmsh_sha256"],
            "9db3090d3b720c57b76bcbfa01d13854823ae2698c91343c20bdd4c2b81f6317",
        )
        self.assertEqual(recipe["system_package_hash_count"], 24)
        self.assertEqual((recipe["runtime_uid"], recipe["runtime_gid"]), (9135, 9135))
        self.assertEqual(len(recipe["planned_inputs"]), 9)
        self.assertEqual(len(recipe["planned_inputs"]), len(set(recipe["planned_inputs"])))
        self.assertIn("containers/gmsh-mesh-f35.lock.json", recipe["planned_inputs"])
        self.assertIn("tests/test_gmsh_mesh_f35_lock.py", recipe["planned_inputs"])
        for relative_path in recipe["planned_inputs"]:
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)

        checksum_block = re.search(
            r"sha256sum \\\n(?P<inputs>.*?)            > gmsh-mesh-f35-source-inputs\.sha256",
            self.workflow,
            re.DOTALL,
        )
        self.assertIsNotNone(checksum_block)
        workflow_inputs = [
            line.strip().removesuffix("\\").strip()
            for line in checksum_block.group("inputs").splitlines()
            if line.strip()
        ]
        self.assertEqual(workflow_inputs, recipe["planned_inputs"])

    def test_unpublished_contract_is_fail_closed(self) -> None:
        self.assertEqual(self.lock["status"], "publication_not_verified_fail_closed")
        image = self.lock["planned_image"]
        self.assertFalse(image["tags_are_release_authority"])
        for key in ("candidate_tag", "verified_tag", "digest", "immutable_reference"):
            self.assertIsNone(image[key], key)
        verification = self.lock["verification"]
        self.assertFalse(verification["publication_verified"])
        for key, value in verification.items():
            if key.endswith("_verified"):
                self.assertIs(value, False, key)
        for gate_set in ("software_verification_gates", "physical_release_gates"):
            self.assertGreater(len(self.lock[gate_set]), 0)
            self.assertTrue(all(value is False for value in self.lock[gate_set].values()))

    def test_claim_boundary_and_sensitive_content(self) -> None:
        claims = self.lock["claim_scope"]
        self.assertTrue(claims["synthetic_occ_volume_mesh_only"])
        self.assertTrue(all(value is False for key, value in claims.items() if key != "synthetic_occ_volume_mesh_only"))
        self.assertNotRegex(self.raw, r"/Users/|/home/[^\s\"]+")
        self.assertNotRegex(self.raw.lower(), r"(password|api[_-]?key|access[_-]?token|private[_-]?key)")
        self.assertNotRegex(self.raw, r"sha256:0{64}")


if __name__ == "__main__":
    unittest.main()
