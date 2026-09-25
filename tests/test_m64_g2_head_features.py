"""G2 culasse : conduits courbes, galerie d'huile, ailettes (numpy) ; CAO et taux de compression en skip."""
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
    def test_head_single_solid_does_not_prove_a_closed_chamber(self):
        import assembly
        import components as comp
        resolved = ROOT / 'twins/m64-cylinder-head/evidence/g2-head-features-20260916/parameters-resolved.json'
        p = {k: row['value'] for k, row in json.loads(resolved.read_text()).items()}
        head = comp.head(p)
        self.assertTrue(assembly.brep_valid(head))
        self.assertEqual(len(head.Solids()), 1)
        g1_faces = len(comp.head(layout.derive(G1_BASE, G1_DESIGN)).Faces())
        self.assertGreater(len(head.Faces()), g1_faces)
        cr = assembly.compression_ratio(p)
        # Les puits de bougie restent ouverts : une BRep de culasse valide ne ferme pas le gaz.
        self.assertEqual(cr['status'], 'blocked_unsealed_chamber')
        self.assertIsNone(cr['compression_ratio'])
        self.assertIsNone(cr['clearance_volume_cc'])
        self.assertIn('upper_probe_boundary', cr['artificial_boundaries_reached'])
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
        def rec(accepted, in_band, score, penalty=0.0):
            # ``score`` est le score géométrique, comme en G1 ; la combustion est tenue à part.
            return {'accepted': accepted, 'cycle_evaluated': True, 'min_slack': score, 'penalty': 0.0,
                    'score': score, 'compression': {'in_band': in_band, 'score_penalty': penalty}}

        # Entre deux configurations acceptées, celle qui est dans la plage l'emporte.
        self.assertGreater(it.Search.rank(rec(True, True, 0.2)), it.Search.rank(rec(True, False, 9.0)))
        # Un refus reste un refus, même dans la plage.
        self.assertGreater(it.Search.rank(rec(True, False, 9.0)), it.Search.rank(rec(False, True, 9.0)))
        # Entre deux refus, seule la géométrie classe : sinon la recherche locale poursuit la plage
        # en abandonnant les contrôles (constaté : dans la plage, 6 échecs, marge -4,1 mm).
        self.assertGreater(it.Search.rank(rec(False, False, -0.5)), it.Search.rank(rec(False, True, -4.1)))
        # La pénalité de combustion ne touche pas le classement d'un refus...
        self.assertEqual(it.Search.rank(rec(False, False, -0.5, penalty=1.8))[3], -0.5)
        # ... mais départage bien deux acceptés également hors plage.
        self.assertGreater(it.Search.rank(rec(True, False, 0.5, penalty=0.2))[3],
                           it.Search.rank(rec(True, False, 0.5, penalty=1.8))[3])

    @unittest.skipUnless(HAVE_CQ, 'cadquery absent')
    def test_connected_volume_excludes_other_voids_and_handles_overlapping_solids(self):
        """Volumes analytiques : 16 mm³ fermés, 1 mm³ séparé, pièces occupantes recouvrantes."""
        import assembly
        import cadquery as cq
        V = cq.Vector
        cavity = cq.Solid.makeBox(2, 2, 4, V(1, 1, 1))
        separate = cq.Solid.makeBox(1, 1, 1, V(6, 6, 1))
        seed = V(2, 2, 2)
        for top in (8, 12):
            probe = cq.Solid.makeBox(10, 10, top)
            housing = probe.cut(cavity, separate)
            duplicate = cq.Solid.makeBox(1, 1, 1, V(8, 8, 1))
            measured = assembly.chamber_volume(probe, [housing, duplicate], seed, 0, top)
            self.assertAlmostEqual(measured['clearance_volume_cc'], 0.016, places=9)
            self.assertAlmostEqual(measured['excluded_disconnected_void_cc'], 0.001, places=9)
            # Même cavité ouverte vers la limite artificielle : aucun taux admissible.
            leak = cq.Solid.makeBox(0.5, 0.5, top, V(1.5, 1.5, 4))
            opened = assembly.chamber_volume(probe, [housing.cut(leak)], seed, 0, top)
            self.assertEqual(opened['status'], 'blocked_unsealed_chamber')
            self.assertIsNone(opened['clearance_volume_cc'])
            missing = assembly.chamber_volume(probe, [housing], V(9, 9, 2), 0, top)
            self.assertEqual(missing['status'], 'blocked_chamber_seed_not_unique')

    @unittest.skipUnless(HAVE_CQ, 'cadquery absent')
    def test_run_rejects_unmeasurable_compression_without_crashing(self):
        import assembly
        cad_result = {'all_brep_valid': True, 'head_solid_count': 1, 'brep_cross_check': [],
                      'compression': {'compression_ratio': None, 'clearance_volume_cc': None,
                                      'status': 'blocked_unsealed_chamber'}}
        with tempfile.TemporaryDirectory() as tmp:
            design = Path(tmp) / 'design.json'
            design.write_text(json.dumps({'selected': {'design': G1_DESIGN}}))
            with patch.object(assembly, 'export_all', return_value=cad_result):
                result = fv_run.run(Path(tmp) / 'out', extra_params=[EXTRA], fixed_design=design)
            self.assertFalse(result['accepted'])
            self.assertFalse(result['cad']['compression']['in_band'])
            self.assertIsNone(result['cad']['compression']['observed_calibration'])
            without_cad = fv_run.run(Path(tmp) / 'no-cad', cad=False, extra_params=[EXTRA], fixed_design=design)
            self.assertFalse(without_cad['accepted'])


