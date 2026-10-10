"""Fluid boundary gates on synthetic, non-engineering fixtures."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

from _deps import require_modules
require_modules("numpy", "trimesh", "pyvista", "scipy")
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bionic_f1_surface", ROOT / "twins/bionic-turbo-f1/prepare_surface.py")
SURFACE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SURFACE)


class FluidSurfaceTests(unittest.TestCase):
    def test_closed_internal_obstacle_allowed_without_discarding_facets(self):
        outer = trimesh.creation.box(extents=[10, 10, 10])
        inner = trimesh.creation.box()
        inner.invert()
        mesh = trimesh.util.concatenate([outer, inner])
        report, result = SURFACE.inspect_fluid(mesh.triangles)
        self.assertTrue(report["passed"])
        self.assertEqual(len(result.faces), 24)
        self.assertEqual(report["surface_components"], 2)
        self.assertFalse(report["containment_and_self_intersection_verified"])
        self.assertFalse(report["source_rotor_topology_preserved"])

    def test_two_separate_bored_obstacles_preserve_source_topology(self):
        outer = trimesh.creation.box(extents=[20, 20, 20])
        wheel = trimesh.creation.torus(major_radius=2, minor_radius=.5, major_sections=12, minor_sections=8)
        wheel.invert()
        nut = wheel.copy()
        nut.apply_translation([0, 0, 3])
        report, _ = SURFACE.inspect_fluid(trimesh.util.concatenate([outer, wheel, nut]).triangles)
        self.assertTrue(report["passed"])
        self.assertTrue(report["source_rotor_topology_preserved"])
        self.assertEqual(sorted(report["component_euler_characteristics"]), [0, 0, 2])
        report, _ = SURFACE.inspect_fluid(trimesh.util.concatenate([outer, wheel]).triangles)
        self.assertTrue(report["passed"])
        self.assertFalse(report["source_rotor_topology_preserved"])

    def test_open_or_two_outer_volumes_rejected(self):
        box = trimesh.creation.box()
        report, _ = SURFACE.inspect_fluid(box.triangles[:-1])
        self.assertFalse(report["passed"])
        moved = box.copy()
        moved.apply_translation([3, 0, 0])
        report, _ = SURFACE.inspect_fluid(trimesh.util.concatenate([box, moved]).triangles)
        self.assertFalse(report["passed"])

    def fixture(self):
        triangles = np.array([
            [[0, 0, 44], [1, 0, 44], [0, 1, 44]],
            [[49, 80, 0], [50, 80, 0], [49, 80, 1]],
            [[10, 0, 20], [10, 1, 20], [10, 0, 21]],
            [[30, 0, 20], [30, 1, 20], [30, 0, 21]],
        ], dtype=float)
        return trimesh.Trimesh(vertices=triangles.reshape(-1, 3), faces=np.arange(12).reshape(-1, 3), process=False)

    def test_labels_and_si_export_preserve_each_facet(self):
        mesh = self.fixture()
        labels, report = SURFACE.label_faces(mesh, np.array([90, 90, .1, 10]), np.array([5, 5, 5, .1]))
        self.assertTrue(report["passed"])
        self.assertEqual(labels.tolist(), list(SURFACE.REGIONS))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fluid.stl"
            SURFACE.write_surface(path, mesh, labels)
            content = path.read_text()
            self.assertEqual(content.count("facet normal"), 4)
            self.assertIn("vertex 0 0 0.044", content)
            with self.assertRaises(FileExistsError):
                SURFACE.write_surface(path, mesh, labels)

    def test_unexplained_wall_and_missing_patch_fail_closed(self):
        mesh = self.fixture()
        _, report = SURFACE.label_faces(mesh, np.array([90, 90, .1, 10]), np.array([5, 5, 5, 10]))
        self.assertFalse(report["passed"])
        self.assertEqual(report["unexplained_stator_faces"], 1)
        _, report = SURFACE.label_faces(mesh, np.full(4, 90), np.full(4, .1))
        self.assertIn("all_four_boundary_regions_required", report["errors"])

    def test_fixed_seal_is_not_rotor_and_nearby_shaft_remains_rotating(self):
        extra = np.array([
            [[4.6, 0, -3.75], [4.7, 0, -3.75], [4.6, .1, -3.75]],
            [[4, 0, -3.2], [4, 0, -3.1], [4, .1, -3.1]],
        ])
        triangles = np.concatenate([self.fixture().triangles, extra])
        mesh = trimesh.Trimesh(vertices=triangles.reshape(-1, 3), faces=np.arange(18).reshape(-1, 3), process=False)
        labels, report = SURFACE.label_faces(mesh, np.array([90, 90, .1, 10, .645, .01]),
                                            np.array([5, 5, 5, .1, 28, 28]))
        self.assertTrue(report["passed"])
        self.assertEqual(labels[-2:].tolist(), ["stator", "rotor"])
        self.assertEqual(report["fixed_seal_faces_nearer_rotor_than_housing"], 1)

    def test_near_coplanar_port_rims_are_walls_not_planar_ports(self):
        extra = np.array([
            [[21.6, 0, 44], [21.6, .1, 43.9995], [21.5, 0, 44]],
            [[62, 80, 0], [62, 79.9995, .1], [62.1, 80, 0]],
        ])
        triangles = np.concatenate([self.fixture().triangles, extra])
        mesh = trimesh.Trimesh(vertices=triangles.reshape(-1, 3), faces=np.arange(18).reshape(-1, 3), process=False)
        labels, report = SURFACE.label_faces(mesh, np.array([90, 90, .1, 10, 90, 90]),
                                            np.array([5, 5, 5, .1, .4, 90]))
        self.assertTrue(report["passed"])
        self.assertEqual(labels[-2:].tolist(), ["stator", "stator"])

    def test_changed_mesh_or_facet_declaration_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            path = directory / "fluid.stl"
            trimesh.creation.box().export(path)
            record = {"file": path.name, "sha256": SURFACE.sha(path), "triangles": 12}
            self.assertEqual(len(SURFACE.load_declared(directory, {"files": [record]}, path.name).faces), 12)
            for bad in (record | {"sha256": "0" * 64}, record | {"triangles": 11}):
                with self.assertRaises(ValueError):
                    SURFACE.load_declared(directory, {"files": [bad]}, path.name)

    def test_trim_collar_requires_cap_contact_local_extent_and_distance(self):
        triangle = np.array([[21.7, 0, 43.8], [21.25, 0, 44], [21.25, .5, 44]])
        variants = [triangle, triangle + [0, 0, -.1], triangle + [0, 0, .1],
                    triangle * [2, 1, 1], triangle.copy()]
        variants[-1][0, 2] = 43
        for i, facet in enumerate(variants):
            triangles = np.concatenate([self.fixture().triangles, [facet]])
            mesh = trimesh.Trimesh(vertices=triangles.reshape(-1, 3), faces=np.arange(15).reshape(-1, 3), process=False)
            _, report = SURFACE.label_faces(mesh, np.array([90, 90, .1, 10, 90]), np.array([5, 5, 5, .1, .67]))
            self.assertEqual(report['passed'], i == 0)
            self.assertEqual(report['inlet_trim_idealization']['faces_exceeding_wall_tolerance'], int(i == 0))
        triangles = np.concatenate([self.fixture().triangles, [triangle]])
        mesh = trimesh.Trimesh(vertices=triangles.reshape(-1, 3), faces=np.arange(15).reshape(-1, 3), process=False)
        _, report = SURFACE.label_faces(mesh, np.array([90, 90, .1, 10, 90]), np.array([5, 5, 5, .1, .76]))
        self.assertFalse(report['passed'])


if __name__ == "__main__":
    unittest.main()
