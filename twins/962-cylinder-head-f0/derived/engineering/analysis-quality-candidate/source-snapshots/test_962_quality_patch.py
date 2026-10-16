"""An improving average/minimum cannot hide more inadmissible fixed facets."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1]/"twins/962-cylinder-head-f0/source/audit_quality_patch.py"
SPEC = importlib.util.spec_from_file_location("quality_patch_guard", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class QualityObjectiveGuard(unittest.TestCase):
    def test_full_surface_objective_rejects_regression_and_stagnation(self):
        before = dict(triangles=100, below_necessary_bound=10, minimum_triangle_SICN=.001)
        for count, minimum, expected in [(9, .001, True), (9, .002, True),
                                         (11, .002, False), (9, .0009, False),
                                         (10, .001, False), (10, .002, False)]:
            with self.subTest(count=count, minimum=minimum):
                after = dict(triangles=100, below_necessary_bound=count, minimum_triangle_SICN=minimum)
                self.assertIs(MODULE.require_quality_objective(before, after), expected)
        for patch in [dict(minimum_triangle_SICN=float("nan")),
                      dict(minimum_triangle_SICN=float("inf")),
                      dict(minimum_triangle_SICN=True), dict(below_necessary_bound=True),
                      dict(triangles=99)]:
            after = dict(triangles=100, below_necessary_bound=9, minimum_triangle_SICN=.001)
            after.update(patch)
            with self.subTest(invalid=patch), self.assertRaises(ValueError):
                MODULE.require_quality_objective(before, after)


if __name__ == "__main__":
    unittest.main()
