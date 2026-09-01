"""Tests statiques de l'image CPU OBJ F15, sans construire ni publier."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "containers/obj-metrology-f15.Dockerfile"
REQUIREMENTS = ROOT / "containers/obj-metrology-f15-requirements.txt"
SMOKE = ROOT / "containers/obj-metrology-f15-smoke.py"
PIPELINE = ROOT / "twins/reference-917-engine/source/build_scan_segmentation_f15.py"
CONTRACT = ROOT / "twins/reference-917-engine/scan-segmentation-f15.json"
WORKFLOW = ROOT / ".github/workflows/obj-metrology-f15-image.yml"
DOC = ROOT / "docs/917_OBJ_METROLOGY_CONTAINER_F15.md"
LOCK = ROOT / "containers/obj-metrology-f15.lock.json"


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("obj_metrology_f15_smoke", SMOKE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ObjMetrologyF15ImageTests(unittest.TestCase):
    def test_dockerfile_est_stdlib_epingle_amd64_et_non_root(self):
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        for fragment in (
            "python:3.12.14-slim-bookworm@sha256:9c47360a2a0355e2",
            'test "${TARGETARCH}" = "amd64"',
            "build_scan_segmentation_f15.py /opt/3dprinting993/twins/reference-917-engine/source/build_scan_segmentation_f15.py",
            "scan-segmentation-f15.json /opt/3dprinting993/twins/reference-917-engine/scan-segmentation-f15.json",
            "METROLOGY_UID=9175",
            "METROLOGY_GID=9175",
            "USER ${METROLOGY_UID}:${METROLOGY_GID}",
            "obj-metrology-f15-smoke",
        ):
            self.assertIn(fragment, dockerfile)
        copy_lines = [
            line.strip() for line in dockerfile.splitlines() if line.startswith("COPY ")
        ]
        self.assertEqual(
            copy_lines,
            [
                "COPY twins/reference-917-engine/source/build_scan_segmentation_f15.py /opt/3dprinting993/twins/reference-917-engine/source/build_scan_segmentation_f15.py",
                "COPY twins/reference-917-engine/scan-segmentation-f15.json /opt/3dprinting993/twins/reference-917-engine/scan-segmentation-f15.json",
                "COPY containers/obj-metrology-f15-smoke.py /usr/local/bin/obj-metrology-f15-smoke",
            ],
        )
        for forbidden in (
            "apt-get",
            "pip install",
            "cuda",
            "nvidia",
            "physicsnemo",
            "numpy",
            "trimesh",
            "networkx",
            "COPY .",
            "COPY raw-scans",
            "COPY work",
            "EXPOSE",
        ):
            self.assertNotIn(forbidden.lower(), dockerfile.lower())

    def test_requirements_documente_zero_dependance(self):
        requirements = REQUIREMENTS.read_text(encoding="utf-8")
        self.assertIn("standard-library-only", requirements)
        self.assertNotIn("==", requirements)
        self.assertNotIn("--hash", requirements)

    def test_smoke_execute_le_vrai_pipeline_sur_fixture(self):
        smoke = _load_smoke_module()
        with patch.object(sys, "version_info", (3, 12, 0)), patch.object(
            smoke.os, "geteuid", return_value=9175
        ):
            report = smoke.run_smoke(pipeline=PIPELINE, contract=CONTRACT)
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["offline_smoke"])
        self.assertTrue(report["non_root"])
        self.assertEqual(report["pipeline"]["implementation"], "python_standard_library_only")
        self.assertEqual(report["pipeline"]["report_status"], "passed_synthetic_fixture_only")
        self.assertEqual(report["pipeline"]["surface_components"], 2)
        self.assertEqual(len(report["pipeline"]["output_files"]), 4)
        self.assertFalse(report["gpu_required"])
        self.assertEqual(
            report["bundled_assets"],
            {"raw_scans": False, "datasets": False, "model_weights": False, "secrets": False},
        )

    def test_smoke_refuse_root(self):
        smoke = _load_smoke_module()
        with patch.object(sys, "version_info", (3, 12, 0)), patch.object(
            smoke.os, "geteuid", return_value=0
        ):
            with self.assertRaisesRegex(RuntimeError, "sans privilèges root"):
                smoke.run_smoke(pipeline=PIPELINE, contract=CONTRACT)

    def test_workflow_garde_digest_provenance_et_execution_hors_ligne(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for fragment in (
            "workflow_dispatch:",
            "platforms: linux/amd64",
            "provenance: mode=max",
            "sbom: true",
            "steps.build.outputs.digest",
            "tag_digest",
            "for attempt in 1 2 3 4 5",
            ".SLSA.buildDefinition.buildType",
            ".SLSA.runDetails.builder.id",
            ".SLSA.buildDefinition.resolvedDependencies",
            "docker pull --platform linux/amd64",
            "--network none --read-only",
            "--cap-drop ALL",
            "--security-opt no-new-privileges",
            "DOCKER_CONFIG=\"${anonymous_config}\"",
        ):
            self.assertIn(fragment, workflow)
        self.assertNotIn(":latest", workflow)
        self.assertNotIn("vast", workflow.lower())

    def test_lock_fixe_index_manifest_et_runtime_amd64(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        image = lock["image"]
        self.assertEqual(lock["schema_version"], "1.0.0")
        self.assertEqual(lock["phase"], "F15")
        self.assertEqual(
            image["repository"],
            "ghcr.io/cluster2600/3dprinting993-obj-metrology-f15",
        )
        self.assertRegex(image["digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(
            image["immutable_reference"],
            f"{image['repository']}@{image['digest']}",
        )
        self.assertEqual(
            image["digest"],
            "sha256:827e639cd126441dfa98fc097d4c8b09a01a28e25545de62ca3a01da963b959a",
        )
        self.assertEqual(
            image["index"]["media_type"], "application/vnd.oci.image.index.v1+json"
        )
        self.assertEqual(image["index"]["size_bytes"], 857)
        self.assertTrue(image["index"]["digest_recomputed"])
        self.assertEqual(image["index"]["platform_manifest_count"], 1)
        self.assertEqual(image["index"]["attestation_manifest_count"], 1)
        self.assertEqual(
            image["platform"],
            {
                "os": "linux",
                "architecture": "amd64",
                "user": "9175:9175",
                "python_version": "3.12.14",
            },
        )

        manifest = image["manifest"]
        self.assertEqual(
            manifest["digest"],
            "sha256:38b88c59b7b78bd17704a909175b0f46aa4d19fd64c90a76a42be200e10397bb",
        )
        self.assertEqual(manifest["layer_count"], 11)
        self.assertEqual(manifest["compressed_size_bytes"], 45462453)
        self.assertEqual(manifest["largest_layer_bytes"], 28232655)
        self.assertLess(
            manifest["largest_layer_bytes"],
            manifest["limits"]["max_layer_bytes_exclusive"],
        )
        self.assertLess(
            manifest["compressed_size_bytes"],
            manifest["limits"]["max_total_bytes_exclusive"],
        )
        self.assertTrue(manifest["limits_passed"])
        self.assertEqual(
            image["attestation_manifest"]["subject_manifest_digest"],
            manifest["digest"],
        )

    def test_lock_relit_les_sha256_des_six_entrees(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        inputs = lock["recipe"]["inputs"]
        self.assertEqual(len(inputs), 6)
        self.assertEqual(len({item["path"] for item in inputs}), 6)
        for item in inputs:
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
            path = ROOT / item["path"]
            self.assertTrue(path.is_file(), item["path"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                item["sha256"],
                item["path"],
            )

    def test_lock_atteste_workflow_sbom_slsa_et_smoke_hors_ligne(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        verification = lock["verification"]
        self.assertEqual(verification["status"], "passed")
        self.assertEqual(verification["workflow"]["run_id"], 33571699112)
        self.assertEqual(verification["workflow"]["conclusion"], "success")
        self.assertEqual(
            verification["workflow"]["url"],
            "https://github.com/cluster2600/3dprinting993/actions/runs/33571699112",
        )
        self.assertRegex(
            verification["evidence_artifact"]["digest"],
            r"^sha256:[0-9a-f]{64}$",
        )
        for gate in (
            "registry_index_digest_recomputed",
            "platform_manifest_digest_recomputed",
            "attestation_manifest_digest_recomputed",
            "published_digest_pulled",
            "anonymous_exact_digest_access",
        ):
            self.assertTrue(verification[gate], gate)

        provenance = verification["provenance"]
        self.assertEqual(provenance["predicate_type"], "https://slsa.dev/provenance/v1")
        self.assertEqual(provenance["resolved_dependency_count"], 3)
        self.assertIn("/actions/runs/33571699112/attempts/1", provenance["builder_id"])
        self.assertRegex(provenance["layer_digest"], r"^sha256:[0-9a-f]{64}$")
        sbom = verification["sbom"]
        self.assertEqual(sbom["predicate_type"], "https://spdx.dev/Document")
        self.assertRegex(sbom["layer_digest"], r"^sha256:[0-9a-f]{64}$")

        smoke = verification["offline_smoke"]
        self.assertEqual(smoke["status"], "passed")
        self.assertTrue(smoke["offline"])
        self.assertTrue(smoke["non_root"])
        self.assertFalse(smoke["gpu_required"])
        self.assertTrue(smoke["synthetic_fixture_only"])
        self.assertEqual(smoke["surface_components"], 2)
        self.assertEqual(smoke["output_file_count"], 4)

    def test_lock_reste_fail_closed_hors_image_cpu(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(
            lock["bundled_assets"],
            {
                "raw_scans": False,
                "datasets": False,
                "model_weights": False,
                "secrets": False,
            },
        )
        gates = lock["release_gates"]
        self.assertEqual(
            {name for name, value in gates.items() if value is True},
            {
                "immutable_public_image_verified",
                "linux_amd64_offline_smoke_verified",
            },
        )
        for name in (
            "canonical_scan_execution_verified_in_image",
            "scan_identity_confirmed",
            "scan_scale_confirmed",
            "metric_units_confirmed",
            "semantic_segmentation_confirmed",
            "geometry_repaired",
            "dimensioned_cad_reconstruction_complete",
            "classical_solver_reference_cases_executed",
            "physicsnemo_dataset_released",
            "physicsnemo_surrogate_trained",
            "physical_correlation_completed",
            "engine_simulation_validated",
            "manufacturing_release",
            "print_release",
            "functional_engine_release",
            "vast_rental_verified_for_current_job",
            "vast_job_allowed",
        ):
            self.assertIs(gates[name], False, name)

    def test_documentation_est_fail_closed_et_contient_le_flux_mermaid(self):
        document = DOC.read_text(encoding="utf-8")
        for fragment in (
            "```mermaid",
            "segmentation géométrique",
            "ne prouve pas",
            "digest immuable",
            "linux/amd64",
            "aucun scan",
            "sans GPU",
            "Vast.ai",
            "bibliothèque standard",
            "obj-metrology-f15.lock.json",
            "sha256:827e639cd126441dfa98fc097d4c8b09a01a28e25545de62ca3a01da963b959a",
        ):
            self.assertIn(fragment, document)


if __name__ == "__main__":
    unittest.main()
