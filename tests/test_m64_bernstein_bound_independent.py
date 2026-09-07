"""Independent algebraic checks; evaluations at sample points are not proofs."""
import contextlib
from fractions import Fraction
import hashlib
import importlib.util
import io
import json
from math import comb, inf, nextafter
from pathlib import Path
import tempfile
import unittest
from unittest import mock


PATH = Path(__file__).resolve().parents[1] / "twins/m64-cylinder-head/bound_bernstein_displacement.py"
SPEC = importlib.util.spec_from_file_location("bernstein_bound_independent", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def power_coefficients(grid):
    """Expand each Bernstein basis polynomial combinatorially, not recursively."""
    m, n = len(grid) - 1, len(grid[0]) - 1
    result = {(a, b): Fraction(0) for a in range(m + 1) for b in range(n + 1)}
    for i, row in enumerate(grid):
        for j, value in enumerate(row):
            for a in range(i, m + 1):
                for b in range(j, n + 1):
                    result[a, b] += (
                        value * comb(m, i) * comb(m - i, a - i)
                        * comb(n, j) * comb(n - j, b - j)
                        * (-1) ** (a - i + b - j)
                    )
    return result


def restrict_power(coefficients, u0, v0, scale):
    """Coefficients of p(u0 + scale*u, v0 + scale*v) by binomial expansion."""
    result = dict.fromkeys(coefficients, Fraction(0))
    for (a, b), value in coefficients.items():
        for r in range(a + 1):
            for s in range(b + 1):
                result[r, s] += (
                    value * comb(a, r) * comb(b, s)
                    * u0 ** (a - r) * v0 ** (b - s) * scale ** (r + s)
                )
    return result


class BernsteinBoundIndependentTests(unittest.TestCase):
    def test_every_subpatch_has_exact_polynomial_identity_on_its_quadrant(self):
        # Non-square, non-symmetric, signed data catches swapped axes/order.
        grids = (
            [[Fraction(7 * i - 3 * j, 11 + i + j) for j in range(5)] for i in range(4)],
            [[Fraction(-3, 7), Fraction(5, 11), Fraction(2, 13)]],
            [[Fraction(-3, 7)], [Fraction(5, 11)], [Fraction(2, 13)]],
            [[Fraction(13, 17)]],
        )
        half = Fraction(1, 2)
        origins = ((0, 0), (0, half), (half, 0), (half, half))
        for grid in grids:
            with self.subTest(shape=(len(grid), len(grid[0]))):
                parent = power_coefficients(grid)
                children = MODULE.split_square(grid)
                self.assertEqual(len(children), 4)
                for child, (u0, v0) in zip(children, origins):
                    self.assertEqual(power_coefficients(child), restrict_power(parent, u0, v0, half))
                    for grandchild, (du, dv) in zip(MODULE.split_square(child), origins):
                        self.assertEqual(
                            power_coefficients(grandchild),
                            restrict_power(parent, u0 + half * du, v0 + half * dv, half * half),
                        )

    def test_partial_quadrant_coverage_never_certifies_the_square(self):
        grid = [[0, 0, 0], [0, 4, 0], [0, 0, 0]]
        limited = MODULE.prove_bound(grid, max_boxes=4)
        self.assertFalse(limited["proven_on_full_square"])
        self.assertEqual(limited["status"], "inconclusive_resource_limit")
        self.assertEqual(limited["visited_boxes"], 4)
        self.assertEqual(limited["accepted_boxes"], 3)
        self.assertEqual(limited["unresolved_boxes"], 1)
        self.assertNotIn("max_absolute_value_bound_exact", limited)
        complete = MODULE.prove_bound(grid, max_boxes=5)
        self.assertTrue(complete["proven_on_full_square"])
        self.assertEqual(complete["accepted_boxes"], 4)

    def test_nondyadic_tangent_maximum_remains_inconclusive_at_finite_depth(self):
        # p(u)=8+6u-9u^2 <= 9; equality only at u=1/3, never a dyadic split.
        # Sampling could incorrectly declare success; Bernstein hull still straddles 9.
        result = MODULE.prove_bound([[8], [11], [5]], limit=9, max_depth=4)
        self.assertEqual(result["status"], "inconclusive_depth_limit")
        self.assertFalse(result["proven_on_full_square"])
        self.assertGreater(result["unresolved_boxes"], 0)
        self.assertNotIn("max_absolute_value_bound_exact", result)

    def test_outward_display_never_undercuts_exact_rational_bound(self):
        result = MODULE.prove_bound([[0.1], [1.3], [0.2]])
        self.assertTrue(result["proven_on_full_square"])
        exact = Fraction(result["max_absolute_value_bound_exact"])
        displayed = result["max_absolute_value_bound_rounded_outward"]
        self.assertGreaterEqual(Fraction(displayed), exact)
        self.assertLess(Fraction(nextafter(displayed, -inf)), exact)

    def test_degree_and_resource_boundaries(self):
        self.assertTrue(MODULE.prove_bound([[0] * 26 for _ in range(26)], max_depth=0, max_boxes=1)["proven_on_full_square"])
        for grid in ([[0] * 27], [[0] for _ in range(27)]):
            with self.subTest(grid=grid), self.assertRaises(ValueError):
                MODULE.prove_bound(grid)

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "NumPy required for NPZ provenance regression")
    def test_cli_hash_identifies_coefficients_actually_used_despite_file_replacement(self):
        import numpy as np

        with tempfile.TemporaryDirectory(prefix="bernstein-provenance-") as directory:
            source = Path(directory) / "coefficients.npz"
            output = Path(directory) / "proof.json"
            np.savez(source, amplitude=np.array([[0.25]]))
            original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            actual_prove_bound = MODULE.prove_bound

            def replace_after_proof(*args, **kwargs):
                result = actual_prove_bound(*args, **kwargs)
                replacement = Path(directory) / "replacement.npz"
                np.savez(replacement, amplitude=np.array([[2.0]]))
                replacement.replace(source)
                return result

            with mock.patch.object(MODULE, "prove_bound", side_effect=replace_after_proof), \
                    mock.patch("sys.argv", [str(PATH), "--coefficients", str(source), "--output", str(output)]), \
                    contextlib.redirect_stdout(io.StringIO()):
                MODULE.main()
            report = json.loads(output.read_text())
            self.assertTrue(report["proven_on_full_square"])
            self.assertEqual(report["input_sha256"], original_hash)
            self.assertNotEqual(report["input_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
