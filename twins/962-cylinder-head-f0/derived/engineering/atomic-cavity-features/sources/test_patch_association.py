"""Pure owner-association refusal fixtures; no head read or VTK import."""
import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).with_name('analyze_patches.py')
spec = importlib.util.spec_from_file_location('held_atomic_patch_analysis', source)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class OwnershipTests(unittest.TestCase):
    def test_shared_boundary_vertex_does_not_make_a_unique_face_ambiguous(self):
        owners = {0: {0}, 1: {0}, 2: {0, 1}, 3: {1}, 4: {1}}
        self.assertEqual(module.unique_owner([0, 1, 2], owners, 10), 0)
        self.assertEqual(module.unique_owner([2, 3, 4], owners, 11), 1)

    def test_cross_patch_or_unknown_vertex_is_refused(self):
        owners = {0: {0}, 1: {0}, 2: {0, 1}, 3: {1}, 4: {1}}
        for face in ([0, 2, 3], [0, 1, 99]):
            with self.subTest(face=face), self.assertRaises(ValueError):
                module.unique_owner(face, owners, 12)

    def test_multiple_immutable_group_owners_are_refused(self):
        owners = {0: {0, 1}, 1: {0, 1}, 2: {0, 1}}
        with self.assertRaises(ValueError):
            module.unique_owner([0, 1, 2], owners, 13)


if __name__ == '__main__':
    unittest.main()
