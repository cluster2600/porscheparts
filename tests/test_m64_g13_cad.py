"""Bounded upper-spine CAD, preserving the actual baseline journal and fixed land."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'twins/m64-cylinder-head/source/fourvalve'))
import g13_cad as g
try:
    import cadquery as cq
except ImportError:
    cq = None


class G13CAD(unittest.TestCase):
    def test_bounded_variants_and_foot_neck(self):
        self.assertEqual(len(g.candidates()), 3)
        self.assertEqual([r['parameters']['spine_width_mm'] for r in g.candidates()], [18, 24, 30])
        for row in g.candidates():
            self.assertEqual(row['journal_width_mm'], 11)
            self.assertEqual(row['parameters']['spine_x_span_mm'], 60)
            self.assertEqual(g.spine_profile(row, 70)[:2], [(-5.5, 1.), (5.5, 1.)])
            edited = copy.deepcopy(row)
            edited['parameters']['journal_width_mm'] = 12
            with self.assertRaises(ValueError):
                g.spine_profile(edited, 70)
            with self.assertRaises(ValueError):
                g.spine_profile(row, 10)

    @unittest.skipUnless(cq, 'cadquery absent')
    def test_spine_preserves_land_and_journals(self):
        import assembly
        p = json.loads(g.g11.BASELINE.read_text())['values']
        base = g.g11.candidate_shape(next(r for r in g.g11.candidates() if r['id'] == 'centre_w11'), p, {})
        land, metadata = g.support_land(base, p)
        for row in g.candidates():
            shape = g.candidate_shape(row, p, base)
            self.assertTrue(assembly.brep_valid(shape))
            self.assertEqual(len(shape.Solids()), 1)
            self.assertGreater(shape.Volume(), base.Volume())
            self.assertLess(base.cut(shape).Volume(), 1e-5)
            candidate_land, candidate_metadata = g.support_land(shape, p)
            self.assertAlmostEqual(metadata['bottom_planar_area_mm2'], candidate_metadata['bottom_planar_area_mm2'], places=5)
            for value in g.difference(candidate_land, land).values():
                self.assertLess(value, 1e-5)
            for result in g.journal_neighbourhoods(shape, base, p).values():
                for value in result.values():
                    self.assertLess(value, 1e-5)


if __name__ == '__main__':
    unittest.main()