class SparkPlugEnvelopeTests(unittest.TestCase):
    def setUp(self):
        resolved = ROOT / 'twins/m64-cylinder-head/evidence/g2-head-features-20260916/parameters-resolved.json'
        self.p = {k: row['value'] for k, row in json.loads(resolved.read_text()).items()}
        extra = json.loads((FV / 'params-plugs/spark_plug_envelope.json').read_text())
        for name, row in extra['parameters'].items():
            pv.verify_provenance(name, row, SRC)
            self.p[name] = row['value']

    def test_socket_uses_shared_geometry_checks_and_rejects_invalid_dimensions(self):
        p = self.p
        for k in layout.PLUGS:
            a, b, r = layout.cylinders(p)[f'plug_{k}_socket']
            o, d = layout.plug_opening(p, k)
            np.testing.assert_allclose(a, o + d * p['plug_thread_reach'])
            self.assertEqual(r, p['plug_socket_diameter'] / 2)
        names = {q['check']: q for q in chk.static_checks(p)}
        self.assertTrue(names['plug_vs_ports']['passed'])
        self.assertTrue(names['plug_vs_swept_valves']['passed'])
        colliding = {q['check']: q for q in chk.static_checks(dict(p, plug_tip_projection=50))}
        self.assertFalse(colliding['plug_vs_piston_tdc']['passed'])
        self.assertTrue(colliding['plug_vs_piston_tdc']['blocking'])
        for key, value in [('plug_thread_reach', -1), ('plug_thread_reach', 1000),
                           ('plug_tip_projection', math.nan), ('plug_socket_diameter', 18),
                           ('plug_seal_diameter', 12)]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                layout.cylinders(dict(p, **{key: value}))

    @unittest.skipUnless(HAVE_CQ, 'cadquery absent')
    def test_candidate_is_closed_window_invariant_but_missing_plug_is_rejected(self):
        import assembly
        import components as comp
        p = self.p
        head = comp.head(p)
        self.assertTrue(assembly.brep_valid(head))
        self.assertEqual(len(head.Solids()), 1)
        for k in layout.PLUGS:
            plug = comp.spark_plug(p, k)
            self.assertTrue(assembly.brep_valid(plug))
            self.assertEqual(len(plug.Solids()), 1)
            self.assertLess(abs(plug.intersect(head).Volume()), 1e-6)
            self.assertGreater(assembly.brep_distance(plug, comp.piston(p, 0)), p['min_wall'])
        values = [assembly.compression_ratio(p, margin) for margin in (2, 10)]
        for row in values:
            self.assertEqual(row['status'], 'synthetic_twin_estimate_not_m64_value')
            self.assertFalse(row['artificial_boundaries_reached'])
            self.assertFalse(row['radial_crevice_included'])
        self.assertAlmostEqual(values[0]['clearance_volume_cc'], values[1]['clearance_volume_cc'], places=6)
        self.assertAlmostEqual(values[0]['compression_ratio'], 7.35744, places=4)
        real_plug = comp.spark_plug
        def missing_second(p, k):
            s = real_plug(p, k)
            return s.translate((200, 0, 0)) if k == 2 else s
        with patch.object(comp, 'spark_plug', side_effect=missing_second):
            opened = assembly.compression_ratio(p)
        self.assertEqual(opened['status'], 'blocked_unsealed_chamber')
        self.assertIsNone(opened['compression_ratio'])


if __name__ == '__main__':
    unittest.main()
