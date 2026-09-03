#!/usr/bin/env python3
"""Tests fail-closed de la chaine mecanique F42.1."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source/run_f42_1_conformal_calculix.py"
REPORT = ROOT / (
    "twins/reference-917-engine/evidence/f42-1-conformal-mechanics/"
    "917-head-f42-1-conformal-mechanics-public-report.json"
)
IMAGE = ROOT / (
    "twins/reference-917-engine/evidence/f42-1-conformal-mechanics/"
    "917-head-f42-1-conformal-mechanics.png"
)


def load_source():
    spec = importlib.util.spec_from_file_location("f42_1_mechanics", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot_load_f42_1_source")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class F421ConformalMechanicsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_source()

    def test_c3d4_face_ownership_is_conformal(self) -> None:
        tetra = np.asarray([[1, 2, 3, 4], [1, 3, 2, 5]], dtype=np.int64)
        faces, owners, labels, metrics = self.module.c3d4_boundary_faces(tetra)
        self.assertEqual(faces.shape, (6, 3))
        self.assertEqual(len(owners), 6)
        self.assertEqual(len(labels), 6)
        self.assertEqual(metrics["boundary_faces"], 6)
        self.assertEqual(metrics["interior_faces"], 1)
        self.assertEqual(metrics["nonmanifold_faces"], 0)

    def test_c3d4_nonmanifold_face_fails_closed(self) -> None:
        tetra = np.asarray(
            [[1, 2, 3, 4], [1, 3, 2, 5], [1, 2, 3, 6]], dtype=np.int64
        )
        with self.assertRaisesRegex(self.module.F421Error, "nonmanifold"):
            self.module.c3d4_boundary_faces(tetra)

    def test_analytic_surface_groups_are_independent_of_entity_ids(self) -> None:
        chamber_center = self.module.CHAMBER_CENTER_MM
        centroids = [chamber_center + np.asarray([0.0, 0.0, 80.0])]
        normals = [np.asarray([0.0, 0.0, -1.0])]
        for axis in self.module.STUD_AXES_XY_MM:
            centroids.append(np.asarray([axis[0] + 5.05, axis[1], 0.0]))
            normals.append(np.asarray([-1.0, 0.0, 0.0]))
        chamber, studs = self.module.classify_boundary_faces(
            np.asarray(centroids), np.asarray(normals)
        )
        self.assertEqual(chamber.tolist(), [True, False, False, False, False])
        self.assertEqual([int(np.count_nonzero(item)) for item in studs], [1, 1, 1, 1])

    def test_support_singularity_exclusion_uses_fixed_physical_radius(self) -> None:
        axis = self.module.STUD_AXES_XY_MM[0]
        centroids = np.asarray(
            [[axis[0] + 14.99, axis[1], 0.0], [axis[0] + 15.01, axis[1], 0.0]]
        )
        self.assertEqual(
            self.module.support_exclusion_mask(centroids).tolist(), [False, True]
        )
        self.assertEqual(self.module.SUPPORT_SINGULARITY_EXCLUSION_RADIUS_MM, 15.0)

    def test_public_verdict_stays_closed_without_hot_material_card(self) -> None:
        case_template = {
            "status": "completed",
            "mesh": {
                "nonmanifold_faces": 0,
                "all_tetrahedra_have_positive_absolute_volume": True,
                "minimum_mean_ratio_quality": 0.05,
                "p01_mean_ratio_quality": 0.10,
                "observed_maximum_tetrahedron_volume_mm3": 10.0,
                "target_maximum_tetrahedron_volume_mm3": 10.0,
            },
            "surface_groups": {
                "chamber_pressure_faces": 100,
                "stud_support_faces_per_stud": [20, 20, 20, 20],
            },
            "results": {
                "support_excluded_von_mises_p95_mpa": 100.0,
                "maximum_displacement_mm": 0.5,
            },
        }
        cases = [
            json.loads(json.dumps(case_template)),
            json.loads(json.dumps(case_template)),
            json.loads(json.dumps(case_template)),
        ]
        cases[-2]["results"]["support_excluded_von_mises_p95_mpa"] = 101.0
        cases[-2]["results"]["maximum_displacement_mm"] = 0.51
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory) / "private.stl"
            private.write_bytes(b"private fixture")
            report = self.module.build_public_report(
                private,
                cases,
                {
                    "pressure_mpa": 10.0,
                    "ambient_temperature_c": 120.0,
                    "chamber_temperature_c": 260.0,
                    "thermal_decay_mm": 12.0,
                },
            )
        self.assertTrue(report["verdict"]["numerical_screen_passed"])
        self.assertFalse(report["gates"]["temperature_dependent_hot_material_card_available"])
        self.assertFalse(report["gates"]["manufacturing_release"])
        self.assertFalse(report["verdict"]["part_authorized_for_print"])
        self.assertFalse(report["verdict"]["part_authorized_for_engine_operation"])

    def test_published_evidence_contains_no_private_geometry(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        self.assertEqual(report["phase"], "F42.1")
        self.assertFalse(report["publication"]["contains_private_geometry"])
        self.assertFalse(report["publication"]["contains_node_coordinates"])
        self.assertFalse(report["publication"]["contains_element_connectivity"])
        self.assertFalse(report["gates"]["mesh_quality_and_size_control_adequate"])
        self.assertFalse(report["gates"]["manufacturing_release"])
        self.assertFalse(report["verdict"]["numerical_screen_passed"])
        self.assertFalse(report["verdict"]["part_authorized_for_print"])
        self.assertRegex(report["private_input"]["sha256"], r"^[0-9a-f]{64}$")
        serialized = REPORT.read_text(encoding="utf-8").lower()
        for forbidden in ("/workspace/", ".stl\"", ".msh\"", ".inp\"", ".dat\""):
            self.assertNotIn(forbidden, serialized)
        self.assertTrue(IMAGE.is_file())
        self.assertGreater(IMAGE.stat().st_size, 50_000)


if __name__ == "__main__":
    unittest.main()
