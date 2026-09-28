"""Small G11 grid contract and optional native geometry regression."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('g11_cad', ROOT/'twins/m64-cylinder-head/source/fourvalve/g11_cad.py')
g = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(g)
try:
    import cadquery as cq
except ImportError:
    cq = None


class G11CAD(unittest.TestCase):
    def test_grid_keeps_parameters_independent_and_rejects_unapproved_variants(self):
        rows = g.candidates()
        self.assertEqual(len({r['id'] for r in rows}), 12)
        for row in rows:
            d = g.dimensions(row)
            self.assertEqual(d['bottom']+d['depth'], 138)
            self.assertEqual(d['centre_x_margin'], 9)
            self.assertEqual(d['outer_journal_width'], 8)
            if row['component'] == 'carrier_base_p':
                self.assertEqual(d['centre_width'], 10)
            else:
                self.assertEqual(d['outer_width'], 18)
                self.assertEqual(d['depth'], 18)
        invalid = dict(rows[0], parameters=dict(rows[0]['parameters'], centre_wall_mm=12))
        with self.assertRaises(ValueError):
            g.dimensions(invalid)

    @unittest.skipUnless(cq, 'cadquery absent')
    def test_rigid_rocker_and_cam_transforms_match_native_construction(self):
        import json
        import rocker_train
        p = json.loads(g.BASELINE.read_text())['values']
        # No full-head construction needed to check the rotation conventions.
        reference = rocker_train.parts(p, 0)
        import components
        reference['piston'] = components.piston(p, 0)
        import kinematics
        import numpy as np
        laws, _ = kinematics.cam_laws(p)
        for side in ('intake', 'exhaust'):
            lift = float(laws[side].valve_lift(np.radians(0))[0])*1000
            for sy in (-1, 1):
                tag = side+('_p' if sy > 0 else '_m')
                reference['valve_'+tag] = components.valve(p, side, sy, lift)
                reference['retainer_'+tag] = components.retainer(p, side, sy, lift)
                reference['spring_'+tag] = components.spring(p, side, sy, lift)
        transformed = g.moving_shapes(p, reference, 137)
        direct = rocker_train.parts(p, 137)
        for name in ('camshaft_intake', 'camshaft_exhaust', 'rocker_intake_p', 'roller_exhaust_m'):
            self.assertLess(abs(transformed[name].Volume()-direct[name].Volume()), 1e-5, name)
            self.assertLess(transformed[name].cut(direct[name]).Volume(), 1e-4, name)


if __name__ == '__main__':
    unittest.main()
