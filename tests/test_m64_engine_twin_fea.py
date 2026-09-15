import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fea", ROOT / "twins/m64-engine-twin/source/fea_screens.py")
fea = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fea)

EIGEN = """
     E I G E N V A L U E   O U T P U T

 MODE NO    EIGENVALUE                       FREQUENCY
                                     REAL PART            IMAGINARY PART
                           (RAD/TIME)      (CYCLES/TIME     (RAD/TIME)

      1   0.9869604E+01   0.3141593E+01   0.5000000E+00   0.0000000E+00
      2   0.1290000E+08   0.3591657E+04   0.5716300E+03   0.0000000E+00

     P A R T I C I P A T I O N   F A C T O R S
"""

STATIC = """
 displacements (vx,vy,vz) for set NALL and time  0.1000000E+01

         1  0.000000E+00  3.000000E+00  4.000000E+00

 stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set BODY and time  0.1000000E+01

         1   1  1.000000E+02  0.000000E+00  0.000000E+00  0.000000E+00  0.000000E+00  0.000000E+00
"""


class FeaParserTests(unittest.TestCase):
    def test_eigen_table(self):
        self.assertEqual(fea.parse_frequencies(EIGEN), [0.5, 571.63])
        with self.assertRaises(RuntimeError):
            fea.parse_frequencies("no table")

    def test_static_tables(self):
        result = fea.parse_static(STATIC)
        self.assertAlmostEqual(result["max_displacement_mm"], 5.0)
        self.assertAlmostEqual(result["von_mises_max_mpa"], 100.0)

    def test_unit_tet_volume(self):
        points = {1: (0, 0, 0), 2: (1, 0, 0), 3: (0, 1, 0), 4: (0, 0, 1)}
        self.assertAlmostEqual(fea.tet_volume(points, [1, 2, 3, 4]), 1 / 6)

    def test_ground_springs_stay_far_below_elastic_threshold(self):
        # Seuil de tri a au moins 10 fois la frequence des ressorts de sol.
        self.assertGreaterEqual(fea.MIN_ELASTIC_HZ, 10 * fea.GROUND_SPRING_HZ)

    def test_materials_declare_their_source_type(self):
        for material in fea.MATERIALS.values():
            self.assertIn(material["source_type"], {"documented", "estimated"})

    def test_recorded_self_check_passed(self):
        record = json.loads((ROOT / "twins/m64-engine-twin/evidence/fea-self-check-20260915.json").read_text())
        self.assertTrue(record["passed"])
        self.assertLess(record["rel_error_f1"], 0.03)
        self.assertLess(record["rel_error_tip"], 0.05)


if __name__ == "__main__":
    unittest.main()
