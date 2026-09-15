"""G1 4 soupapes / 2 bougies : provenance, contrôles, cinématique et itération (numpy seul) ; CAO en skip."""
import copy
import hashlib
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
import iterate as it  # noqa: E402
import kinematics as kin  # noqa: E402
import layout  # noqa: E402
import provenance as pv  # noqa: E402

EVIDENCE = ROOT / 'twins/m64-cylinder-head/evidence/g1-four-valve-20260914'

try:
    import cadquery  # noqa: F401
    HAVE_CQ = True
except ImportError:
    HAVE_CQ = False

SPEC = pv.load_spec()
SRC = pv.load_sources()
BASE, TRACES = pv.resolve_base(SPEC, SRC)


class ProvenanceTests(unittest.TestCase):
    def test_every_parameter_has_known_provenance_and_counts_sum(self):
        counts = pv.counts(SPEC)
        self.assertEqual(sum(counts.values()), len(SPEC['parameters']))
        self.assertEqual(counts['sourced_m64'], 2)
        self.assertEqual(counts['derived_by_iteration'], 0)
        self.assertEqual(set(layout.DERIVED), {n for n, i in SPEC['parameters'].items() if i['provenance'] == 'derived'})

    def test_modified_values_are_refused_for_each_source_kind(self):
        cases = {'bore_diameter': 'contract', 'register_diameter': 'scan', 'guide_protrusion': 'manual',
                 'intake_valve_head_diameter': 'Swindon', 'spring_installed_height': 'GSC5092'}
        for name, word in cases.items():
            spec = copy.deepcopy(SPEC)
            spec['parameters'][name]['value'] += 0.5
            with self.assertRaisesRegex(ValueError, word, msg=name):
                pv.resolve_base(spec, SRC)

    def test_unsourced_and_derived_rules(self):
        spec = copy.deepcopy(SPEC)
        spec['parameters']['min_ligament']['contract_path'] = 'documented_reference_dimensions.cylinder_bore.nominal'
        with self.assertRaisesRegex(ValueError, 'cannot cite'):
            pv.resolve_base(spec, SRC)
        spec = copy.deepcopy(SPEC)
        del spec['parameters']['min_wall']['hypothesis']
        with self.assertRaisesRegex(ValueError, 'hypothesis'):
            pv.resolve_base(spec, SRC)
        spec = copy.deepcopy(SPEC)
        spec['parameters']['roof_ridge_height']['value'] = 20.0
        with self.assertRaisesRegex(ValueError, 'must not store'):
            pv.resolve_base(spec, SRC)
        spec = copy.deepcopy(SPEC)
        spec['parameters']['min_wall']['provenance'] = 'derived_by_iteration'
        with self.assertRaisesRegex(ValueError, 'not allowed'):
            pv.resolve_base(spec, SRC)

    def test_design_space_protects_sourced_values(self):
        space = pv.load_design_space()
        with self.assertRaisesRegex(ValueError, 'requires stage'):
            pv.validate_design(SPEC, space, {'bore_diameter': 101.0}, 1)
        pv.validate_design(SPEC, space, {'bore_diameter': 101.0}, 2)
        with self.assertRaisesRegex(ValueError, 'outside'):
            pv.validate_design(SPEC, space, {'intake_axis_angle': 50.0}, 1)
        with self.assertRaisesRegex(ValueError, 'not an admissible'):
            pv.validate_design(SPEC, space, {'register_diameter': 110.0}, 3)
        for var in space['variables']:
            prov = SPEC['parameters'][var['name']]['provenance']
            if prov in ('sourced_m64', 'stock_993_2v_manual', 'supplier_swindon', 'supplier_gsc5092'):
                self.assertGreater(var['stage'], 1, var['name'])


