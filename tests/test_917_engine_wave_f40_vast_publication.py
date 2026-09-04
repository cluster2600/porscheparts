"""Garde de la preuve de publication OCI F40 Vast."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / "twins/reference-917-engine/evidence/f40-vast/publication.json"
)

EXPECTED_INDEX = (
    "sha256:7767037d971da04b6130bcf9da6014953c118333b6cd8b406220f469b55546fa"
)
EXPECTED_REF = (
    "ghcr.io/cluster2600/3dprinting993-wave-action-f39@" + EXPECTED_INDEX
)


class EngineWaveF40VastPublicationTests(unittest.TestCase):
    def setUp(self):
        self.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_exact_public_image_and_successful_workflow_are_recorded(self):
        self.assertEqual(self.evidence["phase"], "F40-vast-publication")
        self.assertEqual(self.evidence["workflow"]["id"], 33682226117)
        self.assertEqual(self.evidence["workflow"]["status"], "completed")
        self.assertEqual(self.evidence["workflow"]["conclusion"], "success")
        self.assertEqual(self.evidence["image"]["oci_index_digest"], EXPECTED_INDEX)
        self.assertEqual(self.evidence["image"]["immutable_reference"], EXPECTED_REF)
        self.assertEqual(self.evidence["image"]["platform"], "linux/amd64")
        self.assertEqual(self.evidence["image"]["runtime_user"], "0:0")

    def test_publication_gates_are_closed_without_opening_engine_claims(self):
        verification = self.evidence["verification"]
        for gate in (
            "workflow_build_passed",
            "sbom_gate_passed",
            "provenance_gate_passed",
            "workflow_anonymous_pull_passed",
            "independent_anonymous_pull_passed",
            "independent_offline_transport_smoke_passed",
            "solver_no_new_privileges",
        ):
            self.assertIs(verification[gate], True, gate)
        self.assertEqual(verification["solver_uid"], 9139)
        self.assertEqual(verification["aeolus1d_version"], "0.3.3")
        self.assertFalse(verification["embedded_authorized_keys"])
        self.assertFalse(verification["embedded_ssh_host_private_keys"])
        for gate, value in self.evidence["claim_scope"].items():
            self.assertIs(value, False, gate)


if __name__ == "__main__":
    unittest.main()
