"""Preuve agrégée d'exécution canonique F26, sans géométrie suivie."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / "twins/reference-917-engine/topology-context-execution-evidence-f26.json"
)
LOCK = ROOT / "containers/topology-context-f26.lock.json"
CONTRACT = ROOT / "twins/reference-917-engine/topology-context-contract-f26.json"
DOC = ROOT / "docs/917_TOPOLOGY_CONTEXT_F26.md"


class TopologyContextExecutionF26Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))

    def test_exact_locked_image_and_exact_inputs_are_bound(self):
        evidence = self.evidence
        self.assertEqual(evidence["phase"], "F26")
        execution = evidence["execution"]
        self.assertEqual(
            execution["image_reference"],
            self.lock["image"]["immutable_reference"],
        )
        self.assertEqual(
            execution["image_lock_commit"],
            "01e7237efed88e48ce1d86c0581b6944ee6fd897",
        )
        self.assertEqual(
            hashlib.sha256(LOCK.read_bytes()).hexdigest(),
            execution["image_lock_sha256"],
        )
        custody = evidence["input_custody"]
        self.assertEqual(custody["mesh"]["bytes"], 107128223)
        self.assertEqual(
            custody["mesh"]["sha256"],
            "428c4143d073f8330022f2fecbd1ac1ee7784d4f1565f1160020448dbdffa0ae",
        )
        self.assertEqual(
            custody["f18_report"]["sha256"],
            "8208c2fec6561261904c48bb449a1bd50d679e370ee7b4a19a86d78ba265450e",
        )
        self.assertEqual(
            custody["f26_contract"]["sha256"],
            "863a50e1ec577ed79740877292fbbf7e2ae0af73d4996afe8d067fb261445575",
        )
        self.assertEqual(
            hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
            custody["f26_contract"]["sha256"],
        )
        for item in custody.values():
            self.assertTrue(item["expected_sha256_matched"])

    def test_runtime_is_hardened_and_sanitized(self):
        execution = self.evidence["execution"]
        self.assertEqual(execution["container_platform"], "linux/amd64")
        self.assertEqual(execution["runtime_uid_gid"], "9174:9174")
        self.assertEqual(execution["process_exit_code"], 0)
        self.assertEqual(execution["network_mode"], "none")
        self.assertTrue(execution["root_filesystem_read_only"])
        self.assertEqual(execution["capabilities_dropped"], ["ALL"])
        self.assertTrue(execution["no_new_privileges"])
        self.assertTrue(execution["input_mounts_read_only"])
        output = execution["output_backend"]
        self.assertEqual(output["kind"], "docker_volume")
        self.assertTrue(output["copy_on_create_disabled"])
        self.assertEqual(output["private_parent_mode"], "0700")
        self.assertTrue(output["owned_by_runtime_uid_gid"])
        self.assertFalse(output["identifier_recorded"])
        manifest = execution["execution_manifest"]
        self.assertFalse(manifest["arguments_recorded"])
        self.assertFalse(manifest["host_paths_included"])
        self.assertFalse(manifest["container_paths_included"])
        self.assertFalse(manifest["local_volume_identifier_recorded"])

    def test_aggregate_counts_hashes_and_determinism_are_exact(self):
        result = self.evidence["aggregate_result"]
        self.assertEqual(result["boundary_component_count"], 944)
        self.assertEqual(result["batch_count"], 20)
        self.assertEqual(result["manifest_covered_payload_count"], 1889)
        self.assertEqual(result["total_regular_file_count"], 1890)
        self.assertEqual(result["file_type_counts"], {"json": 945, "svg": 944, "csv": 1})
        self.assertEqual(sum(result["file_type_counts"].values()), 1890)
        self.assertEqual(result["total_bytes"], 213063080)
        self.assertEqual(
            result["completion_manifest"],
            {
                "sha256": "acfdf9384440986cb00d08ac9f51f3111cc83d38838e22b75173f5411843af39",
                "bytes": 545596,
                "payload_committed": False,
            },
        )
        self.assertEqual(
            result["tabular_index"]["sha256"],
            "4f308350ee20f85d46b041777a2822e537ce73701a45ce98695b74a4c387bb45",
        )
        self.assertEqual(result["tabular_index"]["bytes"], 256573)
        self.assertEqual(result["tabular_index"]["line_count"], 945)
        self.assertEqual(result["tabular_index"]["observation_count"], 944)
        self.assertEqual(
            result["strict_tree_sha256"],
            "927b10d5266f4727061d5399b5291e5316e7fcb6ed1afa6d69e01c84f3bdde3c",
        )
        self.assertEqual(result["artifact_hashes_reread"], 1889)
        self.assertTrue(result["all_manifest_payload_hashes_verified"])
        self.assertTrue(result["manifest_published_last_as_completion_marker"])
        self.assertEqual(result["confirmed_interface_count"], 0)
        self.assertEqual(result["human_review_completed_count"], 0)
        self.assertFalse(result["output_payloads_committed"])
        replay = self.evidence["deterministic_replay"]
        self.assertTrue(replay["strict_tree_byte_identical_to_first_computation"])
        self.assertFalse(replay["first_computation_release_accepted"])
        self.assertEqual(
            replay["first_computation_rejection"],
            "guarded cleanup refused a replaced directory",
        )
        self.assertEqual(replay["final_execution_exit_code"], 0)

    def test_two_failed_mount_paths_remain_rejected_before_safe_nocopy_path(self):
        incidents = self.evidence["runtime_incidents"]
        self.assertEqual([item["sequence"] for item in incidents], [1, 2, 3])
        macos, copied, safe = incidents
        self.assertEqual(macos["status"], "rejected_fail_closed")
        self.assertEqual(
            macos["observation"],
            "guarded cleanup refused a replaced directory",
        )
        self.assertFalse(macos["guard_weakened"])
        self.assertFalse(macos["output_accepted"])
        self.assertEqual(copied["status"], "rejected_fail_closed")
        self.assertEqual(
            copied["observation"],
            "copy_on_create_restored_output_parent_mode_0755",
        )
        self.assertEqual(copied["required_private_mode"], "0700")
        self.assertFalse(copied["output_accepted"])
        self.assertEqual(safe["environment"], "docker_volume_with_volume_nocopy")
        self.assertEqual(safe["status"], "passed")
        self.assertEqual(safe["private_parent_mode"], "0700")
        self.assertEqual(safe["runtime_uid_gid"], "9174:9174")
        self.assertTrue(safe["output_accepted"])

    def test_only_canonical_software_execution_gates_open(self):
        gates = self.evidence["release_gates"]
        self.assertTrue(all(type(value) is bool for value in gates.values()))
        self.assertEqual(
            {name for name, value in gates.items() if value},
            {
                "canonical_scan_execution_verified_in_published_image",
                "canonical_topology_context_generated",
            },
        )
        for gate in (
            "independent_execution_attestation_verified",
            "human_boundary_review_completed",
            "engine_identity_confirmed",
            "scan_scale_confirmed",
            "metric_units_confirmed",
            "semantic_interfaces_confirmed",
            "dimensioned_cad_reconstruction_complete",
            "cae_geometry_released",
            "classical_solver_reference_cases_executed",
            "physicsnemo_dataset_released",
            "physicsnemo_surrogate_trained",
            "physical_correlation_completed",
            "omniverse_simready_released",
            "engine_simulation_validated",
            "manufacturing_release",
            "print_release",
            "functional_engine_release",
        ):
            self.assertFalse(gates[gate], gate)
        self.assertFalse(
            self.lock["release_gates"][
                "canonical_scan_execution_verified_in_published_image"
            ]
        )
        self.assertFalse(
            self.lock["release_gates"]["canonical_topology_context_generated"]
        )

    def test_tracked_evidence_contains_no_geometry_or_local_artifact(self):
        self.assertTrue(
            all(value is False for value in self.evidence["tracked_summary_content"].values())
        )
        serialized = EVIDENCE.read_text(encoding="utf-8")
        for forbidden in (
            "/Users/",
            "/Volumes/",
            "/private/",
            "/workspace/",
            "raw-scans/",
            "work/917-engine/",
            "boundary_0001",
            "<svg",
            '"coordinates"',
            '"vertices"',
            '"faces"',
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertIsNone(
            re.search(r'"(?:host|container|local)_path"\s*:', serialized)
        )
        self.assertFalse(self.evidence["input_custody"]["mesh"]["payload_committed"])
        self.assertFalse(
            self.evidence["input_custody"]["f18_report"]["payload_committed"]
        )

    def test_documentation_records_safe_runbook_and_scope(self):
        document = DOC.read_text(encoding="utf-8")
        for fragment in (
            "Preuve d’exécution canonique agrégée",
            "topology-context-execution-evidence-f26.json",
            "944 composantes",
            "20 lots",
            "1 889",
            "1 890",
            "213 063 080",
            "volume-nocopy",
            "guarded cleanup refused a replaced directory",
            "0755",
            "0700",
            "canonical_scan_execution_verified_in_published_image",
            "canonical_topology_context_generated",
            "PhysicsNeMo",
            "Omniverse",
            "hors Git",
            "```mermaid",
        ):
            self.assertIn(fragment.lower(), document.lower())


if __name__ == "__main__":
    unittest.main()
