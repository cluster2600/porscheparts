"""Native bounded intake-web checks, no stiffness calculation."""
import json
import unittest
import g14_outer_intake_web_private as c


class IntakeWeb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=json.loads((c.PRIOR/'receipt.json').read_text())
        cls.p=cls.receipt['values']

    def test_single_intake_profile_and_mirror(self):
        p=self.p
        for sy in (-1,1):
            profile=c.band_profiles(p,sy)
            self.assertEqual(set(profile),{'intake'})
            self.assertEqual(profile['intake']['x_mm'],[-40,-20])
            self.assertEqual([z for _,z in profile['intake']['profile_yz_mm']],
                             [p['carrier_face_height']+1,138,138,p['carrier_face_height']+3])
            self.assertAlmostEqual(min(abs(y) for y,_ in profile['intake']['profile_yz_mm']),34.59375)
        plus,minus=c.raw_bands(p,1)[0],c.raw_bands(p,-1)[0]
        self.assertTrue(all(v<=1e-5 for v in c.g13.difference(plus.mirror('XZ'),minus).values()))

    def test_added_material_preserves_base_foot_tools_oil_and_envelope(self):
        p=self.p
        for sy,tag in ((1,'p'),(-1,'m')):
            row=next(r for r in self.receipt['variants'] if r['id']=='outer_inner_lower_bands_'+tag)
            step=c.PRIOR/row['step'];self.assertEqual(c.g11.sha256(step),row['step_sha256'])
            base=c.cq.importers.importStep(str(step)).val();shape=c.reinforced(base,p,sy);new=shape.cut(base)
            self.assertGreater(new.Volume(),0);self.assertLessEqual(base.cut(shape).Volume(),1e-5)
            self.assertTrue(c.assembly.brep_valid(shape));self.assertEqual(len(shape.Solids()),1)
            slab=c.cq.Solid.makeBox(400,200,1,c.cq.Vector(-200,-100,p['carrier_face_height']))
            self.assertLessEqual(c.audit.overlap(new,slab),1e-5)
            before,after=c.g7.native_bounds(base),c.g7.native_bounds(shape)
            for key in before:self.assertAlmostEqual(before[key],after[key],places=6)
            for tool in c.lower.functional_tools(p,sy).values():self.assertLessEqual(c.audit.overlap(new,tool),1e-5)
            for tool in c.g11.oil_paths(p,'carrier_base_p').values():
                self.assertLessEqual(c.audit.overlap(shape,tool if sy==1 else tool.mirror('XZ')),1e-5)
            for tool in c.plug_tools(p,180)[0].values():self.assertLessEqual(c.audit.overlap(new,tool),1e-5)

    def test_full_cross_web_would_obstruct_plug_tool(self):
        web=c.cq.Solid.makeBox(82,14,49,c.cq.Vector(-40,31,89))
        tools,definitions=c.plug_tools(self.p,180)
        self.assertTrue(all(v['radius_mm']==11 for v in definitions.values()))
        self.assertGreater(max(c.audit.overlap(web,t) for t in tools.values()),1)


if __name__=='__main__':unittest.main()
