"""Native regression of the single upper-cap hypothesis, not FEA qualification."""
import unittest

import g14_central_caps_private as cad


class CentralCaps(unittest.TestCase):
    def test_only_local_caps_added_outside_interfaces(self):
        _,_,p,base=cad.inputs();shape=cad.reinforced(base,p)
        self.assertTrue(cad.assembly.brep_valid(shape))
        self.assertEqual(len(shape.Solids()),1)
        self.assertLessEqual(base.cut(shape).Volume(),cad.g11.TOL)
        self.assertAlmostEqual(shape.Volume()-base.Volume(),4078.930025,places=2)
        slab=cad.cq.Solid.makeBox(400,200,1,cad.cq.Vector(-200,-100,p['carrier_face_height']))
        checks=[cad.g13.difference(shape.intersect(slab),base.intersect(slab)),
                *cad.root.previous.journal_masks(shape,base,p).values()]
        self.assertTrue(all(v<=cad.g11.TOL for d in checks for v in d.values()))
        added=shape.cut(base)
        for tool in cad.root.followup.tools(p).values():
            self.assertLessEqual(cad.audit.overlap(added,tool),cad.g11.TOL)
        for side,(pivot,_) in cad.carrier.axes(p).items():
            q=cad.cap_boxes(p)[side]
            self.assertAlmostEqual(q['z_mm'][0]-pivot[2],8.5)
            self.assertAlmostEqual(q['z_mm'][1]-q['z_mm'][0],3)


if __name__=='__main__':
    unittest.main()
