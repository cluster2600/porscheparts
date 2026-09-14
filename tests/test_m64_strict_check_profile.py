import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source'
sys.path.insert(0, str(SOURCE))
import profile_strict_check as prof

EVIDENCE = Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/evidence'


def row(valid=True, faulty=False, solids=1):
    return {'brepcheck_exact': {'status': 'done', 'result': {'valid': valid}},
            'brepcheck_default': {'status': 'done', 'result': {'valid': valid}},
            'bop_full': {'status': 'done', 'result': {'has_faulty': faulty}},
            'tolerances': {'status': 'done', 'result': {'solids': solids}}}


class VerdictTests(unittest.TestCase):
    def test_timeout_is_incomplete_never_pass(self):
        rows = row(); rows['bop_full'] = {'status': 'timeout'}
        self.assertEqual(prof.verdict(rows), 'incomplete')
        self.assertEqual(prof.fast_verdict(rows), 'incomplete')

    def test_missing_phase_is_incomplete(self):
        rows = row(); del rows['brepcheck_exact']
        self.assertEqual(prof.verdict(rows), 'incomplete')

    def test_fail_reasons(self):
        self.assertEqual(prof.verdict(row()), 'pass')
        for bad in (row(valid=False), row(faulty=True), row(solids=12)):
            self.assertEqual(prof.verdict(bad), 'fail')

    def test_reconcile_reports_reread_and_source_delta(self):
        def vol(v, r):
            return {'volume_adaptive_1e-11': {'status': 'done', 'result': {
                        'volume': v, 'error_estimate': 0., 'solids': [{'volume': v}]}},
                    'write_reread': {'status': 'done', 'result': {'reread_volume_adaptive_1e-11': r}}}
        out = prof.reconcile({'source': vol(10., 10.), 'candidate': vol(11., 11.5)})
        self.assertEqual(out['candidate']['minus_source'], 1.)
        self.assertEqual(out['candidate']['reread_minus_in_memory'], .5)

    def test_reconcile_missing_volume_stays_none(self):
        out = prof.reconcile({'source': {}})
        self.assertIsNone(out['source']['volume_adaptive_1e-11'])
        self.assertIsNone(out['source']['minus_source'])


@unittest.skipUnless(importlib.util.find_spec('OCP'), 'OCP native runtime required')
class NativeProfileTests(unittest.TestCase):
    PHASES = ('brepcheck_exact', 'brepcheck_default', 'bop_full', 'tolerances')

    def profile(self, shapes, synthetic=None, nurbs=False, timeout=120.):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp); labelled = dict(shapes)
            if synthetic is not None:
                paths, builds = prof.synthetic_witness(tmp, synthetic, nurbs)
                self.assertTrue(all(b['done'] for b in builds.values()))
                labelled.update(paths)
            return {k: prof.supervise(p, self.PHASES, timeout, tmp) for k, p in labelled.items()}

    def assert_same_verdict(self, profiles):
        for label, rows in profiles.items():
            with self.subTest(label=label):
                self.assertNotEqual(prof.verdict(rows), 'incomplete')
                self.assertEqual(prof.verdict(rows), prof.fast_verdict(rows))

    def test_external_timeout_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            step = EVIDENCE/'four-valve-design-v2-20260907/closed.step'
            rows = prof.supervise(step, ('bop_full',), 0.05, Path(tmp))
        self.assertEqual(rows['bop_full']['status'], 'timeout')
        self.assertEqual(prof.verdict(rows), 'incomplete')

    def test_analytic_witness_same_verdict(self):
        profiles = self.profile({}, synthetic=0.1)
        self.assertEqual({prof.verdict(r) for r in profiles.values()}, {'pass'})
        self.assert_same_verdict(profiles)

    def test_nurbs_witness_brepcheck_default_is_not_equivalent(self):
        profiles = self.profile({}, synthetic=0.1, nurbs=True)
        # Verdict global identique (BOP rejette), mais BRepCheck non exact
        # accepte ce que la méthode exacte refuse : substitution rejetée.
        self.assert_same_verdict(profiles)
        rows = profiles['default']
        self.assertFalse(rows['brepcheck_exact']['result']['valid'])
        self.assertTrue(rows['brepcheck_default']['result']['valid'])

    def test_gauss_default_volume_is_not_a_reconciliation_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, _ = prof.synthetic_witness(Path(tmp), 0.1, True)
            shape = prof.read_shape(paths['source'])
            adaptive = prof.volume(shape, 1e-11)['volume']; gauss = prof.volume(shape, None)['volume']
        self.assertGreater(abs(gauss-adaptive)/adaptive, 1e-3)

    def test_public_steps_same_verdict(self):
        shapes = {name: EVIDENCE/folder/'closed.step' for name, folder in
                  (('v1', 'four-valve-design-20260907'), ('v2', 'four-valve-design-v2-20260907'))}
        shapes['v2_simul'] = EVIDENCE/'four-valve-design-v2-20260907/simultaneous_100pct.step'
        profiles = self.profile(shapes)
        # 12 solides disjoints dans chaque STEP : le contrôle mono-solide rejette.
        self.assertEqual({prof.verdict(r) for r in profiles.values()}, {'fail'})
        self.assert_same_verdict(profiles)


if __name__ == '__main__':
    unittest.main()
