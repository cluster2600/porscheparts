"""Check frozen replay identities and stiffness independently from its summary."""
import gzip
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "twins/964-chassis/monocoque/s6-replay-20261028"


class S6ReplayTests(unittest.TestCase):
    def test_hashes_input_deck_and_qualification_boundaries(self):
        report = json.loads((REPLAY / "validation.json").read_text())
        for name, digest in report["files_sha256"].items():
            self.assertEqual(hashlib.sha256((REPLAY / name).read_bytes()).hexdigest(), digest, name)
        runs = json.loads((REPLAY / "result-after-2.json").read_text())["runs"]
        self.assertEqual(hashlib.sha256(gzip.decompress((REPLAY / "shell.inp.gz").read_bytes())).hexdigest(), runs[0]["file_hashes"]["shell.inp"])
        for name in ("shell.inp", "shell.dat", "parsed.npz"):
            self.assertEqual(runs[0]["file_hashes"][name], runs[1]["file_hashes"][name])
        self.assertFalse(report["mesh_converged"])
        self.assertFalse(report["physical_validation"])
        self.assertFalse(report["manufacturing_authorized"])
        self.assertIsNone(report["strength_pass"])
        self.assertIsNone(report["allowable_MPa"])

    def test_stiffness_from_mesh_and_displacements(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("NumPy required")
        model = np.load(REPLAY / "model.npz", allow_pickle=False)
        result = np.load(REPLAY / "parsed.npz", allow_pickle=False)
        points, u = model["points"], result["u"]
        left, right = model["front_left"], model["front_right"]
        self.assertTrue(np.isfinite(points).all() and np.isfinite(u).all())
        arm = points[left, 1].mean() - points[right, 1].mean()
        angle = np.degrees((u[left, 2].mean() - u[right, 2].mean()) / arm)
        k = (1000 * arm / 1000) / angle
        self.assertAlmostEqual(k, 19899.782469151465, delta=1e-6)
        self.assertLess(np.abs(u[model["rear"]]).max(), 1e-12)
        audit = json.loads((REPLAY / "independent-run-1.json").read_text())
        self.assertAlmostEqual(np.linalg.norm(audit["force_sum_N"]) / 2000, audit["force_balance_relative_error"], delta=1e-15)
        self.assertLess(audit["force_balance_relative_error"], 1e-4)

    def test_bending_replay_hashes_and_stiffness(self):
        folder = REPLAY / "bending"
        report = json.loads((folder / "validation.json").read_text())
        for name, digest in report["files_sha256"].items():
            self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), digest, name)
        runs = json.loads((folder / "result-after-2.json").read_text())["runs"]
        self.assertEqual(hashlib.sha256(gzip.decompress((folder / "shell.inp.gz").read_bytes())).hexdigest(), runs[0]["files_sha256"]["shell.inp"])
        for name in ("shell.inp", "shell.dat", "parsed.npz"):
            self.assertEqual(runs[0]["files_sha256"][name], runs[1]["files_sha256"][name])
        for name in ("mesh_converged", "physical_validation", "manufacturing_authorized"):
            self.assertFalse(report[name])
        self.assertIsNone(report["strength_pass"])
        self.assertIsNone(report["allowable_MPa"])
        try:
            import numpy as np
        except ImportError:
            self.skipTest("NumPy required for independent field checks")
        model = np.load(folder / "model.npz", allow_pickle=False)
        reference = np.load(REPLAY / "model.npz", allow_pickle=False)
        for name in ("points", "triangles"):
            np.testing.assert_array_equal(model[name], reference[name])
        u = np.load(folder / "parsed.npz", allow_pickle=False)["u"]
        self.assertTrue(np.isfinite(u).all())
        forces = model["forces_N"]
        self.assertAlmostEqual(forces.sum(), -2000, delta=1e-9)
        delta = -float(np.dot(u[model["load_nodes"], 2], forces) / forces.sum())
        self.assertAlmostEqual(2000 / delta, report["K_N_per_mm"], delta=1e-6)
        self.assertAlmostEqual(np.linalg.norm(u, axis=1).max(), 0.2860527227290452, delta=1e-9)
        audit = json.loads((folder / "independent-run-1.json").read_text())
        self.assertAlmostEqual(np.linalg.norm(audit["force_sum_N"]) / 2000, audit["force_balance_relative_error"], delta=1e-15)
        self.assertLess(audit["force_balance_relative_error"], 1e-4)


if __name__ == "__main__":
    unittest.main()
