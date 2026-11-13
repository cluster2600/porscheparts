"""The laminate failure post-processor against references it does not produce.

Every expected value here comes from a second route: a closed form, an explicit
textbook formula coded separately, a numerical quadrature, or a brute-force
search of Puck's fracture plane. The material numbers are those of the worked
graphite/epoxy examples in Kaw, *Mechanics of Composite Materials*, 2nd ed.
(2006); they are example inputs, not data for any part.
"""
import json
import math
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/laminate_failure.py"
LAM = runpy.run_path(str(SCRIPT))

STIFFNESS = {"E1": 181e3, "E2": 10.3e3, "G12": 7.17e3, "nu12": 0.28}          # MPa
STRENGTH = {"Xt": 1500.0, "Xc": 1500.0, "Yt": 40.0, "Yc": 246.0, "S": 68.0}    # MPa
PUCK = {"puck_p_plus": 0.30, "puck_p_minus": 0.25}                             # example values only


def ply(angle, thickness=0.125, **extra):
    return {"stiffness": STIFFNESS, "strength": STRENGTH, "angle_deg": angle, "thickness": thickness, **extra}


def explicit_qbar(angle_deg):
    """The rotated stiffness from the explicit fourth-power formulas, coded independently of the module."""
    Q = LAM["reduced_stiffness"](**STIFFNESS)
    q11, q12, q22, q66 = Q[0, 0], Q[0, 1], Q[1, 1], Q[2, 2]
    c, s = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    b11 = q11 * c ** 4 + 2 * (q12 + 2 * q66) * s * s * c * c + q22 * s ** 4
    b22 = q11 * s ** 4 + 2 * (q12 + 2 * q66) * s * s * c * c + q22 * c ** 4
    b12 = (q11 + q22 - 4 * q66) * s * s * c * c + q12 * (s ** 4 + c ** 4)
    b66 = (q11 + q22 - 2 * q12 - 2 * q66) * s * s * c * c + q66 * (s ** 4 + c ** 4)
    b16 = (q11 - q12 - 2 * q66) * s * c ** 3 + (q12 - q22 + 2 * q66) * s ** 3 * c
    b26 = (q11 - q12 - 2 * q66) * s ** 3 * c + (q12 - q22 + 2 * q66) * s * c ** 3
    return np.array([[b11, b12, b16], [b12, b22, b26], [b16, b26, b66]])


def puck_fracture_plane_search(s2, t21, p_plus, p_minus):
    """Puck's action-plane criterion maximised numerically over the fracture angle."""
    S, Yt, Yc = STRENGTH["S"], STRENGTH["Yt"], STRENGTH["Yc"]
    Ra = S / (2 * p_minus) * (math.sqrt(1 + 2 * p_minus * Yc / S) - 1)
    p_tt = p_minus * Ra / S
    theta = np.linspace(-math.pi / 2, math.pi / 2, 40001)
    sn, tnt, tn1 = s2 * np.cos(theta) ** 2, -s2 * np.sin(theta) * np.cos(theta), t21 * np.cos(theta)
    shear = tnt ** 2 + tn1 ** 2
    cos2 = np.divide(tnt ** 2, shear, out=np.zeros_like(shear), where=shear > 0)
    sin2 = np.where(shear > 0, 1 - cos2, 0.0)
    tension = p_tt / Ra * cos2 + p_plus / S * sin2
    compression = p_tt / Ra * cos2 + p_minus / S * sin2
    base = (tnt / Ra) ** 2 + (tn1 / S) ** 2
    exposure = np.where(sn >= 0, np.sqrt(((1 / Yt - tension) * sn) ** 2 + base) + tension * sn,
                        np.sqrt(base + (compression * sn) ** 2) + compression * sn)
    return float(exposure.max())


