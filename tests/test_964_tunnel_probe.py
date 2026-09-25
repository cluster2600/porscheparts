from pathlib import Path
import hashlib
import json
import runpy
import unittest

try:
    import numpy as np
except ImportError:
    np = None


@unittest.skipIf(np is None, "numpy required for scan diagnostics")
class TunnelProbeTests(unittest.TestCase):
    def test_sparse_sections_keep_their_station_and_never_prove_clearance(self):
        probe = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                                  "twins/964-chassis/source/tunnel_probe.py"))["probe"]
        points = []
        for x in range(-1400, 1, 200):
            for y in np.linspace(260, 390, 61):
                points.extend([[x, y, 100], [x, -y, 100]])
            if x != -1200:
                points.extend([[x, y, 102 if x <= -400 else 400] for y in np.linspace(-59, 59, 61)])
        report = probe(np.array(points))
        self.assertEqual([s["x_mm"] for s in report["stations"]], list(range(-1400, 1, 200)))
        self.assertIsNone(report["stations"][1]["visible_relief_mm"])
        self.assertEqual(report["stations"][1]["status"], "insufficient_coverage")
        self.assertEqual(report["cabin_summary"], {"observed_stations": 5, "expected_stations": 6,
                                                  "relief_min_max_mm": [2.0, 2.0]})
        self.assertEqual(report["stations"][-1]["visible_relief_mm"], 300.0)
        self.assertFalse(any(report["release_flags"].values()))
        empty = probe(np.empty((0, 3)))
        self.assertIsNone(empty["cabin_summary"]["relief_min_max_mm"])
        self.assertTrue(all(s["status"] == "insufficient_coverage" for s in empty["stations"]))
        for invalid in (np.array([[0, 0, np.nan]]), np.array([0, 1, 2])):
            with self.assertRaises(ValueError):
                probe(invalid)

        root = Path(__file__).resolve().parents[1]
        twin = root / "twins/964-chassis"
        registration_path = twin / "derived/scan-recalage-20260925.json"
        registration = json.loads(registration_path.read_text())
        actual = json.loads((twin / "derived/tunnel-visibility-20260925.json").read_text())
        self.assertEqual(actual["provenance"]["registration_report_sha256"],
                         hashlib.sha256(registration_path.read_bytes()).hexdigest())
        self.assertEqual(actual["provenance"]["script_sha256"],
                         hashlib.sha256((twin / "source/tunnel_probe.py").read_bytes()).hexdigest())
        self.assertEqual(actual["provenance"]["scan_sha256"], registration["source_sha256"])
        self.assertEqual(actual["provenance"]["vertices_sha256"], registration["outputs"]["verts_vehicle.npy"])
        self.assertFalse(any(actual["release_flags"].values()))
        self.assertFalse(registration["structural_datums_registered"])
        self.assertFalse(registration["manufacturing_released"])
        for step in registration["steps"]:
            self.assertEqual(step["exit_code"], 0)
            self.assertEqual(step["sha256"], hashlib.sha256((root / step["script"]).read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
