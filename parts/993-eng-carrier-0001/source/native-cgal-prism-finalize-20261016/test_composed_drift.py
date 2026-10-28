"""Known exact radical comparisons for the composed distance certificate."""
import unittest
from fractions import Fraction as F
from audit_composed_drift import bounded_sum

class Bounds(unittest.TestCase):
    def test_exact_equality_and_strict_refusal(self):
        self.assertTrue(bounded_sum(F(4),F(9),F(5)))
        self.assertFalse(bounded_sum(F(4),F(9),F(4999,1000)))
    def test_negative_margin_cannot_pass_after_squaring(self):
        self.assertFalse(bounded_sum(F(9),F(16),F(1)))
    def test_irrational_roots_are_compared_without_rounding(self):
        self.assertTrue(bounded_sum(F(2),F(2),F(3)))
        self.assertFalse(bounded_sum(F(2),F(2),F(14,5)))
    def test_tiny_exact_equality(self):
        self.assertTrue(bounded_sum(F(0),F(1,10**40),F(1,10**20)))
    def test_negative_squared_distance_is_rejected(self):
        with self.assertRaises(AssertionError):bounded_sum(F(-1),F(0),F(1))

if __name__=='__main__':unittest.main()