class LaminationTheoryTests(unittest.TestCase):
    def test_stress_rotation_matches_the_double_angle_form(self):
        sx, sy, txy, angle = 2.0, -3.0, 4.0, 60.0
        two = math.radians(2 * angle)
        expected = [(sx + sy) / 2 + (sx - sy) / 2 * math.cos(two) + txy * math.sin(two),
                    (sx + sy) / 2 - (sx - sy) / 2 * math.cos(two) - txy * math.sin(two),
                    -(sx - sy) / 2 * math.sin(two) + txy * math.cos(two)]
        got = LAM["to_material_axes"]([sx, sy, txy], angle)
        np.testing.assert_allclose(got, expected, rtol=1e-12)
        np.testing.assert_allclose(got, [1.714, -2.714, -4.165], atol=5e-4)

    def test_rotated_stiffness_matches_the_explicit_formulas(self):
        Q = LAM["reduced_stiffness"](**STIFFNESS)
        for angle in (0, 17, 30, 45, -45, 60, 90):
            np.testing.assert_allclose(LAM["rotated_stiffness"](Q, angle), explicit_qbar(angle), rtol=1e-10, atol=1e-6)

    def test_abd_equals_through_thickness_quadrature(self):
        layup = [ply(a, t) for a, t in ((0, 0.2), (30, 0.125), (-45, 0.3), (90, 0.15))]
        A, B, D = LAM["abd"](layup)
        total = sum(p["thickness"] for p in layup)
        edges = np.cumsum([0.0] + [p["thickness"] for p in layup]) - total / 2
        a, b, d = np.zeros((3, 3)), np.zeros((3, 3)), np.zeros((3, 3))
        nodes, weights = np.polynomial.legendre.leggauss(4)             # exact for z^2 within a ply
        for p, lo, hi in zip(layup, edges[:-1], edges[1:]):
            qbar = explicit_qbar(p["angle_deg"])
            for x, w in zip(nodes, weights):
                z, dz = (hi + lo) / 2 + x * (hi - lo) / 2, w * (hi - lo) / 2
                a, b, d = a + qbar * dz, b + qbar * z * dz, d + qbar * z * z * dz
        for got, expected in ((A, a), (B, b), (D, d)):
            np.testing.assert_allclose(got, expected, rtol=1e-10, atol=1e-8)

    def test_quasi_isotropic_laminate_has_the_invariant_stiffness(self):
        layup = [ply(a) for a in (0, 45, -45, 90, 90, -45, 45, 0)]
        A, B, _ = LAM["abd"](layup)
        Q = LAM["reduced_stiffness"](**STIFFNESS)
        q11, q12, q22, q66 = Q[0, 0], Q[0, 1], Q[1, 1], Q[2, 2]
        u1, u4, u5 = (3 * q11 + 3 * q22 + 2 * q12 + 4 * q66) / 8, (q11 + q22 + 6 * q12 - 4 * q66) / 8, \
            (q11 + q22 - 2 * q12 + 4 * q66) / 8
        np.testing.assert_allclose(A, np.array([[u1, u4, 0], [u4, u1, 0], [0, 0, u5]]) * 1.0, rtol=1e-10, atol=1e-7)
        np.testing.assert_allclose(B, 0, atol=1e-9)

    def test_published_unsymmetric_laminate_response(self):
        # Kaw's [0/30/-45] graphite/epoxy laminate, 5 mm plies, Nx = Ny = 1000 N/m (SI units).
        si = {"E1": 181e9, "E2": 10.3e9, "G12": 7.17e9, "nu12": 0.28}
        layup = [{"stiffness": si, "angle_deg": a, "thickness": 0.005} for a in (0, 30, -45)]
        A, B, D = LAM["abd"](layup)
        self.assertAlmostEqual(A[0, 0] / 1.739e9, 1, places=3)
        self.assertAlmostEqual(B[0, 0] / -3.129e6, 1, places=3)
        self.assertAlmostEqual(D[0, 0] / 3.343e4, 1, places=3)
        strain, curvature, _ = LAM["ply_stresses"](layup, np.array([1000.0, 1000.0, 0.0]))
        np.testing.assert_allclose(strain, [3.123e-7, 3.492e-6, -7.598e-7], rtol=5e-4)
        np.testing.assert_allclose(curvature, [2.971e-5, -3.285e-4, 4.101e-4], rtol=5e-4)

    def test_ply_stresses_integrate_back_to_the_applied_resultants(self):
        layup = [ply(a, t) for a, t in ((0, 0.2), (30, 0.125), (-45, 0.3), (90, 0.15))]
        N, M = np.array([120.0, -40.0, 15.0]), np.array([3.0, 1.5, -0.7])
        _, _, rows = LAM["ply_stresses"](layup, N, M)
        force, moment = np.zeros(3), np.zeros(3)
        for bottom, top in zip(rows[0::2], rows[1::2]):
            back = np.linalg.inv(self.rotation(bottom["angle_deg"]))      # material axes back to laminate axes
            sb, st = back @ bottom["stress"], back @ top["stress"]
            zb, zt = bottom["z"], top["z"]
            force += (sb + st) / 2 * (zt - zb)                               # stress is linear through a ply
            moment += (sb * (2 * zb + zt) + st * (zb + 2 * zt)) * (zt - zb) / 6
        np.testing.assert_allclose(force, N, rtol=1e-10, atol=1e-10)
        np.testing.assert_allclose(moment, M, rtol=1e-10, atol=1e-10)

    @staticmethod
    def rotation(angle_deg):
        c, s = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
        return np.array([[c * c, s * s, 2 * c * s], [s * s, c * c, -2 * c * s], [-c * s, c * s, c * c - s * s]])


