"""Bounded native checks for a single lower-band hypothesis, no FEA."""
import json
import unittest

import g14_outer_inner_bands_private as c
import layout


class InnerBands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=json.loads((c.PRIOR/'receipt.json').read_text())
        cls.p=cls.receipt['values']

    def test_profiles_preserve_root_height_and_stay_outside_spring_x_envelopes(self):
        p=self.p;z0=p['carrier_face_height']
        for sy in (-1,1):
            bands=c.band_profiles(p,sy)
            self.assertEqual(bands['intake']['x_mm'],[-40,-32])
            self.assertEqual(bands['exhaust']['x_mm'],[32,42])
            for side,data in bands.items():
                yz=data['profile_yz_mm']
                self.assertEqual([z for y,z in yz],[z0+1,108,108,z0+3])
                self.assertAlmostEqual(min(abs(y) for y,z in yz),31.09375)
                self.assertEqual(max(abs(y) for y,z in yz),45)
                u=layout.axis_up(p,side);seat=layout.head_centre(p,side,sy)+u*p[side+'_spring_seat_axial']
                top=seat+u*p['spring_installed_height']
                # Shorter compressed cones lie within the closed outer cone;
                # the inner-x extreme is conservative for both spring and retainer.
                lo=min(seat[0]-15*u[2],top[0]-13*u[2])
                hi=max(seat[0]+15*u[2],top[0]+13*u[2])
                gap=data['x_mm'][0]-hi if side=='intake' else lo-data['x_mm'][1]
                self.assertGreater(gap,1.4)

    def test_raw_bands_mirror_and_avoid_first_millimetre(self):
        p=self.p
        slab=c.cq.Solid.makeBox(400,200,1,c.cq.Vector(-200,-100,p['carrier_face_height']))
        plus,minus=c.raw_bands(p,1),c.raw_bands(p,-1)
        for a,b in zip(plus,minus):
            self.assertTrue(all(v<=1e-5 for v in c.g13.difference(a.mirror('XZ'),b).values()))
            self.assertLessEqual(c.audit.overlap(a,slab),1e-5)

    def test_native_addition_preserves_base_tools_oil_and_envelope(self):
        for sy,tag in ((1,'p'),(-1,'m')):
            row=next(r for r in self.receipt['variants'] if r['id']=='outer_root2_upper_caps_'+tag)
            step=c.PRIOR/row['step'];self.assertEqual(c.g11.sha256(step),row['step_sha256'])
            base=c.cq.importers.importStep(str(step)).val()
            result=c.reinforced(base,self.p,sy);new=result.cut(base)
            self.assertLessEqual(base.cut(result).Volume(),1e-5)
            self.assertTrue(c.assembly.brep_valid(result));self.assertEqual(len(result.Solids()),1)
            self.assertGreater(new.Volume(),0)
            a,b=c.g7.native_bounds(base),c.g7.native_bounds(result)
            for k in a:self.assertAlmostEqual(a[k],b[k],places=6)
            for tool in c.lower.functional_tools(self.p,sy).values():self.assertLessEqual(c.audit.overlap(new,tool),1e-5)
            for tool in c.g11.oil_paths(self.p,'carrier_base_p').values():
                self.assertLessEqual(c.audit.overlap(result,tool if sy==1 else tool.mirror('XZ')),1e-5)


if __name__=='__main__':
    unittest.main()
