"""Tests du verrou de publication de l'image CPU F26."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "containers/topology-context-f26.lock.json"
DOC = ROOT / "docs/917_TOPOLOGY_CONTEXT_F26.md"


class TopologyContextF26LockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))

    def test_exact_public_image_platform_and_attestation_are_pinned(self):
        lock = self.lock
        image = lock["image"]
        verification = lock["verification"]
        self.assertEqual(lock["phase"], "F26")
        self.assertEqual(
            image["digest"],
            "sha256:41764d6d6ed935a763a6b1e07524c68961555b2724e67bbf48a2f261c35a3b10",
        )
        self.assertEqual(
            image["immutable_reference"],
            f"{image['repository']}@{image['digest']}",
        )
        self.assertEqual(image["index"]["size_bytes"], 857)
        self.assertEqual(image["index"]["platform_manifest_count"], 1)
        self.assertEqual(image["index"]["attestation_manifest_count"], 1)
        self.assertEqual(image["platform"]["os"], "linux")
        self.assertEqual(image["platform"]["architecture"], "amd64")
        self.assertEqual(image["platform"]["user"], "9174:9174")
        self.assertEqual(image["platform"]["numpy_version"], "2.2.6")
        self.assertFalse(image["platform"]["gpu_required"])
        self.assertEqual(
            image["manifest"]["digest"],
            "sha256:71a0cff8402602473657b96fdbdd49240569afc01ff341a654f233eb974ef5b6",
        )
        self.assertEqual(
            image["attestation_manifest"]["digest"],
            "sha256:0c5ce6d8759a2d56137c9436d9060e47d32ede3c27724fa428b68cb2b25b022d",
        )
        self.assertEqual(
            image["attestation_manifest"]["subject_manifest_digest"],
            image["manifest"]["digest"],
        )
        predicates = {
            item["predicate_type"]: item
            for item in image["attestation_manifest"]["predicate_layers"]
        }
        self.assertEqual(
            set(predicates),
            {"https://spdx.dev/Document", "https://slsa.dev/provenance/v1"},
        )
        self.assertEqual(
            predicates["https://slsa.dev/provenance/v1"]["digest"],
            verification["provenance"]["layer_digest"],
        )
        self.assertEqual(
            predicates["https://spdx.dev/Document"]["digest"],
            verification["sbom"]["layer_digest"],
        )

    def test_manifest_counts_sizes_and_evidence_metadata_are_exact(self):
        manifest = self.lock["image"]["manifest"]
        layers = manifest["layers"]
        self.assertEqual(manifest["layer_count"], len(layers))
        self.assertEqual(
            manifest["compressed_size_bytes"],
            sum(item["size_bytes"] for item in layers),
        )
        largest = max(layers, key=lambda item: item["size_bytes"])
        self.assertEqual(manifest["largest_layer_digest"], largest["digest"])
        self.assertEqual(manifest["largest_layer_bytes"], largest["size_bytes"])

        expected = {
            "topology-context-f26-index.json": (
                "41764d6d6ed935a763a6b1e07524c68961555b2724e67bbf48a2f261c35a3b10",
                857,
            ),
            "topology-context-f26-platform-manifest.json": (
                "71a0cff8402602473657b96fdbdd49240569afc01ff341a654f233eb974ef5b6",
                2945,
            ),
            "topology-context-f26-attestation-manifest.json": (
                "0c5ce6d8759a2d56137c9436d9060e47d32ede3c27724fa428b68cb2b25b022d",
                1112,
            ),
            "topology-context-f26-provenance.json": (
                "6ff3a9b83490db61a52270595d88460f01d98a4f7bea04e0784741f6186d353d",
                45352,
            ),
            "topology-context-f26-sbom.json": (
                "e6d7cefa49a904167b79f2c5c59cd9df3ccc7441cd2ad8cec3b5a3ea517012bf",
                3278930,
            ),
            "topology-context-f26-smoke.json": (
                "a5d04c4e4f9cbbe6181bd35161dcde34ca92655529d3bb81ee3c16ac51e2fabc",
                2277,
            ),
            "topology-context-f26-bind-smoke.json": (
                "6123d6894d37b6a47a03695808451b90753d42a846c4cb3f6c071650235ff673",
                897,
            ),
            "topology-context-f26-anonymous-smoke.json": (
                "a5d04c4e4f9cbbe6181bd35161dcde34ca92655529d3bb81ee3c16ac51e2fabc",
                2277,
            ),
            "topology-context-f26-image-ref.txt": (
                "306f3850b53103dfc939258086f83ee0902faa9aae37596f5b6931b188d2ba36",
                127,
            ),
        }
        actual = {
            item["name"]: (item["sha256"], item["size_bytes"])
            for item in self.lock["verification"]["evidence_files"]
        }
        self.assertEqual(actual, expected)
        self.assertEqual(
            actual["topology-context-f26-index.json"][0],
            self.lock["image"]["digest"].removeprefix("sha256:"),
        )
        self.assertEqual(
            actual["topology-context-f26-smoke.json"],
            actual["topology-context-f26-anonymous-smoke.json"],
        )
        artifact = self.lock["verification"]["evidence_artifact"]
        self.assertEqual(artifact["id"], 9829792683)
        self.assertEqual(
            artifact["digest"],
            "sha256:4e2b11175b63bf96097728ebcd082629f32347b8a6e4cb7bc8fe681b38f649d1",
        )
        self.assertEqual(artifact["size_bytes"], 308056)
        self.assertFalse(artifact["expired"])

    def test_workflow_provenance_sbom_and_public_pull_are_bound(self):
        verification = self.lock["verification"]
        workflow = verification["workflow"]
        self.assertEqual(workflow["run_id"], 33585072387)
        self.assertEqual(workflow["job_id"], 100107425482)
        self.assertEqual(workflow["conclusion"], "success")
        self.assertEqual(
            workflow["head_sha"],
            self.lock["recipe"]["workflow_head_sha"],
        )
        self.assertEqual(
            verification["provenance"]["source_revision"],
            workflow["head_sha"],
        )
        self.assertTrue(verification["provenance"]["frontend_digest_present"])
        self.assertTrue(verification["provenance"]["base_image_digest_present"])
        self.assertEqual(verification["sbom"]["spdx_version"], "SPDX-2.3")
        self.assertEqual(verification["sbom"]["data_license"], "CC0-1.0")
        self.assertEqual(verification["sbom"]["numpy_version"], "2.2.6")
        self.assertEqual(verification["sbom"]["package_count"], 115)
        self.assertEqual(verification["sbom"]["file_count"], 3237)
        self.assertEqual(verification["sbom"]["relationship_count"], 3810)
        self.assertTrue(verification["published_digest_pulled"])
        self.assertTrue(verification["anonymous_exact_digest_access"])
        self.assertEqual(
            verification["anonymous_access_workflow_step_conclusion"],
            "success",
        )
        self.assertTrue(
            verification["anonymous_smoke"]["exact_digest_pulled_without_credentials"]
        )
        self.assertFalse(verification["cryptographic_signature_verified"])

    def test_recipe_rereads_every_exact_build_and_gate_input(self):
        inputs = self.lock["recipe"]["inputs"]
        self.assertEqual(len(inputs), 9)
        self.assertEqual(len({item["path"] for item in inputs}), len(inputs))
        for item in inputs:
            path = ROOT / item["path"]
            self.assertTrue(path.is_file(), item["path"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                item["sha256"],
                item["path"],
            )

    def test_only_cpu_image_gates_open_and_all_physical_gates_stay_closed(self):
        verification = self.lock["verification"]
        smoke = verification["offline_smoke"]
        bind_smoke = verification["bind_mount_smoke"]
        self.assertEqual(smoke["status"], "passed_synthetic_fixture_only")
        self.assertEqual(smoke["kernel_interfaces"], ["lo"])
        self.assertEqual(smoke["topological_ring_count"], 2)
        self.assertEqual(smoke["orthographic_views_per_component"], 4)
        self.assertEqual(smoke["global_locators_per_component"], 4)
        self.assertEqual(smoke["confirmed_interface_count"], 0)
        self.assertTrue(smoke["payload_hashes_verified"])
        self.assertTrue(smoke["deterministic_tree_byte_identical"])
        self.assertEqual(
            bind_smoke["status"],
            "passed_synthetic_bind_mount_fixture_only",
        )
        self.assertEqual(bind_smoke["runtime_uid_gid"], "9174:9174")
        self.assertTrue(bind_smoke["input_mount_read_only"])
        self.assertTrue(bind_smoke["output_mount_read_write"])
        self.assertTrue(bind_smoke["output_owned_by_runtime_uid"])
        self.assertFalse(bind_smoke["canonical_scan_used"])
        self.assertEqual(bind_smoke["confirmed_interface_count"], 0)
        self.assertEqual(
            {name for name, value in self.lock["release_gates"].items() if value},
            {"immutable_public_image_verified", "linux_amd64_offline_smoke_verified"},
        )
        for gate in (
            "engine_identity_confirmed",
            "scan_identity_confirmed",
            "scan_scale_confirmed",
            "metric_units_confirmed",
            "semantic_interfaces_confirmed",
            "dimensioned_cad_reconstruction_complete",
            "cae_geometry_released",
            "classical_solver_reference_cases_executed",
            "physicsnemo_dataset_released",
            "physicsnemo_surrogate_trained",
            "omniverse_simready_released",
            "manufacturing_release",
            "print_release",
            "functional_engine_release",
        ):
            self.assertFalse(self.lock["release_gates"][gate], gate)

    def test_lock_contains_no_scan_or_derived_topology_payload(self):
        for field in (
            "raw_scans",
            "derived_scan_geometry",
            "f18_reports",
            "ply_files",
            "real_topology_context_outputs",
            "svg_files",
            "datasets",
            "model_weights",
            "secrets",
            "synthetic_fixtures_persisted_in_image",
        ):
            self.assertFalse(self.lock["bundled_assets"][field], field)
        serialized = LOCK.read_text(encoding="utf-8")
        for forbidden in (
            "917-engine-case-with-cylinders.obj",
            "428c4143d073f8330022f2fecbd1ac1ee7784d4f1565f1160020448dbdffa0ae",
            "boundary-review-f18.json",
            "boundary-components-f18.ply",
            "raw-scans/",
            "work/917-engine/",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_documentation_names_exact_digest_run_and_fail_closed_scope(self):
        document = DOC.read_text(encoding="utf-8")
        for fragment in (
            "Publication immuable vérifiée",
            "topology-context-f26.lock.json",
            "33585072387",
            "sha256:41764d6d6ed935a763a6b1e07524c68961555b2724e67bbf48a2f261c35a3b10",
            "9174:9174",
            "linux/amd64",
            "SBOM SPDX",
            "provenance SLSA",
            "accès anonyme",
            "ne prouve pas",
            "PhysicsNeMo",
            "Omniverse",
        ):
            self.assertIn(fragment.lower(), document.lower())


if __name__ == "__main__":
    unittest.main()
