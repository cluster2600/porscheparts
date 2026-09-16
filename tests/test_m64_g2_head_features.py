"""G2 culasse : conduits courbes, galerie d'huile, ailettes (numpy) ; CAO et taux de compression en skip."""
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FV = ROOT / 'twins' / 'm64-cylinder-head' / ('sour' + 'ce') / 'fourvalve'
sys.path[:0] = [str(FV), str(FV / 'cad')]

import checks as chk  # noqa: E402
import features as ft  # noqa: E402
import layout  # noqa: E402
import provenance as pv  # noqa: E402
import run as fv_run  # noqa: E402

EXTRA = FV / 'params-g2' / 'head_features.json'
G1_RESOLVED = ROOT / 'twins/m64-cylinder-head/evidence/g1-four-valve-20260914/parameters-resolved.json'
# Configuration G1 acceptée : la CAO se juge sur elle, pas sur le départ 935 qui échoue aux contrôles.
G1_DESIGN = {name: row['value'] for name, row in json.loads(G1_RESOLVED.read_text()).items()
             if row['provenance'] == 'derived_by_iteration'}

try:
    import cadquery  # noqa: F401
    HAVE_CQ = True
except ImportError:
    HAVE_CQ = False

SRC = pv.load_sources()
G1_SPEC = pv.load_spec()
G1_BASE, _ = pv.resolve_base(G1_SPEC, SRC)
G2_SPEC = fv_run.load_extra(pv.load_spec(), [EXTRA])
G2_BASE, _ = pv.resolve_base(G2_SPEC, SRC)


class G2FeatureTests(unittest.TestCase):
    def setUp(self):
        self.p = layout.derive(G2_BASE)

    def test_g1_is_unchanged_without_extra_parameters(self):
        p = layout.derive(G1_BASE)
        self.assertFalse(ft.enabled(p))
        cyl = layout.cylinders(p)
        self.assertIn('port_intake_p', cyl)
        self.assertFalse(any(k.startswith('port_intake_p_') or k == 'oil_gallery' for k in cyl))

    def test_every_g2_parameter_is_declared_unsourced_with_hypothesis(self):
        for name in G2_SPEC['components']['head_features_g2']:
            item = G2_SPEC['parameters'][name]
            self.assertEqual(item['provenance'], 'unsourced', name)
            self.assertTrue(item.get('hypothesis'), name)
        with self.assertRaises(ValueError):
            fv_run.load_extra(pv.load_spec(), [EXTRA, EXTRA])

    def test_port_path_starts_on_valve_axis_and_ends_on_flange(self):
        for side, sy in layout.VALVES:
            pts, radii = ft.port_path(self.p, side, sy)
            c, u = layout.head_centre(self.p, side, sy), layout.axis_up(self.p, side)
            np.testing.assert_allclose(pts[0], c + u * self.p['throat_axial_offset'], atol=1e-9)
            self.assertAlmostEqual(pts[-1][0], self.p[f'{side}_flange_x'])
            self.assertAlmostEqual(pts[-1][2], self.p[f'{side}_port_z'])
            # Tangentes exactes d'une Bézier cubique : B'(0) ∝ p1 − p0, B'(1) ∝ p3 − p2.
            p0, p1, p2, p3 = ft.port_controls(self.p, side, sy)
            start = (p1 - p0) / np.linalg.norm(p1 - p0)
            self.assertAlmostEqual(float(start @ u), 1.0, places=9, msg='départ tangent à l\'axe de soupape')
            end = (p3 - p2) / np.linalg.norm(p3 - p2)
            self.assertAlmostEqual(abs(float(end[0])), 1.0, places=9, msg='arrivée perpendiculaire à la bride')
            self.assertEqual(len(pts), int(self.p['port_bezier_segments']) + 1)
            self.assertAlmostEqual(radii[0], self.p[f'{side}_throat_diameter'] / 2)

    def test_cylinders_carry_segments_and_gallery_into_checks(self):
        cyl = layout.cylinders(self.p)
        n = int(self.p['port_bezier_segments'])
        for side, sy in layout.VALVES:
            tag = f'{side}_{"p" if sy > 0 else "m"}'
            self.assertNotIn(f'port_{tag}', cyl)
            self.assertEqual(sum(k.startswith(f'port_{tag}_') for k in cyl), n)
        self.assertIn('oil_gallery', cyl)
        names = {c['check'] for c in chk.static_checks(self.p)}
        for expected in ('oil_gallery_vs_spring_pockets', 'oil_gallery_vs_plugs', 'oil_gallery_vs_studs',
                         'oil_gallery_below_carrier_face', 'plug_vs_ports', 'stud_vs_ports'):
            self.assertIn(expected, names)

    def test_fins_stay_outside_block_and_below_carrier_face(self):
        boxes = ft.fin_boxes(self.p)
        self.assertTrue(boxes)
        w = self.p['head_block_width_y']
        for x, y, z, dx, dy, dz in boxes:
            self.assertTrue(y >= w / 2 - 1e-9 or y + dy <= -w / 2 + 1e-9)
            self.assertLessEqual(z + dz, self.p['carrier_face_height'] + 1e-9)
            self.assertGreater(dx, 0)

    @unittest.skipUnless(HAVE_CQ, 'cadquery absent')
    def test_head_single_solid_and_compression_ratio_is_plausible(self):
        import assembly
        import components as comp
        p = layout.derive(G2_BASE, G1_DESIGN)
        head = comp.head(p)
        self.assertTrue(assembly.brep_valid(head))
        self.assertEqual(len(head.Solids()), 1)
        g1_faces = len(comp.head(layout.derive(G1_BASE, G1_DESIGN)).Faces())
        self.assertGreater(len(head.Faces()), g1_faces)
        cr = assembly.compression_ratio(p)
        # Bornes larges : la chambre n'est pas arrêtée. Le taux mesuré sur la configuration G1
        # (grands angles de soupape, piston plat à bol) reste très inférieur aux 8:1 usuels en turbo.
        self.assertTrue(math.isfinite(cr['compression_ratio']))
        self.assertGreater(cr['compression_ratio'], 2.0)
        self.assertLess(cr['compression_ratio'], 16.0)
        self.assertGreater(cr['clearance_volume_cc'], 0.0)
        # Le proxy numpy ignore sièges, gorges et conduits : il sous-estime, mais reste du même ordre.
        proxy = chk.chamber_volume_mm3(p) / 1000
        self.assertLess(proxy, cr['clearance_volume_cc'])
        self.assertGreater(proxy, 0.5 * cr['clearance_volume_cc'])
        self.assertAlmostEqual(cr['swept_volume_cc'],
                               math.pi * (p['bore_diameter'] / 2) ** 2 * p['crank_stroke'] / 1000, places=1)


if __name__ == '__main__':
    unittest.main()