class GeometryTests(unittest.TestCase):
    def test_derivations(self):
        p = layout.derive(BASE)
        self.assertAlmostEqual(p['intake_valve_y'], 40 / 2 + p['min_ligament'] / 2)
        self.assertAlmostEqual(p['intake_axis_angle'], BASE['scan_valve_1_axis_angle'])
        self.assertAlmostEqual(p['plug_1_tilt'], 90 - BASE['plug_1_angle_to_plane'])
        # axe bougie 1 du scan converti vers le haut : (-uy, -ux) -> azimut ~154,5°
        self.assertAlmostEqual(p['plug_1_azimuth'], math.degrees(math.atan2(0.2042, -0.4282)), places=3)
        self.assertAlmostEqual(p['intake_spring_seat_axial'], 110.1 - 40 - p['valve_tip_allowance'])
        fixed = layout.derive(BASE, {'intake_axis_angle': 20.0})
        self.assertEqual(fixed['intake_axis_angle'], 20.0)

    def test_segment_distance_matches_brute_force(self):
        rng = np.random.default_rng(1)
        t = np.linspace(0, 1, 401)
        for _ in range(25):
            a, b, c, d = rng.normal(size=(4, 3)) * 10
            s1 = a + np.outer(t, b - a)
            s2 = c + np.outer(t, d - c)
            brute = np.min(np.linalg.norm(s1[:, None] - s2[None], axis=2))
            self.assertLessEqual(layout.segment_distance(a, b, c, d), brute + 1e-9)
            self.assertAlmostEqual(layout.segment_distance(a, b, c, d), brute, delta=0.1)

    def test_plug_opening_lies_on_roof(self):
        p = layout.derive(BASE)
        for k in layout.PLUGS:
            o, _ = layout.plug_opening(p, k)
            self.assertAlmostEqual(o[2], layout.roof_z(p, o[0]), delta=1e-6)


class KinematicsTests(unittest.TestCase):
    def setUp(self):
        self.p = layout.derive(BASE)

    def test_piston_crown_tdc_bdc(self):
        z = kin.piston_crown_z(self.p, np.array([0.0, 180.0, 360.0]))
        top = self.p['register_depth'] - self.p['deck_clearance']
        self.assertAlmostEqual(z[0], top)
        self.assertAlmostEqual(z[1], top - self.p['crank_stroke'])
        self.assertAlmostEqual(z[2], top)

    def test_valve_piston_gap_flat_crown_by_hand(self):
        p = dict(self.p, piston_pocket_depth=0.0, piston_bowl_depth=0.0)
        lift = np.array([3.0])
        phi = np.array([20.0])
        c, u = layout.head_centre(p, 'intake', 1), layout.axis_up(p, 'intake')
        r = p['intake_valve_head_diameter'] / 2
        lowest = c[2] - r * math.sqrt(1 - u[2] ** 2) - u[2] * 3.0
        expected = lowest - kin.piston_crown_z(p, phi)[0]
        self.assertAlmostEqual(kin.valve_piston_gap(p, 'intake', 1, phi, lift)[0], expected, places=6)

    def test_pair_distance_vectorised_equals_direct_and_detects_penetration(self):
        p = self.p
        la, lb = np.array([0.0, 4.0, 11.5]), np.array([0.0, 2.0, 9.6])
        d = kin.pair_distance_over_cycle(p, ('intake', 1), ('exhaust', 1), la, lb)
        rings = (1.0, 0.75, 0.5, 0.25)
        for k in range(3):
            pa, _, ua, _ = kin.head_cloud(p, 'intake', 1, rings=rings, n=36)
            pb, _, ub, _ = kin.head_cloud(p, 'exhaust', 1, rings=rings, n=36)
            direct = np.min(np.linalg.norm((pa - ua * la[k])[:, None] - (pb - ub * lb[k])[None], axis=2))
            if d[k] > 0:
                self.assertAlmostEqual(d[k], direct, places=6)
        crash = dict(p, intake_valve_x=-5.0, exhaust_valve_x=5.0)
        self.assertEqual(kin.pair_distance_over_cycle(crash, ('intake', 1), ('exhaust', 1), np.array([11.5]),
                                                      np.array([9.6]))[0], 0.0)

    def test_lift_table_uses_v1_law_and_swindon_lift(self):
        phi, lifts = kin.lift_table(self.p, 1.0)
        self.assertAlmostEqual(lifts['intake'].max(), 11.5, delta=0.01)
        self.assertAlmostEqual(lifts['exhaust'].max(), 9.6, delta=0.01)


