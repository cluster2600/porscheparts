import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'))


@unittest.skipUnless(importlib.util.find_spec('numpy'), 'optional numpy runtime')
class CoincidentJunctionTests(unittest.TestCase):
    def test_single_star_and_two_point_contact_are_distinguished(self):
        import numpy as np
        from audit_coincident_junctions import link_summary
        good=link_summary(np.array([[0,1,2,3],[0,1,3,4]]),0)
        self.assertTrue(good['necessary_ball_or_halfball_conditions'])
        bad=link_summary(np.array([[0,1,2,3],[0,4,5,6]]),0)
        self.assertEqual(bad['link_components'],2)
        self.assertFalse(bad['necessary_ball_or_halfball_conditions'])
        with self.assertRaises(ValueError): link_summary(np.array([[0,0,1,2]]),0)

    def test_closed_star_has_spherical_link(self):
        import numpy as np
        from audit_coincident_junctions import link_summary
        value=link_summary(np.array([[0,1,2,3],[0,1,4,2],[0,1,3,4],[0,2,4,3]]),0)
        self.assertEqual(value['link_euler'],2)
        self.assertEqual(value['link_boundary_edges'],0)
        self.assertTrue(value['necessary_ball_or_halfball_conditions'])


if __name__ == '__main__': unittest.main()
