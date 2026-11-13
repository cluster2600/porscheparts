"""Synthetic checks of the 935 flat-fan twin fitting helpers and the 993 F0
blade-angle conversion. No scan is needed: every case has a known answer."""

from __future__ import annotations

import importlib.util
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FAN_SOURCE = ROOT / "twins/935-horizontal-fan-cad-twin/source"
sys.path.insert(0, str(ROOT / "parts/993-eng-flat-fan-rotor-we43-f0-0001/source"))


def load_fan_module(name: str):
    """Load a module of the fan twin under a name of its own.

    fit_frame.py and score_twin.py also exist in the cylinder-head twin. Imported by their bare
    names they stay in sys.modules, and the other twin's tests then receive the wrong module.
    """

    spec = importlib.util.spec_from_file_location(f"flat_fan_twin_{name}", FAN_SOURCE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(FAN_SOURCE))           # for fan_common, which the fan modules import by name
try:
    fit_frame = load_fan_module("fit_frame")
    fit_blades = load_fan_module("fit_blades")
    score_twin = load_fan_module("score_twin")
finally:
    sys.path.remove(str(FAN_SOURCE))

import flat_fan_993_f0  # noqa: E402


class FrameFits(unittest.TestCase):
    def test_plane_fit_recovers_a_tilted_plane(self):
        rng = np.random.default_rng(1)
        xy = rng.uniform(-50, 50, (4000, 2))
        n_true = np.array([0.01, -0.02, 1.0])
        n_true /= np.linalg.norm(n_true)
        z = -(n_true[0] * xy[:, 0] + n_true[1] * xy[:, 1]) / n_true[2] + 7.0 + rng.normal(0, 0.05, 4000)
        n, mu, rms, k = fit_frame.plane_fit(np.c_[xy, z])
        self.assertLess(fit_frame.tilt_deg(n, n_true), 0.01)
        self.assertAlmostEqual(rms, 0.05, delta=0.01)

    def test_circle_fit_recovers_bore(self):
        rng = np.random.default_rng(2)
        t = rng.uniform(0, 2 * np.pi, 3000)
        xy = np.c_[1.5 + 11.31 * np.cos(t), -0.7 + 11.31 * np.sin(t)] + rng.normal(0, 0.05, (3000, 2))
        c, r, rms, k = fit_frame.circle_fit(xy, 10.0)
        self.assertAlmostEqual(r, 11.31, delta=0.01)
        self.assertLess(np.hypot(c[0] - 1.5, c[1] + 0.7), 0.01)


class BladeSection(unittest.TestCase):
    def test_section_of_a_known_thick_arc(self):
        # Camber line along a straight chord at 40 degrees, constant 6 mm thickness band.
        rng = np.random.default_rng(3)
        g = math.radians(40)
        d = np.array([math.cos(g), math.sin(g)])
        n = np.array([-d[1], d[0]])
        x = rng.uniform(0, 80, 20000)
        side = rng.choice([-3.0, 3.0], 20000)
        sz = np.outer(x, d) + np.outer(side, n) + rng.normal(0, 0.03, (20000, 2))
        sec = fit_blades.section(sz, np.zeros(len(sz), int))
        self.assertAlmostEqual(sec["stagger_deg"], 40.0, delta=0.3)
        mid = slice(5, -5)
        self.assertTrue(np.allclose(sec["upper"][mid] - sec["lower"][mid], 6.0, atol=0.2))


class Scorecard(unittest.TestCase):
    def test_summary_shares_and_outliers(self):
        d = np.array([0.05, 0.15, 0.4, 0.9, 5.0])
        a = np.ones(5)
        s = score_twin.summarise(d, a)
        self.assertAlmostEqual(s["within_0.1mm"], 0.2)
        self.assertAlmostEqual(s["within_0.5mm"], 0.6)
        self.assertAlmostEqual(s["unexplained_area_share"], 0.2)


class FlatFan993(unittest.TestCase):
    def test_metal_angles_of_a_straight_section_equal_its_stagger(self):
        x = np.asarray(json.loads((ROOT / "twins/935-horizontal-fan-cad-twin/params/blade.json").read_text())["chord_stations_x"])
        sec = {"upper_mm": list(np.full(len(x), 3.0)), "lower_mm": list(np.full(len(x), -3.0)), "chord_mm": 80.0,
               "stagger_from_tangential_deg": 35.0}
        stg, k1, k2 = flat_fan_993_f0.camber_metal_angles(sec, x)
        self.assertAlmostEqual(stg, 55.0)
        self.assertAlmostEqual(k1, 55.0, places=6)
        self.assertAlmostEqual(k2, 55.0, places=6)

    def test_recorded_comparison_is_consistent(self):
        ev = json.loads((ROOT / "parts/993-eng-flat-fan-rotor-we43-f0-0001/evidence/flat-fan-993-f0.json").read_text())
        for cfg in ("rotor_only", "rotor_and_stator"):
            e = ev[cfg]
            for rotor in (e["935_fitted_rotor"], e["new_rotor"]):
                self.assertAlmostEqual(rotor["flow_m3_s"], ev["duty"]["flow_m3_s"], places=6)
                self.assertEqual(rotor["stalled_station_count"], 0)
            self.assertLessEqual(e["new_rotor"]["tip_speed_m_s"], ev["envelope"]["max_tip_speed_m_s"])
            ratio = e["935_fitted_rotor"]["shaft_power_w"] / e["new_rotor"]["shaft_power_w"]
            self.assertAlmostEqual(e["comparison"]["power_saving_at_duty"], 1 - 1 / ratio, places=3)


if __name__ == "__main__":
    unittest.main()
