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
import iterate as it  # noqa: E402
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


class G2CompressionCriterionTests(unittest.TestCase):
    """Le critère de combustion : proxy calibré pour la recherche, BRep pour le juge."""

    def setUp(self):
        self.p = layout.derive(G2_BASE, G1_DESIGN)

    def test_proxy_counts_piston_pockets(self):
        """Les poches manquaient au proxy : 4 poches de 3,9 mm valent une quinzaine de cm³."""
        self.assertGreater(self.p['piston_pocket_depth'], 0.0)
        without = chk.chamber_volume_mm3(dict(self.p, piston_pocket_depth=0.0))
        self.assertGreater(chk.chamber_volume_mm3(self.p) - without, 10_000.0)

    def test_calibration_is_applied_and_declared(self):
        raw, cal = chk.chamber_volume_mm3(self.p), chk.calibrated_chamber_volume_mm3(self.p)
        self.assertAlmostEqual(cal / raw, G2_BASE['chamber_proxy_calibration'], places=9)
        self.assertLess(chk.calibrated_compression_ratio(self.p), chk.compression_ratio(self.p))
        # Hors G2 la calibration n'existe pas : le taux brut est rendu tel quel.
        p1 = layout.derive(G1_BASE, G1_DESIGN)
        self.assertNotIn('chamber_proxy_calibration', p1)
        self.assertAlmostEqual(chk.calibrated_chamber_volume_mm3(p1), chk.chamber_volume_mm3(p1), places=9)

    def test_band_gap_is_zero_inside_the_widened_band_and_positive_outside(self):
        tol = G2_BASE['compression_proxy_band_tolerance']
        self.assertEqual(chk.compression_band_gap(layout.derive(G1_BASE, G1_DESIGN)), 0.0)  # hors G2
        self.assertGreater(chk.compression_band_gap(self.p), 0.0)  # G1 : taux 4,5, très en dessous
        for angle in (14.0, 16.0):  # voisinage de la plage, mesuré en BRep le 2026-09-16
            d = {k: v for k, v in G1_DESIGN.items() if not k.endswith('_valve_x')}
            p = layout.derive(G2_BASE, dict(d, intake_axis_angle=angle, exhaust_axis_angle=angle))
            self.assertEqual(chk.compression_band_gap(p), 0.0, angle)
            self.assertLessEqual(chk.calibrated_compression_ratio(p), p['compression_ratio_max'] + tol + 1e-9)

    def test_search_record_carries_compression_only_in_g2(self):
        space = pv.load_design_space()
        g2 = it.Search(G2_SPEC, space, G2_BASE).trial(dict(G1_DESIGN), 1, 'test')
        self.assertIn('compression', g2)
        self.assertFalse(g2['compression']['in_band'])
        g1 = it.Search(G1_SPEC, space, G1_BASE).trial(dict(G1_DESIGN), 1, 'test')
        self.assertNotIn('compression', g1)  # journal G1 inchangé, reproductible à l'octet près
        self.assertEqual(g1['score'], round(g1['min_slack'], 3))

    def test_compression_ranks_only_accepted_trials(self):
        def rec(accepted, in_band, slack, score):
            return {'accepted': accepted, 'cycle_evaluated': True, 'min_slack': slack, 'penalty': 0.0,
                    'score': score, 'compression': {'in_band': in_band}}

        # Entre deux configurations acceptées, celle qui est dans la plage l'emporte.
        self.assertGreater(it.Search.rank(rec(True, True, 0.2, 0.2)), it.Search.rank(rec(True, False, 9.0, 9.0)))
        # Un refus reste un refus, même dans la plage.
        self.assertGreater(it.Search.rank(rec(True, False, 9.0, 9.0)), it.Search.rank(rec(False, True, 9.0, 9.0)))
        # Entre deux refus, seule la géométrie classe : sinon la recherche locale poursuit la plage
        # en abandonnant les contrôles (constaté : dans la plage, 6 échecs, marge -4,1 mm).
        far_but_closer = rec(False, False, -0.5, -0.5)
        in_band_but_broken = rec(False, True, -4.1, -4.1)
        self.assertGreater(it.Search.rank(far_but_closer), it.Search.rank(in_band_but_broken))
        # La pénalité de compression ne fausse pas non plus le classement des refus.
        penalised = {**rec(False, False, -0.5, -2.3), 'penalty': 0.0}
        self.assertEqual(it.Search.rank(penalised)[3], -0.5)

    @unittest.skipUnless(HAVE_CQ, 'cadquery absent')
    def test_calibrated_proxy_tracks_brep_near_the_band(self):
        """La calibration ne vaut qu'au voisinage de la plage : c'est là qu'elle doit être juste."""
        import assembly
        d = {k: v for k, v in G1_DESIGN.items() if not k.endswith('_valve_x')}
        p = layout.derive(G2_BASE, dict(d, intake_axis_angle=16.0, exhaust_axis_angle=16.0))
        brep = assembly.compression_ratio(p)
        self.assertLess(abs(chk.calibrated_compression_ratio(p) - brep['compression_ratio']), 0.3)
        # Loin de la plage, elle dérive : le proxy n'est donc jamais le juge.
        far = layout.derive(G2_BASE, dict(d, intake_axis_angle=28.0, exhaust_axis_angle=28.0))
        self.assertGreater(chk.calibrated_compression_ratio(far), assembly.compression_ratio(far)['compression_ratio'])


if __name__ == '__main__':
    unittest.main()
