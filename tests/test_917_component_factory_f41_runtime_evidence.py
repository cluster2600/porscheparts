#!/usr/bin/env python3
"""Contrat de la preuve de qualification runtime Vast F41 C59."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = (
    ROOT
    / "twins/reference-917-engine/evidence/f41-vast-runtime-c59-attempt-1"
)
SUMMARY = EVIDENCE_ROOT / "summary.json"
README = EVIDENCE_ROOT / "README.md"
DOC = ROOT / "docs/917_COMPONENT_FACTORY_F41_VAST_RUNTIME.md"
PUBLICATION = (
    ROOT
    / "twins/reference-917-engine/evidence/f41-vast-image-publication-race-fix/summary.json"
)

IMAGE = (
    "ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:"
    "c59c53b2611a1e3a9e9de5d2cedf8bfb0cd57e72582b2d6b29f6c8fc82bf7e6b"
)
SOURCE_REVISION = "045f41037f04b3dd69b72591d29713a17db8e1c3"
BUNDLE_SHA256 = "2b2d7ace49c0915b5a56da001cf3fae8ca6b97d9bb9c30fd0bda19099c7b0db5"
ARCHIVE_SHA256 = "59ef86584e9dfb16481b76ce79bf5739b129ddf2d3a3869f700b2dd614bd86b5"
FAMILIES = {
    "connecting_rod",
    "crankshaft",
    "main_bearing_pair",
    "piston",
    "piston_pin",
    "piston_ring",
}
GATE_KEYS = {
    "f41_component_factory_executed",
    "real_engine_cad_generated",
    "geometry_dimensionally_validated",
    "engine_model_physically_correlated",
    "omniverse_simready_validated",
    "target_1600_mechanical_hp_proven",
    "engine_start_authorized",
    "manufacturing_authorized",
    "metal_print_authorized",
}


class ComponentFactoryF41RuntimeEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    def test_closed_schema_and_exact_runtime_identity(self):
        self.assertEqual(
            set(self.summary),
            {
                "$comment",
                "schema_version",
                "phase",
                "status",
                "publication_evidence",
                "attempt",
                "qualification",
                "cad_batch",
                "result_archive",
                "cleanup_evidence",
                "repository_scope",
                "gates",
            },
        )
        self.assertEqual(self.summary["schema_version"], "1.0.0")
        self.assertEqual(self.summary["phase"], "F41-vast-runtime-qualification")
        self.assertEqual(
            self.summary["status"],
            "passed_remote_cad_archive_validated_instance_destroyed_not_released",
        )
        self.assertEqual(
            self.summary["publication_evidence"],
            "../f41-vast-image-publication-race-fix/summary.json",
        )
        attempt = self.summary["attempt"]
        self.assertEqual(
            set(attempt),
            {
                "date_utc",
                "source_revision",
                "image",
                "bundle_sha256",
                "bundle_size_bytes",
                "offer_id",
                "instance_id",
                "provider_region",
                "job_id",
                "parent_exit_code",
            },
        )
        self.assertEqual(attempt["date_utc"], "2026-09-03")
        self.assertEqual(attempt["source_revision"], SOURCE_REVISION)
        self.assertEqual(attempt["image"], IMAGE)
        self.assertEqual(attempt["bundle_sha256"], BUNDLE_SHA256)
        self.assertRegex(attempt["bundle_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(attempt["bundle_size_bytes"], 40368)
        self.assertEqual(attempt["offer_id"], 49691948)
        self.assertEqual(attempt["instance_id"], 49707819)
        self.assertEqual(attempt["provider_region"], "Texas, US")
        self.assertEqual(attempt["job_id"], "f41-c59-20260903t025511z")
        self.assertEqual(attempt["parent_exit_code"], 0)

    def test_publication_cross_link_matches_exact_c59_digest(self):
        publication_path = (EVIDENCE_ROOT / self.summary["publication_evidence"]).resolve()
        self.assertEqual(publication_path, PUBLICATION.resolve())
        publication = json.loads(publication_path.read_text(encoding="utf-8"))
        self.assertEqual(publication["image"]["immutable_reference"], IMAGE)
        self.assertTrue(
            publication["verified_scope"]["anonymous_exact_digest_pull_succeeded"]
        )

    def test_qualification_is_bounded_to_six_research_seed_families(self):
        qualification = self.summary["qualification"]
        self.assertEqual(
            set(qualification),
            {"vast_runtime_qualified", "f41_batch_qualified", "qualification_scope"},
        )
        self.assertTrue(qualification["vast_runtime_qualified"])
        self.assertTrue(qualification["f41_batch_qualified"])
        self.assertEqual(
            qualification["qualification_scope"],
            "six_hash_bound_F35_research_seed_families_only",
        )

        batch = self.summary["cad_batch"]
        self.assertEqual(batch["planned_family_count"], 138)
        self.assertEqual(batch["generateable_family_count"], 6)
        self.assertEqual(batch["generated_family_count"], 6)
        self.assertEqual(batch["blocked_family_count"], 132)
        self.assertEqual(set(batch["family_ids"]), FAMILIES)
        self.assertEqual(len(batch["family_ids"]), len(FAMILIES))
        self.assertEqual(
            batch["generated_format_counts"],
            {"STEP": 6, "STL": 6, "3MF": 6, "USD": 0},
        )
        self.assertEqual(batch["verified_artifact_count"], 18)
        self.assertTrue(batch["source_generation_log_verified"])
        self.assertTrue(batch["release_gates_all_false"])
        for field in (
            "geometry_semantics_validated",
            "physical_validation_complete",
            "simulation_validated",
            "manufacturing_released",
        ):
            self.assertFalse(batch[field])

    def test_archive_cleanup_and_repository_boundaries_are_exact(self):
        archive = self.summary["result_archive"]
        self.assertEqual(
            set(archive),
            {
                "sha256",
                "size_bytes",
                "transport_integrity_verified",
                "local_contract_validation_passed",
                "committed_to_repository",
            },
        )
        self.assertEqual(archive["sha256"], ARCHIVE_SHA256)
        self.assertRegex(archive["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(archive["size_bytes"], 772358)
        self.assertTrue(archive["transport_integrity_verified"])
        self.assertTrue(archive["local_contract_validation_passed"])
        self.assertFalse(archive["committed_to_repository"])

        cleanup = self.summary["cleanup_evidence"]
        self.assertEqual(
            set(cleanup),
            {
                "instance_destroyed_verified",
                "known_hosts_removed_after_destroy",
                "compute_billing_risk_cleared",
            },
        )
        self.assertTrue(all(value is True for value in cleanup.values()))
        self.assertTrue(
            all(value is False for value in self.summary["repository_scope"].values())
        )
        self.assertEqual(
            sorted(path.name for path in EVIDENCE_ROOT.iterdir()),
            ["README.md", "summary.json"],
        )

    def test_only_execution_gate_is_open(self):
        gates = self.summary["gates"]
        self.assertEqual(set(gates), GATE_KEYS)
        self.assertTrue(gates["f41_component_factory_executed"])
        self.assertTrue(
            all(
                value is False
                for key, value in gates.items()
                if key != "f41_component_factory_executed"
            )
        )

    def test_human_documents_preserve_the_claim_boundary(self):
        readme = README.read_text(encoding="utf-8")
        documentation = DOC.read_text(encoding="utf-8")
        for fragment in (
            SOURCE_REVISION,
            IMAGE,
            BUNDLE_SHA256,
            ARCHIVE_SHA256,
            "18 artefacts",
            "132 autres restent bloquées",
            "aucune preuve de\n1 600 ch",
        ):
            self.assertIn(fragment, readme)
        self.assertIn("```mermaid", documentation)
        self.assertIn("six familles", documentation)
        self.assertIn("Toutes les gates", documentation)
        self.assertIsNone(
            re.search(r"-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----", readme)
        )


if __name__ == "__main__":
    unittest.main()
