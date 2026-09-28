"""One native regression for the existing outer's shortened root transition."""
import unittest

import g14_outer_root_private as cad


class OuterRoot(unittest.TestCase):
    def test_added_root_preserves_interfaces_tools_and_mirror(self):
        old,_,p=cad.inputs();shapes={};z0=p['carrier_face_height']
        slab=cad.cq.Solid.makeBox(400,200,1,cad.cq.Vector(-200,-100,z0))
        for tag,sy in (('p',1),('m',-1)):
            row=next(r for r in old['variants'] if r['component']=='carrier_base_'+tag)
            path=cad.PRIOR/row['step']
            self.assertEqual(cad.g11.sha256(path),row['step_sha256'])
            base=cad.cq.importers.importStep(str(path)).val()
            shape=cad.reinforced(base,p,sy);shapes[tag]=shape
            self.assertTrue(cad.assembly.brep_valid(shape))
            self.assertEqual(len(shape.Solids()),1)
            self.assertLessEqual(base.cut(shape).Volume(),cad.g11.TOL)
            land,_=cad.g13.support_land(shape,p);old_land,_=cad.g13.support_land(base,p)
            checks=[cad.g13.difference(shape.intersect(slab),base.intersect(slab)),cad.g13.difference(land,old_land),
                    *cad.previous.journal_masks(shape,base,p).values()]
            self.assertTrue(all(v<=cad.g11.TOL for d in checks for v in d.values()))
            added=shape.cut(base);box=added.BoundingBox()
            self.assertGreater(added.Volume(),0)
            self.assertGreaterEqual(box.zmin,z0+1-1e-6)
            self.assertLessEqual(box.zmax,108+1e-6)
            for tool in cad.lower.functional_tools(p,sy).values():
                self.assertLessEqual(cad.audit.overlap(added,tool),cad.g11.TOL)
            for tool in cad.g11.oil_paths(p,'carrier_base_p').values():
                self.assertLessEqual(cad.audit.overlap(shape,tool if sy==1 else tool.mirror('XZ')),cad.g11.TOL)
        self.assertTrue(all(v<=cad.g11.TOL for v in cad.g13.difference(shapes['m'],shapes['p'].mirror('XZ')).values()))


if __name__=='__main__':
    unittest.main()
