"""Known-geometry controls for the process-independent air classifier."""
import importlib.util
from pathlib import Path
import unittest

try:
    import igl
    import numpy as np
    import trimesh
except ModuleNotFoundError as exc:
    raise unittest.SkipTest(f"Native geometry dependencies unavailable: {exc.name}")

SPEC = importlib.util.spec_from_file_location(
    "print935", Path(__file__).resolve().parents[1] / "scripts/screen_935_print_geometry.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CavityScreenTests(unittest.TestCase):
    def test_batched_thickness_on_known_plate(self):
        mesh = trimesh.creation.box([10, 10, 1])
        points = np.tile([0, 0, .5], (33, 1))
        np.testing.assert_allclose(MODULE.bounded_thickness(mesh, points), 1, atol=1e-5)

    def test_solid_box_has_no_air_cavity(self):
        mesh = trimesh.creation.box([10, 10, 10])
        report, points = MODULE.cavity_screen(mesh.vertices, mesh.faces, 1.0)
        self.assertEqual(report["nominal_enclosed_air_cells"], 0)
        self.assertEqual(len(points), 0)

    def test_nested_shell_preserves_real_air_instead_of_filling_it(self):
        outer = trimesh.creation.box([10, 10, 10])
        inner = trimesh.creation.box([4, 4, 4])
        inner.invert()
        mesh = trimesh.util.concatenate([outer, inner])
        report, points = MODULE.cavity_screen(mesh.vertices, mesh.faces, 1.0)
        self.assertEqual(report["nominal_enclosed_air_cells"], 64)
        self.assertTrue((np.abs(points) < 2).all())

    def test_through_bore_is_connected_to_exterior(self):
        mesh = trimesh.creation.annulus(r_min=2, r_max=5, height=10, sections=64)
        report, _ = MODULE.cavity_screen(mesh.vertices, mesh.faces, 1.0)
        self.assertEqual(report["nominal_enclosed_air_cells"], 0)

    def test_air_boundary_and_uncertain_bridge(self):
        air = np.zeros((5, 5, 5), dtype=bool)
        air[2, 2, 2] = True
        self.assertEqual(MODULE.enclosed_air(air).sum(), 1)
        air[2, 2, :3] = True
        self.assertEqual(MODULE.enclosed_air(air).sum(), 0)

    def test_invalid_or_excessive_grid_rejected(self):
        mesh = trimesh.creation.box([10, 10, 10])
        for pitch in [0, -1, float("nan"), .001]:
            with self.subTest(pitch=pitch), self.assertRaises(ValueError):
                MODULE.cavity_screen(mesh.vertices, mesh.faces, pitch)
