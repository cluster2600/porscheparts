"""Controls for source-preserving underbody inspection, not fitted CAD."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "twins/964-chassis/monocoque/scan-coverage-20261029"


def load(name):
    spec = importlib.util.spec_from_file_location("coverage_" + name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load("build_review")
verify = load("verify_review")


class ScanCoverageControls(unittest.TestCase):
    def setUp(self):
        self.vertices = np.array([[-1, 0, 0], [1, 0, 0], [1, 2, 0], [-1, 2, 0],
                                  [5, 0, 0], [6, 0, 0], [5, 1, 0]], dtype=np.float32)
        self.faces = np.array([[0, 1, 2], [0, 2, 3], [4, 5, 6]], dtype=np.int32)
        self.config = {"regions": [{"name": "Search", "bounds": [-2, 2, -3, 3, -1, 1], "colour": [0.2, 0.4, 0.6]}],
                       "unobserved_requirements": ["InteriorTunnel"]}

    def test_crossing_crop_keeps_original_triangle_in_context(self):
        config = [{"name": "Partial", "bounds": [0, 2, -3, 3, -1, 1]}]
        groups = build.partition(self.vertices, self.faces, config)
        self.assertEqual(len(groups["Partial"]), 0)
        np.testing.assert_array_equal(groups["Context"], [0, 1, 2])

    def test_overlapping_windows_do_not_duplicate_source_faces(self):
        regions = self.config["regions"] + [{"name": "Second", "bounds": [-2, 2, -3, 3, -1, 1]}]
        groups = build.partition(self.vertices, self.faces, regions)
        np.testing.assert_array_equal(groups["Search"], [0, 1])
        self.assertEqual(len(groups["Second"]), 0)
        np.testing.assert_array_equal(groups["Context"], [2])

    def test_plane_intersections_match_hand_computed_segment(self):
        ids, ends, touching = build.plane_segments(self.vertices, self.faces[:1], 0, 0, [-10, 10, -10, 10, -1, 1])
        np.testing.assert_array_equal(ids, [0])
        np.testing.assert_array_equal(ends, [[[0, 0, 0], [0, 1, 0]]])
        self.assertEqual(touching, 0)

    def test_plane_touch_and_coplanar_faces_are_counted_not_joined(self):
        for axis, position, expected in ((0, 1, 2), (2, 0, 3)):
            ids, ends, touching = build.plane_segments(self.vertices, self.faces, axis, position, [-10, 10, -10, 10, -1, 1])
            self.assertEqual(touching, expected)
            self.assertEqual(len(ids), 0)
            self.assertEqual(ends.shape, (0, 2, 3))

    def test_section_verifier_rejects_an_invented_endpoint(self):
        config = {"section_scope_bounds": [-10, 10, -10, 10, -1, 1],
                  "sections": [{"name": "cut", "axis": 0, "position_mm": 0}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            endpoints = np.array([[[0, 0, 0], [0, 1, 0]], [[0, 1, 0], [0, 2, 0]]], dtype=float)
            np.savez(path / "cut.npz", source_face_ids=np.array([0, 1]), endpoints=endpoints)
            self.assertEqual(verify.verify_sections(path, self.vertices, self.faces, config)["cut"]["source_intersections_verified"], 2)
            endpoints[0, 1, 1] += 0.1
            np.savez(path / "cut.npz", source_face_ids=np.array([0, 1]), endpoints=endpoints)
            with self.assertRaisesRegex(ValueError, "source triangle edges"):
                verify.verify_sections(path, self.vertices, self.faces, config)

    def test_public_or_existing_output_rejected_before_input_read(self):
        with self.assertRaisesRegex(ValueError, "private directory"):
            build.build("missing", "missing", "missing", HERE / "must-not-create")
        (ROOT / "work").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as directory:
            with self.assertRaisesRegex(ValueError, "private directory"):
                build.build("missing", "missing", "missing", directory)


@unittest.skipUnless(importlib.util.find_spec("pxr"), "Native OpenUSD runtime required")
class NativeScanCoverageControls(unittest.TestCase):
    setUp = ScanCoverageControls.setUp

    def make_stage(self, folder):
        target = Path(folder) / "test.usdc"
        build.write_stage(self.vertices, self.faces,
                          build.partition(self.vertices, self.faces, self.config["regions"]), self.config, target)
        return target

    def test_exact_partition_survives_reopened_usd(self):
        with tempfile.TemporaryDirectory() as folder:
            target = self.make_stage(folder)
            self.assertEqual(verify.verify_stage(target, self.vertices, self.faces, self.config), {"Search": 2, "Context": 1})

    def test_shifted_surface_rejected_even_with_same_topology(self):
        from pxr import Usd, UsdGeom
        with tempfile.TemporaryDirectory() as folder:
            target = self.make_stage(folder)
            stage = Usd.Stage.Open(str(target))
            mesh = UsdGeom.Mesh(stage.GetPrimAtPath("/ScanReview/Observed/Search"))
            points = mesh.GetPointsAttr().Get()
            points[0] = points[0] + (0, 0, 1)
            mesh.GetPointsAttr().Set(points)
            stage.GetRootLayer().Save()
            with self.assertRaisesRegex(ValueError, "coordinates changed"):
                verify.verify_stage(target, self.vertices, self.faces, self.config)

    def test_reversed_triangle_rejected(self):
        from pxr import Usd, UsdGeom
        with tempfile.TemporaryDirectory() as folder:
            target = self.make_stage(folder)
            stage = Usd.Stage.Open(str(target))
            mesh = UsdGeom.Mesh(stage.GetPrimAtPath("/ScanReview/Observed/Search"))
            indices = mesh.GetFaceVertexIndicesAttr().Get()
            indices[0], indices[1] = indices[1], indices[0]
            mesh.GetFaceVertexIndicesAttr().Set(indices)
            stage.GetRootLayer().Save()
            with self.assertRaisesRegex(ValueError, "oriented triangles changed"):
                verify.verify_stage(target, self.vertices, self.faces, self.config)

    def test_fabricated_interior_claim_rejected(self):
        from pxr import Usd
        with tempfile.TemporaryDirectory() as folder:
            target = self.make_stage(folder)
            stage = Usd.Stage.Open(str(target))
            stage.GetDefaultPrim().GetAttribute("scan:interiorSurfacesReconstructed").Set(True)
            stage.GetRootLayer().Save()
            with self.assertRaisesRegex(ValueError, "qualification claim"):
                verify.verify_stage(target, self.vertices, self.faces, self.config)


if __name__ == "__main__":
    unittest.main()