class ChecksTests(unittest.TestCase):
    def test_935_start_fails_and_is_reported_not_adjusted(self):
        p = layout.derive(BASE)
        before = dict(p)
        checks, summary = chk.evaluate(p, 2.0, force_cycle=True)
        self.assertEqual(p, before)
        self.assertFalse(summary['accepted'])
        failed = set(summary['blocking_failed'])
        self.assertTrue({'ligament_plug_1_to_seats', 'ligament_plug_2_to_seats', 'stud_vs_spring_pockets'} <= failed)
        names = {c['check'] for c in checks}
        for required in ('valve_valve_clearance_cycle', 'valve_piston_intake', 'spring_coil_bind_reserve',
                         'plug_vs_studs', 'plug_vs_ports', 'plug_vs_spring_pockets', 'ligament_plug_plug',
                         'stud_vs_ports', 'valve_heads_within_bore'):
            self.assertIn(required, names)
        for c in checks:
            if c['passed'] is None:
                self.assertEqual(c['status'], 'not_computable')
                self.assertFalse(c['blocking'])
            else:
                self.assertEqual(c['passed'], c['slack'] >= -1e-9)
        self.assertIn('inter_cylinder_bridge', summary['not_computable'])

    def test_large_bore_checks_become_limiting(self):
        p = layout.derive(dict(BASE, bore_diameter=106.0))
        by = {c['check']: c for c in chk.static_checks(p)}
        od = 106.0 + 2 * p['liner_min_spigot_wall'] + 2 * p['liner_spigot_radial_clearance']
        self.assertAlmostEqual(by['register_vs_required_liner_od']['limit'], od, places=3)
        stud_free = 2 * (math.hypot(p['stud_span_x'] / 2, p['stud_span_y'] / 2) - p['stud_hole_diameter'] / 2)
        self.assertAlmostEqual(by['liner_od_vs_stud_holes']['value'], stud_free, places=3)
        self.assertFalse(by['liner_od_vs_stud_holes']['passed'])
        self.assertAlmostEqual(chk.displacement_cc(100.0, 76.4), 3600.3, places=1)

    def test_coil_bind_uses_published_gsc_values(self):
        c = [x for x in chk.static_checks(layout.derive(BASE)) if x['check'] == 'spring_coil_bind_reserve'][0]
        self.assertAlmostEqual(c['value'], 40.0 - 11.5 - 24.18, places=3)


class IterationTests(unittest.TestCase):
    def test_small_search_is_deterministic_and_logs_every_trial(self):
        space = pv.load_design_space()
        space = dict(space, budget=dict(space['budget'], grid_samples=3, local_evaluations=4, search_sweep_step_deg=6.0))
        runs = []
        for _ in range(2):
            s = it.Search(SPEC, space, BASE)
            best = s.run(max_stage=1)
            runs.append((best, s.history))
        self.assertEqual(json.dumps(runs[0][1], sort_keys=True), json.dumps(runs[1][1], sort_keys=True))
        bounds = {v['name']: (v['lower'], v['upper']) for v in space['variables']}
        for rec in runs[0][1]:
            self.assertEqual(rec['stage'], 1)
            for name, value in rec['design'].items():
                self.assertTrue(bounds[name][0] - 1e-9 <= value <= bounds[name][1] + 1e-9)
            self.assertIn('limiting_check', rec)
        self.assertEqual(runs[0][1][0]['phase'], 'base_935_start')


