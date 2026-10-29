"""Compare recomputed JSON results with frozen cross-platform float receipts."""

import math


def assert_numeric_receipt(test, actual, expected):
    test.assertIs(type(actual), type(expected))
    if isinstance(expected, dict):
        test.assertEqual(actual.keys(), expected.keys())
        for key in expected:
            with test.subTest(key=key):
                assert_numeric_receipt(test, actual[key], expected[key])
    elif isinstance(expected, list):
        test.assertEqual(len(actual), len(expected))
        for index, (value, reference) in enumerate(zip(actual, expected)):
            with test.subTest(index=index):
                assert_numeric_receipt(test, value, reference)
    elif isinstance(expected, float):
        # Allow libm roundoff and near-zero cancellation, not engineering tolerances.
        test.assertTrue(math.isfinite(actual) and math.isfinite(expected))
        test.assertTrue(math.isclose(actual, expected, rel_tol=1e-13, abs_tol=1e-14),
                        f"{actual!r} != {expected!r}")
    else:
        test.assertEqual(actual, expected)