class CriteriaTests(unittest.TestCase):
    #: the 60 degree graphite/epoxy lamina under (2, -3, 4) S of Kaw's failure-theory examples
    LOCAL = LAM["to_material_axes"]([2.0, -3.0, 4.0], 60.0)

    def test_maximum_stress_reserve_is_the_smallest_strength_ratio(self):
        result = LAM["max_stress"](self.LOCAL, STRENGTH)
        self.assertEqual(result["mode"], "shear")
        self.assertAlmostEqual(result["reserve"], STRENGTH["S"] / 4.165063509, places=6)
        self.assertAlmostEqual(result["reserve"], 16.33, places=2)

    def test_tsai_wu_reserve_solves_the_quadratic(self):
        s1, s2, t = self.LOCAL
        f12 = -0.5 * math.sqrt(1 / (1500.0 * 1500.0) / (40.0 * 246.0))

        def polynomial(r):
            return ((1 / 40.0 - 1 / 246.0) * s2 * r + (s1 * r) ** 2 / 1500.0 ** 2 + (s2 * r) ** 2 / (40.0 * 246.0)
                    + (t * r / 68.0) ** 2 + 2 * f12 * s1 * s2 * r * r - 1)
        lo, hi = 0.0, 100.0
        for _ in range(200):                                             # independent bisection
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if polynomial(mid) < 0 else (lo, mid)
        result = LAM["tsai_wu"](self.LOCAL, STRENGTH, -0.5)
        self.assertAlmostEqual(result["reserve"], lo, places=9)
        self.assertAlmostEqual(result["reserve"], 22.39, places=2)
        with self.assertRaises(ValueError):
            LAM["tsai_wu"](self.LOCAL, STRENGTH, 1.0)

    def test_every_criterion_gives_one_at_each_pure_strength(self):
        pure = {"fibre_tension": (1500.0, 0, 0), "fibre_compression": (-1500.0, 0, 0), "matrix_tension": (0, 40.0, 0),
                "matrix_compression": (0, -246.0, 0), "shear": (0, 0, 68.0)}
        for mode, stress in pure.items():
            self.assertAlmostEqual(LAM["max_stress"](stress, STRENGTH)["reserve"], 1.0, places=12, msg=mode)
            self.assertAlmostEqual(LAM["tsai_wu"](stress, STRENGTH, -0.5)["reserve"], 1.0, places=12, msg=mode)
            self.assertAlmostEqual(LAM["hashin"](stress, STRENGTH, 90.0)["reserve"], 1.0, places=12, msg=mode)
            if stress[0] == 0:
                self.assertAlmostEqual(LAM["puck_inter_fibre"](stress, STRENGTH, 0.30, 0.25)["reserve"], 1.0,
                                       places=12, msg=mode)

    def test_off_axis_strength_closed_forms(self):
        for angle in (5.0, 15.0, 30.0, 45.0, 60.0, 85.0):
            c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
            stress = LAM["to_material_axes"]([1.0, 0.0, 0.0], angle)
            expected = min(1500.0 / c ** 2, 40.0 / s ** 2, 68.0 / (s * c))
            self.assertAlmostEqual(LAM["max_stress"](stress, STRENGTH)["reserve"], expected, places=8)
            hashin = LAM["hashin"](stress, STRENGTH, 90.0)
            matrix = 1 / math.sqrt(s ** 4 / 40.0 ** 2 + (s * c / 68.0) ** 2)
            fibre = 1 / math.sqrt(c ** 4 / 1500.0 ** 2 + (s * c / 68.0) ** 2)
            self.assertAlmostEqual(hashin["reserve"], min(matrix, fibre), places=8)

    def test_puck_modes_equal_the_fracture_plane_search(self):
        cases = [(20, 30), (40, 0), (0, 68), (10, 70), (-30, 80), (-50, 60), (-100, 60), (-150, 40), (-200, 20),
                 (-246, 0), (-5, 1), (-120, -75)]
        seen = set()
        for s2, t in cases:
            result = LAM["puck_inter_fibre"]((0.0, s2, t), STRENGTH, 0.30, 0.25)
            seen.add(result["mode"])
            self.assertAlmostEqual(result["index"], puck_fracture_plane_search(s2, t, 0.30, 0.25), places=5,
                                   msg=f"{s2}, {t}")
        self.assertEqual(seen, {"A", "B", "C"})

    def test_puck_exposure_is_continuous_and_homogeneous(self):
        S, Yc, pm = STRENGTH["S"], STRENGTH["Yc"], 0.25
        Ra = S / (2 * pm) * (math.sqrt(1 + 2 * pm * Yc / S) - 1)
        t_c = S * math.sqrt(1 + 2 * pm * Ra / S)
        for scale in (0.999999, 1.000001):                               # either side of the B to C change
            self.assertAlmostEqual(LAM["puck_inter_fibre"]((0, -Ra, t_c * scale), STRENGTH, 0.30, pm)["index"], 1.0, places=5)
        for s2, t in ((25.0, 40.0), (-40.0, 70.0), (-180.0, 30.0)):
            one = LAM["puck_inter_fibre"]((0, s2, t), STRENGTH, 0.30, pm)["index"]
            self.assertAlmostEqual(LAM["puck_inter_fibre"]((0, 3 * s2, 3 * t), STRENGTH, 0.30, pm)["index"], 3 * one, places=10)

    def test_reserve_factor_brings_each_criterion_to_its_limit(self):
        rng = np.random.default_rng(20261110)
        for _ in range(200):
            stress = rng.uniform(-1, 1, 3) * (800.0, 150.0, 60.0)
            r = LAM["tsai_wu"](stress, STRENGTH, -0.5)["reserve"]
            self.assertAlmostEqual(LAM["tsai_wu"](stress * r, STRENGTH, -0.5)["index"], 1.0, places=9)
            for name, call in (("hashin", lambda v: LAM["hashin"](v, STRENGTH, 90.0)),
                               ("puck", lambda v: LAM["puck_inter_fibre"](v, STRENGTH, 0.30, 0.25)),
                               ("max", lambda v: LAM["max_stress"](v, STRENGTH))):
                self.assertAlmostEqual(call(stress * call(stress)["reserve"])["reserve"], 1.0, places=9, msg=name)


