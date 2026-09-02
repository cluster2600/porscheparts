"""Contrats de l'inventaire exhaustif des frontières du scan 917 F18."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "twins/reference-917-engine/source/review_boundary_components_f18.py"
)
DOC = ROOT / "docs/917_BOUNDARY_HUMAN_REVIEW_F18.md"
EVIDENCE = ROOT / "twins/reference-917-engine/boundary-review-execution-evidence-f18.json"
LOCK = ROOT / "containers/scan-mesh-f17.lock.json"
LOCAL_OUTPUT = ROOT / "work/917-engine/boundary-review-f18-published"


class BoundaryReviewF18Tests(unittest.TestCase):
    def test_source_est_parseable_exhaustif_et_fail_closed(self):
        source = SCRIPT.read_text(encoding="utf-8")
        ast.parse(source)
        for fragment in (
            'REPORT_NAME = "boundary-review-f18.json"',
            'PLY_NAME = "boundary-components-f18.ply"',
            '"allowed_review_classes": ["candidate", "unclassified"]',
            '"boundary_components_truncated": False',
            '"semantic_identification_applied": False',
            '"interface_confirmed": False',
            '"human_review_state": "pending"',
            '"confirmed_interface_count": 0',
            '"projected_area_obj_units_squared"',
            '"perimeter_obj_units"',
            '"centroid_obj_units"',
            '"bounds_min_obj_units"',
            '"bounds_max_obj_units"',
            '"planarity_ratio"',
            '"relative_circle_fit_p95"',
            '"candidate_score"',
            '"--input-sha256"',
            '"--expected-boundary-components"',
            'json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)',
        ):
            self.assertIn(fragment, source)
        self.assertNotIn('"interface_confirmed": True', source)
        self.assertNotIn('"semantic_label": "', source)

    def test_documentation_lie_f16_f17_et_interdit_les_conclusions_physiques(self):
        document = DOC.read_text(encoding="utf-8")
        for fragment in (
            "```mermaid",
            "944 composantes",
            "F16",
            "F17",
            "101 809",
            "lecture seule",
            "boundary-review-f18.json",
            "boundary-components-f18.ply",
            "candidate",
            "unclassified",
            "revue humaine",
            "hors Git",
            "PhysicsNeMo",
            "ne confirme aucune interface",
            "--expected-boundary-components 944",
            "sha256:b48f23d64ceab9c2e6b7b7474cdd81011d27b8a584f7af6b50b6cc05823c5189",
        ):
            self.assertIn(fragment, document)

    @unittest.skipUnless(
        importlib.util.find_spec("numpy") is not None,
        "le test géométrique s'exécute dans l'environnement NumPy/F17",
    )
    def test_fixture_synthetique_exerce_metriques_classes_et_ply(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--synthetic-self-test",
                    "--output",
                    str(output),
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertIn('"confirmed_interface_count": 0', completed.stdout)
            report = json.loads(
                (output / "boundary-review-f18.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["topology"]["boundary_components"], 2)
            self.assertEqual(report["topology"]["reported_boundary_components"], 2)
            self.assertFalse(report["topology"]["boundary_components_truncated"])
            self.assertEqual(
                report["summary"],
                {
                    "candidate_count": 1,
                    "unclassified_count": 1,
                    "confirmed_interface_count": 0,
                    "human_review_pending_count": 2,
                },
            )
            self.assertEqual(
                [item["component_id"] for item in report["components"]],
                ["boundary_0001", "boundary_0002"],
            )
            self.assertEqual(
                [item["review_class"] for item in report["components"]],
                ["candidate", "unclassified"],
            )
            for component in report["components"]:
                self.assertIsNone(component["semantic_label"])
                self.assertFalse(component["interface_confirmed"])
                self.assertEqual(component["human_review_state"], "pending")
                self.assertEqual(len(component["centroid_obj_units"]), 3)
                self.assertEqual(len(component["bounds_min_obj_units"]), 3)
                self.assertEqual(len(component["bounds_max_obj_units"]), 3)
                self.assertGreater(component["perimeter_obj_units"], 0.0)
                self.assertTrue(math.isfinite(component["candidate_score"]))
            self.assertTrue(all(value is False for value in report["release_gates"].values()))

            ply = (output / "boundary-components-f18.ply").read_bytes()
            header, payload = ply.split(b"end_header\n", 1)
            self.assertIn(b"format binary_little_endian 1.0", header)
            self.assertIn(b"element vertex 35", header)
            self.assertIn(b"property uint component_rank", header)
            self.assertIn(b"property uchar candidate", header)
            self.assertTrue(payload)
            self.assertEqual(
                report["visualization"]["point_count"],
                report["topology"]["boundary_vertices"],
            )

    def test_preuve_canonique_reste_agregee_et_fail_closed(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(evidence["phase"], "F18")
        self.assertEqual(
            evidence["execution"]["image_reference"],
            lock["image"]["immutable_reference"],
        )
        self.assertEqual(
            hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
            evidence["execution"]["script"]["sha256"],
        )
        inventory = evidence["inventory"]
        self.assertEqual(inventory["boundary_components"], 944)
        self.assertEqual(inventory["reported_boundary_components"], 944)
        self.assertEqual(inventory["candidate_count"], 19)
        self.assertEqual(inventory["unclassified_count"], 925)
        self.assertEqual(inventory["confirmed_interface_count"], 0)
        self.assertEqual(inventory["human_review_pending_count"], 944)
        self.assertFalse(inventory["diameter_filter_applied"])
        self.assertFalse(inventory["semantic_identification_applied"])
        self.assertTrue(all(value is False for value in evidence["tracked_summary_content"].values()))
        self.assertEqual(
            {name for name, value in evidence["release_gates"].items() if value},
            {"canonical_f18_execution_observed_locally_in_immutable_runtime"},
        )

        serialized = EVIDENCE.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", serialized)
        self.assertNotIn('"centroid_obj_units"', serialized)
        self.assertNotIn('"normal_unoriented_scan_coordinates"', serialized)
        self.assertNotIn('"bounds_min_obj_units"', serialized)

    def test_sorties_locales_correspondent_aux_empreintes_si_presentes(self):
        if not LOCAL_OUTPUT.is_dir():
            self.skipTest("sorties locales F18 absentes de cet environnement")
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        for item in evidence["outputs_local_only"]:
            path = LOCAL_OUTPUT / item["name"]
            self.assertTrue(path.is_file(), item["name"])
            self.assertEqual(path.stat().st_size, item["bytes"], item["name"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                item["sha256"],
                item["name"],
            )
            self.assertTrue(item["contains_derived_coordinates"])
            self.assertFalse(item["committed"])


if __name__ == "__main__":
    unittest.main()
