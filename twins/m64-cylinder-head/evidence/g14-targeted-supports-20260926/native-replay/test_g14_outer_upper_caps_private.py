"""Small native geometry checks, no FE or CAD qualification substitute."""
import json
import unittest
import g14_outer_upper_caps_private as c


class UpperCaps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=json.loads((c.PRIOR/'receipt.json').read_text())['values']

    def test_bounded_boxes_and_axial_gaps(self):
        for sy in (-1,1):
            for side,q in c.cap_boxes(self.p,sy).items():
                pivot,_=c.carrier.axes(self.p)[side]
                self.assertAlmostEqual(q['x_mm'][1]-q['x_mm'][0],18)
                self.assertAlmostEqual(q['z_mm'][1]-q['z_mm'][0],6)
                self.assertAlmostEqual(q['z_mm'][0]-pivot[2],8.5)
                front=min(abs(y) for y in q['y_mm'])
                self.assertAlmostEqual(front-(self.p[side+'_valve_y']+self.p['rocker_width']/2),1)
                self.assertAlmostEqual(front-(self.p[side+'_valve_y']+self.p['cam_lobe_width']/2),6)

    def test_raw_caps_do_not_need_service_pocketing(self):
        for sy in (-1,1):
            shapes=[c.box(q) for q in c.cap_boxes(self.p,sy).values()]
            tools,definitions=c.service_tools(self.p,sy,250)
            self.assertEqual(len(tools),12)
            self.assertEqual(set(tools),set(definitions))
            for shape in shapes:
                for tool in list(tools.values())+list(c.cam_masks(self.p,sy).values()):
                    self.assertLessEqual(c.audit.overlap(shape,tool),1e-5)

    def test_raw_caps_are_mirrored(self):
        plus=[c.box(q) for q in c.cap_boxes(self.p,1).values()]
        minus=[c.box(q) for q in c.cap_boxes(self.p,-1).values()]
        for a,b in zip(plus,minus):
            self.assertTrue(all(v<=1e-5 for v in c.g13.difference(b,a.mirror('XZ')).values()))


if __name__=='__main__':
    unittest.main()
