"""Bounded flare parameters and unchanged upper journal geometry."""
import json
import hashlib
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
FV = ROOT/'twins/m64-cylinder-head/source/fourvalve'
sys.path.insert(0, str(FV))
import g12_cad as g
try:
    import cadquery as cq
except ImportError:
    cq = None


class G12CAD(unittest.TestCase):
    def test_published_geometry_retains_rejections_without_a_stiffness_claim(self):
        evidence = ROOT/'twins/m64-cylinder-head/evidence/g12-local-buttresses-20260926'
        receipt = json.loads((evidence/'cad.json').read_text())
        self.assertEqual(receipt['source_sha256'], hashlib.sha256(Path(g.__file__).read_bytes()).hexdigest())
        self.assertTrue(receipt['complete'])
        for flag in ('FEA_executed', 'manufacturing_authorized', 'engine_start_authorized'):
            self.assertIs(receipt[flag], False)
        self.assertEqual(len(receipt['variants']), 4)
        for row in receipt['variants']:
            self.assertEqual(row['motion_samples_checked'], 144)
            self.assertEqual(row['journal_width_mm'], 11)
            local = '_local' in row['id']
            self.assertEqual(row['cad_accepted'], local)
            self.assertEqual(bool(row['sampled_motion_interferences']), not local)
            if local:
                self.assertEqual(row['rejections'], [])
                self.assertGreater(row['added_buttress_spring_conservative_x_gap_mm'], 2.5)
            if row['id'] == 'centre_w11_local24_foot24_h40':
                for view, expected in row['native_views'].items():
                    self.assertEqual(hashlib.sha256((evidence/('local24-'+view)).read_bytes()).hexdigest(), expected)

    def test_bounded_profiles_keep_upper_width(self):
        self.assertEqual(len(g.candidates()), 4)
        for row in g.candidates():
            p = row['parameters']
            profile = g.flare_profile(p['base_width_mm'], p['flare_height_mm'])
            self.assertEqual(profile[1][0]-profile[0][0], p['base_width_mm'])
            self.assertEqual(profile[2][0]-profile[3][0], 11)
            if 'local_x_span_mm' in p:
                self.assertIn(p['local_x_span_mm'], (24, 28))
                self.assertLessEqual(25+p['local_x_span_mm']/2, 39)
        for w, h in ((24, 50), (30, 40), (math.nan, 40), (11, 40)):
            with self.assertRaises(ValueError):
                g.flare_profile(w, h)

    @unittest.skipUnless(cq, 'cadquery absent')
    def test_flare_preserves_upper_shape_and_is_connected(self):
        import assembly
        p = json.loads(g.g11.BASELINE.read_text())['values']
        base = g.g11.candidate_shape(next(r for r in g.g11.candidates() if r['id'] == 'centre_w11'), p, {})
        top = cq.Solid.makeBox(1000, 1000, 1000, cq.Vector(-500, -500, p['carrier_face_height']+50.001))
        for row in g.candidates():
            shape = g.candidate_shape(row, p, base)
            self.assertTrue(assembly.brep_valid(shape))
            self.assertEqual(len(shape.Solids()), 1)
            self.assertLess(shape.intersect(top).cut(base).Volume(), 1e-5)
            self.assertLess(base.cut(shape).Volume(), 1e-5)
            self.assertGreater(shape.Volume(), base.Volume())


if __name__ == '__main__':
    unittest.main()
