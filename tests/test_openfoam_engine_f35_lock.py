#!/usr/bin/env python3
"""Validation fail-closed du contrat de publication OpenFOAM F35."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "containers/openfoam-engine-f35.lock.json"


class OpenFoamEngineF35LockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = LOCK_PATH.read_text(encoding="utf-8")
        cls.lock = json.loads(cls.raw)

    def test_identity_recipe_and_inputs_are_exact(self) -> None:
        self.assertEqual(self.lock["schema_version"], "1.0.0")
        self.assertEqual(self.lock["phase"], "F35")
        self.assertEqual(self.lock["lot"], "openfoam-engine-f35")
        recipe = self.lock["recipe"]
        self.assertEqual(recipe["platform"], "linux/amd64")
        self.assertEqual(recipe["openfoam_package_version"], "20260724")
        self.assertEqual(recipe["openmpi_version"], "4.1.6-7ubuntu2")
        self.assertEqual(recipe["python3_version"], "3.12.3-0ubuntu2.1")
        self.assertEqual(
            recipe["aate_commit"],
            "c0f75f953d67cd325d28d1300672d14288f22934",
        )
        self.assertRegex(recipe["aate_archive_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual((recipe["runtime_uid"], recipe["runtime_gid"]), (9135, 9135))
        self.assertEqual(len(recipe["planned_inputs"]), 12)
        self.assertEqual(len(recipe["planned_inputs"]), len(set(recipe["planned_inputs"])))
        for relative_path in recipe["planned_inputs"]:
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)

    def test_unpublished_contract_and_all_physical_gates_are_closed(self) -> None:
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
        self.assertTrue(claims["synthetic_serial_and_mpi_solver_smoke_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in claims.items()
                if key != "synthetic_serial_and_mpi_solver_smoke_only"
            )
        )
        self.assertNotRegex(self.raw, r"/Users/|/home/[^\s\"]+")
        self.assertNotRegex(
            self.raw.lower(),
            r"(password|api[_-]?key|access[_-]?token|private[_-]?key)",
        )


if __name__ == "__main__":
    unittest.main()
