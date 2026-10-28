"""Stdlib-only mesh extraction checks; never import OCP, NumPy or a CAD runtime."""
import importlib.util
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import json

spec = importlib.util.spec_from_file_location('private_reference_preparation', Path(__file__).with_name('run.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

V = [(0., 0., 0.), (1., 0., 0.), (0., 1., 0.), (0., 0., 1.)]
F = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]


class Checks(unittest.TestCase):
    def test_exact_tetrahedron(self):
        result = module.validate_surface(V, F)
        self.assertEqual(result['exact_signed_volume_mm3'], '1/6')
        self.assertEqual(result['face_connected_components'], 1)
        self.assertFalse(result['self_intersections_checked'])

    def test_complete_indexed_face_and_reverse(self):
        vertices, faces, lookup = [], [], {}
        module.add_face(V[:3], [(1, 2, 3)], True, vertices, faces, lookup)
        self.assertEqual(vertices, V[:3])
        self.assertEqual(faces, [(0, 2, 1)])
        module.add_face(V[:3], [(1, 2, 3)], False, vertices, faces, lookup)
        self.assertEqual(len(vertices), 3)

    def test_binary64_bits_not_STL32(self):
        x = 1. + 2.**-40
        self.assertNotEqual(x, struct.unpack('<f', struct.pack('<f', x))[0])
        vertices, faces = [], []
        module.add_face([(x, -0., 0.), (0., 1., 0.), (0., 0., 1.)],
                        [(1, 2, 3)], False, vertices, faces, {})
        self.assertEqual(struct.pack('<ddd', *vertices[0]), struct.pack('<ddd', x, -0., 0.))

    def test_one_ULP_is_not_merged(self):
        vertices, faces, lookup = [], [], {}
        module.add_face(V[:3], [(1, 2, 3)], False, vertices, faces, lookup)
        module.add_face([(0., 0., 0.), (math.nextafter(1., 2.), 0., 0.), (0., 1., 0.)],
                        [(1, 2, 3)], False, vertices, faces, lookup)
        self.assertEqual(len(vertices), 4)

    def test_no_missing_face(self):
        with self.assertRaisesRegex(ValueError, 'closed/manifold/oriented'):
            module.validate_surface(V, F[:-1])

    def test_no_orientation_flip(self):
        with self.assertRaisesRegex(ValueError, 'closed/manifold/oriented'):
            module.validate_surface(V, [F[0][::-1]] + F[1:])
        with self.assertRaisesRegex(ValueError, 'positive-volume'):
            module.validate_surface(V, [row[::-1] for row in F])

    def test_no_nonmanifold_or_zero_area(self):
        with self.assertRaises(ValueError):
            module.validate_surface(V, F + [F[0]])
        with self.assertRaisesRegex(ValueError, 'zero-area'):
            module.validate_surface([(0., 0., 0.), (1., 0., 0.), (2., 0., 0.)], [(0, 1, 2)])

    def test_no_empty_or_incomplete_face(self):
        for nodes, faces in [([], []), (V, []), (V, [(0, 1, 2)]), (V, [(1, 2, 5)])]:
            with self.assertRaises(ValueError):
                module.add_face(nodes, faces, False, [], [], {})

    def test_no_nonfinite_node(self):
        for value in [float('inf'), float('nan')]:
            with self.assertRaisesRegex(ValueError, 'Finite binary64'):
                module.add_face([(value, 0., 0.)] + V[1:3], [(1, 2, 3)], False, [], [], {})

    def test_no_second_disconnected_component(self):
        vertices = V + [tuple(c + 3. for c in p) for p in V]
        with self.assertRaisesRegex(ValueError, 'One complete'):
            module.validate_surface(vertices, F + [tuple(i + 4 for i in row) for row in F])

    def test_no_native_import(self):
        self.assertNotIn('OCP', sys.modules)
        self.assertNotIn('numpy', sys.modules)

    def test_exact_plan_resources_and_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            criterion, setting = root / 'criterion.json', root / 'source.py'
            criterion.write_text('{"maximum_mesh_interface_deviation_mm":0.01}')
            setting.write_text('export_stl(body, path, tolerance=.06, angular_tolerance=.10)\n')
            plan = dict(files_sha256={str(criterion): module.sha(criterion), str(setting): module.sha(setting)},
                        parameters=dict(linear_deflection_mm=.01, is_relative=False,
                                        angular_deflection_rad=.10, in_parallel=False),
                        criterion=dict(path=str(criterion), field='maximum_mesh_interface_deviation_mm'),
                        angular_setting_source=str(setting),
                        resources=dict(global_wall_seconds=300, child_wall_seconds_max=260,
                                       child_CPU_seconds=260, cleanup_reserve_seconds=30, threads=1, nice=10))
            module.verify(plan)
            plan['resources']['global_wall_seconds'] = 301
            with self.assertRaisesRegex(ValueError, 'resources'):
                module.verify(plan)
            plan['resources']['global_wall_seconds'] = 300
            criterion.write_text('{"maximum_mesh_interface_deviation_mm":0.02}')
            with self.assertRaisesRegex(ValueError, 'changed'):
                module.verify(plan)

    def test_fresh_output_refuses_dangling_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / 'output'
            output.symlink_to(root / 'missing')
            plan = root / 'plan.json'
            plan.write_text(json.dumps({'output': str(output)}))
            with self.assertRaisesRegex(ValueError, 'Fresh'):
                module.run(plan)


if __name__ == '__main__':
    unittest.main()
