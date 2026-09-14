#!/usr/bin/env python3
"""Contre-calculs indépendants du module V1 distribution M64 (paramètres supposés)."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
from dataclasses import replace
from pathlib import Path
import sys
import unittest

import numpy as np
from scipy.integrate import cumulative_trapezoid

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "twins/m64-cylinder-head/source/valvetrain/valvetrain.py"
EVIDENCE = ROOT / "twins/m64-cylinder-head/evidence/valvetrain-v1"
spec = importlib.util.spec_from_file_location("m64_valvetrain_v1", MODULE)
vt = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = vt
spec.loader.exec_module(vt)


def setup(kind="intake", params=None, hot=False):
    params = params or vt.default_parameters()
    vp, eng = params[kind], params["engine"]
    spring = vt.spring_properties(vp, eng)
    return params, vp, eng, vt.CamLaw.from_params(vp, hot=hot), spring, vt.effective_mass(vp, spring)


class ProvenanceTests(unittest.TestCase):
    def test_every_parameter_has_status_and_justification(self):
        params = vt.default_parameters()
        self.assertEqual(vt.check_provenance(params), [])
        for kind in ("intake", "exhaust"):
            for name in ("valve_mass_kg", "spring_preload_N", "main_event_duration_crank_deg",
                         "contact_stiffness_N_per_mm", "lash_cold_mm", "piston_gap_at_tdc_closed_mm"):
                self.assertEqual(params[kind][name]["status"], "assumed")
            self.assertNotEqual(params[kind]["max_lift_mm"]["status"], "sourced_reference")

    def test_claim_detector_rejects_m64_claim(self):
        params = vt.default_parameters()
        params["intake"]["valve_mass_kg"]["justification"] = "Valeur M64 d'origine"
        self.assertTrue(vt.check_provenance(params))


class CamLawTests(unittest.TestCase):
    def setUp(self):
        _, _, _, self.law, _, _ = setup()
        self.phi = np.linspace(0, 4 * math.pi, 200001)

    def test_analytic_derivatives_match_numerical_integration(self):
        c = [self.law.cam_derivatives(self.phi, k) for k in range(4)]
        for k in range(3):
            integrated = c[k][0] + cumulative_trapezoid(c[k + 1], self.phi, initial=0)
            scale = np.abs(c[k]).max()
            # le jerk (k+1=3) est discontinu aux raccords : erreur trapèze O(h) tolérée
            self.assertLess(np.abs(integrated - c[k]).max() / scale, 1e-6 if k < 2 else 1e-3, k)

    def test_c2_continuity_and_bounded_jerk(self):
        acc = self.law.cam_derivatives(self.phi, 2)
        dphi = self.phi[1] - self.phi[0]
        self.assertLess(np.abs(np.diff(acc)).max(), 1.1 * np.abs(self.law.cam_derivatives(self.phi, 3)).max() * dphi)
        lift = self.law.cam_derivatives(self.phi)
        self.assertAlmostEqual(lift.max(), self.law.max_lift_m + self.law.ramp_height_m, places=9)
        self.assertEqual(lift[0], lift[-1])

    def test_monotone_flanks_and_c_domain(self):
        v = self.law.cam_derivatives(self.phi, 1)
        x = np.mod(self.phi - self.law.centreline_rad + 2 * math.pi, 4 * math.pi) - 2 * math.pi
        self.assertTrue((v[x < 0] >= -1e-12).all() and (v[x > 0] <= 1e-12).all())
        with self.assertRaises(ValueError):
            vt.main_poly(3.0)

    def test_lash_within_ramp_and_hot_seating(self):
        ev = self.law.open_close_events(6500)
        self.assertTrue(ev["lash_within_ramp"])
        self.assertLess(ev["opening_velocity_m_s"], 0.6)
        big = replace(self.law, lash_m=self.law.ramp_height_m * 1.1)
        self.assertFalse(big.open_close_events(6500)["lash_within_ramp"])


class SpringAndMarginTests(unittest.TestCase):
    def test_spring_rate_hand_calculation(self):
        _, vp, eng, _, spring, _ = setup()
        G, d, D, n = 79.3e9, 3.8e-3, 22e-3, 5.0
        self.assertAlmostEqual(spring["rate_N_m"], G * d ** 4 / (8 * D ** 3 * n), delta=1e-6)
        self.assertAlmostEqual(spring["solid_length_m"], 7 * d)
        self.assertAlmostEqual(spring["coil_bind_clearance_m"], 40e-3 - 11.5e-3 - 7 * d)

    def test_coil_bind_detected(self):
        params = vt.default_parameters()
        params["intake"]["spring_installed_length_mm"]["value"] = 37.0
        self.assertFalse(vt.spring_properties(params["intake"], params["engine"])["coil_bind_ok"])

    def test_margin_scales_inverse_square_and_float_rpm_bisection(self):
        _, _, _, law, spring, m = setup()
        m1 = vt.spring_margin(law, spring, m, 3000)["min_margin"]
        m2 = vt.spring_margin(law, spring, m, 6000)["min_margin"]
        self.assertAlmostEqual(m1 / m2, 4.0, places=9)
        n_float = vt.float_rpm_quasistatic(law, spring, m)
        lo, hi = 1000.0, 30000.0
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if vt.spring_margin(law, spring, m, mid)["min_margin"] > 1 else (lo, mid)
        self.assertAlmostEqual(n_float, lo, delta=1e-3)

    def test_heavier_valve_floats_earlier(self):
        params = vt.default_parameters()
        _, _, _, law, spring, m = setup(params=params)
        base = vt.float_rpm_quasistatic(law, spring, m)
        self.assertAlmostEqual(vt.float_rpm_quasistatic(law, spring, 1.21 * m), base / 1.1, delta=1e-6)


class PistonTests(unittest.TestCase):
    def test_slider_crank_limits(self):
        s = vt.piston_drop(np.array([0, math.pi]), 76.4e-3, 127e-3)
        self.assertAlmostEqual(s[0], 0.0); self.assertAlmostEqual(s[1], 76.4e-3)
        phi = np.linspace(0, 2 * math.pi, 50)
        r, l = 38.2e-3, 1.0  # développement en r/l : r(1-cos) + r² sin²/(2l), reste ≤ r⁴/(8l³)
        approx = r * (1 - np.cos(phi)) + r * r * np.sin(phi) ** 2 / (2 * l)
        self.assertLess(np.abs(vt.piston_drop(phi, 2 * r, l) - approx).max(), r ** 4 / (8 * l ** 3) * 1.01)

    def test_interference_detected_when_gap_small(self):
        params, vp, eng, law, _, _ = setup()
        vp["piston_gap_at_tdc_closed_mm"]["value"] = 0.5
        r = vt.interference(law, vp, eng, advance_deg=10)
        self.assertTrue(r["contact"])
        params2, vp2, eng2, law2, _, _ = setup()
        self.assertFalse(vt.interference(law2, vp2, eng2)["contact"])

    def test_gap_hand_point(self):
        _, vp, eng, law, _, _ = setup()
        phi = np.array([math.radians(30)])
        lift = law.valve_lift(phi)
        r, l = 38.2e-3, 127e-3
        s = r * (1 - math.cos(phi[0])) + l - math.sqrt(l * l - (r * math.sin(phi[0])) ** 2)
        expected = 6e-3 + s - lift[0] * math.cos(math.radians(8))
        self.assertAlmostEqual(vt.piston_valve_gap(phi, lift, vp, eng)[0], expected, places=12)


class SdofTests(unittest.TestCase):
    def test_harmonic_limit_and_energy(self):
        m, k, A = 0.1, 4e4, 1e-3
        w = math.sqrt(k / m); T = 2 * math.pi / w
        x, v = vt.free_oscillation(m, k, A, 5 * T, 20000)
        t = np.linspace(0, 5 * T, 20001)
        self.assertLess(np.abs(x - A * np.cos(w * t)).max(), 1e-7)
        energy = 0.5 * m * v ** 2 + 0.5 * k * x[-1] ** 2
        self.assertAlmostEqual(energy / (0.5 * k * A * A), 1.0, places=6)

    def test_low_rpm_follows_kinematics(self):
        _, vp, _, law, spring, m = setup(hot=True)
        s = vt.simulate_sdof(law, vp, spring, m, 2000, cycles=2, steps_per_cycle=7200)
        self.assertLess(s["max_separation_mm"], 0.01)
        self.assertLess(s["max_bounce_mm"], 0.01)
        open_ = s["y_m"] > 1e-3
        self.assertLess(np.abs(s["x_m"][open_] - s["y_m"][open_]).max(), 0.2e-3)

    def test_weak_spring_floats_in_dynamics(self):
        params = vt.default_parameters()
        params["intake"]["spring_preload_N"]["value"] = 60.0
        _, vp, _, law, spring, m = setup(params=params, hot=True)
        n_float = vt.float_rpm_quasistatic(law, spring, m)
        s = vt.simulate_sdof(law, vp, spring, m, 1.3 * n_float, cycles=2, steps_per_cycle=7200)
        self.assertGreater(s["max_separation_mm"], 0.05)


class EvidenceTests(unittest.TestCase):
    def test_results_fingerprints_and_status(self):
        path = EVIDENCE / "valvetrain-v1-results.json"
        if not path.exists():
            self.skipTest("run_study.py non exécuté")
        res = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(res["status"], "sensitivity_study_not_qualification")
        self.assertFalse(res["m64_cam_data_used"]); self.assertFalse(res["bench_correlation"])
        for name, digest in res["fingerprints_sha256"].items():
            candidates = [EVIDENCE / name, MODULE.parent / name]
            f = next(p for p in candidates if p.exists())
            self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(), digest, name)


if __name__ == "__main__":
    unittest.main()
