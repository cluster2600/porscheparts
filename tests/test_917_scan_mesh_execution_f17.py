"""Tests de l'observation locale F17, sans exiger le scan brut en CI."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "twins/reference-917-engine/scan-mesh-execution-evidence-f17.json"
LOCK = ROOT / "containers/scan-mesh-f17.lock.json"
F15 = ROOT / "twins/reference-917-engine/scan-execution-evidence-f15.json"
LOCAL_REPORT = ROOT / "work/917-engine/scan-mesh-f17-published/boundary-screening.json"


class ScanMeshExecutionEvidenceF17Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.f15 = json.loads(F15.read_text(encoding="utf-8"))

    def test_exact_locked_image_and_scan_binary_are_linked(self):
        evidence = self.evidence
        self.assertEqual(evidence["phase"], "F17")
        self.assertEqual(
            evidence["execution"]["image_reference"],
            self.lock["image"]["immutable_reference"],
        )
        self.assertEqual(
            evidence["source_custody"]["sha256"],
            self.f15["source_custody"]["sha256"],
        )
        self.assertTrue(evidence["source_custody"]["expected_sha256_matches_f15"])
        self.assertFalse(evidence["source_custody"]["raw_scan_committed"])
        self.assertFalse(evidence["source_custody"]["geometry_payload_in_evidence"])

    def test_runtime_is_hardened_and_manifest_is_sanitized(self):
        execution = self.evidence["execution"]
        self.assertEqual(execution["network_mode"], "none")
        self.assertTrue(execution["root_filesystem_read_only"])
        self.assertEqual(execution["capabilities_dropped"], ["ALL"])
        self.assertTrue(execution["no_new_privileges"])
        self.assertTrue(execution["source_mount_read_only"])
        manifest = execution["execution_manifest"]
        self.assertEqual(manifest["process_exit_code"], 0)
        self.assertTrue(manifest["argv_sanitized"])
        self.assertFalse(manifest["host_paths_included"])
        self.assertFalse(manifest["runtime_container_id_recorded"])

    def test_counts_match_f15_but_filter_has_no_semantic_authority(self):
        screening = self.evidence["boundary_screening"]
        self.assertEqual(screening["boundary_edges"], self.f15["topology"]["boundary_edges"])
        self.assertEqual(
            screening["boundary_components"],
            self.f15["topology"]["boundary_component_count"],
        )
        self.assertEqual(screening["prefilter_candidate_components"], 528)
        self.assertEqual(screening["current_numeric_filter_output_count"], 2)
        self.assertEqual(len(screening["filter_outputs"]), 2)
        self.assertEqual(
            {item["component_id"] for item in screening["filter_outputs"]},
            {28, 39},
        )
        self.assertTrue(
            all(item["semantic_class"] == "unclassified" for item in screening["filter_outputs"])
        )
        self.assertEqual(screening["units"], "unconfirmed OBJ coordinate units")
        self.assertIn("cannot validate", screening["filter_scale_dependency"])

    def test_tracked_evidence_omits_candidate_coordinates_and_geometry(self):
        serialized = EVIDENCE.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", serialized)
        self.assertNotIn("raw-scans/", serialized)
        self.assertNotIn('"center"', serialized)
        self.assertNotIn('"normal"', serialized)
        self.assertNotIn('"vertices": [', serialized)
        self.assertNotIn('"faces": [', serialized)
        self.assertFalse(
            self.evidence["report"]["contains_candidate_centres_or_normals_in_tracked_evidence"]
        )

    def test_local_report_matches_digest_when_available(self):
        if not LOCAL_REPORT.is_file():
            self.skipTest("rapport local F17 absent de cet environnement")
        report = self.evidence["report"]
        self.assertEqual(LOCAL_REPORT.stat().st_size, report["bytes"])
        self.assertEqual(hashlib.sha256(LOCAL_REPORT.read_bytes()).hexdigest(), report["sha256"])

    def test_only_local_execution_observation_is_true(self):
        gates = self.evidence["release_gates"]
        self.assertTrue(all(type(value) is bool for value in gates.values()))
        self.assertEqual(
            {name for name, value in gates.items() if value},
            {"canonical_scan_boundary_screening_observed_locally_in_immutable_image"},
        )
        for required in (
            "all_boundaries_visually_reviewed",
            "scan_scale_confirmed",
            "semantic_interfaces_confirmed",
            "dimensioned_cad_reconstruction_complete",
            "classical_solver_reference_cases_executed",
            "physicsnemo_dataset_released",
            "physicsnemo_surrogate_trained",
            "engine_simulation_validated",
            "manufacturing_release",
            "print_release",
            "functional_engine_release",
            "vast_job_used",
        ):
            self.assertFalse(gates[required], required)


if __name__ == "__main__":
    unittest.main()