class BoreSweepTests(unittest.TestCase):
    def test_edges_read_the_result_of_their_own_stud_pattern(self):
        import bore_sweep

        def res(ok, check, slack):
            return {'accepted': ok, 'limiting_check': check, 'min_slack': slack}
        rows = [{'bore_diameter': 102.7, 'stud_pattern_935': res(True, 'a', 0.1)},
                {'bore_diameter': 103.0, 'stud_pattern_935': res(False, 'liner_od_vs_stud_holes', -0.17),
                 'stud_pattern_free': res(True, 'valve_piston_intake', 0.32)},
                {'bore_diameter': 106.0, 'stud_pattern_935': res(False, 'liner_od_vs_stud_holes', -3.2),
                 'stud_pattern_free': res(False, 'register_vs_required_liner_od', -0.78)}]
        e = bore_sweep.edges(rows)
        self.assertEqual(e['maximal_passing_bore_stud_935']['first_failing_bore'], 103.0)
        self.assertEqual(e['maximal_passing_bore_stud_935']['limiting_check'], 'liner_od_vs_stud_holes')
        self.assertEqual(e['maximal_passing_bore_any']['bore_diameter'], 103.0)
        self.assertEqual(e['maximal_passing_bore_any']['limiting_check'], 'register_vs_required_liner_od')

    def test_recorded_sweep_is_consistent(self):
        path = EVIDENCE / 'bore-sweep.json'
        if not path.exists():
            self.skipTest('balayage non généré')
        import bore_sweep
        r = json.loads(path.read_text())
        self.assertIs(r['manufacturing_authorized'], False)
        self.assertEqual({k: v for k, v in r.items() if k.startswith(('minimal', 'maximal'))}, bore_sweep.edges(r['rows']))
        for row in r['rows']:
            expected = 'exploratory_beyond_sources' if row['bore_diameter'] > r['documented_upper'] else 'documented_swindon'
            self.assertEqual(row['bore_band'], expected)
            free = row.get('stud_pattern_free')
            if free:
                self.assertFalse(row['stud_pattern_935']['accepted'])
                self.assertIn('non compatibles M64', free['consequence'])

    def test_sweep_flags_exploratory_band_and_stud_consequence(self):
        import bore_sweep
        small = {'grid_samples': 2, 'local_evaluations': 2, 'search_sweep_step_deg': 8.0, 'final_sweep_step_deg': 4.0}
        res = bore_sweep.sweep(SPEC, pv.load_design_space(), bores=[100.0, 106.0], budget_override=small)
        rows = {r['bore_diameter']: r for r in res['rows']}
        self.assertEqual(rows[100.0]['bore_band'], 'documented_swindon')
        self.assertEqual(rows[106.0]['bore_band'], 'exploratory_beyond_sources')
        self.assertEqual(rows[106.0]['provenance'], 'derived_by_iteration')
        self.assertAlmostEqual(rows[106.0]['displacement_cc'], chk.displacement_cc(106.0, 76.4), places=0)
        self.assertEqual(res['inter_cylinder_bridge'], 'not_computable')
        for r in res['rows']:
            if not r['stud_pattern_935']['accepted']:
                self.assertIn('stud_pattern_free', r)
                self.assertIn('non compatibles M64', r['stud_pattern_free']['consequence'])
        with self.assertRaisesRegex(ValueError, 'outside'):
            bore_sweep.sweep(SPEC, pv.load_design_space(), bores=[107.0], budget_override=small)


@unittest.skipUnless((EVIDENCE / 'manifest.json').exists(), 'évidence non générée')
class EvidenceTests(unittest.TestCase):
    def test_manifest_is_consistent_with_inputs(self):
        m = json.loads((EVIDENCE / 'manifest.json').read_text())
        self.assertIs(m['master_geometry'], False)
        self.assertIs(m['manufacturing_authorized'], False)
        self.assertEqual(sum(m['provenance_counts'].values()), len(SPEC['parameters']))
        for rel, digest in m['sha256']['inputs'].items():
            self.assertEqual(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), digest, rel)
        for name, digest in m['sha256']['outputs'].items():
            self.assertEqual(hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(m['iteration']['sourced_values_modified'], [])
        resolved = json.loads((EVIDENCE / 'parameters-resolved.json').read_text())
        for name, value in m['iteration']['design_variables'].items():
            self.assertEqual(resolved[name]['provenance'], 'derived_by_iteration')
            self.assertEqual(resolved[name]['trial'], m['iteration']['best_trial'])

    def test_recorded_best_reproduces_with_numpy_only(self):
        m = json.loads((EVIDENCE / 'manifest.json').read_text())
        space = pv.load_design_space()
        p = layout.derive(BASE, it.mirror(m['iteration']['design_variables'], space))
        _, summary = chk.evaluate(p, space['budget']['final_sweep_step_deg'], force_cycle=True)
        self.assertEqual(summary['accepted'], m['final_summary']['accepted'])
        self.assertAlmostEqual(summary['min_slack'], m['final_summary']['min_slack'], places=3)


@unittest.skipUnless(HAVE_CQ, 'cadquery indisponible')
class CadTests(unittest.TestCase):
    def test_head_valid_single_solid_and_brep_distance_not_below_analytic(self):
        import assembly
        import components as comp
        p = layout.derive(BASE)
        head = comp.head(p)
        self.assertTrue(assembly.brep_valid(head))
        self.assertEqual(len(head.Solids()), 1)
        q = dict(p, piston_pocket_depth=0.0, piston_bowl_depth=0.0)
        phi, lift = np.array([10.0]), np.array([2.5])
        analytic = kin.valve_piston_gap(q, 'intake', 1, phi, lift)[0]
        brep = assembly.brep_distance(comp.valve(q, 'intake', 1, 2.5), comp.piston(q, 10.0))
        self.assertAlmostEqual(brep, analytic, delta=0.05)


if __name__ == '__main__':
    unittest.main()
