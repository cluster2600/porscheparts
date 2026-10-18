"""Changed boundary coordinates must never become source identity by index."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1]/"twins/962-cylinder-head-f0/source/prepare_finest_surface.py"
SPEC = importlib.util.spec_from_file_location("finest_surface_preparation", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FinestSurfaceAssociation(unittest.TestCase):
    def test_actual_coordinates_and_lineage_are_separate_requirements(self):
        original = [-40.25, -6.55982660191512e-7, 35.0]
        changed = [-40.25, -0.08332278732389745, 34.99810562170619]
        MODULE.boundary_coordinate(147195, changed, changed)
        with self.assertRaises(ValueError):
            MODULE.boundary_coordinate(147195, changed, original)
        with self.assertRaises(ValueError):
            MODULE.association_kind(changed, original, [], False)
        self.assertEqual(MODULE.association_kind(changed, original, [], True),
                         "preserved_helper_vertex_lineage_not_original_coordinate_identity")
        self.assertEqual(MODULE.association_kind(original, original, [147194], False),
                         "unique_exact_original_coordinate_match")
        for bad_tag in [True, 0, -1, 1.5]:
            with self.subTest(tag=bad_tag), self.assertRaises(ValueError):
                MODULE.boundary_coordinate(bad_tag, changed, changed)


if __name__ == "__main__":
    unittest.main()
