import unittest

from numeric_receipt import assert_numeric_receipt


class NumericReceiptTests(unittest.TestCase):
    def test_accepts_roundoff_and_near_zero_cancellation(self):
        assert_numeric_receipt(self,
            {"flow_gain": 0.018727599897548908, "swirl": [8.881784197001252e-16], "release": False},
            {"flow_gain": 0.01872759989754913, "swirl": [1.7763568394002505e-15], "release": False})

    def test_rejects_numerical_changes_nonfinite_and_changed_contracts(self):
        for actual, expected in [
            (1.0 + 1e-11, 1.0), (1e-12, 0.0),
            (float("nan"), 1.0), (float("inf"), float("inf")),
            (True, False), (0, False), (1, 1.0),
            ({"x": 1.0}, {"y": 1.0}), ([1.0, 2.0], [1.0]),
            ({"release": True}, {"release": False}), ([2.0], [1.0]),
            ("qualified", "blocked"),
        ]:
            with self.subTest(actual=actual, expected=expected):
                with self.assertRaises(AssertionError):
                    assert_numeric_receipt(unittest.TestCase(), actual, expected)


if __name__ == "__main__":
    unittest.main()