class AssessmentTests(unittest.TestCase):
    def test_cross_ply_fails_first_in_the_transverse_plies(self):
        layup = [ply(a, tsai_wu_f12_star=-0.5, hashin_St=90.0, **PUCK) for a in (0, 90, 90, 0)]
        report = LAM["assess"](layup, [100.0, 0.0, 0.0])
        Q = LAM["reduced_stiffness"](**STIFFNESS)
        A = (Q + explicit_qbar(90)) * 0.25                                # two plies of each, 0.125 thick
        ex, ey = np.linalg.solve(A[:2, :2], [100.0, 0.0])
        transverse = Q[1, 1] * ex + Q[0, 1] * ey                          # s2 of a 90 degree ply
        first = report["first_ply_failure"]
        self.assertEqual({"max_stress", "tsai_wu", "hashin", "puck_inter_fibre"}, set(first))
        for name in ("max_stress", "hashin", "puck_inter_fibre"):
            self.assertIn(first[name]["ply"], (1, 2), name)
            self.assertAlmostEqual(first[name]["reserve"], 40.0 / transverse, places=6, msg=name)
        self.assertEqual(first["puck_inter_fibre"]["mode"], "A")

    def test_a_criterion_without_its_parameters_is_not_evaluated(self):
        report = LAM["assess"]([ply(0), ply(90)], [10.0, 0.0, 0.0])
        self.assertEqual(set(report["first_ply_failure"]), {"max_stress"})
        with self.assertRaises(KeyError):
            LAM["assess"]([{"stiffness": STIFFNESS, "angle_deg": 0, "thickness": 0.1}], [1.0, 0, 0])

    def test_supplied_ply_stresses_bypass_lamination_theory(self):
        rows = [{"ply": 0, "face": "top", "stress": [0.0, 20.0, 0.0]}, {"ply": 1, "face": "top", "stress": [750.0, 0.0, 0.0]}]
        report = LAM["assess"]([ply(0), ply(0)], None, ply_stress_rows=rows)
        self.assertEqual(report["first_ply_failure"]["max_stress"], {"reserve": 2.0, "mode": "matrix_tension", "ply": 0, "face": "top"})
        self.assertIn("supplied", report["source"]["method"])

    def test_command_line_writes_a_report_and_never_overwrites(self):
        case = {"materials": {"example": {"stiffness": STIFFNESS, "strength": STRENGTH, "hashin_St": 90.0}},
                "layup": [{"material": "example", "angle_deg": a, "thickness": 0.125} for a in (0, 90, 90, 0)],
                "N": [100.0, 0.0, 0.0]}
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "case.json", Path(tmp) / "report.json"
            source.write_text(json.dumps(case))
            command = [sys.executable, str(SCRIPT), str(source), "--output", str(output)]
            done = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            report = json.loads(output.read_text())
            self.assertEqual(report["schema"], "laminate-failure/1")
            self.assertEqual(set(report["first_ply_failure"]), {"max_stress", "hashin"})
            self.assertIn("no delamination", report["claims"])
            self.assertNotIn("Infinity", output.read_text())            # an unloaded mode is null, not Infinity
            self.assertNotEqual(subprocess.run(command, capture_output=True, text=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
