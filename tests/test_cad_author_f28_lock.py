"""Tests du verrou de publication de l'image d'auteur CAO F28."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "containers/cad-author-f28.lock.json"
DOC = ROOT / "docs/917_CAD_AUTHOR_IMAGE_F28.md"


class CadAuthorF28LockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))

    def test_exact_public_image_platform_and_attestation_are_pinned(self):
        lock = self.lock
        image = lock["image"]
        verification = lock["verification"]
        self.assertEqual(lock["phase"], "F28")
        self.assertEqual(
            image["digest"],
            "sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57",
        )
        self.assertEqual(
            image["immutable_reference"],
            f"{image['repository']}@{image['digest']}",
        )
        self.assertEqual(image["index"]["size_bytes"], 857)
        self.assertEqual(image["index"]["platform_manifest_count"], 1)
        self.assertEqual(image["index"]["attestation_manifest_count"], 1)
        self.assertTrue(image["index"]["digest_recomputed"])
        self.assertEqual(image["platform"]["os"], "linux")
        self.assertEqual(image["platform"]["architecture"], "amd64")
        self.assertEqual(image["platform"]["user"], "9178:9178")
        self.assertEqual(image["platform"]["build123d_version"], "0.11.1")
        self.assertEqual(image["platform"]["ocp_version"], "7.9.3.1")
        self.assertFalse(image["platform"]["gpu_required"])
        self.assertEqual(
            image["manifest"]["digest"],
            "sha256:dbbebc784706f17a1d4f1d3c04df90baa551e0a72236bd29995f983735a6661b",
        )
        attestation = image["attestation_manifest"]
        self.assertEqual(
            attestation["digest"],
            "sha256:56cbcf8288cf306b362f45f806f1b6982dbcb4149ad78322d818cfbdd38dd7fa",
        )
        self.assertEqual(attestation["subject_manifest_digest"], image["manifest"]["digest"])
        self.assertEqual(
            attestation["subject_manifest_size_bytes"],
            image["manifest"]["size_bytes"],
        )
        predicates = {
            item["predicate_type"]: item
            for item in attestation["predicate_layers"]
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

    def test_manifest_and_real_size_metrics_are_self_consistent(self):
        manifest = self.lock["image"]["manifest"]
        layers = manifest["layers"]
        metrics = self.lock["verification"]["size_metrics"]
        registry = metrics["registry_compressed"]
        local = metrics["local_and_uncompressed"]
        self.assertEqual(manifest["layer_count"], len(layers))
        self.assertEqual(manifest["layer_count"], 18)
        self.assertEqual(
            manifest["compressed_size_bytes"],
            sum(item["size_bytes"] for item in layers),
        )
        largest = max(layers, key=lambda item: item["size_bytes"])
        self.assertEqual(manifest["largest_layer_digest"], largest["digest"])
        self.assertEqual(manifest["largest_layer_bytes"], largest["size_bytes"])
        self.assertEqual(
            registry["compressed_layers_total_bytes"],
            manifest["compressed_size_bytes"],
        )
        self.assertEqual(
            registry["compressed_layer_max_bytes"],
            manifest["largest_layer_bytes"],
        )
        self.assertLessEqual(
            registry["compressed_layers_total_bytes"],
            registry["budgets"]["compressed_layers_total_bytes"],
        )
        self.assertLessEqual(
            registry["compressed_layer_max_bytes"],
            registry["budgets"]["compressed_layer_max_bytes"],
        )
        self.assertEqual(local["uncompressed_layer_tar_bytes"], 865096192)
        self.assertLessEqual(
            local["uncompressed_layer_tar_bytes"],
            local["budgets"]["uncompressed_layer_tar_bytes"],
        )
        self.assertEqual(
            local["local_store_metric_note"],
            "diagnostic_only_engine_backend_dependent_not_gated",
        )
        self.assertNotIn("local_store_reported_bytes", local["budgets"])

    def test_evidence_artifact_and_every_downloaded_file_are_bound(self):
        expected = {
            "cad-author-f28-anonymous-smoke.json": (
                "9e5c7ee5aa4ffb64ef489bb20c263e14b54095656f9b0c3daaa9bb93088642c4",
                5055,
            ),
            "cad-author-f28-anonymous-smoke.stderr": (
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                0,
            ),
            "cad-author-f28-attestation-manifest.json": (
                "56cbcf8288cf306b362f45f806f1b6982dbcb4149ad78322d818cfbdd38dd7fa",
                1112,
            ),
            "cad-author-f28-builder.txt": (
                "b82b2d27bdb30d421b2bc2a7ebb2a516b05276d03aadd2e5c6116c599de3f2e1",
                1842,
            ),
            "cad-author-f28-image-ref.txt": (
                "dc65551b93458266f30e433176e14a6d494bb609cf6b0186f7e2dd8c59f2f52f",
                121,
            ),
            "cad-author-f28-index.json": (
                "18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57",
                857,
            ),
            "cad-author-f28-license-audit.json": (
                "435d64326ca4c0cf86dea89bbfb0a2c6c81724a168f312c59d33c217e482c008",
                1894,
            ),
            "cad-author-f28-platform-manifest.json": (
                "dbbebc784706f17a1d4f1d3c04df90baa551e0a72236bd29995f983735a6661b",
                3710,
            ),
            "cad-author-f28-provenance.json": (
                "91814defc5a3881ee27128a0367e5c598688711fce5e615a99fa1133dae2dc82",
                70062,
            ),
            "cad-author-f28-sbom.json": (
                "9ba2cf98acd42e44d06318d8d30c77864a607060ff28ea29b28c3754283ebaca",
                3838341,
            ),
            "cad-author-f28-size.json": (
                "7cbc72254ad18d06eb834c98ab15a416179d4b05d7b1818ab6b034ce14412105",
                740,
            ),
            "cad-author-f28-smoke.json": (
                "1a7851fe5ead0f7037044fdcf08cdcd46356b18964201b56d74e98c843dff4a7",
                5055,
            ),
            "cad-author-f28-smoke.stderr": (
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                0,
            ),
        }
        actual = {
            item["name"]: (item["sha256"], item["size_bytes"])
            for item in self.lock["verification"]["evidence_files"]
        }
        self.assertEqual(actual, expected)
        self.assertEqual(
            actual["cad-author-f28-index.json"][0],
            self.lock["image"]["digest"].removeprefix("sha256:"),
        )
        self.assertEqual(
            actual["cad-author-f28-platform-manifest.json"][0],
            self.lock["image"]["manifest"]["digest"].removeprefix("sha256:"),
        )
        self.assertEqual(
            actual["cad-author-f28-attestation-manifest.json"][0],
            self.lock["image"]["attestation_manifest"]["digest"].removeprefix("sha256:"),
        )
        empty_sha256 = hashlib.sha256(b"").hexdigest()
        for stderr_name in (
            "cad-author-f28-smoke.stderr",
            "cad-author-f28-anonymous-smoke.stderr",
        ):
            self.assertEqual(actual[stderr_name], (empty_sha256, 0))
        image_reference_bytes = (
            self.lock["image"]["immutable_reference"] + "\n"
        ).encode("ascii")
        self.assertEqual(
            actual["cad-author-f28-image-ref.txt"],
            (hashlib.sha256(image_reference_bytes).hexdigest(), len(image_reference_bytes)),
        )
        artifact = self.lock["verification"]["evidence_artifact"]
        self.assertEqual(artifact["id"], 9832322052)
        self.assertEqual(
            artifact["digest"],
            "sha256:74d475fba171164e7735e108b5feeb45215de0b38300f4e601b736cac395f799",
        )
        self.assertEqual(artifact["size_bytes"], 347872)
        self.assertFalse(artifact["expired"])

    def test_workflow_builder_provenance_sbom_and_public_pull_are_bound(self):
        verification = self.lock["verification"]
        workflow = verification["workflow"]
        builder = self.lock["recipe"]["builder"]
        self.assertEqual(workflow["run_id"], 33592654832)
        self.assertEqual(workflow["job_id"], 100129628308)
        self.assertEqual(workflow["conclusion"], "success")
        self.assertEqual(workflow["head_sha"], self.lock["recipe"]["workflow_head_sha"])
        self.assertEqual(
            verification["provenance"]["source_revision"],
            workflow["head_sha"],
        )
        self.assertEqual(
            verification["provenance"]["builder_id"],
            "https://github.com/cluster2600/3dprinting993/actions/runs/33592654832/attempts/1",
        )
        self.assertEqual(verification["provenance"]["resolved_dependency_count"], 4)
        self.assertTrue(verification["provenance"]["frontend_digest_present"])
        self.assertTrue(verification["provenance"]["base_image_digest_present"])
        self.assertEqual(builder["buildx_version"], "0.36.1")
        self.assertEqual(builder["buildkit_version"], "0.32.2")
        self.assertEqual(
            builder["buildkit_image"],
            "moby/buildkit@sha256:28a898719c18a33f4e8000685287fa36fd0dd9560c6440227d3a732d79bb41d8",
        )
        self.assertEqual(verification["sbom"]["spdx_version"], "SPDX-2.3")
        self.assertEqual(verification["sbom"]["data_license"], "CC0-1.0")
        self.assertEqual(verification["sbom"]["package_count"], 184)
        self.assertEqual(verification["sbom"]["file_count"], 3358)
        self.assertEqual(verification["sbom"]["relationship_count"], 4126)
        self.assertEqual(verification["sbom"]["packages"]["build123d"], "0.11.1")
        self.assertEqual(
            verification["sbom"]["packages"]["cadquery-ocp-novtk"],
            "7.9.3.1.1",
        )
        self.assertTrue(verification["published_digest_pulled"])
        self.assertTrue(verification["anonymous_exact_digest_access"])
        self.assertFalse(verification["cryptographic_signature_verified"])

    def test_recipe_rereads_every_exact_build_and_gate_input(self):
        inputs = self.lock["recipe"]["inputs"]
        self.assertEqual(len(inputs), 6)
        self.assertEqual(len({item["path"] for item in inputs}), len(inputs))
        for item in inputs:
            path = ROOT / item["path"]
            self.assertTrue(path.is_file(), item["path"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                item["sha256"],
                item["path"],
            )
        dependency = self.lock["verification"]["dependency_audit"]
        input_hashes = {item["path"]: item["sha256"] for item in inputs}
        self.assertEqual(
            dependency["requirements_sha256"],
            input_hashes["containers/cad-author-f28-requirements.txt"],
        )
        self.assertEqual(
            dependency["system_packages_sha256"],
            input_hashes["containers/cad-author-f28-system-packages.sha256"],
        )
        self.assertEqual(dependency["wheel_pin_count"], 46)
        self.assertEqual(dependency["wheel_hash_count"], 46)
        self.assertEqual(dependency["system_package_pin_count"], 11)
        self.assertEqual(dependency["system_package_hash_count"], 11)
        self.assertEqual(dependency["unexpected_distributions"], [])

    def test_smokes_prove_only_the_synthetic_cad_path(self):
        smoke = self.lock["verification"]["offline_smoke"]
        anonymous = self.lock["verification"]["anonymous_smoke"]
        self.assertEqual(smoke["status"], "passed_synthetic_cad_fixture_only")
        self.assertEqual(smoke["platform_contract"], "linux/amd64-cpu")
        self.assertEqual(smoke["runtime_uid_gid"], "9178:9178")
        self.assertEqual(smoke["kernel_interfaces"], ["lo"])
        self.assertEqual(smoke["fixture_kind"], "synthetic_box_with_through_bore")
        self.assertEqual(smoke["expected_volume_mm3"], 1819.469035085)
        self.assertEqual(smoke["step_export_bytes"], 18945)
        self.assertTrue(smoke["closed_solid_after_step_roundtrip"])
        self.assertFalse(smoke["canonical_scan_used"])
        self.assertFalse(smoke["vehicle_geometry_used"])
        self.assertNotEqual(
            smoke["authenticated_step_sha256_diagnostic_not_reproducibility_claim"],
            smoke["anonymous_step_sha256_diagnostic_not_reproducibility_claim"],
        )
        self.assertTrue(
            smoke["semantic_payloads_equal_after_removing_step_hash_diagnostic"]
        )
        self.assertTrue(smoke["authenticated_stderr_empty"])
        self.assertTrue(smoke["anonymous_stderr_empty"])
        self.assertTrue(anonymous["exact_digest_pulled_without_credentials"])
        self.assertTrue(anonymous["root_filesystem_read_only"])
        self.assertTrue(anonymous["network_none"])
        self.assertEqual(anonymous["capabilities_dropped"], "ALL")
        self.assertTrue(anonymous["no_new_privileges"])

    def test_only_image_gates_open_and_engine_release_stays_fail_closed(self):
        open_gates = {
            name for name, value in self.lock["release_gates"].items() if value
        }
        self.assertEqual(
            open_gates,
            {
                "immutable_public_image_verified",
                "linux_amd64_offline_synthetic_cad_smoke_verified",
            },
        )
        for gate in (
            "f27_physical_metrology_completed",
            "engine_identity_confirmed",
            "scan_identity_confirmed",
            "physical_scale_confirmed",
            "semantic_interfaces_confirmed",
            "engine_geometry_authored",
            "engine_assembly_released",
            "material_definitions_validated",
            "cae_geometry_released",
            "classical_solver_reference_cases_executed",
            "physicsnemo_dataset_released",
            "physicsnemo_surrogate_trained",
            "omniverse_simready_released",
            "manufacturing_release",
            "fabrication_release",
            "print_release",
            "engine_start_released",
            "functional_engine_release",
            "vast_job_allowed",
        ):
            self.assertFalse(self.lock["release_gates"][gate], gate)
        for name, value in self.lock["bundled_assets"].items():
            if name != "runtime_support_files":
                self.assertFalse(value, name)
        self.assertFalse(self.lock["known_limits"]["step_export_byte_reproducibility_claimed"])
        self.assertFalse(self.lock["known_limits"]["attestations_are_cryptographic_signature"])
        self.assertFalse(self.lock["known_limits"]["engine_geometry_or_function_claimed"])

    def test_lock_contains_no_private_assets_local_paths_or_large_attestations(self):
        serialized = LOCK.read_text(encoding="utf-8")
        self.assertLess(len(serialized.encode("utf-8")), 30000)
        for forbidden in (
            "/Users/",
            "work/917-engine/",
            "raw-scans/",
            "917-engine-case-with-cylinders.obj",
            "428c4143d073f8330022f2fecbd1ac1ee7784d4f1565f1160020448dbdffa0ae",
            "id_vastai",
            "BEGIN OPENSSH PRIVATE KEY",
            "IyBzeW50YXg9",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_documentation_names_exact_lock_run_sizes_and_fail_closed_scope(self):
        document = DOC.read_text(encoding="utf-8")
        for fragment in (
            "Publication immuable F28 vérifiée",
            "cad-author-f28.lock.json",
            "33592654832",
            "sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57",
            "9178:9178",
            "250 798 017",
            "865 096 192",
            "stderr",
            "accès anonyme",
            "ne prouve",
            "PhysicsNeMo",
            "Omniverse",
        ):
            self.assertIn(fragment.lower(), document.lower())


if __name__ == "__main__":
    unittest.main()
