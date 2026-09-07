import importlib.util
from fractions import Fraction
from pathlib import Path
import unittest


PATH = Path(__file__).resolve().parents[1] / "twins/m64-cylinder-head/bound_bernstein_displacement.py"
SPEC = importlib.util.spec_from_file_location("bernstein_bound", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BernsteinBoundTests(unittest.TestCase):
    def test_float_interpretation_is_exact_not_decimal_approximation(self):
        value = MODULE.coefficient_grid([[0.1]])[0][0]
        self.assertEqual(value, Fraction.from_float(0.1))
        self.assertNotEqual(value, Fraction(1, 10))

    def test_constant_in_range(self):
        result = MODULE.prove_bound([[0.85]])
        self.assertTrue(result["proven_on_full_square"])
        self.assertEqual(result["visited_boxes"], 1)
        self.assertFalse(result["geometry_or_manufacturing_authorized"])

    def test_hull_above_limit_does_not_imply_polynomial_failure(self):
        # 4 u (1-u) reaches exactly one; the middle coefficient is two.
        result = MODULE.prove_bound([[0.0], [2.0], [0.0]])
        self.assertTrue(result["proven_on_full_square"])
        self.assertGreater(result["visited_boxes"], 1)
        self.assertEqual(result["max_absolute_value_bound_exact"], "1")

    def test_interior_peak_exceeds_limit_even_when_corners_are_zero(self):
        result = MODULE.prove_bound([[0.0], [3.0], [0.0]])
        self.assertEqual(result["status"], "outside_bound_on_full_square")
        self.assertFalse(result["proven_on_full_square"])

    def test_tensor_product_peak_and_axis_symmetry(self):
        grid = [[0.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 0.0]]
        self.assertTrue(MODULE.prove_bound(grid)["proven_on_full_square"])
        transposed = list(map(list, zip(*grid)))
        self.assertEqual(MODULE.prove_bound(grid), MODULE.prove_bound(transposed))

    def test_negative_displacement_is_bounded_in_absolute_value(self):
        self.assertTrue(MODULE.prove_bound([[0.0], [-2.0], [0.0]])["proven_on_full_square"])
        self.assertFalse(MODULE.prove_bound([[-1.01]])["proven_on_full_square"])

    def test_depth_or_work_exhaustion_never_passes(self):
        grid = [[0.0], [2.0], [0.0]]
        self.assertEqual(MODULE.prove_bound(grid, max_depth=0)["status"], "inconclusive_depth_limit")
        self.assertEqual(MODULE.prove_bound(grid, max_boxes=1)["status"], "inconclusive_resource_limit")

    def test_split_preserves_endpoints_and_exact_midpoint(self):
        left, right = MODULE.split_curve((Fraction(1), Fraction(2), Fraction(4)))
        self.assertEqual(left[0], 1)
        self.assertEqual(right[-1], 4)
        self.assertEqual(left[-1], Fraction(9, 4))
        self.assertEqual(left[-1], right[0])

    def test_invalid_inputs_fail_closed(self):
        for grid in ([], [[]], [[0], [0, 1]], [[True]], [[float("nan")]], [[float("inf")]], [["1"]]):
            with self.subTest(grid=grid), self.assertRaises(ValueError):
                MODULE.prove_bound(grid)
        for kwargs in ({"limit": 0}, {"limit": float("nan")}, {"max_depth": True},
                       {"max_depth": -1}, {"max_boxes": 0}, {"max_boxes": 1.5}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                MODULE.prove_bound([[0]], **kwargs)


if __name__ == "__main__":
    unittest.main()
