"""Native regression for the one shortened w40 root transition."""
import unittest

import g14_central_root_private as cad


class CentralRoot(unittest.TestCase):
    def test_added_root_preserves_first_millimetre_and_journals(self):
        _,_,p,base=cad.inputs();shape=cad.reinforced(base,p)
        self.assertTrue(cad.assembly.brep_valid(shape))
        self.assertEqual(len(shape.Solids()),1)
        self.assertLessEqual(base.cut(shape).Volume(),cad.g11.TOL)
        z0=p['carrier_face_height']
        slab=cad.cq.Solid.makeBox(400,200,1,cad.cq.Vector(-200,-100,z0))
        checks=[cad.g13.difference(shape.intersect(slab),base.intersect(slab)),
                *cad.previous.journal_masks(shape,base,p).values()]
        self.assertTrue(all(v<=cad.g11.TOL for d in checks for v in d.values()))
        added=shape.cut(base);bounds=added.BoundingBox()
        self.assertAlmostEqual(added.Volume(),6902,places=2)
        self.assertGreaterEqual(bounds.zmin,z0+1-1e-6)
        self.assertLessEqual(bounds.zmax,z0+10+1e-6)
        for tool in cad.followup.tools(p).values():
            self.assertLessEqual(cad.audit.overlap(added,tool),cad.g11.TOL)


if __name__=='__main__':
    unittest.main()
