"""Tests fail-closed du verrou de publication CPU air/huile F34b."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "containers/air-oil-cycle-f34b.lock.json"
DOC = ROOT / "docs/917_AIR_OIL_CYCLE_IMAGE_F34B.md"

IMAGE_DIGEST = (
    "sha256:369d51ee12c259e844d01817702d8debedcf400087ab9b289b8e59671d296664"
)
PLATFORM_MANIFEST_DIGEST = (
    "sha256:a998902efd809102035ae1b9ea07d6c6b207e9688557438efc5e543c1c181e9f"
)
ATTESTATION_MANIFEST_DIGEST = (
    "sha256:f32a53bbb42a443c498124630898ddc6a9ae8923384e89a5696206ffd0494f70"
)
SOURCE_SHA = "6a02829cdf6cd968086af63145259091d7f34937"
REPOSITORY = "ghcr.io/cluster2600/3dprinting993-air-oil-cycle-f34b"
IMMUTABLE_REFERENCE = f"{REPOSITORY}@{IMAGE_DIGEST}"
CANDIDATE_REFERENCE = f"{REPOSITORY}:candidate-{SOURCE_SHA}-33634398619-1"
VERIFIED_REFERENCE = f"{REPOSITORY}:verified-{SOURCE_SHA}-33634398619-1"

EXPECTED_LAYERS = [
    ("sha256:a8ac7f6c67abc236e4c745052c404112b8fab6fe8ac3a329d1ef3b867ad67c71", 28232655),
    ("sha256:268fd66f673d556a271a784d33c4541102f05dde43657861a8e793eb30ef38dd", 3533349),
    ("sha256:ec613f6df89286159c101a9b15264bc627366aaf788a9ea9c3a456ad9b9b2b3e", 13672032),
    ("sha256:35ef2f664a5c3b1e1408a24bd668ef33b82a89a534709e1c03aac6d50012d51a", 249),
    ("sha256:4f4fb700ef54461cfa02571ae0db9a0dc1e0cdb5577484a6d75e68dc38e8acc1", 32),
    ("sha256:e9137c83849af6541f0654f4073959d0e281d64db4106b2a07fd24ec4e87d359", 42639413),
    ("sha256:0b51a02beed51c379dbc226bc3103bc856459f4ee46f591a975f7e959bb1a78a", 517),
    ("sha256:c4764a8347907d5f0422701059fed6d2334cd2d56eec98ee4ab5b7c131f1a359", 6763),
    ("sha256:43852aaa70af2b7b26b29840be71bde2587e2abcc7cbb26728b2bf62d3eeb1e8", 14835),
    ("sha256:7228885cb0fc20a014de47af19dbaa05254b03a17d74efd5927cbdea2b0025b1", 4828),
    ("sha256:6de6dec3d4b92a03a04a0e1bf5a8f9f68c49c828948f5b0b4fa3de4f556728d9", 6905),
    ("sha256:fee19a812ba84aa52c77bf691644ed6115a7fbd96afe184e3dfe9c25b81f9d17", 3379),
    ("sha256:e3febbad5ce79b0902cf94a37b9ae68c744d964d2c3ff0ad74de1bd6629b77c2", 363790),
    ("sha256:06b9581148b070a891c1fa049c7f02a5ca083927b7dbba6bd24c850ea5fc1766", 398719),
    ("sha256:4f4fb700ef54461cfa02571ae0db9a0dc1e0cdb5577484a6d75e68dc38e8acc1", 32),
    ("sha256:4f4fb700ef54461cfa02571ae0db9a0dc1e0cdb5577484a6d75e68dc38e8acc1", 32),
]

EXPECTED_EVIDENCE = {
    "air-oil-cycle-f34b-anonymous-audit.json": ("5e3904759a67fda1e8eb00ed045d9f10b41e58467d078e1f2633c4a7c9caf897", 303),
    "air-oil-cycle-f34b-anonymous-pull.txt": ("253c2a83b9f6935be8ea93d44671fe2a09983ab28dcaaa5f62d115855ddc8b93", 2461),
    "air-oil-cycle-f34b-anonymous-smoke.json": ("6ac1e47137b7ac59aca615c18b18f2cce7675e8098ba34effc764ecd51f4e4ca", 8469),
    "air-oil-cycle-f34b-anonymous-smoke.stderr": ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", 0),
    "air-oil-cycle-f34b-attestation-manifest.json": ("f32a53bbb42a443c498124630898ddc6a9ae8923384e89a5696206ffd0494f70", 1112),
    "air-oil-cycle-f34b-builder.txt": ("845f0203debc5de6168bbb1ecced10aea0ace32d8f2e39f6ea1ab9fbb59fe25c", 1842),
    "air-oil-cycle-f34b-candidate-tag.txt": ("991a7282de7a77b62f736286a0f88071e7b33e920c9b9d4ff59bdba43633c502", 118),
    "air-oil-cycle-f34b-derived-fixtures.json": ("976e8cb69f781f845ea0f69921569e2fe331415673b01ad65ce985288a14f3a0", 14112),
    "air-oil-cycle-f34b-derived-fixtures.stderr": ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", 0),
    "air-oil-cycle-f34b-image-ref.txt": ("2344968f9e14d8737136e5d14504526d939dbd85c99078846bd584b3ebd31dfa", 125),
    "air-oil-cycle-f34b-index.json": ("369d51ee12c259e844d01817702d8debedcf400087ab9b289b8e59671d296664", 857),
    "air-oil-cycle-f34b-platform-manifest.json": ("a998902efd809102035ae1b9ea07d6c6b207e9688557438efc5e543c1c181e9f", 3326),
    "air-oil-cycle-f34b-provenance.json": ("005e63e3d5d9d9d64d2cc7fcc2fcf7101583876c2d4ec6b91170c76d6eeb345d", 60303),
    "air-oil-cycle-f34b-release-tag.txt": ("b1058941dc009f2a99a4a23f095d49ef0af3853d47c512b86edb36646cf82dc0", 117),
    "air-oil-cycle-f34b-sbom.json": ("a3f7eae0e0a3dbb9f6be55746856eba79216edf8e80f312ede0e04c6316110c8", 3314976),
    "air-oil-cycle-f34b-smoke.json": ("6ac1e47137b7ac59aca615c18b18f2cce7675e8098ba34effc764ecd51f4e4ca", 8469),
    "air-oil-cycle-f34b-smoke.stderr": ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", 0),
    "air-oil-cycle-f34b-source-inputs.sha256": ("49da03a2575a6f0a0e61d96d15abd09e3b2bb08989a1025df3f19191777b1d1e", 1681),
    "air-oil-cycle-f34b-static-tests.txt": ("dbed088784f2acdc6799c4518d37165585dd5d17eb9693e4a6a906cc1f961ca7", 7685),
}

EXPECTED_INPUTS = {
    ".github/workflows/air-oil-cycle-f34b-image.yml": "6d9a226c99b58cead3b2ac709dd94d36bed4bfe96b5243a1ab8790ed19af6f46",
    "containers/air-oil-cycle-f34b.Dockerfile": "b2e8f95347e9bc089926b3c7cf1c4fe973d0332d39bc540073af71843cbc6f5a",
    "containers/air-oil-cycle-f34b.Dockerfile.dockerignore": "5addbb9cb8c088a504a5a81e904b5f5652c95d280ea5c5f246713c39e5ca88f8",
    "containers/air-oil-cycle-f34b.requirements.txt": "1da2fe643628655b2468ad1f16d562b274c2bea0653542ed7eebddd99145ab15",
    "containers/air-oil-cycle-f34b-smoke.py": "b8e63c3267292b7fd526565465f783329b1f2b0f8e12e33728051ef3912bd9c5",
    "scripts/export_917_air_oil_seeds_f34b.py": "267156346170c5b90a8c2b5975a3f6736f3d63f0a428a4db1f98e6b087bde83a",
    "scripts/run_917_air_oil_cycle_f34b.py": "a42ccf2ebba58c698bc36facfc1233c6c6e437bd3a7e84069dd95a4e3d449548",
    "scripts/run_917_doe_f34.py": "763de9e7ab71b7d5365c404320d266760b7fa4b1fc2e7cc241ff24ed551adea4",
    "tests/test_917_air_oil_seeds_f34b.py": "a5e810c63801c0430873d4fe002ca0172da6899c163addc6a495e98527cf933a",
    "tests/test_917_air_oil_cycle_f34b.py": "25e9be4fe42912ffbfce4247ab801f37f67cae6aa3ab3f08865c743bd77e94ef",
    "tests/test_air_oil_cycle_f34b_image.py": "9084444ea16cc761f4a6ef7edf71b3c855237a4e3f510af529f3cdf70ac53cf9",
    "twins/reference-917-engine/air-oil-core-controls-f34a.json": "a1e4c7626fccf634856df4f167edfa0f1ad2a32337e4ff9e2386a6abf930c8fa",
    "twins/reference-917-engine/doe-surrogate-f34.json": "575de28758a6f65f5471e7d4767d0427c58a4ae87ec81b002c5097e2026edc4e",
    "twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json": "74745e4ac18915c224e40fae1dbae739a9b6eea2aa9b374d4d7cbc234cd21149",
    "twins/reference-917-engine/evidence/f34/doe-case-manifest.json": "665cbc390a38bf29b824a1d8b9743fd21c381bb46f5c91a8c85b2aab7330a5be",
}

EXPECTED_BUNDLE = {
    "requirements.txt": EXPECTED_INPUTS["containers/air-oil-cycle-f34b.requirements.txt"],
    "smoke.py": EXPECTED_INPUTS["containers/air-oil-cycle-f34b-smoke.py"],
    "scripts/run_917_air_oil_cycle_f34b.py": EXPECTED_INPUTS["scripts/run_917_air_oil_cycle_f34b.py"],
    "twins/reference-917-engine/air-oil-core-controls-f34a.json": EXPECTED_INPUTS["twins/reference-917-engine/air-oil-core-controls-f34a.json"],
    "twins/reference-917-engine/doe-surrogate-f34.json": EXPECTED_INPUTS["twins/reference-917-engine/doe-surrogate-f34.json"],
    "twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json": EXPECTED_INPUTS["twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json"],
    "twins/reference-917-engine/evidence/f34/doe-case-manifest.json": EXPECTED_INPUTS["twins/reference-917-engine/evidence/f34/doe-case-manifest.json"],
}

PHYSICAL_GATES = {
    "target_definition_complete",
    "target_power_proven",
    "mass_and_energy_balance_validated",
    "thermodynamic_cycle_validated",
    "air_cooling_validated",
    "oil_system_validated",
    "turbo_match_validated",
    "combustion_and_knock_validated",
    "controls_and_overspeed_protection_validated",
    "structural_and_fatigue_validated",
    "doe_execution_complete",
    "physical_correlation_complete",
    "test_bench_start_authorized",
    "porsche_993_packaging_validated",
    "porsche_993_vehicle_installation_authorized",
    "metal_print_authorized",
    "manufacturing_authorized",
}

TRUE_SOFTWARE_GATES = {
    "workflow_source_on_main_verified",
    "exact_source_inputs_recorded",
    "static_test_suite_passed",
    "linux_amd64_image_published",
    "registry_index_digest_recomputed",
    "platform_manifest_digest_recomputed",
    "attestation_manifest_digest_recomputed",
    "sbom_attestation_present",
    "provenance_attestation_present",
    "hardened_offline_smoke_passed",
    "synthetic_noncanonical_fixture_smoke_passed",
    "anonymous_exact_digest_pull_verified",
    "anonymous_offline_smoke_byte_identical",
    "verified_tag_promoted_after_gates",
}
FALSE_SOFTWARE_GATES = {
    "cryptographic_signature_verified",
    "semantic_content_license_audit_performed",
    "vulnerability_scan_completed",
}


class AirOilCycleF34bLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))

    def test_exact_public_image_platform_and_attestations_are_pinned(self):
        lock = self.lock
        image = lock["image"]
        self.assertEqual(lock["phase"], "F34b")
        self.assertEqual(
            set(lock),
            {
                "$comment",
                "schema_version",
                "phase",
                "status",
                "claim_scope",
                "image",
                "recipe",
                "verification",
                "bundled_assets",
                "release_gates",
                "known_limits",
            },
        )
        self.assertEqual(
            lock["status"],
            "immutable_public_cpu_air_oil_runtime_verified_all_engine_physical_release_blocked",
        )
        self.assertEqual(image["repository"], REPOSITORY)
        self.assertEqual(image["digest"], IMAGE_DIGEST)
        self.assertEqual(image["immutable_reference"], IMMUTABLE_REFERENCE)
        self.assertEqual(image["candidate_reference"], CANDIDATE_REFERENCE)
        self.assertEqual(image["verified_tag_reference"], VERIFIED_REFERENCE)
        self.assertFalse(image["tags_are_release_authority"])
        self.assertEqual(image["index"]["size_bytes"], 857)
        self.assertTrue(image["index"]["digest_recomputed"])
        self.assertEqual(image["index"]["platform_manifest_count"], 1)
        self.assertEqual(image["index"]["attestation_manifest_count"], 1)
        self.assertEqual(image["platform"]["os"], "linux")
        self.assertEqual(image["platform"]["architecture"], "amd64")
        self.assertEqual(image["platform"]["user"], "9133:9133")
        self.assertEqual(image["platform"]["python_version"], "3.12.14")
        self.assertEqual(image["platform"]["cantera_version"], "3.2.0")
        self.assertEqual(image["platform"]["numpy_version"], "2.5.2")
        self.assertFalse(image["platform"]["gpu_required"])
        self.assertEqual(image["manifest"]["digest"], PLATFORM_MANIFEST_DIGEST)

        attestation = image["attestation_manifest"]
        self.assertEqual(attestation["digest"], ATTESTATION_MANIFEST_DIGEST)
        self.assertEqual(attestation["subject_manifest_digest"], PLATFORM_MANIFEST_DIGEST)
        self.assertEqual(attestation["subject_manifest_size_bytes"], 3326)
        predicates = {item["predicate_type"]: item for item in attestation["predicate_layers"]}
        self.assertEqual(
            set(predicates),
            {"https://spdx.dev/Document", "https://slsa.dev/provenance/v1"},
        )
        self.assertEqual(
            predicates["https://spdx.dev/Document"],
            {
                "predicate_type": "https://spdx.dev/Document",
                "digest": "sha256:1ed9b54fb4fc87052a11865dd172b6575770affccf1a160c7c65debd8818dc65",
                "size_bytes": 2446934,
            },
        )
        self.assertEqual(
            predicates["https://slsa.dev/provenance/v1"],
            {
                "predicate_type": "https://slsa.dev/provenance/v1",
                "digest": "sha256:08dfdb3f83aa104d5fa66a80ffa7b48757f8977af41d9cc25fb8ece2c19d2614",
                "size_bytes": 31928,
            },
        )

    def test_platform_manifest_layers_and_sizes_are_exact(self):
        manifest = self.lock["image"]["manifest"]
        actual_layers = [(item["digest"], item["size_bytes"]) for item in manifest["layers"]]
        self.assertEqual(actual_layers, EXPECTED_LAYERS)
        self.assertEqual(manifest["layer_count"], 16)
        self.assertEqual(manifest["layer_count"], len(actual_layers))
        self.assertEqual(manifest["compressed_size_bytes"], 88877530)
        self.assertEqual(
            manifest["compressed_size_bytes"],
            sum(size for _, size in actual_layers),
        )
        self.assertEqual(
            (manifest["largest_layer_digest"], manifest["largest_layer_bytes"]),
            max(actual_layers, key=lambda item: item[1]),
        )
        self.assertEqual(
            (manifest["config_digest"], manifest["config_size_bytes"]),
            (
                "sha256:1d4d76bf43e489480d287f9d41844ba8616269996574079b4d6b835a7e1248be",
                12785,
            ),
        )

    def test_workflow_artifact_and_all_nineteen_evidence_files_are_bound(self):
        verification = self.lock["verification"]
        workflow = verification["workflow"]
        self.assertEqual(workflow["run_id"], 33634398619)
        self.assertEqual(workflow["job_id"], 100261510400)
        self.assertEqual(workflow["head_sha"], SOURCE_SHA)
        self.assertEqual(workflow["conclusion"], "success")
        self.assertEqual(workflow["run_attempt"], 1)

        artifact = verification["evidence_artifact"]
        self.assertEqual(artifact["id"], 9848193764)
        self.assertEqual(
            artifact["name"],
            f"air-oil-cycle-f34b-{SOURCE_SHA}-33634398619-1",
        )
        self.assertEqual(
            artifact["digest"],
            "sha256:7cb73a86d2eb7a9c6beafea41bd10dc588207615964460b4de3d57380b27aca4",
        )
        self.assertEqual(artifact["size_bytes"], 324511)
        self.assertFalse(artifact["expired"])

        actual = {
            item["name"]: (item["sha256"], item["size_bytes"])
            for item in verification["evidence_files"]
        }
        self.assertEqual(len(actual), 19)
        self.assertEqual(actual, EXPECTED_EVIDENCE)
        self.assertEqual(actual["air-oil-cycle-f34b-index.json"][0], IMAGE_DIGEST.removeprefix("sha256:"))
        self.assertEqual(actual["air-oil-cycle-f34b-platform-manifest.json"][0], PLATFORM_MANIFEST_DIGEST.removeprefix("sha256:"))
        self.assertEqual(actual["air-oil-cycle-f34b-attestation-manifest.json"][0], ATTESTATION_MANIFEST_DIGEST.removeprefix("sha256:"))
        empty = hashlib.sha256(b"").hexdigest()
        for name in (
            "air-oil-cycle-f34b-smoke.stderr",
            "air-oil-cycle-f34b-derived-fixtures.stderr",
            "air-oil-cycle-f34b-anonymous-smoke.stderr",
        ):
            self.assertEqual(actual[name], (empty, 0))
        self.assertEqual(
            actual["air-oil-cycle-f34b-smoke.json"],
            actual["air-oil-cycle-f34b-anonymous-smoke.json"],
        )
        image_ref_payload = (IMMUTABLE_REFERENCE + "\n").encode("ascii")
        self.assertEqual(
            actual["air-oil-cycle-f34b-image-ref.txt"],
            (hashlib.sha256(image_ref_payload).hexdigest(), len(image_ref_payload)),
        )

    def test_provenance_sbom_registry_and_recipe_are_exact(self):
        verification = self.lock["verification"]
        provenance = verification["provenance"]
        self.assertEqual(
            provenance["layer_digest"],
            "sha256:08dfdb3f83aa104d5fa66a80ffa7b48757f8977af41d9cc25fb8ece2c19d2614",
        )
        self.assertEqual(provenance["source_repository"], "https://github.com/cluster2600/3dprinting993")
        self.assertEqual(provenance["source_revision"], SOURCE_SHA)
        self.assertEqual(
            provenance["builder_id"],
            "https://github.com/cluster2600/3dprinting993/actions/runs/33634398619/attempts/1",
        )
        self.assertEqual(provenance["resolved_dependency_count"], 4)

        sbom = verification["sbom"]
        self.assertEqual(
            sbom["layer_digest"],
            "sha256:1ed9b54fb4fc87052a11865dd172b6575770affccf1a160c7c65debd8818dc65",
        )
        self.assertEqual(sbom["spdx_version"], "SPDX-2.3")
        self.assertEqual(sbom["data_license"], "CC0-1.0")
        self.assertEqual(sbom["package_count"], 118)
        self.assertEqual(sbom["file_count"], 3244)
        self.assertEqual(sbom["relationship_count"], 3823)
        self.assertEqual(
            sbom["packages"],
            {"cantera": "3.2.0", "numpy": "2.5.2", "typing-extensions": "4.16.0"},
        )

        registry = verification["registry"]
        self.assertTrue(registry["package_public"])
        self.assertEqual(registry["package_id"], 14809188)
        self.assertEqual(registry["index_version_id"], 1200441449)
        self.assertTrue(registry["published_digest_pulled"])
        self.assertTrue(registry["anonymous_exact_digest_access"])
        self.assertTrue(registry["verified_tag_promoted_after_anonymous_gate"])
        self.assertFalse(registry["cryptographic_signature_verified"])

        recipe = self.lock["recipe"]
        self.assertEqual(
            recipe["dockerfile_frontend_digest"],
            "sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e",
        )
        self.assertEqual(
            recipe["base_image"],
            "python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2da18516d0b1c2126ec22c195d2185e97347c9d98398c5bef",
        )
        self.assertEqual(recipe["builder"]["buildx_version"], "0.36.1")
        self.assertEqual(recipe["builder"]["buildkit_version"], "0.32.2")
        self.assertEqual(
            recipe["builder"]["buildkit_image"],
            "moby/buildkit@sha256:28a898719c18a33f4e8000685287fa36fd0dd9560c6440227d3a732d79bb41d8",
        )

    def test_recipe_rereads_all_fifteen_exact_source_inputs(self):
        recipe = self.lock["recipe"]
        self.assertEqual(recipe["workflow_head_sha"], SOURCE_SHA)
        inputs = recipe["inputs"]
        self.assertEqual(len(inputs), 15)
        self.assertEqual(
            {item["path"]: item["sha256"] for item in inputs},
            EXPECTED_INPUTS,
        )
        self.assertEqual(len({item["path"] for item in inputs}), 15)
        for item in inputs:
            source = ROOT / item["path"]
            self.assertTrue(source.is_file(), item["path"])
            self.assertEqual(
                hashlib.sha256(source.read_bytes()).hexdigest(),
                item["sha256"],
                item["path"],
            )

    def test_bundle_is_exactly_seven_public_files_without_semantic_overclaim(self):
        audit = self.lock["bundled_assets"]
        self.assertEqual(audit["file_count"], 7)
        self.assertEqual(audit["exact_files_sha256"], EXPECTED_BUNDLE)
        self.assertFalse(audit["contains_scan_or_print_geometry"])
        self.assertFalse(audit["contains_model_weights"])
        self.assertFalse(audit["contains_proprietary_manual"])
        self.assertFalse(audit["contains_secret_named_files"])
        self.assertFalse(audit["contains_network_or_process_solver_api"])
        self.assertFalse(audit["semantic_content_license_audit_performed"])

    def test_default_smoke_is_preflight_only_with_all_physical_gates_closed(self):
        smoke = self.lock["verification"]["runtime_smoke"]
        self.assertTrue(smoke["authenticated_and_anonymous_outputs_byte_identical"])
        self.assertTrue(smoke["offline"])
        self.assertTrue(smoke["non_root"])
        self.assertTrue(smoke["network_isolation_verified"])
        self.assertTrue(smoke["generic_cantera_fixture_only_in_default_command"])
        self.assertEqual(smoke["canonical_doe_cases_planned"], 2570)
        self.assertEqual(smoke["canonical_doe_cases_executed"], 0)
        for key in (
            "authoritative_engine_power_prediction_available",
            "validated_1600_hp",
            "physicsnemo_executed",
            "omniverse_executed",
            "vast_used",
        ):
            self.assertFalse(smoke[key], key)

    def test_two_synthetic_fixtures_are_noncanonical_and_nonauthoritative(self):
        smoke = self.lock["verification"]["runtime_smoke"]
        self.assertEqual(smoke["synthetic_noncanonical_fixture_cases_executed"], 2)
        self.assertEqual(smoke["source_seed_cases_executed"], 0)
        self.assertEqual(smoke["canonical_doe_cases_executed"], 0)
        self.assertFalse(smoke["authoritative_engine_power_prediction_available"])
        self.assertFalse(smoke["validated_1600_hp"])
        self.assertEqual(
            EXPECTED_EVIDENCE["air-oil-cycle-f34b-derived-fixtures.json"],
            ("976e8cb69f781f845ea0f69921569e2fe331415673b01ad65ce985288a14f3a0", 14112),
        )

    def test_only_exact_software_gates_open_and_physical_gates_stay_closed(self):
        software = self.lock["release_gates"]["software"]
        self.assertEqual(
            software,
            {
                "immutable_public_image_verified": True,
                "offline_linux_amd64_smoke_verified": True,
                "anonymous_exact_digest_access_verified": True,
                "supply_chain_metadata_bound": True,
                "two_noncanonical_regression_fixtures_verified": True,
            },
        )

        physical = self.lock["release_gates"]["physical"]
        self.assertEqual(set(physical), PHYSICAL_GATES)
        self.assertTrue(all(value is False for value in physical.values()))

    def test_lock_contains_no_private_payload_secret_or_embedded_attestation(self):
        serialized = LOCK.read_text(encoding="utf-8")
        self.assertLess(len(serialized.encode("utf-8")), 50000)
        for forbidden in (
            "/Users/",
            "/private/tmp/",
            "/tmp/f34b-evidence",
            "work/917-engine/",
            "raw-scans/",
            "917-engine-case-with-cylinders.obj",
            "id_vastai",
            "BEGIN OPENSSH PRIVATE KEY",
            "OPENBAO_TOKEN",
            "GHCR_TOKEN",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertIsNone(
            re.search(r'"(?:data|payload|content)"\s*:\s*"[A-Za-z0-9+/]{256,}={0,2}"', serialized)
        )

    def test_documentation_names_digest_run_lock_and_fail_closed_scope(self):
        document = DOC.read_text(encoding="utf-8").lower()
        for fragment in (
            "publication immuable f34b vérifiée",
            "air-oil-cycle-f34b.lock.json",
            "33634398619",
            IMAGE_DIGEST,
            "linux/amd64",
            "9133:9133",
            "accès anonyme",
            "2 570 cas planifiés",
            "aucun cas canonique",
            "exécuté",
            "ne prouve pas",
            "1 600 ch",
            "physicsnemo",
            "omniverse",
            "vast.ai",
            "signature cryptographique",
        ):
            self.assertIn(fragment.lower(), document)


if __name__ == "__main__":
    unittest.main()
