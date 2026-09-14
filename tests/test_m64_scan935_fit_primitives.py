"""Tests synthétiques des ajustements utilisés sur le scan 935 (numpy seul).

Aucun scan n'est lu : plans, cercles et perçages sont générés avec des
paramètres connus et bruités, puis retrouvés dans une tolérance.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

try:
    import numpy as np
except ImportError:  # pragma: no cover - la CI installe numpy
    np = None

ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / 'twins' / 'm64-cylinder-head' / 'source' / 'scan935'


def load(name):
    spec = importlib.util.spec_from_file_location(f'scan935_{name}', MODULE_DIR / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MODULE_DIR))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(MODULE_DIR))
    return module


@unittest.skipIf(np is None, 'numpy absent')
class FitPrimitivesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fp = load('fit_primitives')
        cls.rng = np.random.default_rng(1)

    def test_plane_with_outliers(self):
        normal = np.array([0.02, -0.01, 1.0])
        normal /= np.linalg.norm(normal)
        u, v = self.fp.orthonormal_basis(normal)
        uv = self.rng.uniform(-60, 60, (4000, 2))
        pts = uv[:, :1] * u + uv[:, 1:] * v + normal * (-87.0 + self.rng.normal(0, 0.03, (4000, 1)))
        outliers = self.rng.uniform(-60, 60, (600, 3))
        c, n, inl = self.fp.ransac_plane(np.vstack((pts, outliers)), 0.15,
                                         reference_normal=np.array([0, 0, 1.0]))
        self.assertLess(self.fp.angle_between_deg(n, normal), 0.05)
        self.assertAlmostEqual(float(c @ n), -87.0, delta=0.02)
        stats = self.fp.residual_stats(self.fp.plane_residuals(pts, c, n))
        self.assertAlmostEqual(stats['rms'], 0.03, delta=0.01)

    def test_circle_partial_arc_with_outliers(self):
        ang = self.rng.uniform(0, 1.6 * np.pi, 800)
        xy = np.column_stack((128.1 + 56.7 * np.cos(ang), -168.7 + 56.7 * np.sin(ang)))
        xy += self.rng.normal(0, 0.05, xy.shape)
        xy = np.vstack((xy, self.rng.uniform(60, 200, (200, 2)) - [0, 250]))
        c, r, inl = self.fp.ransac_circle(xy, 0.2, radius_range=(40, 70))
        self.assertAlmostEqual(2 * r, 113.4, delta=0.05)
        self.assertLess(np.linalg.norm(c - [128.1, -168.7]), 0.05)
        self.assertTrue(270.0 <= self.fp.angular_coverage_deg(xy[inl], c) <= 300.0)

    def test_tilted_bore_cylinder(self):
        axis = np.array([-0.2, 0.43, -0.88])
        axis /= np.linalg.norm(axis)
        origin = np.array([101.0, -170.0, -116.0])
        u, v = self.fp.orthonormal_basis(axis)
        t = self.rng.uniform(-6, 6, 3000)
        ang = self.rng.uniform(0, 2 * np.pi, 3000)
        pts = origin + np.outer(t, axis) + 5.6 * (np.outer(np.cos(ang), u) + np.outer(np.sin(ang), v))
        pts += self.rng.normal(0, 0.05, pts.shape)
        hint = axis + np.array([0.08, -0.05, 0.03])
        o, a, r, res, inl = self.fp.ransac_cylinder(pts, hint / np.linalg.norm(hint), 0.3)
        self.assertLess(self.fp.angle_between_deg(a, axis), 0.3)
        self.assertAlmostEqual(2 * r, 11.2, delta=0.03)
        offset = (o - origin) - ((o - origin) @ axis) * axis
        self.assertLess(np.linalg.norm(offset), 0.05)

    def test_stud_pattern_recovered(self):
        measure = load('measure_interfaces')
        centres = np.array([[-43.2, 42.8], [43.1, 43.0], [43.3, -42.6], [-42.9, -42.9]])
        pts = []
        for cx, cy in centres:
            ang = self.rng.uniform(0, 2 * np.pi, 400)
            z = self.rng.uniform(-10, -2, 400)
            pts.append(np.column_stack((cx + 5.3 * np.cos(ang), cy + 5.3 * np.sin(ang), z)))
        pts = np.vstack(pts) + self.rng.normal(0, 0.04, (1600, 3))
        holes = [measure.fit_axis_hole(pts, np.array([cx, cy, -6.0]), np.array([0, 0, 1.0]),
                                       ball=9.0, radius_range=(4.0, 7.0)) for cx, cy in centres]
        pattern = measure.pattern_summary([h['centre_xy'] for h in holes])
        for hole, (cx, cy) in zip(holes, centres):
            self.assertAlmostEqual(hole['diameter'], 10.6, delta=0.05)
            self.assertLess(np.hypot(hole['centre_xy'][0] - cx, hole['centre_xy'][1] - cy), 0.05)
        self.assertAlmostEqual(pattern['span_x'], 86.5, delta=0.1)
        self.assertEqual(pattern['count'], 4)

    def test_cluster_circles_in_slab(self):
        measure = load('measure_interfaces')
        pts = []
        for cx, cy, r in [(0, 0, 5.3), (40, 0, 3.6), (0, 40, 20.0)]:
            n = int(80 * r)
            ang = self.rng.uniform(0, 2 * np.pi, n)
            pts.append(np.column_stack((cx + r * np.cos(ang), cy + r * np.sin(ang))))
        found = measure.circles_in_slab(np.vstack(pts), radius_range=(2, 25))
        diam = sorted(round(f['diameter'], 1) for f in found)
        self.assertEqual(diam, [7.2, 10.6, 40.0])


class Scan935ContractFactsTest(unittest.TestCase):
    """Les faits 935 restent candidats : aucun nominal, aucun statut « found »."""

    def setUp(self):
        import json
        base = ROOT / 'twins' / 'm64-cylinder-head'
        self.contract = json.loads((base / 'interface-contract.json').read_text())
        self.evidence = json.loads((base / 'evidence' / 'scan935-interfaces-20260914.json').read_text())

    def test_candidate_facts_never_promoted(self):
        facts = [f for item in self.contract['critical_interfaces'].values()
                 for f in item['documented_partial_facts'] if f['source'] == 'W935']
        self.assertGreaterEqual(len(facts), 8)
        for f in facts:
            self.assertFalse(f['promoted_to_nominal'])
            self.assertEqual(f['confidence'], 'measured_on_935_scan_evidence_C')
        for item in self.contract['critical_interfaces'].values():
            self.assertIsNone(item['nominal'])
            self.assertNotEqual(item['status'], 'found')

    def test_evidence_is_numbers_only_and_fingerprinted(self):
        self.assertEqual(self.evidence['source']['sha256'],
                         '4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486')
        self.assertFalse(self.evidence['source']['raw_and_geometric_derivatives_in_git'])
        self.assertEqual(self.evidence['scale_assessment']['conclusion'], 'mm_coherent_not_calibrated')
        png = list((ROOT / 'twins' / 'm64-cylinder-head' / 'source' / 'scan935').glob('*.png'))
        self.assertEqual(png, [])


if __name__ == '__main__':
    unittest.main()
