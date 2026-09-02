"""Tests de l'observation locale F15, sans exiger le scan brut en CI."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "twins/reference-917-engine/scan-execution-evidence-f15.json"
LOCK = ROOT / "containers/obj-metrology-f15.lock.json"
CONTRACT = ROOT / "twins/reference-917-engine/scan-segmentation-f15.json"
EXPECTED_GATE_KEYS = {
    "canonical_scan_execution_observed_locally_in_immutable_image",
    "independent_execution_attestation_verified",
    "scan_identity_confirmed",
    "scan_scale_confirmed",
    "metric_units_confirmed",
    "semantic_segmentation_confirmed",
    "geometry_repaired",
    "watertight_manufacturing_geometry",
    "dimensioned_cad_reconstruction_complete",
    "classical_solver_reference_cases_executed",
    "physicsnemo_dataset_released",
    "physicsnemo_surrogate_trained",
    "physical_correlation_completed",
    "engine_simulation_validated",
    "manufacturing_release",
    "print_release",
    "functional_engine_release",
    "vast_job_used",
}
LOCAL_OUTPUT = ROOT / "work/917-engine/scan-segmentation-f15"


class ScanExecutionEvidenceF15Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_execution_uses_exact_locked_image_and_canonical_binary(self):
        evidence = self.evidence
        self.assertEqual(evidence["schema_version"], "1.0.0")
        self.assertEqual(evidence["phase"], "F15")
        self.assertEqual(
            evidence["execution"]["image_reference"],
            self.lock["image"]["immutable_reference"],
        )
        self.assertEqual(
            evidence["source_custody"]["sha256"],
            self.contract["source_custody"]["expected_sha256"],
        )
        self.assertTrue(evidence["source_custody"]["expected_sha256_matches"])
        self.assertFalse(evidence["source_custody"]["source_modified"])
        self.assertFalse(evidence["source_custody"]["source_copy_created"])
        self.assertFalse(evidence["source_custody"]["raw_scan_committed"])

    def test_runtime_was_hardened_and_scope_is_local_only(self):
        execution = self.evidence["execution"]
        self.assertEqual(execution["container_platform"], "linux/amd64")
        self.assertEqual(execution["network_mode"], "none")
        self.assertTrue(execution["root_filesystem_read_only"])
        self.assertEqual(execution["capabilities_dropped"], ["ALL"])
        self.assertTrue(execution["no_new_privileges"])
        self.assertTrue(execution["source_mount_read_only"])
        self.assertTrue(execution["persistent_output_mount_only_writable_location"])
        self.assertTrue(execution["ephemeral_tmpfs_writable"])
        self.assertTrue(execution["temporary_files_removed"])
        self.assertGreater(execution["elapsed_seconds"], 0)
        manifest = execution["execution_manifest"]
        self.assertEqual(manifest["kind"], "sanitized_local_operator_observation")
        self.assertEqual(manifest["runtime_image_reference"], execution["image_reference"])
        self.assertEqual(manifest["process_exit_code"], 0)
        self.assertEqual(
            manifest["argv"],
            [
                "python3",
                "/opt/3dprinting993/twins/reference-917-engine/source/build_scan_segmentation_f15.py",
                "--contract",
                "/opt/3dprinting993/twins/reference-917-engine/scan-segmentation-f15.json",
                "--source",
                "/workspace/input/917-engine-case-with-cylinders.obj",
                "--output",
                "/workspace/output",
            ],
        )
        self.assertTrue(manifest["argv_sanitized"])
        self.assertFalse(manifest["host_paths_included"])
        self.assertFalse(manifest["runtime_container_id_recorded"])
        self.assertEqual(
            manifest["policy"],
            {
                "platform": "linux/amd64",
                "network": "none",
                "root_filesystem": "read_only",
                "tmpfs": "/tmp:rw,noexec,nosuid,size=16m",
                "capabilities_dropped": ["ALL"],
                "no_new_privileges": True,
                "source_mount": "read_only",
                "persistent_output_mount": "only_persistent_writable_location",
            },
        )
        authority = self.evidence["evidence_authority"]
        self.assertEqual(authority["kind"], "local_operator_observation")
        self.assertFalse(authority["independent_reproduction_verified"])
        self.assertFalse(authority["cryptographic_operator_signature_present"])
        self.assertFalse(authority["release_authority"])

    def test_inventory_reconciles_exactly_with_contract(self):
        report = self.evidence["report"]
        self.assertEqual(report["status"], "passed_inventory_only")
        self.assertEqual(report["execution_scope"], "canonical_scan")
        for key in (
            "contract_integrity_error_count",
            "source_custody_error_count",
            "canonical_reconciliation_error_count",
            "parse_error_count",
            "parse_warning_count",
        ):
            self.assertEqual(report[key], 0, key)
        expected = self.contract["canonical_reconciliation"]
        inventory = self.evidence["format_inventory"]
        topology = self.evidence["topology"]
        self.assertEqual(inventory["vertices"], expected["vertices"])
        self.assertEqual(inventory["polygon_faces"], expected["polygon_faces"])
        self.assertEqual(inventory["triangle_faces"], expected["triangles"])
        self.assertEqual(inventory["zero_area_faces"], expected["zero_area_faces"])
        self.assertEqual(topology["surface_component_count"], expected["surface_components"])
        self.assertEqual(topology["boundary_edges"], expected["boundary_edges"])
        self.assertEqual(topology["non_manifold_edges"], expected["non_manifold_edges"])
        self.assertEqual(
            self.evidence["raw_coordinate_metrology"]["bounds_min_obj_units"],
            expected["bounds_min_obj_units"],
        )
        self.assertEqual(
            self.evidence["raw_coordinate_metrology"]["bounds_max_obj_units"],
            expected["bounds_max_obj_units"],
        )
        self.assertEqual(sum(item["vertex_count"] for item in topology["surface_components"]), inventory["vertices"])
        self.assertEqual(sum(item["face_count"] for item in topology["surface_components"]), inventory["polygon_faces"])
        self.assertFalse(topology["watertight"])
        self.assertFalse(topology["boundary_loop_semantics_confirmed"])

    def test_obj_has_no_usable_semantic_declarations(self):
        inventory = self.evidence["format_inventory"]
        for key in (
            "named_object_declarations",
            "named_group_declarations",
            "named_material_declarations",
            "material_library_declarations",
        ):
            self.assertEqual(inventory[key], 0)
        self.assertFalse(inventory["usable_semantic_declarations"])

    def test_output_manifest_contains_only_lightweight_digests(self):
        outputs = self.evidence["local_outputs"]
        self.assertEqual(
            {item["name"] for item in outputs},
            {
                "scan-segmentation-f15-report.json",
                "surface-components-f15.csv",
                "boundary-components-f15.csv",
                "obj-declarations-f15.json",
            },
        )
        for item in outputs:
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(item["bytes"], 0)
            self.assertFalse(item["contains_geometry_payload"])
        self.assertEqual(
            self.evidence["report"]["sha256"],
            next(item["sha256"] for item in outputs if item["name"].startswith("scan-")),
        )
        serialized = EVIDENCE.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", serialized)
        self.assertNotIn("raw-scans/", serialized)
        self.assertNotIn('"faces": [', serialized)
        self.assertNotIn('"vertices": [', serialized)

    def test_local_outputs_match_the_tracked_digests_when_available(self):
        if not LOCAL_OUTPUT.is_dir():
            self.skipTest("sorties locales F15 absentes de cet environnement")
        for item in self.evidence["local_outputs"]:
            path = LOCAL_OUTPUT / item["name"]
            self.assertTrue(path.is_file(), item["name"])
            self.assertEqual(path.stat().st_size, item["bytes"], item["name"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                item["sha256"],
                item["name"],
            )

    def test_only_execution_gate_is_true(self):
        gates = self.evidence["release_gates"]
        self.assertEqual(set(gates), EXPECTED_GATE_KEYS)
        self.assertTrue(all(type(value) is bool for value in gates.values()))
        self.assertEqual(
            {name for name, value in gates.items() if value is True},
            {"canonical_scan_execution_observed_locally_in_immutable_image"},
        )
        for required in (
            "scan_identity_confirmed",
            "scan_scale_confirmed",
            "semantic_segmentation_confirmed",
            "geometry_repaired",
            "watertight_manufacturing_geometry",
            "dimensioned_cad_reconstruction_complete",
            "classical_solver_reference_cases_executed",
            "physicsnemo_dataset_released",
            "physicsnemo_surrogate_trained",
            "physical_correlation_completed",
            "engine_simulation_validated",
            "manufacturing_release",
            "print_release",
            "functional_engine_release",
            "vast_job_used",
        ):
            self.assertIs(gates[required], False, required)
        manifest = self.evidence["execution"]["execution_manifest"]
        self.assertEqual(manifest["process_exit_code"], 0)
        self.assertEqual(self.evidence["report"]["status"], "passed_inventory_only")
        self.assertTrue(self.evidence["source_custody"]["expected_sha256_matches"])


if __name__ == "__main__":
    unittest.main()
