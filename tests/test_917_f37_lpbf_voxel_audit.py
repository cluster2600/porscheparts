"""Régression du contrôle grossier de poudre piégée LPBF F37."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source/analyze_f36_lpbf_printability.py"
COMPILER = ROOT / "twins/reference-917-engine/source/compile_f37_lpbf_manufacturing_plan.py"

try:
    import numpy as np
    import trimesh
except ImportError:  # L'image mesh-cfd exécute les cas géométriques complets.
    np = None
    trimesh = None


class LpbfVoxelAuditSourceTests(unittest.TestCase):
    def test_fill_holes_is_not_used_before_trapped_void_classification(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn('.fill(method="holes")', source)
        self.assertNotIn("mesh.contains(", source)
        self.assertNotIn("trimesh.proximity.thickness", source)
        self.assertIn("winding_number_at_point", source)
        self.assertIn("WINDING_CHUNK_TRIANGLES", source)
        self.assertIn("THICKNESS_MAX_INDEX_REFERENCES", source)
        self.assertIn("surface_voxel_components_plus_chunked_winding_number", source)


class LpbfManufacturingCompilerFailClosedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("f37_lpbf_compiler", COMPILER)
        assert spec is not None and spec.loader is not None
        cls.compiler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.compiler)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        directory = Path(self.temporary.name)
        self.contract_path = directory / "contract.json"
        self.cad_path = directory / "cad.json"
        release_gates = {
            "absolute_scale_confirmed": False,
            "metal_print_authorized": False,
            "engine_start_authorized": False,
        }
        self.contract = {"phase": "F37", "release_gates": release_gates}
        self.contract_path.write_text(json.dumps(self.contract), encoding="utf-8")
        self.cad = {
            "phase": "F37",
            "inputs": {"contract_sha256": self.compiler.sha256(self.contract_path)},
            "release_gates": release_gates,
        }
        self.cad_path.write_text(json.dumps(self.cad), encoding="utf-8")
        self.args = SimpleNamespace(
            f37_contract=self.contract_path,
            f37_cad_report=self.cad_path,
        )
        self.printability = {
            "phase": "F37",
            "status": "lpbf_geometric_virtual_build_screen_complete_release_blocked",
            "classification": "virtual_printability_screen_not_calibrated_process_simulation",
            "inputs": {
                "head_sha256": "head-sha",
                "geometry_report_sha256": "geometry-sha",
                "scale_confirmed": False,
            },
            "orientations": [
                {"id": "best", "score": 10.0, "fits_250x250x325_mm": True},
                {"id": "worse", "score": 20.0, "fits_250x250x325_mm": True},
            ],
            "selected_orientation": "best",
            "selected": {"id": "best", "score": 10.0, "fits_250x250x325_mm": True},
            "voxel_audit": {
                "method": "surface_voxel_components_plus_chunked_winding_number_without_fill_holes",
                "pitch_mm": 2.0,
                "trapped_void_voxels": 3,
                "trapped_void_volume_mm3": 24.0,
                "unsupported_voxels_above_plate": 1,
                "occupied_voxels_above_plate": 100,
                "unsupported_fraction": 0.01,
            },
            "head_mass_kg": 2.8,
            "assumed_density_kg_m3": 2670.0,
            "thickness_audit": {
                "method": "sampled_inward_normal_ray_uniform_grid_exact_triangle_intersection",
                "requested_sample_count": 100,
                "sample_count": 100,
                "unresolved_sample_count": 0,
                "minimum_resolved_fraction": 0.95,
                "spatial_index_triangle_references": 200,
                "spatial_index_reference_limit": 1000,
                "p01_mm_if_scale_is_mm": 1.6,
            },
            "gates": {
                "watertight_single_body": True,
                "fits_build_envelope": True,
                "sampled_p01_thickness_at_least_1_5_mm": True,
                "coarse_trapped_void_volume_zero": False,
                "coarse_layer_support_fraction_below_0_5_percent": False,
                "absolute_scale_confirmed": False,
                "metal_print_authorized": False,
                "engine_start_authorized": False,
            },
        }
        self.head_mesh = {
            "phase": "F37",
            "status": "local_mesh_boolean_proof_complete_physical_and_manufacturing_release_blocked",
            "inputs": {
                "contract_sha256": self.compiler.sha256(self.contract_path),
                "cad_report_sha256": self.compiler.sha256(self.cad_path),
                "geometry_report_sha256": "geometry-sha",
                "scale_confirmed": False,
            },
            "local_only_artifacts": {
                "917-head-f37-printable-proof.local.stl": {"sha256": "head-sha"}
            },
            "result": {"watertight": True, "body_count": 1},
        }
        self.locked = {
            "phase": "F36",
            "classification": "linear_elastic_uniform_cooling_locked_plate_upper_bound_not_calibrated_lpbf",
        }

    def tearDown(self):
        self.temporary.cleanup()

    def validate(self):
        self.compiler.validate_inputs(
            self.printability,
            self.head_mesh,
            self.locked,
            self.contract,
            self.cad,
            self.args,
        )

    def test_consistent_inputs_are_accepted(self):
        self.validate()

    def test_f36_locked_plate_cannot_be_relabelled_f37(self):
        self.locked["phase"] = "F37"
        with self.assertRaisesRegex(ValueError, "proxy F36"):
            self.validate()

    def test_release_authorization_cannot_enter_the_virtual_compiler(self):
        self.printability["gates"]["metal_print_authorized"] = True
        with self.assertRaisesRegex(ValueError, "metal_print_authorized=false"):
            self.validate()

    def test_old_voxel_method_is_rejected(self):
        self.printability["voxel_audit"]["method"] = "surface_fill_holes"
        with self.assertRaisesRegex(ValueError, "méthode d'audit voxel"):
            self.validate()

    def test_non_minimum_orientation_is_rejected(self):
        self.printability["selected_orientation"] = "worse"
        self.printability["selected"] = {
            "id": "worse",
            "score": 20.0,
            "fits_250x250x325_mm": True,
        }
        with self.assertRaisesRegex(ValueError, "minimum admissible"):
            self.validate()

    def test_inconsistent_voxel_volume_is_rejected(self):
        self.printability["voxel_audit"]["trapped_void_volume_mm3"] = 25.0
        with self.assertRaisesRegex(ValueError, "volume de vide voxel"):
            self.validate()

    def test_tampered_selected_metrics_are_rejected(self):
        self.printability["selected"]["score"] = 10.0
        self.printability["selected"]["extents_mm_if_scale_is_mm"] = [1.0, 2.0, 3.0]
        with self.assertRaisesRegex(ValueError, "métriques de l'orientation"):
            self.validate()

    def test_tampered_derived_gate_is_rejected(self):
        self.printability["gates"]["coarse_trapped_void_volume_zero"] = True
        with self.assertRaisesRegex(ValueError, "porte LPBF dérivée"):
            self.validate()

    def test_old_unbounded_thickness_method_is_rejected(self):
        self.printability["thickness_audit"]["method"] = "bidirectional_surface_ray_sample"
        with self.assertRaisesRegex(ValueError, "méthode de mesure d'épaisseur"):
            self.validate()

    def test_insufficient_thickness_ray_coverage_is_rejected(self):
        self.printability["thickness_audit"]["sample_count"] = 94
        self.printability["thickness_audit"]["unresolved_sample_count"] = 6
        with self.assertRaisesRegex(ValueError, "couverture ou borne mémoire"):
            self.validate()


@unittest.skipUnless(trimesh is not None and np is not None, "trimesh absent hors image mesh-cfd")
class LpbfVoxelAuditGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("f37_lpbf", SOURCE)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_closed_internal_cavity_is_detected(self):
        outer = trimesh.creation.box(extents=[30.0, 30.0, 30.0])
        inner = trimesh.creation.box(extents=[10.0, 10.0, 10.0])
        inner.invert()
        hollow = trimesh.util.concatenate((outer, inner))
        self.assertTrue(hollow.is_watertight)
        result = self.module.voxel_audit(hollow)
        self.assertGreater(result["trapped_void_voxels"], 0)
        self.assertIn(
            "trapped_void",
            {item["classification"] for item in result["enclosed_component_classification"]},
        )

    def test_open_through_hole_is_not_classified_as_trapped(self):
        annulus = trimesh.creation.annulus(r_min=5.0, r_max=15.0, height=20.0, sections=64)
        self.assertTrue(annulus.is_watertight)
        result = self.module.voxel_audit(annulus)
        self.assertEqual(result["trapped_void_voxels"], 0)

    def test_uniform_grid_ray_thickness_matches_box_faces(self):
        box = trimesh.creation.box(extents=[10.0, 20.0, 30.0])
        result = self.module.thickness_audit(box, sample_count=240)
        self.assertEqual(result["unresolved_sample_count"], 0)
        self.assertAlmostEqual(result["minimum_mm_if_scale_is_mm"], 10.0, places=5)
        self.assertAlmostEqual(result["p01_mm_if_scale_is_mm"], 10.0, places=5)
        self.assertLessEqual(
            result["spatial_index_triangle_references"],
            result["spatial_index_reference_limit"],
        )

    def test_spatial_index_reference_cap_fails_closed(self):
        box = trimesh.creation.box(extents=[10.0, 20.0, 30.0])
        original = self.module.THICKNESS_MAX_INDEX_REFERENCES
        self.module.THICKNESS_MAX_INDEX_REFERENCES = 1
        try:
            with self.assertRaisesRegex(RuntimeError, "index d'épaisseur trop grand"):
                self.module.build_triangle_grid_index(box)
        finally:
            self.module.THICKNESS_MAX_INDEX_REFERENCES = original


if __name__ == "__main__":
    unittest.main()
