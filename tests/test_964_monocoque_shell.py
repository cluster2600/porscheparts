import json
import unittest
from pathlib import Path

try:
    import numpy as np
except ImportError:          # the host may lack numpy; the outline checks do not need it
    np = None

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "twins/964-chassis/monocoque"


class MonocoqueShellTests(unittest.TestCase):
    def test_traced_outline_matches_published_dimensions(self) -> None:
        p = json.loads((SHELL / "data/profiles-50-05a.json").read_text(encoding="utf-8"))
        d = [q[0] for q in p["side_top"]]
        z = [q[1] for q in p["side_top"]]
        self.assertAlmostEqual(max(z), 1310.0, delta=1.0)        # anchored roof height
        self.assertLess(min(d), -700.0)                           # reaches the P1 plane (-722)
        self.assertGreater(max(d), 3030.0)                        # reaches the P16 plane (3034.5)
        mid = [w for x, w in p["plan_half_width"] if 800 < x < 1500]
        self.assertTrue(mid and all(700 < w < 900 for w in mid)) # sills, at body width
        for name in ("door_aperture", "quarter_window", "rear_wheel_house"):
            self.assertGreater(len(p["openings"][name]), 20)

    @unittest.skipIf(np is None, "numpy not installed")
    def test_torsion_snapshot_is_consistent(self) -> None:
        t = np.load(SHELL / "derived/torsion-snapshot.npz")
        self.assertEqual(len(t["points"]), len(t["von_mises"]))
        self.assertLess(int(t["triangles"].max()), len(t["points"]))
        self.assertGreater(float(t["K"]), 0.0)
        self.assertAlmostEqual(float(t["thickness_mm"]), 0.8)


if __name__ == "__main__":
    unittest.main()
