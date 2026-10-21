"""The authorised longer resource case must preserve every geometric policy byte."""
from pathlib import Path
import unittest


class DeadlineOnlyChangeTests(unittest.TestCase):
    def test_long_helper_diff_is_only_deadline_argument_ceiling(self):
        folder=Path(__file__).resolve().parents[1]/"twins/962-cylinder-head-f0/source/analysis-cgal"
        original=(folder/"envelope.cpp").read_text()
        expected=original.replace("deadline>285","deadline>1800").replace("<=285s","<=1800s")
        self.assertNotEqual(expected,original)
        self.assertEqual((folder/"envelope_long.cpp").read_text(),expected)


if __name__=="__main__":unittest.main()
