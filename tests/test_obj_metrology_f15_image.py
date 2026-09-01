"""Tests statiques de l'image CPU OBJ F15, sans construire ni publier."""

from __future__ import annotations

import importlib.util
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
            '.["linux/amd64"].SLSA.buildType',
            "docker pull --platform linux/amd64",
            "--network none --read-only",
            "--cap-drop ALL",
            "--security-opt no-new-privileges",
            "DOCKER_CONFIG=\"${anonymous_config}\"",
        ):
            self.assertIn(fragment, workflow)
        self.assertNotIn(":latest", workflow)
        self.assertNotIn("vast", workflow.lower())

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
        ):
            self.assertIn(fragment, document)


if __name__ == "__main__":
    unittest.main()
