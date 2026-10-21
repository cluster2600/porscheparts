"""Exact fixed-face quality arithmetic, independent of the native floating metric."""
from fractions import Fraction
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"twins/962-cylinder-head-f0/source"))
from certify_fixed_face import certificate


class RationalFaceTests(unittest.TestCase):
    def test_right_isosceles_face_is_not_rejected(self):
        row=certificate([[0.,0,0],[1.,0,0],[0,1.,0]])
        q=row["exact_triangle_SICN_squared"]
        self.assertEqual(Fraction(int(q["numerator"]),int(q["denominator"])),Fraction(3,4))
        self.assertFalse(row["no_positive_linear_tetrahedron_with_this_fixed_face_can_reach_SICN_point1"])

    def test_exact_binary_sliver_proves_impossibility_and_scale_invariance(self):
        p=[[0.,0,0],[1.,0,0],[0,1/1024,0]];row=certificate(p)
        self.assertTrue(row["exact_strict_inequality_2700_cross_squared_lt_edge_sum_squared"])
        scaled=certificate([[x*2**20 for x in v] for v in p])
        self.assertEqual(row["exact_triangle_SICN_squared"],scaled["exact_triangle_SICN_squared"])

    def test_degenerate_and_nonfinite_input_rejected(self):
        for p in [[[0.,0,0],[1.,0,0],[2.,0,0]],[[0.,0,0],[1.,0,0],[0,float("nan"),0]]]:
            with self.assertRaises(ValueError):certificate(p)


if __name__=="__main__":unittest.main()
